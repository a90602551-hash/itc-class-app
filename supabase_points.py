"""
Supabase 포인트 연동 모듈 - requests 직접 사용 (supabase 라이브러리 우회)
"""
import datetime
import requests
import streamlit as st


def _headers() -> dict:
    key = st.secrets["supabase"]["key"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _base() -> str:
    return st.secrets["supabase"]["url"].rstrip("/") + "/rest/v1"


def find_student_by_name(name: str) -> dict | None:
    """이름으로 학생 찾기. 없으면 자동 생성."""
    url = f"{_base()}/point_students"
    res = requests.get(url, headers=_headers(), params={"name": f"eq.{name}", "limit": 1})
    res.raise_for_status()
    data = res.json()

    if data:
        return data[0]

    # 없으면 자동 생성
    ins = requests.post(url, headers=_headers(), json={"name": name, "total_points": 0})
    ins.raise_for_status()
    result = ins.json()
    return result[0] if result else None


def add_points_bulk(entries: list[dict]) -> dict[str, int]:
    """
    여러 학생 포인트를 한 번에 처리.
    entries: [{"student_id": str, "student_name": str, "point_change": int, "reason": str}, ...]
    반환: {student_name: new_total, ...}
    """
    now = datetime.datetime.now().isoformat()
    base = _base()
    hdrs = _headers()
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
    requests.post(f"{base}/point_records", headers=hdrs, json=records).raise_for_status()

    # 학생별 total_points 업데이트
    for e in entries:
        sname = e["student_name"]
        sid   = e["student_id"]
        pts   = e["point_change"]

        res = requests.get(
            f"{base}/point_students",
            headers=hdrs,
            params={"id": f"eq.{sid}", "select": "total_points", "limit": 1}
        )
        res.raise_for_status()
        current = res.json()[0]["total_points"] if res.json() else 0
        new_total = current + pts

        requests.patch(
            f"{base}/point_students",
            headers=hdrs,
            params={"id": f"eq.{sid}"},
            json={"total_points": new_total, "updated_at": now}
        ).raise_for_status()

        results[sname] = new_total

    return results
