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

> このセクションはClaude Codeが自律的に読み、ユーザーの代わりにセットアップを完了させるための指示書です。
> ユーザーがこのリポジトリをCloneしてClaude Codeに「セットアップして」と伝えるだけで、以下の手順を自動実行してください。

---

### Claude Codeへの指示

あなたはWinNicoのセットアップをユーザーの代わりに完全に完了させてください。  
ユーザーは待っているだけでよい状態にすることがゴールです。  
各ステップを順番に実行し、問題があればその場で対処してください。  
ユーザーへの確認が必要な場面では、必ず**AskUserQuestionツール**を使って一問一答で聞いてください。

---

### Step 1: Pythonバージョンの確認

```bash
python --version
```

- Python 3.10以上であればOK。そのまま次へ。
- 3.10未満の場合はユーザーに伝えて中断する。

---

### Step 2: 依存パッケージのインストール

まず仮想環境がアクティブかどうか確認する:

```bash
python -c "import sys; print('venv' if sys.prefix != getattr(sys, 'base_prefix', sys.prefix) else 'system')"
```

- `venv` と表示された場合 → ユーザーに以下を伝えてから `deactivate` するよう案内する:
  > 「仮想環境がアクティブです。setup_hooks.py はシステムのPythonパスを設定ファイルに書き込むため、仮想環境内でセットアップすると後でフックが壊れることがあります。一度 `deactivate` してから続けることをお勧めします。このまま続けますか？」
- `system` と表示された場合 → そのまま次へ。

パッケージをインストールする:

```bash
pip install -r requirements.txt
```

失敗した場合は以下を順番に試す:
1. `pip install PyQt5-Qt5 PyQt5-sip PyQt5` （PyQt5のwheel問題）
2. `pip install pywin32` （pywin32単体で再試行）
3. いずれも失敗した場合はエラー内容をユーザーに提示し、[Troubleshooting](#troubleshooting) を参照するよう案内する。

---

### Step 3: Claude Code フックの登録

既存の `~/.claude/settings.json` の設定は**バックアップが自動作成されるので安全**であることをユーザーに伝えてから実行する:

```bash
python setup_hooks.py
```

完了したら `~/.claude/settings.json` に `PreToolUse` と `Stop` の両方にWinNicoのエントリが追加されたことを確認する:

```bash
python -c "import json,pathlib; s=json.loads(pathlib.Path.home().joinpath('.claude','settings.json').read_text(encoding='utf-8')); [print(k, len(v), 'entries') for k,v in s.get('hooks',{}).items()]"
```

---

### Step 4: config.yaml の作成

`config.default.yaml` を元に `config.yaml` を作成する。以下をユーザーに**一問ずつ**確認してから作成する:

**質問1: 使用しているエディタ・ターミナルは何ですか？**

ウィンドウ上部のタイトルバーに表示されている文字列をそのまま教えてもらう。  
例: `Antigravity` / `Cursor` / `Visual Studio Code` / `Windows Terminal` など  
→ `target_window_titles` に設定する。  
⚠️ `"Claude"` という文字列は避ける（ブラウザでClaude.aiを開いているタブにも一致するため）。

**質問2: キャラクター画像はどうしますか？**

- 付属の `character.png` をそのまま使う → `character_image: "character.png"` のまま
- 自分の画像を使いたい → PNG推奨・透過対応。ファイルのパスを教えてもらい `character_image` に設定する

**質問3: Cursor または VSCode を使っていますか？**

- Yes → `use_cursor_pos: true` に設定する（Electron系エディタはSendMessage方式が効かないため）
- No → `use_cursor_pos: false`（デフォルト）のまま

回答をもとに `config.yaml` を作成する（`config.default.yaml` をベースに変更箇所のみ上書き）。

---

### Step 5: WinNicoの起動案内

ここからはユーザーに操作を案内する。以下をユーザーに伝える:

---

**セットアップが完了しました！あとは2つのターミナルを開いて以下を実行するだけです。**

**ターミナル1（WinNicoを起動・起動したままにしておく）:**
```bash
python winnico_app.py
```
起動すると `[WinNico self-check] ✅ 環境チェック OK` と表示されます。  
画面下部中央にキャラクターが表示されたら成功です。

**ターミナル2（Claude Codeをbypassモードで起動）:**
```bash
claude --permission-mode bypassPermissions
```

> **`--permission-mode bypassPermissions` について:**  
> このフラグはClaude Code自身の承認UIを無効化し、すべての承認判断をWinNicoに委譲するモードです。  
> このフラグなしで起動すると、Claude Code自身のUIが先に表示されてWinNicoが機能しません。  
> WinNicoを使う場合は**必ずこのフラグ付きで起動**してください。

> **起動順序について:**  
> WinNicoを**必ずClaude Codeより先に**起動してください。  
> WinNicoが起動していない状態でClaude Codeが危険なコマンドを実行しようとすると、コマンドは自動的にブロックされます（黙って実行されることはありません）。

---

### Step 6: 動作確認

WinNicoとClaude Codeの両方が起動したら、Claude Codeのチャットで以下を試してもらうよう案内する:

```
curl --version を実行してみてください
```

WinNicoのキャラクターが承認ダイアログを表示し、通知音が鳴ればセットアップ完了です。  
反応しない場合は [Troubleshooting](#troubleshooting) を参照してください。

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
