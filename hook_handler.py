"""
WinNico - Claude Code フックハンドラー
Claude Code の PreToolUse フックから呼び出されるスクリプト。
WinNico アプリにリクエストを送り、ユーザーの承認/拒否結果を返す。

このスクリプトは Claude Code が自動的に呼び出します。手動実行は不要です。
"""

import sys
import json
import socket
import time

SOCKET_PORT = 19234
TIMEOUT_SECONDS = 120   # 承認待ちのタイムアウト（秒）

# 承認が必要なツール（これ以外は全部スルー）
APPROVAL_TOOLS = {
    "Bash",
}

# Bash の中でも承認が必要な危険コマンド（キーワード → 説明）
DANGEROUS_BASH_KEYWORDS = {
    "rm ":          "ファイル/フォルダを削除",
    "rm\t":         "ファイル/フォルダを削除",
    "rmdir":        "フォルダを削除",
    "git push":     "リモートにpush",
    "git reset":    "gitの履歴をリセット",
    "git checkout": "ブランチ/ファイルを切り替え",
    "git clean":    "未追跡ファイルを削除",
    "pip install":  "Pythonパッケージをインストール",
    "pip uninstall":"Pythonパッケージを削除",
    "npm install":  "npmパッケージをインストール",
    "npm uninstall":"npmパッケージを削除",
    "drop ":        "DBテーブルを削除",
    "delete ":      "DBレコードを削除",
    "truncate ":    "DBテーブルを空にする",
    "format ":      "ディスクをフォーマット",
    "mkfs":         "ファイルシステムを作成",
    "shutdown":     "シャットダウン",
    "reboot":       "再起動",
    "curl ":        "外部からダウンロード",
    "wget ":        "外部からダウンロード",
    "powershell":   "PowerShellを実行",
    "cmd /c":       "cmdコマンドを実行",
}

# 通知のみで承認不要なツール（キャラが教えてくれるだけ）
NOTIFY_ONLY_TOOLS = {
    "WebSearch",
    "WebFetch",
}


def send_to_winnico(payload: dict) -> dict:
    """WinNico アプリに JSON を送り、レスポンスを受け取る"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT_SECONDS)
        sock.connect(("127.0.0.1", SOCKET_PORT))
        sock.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode())

        raw = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            raw += chunk
            if raw.endswith(b"\n"):
                break
        sock.close()
        return json.loads(raw.decode())
    except (ConnectionRefusedError, socket.timeout):
        # WinNico が起動していない場合はデフォルト許可
        return {"behavior": "allow"}
    except Exception as e:
        sys.stderr.write(f"[WinNico hook] エラー: {e}\n")
        return {"behavior": "allow"}


def main():
    # Claude Code は stdin に JSON を流し込む
    raw_input = sys.stdin.read()

    try:
        hook_data = json.loads(raw_input)
    except json.JSONDecodeError:
        # パースできなければ許可
        sys.exit(0)

    tool_name  = hook_data.get("tool_name", "")
    tool_input = hook_data.get("tool_input", {})

    # --- 通知のみ（承認不要）---
    if tool_name in NOTIFY_ONLY_TOOLS:
        msg = _build_notify_message(tool_name, tool_input)
        send_to_winnico({"type": "notification", "message": msg})
        sys.exit(0)

    # --- 承認不要なツールはスルー ---
    if tool_name not in APPROVAL_TOOLS:
        sys.exit(0)

    # --- Bash は危険コマンドのみ承認 ---
    danger_kw = ""  # まとめて許可用のキーワード種別名
    if tool_name == "Bash":
        command = tool_input.get("command", "").lower()
        matched_desc = None
        matched_kw   = None
        for kw, desc in DANGEROUS_BASH_KEYWORDS.items():
            if kw in command:
                matched_desc = desc
                matched_kw   = kw.strip()
                break
        if not matched_desc:
            sys.exit(0)
        tool_input["_danger_desc"] = matched_desc
        danger_kw = matched_kw or ""

    # --- 承認が必要なツール ---
    summary = _build_approval_summary(tool_name, tool_input)
    response = send_to_winnico({
        "type":       "approval",
        "tool_name":  tool_name,
        "tool_input": tool_input,
        "summary":    summary,
        "danger_kw":  danger_kw,
    })

    behavior = response.get("behavior", "allow")

    if behavior == "block":
        reason = response.get("reason", "ユーザーが拒否しました")
        # Claude Code に block を返す（stdout に JSON + 改行）
        result = {
            "decision": "block",
            "reason":   reason,
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    # allow の場合は何も出力せず exit 0
    sys.exit(0)


def _build_approval_summary(tool_name: str, tool_input: dict) -> str:
    """承認ダイアログ用の要約テキストを構築"""
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        danger_desc = tool_input.get("_danger_desc", "")
        lines = [l.strip() for l in cmd.strip().splitlines() if l.strip()]
        if len(lines) == 0:
            return "$ (空コマンド)"
        first = lines[0][:120]
        cmd_text = f"$ {first}"
        if len(lines) > 1:
            rest = "\n".join(lines[1:4])[:200]
            cmd_text += f"\n{rest}"
            if len(lines) > 4:
                cmd_text += f"\n... (+{len(lines)-4}行)"
        explanation = _explain_command(cmd.strip())
        header = f"⚠️ {danger_desc}\n📝 {explanation}" if danger_desc else f"📝 {explanation}"
        return f"{header}\n\n{cmd_text}"

    if tool_name == "Write":
        path = tool_input.get("file_path", "")
        content = tool_input.get("content", "")
        lines = content.strip().splitlines()
        return f"新規作成: {path}\n{len(lines)}行のファイル"

    if tool_name == "Edit":
        path = tool_input.get("file_path", "").replace("\\", "/").split("/")[-1]
        old = tool_input.get("old_string", "")[:200].replace("\n", "\n  ")
        new = tool_input.get("new_string", "")[:200].replace("\n", "\n  ")
        return f"📄 {path}\n\n[-] {old}\n\n[+] {new}"

    if tool_name == "NotebookEdit":
        path = tool_input.get("notebook_path", "")
        return f"Notebook編集: {path}"

    return str(tool_input)[:100]


def _explain_command(cmd: str) -> str:
    """コマンドを自然な日本語で説明する"""
    import re
    c = cmd.strip()
    lower = c.lower()

    # rm
    if lower.startswith("rm "):
        flags = re.findall(r'-\w+', c)
        targets = [t for t in c.split() if not t.startswith('-') and t != 'rm']
        target_str = "、".join(t.split("/")[-1].split("\\")[-1] for t in targets[:3])
        force = "-f" in flags or "--force" in flags
        recursive = "-r" in flags or "-rf" in flags or "-fr" in flags
        desc = "強制" if force else ""
        desc += "再帰的に" if recursive else ""
        return f"{target_str} を{desc}削除する"

    # git push
    if "git push" in lower:
        parts = c.split()
        remote = parts[parts.index("push") + 1] if "push" in parts and len(parts) > parts.index("push") + 1 else "origin"
        branch = parts[parts.index("push") + 2] if len(parts) > parts.index("push") + 2 else ""
        return f"{remote}/{branch} にpushする".rstrip("/")

    # git reset
    if "git reset" in lower:
        hard = "--hard" in lower
        return f"gitを{'ハードリセット（変更を破棄）' if hard else 'リセット'}する"

    # git checkout
    if "git checkout" in lower:
        parts = c.split()
        target = parts[-1] if len(parts) > 2 else ""
        return f"'{target}' にcheckoutする"

    # git clean
    if "git clean" in lower:
        return "未追跡ファイルをすべて削除する"

    # pip install/uninstall
    if "pip install" in lower:
        pkgs = re.findall(r'(?:install)\s+([\w\-\[\],>=<.]+)', c, re.I)
        return f"{' '.join(pkgs)} をインストールする" if pkgs else "Pythonパッケージをインストールする"

    if "pip uninstall" in lower:
        pkgs = re.findall(r'(?:uninstall)\s+([\w\-]+)', c, re.I)
        return f"{' '.join(pkgs)} を削除する" if pkgs else "Pythonパッケージを削除する"

    # npm install/uninstall
    if "npm install" in lower:
        parts = c.split()
        idx = next((i for i, p in enumerate(parts) if p == "install"), -1)
        pkgs = parts[idx+1:idx+4] if idx >= 0 else []
        pkgs = [p for p in pkgs if not p.startswith("-")]
        return f"{' '.join(pkgs)} をインストールする" if pkgs else "npmパッケージをインストールする"

    # shutdown/reboot
    if "shutdown" in lower:
        return "システムをシャットダウンする"
    if "reboot" in lower:
        return "システムを再起動する"

    # curl/wget
    if lower.startswith("curl ") or lower.startswith("wget "):
        urls = re.findall(r'https?://[^\s"\']+', c)
        url = urls[0] if urls else "不明なURL"
        return f"{url} からダウンロードする"

    return "コマンドを実行する"


def _build_notify_message(tool_name: str, tool_input: dict) -> str:
    """通知用メッセージを構築"""
    if tool_name == "WebSearch":
        q = tool_input.get("query", "")
        return f"🔍 検索中\n{q[:50]}"
    if tool_name == "WebFetch":
        url = tool_input.get("url", "")
        return f"🌐 取得中\n{url[:50]}"
    return f"⚙️ {tool_name} 実行中"


if __name__ == "__main__":
    main()
