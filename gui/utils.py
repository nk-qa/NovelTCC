"""
GUI 공통 유틸리티
"""
import tempfile
import atexit
from pathlib import Path
from paths import resource

ICON_PNG = resource("gui/assets/icon.png")

_ico_tmp_path: str | None = None


def _get_ico_path() -> str | None:
    """PNG → 임시 ICO 변환 (Pillow 필요). 변환된 경로를 반환."""
    global _ico_tmp_path
    if _ico_tmp_path:
        return _ico_tmp_path
    if not ICON_PNG.exists():
        return None
    try:
        from PIL import Image
        img = Image.open(ICON_PNG)
        tmp = tempfile.NamedTemporaryFile(suffix=".ico", delete=False)
        tmp.close()
        img.save(tmp.name, format="ICO", sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
        _ico_tmp_path = tmp.name
        atexit.register(_cleanup_ico)
        return _ico_tmp_path
    except Exception:
        return None


def _cleanup_ico():
    if _ico_tmp_path:
        try:
            Path(_ico_tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


def apply_dpi_scaling(root):
    """실제 DPI를 읽어 tkinter 스케일을 맞춤 → 모든 해상도에서 동일한 물리적 크기 유지
    tkinter scaling 단위: 픽셀/포인트 (1포인트 = 1/72인치)
    따라서 올바른 공식 = dpi / 72
    """
    try:
        dpi = root.winfo_fpixels('1i')  # 1인치당 픽셀 수 (실제 DPI)
        scale = dpi / 72.0              # 픽셀/포인트 변환
        root.tk.call('tk', 'scaling', scale)
    except Exception:
        pass


def apply_icon(window):
    """창에 icon.png 아이콘 적용 (Pillow → iconbitmap, 폴백 → iconphoto)"""
    ico = _get_ico_path()
    if ico:
        try:
            window.iconbitmap(ico)
            return
        except Exception:
            pass
    # 폴백: Pillow 없거나 iconbitmap 실패 시
    if ICON_PNG.exists():
        try:
            import tkinter as tk
            img = tk.PhotoImage(file=str(ICON_PNG))
            window.iconphoto(True, img)
            window._icon_ref = img  # GC 방지
        except Exception:
            pass
