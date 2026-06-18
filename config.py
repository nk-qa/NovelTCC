"""
설정 저장/불러오기 모듈
- API Key 등 민감 정보는 OS keyring에 저장
- 나머지 설정은 ~/.tc_generator/config.json에 저장
"""
import json
from pathlib import Path

import keyring

SERVICE_NAME = "confluence_tc_generator"
CONFIG_DIR = Path.home() / ".tc_generator"
CONFIG_FILE = CONFIG_DIR / "config.json"

_KEYRING_KEYS = {"claude_api_key", "confluence_api_token"}

_DEFAULTS = {
    "confluence_base_url": "",
    "confluence_email": "",
    "output_dir": str(Path.home() / "Desktop"),
}


def _load_json() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_json(data: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get(key: str) -> str:
    if key in _KEYRING_KEYS:
        return keyring.get_password(SERVICE_NAME, key) or ""
    data = _load_json()
    return data.get(key, _DEFAULTS.get(key, ""))


def save_value(key: str, value: str):
    if key in _KEYRING_KEYS:
        keyring.set_password(SERVICE_NAME, key, value)
    else:
        data = _load_json()
        data[key] = value
        _save_json(data)


def save_all(settings: dict):
    """settings 딕셔너리 전체를 한 번에 저장"""
    json_data = _load_json()
    for key, value in settings.items():
        if key in _KEYRING_KEYS:
            keyring.set_password(SERVICE_NAME, key, value)
        else:
            json_data[key] = value
    _save_json(json_data)


def load_all() -> dict:
    """모든 설정을 딕셔너리로 반환"""
    data = _load_json()
    result = {**_DEFAULTS, **data}
    for key in _KEYRING_KEYS:
        result[key] = keyring.get_password(SERVICE_NAME, key) or ""
    return result
