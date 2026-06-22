"""
메인 화면
"""
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, font as tkfont
from gui.dialogs import show_error, show_warning, show_info
from gui.utils import apply_icon, apply_dpi_scaling
from pathlib import Path
from paths import resource, userfile

import config
from core.confluence_client import ConfluenceClient
from core.claude_client import generate_tc
from core.xlsx_writer import write_tc
from gui.settings_window import SettingsWindow


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        apply_dpi_scaling(self)
        self._apply_fonts()
        self.title("NovelTCC")
        self.resizable(False, False)
        apply_icon(self)
        self._build_ui()
        self._load_output_dir()
        self._check_settings()

    def _apply_fonts(self):
        """한국어 가독성을 위해 기본 폰트를 맑은 고딕 10pt로 설정"""
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkCaptionFont"):
            try:
                f = tkfont.nametofont(name)
                f.configure(family="맑은 고딕", size=10)
            except Exception:
                pass

    def _build_ui(self):
        # ── 배너 ─────────────────────────────────────
        banner_path = resource("gui/assets/banner.png")
        if banner_path.exists():
            self._banner = tk.PhotoImage(file=str(banner_path))
            tk.Label(self, image=self._banner, bd=0).pack(fill="x")

        # ── 상단 안내 문구 + 설정 버튼 ──────────────
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", padx=16, pady=(12, 0))
        ttk.Label(top_frame, text="처음 온 왓슨은 옆 설정 버튼을 누르는 것입니다!",
                  foreground="gray").pack(side="left")
        ttk.Button(top_frame, text="설정", command=self._open_settings, width=8).pack(side="right")

        # ── Confluence URL 입력 ──────────────────────
        url_frame = ttk.LabelFrame(self, text="기획서 URL", padding=10)
        url_frame.pack(fill="x", padx=16, pady=(16, 8))

        self.var_page_url = tk.StringVar()
        url_row = ttk.Frame(url_frame)
        url_row.pack(fill="x")
        ttk.Entry(url_row, textvariable=self.var_page_url, width=74).pack(side="left", padx=(0, 8))
        ttk.Button(url_row, text="조회", command=self._preview_page).pack(side="left")
        ttk.Label(url_frame, text="Confluence 기획서 URL을 넣고 조회 하는 것입니다!",
                  foreground="gray").pack(anchor="w", pady=(4, 0))

        # ── 출력 경로 ────────────────────────────────
        out_frame = ttk.LabelFrame(self, text="출력 파일", padding=10)
        out_frame.pack(fill="x", padx=16, pady=8)

        self.var_output_path = tk.StringVar()
        out_row = ttk.Frame(out_frame)
        out_row.pack(fill="x")
        ttk.Entry(out_row, textvariable=self.var_output_path, width=66).pack(side="left", padx=(0, 8))
        ttk.Button(out_row, text="찾아보기", command=self._browse_output).pack(side="left")
        ttk.Label(out_frame, text="작성된 TC를 어디에 생성할지 정하는 것입니다!",
                  foreground="gray").pack(anchor="w", pady=(4, 0))

        # ── 실행 버튼 ────────────────────────────────
        self.btn_generate = ttk.Button(
            self, text="TC 생성 시작", command=self._start_generate, width=20
        )
        self.btn_generate.pack(pady=10)

        # ── 진행 로그 ────────────────────────────────
        log_frame = ttk.LabelFrame(self, text="진행 로그", padding=10)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.log_text = tk.Text(log_frame, height=12, width=82, state="disabled",
                                bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9))
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # 진행 바
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=500)
        self.progress.pack(pady=(0, 12))

    def _load_output_dir(self):
        default_path = userfile("TC_Result.xlsx")
        self.var_output_path.set(str(default_path))

    def _check_settings(self):
        cfg = config.load_all()
        missing = []
        if not cfg.get("confluence_base_url"):
            missing.append("Confluence Base URL")
        if cfg.get("claude_mode", "cli") == "api" and not cfg.get("claude_api_key"):
            missing.append("Claude API Key")
        if missing:
            self.log(f"[안내] 설정이 필요한 것입니다!: {', '.join(missing)} → 상단 메뉴 > 설정")

    def _open_settings(self):
        SettingsWindow(self)

    def _preview_page(self):
        url = self.var_page_url.get().strip()
        if not url:
            show_warning(self, "왓슨!!", "Confluence 페이지 URL을 입력해야 하는 것입니다!")
            return

        cfg = config.load_all()
        if not cfg.get("confluence_base_url"):
            show_warning(self, "왓슨!!", "설정에서 Confluence Base URL을 먼저 입력해야 하는 것입니다!")
            return

        self.log("기획서 제목 조회 중인 것입니다!")
        self.progress.start()

        def run():
            try:
                client = ConfluenceClient(
                    cfg["confluence_base_url"], cfg["confluence_email"], cfg["confluence_api_token"]
                )
                title = client.get_page_title(url)
                self.after(0, lambda: self.log(f"[조회 완료] {title}"))
                self.after(0, lambda: self.log('왓슨은 저만 믿으시고 "TC 생성 시작" 버튼을 누르는 것입니다!'))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self.log(f"[오류] {err}"))
            finally:
                self.after(0, self.progress.stop)

        threading.Thread(target=run, daemon=True).start()

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel 파일", "*.xlsx")],
            initialfile=Path(self.var_output_path.get()).name,
            title="출력 파일 경로 선택",
        )
        if path:
            self.var_output_path.set(path)
            config.save_value("output_dir", str(Path(path).parent))

    def _start_generate(self):
        url = self.var_page_url.get().strip()
        output = self.var_output_path.get().strip()

        if not url:
            show_warning(self, "왓슨!!", "Confluence 페이지 URL을 입력해야 하는 것입니다!")
            return
        if not output:
            show_warning(self, "왓슨!!", "출력 파일 경로를 지정해야 하는 것입니다!")
            return

        cfg = config.load_all()
        missing = []
        if not cfg.get("confluence_base_url"):
            missing.append("Confluence Base URL")
        if cfg.get("claude_mode", "cli") == "api" and not cfg.get("claude_api_key"):
            missing.append("Claude API Key")
        if missing:
            show_error(self, "왓슨!!", f"다음 설정을 완료해야 하는 것입니다!:\n- " + "\n- ".join(missing))
            return

        self.btn_generate.config(state="disabled")
        self.progress.start()
        self.log("=" * 50)
        self.log("TC 생성 시작인 것입니다!")

        def run():
            try:
                # 1. Confluence 기획서 불러오기
                self.after(0, lambda: self.log("Confluence 기획서 불러오는 중인 것입니다!"))
                client = ConfluenceClient(
                    cfg["confluence_base_url"], cfg["confluence_email"], cfg["confluence_api_token"]
                )
                title, content = client.get_page_content(url, api_key=cfg.get("claude_api_key", ""))
                self.after(0, lambda: self.log(f"  ✔ 기획서 로드 완료된 것입니다!: {title} ({len(content)}자)"))

                # 2. Claude API로 TC 생성
                self.after(0, lambda: self.log("Claude API로 TC 설계 중인 것입니다! (시간이 걸릴 수 있는 것입니다!)"))

                def on_progress(msg):
                    self.after(0, lambda: self.log(f"  {msg}"))

                tc_list = generate_tc(
                    title, content,
                    mode=cfg.get("claude_mode", "cli"),
                    api_key=cfg.get("claude_api_key", ""),
                    on_progress=on_progress,
                )
                self.after(0, lambda: self.log(f"  ✔ TC {len(tc_list)}개 생성 완료된 것입니다!"))

                # 3. xlsx 저장
                self.after(0, lambda: self.log("xlsx 파일 작성 중인 것입니다!"))
                saved_path = write_tc(tc_list, output, title)
                self.after(0, lambda: self.log(f"  ✔ 저장 완료된 것입니다!: {saved_path}"))
                self.after(0, lambda: show_info(
                    self, "사건 해결인 것입니다!", f"테스트 케이스 {len(tc_list)}개를 설계한 것입니다!",
                    action=("파일 위치 열기", lambda: subprocess.Popen(f'explorer /select,"{saved_path}"', shell=True))
                ))

            except Exception as e:
                err = str(e)
                self.after(0, lambda: self.log(f"[오류] {err}"))
                self.after(0, lambda: show_error(self, "문제가 발생한 것입니다...", err))
            finally:
                self.after(0, self.progress.stop)
                self.after(0, lambda: self.btn_generate.config(state="normal"))

        threading.Thread(target=run, daemon=True).start()

    def log(self, msg: str):
        line = msg if msg.strip("=") == "" else f"노벨 : {msg}"
        self.log_text.config(state="normal")
        self.log_text.insert("end", line + "\n")
        # 500줄 초과 시 오래된 로그 정리
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 500:
            self.log_text.delete("1.0", f"{lines - 499}.0")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
