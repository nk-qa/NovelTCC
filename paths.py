"""
경로 헬퍼 - 개발 환경 / 폴더 배포 exe 환경 양쪽 대응

폴더째 배포 방식이므로 exe와 모든 파일이 같은 프로젝트 폴더에 위치.
- frozen 시: exe 파일이 있는 폴더(= 프로젝트 루트)를 기준으로 읽음
- 개발 시:   paths.py가 있는 폴더(= 프로젝트 루트)를 기준으로 읽음
"""
import sys
from pathlib import Path


def _base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent  # exe 위치 = 프로젝트 폴더
    return Path(__file__).parent            # 개발 시 프로젝트 루트


def resource(relative: str) -> Path:
    """에셋, 템플릿 등 읽기 전용 파일 경로"""
    return _base() / relative


def userfile(relative: str) -> Path:
    """출력 파일, prompt.md 등 사용자 읽기/쓰기 파일 경로"""
    return _base() / relative
