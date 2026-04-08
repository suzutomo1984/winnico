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

### Step 1: Pythonバージョンの確認

```bash
python --version
```

Python 3.10以上であることを確認する。

### Step 2: 依存パッケージの確認・インストール

> **重要:** 仮想環境（venv, conda等）がアクティブな場合は **必ず `deactivate`** してから実行する。  
> `setup_hooks.py` はシステムのPythonパスを `settings.json` に書き込む。仮想環境のPythonパスが書き込まれると、venv削除後にフックが壊れる。

```bash
pip show PyQt5 pywin32 pyyaml
```

未インストールのものがあれば実行する:

```bash
pip install -r requirements.txt
```

失敗した場合:
- PyQt5が失敗する場合: `pip install PyQt5-Qt5 PyQt5-sip PyQt5` を試す
- pywin32が失敗する場合: [pywin32 Releases](https://github.com/mhammond/pywin32/releases) から手動でインストールする

### Step 3: フックの登録

既存の `~/.claude/settings.json` の設定は保持される（バックアップも自動作成される）ことをユーザーに伝えてから実行する。

```bash
python setup_hooks.py
```

### Step 4: config.yaml の作成（必須）

ユーザーに以下を一問一答で確認してから `config.yaml` を作成する：

1. **使用エディタ・ターミナルのタイトルバーに何と表示されているか？**
   ウィンドウ上部のバーを見て、そこに書いてある文字列をそのまま教えてもらう。  
   例: `Antigravity` / `Cursor` / `Visual Studio Code` / `Windows PowerShell` など  
   → その文字列を `target_window_titles` に設定する  
   ⚠️ `"Claude"` は避ける（ブラウザでClaude.aiを開いているタブにも一致するため）

2. **キャラクター画像はどうする？**
   - デフォルト（付属の `character.png`）をそのまま使う → 設定変更不要
   - 好きな画像に差し替えたい → PNG推奨・透過対応。画像ファイルのパスを `character_image` に設定する

3. **フォーカス方式は？**（Cursor/VSCodeを使っている場合は必ず確認）
   - `use_cursor_pos: false`（デフォルト・カーソルが動かない）
   - `use_cursor_pos: true`（Cursor/VSCodeなどElectron系でフォーカスが効かない場合）

4. **チャット入力欄の位置はデフォルト（60px）でよいか？**
   ずれる場合は `chat_input_offset_from_bottom` を調整する。

### Step 5: 起動と動作確認

**必ずWinNicoを先に起動してから、Claude Codeを起動すること。順番が逆になるとコマンドがブロックされる。**

```bash
# ターミナル1: WinNicoを起動したままにする
python winnico_app.py
```

起動時に `[WinNico self-check] ✅ 環境チェック OK` が表示されることを確認する。  
❌ や ⚠️ が出た場合はメッセージに従って問題を解決してから進む。

```bash
# ターミナル2: Claude Codeをbypassモードで起動（必須）
claude --permission-mode bypassPermissions
```

**`--permission-mode bypassPermissions` を忘れると、Claude Code自身の承認UIが表示されWinNicoは機能しない。**

### Step 6: 動作確認

Claude Codeのチャットで以下を実行し、WinNicoが反応することを確認する：

```
curl --version を実行してみてください
```

WinNicoのキャラクターが承認ダイアログを表示したらセットアップ完了。  
反応しない場合は下記 Troubleshooting を参照。

---

## Troubleshooting

| 症状 | 原因 | 対処 |
|---|---|---|
| `pip install PyQt5` が失敗する | Python 3.13以降でwheelが提供されていない場合がある | `pip install PyQt5-Qt5 PyQt5-sip PyQt5` を試す |
| `pywin32` をインストールできない | Windows環境依存 | [pywin32 Releases](https://github.com/mhammond/pywin32/releases) から手動インストール |
| キャラクターが全く反応しない | `bypassPermissions` フラグ忘れ | `claude --permission-mode bypassPermissions` で起動しているか確認 |
| 「WinNicoが起動していません」でブロックされる | WinNicoが未起動 | `python winnico_app.py` を先に起動してから `claude` を起動する |
| ポート19234エラーで起動できない | 別プロセスがポートを使用中 | `netstat -ano \| findstr 19234` で確認し、該当プロセスを終了する |
| フックを登録したのにキャラクターが反応しない | venv内でセットアップし、venvのPythonパスが書き込まれた | `python setup_hooks.py --remove` → venvを `deactivate` → `python setup_hooks.py` を再実行 |
| キャラクターをクリックしてもウィンドウがフォーカスされない | Electron系エディタではSendMessage方式が効かない | `config.yaml` で `use_cursor_pos: true` に変更 |
| `self-check` で `pywin32` エラーが出る | pywin32が正しくインストールされていない | `pip install pywin32` を実行後、Pythonを再起動する |

---

## License

MIT

## Author

[suzutomo1984](https://github.com/suzutomo1984)
