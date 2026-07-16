"""
Firebase Firestore 포인트 연동 모듈
the-fluent-point 프로젝트와 연동
"""
import os
import time
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google.api_core.exceptions import ResourceExhausted

_SA_FILE = os.path.join(os.path.dirname(__file__), "firebase_service_account.json")
_APP_NAME = "fluent_point"
_db = None

# 학생 이름 → {id, total_points, ...} 캐시
_student_cache: dict[str, dict | None] = {}


def _load_sa_info() -> dict:
    try:
        import streamlit as st
        if "firebase_service_account" in st.secrets:
            info = dict(st.secrets["firebase_service_account"])
            info["private_key"] = info["private_key"].replace("\\n", "\n")
            return info
    except Exception:
        pass
    import json
    with open(_SA_FILE, encoding="utf-8") as f:
        return json.load(f)


def _get_db():
    global _db
    if _db is not None:
        return _db
    try:
        app = firebase_admin.get_app(_APP_NAME)
    except ValueError:
        info = _load_sa_info()
        cred = credentials.Certificate(info)
        app = firebase_admin.initialize_app(cred, name=_APP_NAME)
    _db = firestore.client(app=app)
    return _db


def _retry(fn, retries=3, delay=2.0):
    for attempt in range(retries):
        try:
            return fn()
        except ResourceExhausted:
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                raise


def find_student_by_name(name: str) -> dict | None:
    """이름으로 학생 찾기 (캐시 우선)"""
    if name in _student_cache:
        return _student_cache[name]
    db = _get_db()

    def query():
        docs = db.collection("students").where("name", "==", name).limit(1).stream()
        for doc in docs:
            return {"id": doc.id, **doc.to_dict()}
        return None

    result = _retry(query)
    _student_cache[name] = result
    return result


def add_points_bulk(entries: list[dict]) -> dict[str, int]:
    """
    여러 학생 포인트를 한 번의 batch write로 처리.
    entries: [{"student_id": str, "student_name": str, "point_change": int, "reason": str}, ...]
    반환: {student_name: new_total, ...}
    """
    db = _get_db()
    now = datetime.datetime.now()
    results = {}

    def batch_write():
        batch = db.batch()
        for entry in entries:
            sid = entry["student_id"]
            sname = entry["student_name"]
            pts = entry["point_change"]
            reason = entry["reason"]

            # 포인트 기록 (새 doc 추가)
            record_ref = db.collection("point_records").document()
            batch.set(record_ref, {
                "student_id": sid,
                "student_name": sname,
                "point_change": pts,
                "reason": reason,
                "category": "수업포인트",
                "recorded_at": now,
                "created_at": now,
                "updated_at": now,
            })

            # 누적 포인트 INCREMENT (읽기 없이 원자적 증가)
            student_ref = db.collection("students").document(sid)
            batch.update(student_ref, {
                "total_points": firestore.Increment(pts),
                "updated_at": now,
            })

        batch.commit()

    _retry(batch_write)

    # 커밋 후 캐시 무효화 + 새 누적 포인트 조회
    for entry in entries:
        sname = entry["student_name"]
        _student_cache.pop(sname, None)
        updated = find_student_by_name(sname)
        results[sname] = (updated or {}).get("total_points", "?")

    return results


def add_points(student_id: str, student_name: str, point_change: int, reason: str, category: str = "수업포인트"):
    """단일 학생 포인트 추가 (하위 호환용)"""
    result = add_points_bulk([{
        "student_id": student_id,
        "student_name": student_name,
        "point_change": point_change,
        "reason": reason,
    }])
    return result.get(student_name, 0)
