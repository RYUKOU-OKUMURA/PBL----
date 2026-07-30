#!/usr/bin/env python3
"""Safely apply CTR-focused edits to published WordPress posts 965, 612, 976."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from post_to_wp import load_config  # noqa: E402

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "change_manifest.json"
PLAN_PATH = ROOT / "rollout_plan.json"
STATE_PATH = ROOT / "rollout_state.json"
PREVIEW_DIR = ROOT / "qa_preview"
POST_IDS = (965, 612, 976)

TABLE_965 = """
<div class="wp-block-table"><table><thead><tr><th>装具名</th><th>固定範囲</th><th>特徴</th><th>医師が検討する場面の例</th></tr></thead><tbody>
<tr><td>ミルウォーキー装具（ブレース）</td><td>骨盤〜首</td><td>固定範囲が広く、固定力が高い設計</td><td>医師が強い固定を検討する場合</td></tr>
<tr><td>ボストンブレース</td><td>脇下〜骨盤</td><td>比較的動きやすい</td><td>腰椎の湾曲を中心に管理する場合</td></tr>
<tr><td>シュロス装具</td><td>個別設計</td><td>オーダーメイド</td><td>体の形に合わせた設計が必要な場合</td></tr>
<tr><td>チェネオ装具（プレーリーくん）</td><td>幼児向け</td><td>着けやすさ重視</td><td>小児の側弯症で装具が検討される場合</td></tr>
</tbody></table></div>
<p>※装具の選択はコブ角、成長段階、生活背景などを踏まえ、主治医と相談して決めます。</p>
"""

INTRO_612_OLD = (
    "<p>今回の記事は、慢性的な肩こりや首こりの方に向けて、</p>\r\n"
    "<ul>\r\n\t<li><strong>首の詰まり感を感じる</strong></li>\r\n"
    "\t<li><strong>上を向くと首に痛みを感じる</strong></li>\r\n"
    "</ul>\r\n"
    "<p>などの症状の改善方法をご紹介します！</p>\r\n"
    "<p>改善法の一つに当院でしか受けれない、<br />\r\n"
    "『レッドコード整体』もご紹介しますので、<br />\r\n"
    "ぜひ最後まで読んでください(^^)/</p>"
)

INTRO_612_NEW = (
    "<p>僕のところにも、「首が詰まる感じが続くんですが、頚椎症でしょうか」と相談される方がいます。</p>\r\n"
    "<p>「首が詰まる」「上を向くと首が痛い」と感じるときは、首の骨の変性（頚椎症）などが気になる方も多いと思います。"
    "まず確認したいポイントと、無理のないセルフケアの考え方を整理します。個人差があるため、ここで示す内容はあくまで一般的な目安です。"
    "強い痛みやしびれ、発熱などがある場合は、医療機関への相談を優先してください。</p>\r\n"
    "<p>日常に取り入れやすいストレッチの例も、あわせて触れます(^^)/</p>"
)

SECTIONS_976 = """
<h2>後遺症として報告されやすいこと</h2>
<p>研究や臨床報告では、手術後に背中・腰・肩まわりの痛みや違和感が残る例が報告されています。これらは「後遺症」と検索されることもありますが、痛みの原因は人によって異なり、すべてが手術そのものに直接結びつくわけではありません。</p>
<p>手術部位の組織損傷に伴う痛み、神経系の過敏化、心理社会的な要因など、複数の要素が関わる可能性があります。気になる症状がある場合は、自己判断で原因を決めず、担当医と相談することが大切です。</p>
<h2>術後の痛みはいつまで続く？研究が示す目安</h2>
<p>2007年の研究では、半数以上の方が手術後も痛みを感じており、1年経過後も改善しない例が少なくないと報告されています。ただし、これは調査対象や評価方法によって異なるため、個人の回復期間を断定することはできません。</p>
<p>「いつまで続くのか」が気になる場合は、痛みの強さ・出る場面・日常生活への影響を記録し、定期受診のタイミングで主治医に確認してください。急な悪化や新たなしびれなどがある場合は、早めの受診を検討してください。</p>
"""

RELATED_976_EXTRA = """
<li><a href="https://physical-balance-lab.com/1092/">大人の脊柱側弯症、手術が必要なときって？―分かりやすく解説します</a></li>
<li><a href="https://physical-balance-lab.com/1171/">【側弯症解説シリーズ】第3回：脊柱を支える筋肉の秘密！側弯症で起こる筋肉の拘縮メカニズムと改善法</a></li>
<li><a href="https://physical-balance-lab.com/1191/">【側弯症解説シリーズ】第9回：側弯症を楽にする！専門家推奨のリハビリテーションプログラム</a></li>
<li><a href="https://physical-balance-lab.com/1182/">【側弯症解説シリーズ】第7回：脊柱側弯症で変わる歩き方と背中の筋肉の働き</a></li>
"""


class RolloutError(RuntimeError):
    pass


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def wp_auth(config: dict[str, str]) -> HTTPBasicAuth:
    return HTTPBasicAuth(config["WP_USER"], config["WP_APP_PASSWORD"])


def fetch_post(config: dict[str, str], post_id: int) -> dict[str, Any]:
    response = requests.get(
        f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
        params={"context": "edit"},
        auth=wp_auth(config),
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def load_backup(post_id: int) -> dict[str, Any]:
    path = ROOT / f"backup_{post_id}.json"
    if not path.exists():
        raise RolloutError(f"Missing backup: {path}")
    return read_json(path)


def transform_content(post_id: int, content: str) -> str:
    if post_id == 965:
        marker = (
            "<h2>現代の側弯症装具、その種類と特徴を解説</h2>\r\n"
            "<p>現代の側弯症装具は、大きく分けて4つの種類があります。"
        )
        if marker not in content:
            raise RolloutError("965: insertion marker not found")
        if "wp-block-table" in content:
            return content
        return content.replace(
            marker,
            "<h2>現代の側弯症装具、その種類と特徴を解説</h2>\r\n"
            + TABLE_965
            + "\r\n<p>現代の側弯症装具は、大きく分けて4つの種類があります。",
        )
    if post_id == 612:
        if INTRO_612_OLD not in content:
            raise RolloutError("612: intro marker not found")
        return content.replace(INTRO_612_OLD, INTRO_612_NEW)
    if post_id == 976:
        updated = content
        if "<h2>後遺症として報告されやすいこと</h2>" not in updated:
            updated = updated.replace("<h2>まとめ</h2>", SECTIONS_976 + "\r\n<h2>まとめ</h2>")
        for link_html, label in [
            ('href="https://physical-balance-lab.com/1092/"', "1092"),
            ('href="https://physical-balance-lab.com/1171/"', "1171"),
            ('href="https://physical-balance-lab.com/1182/"', "1182"),
        ]:
            if link_html not in updated:
                updated = updated.replace(
                    "<li><a href=\"https://physical-balance-lab.com/1682/\">",
                    RELATED_976_EXTRA + "\n<li><a href=\"https://physical-balance-lab.com/1682/\">",
                    1,
                )
                break
        return updated
    raise RolloutError(f"Unsupported post_id: {post_id}")


def expected_post(post_id: int, backup: dict[str, Any], manifest: dict[str, Any]) -> dict[str, str]:
    spec = manifest["posts"][str(post_id)]
    title = spec["title"] if spec.get("title") else backup["title"]
    excerpt = spec.get("excerpt") or backup.get("excerpt", "")
    content = transform_content(post_id, backup["content_raw"])
    return {"title": title, "excerpt": excerpt, "content": content}


def assert_matches_baseline(current: dict[str, Any], baseline: dict[str, Any]) -> None:
    post_id = int(current["id"])
    if current["status"] != baseline["status"]:
        raise RolloutError(f"post {post_id}: status changed")
    if current["slug"] != baseline["slug"]:
        raise RolloutError(f"post {post_id}: slug changed")
    if sha256_text(current["content"]["raw"]) != sha256_text(baseline["content_raw"]):
        raise RolloutError(f"post {post_id}: content changed since backup")


def write_qa_preview(post_id: int, expected: dict[str, str]) -> Path:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    path = PREVIEW_DIR / f"{post_id}_qa.md"
    body = (
        f"# Post ID {post_id}\n\n"
        f"## Title\n{expected['title']}\n\n"
        f"## Excerpt\n{expected['excerpt']}\n\n"
        f"## Content (HTML)\n\n"
        f"{expected['content']}\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def command_plan(_config: dict[str, str]) -> None:
    manifest = read_json(MANIFEST_PATH)
    plan: dict[str, Any] = {"posts": {}, "qa_files": {}}
    for post_id in POST_IDS:
        backup = load_backup(post_id)
        expected = expected_post(post_id, backup, manifest)
        plan["posts"][str(post_id)] = {
            "baseline_content_sha256": sha256_text(backup["content_raw"]),
            "expected_content_sha256": sha256_text(expected["content"]),
            "title": expected["title"],
            "excerpt": expected["excerpt"],
            "status": backup["status"],
            "slug": backup["slug"],
        }
        qa_path = write_qa_preview(post_id, expected)
        plan["qa_files"][str(post_id)] = str(qa_path)
        print(f"PLANNED post={post_id} qa={qa_path}")
    write_json(PLAN_PATH, plan)
    print(f"PLAN={PLAN_PATH}")


def rollback_posts(
    config: dict[str, str],
    touched: list[int],
) -> None:
    for post_id in reversed(touched):
        backup = load_backup(post_id)
        response = requests.post(
            f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
            json={
                "title": backup["title"],
                "excerpt": backup.get("excerpt", ""),
                "content": backup["content_raw"],
            },
            auth=wp_auth(config),
            timeout=60,
        )
        response.raise_for_status()
        restored = fetch_post(config, post_id)
        if sha256_text(restored["content"]["raw"]) != sha256_text(backup["content_raw"]):
            raise RolloutError(f"Rollback verification failed for post {post_id}")
        print(f"ROLLED_BACK post={post_id}")


def command_apply(config: dict[str, str]) -> None:
    manifest = read_json(MANIFEST_PATH)
    plan = read_json(PLAN_PATH)
    touched: list[int] = []
    try:
        for post_id in POST_IDS:
            backup = load_backup(post_id)
            current = fetch_post(config, post_id)
            baseline = {
                "status": backup["status"],
                "slug": backup["slug"],
                "content_raw": backup["content_raw"],
            }
            assert_matches_baseline(current, baseline)
            if sha256_text(current["content"]["raw"]) != plan["posts"][str(post_id)]["baseline_content_sha256"]:
                raise RolloutError(f"post {post_id}: baseline hash mismatch with plan")
            expected = expected_post(post_id, backup, manifest)
            response = requests.post(
                f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
                json={
                    "title": expected["title"],
                    "excerpt": expected["excerpt"],
                    "content": expected["content"],
                },
                auth=wp_auth(config),
                timeout=60,
            )
            response.raise_for_status()
            updated = fetch_post(config, post_id)
            if sha256_text(updated["content"]["raw"]) != sha256_text(expected["content"]):
                raise RolloutError(f"post {post_id}: content not applied correctly")
            if updated["title"]["raw"] != expected["title"]:
                raise RolloutError(f"post {post_id}: title not applied correctly")
            touched.append(post_id)
            print(f"UPDATED post={post_id}")
        command_verify(config)
    except Exception:
        if touched:
            rollback_posts(config, touched)
        raise


def command_verify(config: dict[str, str]) -> None:
    manifest = read_json(MANIFEST_PATH)
    for post_id in POST_IDS:
        backup = load_backup(post_id)
        expected = expected_post(post_id, backup, manifest)
        current = fetch_post(config, post_id)
        if current["status"] != backup["status"]:
            raise RolloutError(f"post {post_id}: status changed")
        if current["slug"] != backup["slug"]:
            raise RolloutError(f"post {post_id}: slug changed")
        if sha256_text(current["content"]["raw"]) != sha256_text(expected["content"]):
            raise RolloutError(f"post {post_id}: content mismatch")
        if current["title"]["raw"] != expected["title"]:
            raise RolloutError(f"post {post_id}: title mismatch")
        public = requests.get(current["link"], timeout=45)
        if public.status_code != 200:
            raise RolloutError(f"post {post_id}: public HTTP {public.status_code}")
        print(f"VERIFIED post={post_id} status={current['status']} public=200")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("plan", "apply", "verify"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    try:
        if args.command == "plan":
            command_plan(config)
        elif args.command == "apply":
            command_apply(config)
        else:
            command_verify(config)
    except (RolloutError, requests.RequestException, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
