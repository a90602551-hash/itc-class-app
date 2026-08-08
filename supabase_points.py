"""
Supabase 포인트 연동 모듈 (Firebase 대체)
"""
import datetime
from supabase import create_client, Client

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is not None:
        return _client

    import streamlit as st
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    _client = create_client(url, key)
    return _client


# 학생 이름 → 레코드 캐시
_student_cache: dict[str, dict | None] = {}


def find_student_by_name(name: str) -> dict | None:
    """이름으로 학생 찾기. 없으면 자동 생성."""
    if name in _student_cache:
        return _student_cache[name]

    db = _get_client()
    res = db.table("point_students").select("*").eq("name", name).limit(1).execute()

    if res.data:
        result = res.data[0]
    else:
        # 없으면 자동 생성
        ins = db.table("point_students").insert({"name": name, "total_points": 0}).execute()
        result = ins.data[0] if ins.data else None

    _student_cache[name] = result
    return result


def add_points_bulk(entries: list[dict]) -> dict[str, int]:
    """
    여러 학생 포인트를 한 번에 처리.
    entries: [{"student_id": str, "student_name": str, "point_change": int, "reason": str}, ...]
    반환: {student_name: new_total, ...}
    """
    db = _get_client()
    now = datetime.datetime.now().isoformat()
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
    db.table("point_records").insert(records).execute()

    # 학생별 total_points 업데이트
    for e in entries:
        sname = e["student_name"]
        sid   = e["student_id"]
        pts   = e["point_change"]

        res = db.table("point_students").select("total_points").eq("id", sid).single().execute()
        current = res.data["total_points"] if res.data else 0
        new_total = current + pts

        db.table("point_students").update({
            "total_points": new_total,
            "updated_at": now,
        }).eq("id", sid).execute()

        _student_cache.pop(sname, None)
        results[sname] = new_total

    return results
