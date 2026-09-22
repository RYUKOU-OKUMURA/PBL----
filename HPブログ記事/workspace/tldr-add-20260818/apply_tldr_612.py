#!/usr/bin/env python3
"""post 612 の本文冒頭にサイト標準TL;DRを挿入するスクリプト。

対象: 首の詰まり・上を向くと痛い｜確認したいポイントと受診の目安
      https://physical-balance-lab.com/612/

挿入ルール:
  content.raw の最先頭（既存の最初の要素＝プロフィール画像 <p><img ...wp-image-361...></p> の直前）に
  TL;DRブロック <p class="tldr">…</p> を挿入する。
  新記事（post 2079 / 1823）の標準構造「TL;DR → 執筆者情報 → 目次 → 本文」と同じ順序にするため。
  既存本文は一切変更しない。title / excerpt / status は更新しない（content のみ）。

使い方:
  python3 apply_tldr_612.py            # dry-run（デフォルト）: WPへ書き込まない
  python3 apply_tldr_612.py --apply    # 本番適用: WP REST API で content を更新
"""

from __future__ import annotations

import argparse
import os
import re
import sys

import requests
from dotenv import load_dotenv

POST_ID = 612

# TL;DR本文: 113字（規定 80〜120字・1文完結・数字1つ以上）。
# 「1回30秒」は本文の頚長筋ストレッチ記述（約30秒キープ）に準拠。
# 効果断定・改善保証を避けた表現（薬機法・医療広告ガイドライン配慮）。
# 2026-08-18 QA(style-guard): 「考えられます。→考えられるため、」に修正し1文完結化。
TLDR_HTML = (
    '<p class="tldr">「首が詰まる」「上を向くと痛い」は、長時間同じ姿勢で首前側の筋肉'
    "（頚長筋など）の硬さが考えられるため、痛みの出る動作と症状を記録し、優しいストレッチを"
    "1回30秒試して、強い痛み・しびれ・発熱は医療機関への相談を優先しましょう。</p>"
)

# 挿入位置: content.raw の先頭（最初の <p> の直前）。
# 612はTL;DRなしでプロフィール画像から始まるため、最先頭挿入で新記事標準の構造になる。
# 冒頭にすでに tldr がある場合は二重挿入を防ぎ、処理を中断する。


def load_config() -> dict[str, str]:
    load_dotenv()
    config = {
        "WP_URL": os.environ.get("WP_URL", ""),
        "WP_USER": os.environ.get("WP_USER", ""),
        "WP_APP_PASSWORD": os.environ.get("WP_APP_PASSWORD", ""),
    }
    missing = [k for k, v in config.items() if not v]
    if missing:
        sys.exit(f"エラー: .env に必要な変数がありません: {', '.join(missing)}")
    return config


def fetch_post(config: dict[str, str]) -> dict:
    base = config["WP_URL"].rstrip("/") + "/wp-json/wp/v2"
    resp = requests.get(
        f"{base}/posts/{POST_ID}",
        auth=(config["WP_USER"], config["WP_APP_PASSWORD"]),
        params={"context": "edit"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def build_new_content(content_raw: str) -> str:
    # 改行コードは既存本文に合わせ CRLF
    if "class=\"tldr\"" in content_raw:
        sys.exit("エラー: すでにTL;DRが存在します。二重挿入を防ぐため処理を中止します。")
    return TLDR_HTML + "\r\n" + content_raw


def apply_update(config: dict[str, str], new_content: str) -> dict:
    base = config["WP_URL"].rstrip("/") + "/wp-json/wp/v2"
    resp = requests.post(
        f"{base}/posts/{POST_ID}",
        auth=(config["WP_USER"], config["WP_APP_PASSWORD"]),
        json={"content": new_content},  # content のみ。title/excerpt/status は送らない
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def show_dry_run(old: str, new: str) -> None:
    print("=" * 60)
    print(f"[dry-run] post {POST_ID} へのTL;DR挿入プレビュー（WPには書き込みません）")
    print("=" * 60)

    m = re.search(r"class=\"tldr\"", new)
    insert_pos = m.start() - len("<p ")  # 挿入ブロックの開始位置（概算）
    block_start = new.find(TLDR_HTML)
    block_end = block_start + len(TLDR_HTML)

    print("\n--- 挿入ブロック全文 ---")
    print(TLDR_HTML)

    print("\n--- 挿入位置: 前200字（既存本文の先頭側） ---")
    print(repr(new[block_start - 200 : block_start]) if block_start >= 200 else repr(new[:block_start]))

    print("\n--- 挿入位置: 後200字（既存本文側） ---")
    print(repr(new[block_end : block_end + 200]))

    print("\n--- 文字数 ---")
    plain = re.sub(r"<[^>]+>", "", TLDR_HTML)
    print(f"TL;DR本文（タグ除去）: {len(plain)} 字（規定: 80〜120字）")
    print(f"content.raw: {len(old)} 字 → {len(new)} 字（差分 +{len(new) - len(old)} 字）")

    print("\n--- 検証 ---")
    ok_head = new.startswith(TLDR_HTML)
    ok_unchanged = old in new[len(TLDR_HTML) + 2 :]
    print(f"TL;DRがcontent先頭に配置されている: {ok_head}")
    print(f"既存本文が変更なく保持されている: {ok_unchanged}")
    if ok_head and ok_unchanged:
        print("\n=> 挿入位置・保持確認OK。本番適用は --apply を指定してください。")
    else:
        print("\n=> 検証NG。適用しないでください。")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="post 612 にTL;DRを挿入")
    parser.add_argument("--apply", action="store_true", help="WordPressへ本番適用（contentのみ更新）")
    args = parser.parse_args()

    config = load_config()
    post = fetch_post(config)
    old = post["content"]["raw"]
    new = build_new_content(old)

    if not args.apply:
        show_dry_run(old, new)
        return

    result = apply_update(config, new)
    link = result.get("link", "")
    print(f"[apply] post {POST_ID} のcontentを更新しました: {link}")
    # 更新後の再取得で検証
    verify = fetch_post(config)
    ok = verify["content"]["raw"].startswith(TLDR_HTML)
    print(f"更新後のcontent先頭がTL;DRか: {ok}")


if __name__ == "__main__":
    main()
