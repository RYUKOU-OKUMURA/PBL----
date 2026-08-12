# 抜粋パッチ #1182（2026-08-13）

公開記事1本の抜粋のみ更新。タイトル・本文・公開日時・スラッグ・status は不変。

## 対象
| ID | 変更 |
|----|------|
| 1182 | 抜粋のみ。先頭を「側弯症の歩き方」にし、肩・骨盤・股関節の変化と受診目安を記載。本文・JSON-LDは未改修 |

## 抜粋
- 旧: （空）
- 新: 側弯症の歩き方では、肩・骨盤・股関節の動きが変わりやすいことがあります。研究で報告された範囲で個人差があり、痛みやしびれが強い場合は医療機関への受診を先に検討してください。（86字）

## 不変確認
- status: `publish`
- date: `2025-04-18T17:43:26`
- title: 【側弯症解説シリーズ】第7回：脊柱側弯症で変わる歩き方と背中の筋肉の働き〜気づかない身体の変化と簡単改善法〜
- 本文SHA256: `4fecd6fd6fedd68906de49a9ebd7e6060a414367d859bdd47d429b711d522b88`（バックアップと一致）
- 公開URL: https://physical-balance-lab.com/1182/ → HTTP 200

## QA
- medical-compliance-checker: 公開可（抜粋のみ。治る・取り戻せる・必ず改善なし）
- chinese-char-detector: 混入なし（「弯」は日本語の医学用語として許容）
- japanese-blog-style-guard: 旧本文の全面リライトではないため未実施

## 実行
```bash
python3 HPブログ記事/workspace/1182-excerpt-20260813/apply_patch.py backup
python3 HPブログ記事/workspace/1182-excerpt-20260813/apply_patch.py plan
python3 HPブログ記事/workspace/1182-excerpt-20260813/apply_patch.py apply
python3 HPブログ記事/workspace/1182-excerpt-20260813/apply_patch.py verify
```

payload は `title` / `excerpt` / `content` のみ。`status` と `date` は送っていない。

## ロールバック
`backup_1182.json` の title / excerpt / content を同じスクリプトの rollback 経路、または REST で復元する。

```bash
python3 - <<'PY'
import json, os, requests
from pathlib import Path
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
load_dotenv()
backup = json.loads(Path("HPブログ記事/workspace/1182-excerpt-20260813/backup_1182.json").read_text())
r = requests.post(
    f"{os.getenv('WP_URL').rstrip('/')}/wp-json/wp/v2/posts/1182",
    json={"title": backup["title"], "excerpt": backup.get("excerpt", ""), "content": backup["content_raw"]},
    auth=HTTPBasicAuth(os.getenv("WP_USER"), os.getenv("WP_APP_PASSWORD")),
    timeout=60,
)
r.raise_for_status()
print("rolled back", r.json()["id"])
PY
```
