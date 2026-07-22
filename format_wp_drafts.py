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
from wp_fixed_elements import (
    FixedElementsError,
    REQUIRED_SELECTORS,
    publication_html_errors,
    replace_footer,
)


JST = timezone(timedelta(hours=9))
RED_STYLE = "color: #ff0000;"
FIXED_SELECTORS = dict(REQUIRED_SELECTORS)
HEADING_RE = re.compile(
    r"<h2\b[^>]*>(?P<title>.*?)</h2>", re.IGNORECASE | re.DOTALL
)
PARAGRAPH_RE = re.compile(
    r"<p(?P<attrs>\s[^>]*)?>(?P<inner>.*?)</p>", re.IGNORECASE | re.DOTALL
)
LIST_ITEM_RE = re.compile(
    r"<li(?P<attrs>\s[^>]*)?>(?P<inner>.*?)</li>", re.IGNORECASE | re.DOTALL
)
JSONLD_SCRIPT_RE = re.compile(
    r'<script\b(?=[^>]*type=["\']application/ld\+json["\'])[^>]*>.*?</script>',
    re.IGNORECASE | re.DOTALL,
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


def api_get_page(
    config: dict[str, str], path: str, **params: Any
) -> tuple[list[dict[str, Any]], int]:
    response = requests.get(
        f"{config['WP_URL']}/wp-json/wp/v2/{path}",
        params=params,
        auth=auth(config),
        timeout=30,
    )
    response.raise_for_status()
    try:
        total_pages = int(response.headers["X-WP-TotalPages"])
    except (KeyError, ValueError) as exc:
        raise PipelineError("WordPress collection response has no valid total-page count") from exc
    payload = response.json()
    if not isinstance(payload, list):
        raise PipelineError("WordPress collection response is not a list")
    return payload, total_pages


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
        batch, total_pages = api_get_page(
            config,
            "posts",
            context="edit",
            status="draft",
            per_page=100,
            page=page,
        )
        posts.extend(batch)
        if page >= total_pages:
            return posts
        page += 1


def fetch_future_posts(config: dict[str, str]) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    page = 1
    while True:
        batch, total_pages = api_get_page(
            config,
            "posts",
            context="edit",
            status="future",
            per_page=100,
            page=page,
        )
        posts.extend(batch)
        if page >= total_pages:
            return posts
        page += 1


def future_queue_snapshot(
    posts: Iterable[dict[str, Any]], excluded_ids: set[int] | None = None
) -> list[dict[str, Any]]:
    excluded_ids = excluded_ids or set()
    return sorted(
        (
            {
                "id": int(post["id"]),
                "date": post.get("date"),
                "date_gmt": post.get("date_gmt"),
            }
            for post in posts
            if int(post["id"]) not in excluded_ids
        ),
        key=lambda item: item["id"],
    )


def raw_title(post: dict[str, Any]) -> str:
    return post.get("title", {}).get("raw") or post.get("title", {}).get("rendered", "")


def raw_content(post: dict[str, Any]) -> str:
    return post.get("content", {}).get("raw") or post.get("content", {}).get("rendered", "")


def raw_excerpt(post: dict[str, Any]) -> str:
    return post.get("excerpt", {}).get("raw") or ""


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


def add_breaks_to_list_inner(inner: str) -> tuple[str, int]:
    if "<p" in inner.lower():
        return inner, 0
    soup = BeautifulSoup(f"<li>{inner}</li>", "html.parser")
    item = soup.find("li")
    if item is None:
        return inner, 0
    added = 0
    for node in list(item.descendants):
        if not isinstance(node, NavigableString) or "。" not in str(node):
            continue
        if node.parent and node.parent.name in {"a", "strong", "span", "em", "script", "style"}:
            continue
        parts = str(node).split("。")
        replacements: list[Any] = []
        for index, part in enumerate(parts):
            if index < len(parts) - 1:
                replacements.append(NavigableString(part + "。"))
                if "".join(parts[index + 1 :]).strip():
                    replacements.extend((soup.new_tag("br"), NavigableString("\n")))
                    added += 1
            elif part:
                replacements.append(NavigableString(part.lstrip()))
        if replacements:
            node.replace_with(*replacements)
    return item.decode_contents(formatter="minimal"), added


def add_body_breaks(html: str) -> tuple[str, int]:
    start, end = body_bounds(html)
    body = html[start:end]
    if BeautifulSoup(body, "html.parser").select("li li"):
        raise PipelineError("nested list items require manual formatting")
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
    def replace_list_item(match: re.Match[str]) -> str:
        nonlocal total
        attrs = match.group("attrs") or ""
        inner, added = add_breaks_to_list_inner(match.group("inner"))
        if added == 0:
            return match.group(0)
        total += added
        return f"<li{attrs}>{inner}</li>"

    formatted = LIST_ITEM_RE.sub(replace_list_item, formatted)
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
    return selected_posts(config, "draft", ids)


def selected_posts(
    config: dict[str, str], status: str, ids: set[int] | None
) -> list[dict[str, Any]]:
    if status == "draft":
        posts = fetch_drafts(config)
    elif status == "future":
        posts = fetch_future_posts(config)
    else:
        raise PipelineError(f"unsupported post status: {status}")
    posts = [post for post in posts if normalized_text(raw_content(post))]
    if ids is not None:
        posts = [post for post in posts if post["id"] in ids]
        missing = ids - {post["id"] for post in posts}
        if missing:
            raise PipelineError(f"{status} post IDs not found: {sorted(missing)}")
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


def command_unschedule(
    config: dict[str, str],
    ids: set[int] | None,
    apply: bool,
    backup_dir: Path,
) -> int:
    """Move selected future posts back to draft without changing their content."""
    posts = selected_posts(config, "future", ids)
    for post in posts:
        print(
            json.dumps(
                {
                    "id": post["id"],
                    "date": post.get("date"),
                    "date_gmt": post.get("date_gmt"),
                    "title": raw_title(post),
                    "content_sha256": content_hash(raw_content(post)),
                },
                ensure_ascii=False,
            )
        )
    if not apply:
        print(f"DRY_RUN=1 UNSCHEDULE_PENDING={len(posts)}")
        return 0

    backup = backup_posts(posts, backup_dir, "before-unschedule")
    print(f"BACKUP={backup}")
    attempted: list[dict[str, Any]] = []
    try:
        for original in posts:
            current = fetch_post(config, original["id"])
            if (
                current.get("status") != "future"
                or current.get("date") != original.get("date")
                or current.get("date_gmt") != original.get("date_gmt")
                or raw_content(current) != raw_content(original)
                or raw_title(current) != raw_title(original)
            ):
                raise PipelineError(
                    f"post {original['id']} changed after unschedule preview"
                )
            attempted.append(original)
            api_post(config, original["id"], {"status": "draft"})
            verified = fetch_post(config, original["id"])
            if (
                verified.get("status") != "draft"
                or raw_content(verified) != raw_content(original)
                or raw_title(verified) != raw_title(original)
            ):
                raise PipelineError(
                    f"post {original['id']} failed unschedule verification"
                )
            print(f"UNSCHEDULED={original['id']} STATUS=draft")

        for original in posts:
            verified = fetch_post(config, original["id"])
            if (
                verified.get("status") != "draft"
                or raw_content(verified) != raw_content(original)
                or raw_title(verified) != raw_title(original)
            ):
                raise PipelineError(
                    f"post {original['id']} failed final unschedule verification"
                )
    except Exception:
        rollback_errors: list[str] = []
        for original in reversed(attempted):
            try:
                api_post(
                    config,
                    original["id"],
                    {
                        "title": raw_title(original),
                        "content": raw_content(original),
                        "status": "future",
                        "date": original.get("date"),
                        "date_gmt": original.get("date_gmt"),
                    },
                )
                restored = fetch_post(config, original["id"])
                if (
                    restored.get("status") != "future"
                    or restored.get("date") != original.get("date")
                    or restored.get("date_gmt") != original.get("date_gmt")
                    or raw_content(restored) != raw_content(original)
                    or raw_title(restored) != raw_title(original)
                ):
                    raise PipelineError("restored post does not match its backup")
            except Exception as rollback_exc:
                rollback_errors.append(f"{original['id']}: {rollback_exc}")
        if rollback_errors:
            raise PipelineError(
                "unschedule failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            )
        raise

    print(f"UNSCHEDULED_TOTAL={len(posts)}")
    return 0


def command_export(
    config: dict[str, str],
    status: str,
    ids: set[int] | None,
    output_dir: Path,
) -> int:
    """Export edit-context HTML and a manifest for read-only final QA."""
    posts = selected_posts(config, status, ids)
    stamp = datetime.now(JST).strftime("%Y%m%d-%H%M%S-%f")
    export_dir = output_dir / f"wp-export-{status}-{stamp}"
    export_dir.mkdir(parents=True, exist_ok=False)
    manifest: list[dict[str, Any]] = []
    for post in posts:
        html = raw_content(post)
        path = export_dir / f"{post['id']}.html"
        path.write_text(html, encoding="utf-8")
        manifest.append(
            {
                "id": post["id"],
                "title": raw_title(post),
                "status": post.get("status"),
                "date": post.get("date"),
                "date_gmt": post.get("date_gmt"),
                "content_sha256": content_hash(html),
                "file": path.name,
            }
        )
        print(f"EXPORTED={post['id']} FILE={path}")
    (export_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"EXPORT_DIR={export_dir} COUNT={len(posts)}")
    return 0


def require_publication_html(html: str, label: str) -> None:
    errors = publication_html_errors(html)
    if errors:
        raise PipelineError(f"{label} failed fixed-element preflight: {'; '.join(errors)}")


def command_fixed_elements(
    config: dict[str, str],
    status: str,
    ids: set[int] | None,
    apply: bool,
    backup_dir: Path,
) -> int:
    posts = selected_posts(config, status, ids)
    previews: list[tuple[dict[str, Any], str]] = []
    invalid: list[int] = []
    for post in posts:
        original = raw_content(post)
        try:
            updated = replace_footer(original)
            errors = publication_html_errors(updated)
        except FixedElementsError as exc:
            updated = original
            errors = [str(exc)]
        changed = updated != original
        if errors:
            invalid.append(post["id"])
        elif changed:
            previews.append((post, updated))
        print(
            json.dumps(
                {
                    "id": post["id"],
                    "date": post.get("date"),
                    "title": raw_title(post),
                    "changed": changed,
                    "errors": errors,
                },
                ensure_ascii=False,
            )
        )
    if invalid:
        raise PipelineError(f"fixed-element preflight failed for post IDs: {invalid}")
    if not apply:
        print(f"DRY_RUN=1 PENDING={len(previews)} TOTAL={len(posts)}")
        return 0
    if not previews:
        print(f"UPDATED=0 TOTAL={len(posts)}")
        return 0

    backup = backup_posts(
        (post for post, _ in previews), backup_dir, f"before-{status}-fixed-elements"
    )
    print(f"BACKUP={backup}")
    attempted: list[dict[str, Any]] = []
    try:
        for original, updated_content in previews:
            current = fetch_post(config, original["id"])
            if (
                current.get("status") != original.get("status")
                or current.get("date") != original.get("date")
                or current.get("date_gmt") != original.get("date_gmt")
                or raw_content(current) != raw_content(original)
            ):
                raise PipelineError(f"post {original['id']} changed after preview")
            attempted.append(original)
            updated = api_post(config, original["id"], {"content": updated_content})
            verified = fetch_post(config, original["id"])
            if raw_content(verified) != updated_content:
                raise PipelineError(f"post {original['id']} failed content verification")
            if (
                verified.get("status") != original.get("status")
                or verified.get("date") != original.get("date")
                or verified.get("date_gmt") != original.get("date_gmt")
            ):
                raise PipelineError(
                    f"post {original['id']} status or schedule changed during update"
                )
            require_publication_html(updated_content, f"post {original['id']}")
            print(f"UPDATED={updated['id']} STATUS={updated['status']} DATE={updated['date']}")
        for original, updated_content in previews:
            verified = fetch_post(config, original["id"])
            if (
                raw_content(verified) != updated_content
                or verified.get("status") != original.get("status")
                or verified.get("date") != original.get("date")
                or verified.get("date_gmt") != original.get("date_gmt")
            ):
                raise PipelineError(f"post {original['id']} failed final batch verification")
    except Exception as update_error:
        rollback_errors: list[str] = []
        for original in reversed(attempted):
            try:
                current = fetch_post(config, original["id"])
                if (
                    raw_content(current) != raw_content(original)
                    or current.get("status") != original.get("status")
                    or current.get("date") != original.get("date")
                    or current.get("date_gmt") != original.get("date_gmt")
                ):
                    api_post(
                        config,
                        original["id"],
                        {
                            "content": raw_content(original),
                            "status": original["status"],
                            "date": original["date"],
                            "date_gmt": original["date_gmt"],
                        },
                    )
                restored = fetch_post(config, original["id"])
                if (
                    raw_content(restored) != raw_content(original)
                    or restored.get("status") != original.get("status")
                    or restored.get("date") != original.get("date")
                    or restored.get("date_gmt") != original.get("date_gmt")
                ):
                    raise PipelineError("rollback verification failed")
                print(f"ROLLED_BACK={original['id']}")
            except Exception as rollback_error:
                rollback_errors.append(f"{original['id']}: {rollback_error}")
        if rollback_errors:
            raise PipelineError(
                f"footer update failed ({update_error}); rollback errors: {rollback_errors}"
            ) from update_error
        raise
    print(f"VERIFIED={len(previews)} STATUS={status}")
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


def parse_jst_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=JST)
    return parsed.astimezone(JST).replace(microsecond=0)


def next_slot_for_future_posts(
    future_posts: Iterable[dict[str, Any]], now: datetime
) -> datetime:
    posts = list(future_posts)
    if posts:
        latest = max(parse_jst_datetime(post["date"]) for post in posts)
        day = latest.date() + timedelta(days=2)
    else:
        day = now.date()
    next_slot = datetime(day.year, day.month, day.day, 13, 0, tzinfo=JST)
    while next_slot <= now:
        next_slot += timedelta(days=2)
    return next_slot


def command_next_slot(config: dict[str, str]) -> int:
    actual_timezone = wordpress_timezone(config)
    if actual_timezone != "Asia/Tokyo":
        raise PipelineError(f"unexpected WordPress timezone: {actual_timezone!r}")
    future_posts = fetch_future_posts(config)
    now = datetime.now(JST).replace(microsecond=0)
    next_slot = next_slot_for_future_posts(future_posts, now)
    print(f"NEXT_SLOT={next_slot.isoformat()}")
    print(f"FUTURE_COUNT={len(future_posts)}")
    if future_posts:
        latest = max(parse_jst_datetime(post["date"]) for post in future_posts)
        print(f"LATEST_FUTURE={latest.isoformat()}")
    return 0


def remove_visible_metadata(html: str) -> tuple[str, str | None]:
    pattern = re.compile(
        r"(?P<meta>\s*<h2\b[^>]*>\s*メタ(?:ディスクリプション|ティスクリフション)\s*</h2>.*?)(?=<script\b[^>]*type=[\"']application/ld\+json[\"'])",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(html)
    if not match:
        return html, None
    soup = BeautifulSoup(match.group("meta"), "html.parser")
    first_paragraph = soup.find("p")
    excerpt = first_paragraph.get_text(" ", strip=True) if first_paragraph else None
    return html[: match.start()] + "\n\n" + html[match.end() :], excerpt


def update_jsonld_dates(html: str, local_date: datetime) -> str:
    matches = list(JSONLD_SCRIPT_RE.finditer(html))
    if len(matches) != 1:
        raise PipelineError(f"expected one raw JSON-LD script, found {len(matches)}")
    match = matches[0]
    script_soup = BeautifulSoup(match.group(0), "html.parser")
    script = script_soup.find("script")
    if script is None:
        raise PipelineError("JSON-LD script could not be parsed")
    data = json.loads(script.string or script.get_text())
    article_nodes = [node for node in data.get("@graph", []) if node.get("@type") == "Article"]
    if len(article_nodes) != 1:
        raise PipelineError(f"expected one Article JSON-LD node, found {len(article_nodes)}")
    iso_date = local_date.isoformat()
    article_nodes[0]["datePublished"] = iso_date
    article_nodes[0]["dateModified"] = iso_date
    replacement = (
        '<script type="application/ld+json">\n'
        + json.dumps(data, ensure_ascii=False, indent=2)
        + "\n</script>"
    )
    updated = html[: match.start()] + replacement + html[match.end() :]
    verified_soup = BeautifulSoup(updated, "html.parser")
    verified_scripts = verified_soup.select(FIXED_SELECTORS["jsonld"])
    if len(verified_scripts) != 1:
        raise PipelineError("JSON-LD script count changed during date update")
    verified_data = json.loads(verified_scripts[0].string or verified_scripts[0].get_text())
    verified_articles = [
        node for node in verified_data.get("@graph", []) if node.get("@type") == "Article"
    ]
    if len(verified_articles) != 1 or any(
        verified_articles[0].get(key) != iso_date for key in ("datePublished", "dateModified")
    ):
        raise PipelineError("JSON-LD dates were not updated exactly")
    return updated


def command_prepare(
    config: dict[str, str],
    ids: set[int] | None,
    first_at: datetime,
    apply: bool,
    backup_dir: Path,
) -> int:
    posts = selected_drafts(config, ids)
    dates = schedule_dates(len(posts), first_at)
    prepared: list[tuple[dict[str, Any], str, str, datetime]] = []
    for post, date in zip(posts, dates):
        original = raw_content(post)
        cleaned, excerpt = remove_visible_metadata(original)
        updated = update_jsonld_dates(cleaned, date)
        validate_jsonld(updated)
        validate_toc(updated)
        if fixed_counts(updated) != fixed_counts(original):
            raise PipelineError(f"post {post['id']} fixed elements changed during prepare")
        expected_excerpt = excerpt if excerpt is not None else raw_excerpt(post)
        prepared.append((post, updated, expected_excerpt, date))
        print(
            f"PREPARE={post['id']} DATE={date.isoformat()} "
            f"METADATA_REMOVED={cleaned != original} EXCERPT={bool(excerpt)}"
        )
    if not apply:
        print(f"DRY_RUN=1 COUNT={len(prepared)}")
        return 0
    backup = backup_posts((post for post, _, _, _ in prepared), backup_dir, "before-prepare")
    print(f"BACKUP={backup}")
    for original, updated_html, expected_excerpt, date in prepared:
        current = fetch_post(config, original["id"])
        if (
            current.get("status") != "draft"
            or raw_content(current) != raw_content(original)
            or raw_excerpt(current) != raw_excerpt(original)
        ):
            raise PipelineError(f"post {original['id']} changed after prepare preview")
        payload: dict[str, Any] = {"content": updated_html, "excerpt": expected_excerpt}
        try:
            api_post(config, original["id"], payload)
            verified = fetch_post(config, original["id"])
            if (
                raw_content(verified) != updated_html
                or raw_excerpt(verified) != expected_excerpt
                or verified.get("status") != "draft"
            ):
                raise PipelineError(f"post {original['id']} prepare verification failed")
        except Exception:
            restore_payload = {
                "content": raw_content(original),
                "excerpt": raw_excerpt(original),
                "status": "draft",
            }
            api_post(config, original["id"], restore_payload)
            restored = fetch_post(config, original["id"])
            if (
                raw_content(restored) != raw_content(original)
                or raw_excerpt(restored) != raw_excerpt(original)
                or restored.get("status") != "draft"
            ):
                raise PipelineError(f"post {original['id']} prepare rollback failed")
            print(f"ROLLED_BACK={original['id']}")
            raise
        print(f"PREPARED={original['id']} DATE={date.isoformat()}")
    return 0


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
    first_at: datetime,
) -> int:
    posts = selected_drafts(config, ids)
    now = datetime.now(JST).replace(microsecond=0)
    future_posts = fetch_future_posts(config)
    if first_at <= now:
        raise PipelineError(
            f"requested first slot is no longer in the future: {first_at.isoformat()}"
        )
    expected_first_at = next_slot_for_future_posts(future_posts, now)
    if first_at != expected_first_at:
        raise PipelineError(
            "requested first slot is stale: "
            f"expected {expected_first_at.isoformat()}, got {first_at.isoformat()}"
        )
    dates = schedule_dates(len(posts), first_at)
    items = []
    for index, (post, date) in enumerate(zip(posts, dates)):
        require_publication_html(raw_content(post), f"post {post['id']}")
        status = "future" if date > now else ("publish" if index == 0 else "future")
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
        "future_queue_snapshot": future_queue_snapshot(future_posts),
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
        require_publication_html(raw_content(post), f"post {post_id}")
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


def replace_jsonld_headline(html: str, old_title: str, new_title: str) -> str:
    """Replace exactly one JSON-LD headline without reformatting the script."""
    old_json = json.dumps(old_title, ensure_ascii=False)
    new_json = json.dumps(new_title, ensure_ascii=False)
    pattern = re.compile(r'("headline"\s*:\s*)' + re.escape(old_json))
    updated, count = pattern.subn(lambda match: match.group(1) + new_json, html)
    if count != 1:
        raise PipelineError(
            f"expected one JSON-LD headline matching {old_title!r}, found {count}"
        )
    validate_jsonld(updated)
    return updated


def article_headlines(html: str) -> list[str]:
    headlines: list[str] = []
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.select(FIXED_SELECTORS["jsonld"]):
        data = json.loads(script.string or script.get_text())
        candidates = data.get("@graph", []) if isinstance(data, dict) else []
        if isinstance(data, dict) and data.get("@type") == "Article":
            candidates = [data]
        for candidate in candidates:
            article_type = candidate.get("@type") if isinstance(candidate, dict) else None
            types = article_type if isinstance(article_type, list) else [article_type]
            if "Article" in types and candidate.get("headline"):
                headlines.append(str(candidate["headline"]))
    return headlines


def load_title_plan(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("version") != 1 or not isinstance(data.get("items"), list):
        raise PipelineError("unsupported title plan")
    required = {"id", "main_query", "old_title", "new_title"}
    for item in data["items"]:
        if not required.issubset(item):
            raise PipelineError(f"invalid title-plan item: {item!r}")
    ids = [item["id"] for item in data["items"]]
    if len(ids) != len(set(ids)):
        raise PipelineError("title plan contains duplicate IDs")
    for item in data["items"]:
        for key in ("main_query", "old_title", "new_title"):
            if not isinstance(item[key], str) or not item[key].strip():
                raise PipelineError(f"title-plan item {item['id']} has an empty {key}")
    main_queries = [item["main_query"] for item in data["items"]]
    if len(main_queries) != len(set(main_queries)):
        raise PipelineError("title plan contains duplicate main queries")
    new_titles = [item["new_title"] for item in data["items"]]
    if len(new_titles) != len(set(new_titles)):
        raise PipelineError("title plan contains duplicate new titles")
    return data


def command_retitle_plan(
    config: dict[str, str],
    publication_plan_path: Path,
    title_plan_path: Path,
    apply: bool,
    backup_dir: Path,
) -> int:
    publication_plan = load_plan(publication_plan_path)
    title_plan = load_title_plan(title_plan_path)
    if publication_plan.get("site_url") != config["WP_URL"]:
        raise PipelineError("publication plan site does not match configured WordPress site")
    actual_timezone = wordpress_timezone(config)
    if actual_timezone != publication_plan.get("timezone") or actual_timezone != "Asia/Tokyo":
        raise PipelineError(f"unexpected WordPress timezone: {actual_timezone!r}")
    publication_items = {item["id"]: item for item in publication_plan["items"]}
    title_items = {item["id"]: item for item in title_plan["items"]}
    if set(publication_items) != set(title_items):
        raise PipelineError("title-plan IDs do not exactly match publication-plan IDs")

    current_by_id: dict[int, dict[str, Any]] = {}
    updated_content: dict[int, str] = {}
    changed_ids: list[int] = []
    for item in title_plan["items"]:
        post_id = item["id"]
        current = fetch_post(config, post_id)
        current_by_id[post_id] = current
        publication_item = publication_items[post_id]
        if not schedule_matches(current, publication_item):
            raise PipelineError(f"post {post_id} no longer matches the publication plan")
        if raw_title(current) != item["old_title"]:
            raise PipelineError(f"post {post_id} title no longer matches the title plan")
        if publication_item.get("title") != item["old_title"]:
            raise PipelineError(f"post {post_id} publication-plan title mismatch")
        headlines = article_headlines(raw_content(current))
        if headlines != [item["old_title"]]:
            raise PipelineError(
                f"post {post_id} expected one matching Article headline, got {headlines!r}"
            )
        if item["old_title"] == item["new_title"]:
            continue
        updated_content[post_id] = replace_jsonld_headline(
            raw_content(current), item["old_title"], item["new_title"]
        )
        changed_ids.append(post_id)
        print(f"RETITLE_PENDING={post_id} TITLE={item['new_title']}")

    if not apply:
        print(f"DRY_RUN=1 RETITLE_PENDING={len(changed_ids)}")
        return 0

    backup = backup_posts(
        (current_by_id[post_id] for post_id in changed_ids),
        backup_dir,
        "before-retitle",
    )
    print(f"BACKUP={backup}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(JST).strftime("%Y%m%d-%H%M%S-%f")
    plan_backup = backup_dir / f"publication-plan-before-retitle-{stamp}.json"
    original_plan_text = publication_plan_path.read_text(encoding="utf-8")
    plan_backup.write_text(original_plan_text, encoding="utf-8")
    print(f"PLAN_BACKUP={plan_backup}")
    applied: list[int] = []
    stored_content: dict[int, str] = {}
    try:
        for post_id in changed_ids:
            item = title_items[post_id]
            before = current_by_id[post_id]
            applied.append(post_id)
            api_post(
                config,
                post_id,
                {"title": item["new_title"], "content": updated_content[post_id]},
            )
            verified = fetch_post(config, post_id)
            if (
                raw_title(verified) != item["new_title"]
                or verified.get("status") != before.get("status")
                or verified.get("date") != before.get("date")
                or verified.get("date_gmt") != before.get("date_gmt")
                or article_headlines(raw_content(verified)) != [item["new_title"]]
                or raw_content(verified) != updated_content[post_id]
            ):
                raise PipelineError(f"post {post_id} failed retitle verification")
            stored_content[post_id] = raw_content(verified)
            print(f"RETITLED={post_id} TITLE={item['new_title']}")
        reviewed_at = datetime.now(JST).isoformat()
        for post_id, publication_item in publication_items.items():
            title_item = title_items[post_id]
            publication_item["title"] = title_item["new_title"]
            publication_item["main_query"] = title_item["main_query"]
            publication_item["title_reviewed_at"] = reviewed_at
            saved_html = stored_content.get(post_id, raw_content(current_by_id[post_id]))
            publication_item["content_sha256"] = content_hash(saved_html)
        save_plan(publication_plan, publication_plan_path)
    except Exception as update_error:
        rollback_errors: list[str] = []
        for post_id in reversed(applied):
            before = current_by_id[post_id]
            try:
                api_post(
                    config,
                    post_id,
                    {
                        "title": raw_title(before),
                        "content": raw_content(before),
                        "status": before["status"],
                        "date": before["date"],
                        "date_gmt": before["date_gmt"],
                    },
                )
                restored = fetch_post(config, post_id)
                if (
                    raw_title(restored) != raw_title(before)
                    or raw_content(restored) != raw_content(before)
                    or restored.get("status") != before.get("status")
                    or restored.get("date") != before.get("date")
                    or restored.get("date_gmt") != before.get("date_gmt")
                ):
                    raise PipelineError("restored post does not match its backup")
                print(f"ROLLED_BACK={post_id}")
            except Exception as rollback_error:
                rollback_errors.append(f"post {post_id}: {rollback_error}")
        try:
            temporary = publication_plan_path.with_name(publication_plan_path.name + ".restore")
            temporary.write_text(original_plan_text, encoding="utf-8")
            temporary.replace(publication_plan_path)
        except Exception as plan_restore_error:
            rollback_errors.append(f"publication plan: {plan_restore_error}")
        if rollback_errors:
            raise PipelineError(
                "retitle failed and rollback was incomplete: " + "; ".join(rollback_errors)
            ) from update_error
        raise

    print(f"PLAN_UPDATED={publication_plan_path} RETITLED={len(changed_ids)}")
    return 0


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
        require_publication_html(raw_content(current), f"post {item['id']}")
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
    if pending and "future_queue_snapshot" not in plan:
        raise PipelineError("publication plan has no future-queue safety snapshot")

    planned_ids = {int(item["id"]) for item in plan["items"]}

    def verify_future_queue_unchanged() -> None:
        current_snapshot = future_queue_snapshot(
            fetch_future_posts(config), excluded_ids=planned_ids
        )
        if current_snapshot != plan.get("future_queue_snapshot"):
            raise PipelineError(
                "future queue changed after plan creation; recompute the slot and rerun QA"
            )

    if pending:
        verify_future_queue_unchanged()
    if not apply:
        print(f"DRY_RUN=1 PENDING={len(pending)}")
        return 0
    backup = backup_posts(current_by_id.values(), backup_dir, "before-schedule")
    print(f"BACKUP={backup}")
    ordered = [item for item in pending if item["status"] == "future"] + [
        item for item in pending if item["status"] == "publish"
    ]
    for item in ordered:
        verify_future_queue_unchanged()
        payload = {
            "status": item["status"],
            "date": item["date"],
            "date_gmt": item["date_gmt"],
        }
        api_post(config, item["id"], payload)
        verified = fetch_post(config, item["id"])
        if not schedule_matches(verified, item):
            raise PipelineError(f"post {item['id']} failed schedule verification")
        require_publication_html(raw_content(verified), f"post {item['id']}")
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
    subparsers.add_parser("next-slot")
    unschedule = subparsers.add_parser("unschedule")
    unschedule_selection = unschedule.add_mutually_exclusive_group(required=True)
    unschedule_selection.add_argument("--ids", type=int, nargs="+")
    unschedule_selection.add_argument("--all", action="store_true")
    unschedule.add_argument("--apply", action="store_true")
    export = subparsers.add_parser("export")
    export.add_argument("--status", choices=("draft", "future"), required=True)
    export_selection = export.add_mutually_exclusive_group(required=True)
    export_selection.add_argument("--ids", type=int, nargs="+")
    export_selection.add_argument("--all", action="store_true")
    export.add_argument("--out-dir", type=Path, required=True)
    fixed_elements = subparsers.add_parser("fixed-elements")
    fixed_elements.add_argument("--status", choices=("draft", "future"), required=True)
    fixed_selection = fixed_elements.add_mutually_exclusive_group(required=True)
    fixed_selection.add_argument("--ids", type=int, nargs="+")
    fixed_selection.add_argument("--all", action="store_true")
    fixed_elements.add_argument("--apply", action="store_true")
    fix_footers = subparsers.add_parser("fix-future-footers", help=argparse.SUPPRESS)
    fix_footers.add_argument("--apply", action="store_true")
    for command in ("format", "prepare", "plan"):
        subparser = subparsers.add_parser(command)
        selection = subparser.add_mutually_exclusive_group(required=True)
        selection.add_argument("--ids", type=int, nargs="+")
        selection.add_argument("--all", action="store_true")
        if command in {"format", "prepare"}:
            subparser.add_argument("--apply", action="store_true")
        if command in {"prepare", "plan"}:
            subparser.add_argument("--first-at", required=True)
        if command == "plan":
            subparser.add_argument("--plan", type=Path, required=True)
    approve = subparsers.add_parser("approve")
    approve.add_argument("--plan", type=Path, required=True)
    approve.add_argument("--ids", type=int, nargs="+", required=True)
    schedule = subparsers.add_parser("schedule")
    schedule.add_argument("--plan", type=Path, required=True)
    schedule.add_argument("--apply", action="store_true")
    retitle = subparsers.add_parser("retitle")
    retitle.add_argument("--plan", type=Path, required=True)
    retitle.add_argument("--titles", type=Path, required=True)
    retitle.add_argument("--apply", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config()
    try:
        if args.command == "inventory":
            return command_inventory(config)
        if args.command == "next-slot":
            return command_next_slot(config)
        if args.command == "unschedule":
            return command_unschedule(
                config,
                selection_from_args(args),
                args.apply,
                args.backup_dir,
            )
        if args.command == "export":
            return command_export(
                config,
                args.status,
                selection_from_args(args),
                args.out_dir,
            )
        if args.command == "fixed-elements":
            return command_fixed_elements(
                config,
                args.status,
                selection_from_args(args),
                args.apply,
                args.backup_dir,
            )
        if args.command == "fix-future-footers":
            print(
                "WARNING: fix-future-footers is deprecated; use "
                "fixed-elements --status future --all",
                file=sys.stderr,
            )
            return command_fixed_elements(config, "future", None, args.apply, args.backup_dir)
        if args.command == "format":
            return command_format(config, selection_from_args(args), args.apply, args.backup_dir)
        if args.command == "prepare":
            return command_prepare(
                config,
                selection_from_args(args),
                parse_jst_datetime(args.first_at),
                args.apply,
                args.backup_dir,
            )
        if args.command == "plan":
            return command_plan(
                config,
                selection_from_args(args),
                args.plan,
                parse_jst_datetime(args.first_at),
            )
        if args.command == "approve":
            return command_approve(config, args.plan, set(args.ids))
        if args.command == "schedule":
            return command_schedule_plan(config, args.plan, args.apply, args.backup_dir)
        if args.command == "retitle":
            return command_retitle_plan(
                config,
                args.plan,
                args.titles,
                args.apply,
                args.backup_dir,
            )
    except (PipelineError, requests.RequestException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
