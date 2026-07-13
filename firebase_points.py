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

# 학생 이름 → {id, ...} 캐시 (Firestore 조회 횟수 최소화)
_student_cache: dict[str, dict | None] = {}


def _load_sa_info() -> dict:
    """서비스 계정 정보 로드 (Streamlit secrets 우선, 로컬 파일 폴백)"""
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


def _retry(fn, retries=3, delay=1.5):
    """ResourceExhausted 발생 시 최대 retries번 재시도"""
    for attempt in range(retries):
        try:
            return fn()
        except ResourceExhausted:
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                raise


def find_student_by_name(name: str) -> dict | None:
    """이름으로 학생 찾기 (캐시 우선, Firestore 조회 최소화)"""
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


def add_points(student_id: str, student_name: str, point_change: int, reason: str, category: str = "수업포인트"):
    """포인트 추가/차감"""
    if point_change == 0:
        return 0
    db = _get_db()
    now = datetime.datetime.now()

    def write():
        db.collection("point_records").add({
            "student_id": student_id,
            "student_name": student_name,
            "point_change": point_change,
            "reason": reason,
            "category": category,
            "recorded_at": now,
            "created_at": now,
            "updated_at": now,
        })
        student_ref = db.collection("students").document(student_id)
        student_snap = student_ref.get()
        student_data = student_snap.to_dict() or {}
        new_total = (student_data.get("total_points") or 0) + point_change
        student_ref.update({"total_points": new_total, "updated_at": now})
        return new_total

    new_total = _retry(write)
    _student_cache.pop(student_name, None)
    return new_total
