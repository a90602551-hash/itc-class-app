"""
Supabase 포인트 연동 모듈 - requests 직접 사용
"""
import datetime
import json
from urllib.parse import quote
import requests
import streamlit as st


def _headers() -> dict:
    key = st.secrets["supabase"]["key"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json; charset=utf-8",
        "Prefer": "return=representation",
    }


def _base() -> str:
    return st.secrets["supabase"]["url"].rstrip("/") + "/rest/v1"


def _get(url: str, params: dict) -> list:
    """GET 요청 - 쿼리 파라미터 한글 안전 처리"""
    qs = "&".join(f"{k}={quote(str(v), safe='=.')}" for k, v in params.items())
    res = requests.get(f"{url}?{qs}", headers=_headers())
    res.raise_for_status()
    return res.json()


def _post(url: str, body) -> list:
    """POST 요청 - UTF-8 명시 직렬화"""
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    res = requests.post(url, headers=_headers(), data=data)
    res.raise_for_status()
    return res.json()


def _patch(url: str, params: dict, body: dict):
    """PATCH 요청 - UTF-8 명시 직렬화"""
    qs = "&".join(f"{k}={quote(str(v), safe='=.')}" for k, v in params.items())
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    res = requests.patch(f"{url}?{qs}", headers=_headers(), data=data)
    res.raise_for_status()
    return res.json()


def find_student_by_name(name: str) -> dict | None:
    """이름으로 학생 찾기. 없으면 자동 생성."""
    url = f"{_base()}/point_students"
    data = _get(url, {"name": f"eq.{name}", "limit": "1"})

    if data:
        return data[0]

    # 없으면 자동 생성
    result = _post(url, {"name": name, "total_points": 0})
    return result[0] if result else None


def add_points_bulk(entries: list[dict]) -> dict[str, int]:
    """
    여러 학생 포인트를 한 번에 처리.
    entries: [{"student_id": str, "student_name": str, "point_change": int, "reason": str}, ...]
    반환: {student_name: new_total, ...}
    """
    now = datetime.datetime.now().isoformat()
    base = _base()
    results = {}

    # point_records 일괄 삽입
    records = [
        {
            "student_id":   e["student_id"],
            "student_name": e["student_name"],
            "point_change": e["point_change"],
            "reason":       e["reason"],
            "category":     e.get("category", "수업포인트"),
            "recorded_at":  now,
            "created_at":   now,
        }
        for e in entries
    ]
    _post(f"{base}/point_records", records)

    # 학생별 total_points 업데이트
    for e in entries:
        sname = e["student_name"]
        sid   = e["student_id"]
        pts   = e["point_change"]

        rows = _get(f"{base}/point_students", {"id": f"eq.{sid}", "select": "total_points", "limit": "1"})
        current = rows[0]["total_points"] if rows else 0
        new_total = current + pts

        _patch(f"{base}/point_students", {"id": f"eq.{sid}"}, {"total_points": new_total, "updated_at": now})
        results[sname] = new_total

    return results
