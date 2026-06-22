"""
Claude 연동 모듈 - API Key 방식 / Claude Code CLI 방식 지원
"""
import base64
import json
import os
import re
import subprocess
import tempfile
import threading
import time
import anthropic
from paths import userfile

PROMPT_MD_PATH = userfile("prompt.md")

SYSTEM_PROMPT = """당신은 게임 QA 전문가입니다.
주어진 게임 기획서를 분석하여 테스트 케이스를 설계하는 것이 역할입니다.

## 출력 규칙
- 반드시 JSON 배열 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.
- 각 항목은 아래 구조를 따릅니다:
  {
    "대분류": "기능 영역 (예: 전투, UI, 캐릭터)",
    "중분류": "세부 영역 (예: 스킬, 인벤토리)",
    "소분류": "구체적 항목 (예: 스킬 발동, 아이템 획득)",
    "확인 항목": "테스트 시나리오 또는 확인해야 할 내용",
    "비고": "해당 TC가 [이미지 설명: ...] 내용을 근거로 작성된 경우에만 \"이미지 참조\" 입력, 그 외에는 빈 문자열"
  }

## TC 설계 원칙
- 정상 동작(Happy Path) 케이스를 먼저 작성
- 기획서에 명시된 조건과 수치를 TC에 반영하되, 명시되지 않은 암묵적 예외(상태 충돌, 자원 부족, 권한 없음, 연속 입력, 비정상 순서 등)를 적극 도출
- 경계값(최솟값·최댓값·초과값) 및 엣지 케이스를 포함
- 해당 기능에서 발생 가능한 모든 실패 시나리오를 케이스화할 것
- 리소스(이미지, 사운드, 애니메이션 등)가 포함된 기능은 HD/SD 그래픽 옵션 환경 각각에서 동작을 확인하는 케이스를 포함
- 게임 QA 관점에서 놓치기 쉬운 케이스(멀티 플랫폼, 네트워크 끊김, 동시성 등) 포함
- 대분류 > 중분류 > 소분류 순으로 논리적 계층을 유지"""


def _load_extra_prompt() -> str:
    """prompt.md가 존재하면 내용 반환, 없으면 빈 문자열"""
    if PROMPT_MD_PATH.exists():
        return "\n\n## 추가 TC 설계 지침\n" + PROMPT_MD_PATH.read_text(encoding="utf-8")
    return ""


def _build_user_message(title: str, content: str) -> str:
    return f"""다음 기획서를 분석하여 테스트 케이스를 설계해주세요.

## 기획서 제목
{title}

## 기획서 내용
{content}

위 기획서를 바탕으로 QA 테스트 케이스를 JSON 배열 형식으로 작성해주세요."""


def _parse_response(raw: str) -> list[dict]:
    """Claude 응답에서 JSON 배열 추출. max_tokens 초과로 잘린 경우 복구 시도."""
    raw = raw.strip()
    # ```json ... ``` 블록 대응
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            if part.startswith("json"):
                part = part[4:]
            part = part.strip()
            if part.startswith("["):
                raw = part
                break

    # JSON 배열 시작점: [{ 또는 [ ] 패턴만 인식 (이미지 설명 등 [텍스트] 오인식 방지)
    m = re.search(r'\[(\s*\{|\s*\])', raw)
    if not m:
        preview = raw[:300] if len(raw) > 300 else raw
        raise ValueError(f"Claude 응답에서 JSON 배열을 찾을 수 없는 것입니다.\n\n[응답 내용]\n{preview}")

    json_str = raw[m.start():]

    # 1차 시도: 정상 파싱
    end = json_str.rfind("]")
    if end != -1:
        try:
            tc_list = json.loads(json_str[:end + 1])
            if isinstance(tc_list, list):
                return tc_list
        except json.JSONDecodeError:
            pass

    # 2차 시도: 응답 잘림 복구 - 마지막 완전한 객체까지만 추출
    last_obj = json_str.rfind("},")
    if last_obj == -1:
        last_obj = json_str.rfind("}")
    if last_obj != -1:
        try:
            recovered = json_str[:last_obj + 1] + "]"
            tc_list = json.loads(recovered)
            if isinstance(tc_list, list) and tc_list:
                return tc_list
        except json.JSONDecodeError:
            pass

    preview = raw[:300] if len(raw) > 300 else raw
    raise ValueError(f"Claude 응답에서 JSON 배열을 찾을 수 없는 것입니다.\n\n[응답 내용]\n{preview}")


# ── API Key 방식 ──────────────────────────────────────────────────────────────

def _count_complete_objects(text: str) -> int:
    """스트리밍 버퍼에서 완성된 JSON 객체 수 반환 (진행률 표시용)"""
    count = 0
    depth = 0
    in_str = False
    esc = False
    for ch in text:
        if esc:
            esc = False
            continue
        if ch == '\\' and in_str:
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                count += 1
    return count


def generate_tc_api(api_key: str, title: str, content: str, extra_prompt: str = "", on_progress=None) -> list[dict]:
    client = anthropic.Anthropic(api_key=api_key)
    if on_progress:
        on_progress("Claude API 스트리밍 시작인 것입니다!")

    full_text = ""
    last_reported = 0
    chars_since_check = 0

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        system=SYSTEM_PROMPT + extra_prompt,
        messages=[{"role": "user", "content": _build_user_message(title, content)}],
    ) as stream:
        for delta in stream.text_stream:
            full_text += delta
            chars_since_check += len(delta)
            # 50자마다 완성된 TC 객체 수 체크 → 변화 있을 때만 알림
            if chars_since_check >= 50:
                chars_since_check = 0
                tc_count = _count_complete_objects(full_text)
                if on_progress and tc_count > last_reported:
                    last_reported = tc_count
                    on_progress(f"TC {tc_count}개 작성 중인 것입니다...")

    if not full_text:
        raise ValueError("Claude API 응답이 비어있는 것입니다.")

    if on_progress:
        on_progress("응답 파싱 중인 것입니다!")
    return _parse_response(full_text)


def test_api_key(api_key: str) -> tuple[bool, str]:
    try:
        client = anthropic.Anthropic(api_key=api_key)
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "hi"}],
        )
        return True, "API Key 확인 완료인 것입니다!"
    except anthropic.AuthenticationError:
        return False, "유효하지 않은 API Key인 것입니다!"
    except anthropic.BadRequestError as e:
        if "credit balance is too low" in str(e):
            return True, "API Key 유효한 것입니다! (크레딧 부족 - billing에서 충전 필요한 것입니다!)"
        return False, f"오류: {e}"
    except Exception as e:
        return False, f"오류: {e}"


# ── Claude Code CLI 방식 ──────────────────────────────────────────────────────

def generate_tc_cli(title: str, content: str, extra_prompt: str = "", on_progress=None) -> list[dict]:
    prompt = f"{SYSTEM_PROMPT}{extra_prompt}\n\n{_build_user_message(title, content)}"

    if on_progress:
        on_progress("Claude Code CLI 호출 중인 것입니다!")

    # CI=true: TUI/스피너 비활성화 → exe 환경에서 hang 방지
    env = os.environ.copy()
    env["CI"] = "true"
    env["NO_COLOR"] = "1"

    tmp_path = None
    try:
        # stdin=PIPE 방식은 Windows shell=True 환경에서 claude에 전달이 불안정하므로
        # 임시 파일 리디렉션 방식 사용
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", encoding="utf-8", delete=False) as tmp:
            tmp.write(prompt)
            tmp_path = tmp.name

        proc = subprocess.Popen(
            f'claude --print --dangerously-skip-permissions < "{tmp_path}"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
        )

        stdout_buf, stderr_buf = [], []
        t_stdout = threading.Thread(target=lambda: stdout_buf.append(proc.stdout.read()), daemon=True)
        t_stderr = threading.Thread(target=lambda: stderr_buf.append(proc.stderr.read()), daemon=True)
        t_stdout.start()
        t_stderr.start()

        # 진행 상황 폴링
        timeout = 1200
        notify_start = 60
        notify_interval = 60
        start = time.time()
        last_tick = -1

        while proc.poll() is None:
            elapsed = time.time() - start
            if elapsed > timeout:
                proc.kill()
                raise RuntimeError("Claude CLI 응답 시간이 초과된 것입니다! (20분)")
            tick = int((elapsed - notify_start) // notify_interval)
            if on_progress and tick >= 0 and tick != last_tick and elapsed >= notify_start:
                last_tick = tick
                on_progress(f"기획서 내용이 많아서 좀 더 걸리는 것입니다..! ({int(elapsed // 60)}분 경과 중인 것입니다)")
            time.sleep(1)

        # 프로세스 종료 후 stdout/stderr 읽기 스레드 완료 대기 (race condition 방지)
        t_stdout.join()
        t_stderr.join()

        stdout_data = "".join(stdout_buf)
        stderr_data = "".join(stderr_buf)

        if proc.returncode != 0:
            raise RuntimeError(f"CLI 오류: {stderr_data.strip()}")

        if on_progress:
            on_progress("응답 파싱 중인 것입니다!")
        return _parse_response(stdout_data)

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def test_cli() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            'echo respond with only: ok | claude --print --dangerously-skip-permissions',
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        if result.returncode == 0 and "ok" in result.stdout.lower():
            return True, "Claude Code CLI 사용 가능한 것입니다!"
        return False, f"CLI 응답 오류인 것입니다!: {result.stderr.strip()}"
    except FileNotFoundError:
        return False, "claude 명령어를 찾을 수 없는 것입니다! Claude Code가 설치되어 있는지 확인해야 하는 것입니다!"
    except Exception as e:
        return False, f"오류: {e}"


# ── Haiku 이미지 설명 ─────────────────────────────────────────────────────────

def describe_image(api_key: str, image_bytes: bytes, media_type: str, filename: str) -> str:
    """claude-haiku로 이미지를 QA 관점 텍스트로 요약"""
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64.standard_b64encode(image_bytes).decode("utf-8"),
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "이 이미지는 게임 기획서의 첨부 파일입니다.\n"
                        "QA 테스트케이스 작성에 필요한 정보(UI 구성 요소, 수치, 조건, 상태 흐름)를 "
                        "3문장 이내로 간략히 설명하세요. 한국어로 답하세요."
                    ),
                },
            ],
        }],
    )
    return f"[이미지 설명: {resp.content[0].text.strip()}]"


# ── 통합 진입점 ───────────────────────────────────────────────────────────────

def generate_tc(title: str, content: str, mode: str = "cli",
                api_key: str = "", on_progress=None) -> list[dict]:
    """
    mode: "cli" → Claude Code CLI 사용
          "api" → Anthropic API Key 사용
    """
    extra = _load_extra_prompt()
    if mode == "api":
        return generate_tc_api(api_key, title, content, extra, on_progress)
    else:
        return generate_tc_cli(title, content, extra, on_progress)
