"""
커스텀 다이얼로그 - alert.png 아이콘 통일 적용
"""
import tkinter as tk
from tkinter import ttk
from gui.utils import apply_icon
from paths import resource

ALERT_ICON = resource("gui/assets/alert.png")


def _base_dialog(parent, title: str, message: str, *, selectable: bool = False, action: tuple | None = None):
    """공통 다이얼로그 베이스. selectable=True 이면 텍스트 복사 가능."""
    dlg = tk.Toplevel(parent)
    dlg.title(title)
    dlg.resizable(False, False)
    dlg.grab_set()
    apply_icon(dlg)

    # ── 아이콘 + 제목 ──────────────────────────────
    header = ttk.Frame(dlg)
    header.pack(fill="x", padx=16, pady=(14, 4))
    header.columnconfigure(1, weight=1)

    col = 0
    if ALERT_ICON.exists():
        img = tk.PhotoImage(file=str(ALERT_ICON))
        icon_lbl = tk.Label(header, image=img, bd=0)
        icon_lbl.image = img  # GC 방지
        icon_lbl.grid(row=0, column=0, padx=(0, 8))
        col = 1

    ttk.Label(header, text=title, font=("맑은 고딕", 10, "bold")).grid(
        row=0, column=col, sticky="w"
    )

    # ── 메시지 영역 ───────────────────────────────
    if selectable:
        frame = ttk.Frame(dlg)
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        text = tk.Text(
            frame,
            wrap="word",
            height=8,
            width=74,
            font=("Consolas", 9),
            bg="#fff0f0",
            relief="solid",
            borderwidth=1,
        )
        scroll = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        text.insert("1.0", message)
        text.config(state="disabled")
    else:
        ttk.Label(dlg, text=message, wraplength=400, justify="left").pack(
            padx=24, pady=(0, 12)
        )

    # ── 버튼 영역 ─────────────────────────────────
    btn_frame = ttk.Frame(dlg)
    btn_frame.pack(fill="x", padx=16, pady=(0, 14))

    if selectable:
        def copy_all():
            dlg.clipboard_clear()
            dlg.clipboard_append(message)
        ttk.Button(btn_frame, text="전체 복사", command=copy_all, width=10).pack(side="left")

    ttk.Button(btn_frame, text="알겠어", command=dlg.destroy, width=10).pack(side="right")
    if action:
        action_label, action_cmd = action
        ttk.Button(btn_frame, text=action_label, command=action_cmd).pack(side="right", padx=(0, 8))

    # ── 자연 크기 확정 + 부모 기준 중앙 배치 ────
    dlg.update_idletasks()
    w = dlg.winfo_reqwidth()
    h = dlg.winfo_reqheight()
    pw = parent.winfo_rootx() + parent.winfo_width() // 2
    ph = parent.winfo_rooty() + parent.winfo_height() // 2
    x = pw - w // 2
    y = ph - h // 2
    dlg.geometry(f"{w}x{h}+{x}+{y}")

    dlg.wait_window(dlg)  # 닫힐 때까지 블로킹 (부모 창이 먼저 닫히는 현상 방지)


def show_error(parent, title: str, message: str):
    """텍스트 선택/복사 가능한 에러 다이얼로그"""
    _base_dialog(parent, title, message, selectable=True)


def show_warning(parent, title: str, message: str):
    """경고 다이얼로그"""
    _base_dialog(parent, title, message)


def show_info(parent, title: str, message: str, action: tuple | None = None):
    """정보 다이얼로그. action=(버튼라벨, 콜백) 으로 추가 버튼 삽입 가능"""
    _base_dialog(parent, title, message, action=action)
