"""
Confluence Cloud API 연동 모듈
"""
import html as _html
import re
import requests
from concurrent.futures import ThreadPoolExecutor
from requests.auth import HTTPBasicAuth
from urllib.parse import unquote_plus


class ConfluenceClient:
    def __init__(self, base_url: str, email: str, api_token: str):
        base_url = base_url.strip().rstrip("/")
        if not base_url:
            raise ValueError("Confluence Base URL이 설정되지 않았습니다. 설정 화면에서 입력해주세요.")
        if not base_url.startswith("http"):
            base_url = "https://" + base_url
        self.base_url = base_url
        self.auth = HTTPBasicAuth(email, api_token)
        self.headers = {"Accept": "application/json"}

    def test_connection(self) -> tuple[bool, str]:
        """연결 테스트. (성공여부, 메시지) 반환"""
        try:
            url = f"{self.base_url}/wiki/rest/api/space"
            resp = requests.get(url, auth=self.auth, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                return True, "연결 성공인 것입니다!"
            elif resp.status_code == 401:
                return False, "인증 실패인 것입니다!: 이메일 또는 API Token을 확인해야 하는 것입니다!"
            else:
                return False, f"연결 실패인 것입니다! (HTTP {resp.status_code})"
        except requests.exceptions.ConnectionError:
            return False, "연결 실패인 것입니다!: URL을 확인해야 하는 것입니다!"
        except Exception as e:
            return False, f"오류인 것입니다!: {e}"

    def get_page_title(self, page_url: str) -> str:
        """페이지 제목만 조회 (미리보기용, 본문/이미지 처리 없음)"""
        page_id = self._resolve_page_id(page_url)
        url = f"{self.base_url}/wiki/rest/api/content/{page_id}"
        resp = requests.get(url, auth=self.auth, headers=self.headers,
                            params={"expand": "title"}, timeout=15)
        resp.raise_for_status()
        return resp.json().get("title", "")

    def get_page_content(self, page_url: str, api_key: str = "") -> tuple[str, str]:
        """
        Confluence 페이지 URL에서 본문 텍스트를 추출
        api_key 있으면 이미지를 Haiku로 설명 텍스트로 변환, 없으면 파일명 플레이스홀더 삽입
        반환: (페이지 제목, 본문 텍스트)
        """
        page_id = self._resolve_page_id(page_url)

        url = f"{self.base_url}/wiki/rest/api/content/{page_id}"
        params = {"expand": "body.storage,title"}
        resp = requests.get(url, auth=self.auth, headers=self.headers, params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        title = data.get("title", "")
        body_storage = data.get("body", {}).get("storage", {}).get("value", "")

        # 이미지 태그를 설명 텍스트로 치환 (strip 전에 처리)
        filenames = self._extract_image_filenames(body_storage)
        descriptions: dict[str, str] = {}
        if filenames and api_key:
            from core.claude_client import describe_image

            def _describe(fname: str) -> tuple[str, str]:
                result = self._fetch_attachment_bytes(page_id, fname)
                if result:
                    img_bytes, media_type = result
                    try:
                        return fname, describe_image(api_key, img_bytes, media_type, fname)
                    except Exception:
                        pass
                return fname, f"[이미지: {fname}]"

            with ThreadPoolExecutor(max_workers=4) as executor:
                for fname, desc in executor.map(_describe, filenames):
                    descriptions[fname] = desc
        body_storage = self._replace_image_tags(body_storage, descriptions)

        # HTML/XML 태그 제거하여 순수 텍스트 추출
        plain_text = self._strip_tags(body_storage)
        return title, plain_text

    def _extract_image_filenames(self, html: str) -> list[str]:
        """Storage Format XML에서 첨부 이미지 파일명 추출 (순서 유지, 중복 제거)"""
        seen = set()
        result = []
        for fname in re.findall(r'ri:filename="([^"]+)"', html):
            if fname not in seen:
                seen.add(fname)
                result.append(fname)
        return result

    def _fetch_attachment_bytes(self, page_id: str, filename: str) -> tuple[bytes, str] | None:
        """첨부파일 바이너리 다운로드. (bytes, media_type) 반환, 실패 시 None."""
        try:
            url = f"{self.base_url}/wiki/rest/api/content/{page_id}/child/attachment"
            params = {"filename": filename, "expand": "version"}
            resp = requests.get(url, auth=self.auth, headers=self.headers, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            results = resp.json().get("results", [])
            if not results:
                return None
            download_path = results[0]["_links"]["download"]
            media_type = results[0].get("metadata", {}).get("mediaType", "image/png")
            dl = requests.get(f"{self.base_url}/wiki{download_path}", auth=self.auth, timeout=30)
            if dl.status_code != 200:
                return None
            return dl.content, media_type
        except Exception:
            return None

    def _replace_image_tags(self, html: str, descriptions: dict[str, str]) -> str:
        """<ac:image> 블록을 설명 텍스트(또는 파일명 플레이스홀더)로 교체"""
        def replacer(m):
            fname_match = re.search(r'ri:filename="([^"]+)"', m.group(0))
            if fname_match:
                fname = fname_match.group(1)
                desc = descriptions.get(fname, f"[이미지: {fname}]")
                return f"\n{desc}\n"
            return ""
        return re.sub(r"<ac:image[^/].*?</ac:image>|<ac:image[^>]*/>", replacer, html, flags=re.DOTALL)

    def _resolve_page_id(self, url: str) -> str:
        """URL에서 페이지 ID 반환. 추출 실패 시 ValueError 발생."""
        page_id = self._extract_page_id(url)
        if not page_id:
            page_id = self._search_page_id_by_display_url(url)
        if not page_id:
            raise ValueError(f"아무래도 기획서 링크가 잘못된 것 같습니다!\n URL : {url}")
        return page_id

    def _extract_page_id(self, url: str) -> str | None:
        """URL에서 페이지 ID 추출 (숫자 ID가 포함된 패턴)"""
        # 패턴 1: /pages/1234567890
        m = re.search(r"/pages/(\d+)", url)
        if m:
            return m.group(1)
        # 패턴 2: pageId=1234567890
        m = re.search(r"pageId=(\d+)", url)
        if m:
            return m.group(1)
        return None

    def _search_page_id_by_display_url(self, url: str) -> str | None:
        """/display/SPACE/Title 형식 URL에서 검색 API로 페이지 ID 조회"""
        m = re.search(r"/display/([^/?#]+)/([^?#]+)", url)
        if not m:
            return None
        space_key = m.group(1)
        title = unquote_plus(m.group(2))
        try:
            search_url = f"{self.base_url}/wiki/rest/api/content"
            params = {"title": title, "spaceKey": space_key, "type": "page"}
            resp = requests.get(search_url, auth=self.auth, headers=self.headers,
                                params=params, timeout=15)
            if resp.status_code != 200:
                return None
            results = resp.json().get("results", [])
            return results[0]["id"] if results else None
        except Exception:
            return None

    def _strip_tags(self, html: str) -> str:
        """HTML 태그 제거 및 텍스트 정리"""
        # 테이블 셀 구분을 줄바꿈으로
        text = re.sub(r"</t[dh]>", "\t", html)
        text = re.sub(r"</tr>", "\n", text)
        # 블록 요소 줄바꿈
        text = re.sub(r"</?(p|div|li|h[1-6]|br)[^>]*>", "\n", text)
        # 나머지 태그 제거
        text = re.sub(r"<[^>]+>", "", text)
        # HTML 엔티티 (먼저 &nbsp; → 일반 공백, 나머지는 html.unescape로 일괄 처리)
        text = text.replace("&nbsp;", " ")
        text = _html.unescape(text)
        # 연속 공백/줄바꿈 정리
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()
