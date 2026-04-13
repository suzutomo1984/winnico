"""
WinNico - Stop フックハンドラー
Claude Code の応答完了時に呼び出されるスクリプト。
Clawd に「完了したよ！」と通知する。
"""

import sys
import json
import socket

SOCKET_PORT = 19234


def main():
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    raw_input = sys.stdin.read()

    try:
        hook_data = json.loads(raw_input)
    except json.JSONDecodeError:
        hook_data = {}

    # 完了通知をWINNICOに送る
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect(("127.0.0.1", SOCKET_PORT))
        payload = json.dumps({
            "type": "notification",
            "message": "✅ 完了したよ！"
        }, ensure_ascii=False) + "\n"
        sock.sendall(payload.encode())
        sock.recv(256)
        sock.close()
    except Exception:
        pass  # WINNICOが起動していなければ無視

    sys.exit(0)


if __name__ == "__main__":
    main()
