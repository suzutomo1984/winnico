"""
WinNico - Claude Code Windows コンパニオン
画面上に常駐するキャラクターが Claude Code の承認リクエストを通知してくれるアプリ

起動方法: python winnico_app.py
"""

import sys
import threading
import socket
import json
import time
import math
import traceback
import winsound
from pathlib import Path
try:
    import win32gui
    import win32con
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton,
                              QSystemTrayIcon, QMenu, QAction, QTextEdit, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QRect, QPoint, QRectF
from PyQt5.QtGui import (QPainter, QColor, QBrush, QPen, QFont, QPainterPath,
                          QRadialGradient, QLinearGradient, QIcon, QPixmap)

# TCP ポート (hook_handler.py と合わせること)
SOCKET_PORT = 19234

# ============================================================
# 設定ローダー
# ============================================================
_BASE_DIR = Path(__file__).parent

def _load_config() -> dict:
    """config.yaml → config.default.yaml の順で読み込む。yamlが使えない場合はデフォルト値を返す。"""
    defaults = {
        "character_image": "character.png",
        "target_window_titles": ["Claude", "Terminal"],
        "chat_input_offset_from_bottom": 60,
        "use_cursor_pos": False,
    }
    if not HAS_YAML:
        return defaults

    for fname in ("config.yaml", "config.default.yaml"):
        cfg_path = _BASE_DIR / fname
        if cfg_path.exists():
            try:
                with open(cfg_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                # デフォルト値で補完
                for k, v in defaults.items():
                    data.setdefault(k, v)
                return data
            except Exception as e:
                print(f"[WinNico] 設定ファイル読み込みエラー ({fname}): {e}")
    return defaults

CONFIG = _load_config()

# ============================================================
# スレッド間通信用シグナルブリッジ
# ============================================================
class SignalBridge(QObject):
    approval_requested   = pyqtSignal(dict)
    notification_received = pyqtSignal(str)
    focus_requested      = pyqtSignal()

# セッション中に「まとめて許可」されたキーワード種別を保持
_auto_allow_keywords: set = set()

bridge = SignalBridge()


def _play_sound(sound_type: str) -> None:
    """Windowsシステムサウンドを非同期で鳴らす"""
    def _play():
        try:
            if sound_type == "alert":
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            elif sound_type == "complete":
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass
    threading.Thread(target=_play, daemon=True).start()

# ============================================================
# メインキャラクターウィンドウ
# ============================================================
class NicoWindow(QWidget):

    IDLE    = "idle"
    ALERT   = "alert"
    HAPPY   = "happy"
    WAITING = "waiting"

    # Claude ブランドカラー
    C_ORANGE    = QColor(207,  93,  38)
    C_ORANGE_LT = QColor(240, 140,  60)
    C_ORANGE_DK = QColor(160,  60,  20)
    C_CREAM     = QColor(255, 240, 220)
    C_STAR      = QColor(255, 200,  80)

    def __init__(self):
        super().__init__()
        self.state        = self.IDLE
        self.anim_frame   = 0
        self.blink_frame  = 0
        self.alert_shake  = 0
        self.speech_text  = ""

        self._response_event  = None
        self._response_result = None
        self._drag_offset     = QPoint()
        self._current_danger_kw: str = ""  # 現在の承認リクエストのキーワード種別

        # キャラ画像ロード（透過PNG対応・config.yamlで差し替え可能）
        img_setting = CONFIG.get("character_image", "character.png")
        img_path = Path(img_setting) if Path(img_setting).is_absolute() else _BASE_DIR / img_setting
        if not img_path.exists():
            print(f"[WinNico] キャラ画像が見つかりません: {img_path}、デフォルトにフォールバック")
            img_path = _BASE_DIR / "character.png"
        self._char_pixmap = QPixmap(str(img_path)).scaled(
            80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        self._setup_ui()
        self._setup_tray()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)   # 20 FPS

        bridge.approval_requested.connect(self._on_approval_request)
        bridge.notification_received.connect(self._on_notification)
        bridge.focus_requested.connect(self._focus_claude_window)

    # ----------------------------------------------------------
    # UI セットアップ
    # ----------------------------------------------------------
    def _setup_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(280, 380)

        # 画面下部中央（タスクバーの上）に配置
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - 280) // 2
        y = screen.height() - 380 - 10  # タスクバー上から10px
        self.move(x, y)

        # ボタンを最上部に配置（3ボタン構成 + 閉じる + キャンセル）
        self.approve_btn     = QPushButton("✅ 許可", self)
        self.approve_all_btn = QPushButton("✅✅ 以降も許可", self)
        self.deny_btn        = QPushButton("❌ 拒否", self)
        self.close_btn       = QPushButton("✕ 閉じる", self)
        self.cancel_btn      = QPushButton("🛑 処理を止める", self)
        self.approve_btn.setGeometry(15,  8,  78, 34)
        self.approve_all_btn.setGeometry(97,  8,  90, 34)
        self.deny_btn.setGeometry(191,  8,  74, 34)
        self.close_btn.setGeometry(15,  8, 250, 34)
        self.cancel_btn.setGeometry(15, 46, 250, 30)

        # テキストエリアはボタンの下
        self.text_area = QTextEdit(self)
        self.text_area.setGeometry(12, 84, 256, 156)
        self.text_area.setReadOnly(True)
        self.text_area.setFont(QFont("Meiryo", 9))
        self.text_area.setStyleSheet("""
            QTextEdit {
                background: rgba(255, 245, 230, 220);
                border: 2px solid #f08232;
                border-radius: 10px;
                padding: 6px;
                color: #3c1e0a;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #f08232;
                border-radius: 4px;
            }
        """)
        self.text_area.hide()

        for btn, color, hover in [
            (self.approve_btn,     "#4CAF50", "#45a049"),
            (self.approve_all_btn, "#2196F3", "#1976D2"),
            (self.deny_btn,        "#f44336", "#da190b"),
            (self.close_btn,       "#888888", "#666666"),
            (self.cancel_btn,      "#b71c1c", "#7f0000"),
        ]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color}; color: white; border-radius: 10px;
                    font-size: 11px; font-weight: bold; border: none;
                }}
                QPushButton:hover {{ background: {hover}; }}
            """)
            btn.hide()

        self.approve_btn.clicked.connect(lambda: self._respond(True, bulk=False))
        self.approve_all_btn.clicked.connect(lambda: self._respond(True, bulk=True))
        self.deny_btn.clicked.connect(lambda: self._respond(False, bulk=False))
        self.close_btn.clicked.connect(self._back_to_idle)
        self.cancel_btn.clicked.connect(self._cancel_processing)

    def _setup_tray(self):
        pix = QPixmap(32, 32)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(self.C_ORANGE))
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        # 星マーク
        star = QPainterPath()
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            r = 7 if i % 2 == 0 else 3.5
            x = 16 + r * math.cos(angle)
            y = 16 + r * math.sin(angle)
            if i == 0: star.moveTo(x, y)
            else:       star.lineTo(x, y)
        star.closeSubpath()
        p.setBrush(QBrush(self.C_STAR))
        p.drawPath(star)
        p.end()

        self._tray = QSystemTrayIcon(QIcon(pix), self)
        menu = QMenu()
        qa = QAction("終了", self)
        qa.triggered.connect(QApplication.quit)
        menu.addAction(qa)
        self._tray.setContextMenu(menu)
        self._tray.setToolTip("WinClaude - Claude Code コンパニオン")
        self._tray.show()

    # ----------------------------------------------------------
    # アニメーション
    # ----------------------------------------------------------
    def _tick(self):
        self.anim_frame  += 1
        self.blink_frame += 1
        if self.alert_shake > 0:
            self.alert_shake -= 1
        self.update()

    def _bob_y(self):
        if self.state == self.ALERT:
            return math.sin(self.anim_frame * 0.25) * 7
        if self.state == self.HAPPY:
            return math.sin(self.anim_frame * 0.35) * 5
        return math.sin(self.anim_frame * 0.07) * 2

    def _shake_x(self):
        if self.alert_shake > 0:
            return math.sin(self.anim_frame * 0.8) * 6 * (self.alert_shake / 20)
        return 0.0

    # ----------------------------------------------------------
    # 描画
    # ----------------------------------------------------------
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # ウィンドウ全体を透明でクリア
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)

        if self.speech_text and self.state in (self.ALERT, self.WAITING, self.HAPPY):
            self._draw_bubble(p, self.speech_text)

        # キャラ画像を描画（ボブアニメーション＋シェイク）
        cx = int(130 + self._shake_x())
        cy = int(310 + self._bob_y())
        img_x = cx - self._char_pixmap.width() // 2
        img_y = cy - self._char_pixmap.height() // 2

        # アラート時に明るくフラッシュ
        if self.state == self.ALERT:
            alpha = int(200 + 55 * math.sin(self.anim_frame * 0.25))
            p.setOpacity(alpha / 255)
        else:
            p.setOpacity(1.0)

        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.drawPixmap(img_x, img_y, self._char_pixmap)
        p.setOpacity(1.0)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)

        p.end()

    def _draw_bubble(self, p, text):
        rect = QRectF(8, 50, 244, 200)
        color = QColor(255, 245, 230) if self.state == self.HAPPY else QColor(255, 238, 220)
        border = self.C_ORANGE if self.state == self.HAPPY else QColor(240, 130, 50)

        p.setRenderHint(QPainter.Antialiasing, True)
        p.setBrush(QBrush(color))
        p.setPen(QPen(border, 2))
        p.drawRoundedRect(rect, 14, 14)

        # 尻尾（キャラy=310に向けて）
        tail = QPainterPath()
        tail.moveTo(112, 249)
        tail.lineTo(130, 265)
        tail.lineTo(148, 249)
        tail.closeSubpath()
        p.setBrush(QBrush(color))
        p.setPen(Qt.NoPen)
        p.drawPath(tail)
        p.setPen(QPen(border, 2))
        p.drawLine(QPoint(112, 249), QPoint(130, 265))
        p.drawLine(QPoint(130, 265), QPoint(148, 249))

        p.setPen(QPen(QColor(60, 30, 10)))
        p.setFont(QFont("Meiryo", 9))
        p.drawText(
            rect.adjusted(10, 8, -10, -8).toRect(),
            Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
            text
        )
        p.setRenderHint(QPainter.Antialiasing, False)

    def _draw_pixel_character(self, p, cx, cy):
        """ドット絵キャラを描画する"""
        S = 8  # 1ドットのサイズ（px）

        # 状態による色変化
        if self.state == self.ALERT:
            body_col = QColor(210, 100, 40)
        elif self.state == self.HAPPY:
            body_col = QColor(230, 130, 60)
        else:
            body_col = QColor(196, 98, 52)  # 元画像のオレンジ茶

        dark_col  = QColor(120, 55, 20)   # 輪郭・影
        eye_col   = QColor(20, 20, 20)    # 目

        def dot(gx, gy, col=None):
            """グリッド座標(gx,gy)にドットを描く。中心cx,cyからの相対"""
            c = col if col else body_col
            p.setBrush(QBrush(c))
            p.setPen(Qt.NoPen)
            p.drawRect(int(cx + gx * S), int(cy + gy * S), S, S)

        # --- キャラのドットマップ（グリッド座標、cx/cy が左上基準） ---
        # 画像を分析: 横8ドット×高さ8ドット程度、腕と足付き
        # オフセットをキャラ中心に合わせる: cx,cy をキャラ中央上端に設定
        ox, oy = -4, -8  # グリッドオフセット（中央揃え）

        # ドットマップ定義 (row, col) → 0=透明, 1=体, 2=暗い(輪郭)
        pixel_map = [
            # col:  0  1  2  3  4  5  6  7
            [0, 0, 2, 2, 2, 2, 0, 0],  # row 0  頭上
            [0, 2, 1, 1, 1, 1, 2, 0],  # row 1
            [2, 1, 1, 2, 2, 1, 1, 2],  # row 2  目の行
            [2, 1, 1, 1, 1, 1, 1, 2],  # row 3
            [2, 1, 1, 1, 1, 1, 1, 2],  # row 4
            [0, 2, 1, 1, 1, 1, 2, 0],  # row 5
            [0, 0, 2, 2, 2, 2, 0, 0],  # row 6  胴体下
            # 腕
        ]

        for row, cols in enumerate(pixel_map):
            for col, val in enumerate(cols):
                if val == 0:
                    continue
                color = dark_col if val == 2 else body_col
                dot(ox + col, oy + row, color)

        # 目（row2: col2,col5 の位置に黒ドット）
        blink = (self.blink_frame % 120) < 4
        if not blink:
            dot(ox + 2, oy + 2, eye_col)
            dot(ox + 5, oy + 2, eye_col)
        else:
            # まばたき: 目を横線に
            dot(ox + 2, oy + 2, dark_col)
            dot(ox + 5, oy + 2, dark_col)

        # 左腕
        dot(ox - 1, oy + 2, dark_col)
        dot(ox - 1, oy + 3, body_col)
        dot(ox - 1, oy + 4, dark_col)

        # 右腕
        dot(ox + 8, oy + 2, dark_col)
        dot(ox + 8, oy + 3, body_col)
        dot(ox + 8, oy + 4, dark_col)

        # 左足
        dot(ox + 1, oy + 7, dark_col)
        dot(ox + 1, oy + 8, body_col)
        dot(ox + 2, oy + 8, dark_col)

        # 右足
        dot(ox + 5, oy + 7, dark_col)
        dot(ox + 5, oy + 8, body_col)
        dot(ox + 6, oy + 8, dark_col)

        # アラート時: 体を点滅させる
        if self.state == self.ALERT:
            alpha = int(180 + 75 * math.sin(self.anim_frame * 0.3))
            flash = QColor(255, 220, 50, alpha)
            dot(ox + 3, oy + 4, flash)
            dot(ox + 4, oy + 4, flash)

    # ----------------------------------------------------------
    # スロット
    # ----------------------------------------------------------
    def _on_approval_request(self, data):
        tool_name  = data.get("tool_name", "不明なツール")
        summary    = data.get("summary", "")
        danger_kw  = data.get("danger_kw", "")  # hook_handlerから送られるキーワード種別

        # まとめて許可済みのキーワード種別なら即allow
        if danger_kw and danger_kw in _auto_allow_keywords:
            self._response_event  = threading.Event()
            self._response_result = True
            self._response_event.set()
            return

        TOOL_NAMES_JA = {
            "Bash":        "コマンド実行",
            "Edit":        "ファイル編集",
            "Write":       "ファイル作成",
            "NotebookEdit": "ノートブック編集",
        }
        TOOL_PHRASES = [
            "ねえ、これやっていい？",
            "ちょっといいかな？",
            "これ、許可してくれる？",
            "お願いがあるんだけど！",
            "ひとついい？",
        ]
        import random
        tool_ja = TOOL_NAMES_JA.get(tool_name, tool_name)
        phrase   = random.choice(TOOL_PHRASES)

        # 現在のキーワード種別を保持（_respondで使う）
        self._current_danger_kw = danger_kw

        # 「以降も許可」ボタンのラベルをキーワード種別に合わせる
        if danger_kw:
            self.approve_all_btn.setText(f"✅✅ {danger_kw}系は全部許可")
        else:
            self.approve_all_btn.setText("✅✅ 以降も許可")

        # テキストエリアに内容を表示
        self.text_area.setPlainText(f"{phrase}\n\n🛠 {tool_ja}\n{summary}")
        self.text_area.show()
        self.text_area.verticalScrollBar().setValue(0)
        self.speech_text = ""  # paintEventの吹き出しは使わない

        self.state       = self.ALERT
        self.alert_shake = 20
        self._response_event  = threading.Event()
        self._response_result = None

        _play_sound("alert")

        self.approve_btn.show()
        self.approve_all_btn.show()
        self.deny_btn.show()
        self.cancel_btn.show()
        self.raise_()

        self._tray.showMessage(
            "Claude Code - 承認が必要",
            f"{tool_name}: {summary[:80]}",
            QSystemTrayIcon.Information,
            5000
        )

    def _on_notification(self, message):
        self.text_area.setPlainText(message)
        self.text_area.show()
        self.close_btn.show()
        self.speech_text = ""
        self.state       = self.HAPPY
        self.alert_shake = 10
        _play_sound("complete")
        QTimer.singleShot(7000, self._back_to_idle)

    def _respond(self, approved: bool, bulk: bool = False):
        # まとめて許可の場合、このキーワード種別をセッション中auto-allowに登録
        if bulk and approved and self._current_danger_kw:
            _auto_allow_keywords.add(self._current_danger_kw)
            msg = f"✅ {self._current_danger_kw}系は以降全部許可！"
        else:
            msg = "✅ 了解！" if approved else "🚫 拒否したよ"

        self._response_result = approved
        self.approve_btn.hide()
        self.approve_all_btn.hide()
        self.deny_btn.hide()
        self.cancel_btn.hide()
        self.text_area.hide()
        self.text_area.setPlainText(msg)
        self.text_area.show()
        self.state = self.HAPPY if approved else self.IDLE
        QTimer.singleShot(2000, self._back_to_idle)
        if self._response_event:
            self._response_event.set()

    def _cancel_processing(self):
        """処理を止める（ESC相当）— 承認待ちをblockで返す"""
        self._response_result = False
        self.approve_btn.hide()
        self.approve_all_btn.hide()
        self.deny_btn.hide()
        self.cancel_btn.hide()
        self.text_area.hide()
        self.text_area.setPlainText("🛑 処理を止めたよ")
        self.text_area.show()
        self.state = self.IDLE
        QTimer.singleShot(2000, self._back_to_idle)
        if self._response_event:
            self._response_event.set()

    def _back_to_idle(self):
        self.state       = self.IDLE
        self.speech_text = ""
        self.text_area.hide()
        self.close_btn.hide()
        self.cancel_btn.hide()

    # ----------------------------------------------------------
    # ドラッグ＆クリック
    # ----------------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_offset = e.globalPos() - self.frameGeometry().topLeft()
            self._drag_start  = e.globalPos()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            # ほぼ動いていない（ドラッグでない）場合はクリックとみなす
            if hasattr(self, "_drag_start"):
                diff = e.globalPos() - self._drag_start
                if abs(diff.x()) < 5 and abs(diff.y()) < 5:
                    self._focus_claude_window()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_offset:
            self.move(e.globalPos() - self._drag_offset)

    def _focus_claude_window(self):
        """設定ファイルで指定されたウィンドウをフォーカスする"""
        if not HAS_WIN32:
            return

        target_titles  = CONFIG.get("target_window_titles", ["Antigravity"])
        offset_bottom  = CONFIG.get("chat_input_offset_from_bottom", 60)
        use_cursor_pos = CONFIG.get("use_cursor_pos", False)

        def enum_handler(hwnd, results):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd).lower()
            for t in target_titles:
                if t.lower() in title:
                    results.append((hwnd, win32gui.GetWindowText(hwnd)))

        found = []
        win32gui.EnumWindows(enum_handler, found)

        if not found:
            return

        hwnd = found[0][0]
        try:
            # 最小化されてたら復元
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.05)

            # WINNICOを先にアクティブにしてから対象ウィンドウへ（クリック時はWINNICOがフォアグラウンド）
            my_hwnd = int(self.winId())
            win32gui.SetForegroundWindow(my_hwnd)
            time.sleep(0.05)
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1)

            # チャット入力欄にフォーカスを送る
            rect = win32gui.GetWindowRect(hwnd)
            win_left, win_top, win_right, win_bottom = rect
            click_x = (win_left + win_right) // 2
            click_y = win_bottom - offset_bottom
            if use_cursor_pos:
                # SetCursorPos方式: 物理クリック（カーソルが動く）
                # Electron系エディタ（Cursor, VSCode等）でSendMessageが効かない場合に使用
                win32api.SetCursorPos((click_x, click_y))
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, click_x, click_y, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, click_x, click_y, 0, 0)
                print(f"[WinNico] フォーカス試行: {found[0][1]} → SetCursorPos({click_x}, {click_y})")
            else:
                # SendMessage方式: カーソルが動かない（デフォルト）
                lParam = (click_y - win_top) << 16 | (click_x - win_left)
                win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
                win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
                print(f"[WinNico] フォーカス試行: {found[0][1]} → SendMessage({click_x}, {click_y})")
        except Exception as e:
            print(f"[WinNico] フォーカス失敗: {e}")


# ============================================================
# ソケットサーバー
# ============================================================
def _create_socket_server() -> socket.socket:
    """ソケットサーバーを生成してバインドする。失敗時はOSErrorを送出する。"""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", SOCKET_PORT))  # ポート使用中なら OSError
    srv.listen(5)
    return srv


def run_socket_server(srv: socket.socket, nico):
    print(f"[WinClaude] ソケットサーバー起動 ポート {SOCKET_PORT}")
    while True:
        try:
            conn, _ = srv.accept()
        except Exception:
            break
        threading.Thread(
            target=_handle_connection, args=(conn, nico), daemon=True
        ).start()


def _handle_connection(conn, nico):
    try:
        raw = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk: break
            raw += chunk
            if raw.endswith(b"\n"): break

        request  = json.loads(raw.decode())
        msg_type = request.get("type", "approval")

        if msg_type == "notification":
            bridge.notification_received.emit(request.get("message", "通知"))
            conn.sendall(b'{"status":"ok"}\n')
            return

        bridge.approval_requested.emit(request)

        # 応答待ち（最大 120 秒）
        for _ in range(240):
            if nico._response_event and nico._response_event.is_set():
                break
            time.sleep(0.5)

        approved = nico._response_result if nico._response_result is not None else False
        nico._response_event  = None
        nico._response_result = None

        if approved:
            resp = {"behavior": "allow"}
        else:
            resp = {"behavior": "block", "reason": "ユーザーが WinClaude で拒否しました"}

        conn.sendall((json.dumps(resp, ensure_ascii=False) + "\n").encode())

    except Exception as e:
        print(f"[WinClaude] エラー:\n{traceback.format_exc()}")
        try:
            err_resp = json.dumps(
                {"behavior": "block", "reason": "WinNicoサーバーでエラーが発生しました。"},
                ensure_ascii=False
            ) + "\n"
            conn.sendall(err_resp.encode())
        except Exception:
            pass
    finally:
        conn.close()


# ============================================================
# エントリポイント
# ============================================================
def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    nico = NicoWindow()
    nico.show()

    try:
        srv = _create_socket_server()
    except OSError as e:
        print(f"[WinClaude] 致命的エラー: ポート {SOCKET_PORT} をバインドできません: {e}")
        print("別のWinNicoが起動中か、ポートが使用中の可能性があります。")
        sys.exit(1)

    t = threading.Thread(target=run_socket_server, args=(srv, nico), daemon=True)
    t.start()

    print("[WinClaude] 起動しました。Claude Code の承認を待機中...")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
