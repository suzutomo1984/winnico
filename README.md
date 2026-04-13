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

> このセクションはClaude Codeが自律的に読み、ユーザーの代わりにセットアップを**すべて**完了させるための指示書です。  
> **ユーザーはClaude Codeに「WinNicoをセットアップして」と伝えるだけでよい**状態にすることがゴールです。  
> 各ステップを順番に実行し、問題があればその場で対処してください。  
> ユーザーへの確認が必要な場面では、必ず **AskUserQuestionツール** を使って一問一答で聞いてください。

---

### Step -1: リポジトリの準備

まず適切な場所にリポジトリをクローンし、以降の作業ディレクトリを確定する:

```bash
# まだクローンしていない場合
git clone https://github.com/suzutomo1984/winnico.git "%USERPROFILE%\winnico"
```

クローン済みの場合は最新版に更新する:

```bash
cd "%USERPROFILE%\winnico" && git pull
```

**重要**: 以降のすべてのコマンドは winnico フォルダの絶対パスで実行する。  
例: `cd /d "C:\Users\ユーザー名\winnico" && python -m pip install -r requirements.txt`

---

### Step 0: 環境スキャン（Pythonコマンド検出 → 環境確認）

#### 0-A: Pythonコマンドを検出する

以下のコマンドを順に試し、最初に成功したものを「使用するPythonコマンド」として記録する:

```bash
python --version
```

失敗した場合:
```bash
python3 --version
```

それも失敗した場合:
```bash
py -3 --version
```

すべて失敗した場合:  
> 「Pythonが見つかりません。  
> https://www.python.org/downloads/ からPython 3.11以上をインストールしてください。  
> インストール時に **"Add Python to PATH"** にチェックを入れるのを忘れずに。  
> インストール完了後、このターミナルを閉じて新しいターミナルで再度「セットアップして」と伝えてください。」  
> → インストールが完了するまでここで停止する。

以降のすべてのコマンドで `python` の部分は「検出したPythonコマンド」に読み替えて実行する。

#### 0-B: 環境スキャンを実行する

```bash
<検出したPythonコマンド> -c "
import sys, importlib.util

results = []

# Pythonバージョン
ver = sys.version_info
ok = ver >= (3, 10)
warn_313 = ver >= (3, 13)
results.append(f'Python: {sys.version.split()[0]} ({\"OK\" if ok else \"NG: 3.10以上が必要\"}){\" [警告: 3.13以上はPyQt5が動作しない場合があります]\" if warn_313 else \"\"}')

# 仮想環境
in_venv = sys.prefix != getattr(sys, 'base_prefix', sys.prefix)
results.append(f'venv: {\"アクティブ (注意)\" if in_venv else \"なし (OK)\"}')
if in_venv:
    results.append(f'  システムPython候補: py -3 または python3 で確認してください')

# パッケージ確認
for pkg, import_name in [('PyQt5','PyQt5'), ('pywin32','win32gui'), ('pyyaml','yaml')]:
    found = importlib.util.find_spec(import_name) is not None
    results.append(f'{pkg}: {\"インストール済み\" if found else \"未インストール\"}')

for r in results:
    print(r)
"
```

スキャン結果を確認して以下のように対処する:

**Python が `NG` の場合（3.10未満）:**  
Pythonの再インストールをユーザーに案内して停止する。

**Python が 3.13以上の場合:**  
Step 2でPyQt5インストールに失敗した時のフォールバック手順を参照する。

**venv が `アクティブ` の場合:**  
→ Step 1へ進む。

**パッケージが `未インストール` の場合:**  
→ Step 2でインストールする（スキャン結果を記録しておく）。

全ての項目がOKであれば結果をユーザーに提示してStep 2へ進む。

---

### Step 1: （スキップ可）仮想環境の対処

Step 0で仮想環境がアクティブだった場合のみ実行する。

> **注意**: Claude CodeのBashツールでは `deactivate` コマンドは次のコマンドに引き継がれません。  
> 代わりに、システムのPythonを直接使用する方式をとります。

以下でシステムのPythonパスを取得する:

```bash
py -3 -c "import sys; print(sys.executable)"
```

`py -3` が使えない場合は以下を試す:
```bash
where python3
```

取得したパス（例: `C:\Python311\python.exe`）を以降のすべてのコマンドで `python` の代わりに使用する。  
例: `"C:\Python311\python.exe" -m pip install -r requirements.txt`

> **それでも解決しない場合:** AskUserQuestionでユーザーに確認する:  
> 「仮想環境 (venv) がアクティブです。venvを deactivate してから新しいターミナルでセットアップをやり直すか、このまま続けますか？このまま続ける場合、将来venvを削除するとフックが壊れます。」

---

### Step 2: 依存パッケージのインストール

```bash
cd /d "<winicoのパス>" && <python> -m pip install -r requirements.txt
```

失敗した場合は以下を順番に試す:

1. PyQt5が失敗した場合:
   ```bash
   <python> -m pip install PyQt5-Qt5 PyQt5-sip PyQt5
   ```
2. Python 3.13以上でPyQt5が動作しない場合:
   > 「Python 3.13以上はPyQt5の公式wheelが提供されていない場合があります。  
   > Python 3.11または3.12への変更を検討するか、[Troubleshooting](#troubleshooting) を参照してください。」  
   > → ユーザーに状況を説明して停止する。
3. pywin32が失敗した場合:
   ```bash
   <python> -m pip install pywin32
   ```
4. いずれも失敗した場合 → エラー内容をユーザーに提示し、[Troubleshooting](#troubleshooting) を案内して停止する。

---

### Step 3: Claude Code フックの登録

既存の `~/.claude/settings.json` の設定は**バックアップが自動作成されるので安全**であることをユーザーに伝えてから実行する:

```bash
cd /d "<winnicoのパス>" && <python> setup_hooks.py
```

仮想環境がアクティブでシステムPythonを直接使う場合:
```bash
cd /d "<winnicoのパス>" && "<システムPythonのパス>" setup_hooks.py
```

完了後、フックが正しく登録されたか確認する:

```bash
<python> -c "import json,pathlib; s=json.loads(pathlib.Path.home().joinpath('.claude','settings.json').read_text(encoding='utf-8')); [print(k, len(v), 'entries') for k,v in s.get('hooks',{}).items()]"
```

`PreToolUse` と `Stop` の両方に `1 entries` 以上表示されればOK。

---

### Step 4: config.yaml の作成

以下をユーザーに **一問ずつ** AskUserQuestionで確認してから `config.yaml` を作成する:

**質問1: 今使っているエディタ・ターミナルは何ですか？**

ウィンドウ上部のタイトルバーに表示されている文字列をそのまま教えてもらう。  
例: `Antigravity` / `Cursor` / `Visual Studio Code` / `Windows Terminal` など  
→ `target_window_titles` に設定する。  
⚠️ `"Claude"` は避ける（ブラウザでClaude.aiのタブにも一致するため）。

**質問2（条件付き）: マウスカーソルの動作方式について**

質問1の回答に `Cursor` または `Visual Studio Code` (もしくは `VSCode`) が含まれる場合は **質問2をスキップして** `use_cursor_pos: true` を自動設定する。

それ以外のエディタの場合のみ質問する:
> 「キャラクターをクリックしてもエディタにフォーカスが移らない場合は `use_cursor_pos: true` にすると改善することがあります。デフォルト（false）でよいですか？」

**質問3: キャラクター画像はどうしますか？**

- 付属の `character.png` をそのまま使う → 変更不要
- 自分の画像を使いたい → PNG推奨・透過対応。ファイルのパスを教えてもらい `character_image` に設定する

回答をもとに `config.yaml` をWriteツールで直接作成する（`config.default.yaml` の内容をベースに回答を反映して上書き）。  
既に `config.yaml` が存在する場合は `config.yaml.bak` にバックアップしてから上書きする。

---

### Step 5: 動作確認（WinNico起動テスト）

WinNicoをバックグラウンドで起動する（`run_in_background: true` パラメータを使用すること）:

```bash
cd /d "<winnicoのパス>" && <python> winnico_app.py
```

> **重要**: このコマンドは `run_in_background: true` で実行すること。  
> そうしないとWinNicoのGUIプロセスがBashツールをブロックして次のステップに進めなくなる。

起動後、3秒待ってから接続テストを行う:

```bash
<python> -c "
import socket, time

for i in range(6):
    time.sleep(1)
    try:
        s = socket.socket()
        s.settimeout(3)
        s.connect(('127.0.0.1', 19234))
        s.close()
        print('WinNico: 起動確認OK')
        break
    except Exception as e:
        if i == 5:
            print(f'WinNico: 起動確認失敗 - {e}')
        else:
            print(f'  接続待ち... ({i+1}/6)')
"
```

- `起動確認OK` → WinNicoが正常に起動している。Step 6へ。
- `起動確認失敗` → ユーザーに手動起動を依頼する（後述）。

---

### Step 6: セットアップ完了の案内

以下をユーザーに伝える:

---

**✅ セットアップが完了しました！**

WinNicoが起動しています。画面下部中央にキャラクターが表示されているはずです。

**次回からの起動方法:**

WinNicoとClaude Codeは**この順番**で起動してください。

**① WinNicoを起動（先に起動・起動したままにしておく）:**

方法A: バッチファイルをダブルクリック（推奨）
```
winnicoフォルダ内の start_winnico.bat をダブルクリック
```

方法B: ターミナルから起動
```bash
python winnico_app.py
```

**② Claude Codeをbypassモードで起動:**
```bash
claude --permission-mode bypassPermissions
```

> **`--permission-mode bypassPermissions` とは？**  
> Claude Code自身の承認UIを無効化し、すべての承認判断をWinNicoに委譲するモードです。  
> このフラグなしで起動すると、Claude Code自身の承認UIが先に表示されてWinNicoが動きません。  
> WinNicoを使う場合は**必ずこのフラグ付きで起動**してください。
>
> **注意**: bypassモードでは、ファイルの編集・作成（Edit/Write）は通知のみで自動許可されます。  
> Bashコマンド（rm、git push 等）のみが承認ダイアログの対象です。

> **起動順序が重要な理由:**  
> WinNicoが起動していない状態でClaude Codeが危険なコマンドを実行しようとすると、コマンドは自動的にブロックされます。必ずWinNicoを先に起動してください。

**動作テスト:**  
Claude Codeのチャットで「`curl --version` を実行して」と入力してみてください。  
WinNicoのキャラクターが承認ダイアログを表示し、通知音が鳴ればセットアップ完了です！

---

> **WinNicoが画面に表示されない場合（run_in_backgroundで起動できなかった場合）:**  
> 新しいターミナルを開いて以下を実行してください:
> ```bash
> cd /d "<winnicoのパス>"
> python winnico_app.py
> ```
> 起動したら `[WinNico self-check] ✅ 環境チェック OK` が表示されるはずです。  
> その後、別のターミナルで `claude --permission-mode bypassPermissions` を起動してください。

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
