"""
WinNico - Claude Code フックセットアップ
このスクリプトを一度実行すると、Claude Code の settings.json に
PreToolUse フックが自動登録されます。

使い方: python setup_hooks.py
"""

import json
import os
import sys
import shutil
import tempfile
from pathlib import Path


def _write_json_atomic(path: Path, data: dict) -> None:
    """JSON をアトミックに書き込む（クラッシュ時に既存ファイルを壊さない）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(path.parent), delete=False, suffix=".tmp"
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        temp_name = tmp.name
    os.replace(temp_name, path)


def get_claude_settings_path() -> Path:
    """Claude Code の settings.json パスを返す（~/.claude/settings.json が正）"""
    return Path.home() / ".claude" / "settings.json"


def get_hook_handler_path() -> Path:
    """hook_handler.py の絶対パスを返す"""
    return (Path(__file__).parent / "hook_handler.py").resolve()


def get_stop_handler_path() -> Path:
    """stop_handler.py の絶対パスを返す"""
    return (Path(__file__).parent / "stop_handler.py").resolve()


def _is_winnico_entry(entry: dict) -> bool:
    """エントリが WinNico のフックかどうかを判定する"""
    needles = ("winnico", "hook_handler", "stop_handler")
    return any(
        any(n in h.get("command", "").lower() for n in needles)
        for h in entry.get("hooks", [])
    )


def setup():
    force = "--force" in sys.argv

    # 仮想環境チェック
    if sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        print("[警告] 仮想環境がアクティブです。")
        print(f"  仮想環境Python: {sys.executable}")
        print("  このまま登録すると、仮想環境を削除した時にフックが壊れます。")
        if not force:
            print("  続行する場合は --force オプションを付けて再実行してください。")
            print("  例: python setup_hooks.py --force")
            print("中断しました。")
            sys.exit(0)
        else:
            print("  [--force] 仮想環境のまま続行します。")

    settings_path = get_claude_settings_path()
    hook_script   = get_hook_handler_path()
    stop_script   = get_stop_handler_path()
    python_exe    = sys.executable

    print(f"[WinNico Setup]")
    print(f"  設定ファイル: {settings_path}")
    print(f"  フックスクリプト: {hook_script}")
    print(f"  Stopスクリプト: {stop_script}")
    print(f"  Python: {python_exe}")
    print()

    hook_command = f'"{python_exe}" "{hook_script}"'
    stop_command = f'"{python_exe}" "{stop_script}"'

    # settings.json を読み込む（なければ新規作成）
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        # バックアップ
        backup = settings_path.with_suffix(".json.bak")
        shutil.copy2(settings_path, backup)
        print(f"  バックアップ作成: {backup}")

        with open(settings_path, "r", encoding="utf-8") as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError:
                settings = {}
    else:
        settings = {}

    # hooks セクションを構築
    if "hooks" not in settings:
        settings["hooks"] = {}

    hooks = settings["hooks"]

    if "PreToolUse" not in hooks:
        hooks["PreToolUse"] = []

    # 既存の WinNico エントリを削除（重複防止）
    hooks["PreToolUse"] = [h for h in hooks["PreToolUse"] if not _is_winnico_entry(h)]

    # WinNico フックを追加
    winnico_hook = {
        "matcher": "",          # 全ツール対象（hook_handler.py 内でフィルタリング）
        "hooks": [
            {
                "type":    "command",
                "command": hook_command,
            }
        ],
    }
    hooks["PreToolUse"].append(winnico_hook)

    # Stop フック（応答完了通知）
    if "Stop" not in hooks:
        hooks["Stop"] = []

    # 既存のWinNico Stopフックを削除（重複防止）
    hooks["Stop"] = [h for h in hooks["Stop"] if not _is_winnico_entry(h)]

    stop_hook = {
        "hooks": [
            {
                "type":    "command",
                "command": stop_command,
            }
        ],
    }
    hooks["Stop"].append(stop_hook)

    # 書き込み（アトミック：クラッシュ時に既存設定を壊さない）
    _write_json_atomic(settings_path, settings)

    print("  ✅ フック登録完了！")
    print()
    print("使い方:")
    print("  1. python winnico_app.py  を起動したままにする")
    print("  2. 通常通り claude を実行する")
    print("  3. Claude Code がツールを使おうとすると、キャラが承認を求めます")
    print()
    print("フックを削除する場合は setup_hooks.py --remove を実行してください")


def remove():
    settings_path = get_claude_settings_path()
    if not settings_path.exists():
        print("settings.json が見つかりません。")
        return

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except json.JSONDecodeError as e:
        print(f"settings.json のJSONが壊れています: {e}")
        return

    hooks = settings.setdefault("hooks", {})
    hooks["PreToolUse"] = [h for h in hooks.get("PreToolUse", []) if not _is_winnico_entry(h)]
    hooks["Stop"]       = [h for h in hooks.get("Stop", [])       if not _is_winnico_entry(h)]

    _write_json_atomic(settings_path, settings)

    print("✅ WinNico の PreToolUse / Stop フックを削除しました。")


if __name__ == "__main__":
    if "--remove" in sys.argv:
        remove()
    else:
        setup()
