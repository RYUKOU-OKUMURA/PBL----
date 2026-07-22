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
LINE_INVITATION = "公式LINEから24時間受け付けてます！"
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
愛知、名古屋で姿勢や動作の不調でお悩みの方へ、体の使い方を整える整体<br />
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

    footer_matches = list(FOOTER_RE.finditer(html))
    if len(footer_matches) == 1:
        footer_match = footer_matches[0]
        if footer_match.group(0) != CANONICAL_FOOTER:
            errors.append("footer: canonical HTML does not match")
    else:
        footer_match = None

    invitation_positions = [match.start() for match in re.finditer(re.escape(LINE_INVITATION), html)]
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
