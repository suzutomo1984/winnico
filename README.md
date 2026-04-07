# WinNico 🍊

Claude Code for Windows — 画面上に常駐するキャラクターがClaude Codeの承認リクエストを通知してくれるアプリ。

---

### WinNicoとは？

WinNicoは **Windows版 Claude Code** のデスクトップコンパニオンです。

Claude Codeが危険なコマンド（`rm`、`git push`、`curl` 等）を実行しようとしたとき、画面上のキャラクターが承認を求めてきます。ターミナルを見張らなくても、重要な操作だけ確認できます。

**機能：**
- 🍊 画面上に常駐するアニメーションキャラクター
- ✅ 個別に許可 / ❌ 拒否
- ✅✅ **まとめて許可** — `curl` 系など同じ種別のコマンドをセッション中ずっと自動許可
- 🔔 無害なツール（WebSearch等）は通知のみ
- 🖱️ キャラをクリックでClaude Codeウィンドウにフォーカス

### 必要環境

- Windows 10/11
- Python 3.10以上
- [Claude Code](https://claude.ai/code) インストール済み

### インストール

> [!WARNING]
> **WinNicoは必ずClaude Codeより先に起動してください。**
> `winnico_app.py` が起動していない場合、危険なコマンドは**ブロックされます**（黙って許可はされません）。

```bash
# 1. クローン
git clone https://github.com/suzutomo1984/winnico.git
cd winnico

# 2. 依存パッケージをインストール
pip install -r requirements.txt

# 3. Claude Code フックを登録（初回のみ）
python setup_hooks.py

# 4. WinNico を起動（バックグラウンドで起動したままにする）
python winnico_app.py

# 5. 別のターミナルでClaude Codeをbypassモードで起動
claude --permission-mode bypassPermissions
```

> [!IMPORTANT]
> **`--permission-mode bypassPermissions` を必ず付けて起動してください。**
> このフラグなしで起動すると、Claude Code自身の承認UIが先に表示されWinNicoが機能しません。
> bypassモードにすることで、Claude CodeはUIを出さずにWinNicoにすべての承認を委譲します。

### アンインストール

```bash
python setup_hooks.py --remove
```

### 承認が必要なコマンド一覧

`hook_handler.py` の `DANGEROUS_BASH_KEYWORDS` で自由にカスタマイズできます。

### まとめて許可について

調査系タスクなど `curl` が何度も走るシーンでは、**✅✅ curl系は全部許可** ボタンを押せばそのセッション中は同種コマンドを自動で許可します。WinNicoを再起動するとリセットされます。

### キャラクター・ウィンドウ設定の変更

`config.default.yaml` を `config.yaml` にコピーして編集するだけ：

```yaml
# キャラ画像（winnicoフォルダからの相対パス、または絶対パス）
character_image: "my_character.png"

# フォーカス対象ウィンドウのタイトルキーワード（部分一致・大文字小文字無視）
target_window_titles:
  - "Cursor"          # Cursorユーザーはここを変える
  # - "Visual Studio Code"
  # - "Antigravity"

# チャット入力欄のクリック位置（ウィンドウ下端からの距離 px）
chat_input_offset_from_bottom: 60

# マウスカーソルを動かしてクリックする方式（デフォルト: false）
# Electron系エディタ（Cursor, VSCode等）でフォーカスが効かない場合は true にする
use_cursor_pos: false
```

`config.yaml` は `.gitignore` 対象なので個人設定が誤ってpushされません。

---

## For Claude Code

このリポジトリをClone後、Claude Codeに読ませると対話形式でセットアップを進めることができます。

**Claude Codeへの指示:** 以下の手順でユーザーに一問一答しながらセットアップを進めてください。

### Step 1: 依存パッケージの確認・インストール

```bash
pip show PyQt5 pywin32 pyyaml
```

未インストールのものがあれば `pip install -r requirements.txt` を実行する。

### Step 2: フックの登録

既存の `~/.claude/settings.json` の設定は保持されることをユーザーに伝えてから実行する。

```bash
python setup_hooks.py
```

### Step 3: config.yaml の作成（必須）

ユーザーに以下を一問一答で確認してから `config.yaml` を作成する：

1. **使用エディタ・ターミナルは？**
   例: Antigravity / Cursor / Visual Studio Code / Windows Terminal など
   → タイトルバーに表示される文字列を `target_window_titles` に設定する

2. **キャラクター画像はどうする？**
   - デフォルト（付属の `character.png`）をそのまま使う
   - 自分で用意した画像に差し替える（PNG推奨・透過対応）
   → 差し替える場合は画像ファイルのパスを `character_image` に設定する

3. **フォーカス方式は？**
   - `use_cursor_pos: false`（デフォルト・カーソルが動かない）
   - `use_cursor_pos: true`（Cursor/VSCodeなどElectron系でフォーカスが効かない場合）

4. **チャット入力欄の位置はデフォルト（60px）でよいか？**
   ずれる場合は `chat_input_offset_from_bottom` を調整する。

### Step 4: 起動案内

```bash
# ターミナル1: WinNicoを起動したままにする
python winnico_app.py

# ターミナル2: Claude Codeをbypassモードで起動（必須）
claude --permission-mode bypassPermissions
```

---

## License

MIT

## Author

[suzutomo1984](https://github.com/suzutomo1984)
