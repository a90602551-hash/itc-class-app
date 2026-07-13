"""
The Fluent 콘텐츠 연동 모듈
kids-learning-platform API에서 단어/표현/문법 가져오기
"""
import requests

FLUENT_BASE_URL = "https://kids-learning-platform-ivpg.vercel.app"

def fetch_fluent_content(level: int, unit: int) -> dict:
    """
    The Fluent에서 레벨/유닛 콘텐츠 가져오기.
    반환: {"title": str, "words": [...], "expressions": [...], "grammar": str}
    """
    try:
        resp = requests.get(
            f"{FLUENT_BASE_URL}/api/content",
            params={"level": level, "unit": unit},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "title":       data.get("title", ""),
            "words":       data.get("words", []),
            "expressions": data.get("expressions", []),
            "grammar":     data.get("grammar", ""),
        }
    except Exception as e:
        return {
            "title":       "",
            "words":       [],
            "expressions": [],
            "grammar":     f"[The Fluent 연동 오류: {e}]",
        }
