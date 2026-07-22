#!/usr/bin/env python3
"""Canonical WordPress fixed elements and publication preflight checks for PBL."""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup


FOOTER_RE = re.compile(r"<footer\b[^>]*>.*?</footer>", re.IGNORECASE | re.DOTALL)
JSONLD_SCRIPT_RE = re.compile(
    r'<script\b(?=[^>]*type=["\']application/ld\+json["\'])[^>]*>.*?</script>',
    re.IGNORECASE | re.DOTALL,
)
DIV_RE = re.compile(r"<div\b[^>]*>.*?</div>", re.IGNORECASE | re.DOTALL)
LINE_INVITATION = "公式LINEへのメッセージ送信は24時間可能です。返信は営業時間内です。"
PREVIOUS_LINE_INVITATION = "公式LINEから24時間お問い合わせを受け付けています。"
LEGACY_LINE_INVITATION = "公式LINEから24時間受け付けてます！"
LINE_INVITATION_MARKERS = (
    LINE_INVITATION,
    PREVIOUS_LINE_INVITATION,
    LEGACY_LINE_INVITATION,
)
LINE_INVITATION_TERMS = ("公式LINE", "ご予約", "お問い合わせ", "ご相談")
AUTHOR_LABEL = "この記事の執筆・監修：奥村龍晃（柔道整復師）"
CANONICAL_LINE_TEXT = (
    "公式LINEへのメッセージ送信は24時間可能です。返信は営業時間内です。 "
    "ご予約や当院の一般的なご案内についてお問い合わせいただけます。"
    "診断・治療方針などの医療上の判断は医療機関へご相談ください。"
)
REQUIRED_SELECTORS = {
    "tldr": ".tldr",
    "author": ".wp-image-361",
    "toc": "nav.toc",
    "disclaimer": ".disclaimer",
    "line_button": ".q_button_wrap",
    "footer": "footer",
    "jsonld": 'script[type="application/ld+json"]',
}
CANONICAL_FOOTER = """<footer>
<p style="text-align: center;"><img class="size-full wp-image-629 aligncenter"
    src="https://physical-balance-lab.com/wp/wp-content/uploads/2024/05/ogp.jpg"
    alt="レッドコード整体" width="1200" height="630" /></p>

<p>ーーーーーーーーーーーーーーーーーーーーーーーーーーーー<br />
〒464-0026<br />
愛知県名古屋市千種区井上町117 井上協栄ビル2階<br />
名古屋市営地下鉄東山線「星ヶ丘駅」2番口徒歩2分<br />
愛知県名古屋市で、姿勢や日常動作についてのご相談を受け付ける整体院<br />
フィジカルバランスラボ整体院<br />
ーーーーーーーーーーーーーーーーーーーーーーーーーーーー</p>
</footer>"""


class FixedElementsError(RuntimeError):
    """Raised when fixed elements cannot be normalized safely."""


def fixed_element_counts(html: str) -> dict[str, int]:
    """Return fixed-element counts without changing the supplied HTML."""
    soup = BeautifulSoup(html, "html.parser")
    return {name: len(soup.select(selector)) for name, selector in REQUIRED_SELECTORS.items()}


def publication_html_errors(html: str) -> list[str]:
    """Return deterministic preflight errors for publication-bound PBL HTML."""
    errors: list[str] = []
    counts = fixed_element_counts(html)
    for name, count in counts.items():
        if count != 1:
            errors.append(f"{name}: expected 1, found {count}")

    if html.count(AUTHOR_LABEL) != 1:
        errors.append("author_copy: expected canonical author label once")

    soup = BeautifulSoup(html, "html.parser")
    disclaimer = soup.select_one(".disclaimer")
    if disclaimer is not None:
        disclaimer_text = disclaimer.get_text(" ", strip=True)
        if "医療機関" not in disclaimer_text:
            errors.append("disclaimer_copy: medical consultation wording is missing")
        if "2週間以上" in disclaimer_text or "専門家への受診" in disclaimer_text:
            errors.append("disclaimer_copy: legacy consultation threshold remains")

    footer_matches = list(FOOTER_RE.finditer(html))
    if len(footer_matches) == 1:
        footer_match = footer_matches[0]
        if footer_match.group(0) != CANONICAL_FOOTER:
            errors.append("footer: canonical HTML does not match")
    else:
        footer_match = None

    invitation_positions = sorted(
        match.start()
        for marker in LINE_INVITATION_MARKERS
        for match in re.finditer(re.escape(marker), html)
    )
    if len(invitation_positions) > 1:
        errors.append(
            f"line_invitation: expected at most 1 paragraph, found {len(invitation_positions)}"
        )

    disclaimer_position = html.find("disclaimer")
    button_position = html.find("q_button_wrap")
    jsonld_matches = list(JSONLD_SCRIPT_RE.finditer(html))
    jsonld_position = jsonld_matches[0].start() if len(jsonld_matches) == 1 else -1
    footer_position = footer_match.start() if footer_match is not None else -1
    if min(disclaimer_position, button_position, footer_position, jsonld_position) >= 0:
        invitation_blocks = []
        for match in DIV_RE.finditer(html, disclaimer_position, button_position):
            block = BeautifulSoup(match.group(0), "html.parser")
            paragraph = block.find("p")
            paragraph_text = paragraph.get_text(" ", strip=True) if paragraph else ""
            if paragraph_text and any(
                term in paragraph_text for term in LINE_INVITATION_TERMS
            ):
                invitation_blocks.append(match.group(0))
        if len(invitation_blocks) != 1:
            errors.append(
                f"line_invitation_block: expected 1 before the button, found {len(invitation_blocks)}"
            )
        elif (
            BeautifulSoup(invitation_blocks[0], "html.parser").get_text(" ", strip=True)
            != CANONICAL_LINE_TEXT
        ):
            errors.append("line_invitation_copy: canonical invitation text does not match")
        if not disclaimer_position < button_position < footer_position < jsonld_position:
            errors.append(
                "order: expected disclaimer < LINE button < footer < JSON-LD"
            )
        if invitation_positions and invitation_positions[0] > button_position:
            errors.append("line_invitation: invitation must be before the LINE button")

    if len(jsonld_matches) == 1:
        script = BeautifulSoup(jsonld_matches[0].group(0), "html.parser").find("script")
        try:
            json.loads(script.string or script.get_text())
        except (AttributeError, json.JSONDecodeError) as exc:
            errors.append(f"jsonld: invalid JSON ({exc})")
    return errors


def replace_footer(html: str) -> str:
    """Replace exactly one footer while preserving all bytes outside it."""
    matches = list(FOOTER_RE.finditer(html))
    if len(matches) != 1:
        raise FixedElementsError(f"expected one footer, found {len(matches)}")
    match = matches[0]
    before = html[: match.start()]
    after = html[match.end() :]
    if "q_button_wrap" not in before:
        raise FixedElementsError("official LINE button was not found before the footer")
    updated = before + CANONICAL_FOOTER + after
    if updated[: match.start()] != before:
        raise FixedElementsError("content before the footer changed")
    updated_footer = FOOTER_RE.search(updated)
    if updated_footer is None or updated[updated_footer.end() :] != after:
        raise FixedElementsError("content after the footer changed")
    return updated
