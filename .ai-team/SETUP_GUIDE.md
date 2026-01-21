# AI組織環境構築ガイド

tmuxとClaude Codeを使ったマルチエージェントAI組織の構築手順

---

## 目次

1. [システム概要](#システム概要)
2. [前準備](#前準備)
3. [環境構築](#環境構築)
4. [AIエージェントの起動](#aiエージェントの起動)
5. [使い方](#使い方)
6. [トラブルシューティング](#トラブルシューティング)
7. [他プロジェクトへの移植](#他プロジェクトへの移植)

---

## システム概要

### AI組織の構成

```
┌─────────────────────────────────────────────────────┐
│                   Human User                         │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   PRESIDENT Session   │ (紫色)
        │   プロジェクト統括責任者  │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │    boss1              │ (赤色)
        │    チームリーダー       │
        └───┬───────┬───────┬───┘
        │       │       │
    ┌───▼───┐ ┌──▼───┐ ┌─▼─────┐
    │worker1│ │worker2│ │worker3│ (青色)
    │実行担当A│ │実行担当B│ │実行担当C│
    └───────┘ └───────┘ └───────┘
```

### 特徴

- **並列処理**: 4つのAIが同時に作業可能
- **役割分担**: 社長、マネージャー、実行者それぞれ専門的に作業
- **tmuxベース**: ターミナル上で全エージェントを同時監視

---

## 前準備

### 1. tmuxのインストール

tmuxはターミナルを分割して複数の画面を同時に見られるツールです。

**Macの場合:**
```bash
# Homebrewがない場合は先にインストール
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# tmuxをインストール
brew install tmux
```

**Ubuntuの場合:**
```bash
sudo apt update
sudo apt install tmux
```

### 2. tmuxのマウス操作設定（推奨）

tmuxをマウスで操作できるように設定します。

**1. 設定ファイルを作成/編集:**

```bash
# ファイルがなければ作成
touch ~/.tmux.conf

# エディタで開く
nano ~/.tmux.conf
# または
code ~/.tmux.conf
```

**2. 以下の設定を追加:**

```conf
# マウス操作を有効にする
set-option -g mouse on

# ダブルクリックでタイルレイアウトに変更
bind -n DoubleClick1Pane select-layout tiled
```

**3. 設定を反映:**

```bash
# 設定をリロード
tmux source-file ~/.tmux.conf
```

**これでできること:**
- マウスクリックでAIの画面を選択
- スクロールで過去のログを確認
- ドラッグで画面サイズを調整
- ダブルクリックで画面を整理

### 3. Node.jsのインストール

Claude Code CLIの前提条件として必要です。

https://nodejs.org/ja から最新LTS版をダウンロードしてインストールしてください。

**インストール確認:**
```bash
node --version
npm --version
```

### 4. Claude Code CLIのインストール

```bash
npm install -g @anthropic-ai/claude-code
```

**インストール確認:**
```bash
claude --version
```

---

## 環境構築

### 方法1: Gitクローン（初めての場合）

```bash
# リポジトリをクローン
git clone https://github.com/Akira-Papa/Claude-Code-Communication.git
cd Claude-Code-Communication

# 実行権限を付与
chmod +x setup.sh agent-send.sh launch-agents.sh

# 環境構築スクリプト実行
./setup.sh
```

### 方法2: 既存プロジェクトに導入する場合

```bash
# 既存のプロジェクトディレクトリに移動
cd /path/to/your/project

# このシステムからエクスポートスクリプトを実行
/path/to/Claude-Code-Communication/export-to-project.sh . my-project

# 生成された.ai-teamディレクトリ内でセットアップ
.ai-team/setup.sh
```

### setup.shが実行すること

1. 既存のtmuxセッションをクリーンアップ
2. **presidentセッション**を作成（1ペイン）
3. **multiagentセッション**を作成（4ペイン分割）
4. 各ペインに色付きプロンプトを設定

**セッション構成:**
- `president`: 紫色プロンプト
- `multiagent:0.0` (boss1): 赤色プロンプト
- `multiagent:0.1` (worker1): 青色プロンプト
- `multiagent:0.2` (worker2): 青色プロンプト
- `multiagent:0.3` (worker3): 青色プロンプト

---

## AIエージェントの起動

### Step 1: PRESIDENT（社長）を起動

```bash
# presidentセッションにアタッチ
tmux attach-session -t president

# Claude Codeを起動
claude --dangerously-skip-permissions
```

**初回のみ認証が必要です。**
- 表示されるURLをブラウザで開く
- 認証を完了させる
- 「Claude is ready!」と出たら成功

**デタッチ（画面から抜ける）:**
```
Ctrl+B → D
```

### Step 2: 部下たち（boss1 + workers）を一括起動

**方法A: 起動スクリプトを使用**

```bash
./launch-agents.sh
```

**方法B: 手動で一括起動**

```bash
# 各ペインにClaude Code起動コマンドを送信
for i in {0..3}; do
  tmux send-keys -t multiagent:0.$i 'claude --dangerously-skip-permissions' C-m
done
```

**方法C: 個別に起動**

```bash
# multiagentセッションにアタッチ
tmux attach-session -t multiagent

# 各ペインで順番に実行（ペインを移動しながら）
claude --dangerously-skip-permissions
```

### Step 3: 起動確認

```bash
# セッション一覧を表示
tmux list-sessions
```

以下の2つのセッションが表示されていれば成功です：
- `president`
- `multiagent`

---

## 使い方

### 基本的な指示の流れ

```
Human User → PRESIDENT → boss1 → worker1,2,3 → boss1 → PRESIDENT → Human User
```

### PRESIDENTへの指示

**方法1: presidentセッションに直接入力**

```bash
tmux attach-session -t president
```

```
あなたはpresidentです。指示書(instructions/president.md)に従って、
おしゃれな充実したIT企業のホームページをhtml,css,jsで作成してください。
```

**方法2: agent-send.shを使用**

```bash
./agent-send.sh president "あなたはpresidentです。プロジェクトを開始してください"
```

### boss1への指示

```bash
./agent-send.sh boss1 "あなたはboss1です。

【タスク】TODOアプリの開発
【納期】今日中
【成果物】
- index.html
- style.css
- app.js

【機能要件】
- タスクの追加
- タスクの完了/未完了の切り替え
- タスクの削除
- ローカルストレージでのデータ保存

30分ごとに進捗報告してください。"
```

### Workerへの指示

```bash
./agent-send.sh worker1 "HTML/CSSでUIを作成してください"
./agent-send.sh worker2 "JavaScriptでロジックを実装してください"
./agent-send.sh worker3 "テストコードを作成してください"
```

### エージェント一覧の確認

```bash
./agent-send.sh --list
```

```
📋 利用可能なエージェント:
==========================
  president → president:0     (プロジェクト統括責任者)
  boss1     → multiagent:0.0  (チームリーダー)
  worker1   → multiagent:0.1  (実行担当者A)
  worker2   → multiagent:0.2  (実行担当者B)
  worker3   → multiagent:0.3  (実行担当者C)
```

### 進捗確認

```bash
./project-status.sh
```

---

## トラブルシューティング

### Q: 「tmux: command not found」と出る

**A:** tmuxがインストールされていません。

```bash
# Mac
brew install tmux

# Ubuntu
sudo apt install tmux
```

### Q: 「permission denied」エラーが出る

**A:** スクリプトに実行権限を付けてください。

```bash
chmod +x setup.sh agent-send.sh launch-agents.sh
```

### Q: セッションが見つからない

**A:** セッションを確認して、なければ再作成してください。

```bash
# セッション確認
tmux list-sessions

# 再作成
./setup.sh
```

### Q: メッセージが届かない

**A:** ログを確認してください。

```bash
# 送信ログを確認
tail -f logs/send_log.txt

# リアルタイムで監視
tail -f logs/send_log.txt
```

### Q: 最初からやり直したい

**A:** 全部リセットしてください。

```bash
# 全tmuxセッション終了
tmux kill-server

# 一時ファイル削除
rm -rf ./tmp/*

# 再セットアップ
./setup.sh
```

### Q: Claude Codeが起動しない

**A:** 以下を確認してください。

1. Claude Code CLIがインストールされているか
   ```bash
   claude --version
   ```

2. 認証が完了しているか（初回のみブラウザ認証が必要）

### Q: プロンプトの色がおかしい

**A:** セッションを再作成してください。

```bash
tmux kill-session -t president
tmux kill-session -t multiagent
./setup.sh
```

---

## 他プロジェクトへの移植

このシステムを他のプロジェクトディレクトリに導入するには、エクスポートスクリプトを使用します。

### エクスポート手順

```bash
# 基本形式
./export-to-project.sh <ターゲットディレクトリ> [プロジェクト名]

# 例
./export-to-project.sh ~/projects/my-blog
./export-to-project.sh ~/projects/web-dev my-web-team
```

### 生成されるファイル

```
ターゲットディレクトリ/
├── .ai-team/              # AIチーム環境
│   ├── setup.sh          # 環境セットアップ
│   ├── launch-agents.sh  # Claude起動
│   ├── agent-send.sh     # 指示送信
│   ├── project-status.sh # 進捗確認
│   ├── instructions/     # 指示書
│   ├── logs/             # 通信ログ
│   └── tmp/              # 一時ファイル
└── AI_TEAM_README.md     # AIチーム用README
```

### プロジェクトでの使用

```bash
cd /path/to/project

# 環境セットアップ
.ai-team/setup.sh

# Claude起動
.ai-team/launch-agents.sh

# 指示送信
.ai-team/agent-send.sh president "プロジェクトを開始してください"
```

---

## tmux基本操作

### セッション操作

| 操作 | コマンド |
|------|---------|
| セッション一覧 | `tmux list-sessions` または `tmux ls` |
| セッションにアタッチ | `tmux attach-session -t 名前` または `tmux a -t 名前` |
| セッションをデタッチ | `Ctrl+B` → `D` |
| セッション終了 | `tmux kill-session -t 名前` |
| 全セッション終了 | `tmux kill-server` |

### ペイン操作

| 操作 | コマンド |
|------|---------|
| ペイン移動 | `Ctrl+B` → `矢印キー` または マウスクリック |
| ペインサイズ変更 | `Ctrl+B` → `Ctrl+矢印キー` または マウスドラッグ |
| ペインを入れ替え | `Ctrl+B` → `o` |
| ペインをZoom | `Ctrl+B` → `z` （再度`z`で戻る） |

### ウィンドウ操作

| 操作 | コマンド |
|------|---------|
| 新規ウィンドウ | `Ctrl+B` → `c` |
| ウィンドウ切り替え | `Ctrl+B` → `数字` |
| ウィンドウ一覧 | `Ctrl+B` → `w` |

---

## 参考リンク

- [Claude Code公式ドキュメント](https://docs.anthropic.com/en/docs/claude-code/overview)
- [GitHub: Claude-Code-Communication](https://github.com/Akira-Papa/Claude-Code-Communication)
- [Qiita: tmuxでClaude CodeのMaxプランでAI組織を動かし放題](https://qiita.com/akira_papa_AI/items/9f6c6605e925a88b9ac5)

---

## ライセンス

このプロジェクトは、コミュニティによって開発・共有されています。

---

Happy Coding with AI Team! 🚀
