#!/usr/bin/env python3
"""Format and schedule existing WordPress drafts for PBL.

The formatter intentionally limits edits to article-body paragraphs and
article-specific emphasis. Fixed WordPress blocks and JSON-LD are validated
before and after every transformation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup, Comment, NavigableString
from requests.auth import HTTPBasicAuth

from post_to_wp import load_config


JST = timezone(timedelta(hours=9))
RED_STYLE = "color: #ff0000;"
FIXED_SELECTORS = {
    "tldr": ".tldr",
    "toc": ".toc",
    "disclaimer": ".disclaimer",
    "footer": "footer",
    "jsonld": 'script[type="application/ld+json"]',
}
HEADING_RE = re.compile(
    r"<h2\b[^>]*>(?P<title>.*?)</h2>", re.IGNORECASE | re.DOTALL
)
PARAGRAPH_RE = re.compile(
    r"<p(?P<attrs>\s[^>]*)?>(?P<inner>.*?)</p>", re.IGNORECASE | re.DOTALL
)
QUOTE_RE = re.compile(r"「[^「」]{8,100}」")


class PipelineError(RuntimeError):
    """Raised when a safety check fails."""


def auth(config: dict[str, str]) -> HTTPBasicAuth:
    return HTTPBasicAuth(config["WP_USER"], config["WP_APP_PASSWORD"])


def api_get(config: dict[str, str], path: str, **params: Any) -> Any:
    response = requests.get(
        f"{config['WP_URL']}/wp-json/wp/v2/{path}",
        params=params,
        auth=auth(config),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def api_post(config: dict[str, str], post_id: int, payload: dict[str, Any]) -> Any:
    response = requests.post(
        f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
        json=payload,
        auth=auth(config),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def fetch_post(config: dict[str, str], post_id: int) -> dict[str, Any]:
    return api_get(config, f"posts/{post_id}", context="edit")


def fetch_drafts(config: dict[str, str]) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = api_get(
            config,
            "posts",
            context="edit",
            status="draft",
            per_page=100,
            page=page,
        )
        posts.extend(batch)
        if len(batch) < 100:
            return posts
        page += 1


def raw_title(post: dict[str, Any]) -> str:
    return post.get("title", {}).get("raw") or post.get("title", {}).get("rendered", "")


def raw_content(post: dict[str, Any]) -> str:
    return post.get("content", {}).get("raw") or post.get("content", {}).get("rendered", "")


def content_hash(html: str) -> str:
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def normalized_text(html: str) -> str:
    return re.sub(r"\s+", "", BeautifulSoup(html, "html.parser").get_text())


def protected_structure(html: str) -> tuple[list[tuple[str, tuple[tuple[str, str], ...]]], list[str]]:
    """Return non-formatting element/attribute and comment signatures."""
    soup = BeautifulSoup(html, "html.parser")
    tags: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    for tag in soup.find_all(True):
        if tag.name in {"br", "strong"}:
            continue
        if tag.name == "span" and "#ff0000" in str(tag.get("style", "")).lower().replace(" ", ""):
            continue
        attrs = tuple(
            sorted(
                (key, " ".join(value) if isinstance(value, list) else str(value))
                for key, value in tag.attrs.items()
            )
        )
        tags.append((tag.name, attrs))
    comments = [str(comment) for comment in soup.find_all(string=lambda value: isinstance(value, Comment))]
    return tags, comments


def fixed_counts(html: str) -> dict[str, int]:
    soup = BeautifulSoup(html, "html.parser")
    return {name: len(soup.select(selector)) for name, selector in FIXED_SELECTORS.items()}


def validate_jsonld(html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    for index, script in enumerate(soup.select(FIXED_SELECTORS["jsonld"]), start=1):
        try:
            json.loads(script.string or script.get_text())
        except json.JSONDecodeError as exc:
            raise PipelineError(f"JSON-LD {index} is invalid: {exc}") from exc


def validate_toc(html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    ids = {tag.get("id") for tag in soup.find_all(id=True)}
    for link in soup.select(".toc a[href^='#']"):
        target = link.get("href", "")[1:]
        if target not in ids:
            raise PipelineError(f"TOC target is missing: #{target}")


def body_bounds(html: str) -> tuple[int, int]:
    first_h2 = re.search(r"<h2\b", html, re.IGNORECASE)
    if not first_h2:
        raise PipelineError("article body has no h2")
    end_candidates = [
        match.start()
        for pattern in (
            r'<h2\b[^>]*id=["\']references["\']',
            r'<div\b[^>]*class=["\'][^"\']*disclaimer',
        )
        if (match := re.search(pattern, html[first_h2.start() :], re.IGNORECASE))
    ]
    end = first_h2.start() + min(end_candidates) if end_candidates else len(html)
    return first_h2.start(), end


def section_span(html: str, heading: str) -> tuple[int, int] | None:
    matches = list(HEADING_RE.finditer(html))
    for index, match in enumerate(matches):
        title = BeautifulSoup(match.group("title"), "html.parser").get_text(strip=True)
        if title == heading:
            end = matches[index + 1].start() if index + 1 < len(matches) else len(html)
            return match.end(), end
    return None


def paragraph_texts(section_html: str) -> list[str]:
    soup = BeautifulSoup(section_html, "html.parser")
    return [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]


def replace_once_in_span(
    html: str,
    span: tuple[int, int],
    text: str,
    wrapper: str,
) -> tuple[str, bool]:
    start, end = span
    section = html[start:end]
    if not text:
        return html, False

    def modify_paragraph(match: re.Match[str]) -> str:
        paragraph_html = match.group(0)
        soup = BeautifulSoup(paragraph_html, "html.parser")
        paragraph = soup.find("p")
        if paragraph is None:
            return paragraph_html
        for node in list(paragraph.descendants):
            if not isinstance(node, NavigableString) or text not in str(node):
                continue
            ancestors = {parent.name for parent in node.parents if getattr(parent, "name", None)}
            if ancestors & {"a", "script", "style"}:
                continue
            red_ancestor = next(
                (
                    parent
                    for parent in node.parents
                    if getattr(parent, "name", None) == "span"
                    and "#ff0000" in str(parent.get("style", "")).lower().replace(" ", "")
                ),
                None,
            )
            wants_red = "#ff0000" in wrapper
            wants_bold = "<strong>" in wrapper
            strong_ancestor = next(
                (parent for parent in node.parents if getattr(parent, "name", None) == "strong"),
                None,
            )
            if (not wants_red or red_ancestor) and (not wants_bold or strong_ancestor):
                return paragraph_html
            before, after = str(node).split(text, 1)
            effective_wrapper = wrapper
            if wants_red and wants_bold and strong_ancestor and not red_ancestor:
                effective_wrapper = f'<span style="{RED_STYLE}">{{text}}</span>'
            elif wants_red and wants_bold and red_ancestor and not strong_ancestor:
                effective_wrapper = "<strong>{text}</strong>"
            fragment = BeautifulSoup(effective_wrapper.format(text=text), "html.parser")
            replacement: list[Any] = []
            if before:
                replacement.append(NavigableString(before))
            replacement.extend(list(fragment.contents))
            if after:
                replacement.append(NavigableString(after))
            node.replace_with(*replacement)
            return str(paragraph)
        return paragraph_html

    changed = False

    def replace_first(match: re.Match[str]) -> str:
        nonlocal changed
        if changed:
            return match.group(0)
        result = modify_paragraph(match)
        changed = result != match.group(0)
        return result

    updated_section = PARAGRAPH_RE.sub(replace_first, section)
    return html[:start] + updated_section + html[end:], changed


def red_count(html: str) -> int:
    start, end = body_bounds(html)
    soup = BeautifulSoup(html[start:end], "html.parser")
    return sum(
        1
        for tag in soup.find_all(style=True)
        if "#ff0000" in str(tag.get("style", "")).lower().replace(" ", "")
    )


def ensure_intro_emphasis(html: str) -> tuple[str, list[str]]:
    span = section_span(html, "はじめに")
    if not span:
        return html, []
    section = html[span[0] : span[1]]
    texts = paragraph_texts(section)
    quotes = []
    for text in texts:
        quotes.extend(QUOTE_RE.findall(text))
    changes: list[str] = []
    if quotes:
        first = quotes[0]
        if f"<strong>{first}</strong>" not in section:
            html, changed = replace_once_in_span(html, span, first, "<strong>{text}</strong>")
            if changed:
                changes.append(f"bold:{first}")
                span = section_span(html, "はじめに") or span
    if len(quotes) > 1 and red_count(html) < 4:
        second = quotes[1]
        html, changed = replace_once_in_span(
            html,
            span,
            second,
            f'<span style="{RED_STYLE}"><strong>{{text}}</strong></span>',
        )
        if changed:
            changes.append(f"red+bold:{second}")
    return html, changes


def concept_candidate(section_html: str, kind: str) -> str | None:
    text = BeautifulSoup(section_html, "html.parser").get_text(" ", strip=True)
    if kind == "why":
        patterns = [
            r"(?:ここで)?大切なの(?:が|は)、?([^。]{2,45}?)(?:です|という点です)(?:。|$)",
            r"重要なの(?:が|は)、?([^。]{2,45}?)(?:です|という点です)(?:。|$)",
        ]
    else:
        patterns = [
            r"「([^「」]{0,20}どの瞬間[^「」]{0,45})」",
            r"「([^「」]{0,35}どこで[^「」]{0,35})」",
            r"(どの瞬間[^。]{4,55})",
        ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip(" 、。")
    if kind == "why":
        key_phrases = (
            "背骨と骨盤の前後バランス",
            "肩甲骨と胸郭",
            "胸郭と肩甲骨",
            "骨の成長余力",
            "成長の残り具合",
            "骨盤と体幹",
            "体の重心",
            "足裏の荷重",
            "骨盤の傾き",
            "股関節の動き",
            "胸郭の動き",
            "背骨の並び方",
            "片脚で支える瞬間",
        )
        for phrase in key_phrases:
            if phrase in text:
                return phrase
        for sentence in (part.strip() for part in text.split("。")):
            if 10 <= len(sentence) <= 90 and any(
                marker in sentence for marker in ("大切", "ポイント", "関係")
            ):
                return sentence
    else:
        fallback = re.search(r"(?:まずは|最初に)、?([^。]{10,70})", text)
        if fallback:
            return fallback.group(1).strip(" 、。")
    return None


def conclusion_candidate(section_html: str) -> str | None:
    paragraphs = paragraph_texts(section_html)
    candidates: list[str] = []
    for paragraph in paragraphs:
        candidates.extend(s.strip() + "。" for s in paragraph.split("。") if 10 <= len(s.strip()) <= 90)
    preferred = [
        sentence
        for sentence in candidates
        if any(word in sentence for word in ("できること", "大切", "少しずつ", "つなげ"))
    ]
    return (preferred or candidates)[-1] if (preferred or candidates) else None


def add_role_emphasis(html: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    for heading, kind in (("なぜ起こるのか", "why"), ("解決の方向性", "solution")):
        if red_count(html) >= 4:
            break
        span = section_span(html, heading)
        if not span:
            continue
        candidate = concept_candidate(html[span[0] : span[1]], kind)
        if candidate:
            html, changed = replace_once_in_span(
                html,
                span,
                candidate,
                f'<span style="{RED_STYLE}">{{text}}</span>',
            )
            if changed:
                changes.append(f"red:{candidate}")
    if red_count(html) < 4:
        span = section_span(html, "まとめと次の一歩")
        if span:
            candidate = conclusion_candidate(html[span[0] : span[1]])
            if candidate:
                html, changed = replace_once_in_span(
                    html,
                    span,
                    candidate,
                    f'<span style="{RED_STYLE}"><strong>{{text}}</strong></span>',
                )
                if changed:
                    changes.append(f"red+bold:{candidate}")
    return html, changes


def add_breaks_to_inner(inner: str) -> tuple[str, int]:
    if "<script" in inner.lower() or "<style" in inner.lower():
        return inner, 0
    soup = BeautifulSoup(f"<p>{inner}</p>", "html.parser")
    paragraph = soup.find("p")
    if paragraph is None:
        return inner, 0
    added = 0
    for node in list(paragraph.descendants):
        if not isinstance(node, NavigableString) or "。" not in str(node):
            continue
        if node.parent and node.parent.name in {"a", "strong", "span", "em", "script", "style"}:
            continue
        value = str(node)
        parts = value.split("。")
        if len(parts) < 2:
            continue
        replacements: list[Any] = []
        for index, part in enumerate(parts):
            if index < len(parts) - 1:
                replacements.append(NavigableString(part + "。"))
                later_text = "".join(parts[index + 1 :]).strip()
                if later_text:
                    replacements.append(soup.new_tag("br"))
                    replacements.append(NavigableString("\n"))
                    added += 1
            elif part:
                replacements.append(NavigableString(part.lstrip()))
        if replacements:
            node.replace_with(*replacements)
    return paragraph.decode_contents(formatter="minimal"), added


def add_body_breaks(html: str) -> tuple[str, int]:
    start, end = body_bounds(html)
    body = html[start:end]
    total = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal total
        attrs = match.group("attrs") or ""
        inner, added = add_breaks_to_inner(match.group("inner"))
        if added == 0:
            return match.group(0)
        total += added
        return f"<p{attrs}>{inner}</p>"

    formatted = PARAGRAPH_RE.sub(replace, body)
    return html[:start] + formatted + html[end:], total


def format_article(html: str) -> tuple[str, dict[str, Any]]:
    before_counts = fixed_counts(html)
    if any(before_counts.get(name) != 1 for name in FIXED_SELECTORS):
        raise PipelineError(f"fixed element count is not exactly one: {before_counts}")
    validate_jsonld(html)
    validate_toc(html)
    before_text = normalized_text(html)
    before_structure = protected_structure(html)
    formatted, emphasis = ensure_intro_emphasis(html)
    formatted, more_emphasis = add_role_emphasis(formatted)
    emphasis.extend(more_emphasis)
    formatted, breaks_added = add_body_breaks(formatted)
    if normalized_text(formatted) != before_text:
        raise PipelineError("visible article text changed during formatting")
    if fixed_counts(formatted) != before_counts:
        raise PipelineError("fixed element counts changed during formatting")
    if protected_structure(formatted) != before_structure:
        raise PipelineError("protected HTML structure changed during formatting")
    validate_jsonld(formatted)
    validate_toc(formatted)
    return formatted, {
        "breaks_added": breaks_added,
        "emphasis": emphasis,
        "red_count": red_count(formatted),
    }


def backup_posts(posts: Iterable[dict[str, Any]], directory: Path, label: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(JST).strftime("%Y%m%d-%H%M%S-%f")
    path = directory / f"wp-drafts-{label}-{stamp}.json"
    with path.open("x", encoding="utf-8") as handle:
        json.dump(list(posts), handle, ensure_ascii=False, indent=2)
    return path


def selected_drafts(config: dict[str, str], ids: set[int] | None) -> list[dict[str, Any]]:
    posts = fetch_drafts(config)
    posts = [post for post in posts if normalized_text(raw_content(post))]
    if ids is not None:
        posts = [post for post in posts if post["id"] in ids]
        missing = ids - {post["id"] for post in posts}
        if missing:
            raise PipelineError(f"draft IDs not found: {sorted(missing)}")
    return sorted(posts, key=lambda post: post["id"], reverse=True)


def command_inventory(config: dict[str, str]) -> int:
    posts = fetch_drafts(config)
    for post in sorted(posts, key=lambda item: item["id"], reverse=True):
        html = raw_content(post)
        print(
            json.dumps(
                {
                    "id": post["id"],
                    "title": raw_title(post),
                    "text_length": len(normalized_text(html)),
                    "fixed": fixed_counts(html),
                    "red": red_count(html) if re.search(r"<h2\b", html, re.I) else 0,
                },
                ensure_ascii=False,
            )
        )
    return 0


def command_format(
    config: dict[str, str],
    ids: set[int] | None,
    apply: bool,
    backup_dir: Path,
) -> int:
    posts = selected_drafts(config, ids)
    previews: list[tuple[dict[str, Any], str, dict[str, Any]]] = []
    for post in posts:
        formatted, report = format_article(raw_content(post))
        previews.append((post, formatted, report))
        print(json.dumps({"id": post["id"], "title": raw_title(post), **report}, ensure_ascii=False))
    if not apply:
        print(f"DRY_RUN=1 COUNT={len(previews)}")
        return 0
    backup = backup_posts((post for post, _, _ in previews), backup_dir, "before-format")
    print(f"BACKUP={backup}")
    for original, formatted, _ in previews:
        current = fetch_post(config, original["id"])
        if current.get("status") != "draft":
            raise PipelineError(f"post {original['id']} is no longer a draft")
        if raw_content(current) != raw_content(original):
            raise PipelineError(f"post {original['id']} changed after preview")
        try:
            updated = api_post(config, original["id"], {"content": formatted})
            verified = fetch_post(config, original["id"])
            if raw_content(verified) != formatted or verified.get("status") != "draft":
                raise PipelineError(f"post {original['id']} failed post-update verification")
        except Exception:
            try:
                possibly_changed = fetch_post(config, original["id"])
                if raw_content(possibly_changed) != raw_content(original):
                    api_post(config, original["id"], {"content": raw_content(original), "status": "draft"})
                    restored = fetch_post(config, original["id"])
                    if raw_content(restored) != raw_content(original) or restored.get("status") != "draft":
                        raise PipelineError(f"post {original['id']} rollback failed")
                    print(f"ROLLED_BACK={original['id']}")
            except Exception as rollback_error:
                raise PipelineError(
                    f"post {original['id']} update failed and rollback could not be verified: {rollback_error}"
                ) from rollback_error
            raise
        print(f"UPDATED={updated['id']} STATUS={updated['status']}")
    return 0


def schedule_dates(count: int, now: datetime) -> list[datetime]:
    dates = [now]
    first_future = (now + timedelta(days=2)).date()
    for index in range(count - 1):
        day = first_future + timedelta(days=index * 2)
        dates.append(datetime(day.year, day.month, day.day, 13, 0, tzinfo=JST))
    return dates


def load_plan(path: Path) -> dict[str, Any]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("version") != 1 or not isinstance(plan.get("items"), list):
        raise PipelineError(f"invalid publication plan: {path}")
    return plan


def save_plan(plan: dict[str, Any], path: Path, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(plan, handle, ensure_ascii=False, indent=2)
        return
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def command_plan(
    config: dict[str, str],
    ids: set[int] | None,
    path: Path,
) -> int:
    posts = selected_drafts(config, ids)
    now = datetime.now(JST).replace(microsecond=0)
    dates = schedule_dates(len(posts), now)
    items = []
    for index, (post, date) in enumerate(zip(posts, dates)):
        status = "publish" if index == 0 else "future"
        print(f"{post['id']}\t{status}\t{date.isoformat()}\t{raw_title(post)}")
        utc_date = date.astimezone(timezone.utc)
        items.append(
            {
                "id": post["id"],
                "title": raw_title(post),
                "content_sha256": content_hash(raw_content(post)),
                "status": status,
                "date": date.strftime("%Y-%m-%dT%H:%M:%S"),
                "date_gmt": utc_date.strftime("%Y-%m-%dT%H:%M:%S"),
                "qa_approved": False,
            }
        )
    plan = {
        "version": 1,
        "site_url": config["WP_URL"],
        "timezone": "Asia/Tokyo",
        "created_at": now.isoformat(),
        "items": items,
    }
    save_plan(plan, path, exclusive=True)
    print(f"PLAN={path} COUNT={len(items)}")
    return 0


def command_approve(config: dict[str, str], path: Path, ids: set[int]) -> int:
    plan = load_plan(path)
    plan_items = {item["id"]: item for item in plan["items"]}
    missing = ids - set(plan_items)
    if missing:
        raise PipelineError(f"IDs are not in the plan: {sorted(missing)}")
    for post_id in sorted(ids):
        post = fetch_post(config, post_id)
        if post.get("status") != "draft":
            raise PipelineError(f"post {post_id} is not a draft during QA approval")
        if content_hash(raw_content(post)) != plan_items[post_id]["content_sha256"]:
            raise PipelineError(f"post {post_id} content changed after plan creation")
        plan_items[post_id]["qa_approved"] = True
        plan_items[post_id]["qa_approved_at"] = datetime.now(JST).isoformat()
        print(f"QA_APPROVED={post_id}")
    save_plan(plan, path)
    return 0


def wordpress_timezone(config: dict[str, str]) -> str:
    settings = api_get(config, "settings", context="edit")
    return settings.get("timezone") or ""


def schedule_matches(post: dict[str, Any], item: dict[str, Any]) -> bool:
    return (
        post.get("status") == item["status"]
        and post.get("date") == item["date"]
        and post.get("date_gmt") == item["date_gmt"]
        and content_hash(raw_content(post)) == item["content_sha256"]
    )


def command_schedule_plan(
    config: dict[str, str],
    path: Path,
    apply: bool,
    backup_dir: Path,
) -> int:
    plan = load_plan(path)
    if plan.get("site_url") != config["WP_URL"]:
        raise PipelineError("publication plan site does not match configured WordPress site")
    actual_timezone = wordpress_timezone(config)
    if actual_timezone != plan.get("timezone") or actual_timezone != "Asia/Tokyo":
        raise PipelineError(f"unexpected WordPress timezone: {actual_timezone!r}")
    if not plan["items"] or any(not item.get("qa_approved") for item in plan["items"]):
        raise PipelineError("every planned post must be QA-approved before scheduling")
    current_by_id: dict[int, dict[str, Any]] = {}
    pending: list[dict[str, Any]] = []
    for item in plan["items"]:
        current = fetch_post(config, item["id"])
        current_by_id[item["id"]] = current
        if schedule_matches(current, item):
            print(f"ALREADY_MATCHES={item['id']}")
            continue
        if current.get("status") != "draft":
            raise PipelineError(
                f"post {item['id']} is {current.get('status')}, not draft or matching plan"
            )
        if content_hash(raw_content(current)) != item["content_sha256"]:
            raise PipelineError(f"post {item['id']} content does not match approved hash")
        pending.append(item)
        print(f"PENDING={item['id']} STATUS={item['status']} DATE={item['date']}")
    if not apply:
        print(f"DRY_RUN=1 PENDING={len(pending)}")
        return 0
    backup = backup_posts(current_by_id.values(), backup_dir, "before-schedule")
    print(f"BACKUP={backup}")
    ordered = [item for item in pending if item["status"] == "future"] + [
        item for item in pending if item["status"] == "publish"
    ]
    for item in ordered:
        payload = {
            "status": item["status"],
            "date": item["date"],
            "date_gmt": item["date_gmt"],
        }
        api_post(config, item["id"], payload)
        verified = fetch_post(config, item["id"])
        if not schedule_matches(verified, item):
            raise PipelineError(f"post {item['id']} failed schedule verification")
        print(f"SCHEDULED={item['id']} STATUS={item['status']} DATE={item['date']}")
    return 0


def selection_from_args(args: argparse.Namespace) -> set[int] | None:
    if getattr(args, "all", False):
        return None
    values = getattr(args, "ids", None)
    if not values:
        raise PipelineError("specify --ids ID [ID ...] or explicit --all")
    return set(values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path.home() / ".codex" / "backups" / "pbl-wordpress",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("inventory")
    for command in ("format", "plan"):
        subparser = subparsers.add_parser(command)
        selection = subparser.add_mutually_exclusive_group(required=True)
        selection.add_argument("--ids", type=int, nargs="+")
        selection.add_argument("--all", action="store_true")
        if command == "format":
            subparser.add_argument("--apply", action="store_true")
        else:
            subparser.add_argument("--plan", type=Path, required=True)
    approve = subparsers.add_parser("approve")
    approve.add_argument("--plan", type=Path, required=True)
    approve.add_argument("--ids", type=int, nargs="+", required=True)
    schedule = subparsers.add_parser("schedule")
    schedule.add_argument("--plan", type=Path, required=True)
    schedule.add_argument("--apply", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config()
    try:
        if args.command == "inventory":
            return command_inventory(config)
        if args.command == "format":
            return command_format(config, selection_from_args(args), args.apply, args.backup_dir)
        if args.command == "plan":
            return command_plan(config, selection_from_args(args), args.plan)
        if args.command == "approve":
            return command_approve(config, args.plan, set(args.ids))
        if args.command == "schedule":
            return command_schedule_plan(config, args.plan, args.apply, args.backup_dir)
    except (PipelineError, requests.RequestException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
