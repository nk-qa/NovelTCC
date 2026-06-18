"""
설정 화면 - Confluence 계정 및 Claude 연동 설정
"""
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk
from gui.dialogs import show_info
from gui.utils import apply_icon

import config
from core.confluence_client import ConfluenceClient
from core.claude_client import test_api_key, test_cli


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("설정하는 것입니다 왓슨!!")
        self.resizable(False, False)
        self.grab_set()

        apply_icon(self)
        self._build_ui()
        self._load_settings()
        self._center(parent)

    def _center(self, parent):
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        self.geometry(f"{w}x{h}")  # 내용 기준으로 크기 고정
        pw = parent.winfo_rootx() + parent.winfo_width() // 2
        ph = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{pw - w // 2}+{ph - h // 2}")

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # ── Confluence 섹션 ──────────────────────────
        conf_frame = ttk.LabelFrame(self, text="Confluence 설정", padding=10)
        conf_frame.pack(fill="x", padx=16, pady=(16, 8))

        ttk.Label(conf_frame, text="Base URL").grid(row=0, column=0, sticky="w", **pad)
        self.var_url = tk.StringVar()
        ttk.Entry(conf_frame, textvariable=self.var_url, width=58).grid(row=0, column=1, **pad)
        ttk.Label(conf_frame, text="기본: https://su-nk.atlassian.net/", foreground="gray").grid(
            row=1, column=1, sticky="w", padx=12
        )

        ttk.Label(conf_frame, text="이메일").grid(row=2, column=0, sticky="w", **pad)
        self.var_email = tk.StringVar()
        ttk.Entry(conf_frame, textvariable=self.var_email, width=58).grid(row=2, column=1, **pad)

        ttk.Label(conf_frame, text="API Token").grid(row=3, column=0, sticky="w", **pad)
        self.var_token = tk.StringVar()
        ttk.Entry(conf_frame, textvariable=self.var_token, show="*", width=58).grid(row=3, column=1, **pad)
        hint_frame = ttk.Frame(conf_frame)
        hint_frame.grid(row=4, column=1, sticky="w", padx=12)
        ttk.Label(hint_frame, text="Atlassian 계정 설정 > API Token에서 발급", foreground="gray").pack(side="left", padx=(0, 8))
        ttk.Button(hint_frame, text="API Token 발급받기",
                   command=lambda: webbrowser.open("https://id.atlassian.com/manage-profile/security/api-tokens")
                   ).pack(side="left")

        conf_action = ttk.Frame(conf_frame)
        conf_action.grid(row=5, column=0, columnspan=2, sticky="ew", padx=12, pady=4)
        self.lbl_conf_status = ttk.Label(conf_action, text="")
        self.lbl_conf_status.pack(side="left")
        ttk.Button(conf_action, text="연결 테스트", command=self._test_confluence).pack(side="right")

        # ── Claude 섹션 ──────────────────────────────
        claude_frame = ttk.LabelFrame(self, text="Claude 설정", padding=10)
        claude_frame.pack(fill="x", padx=16, pady=8)

        # 연동 방식 선택
        ttk.Label(claude_frame, text="연동 방식").grid(row=0, column=0, sticky="w", **pad)
        self.var_mode = tk.StringVar(value="cli")
        mode_frame = ttk.Frame(claude_frame)
        mode_frame.grid(row=0, column=1, sticky="w", padx=12, pady=6)
        ttk.Radiobutton(mode_frame, text="Claude Code CLI (설치된 경우)", variable=self.var_mode,
                        value="cli", command=self._on_mode_change).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(mode_frame, text="API Key", variable=self.var_mode,
                        value="api", command=self._on_mode_change).pack(side="left")

        # CLI 테스트 버튼
        cli_action = ttk.Frame(claude_frame)
        cli_action.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=2)
        self.lbl_cli_status = ttk.Label(cli_action, text="")
        self.lbl_cli_status.pack(side="left")
        self.btn_test_cli = ttk.Button(cli_action, text="CLI 확인", command=self._test_cli)
        self.btn_test_cli.pack(side="left", padx=(8, 0))

        # API Key 입력 (CLI 선택 시 비활성)
        ttk.Label(claude_frame, text="API Key").grid(row=2, column=0, sticky="w", **pad)
        self.var_claude_key = tk.StringVar()
        self.entry_api_key = ttk.Entry(claude_frame, textvariable=self.var_claude_key, show="*", width=58)
        self.entry_api_key.grid(row=2, column=1, **pad)
        self.lbl_api_hint = ttk.Label(claude_frame, text="console.anthropic.com에서 발급", foreground="gray")
        self.lbl_api_hint.grid(row=3, column=1, sticky="w", padx=12)

        api_action = ttk.Frame(claude_frame)
        api_action.grid(row=4, column=0, columnspan=2, sticky="ew", padx=12, pady=4)
        self.lbl_api_status = ttk.Label(api_action, text="")
        self.lbl_api_status.pack(side="left")
        self.btn_test_api = ttk.Button(api_action, text="키 확인", command=self._test_claude_api)
        self.btn_test_api.pack(side="right")

        # ── 하단 버튼 ────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=16, pady=(8, 16))

        ttk.Button(btn_frame, text="저장", command=self._save, width=12).pack(side="right", padx=4)
        ttk.Button(btn_frame, text="취소", command=self.destroy, width=12).pack(side="right", padx=4)

    def _on_mode_change(self):
        is_api = self.var_mode.get() == "api"
        state = "normal" if is_api else "disabled"
        self.entry_api_key.config(state=state)
        self.btn_test_api.config(state=state)
        self.btn_test_cli.config(state="normal" if not is_api else "disabled")

    def _load_settings(self):
        cfg = config.load_all()
        self.var_url.set(cfg.get("confluence_base_url", "https://su-nk.atlassian.net/"))
        self.var_email.set(cfg.get("confluence_email", ""))
        self.var_token.set(cfg.get("confluence_api_token", ""))
        self.var_claude_key.set(cfg.get("claude_api_key", ""))
        self.var_mode.set(cfg.get("claude_mode", "cli"))
        self._on_mode_change()

    def _test_confluence(self):
        self.lbl_conf_status.config(text="확인 중인 것입니다!", foreground="gray")
        self.update()

        def run():
            try:
                client = ConfluenceClient(self.var_url.get(), self.var_email.get(), self.var_token.get())
                ok, msg = client.test_connection()
            except Exception as e:
                ok, msg = False, str(e)
            color = "#2e7d32" if ok else "#c62828"
            self.after(0, lambda: self.lbl_conf_status.config(text=msg, foreground=color))

        threading.Thread(target=run, daemon=True).start()

    def _test_cli(self):
        self.lbl_cli_status.config(text="확인 중인 것입니다!", foreground="gray")
        self.btn_test_cli.config(state="disabled")
        self.update()

        def run():
            ok, msg = test_cli()
            color = "#2e7d32" if ok else "#c62828"
            self.after(0, lambda: self.lbl_cli_status.config(text=msg, foreground=color))
            self.after(0, lambda: self.btn_test_cli.config(state="normal"))

        threading.Thread(target=run, daemon=True).start()

    def _test_claude_api(self):
        self.lbl_api_status.config(text="확인 중인 것입니다!", foreground="gray")
        self.update()

        def run():
            ok, msg = test_api_key(self.var_claude_key.get())
            color = "#2e7d32" if ok else "#c62828"
            self.after(0, lambda: self.lbl_api_status.config(text=msg, foreground=color))

        threading.Thread(target=run, daemon=True).start()

    def _save(self):
        config.save_all({
            "confluence_base_url": self.var_url.get().strip(),
            "confluence_email": self.var_email.get().strip(),
            "confluence_api_token": self.var_token.get().strip(),
            "claude_api_key": self.var_claude_key.get().strip(),
            "claude_mode": self.var_mode.get(),
        })
        show_info(self, "완벽합니다 왓슨!!", "설정이 저장된 것입니다!")
        self.destroy()
