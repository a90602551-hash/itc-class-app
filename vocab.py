import re
import requests
from bs4 import BeautifulSoup
from config import ITC_URL


def fetch_lesson_content(level: int, lesson: int) -> dict:
    """
    ITC 웹사이트에서 해당 레벨/레슨의 단어와 표현을 가져옴.
    반환: {"words": [...], "expressions": [...]}
    """
    url = ITC_URL.format(level=level, lesson=lesson)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except Exception as e:
        return {"words": [], "expressions": [], "error": str(e)}

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text("\n")

    words = _parse_section(text, "NEW WORDS", "NEW EXPRESSIONS")
    expressions = _parse_section(text, "NEW EXPRESSIONS", "DIALOGUE")

    return {"words": words, "expressions": expressions}


def _parse_section(text: str, start_marker: str, end_marker: str) -> list[str]:
    """섹션 사이의 번호 매겨진 항목 추출"""
    try:
        start = text.index(start_marker) + len(start_marker)
        end = text.index(end_marker, start) if end_marker in text[start:] else len(text)
        section = text[start:end]
    except ValueError:
        return []

    # "1. word - 뜻" 또는 "1. word 뜻" 형태 파싱
    items = []
    # 번호로 시작하는 줄 찾기
    lines = [l.strip() for l in section.split("\n") if l.strip()]
    for line in lines:
        # 숫자. 으로 시작하는 항목
        m = re.match(r"^\d+\.\s+(.+)", line)
        if m:
            items.append(m.group(1).strip())

    return items
