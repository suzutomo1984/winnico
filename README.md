# WinNico 🍊

**Claude Code for Windows** — A desktop companion that sits on your screen and handles tool approval requests from Claude Code.

[日本語](#日本語) | [English](#english)

---

## English

### What is WinNico?

WinNico is a small always-on-top companion window for **Claude Code on Windows**.

When Claude Code wants to run a potentially dangerous command (like `rm`, `git push`, `curl`, etc.), WinNico pops up and asks for your approval — so you stay in control without having to babysit the terminal.

**Features:**
- 🍊 Animated character lives on your screen
- ✅ Approve / ❌ Deny individual tool requests
- ✅✅ **Bulk approve** — approve all future `curl` requests (or any keyword type) for the rest of the session
- 🔔 Notifications for non-dangerous tools (WebSearch, WebFetch)
- 🖱️ Click the character to focus Claude Code's window
- ⌨️ Double-tap `Ctrl` hotkey to focus Claude Code's window
- 🔧 One-command setup

### Requirements

- Windows 10/11
- Python 3.10+
- [Claude Code](https://claude.ai/code) installed

### Installation

```bash
# 1. Clone this repository
git clone https://github.com/suzutomo1984/winnico.git
cd winnico

# 2. Install dependencies
pip install -r requirements.txt

# 3. Register Claude Code hooks (run once)
python setup_hooks.py

# 4. Start WinNico
python winnico_app.py
```

That's it! WinNico will now intercept Claude Code's tool requests.

### Uninstall

```bash
# Remove hooks from Claude Code settings
python setup_hooks.py --remove
```

### Which commands require approval?

By default, WinNico asks for approval on these Bash commands:

| Command | Reason |
|---------|--------|
| `rm` / `rmdir` | File deletion |
| `git push` | Remote push |
| `git reset` | History rewrite |
| `git clean` | Untracked file deletion |
| `pip install/uninstall` | Package changes |
| `npm install/uninstall` | Package changes |
| `curl` / `wget` | External downloads |
| `powershell` | PowerShell execution |
| `shutdown` / `reboot` | System commands |
| `format` / `mkfs` | Disk operations |
| SQL: `drop` / `delete` / `truncate` | Database operations |

All other commands (Read, Grep, Glob, Edit, Write, etc.) pass through silently.

To customize, edit `DANGEROUS_BASH_KEYWORDS` in `hook_handler.py`.

### Bulk Approve

During a session with lots of similar requests (e.g., Claude running multiple `curl` commands), click **✅✅ Approve all `curl` requests** to auto-approve that command type for the rest of the session.

The auto-approve list resets when you restart WinNico.

### Customizing the Character

Replace `character.png` with any 80×80 PNG (transparent background recommended).

---

## 日本語

### WinNicoとは？

WinNicoは **Windows版 Claude Code** のデスクトップコンパニオンです。

Claude Codeが危険なコマンド（`rm`、`git push`、`curl` 等）を実行しようとしたとき、画面上のキャラクターが承認を求めてきます。ターミナルを見張らなくても、重要な操作だけ確認できます。

**機能：**
- 🍊 画面上に常駐するアニメーションキャラクター
- ✅ 個別に許可 / ❌ 拒否
- ✅✅ **まとめて許可** — `curl` 系など同じ種別のコマンドをセッション中ずっと自動許可
- 🔔 無害なツール（WebSearch等）は通知のみ
- 🖱️ キャラをクリックでClaude Codeウィンドウにフォーカス
- ⌨️ `Ctrl` 2回押しでClaude Codeにフォーカス
- 🔧 セットアップは1コマンド

### 必要環境

- Windows 10/11
- Python 3.10以上
- [Claude Code](https://claude.ai/code) インストール済み

### インストール

```bash
# 1. クローン
git clone https://github.com/suzutomo1984/winnico.git
cd winnico

# 2. 依存パッケージをインストール
pip install -r requirements.txt

# 3. Claude Code フックを登録（初回のみ）
python setup_hooks.py

# 4. WinNico を起動
python winnico_app.py
```

以降はClaude Codeを使うたびに、WinNicoが承認をインターセプトします。

### アンインストール

```bash
python setup_hooks.py --remove
```

### 承認が必要なコマンド一覧

`hook_handler.py` の `DANGEROUS_BASH_KEYWORDS` で自由にカスタマイズできます。

### まとめて許可について

調査系タスクなど `curl` が何度も走るシーンでは、**✅✅ curl系は全部許可** ボタンを押せばそのセッション中は同種コマンドを自動で許可します。WinNicoを再起動するとリセットされます。

### キャラクター変更

`character.png`（推奨: 80×80px・透過PNG）を差し替えるだけです。

---

## License

MIT

## Author

[suzutomo1984](https://github.com/suzutomo1984)
