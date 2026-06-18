"""
스플래시 화면 - 프로그램 시작 시 페이드 인/아웃 연출
"""
import tkinter as tk
from gui.utils import apply_dpi_scaling
from paths import resource

SPLASH_IMAGE = resource("gui/assets/load.png")

FADE_IN_STEPS = 20
FADE_OUT_STEPS = 20
STEP_MS = 30       # 페이드 한 스텝 간격 (ms)
HOLD_MS = 1200     # 완전히 보이는 상태 유지 시간 (ms)


def show_splash(on_done: callable):
    """스플래시를 띄우고 완료 후 on_done() 호출"""
    root = tk.Tk()
    apply_dpi_scaling(root)
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.0)
    root.configure(bg="black")

    img = tk.PhotoImage(file=str(SPLASH_IMAGE))
    w, h = img.width(), img.height()

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")

    lbl = tk.Label(root, image=img, bd=0, bg="black")
    lbl.pack()
    lbl.image = img  # GC 방지

    def fade_in(step=0):
        alpha = step / FADE_IN_STEPS
        root.attributes("-alpha", alpha)
        if step < FADE_IN_STEPS:
            root.after(STEP_MS, fade_in, step + 1)
        else:
            root.after(HOLD_MS, fade_out)

    def fade_out(step=0):
        alpha = 1.0 - step / FADE_OUT_STEPS
        root.attributes("-alpha", alpha)
        if step < FADE_OUT_STEPS:
            root.after(STEP_MS, fade_out, step + 1)
        else:
            root.destroy()
            on_done()

    root.after(50, fade_in)
    root.mainloop()
