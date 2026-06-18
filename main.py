"""
Confluence TC Generator - 진입점
"""
import sys
import os
import ctypes

# 패키지 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows DPI 스케일링 대응 (125%·150% 등 환경에서 레이아웃 깨짐 방지)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from gui.main_window import MainWindow
from gui.splash import show_splash


def main():
    def launch():
        app = MainWindow()
        app.mainloop()

    show_splash(on_done=launch)


if __name__ == "__main__":
    main()
