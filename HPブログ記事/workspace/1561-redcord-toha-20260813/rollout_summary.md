# #1561 レッドコード整体とは 情報型リライト（2026-08-13）

公開済み記事の新規URLなしリライト。`post_to_wp.py --update-post-id` は使っていない。

## 対象

- ID: 1561
- 公開URL: https://physical-balance-lab.com/1561/
- 適用後: status=`publish`、date=`2025-09-10T16:29:08`、slug不変、公開URL HTTP 200
- ローカル原稿: `HPブログ記事/投稿前/レッドコード整体とは？赤いロープで体を支える施術の考え方.md`
- バックアップ: `HPブログ記事/workspace/1561-redcord-toha-20260813/backup_1561.json`
- 適用スクリプト: `HPブログ記事/workspace/1561-redcord-toha-20260813/apply_patch.py`

## バックアップ時点の固定要素（現行稿）

- TL;DR: あり（効果断定「約2週間で痛みを抑えつつ…治療システム」）
- 執筆者情報: あり（旧コピー「脊柱側弯症専門」）
- 目次: あり（空の `nav aria-label="目次"` が多数重複）
- 免責 `.disclaimer`: なし
- LINE CTA `.q_button_wrap`: なし（旧案内文のみ）
- 正規フッター: なし（旧院情報・「治療なら」表現）
- JSON-LD: あり（冒頭配置、`痛みなく動ける` / MedicalCondition / possibleTreatment）
- 参考文献: あり（内部資料由来のPMID混在。本文と不一致）
- 抜粋: 空

## タイトル

| | 文言 |
|---|---|
| 旧 | レッドコード整体とは？Neuracの科学と「痛みなく動ける」理由 |
| 新 | レッドコード整体とは？赤いロープで体を支える施術の考え方 |

WordPress title / 原稿タイトル / JSON-LD `headline` は同一。先頭は主クエリ「レッドコード整体とは」。

## 抜粋

| | 文言 |
|---|---|
| 旧 | （空） |
| 新 | レッドコード整体とは、天井の赤いロープで体重の一部を預ける施術です。無重力整体と呼ばれる理由と、初回に確認しながら進める考え方を情報として整理します。 |

## 情報型の役割分担

- ホームページがブランドクエリ（レッドコード整体 / 施術 / 無重力整体）の owner
- ブログ #1561 は「とは」の情報型。予約・料金・適応の受け皿にしない
- 現行サイトに独立した料金スラッグはなし（`/price/` 等は 404）。料金・予約は `/for-newcomers/` と `/contact/` へリンク
- ブランド案内はトップ `https://physical-balance-lab.com/` へ一文で渡す
- ぎっくり腰シリーズは #1667 の1本のみ

## QA判定（固定要素込み・修正後の再実行）

| チェック | 判定 |
|---|---|
| `post_to_wp.py --preflight-only` | OK |
| japanese-blog-style-guard | 重大指摘なし |
| medical-compliance-checker | 公開可 |
| chinese-char-detector | 中国語混入なし |

PMID 34570056 は epub 2021-09-23、print 2024-10-01（J Strength Cond Res 38(10)）。本文・参考文献・JSON-LD の「2024年」は刊行年。

## 適用結果

```
UPDATED post=1561
VERIFIED post=1561 status=publish date=2025-09-10T16:29:08
slug=（不変） public=200
title=headline=レッドコード整体とは？赤いロープで体を支える施術の考え方
```

payload は title / excerpt / content のみ。status / date / slug は変更していない。タグも変更していない。

## ロールバック

失敗時・差し戻し時はバックアップから title / excerpt / content だけ戻す。

```bash
python3 - <<'PY'
import json, os, requests
from pathlib import Path
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

root = Path("HPブログ記事/workspace/1561-redcord-toha-20260813")
load_dotenv(".env")
backup = json.loads((root / "backup_1561.json").read_text(encoding="utf-8"))
url = os.getenv("WP_URL").rstrip("/")
auth = HTTPBasicAuth(os.getenv("WP_USER"), os.getenv("WP_APP_PASSWORD"))
r = requests.post(
    f"{url}/wp-json/wp/v2/posts/1561",
    json={
        "title": backup["title"],
        "excerpt": backup.get("excerpt", ""),
        "content": backup["content_raw"],
    },
    auth=auth,
    timeout=60,
)
r.raise_for_status()
print("rolled back", r.json()["id"])
PY
```

または:

```bash
python3 HPブログ記事/workspace/1561-redcord-toha-20260813/apply_patch.py verify
```

verify が新稿と不一致なら、上記バックアップ POST で戻す。戻したあとに status / date / slug がバックアップと一致することを再取得して確認する。

## コミット

ユーザー依頼があるまでコミットしない。
