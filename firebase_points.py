"""
Firebase Firestore 포인트 연동 모듈
the-fluent-point 프로젝트와 연동
"""
import os
import datetime
import firebase_admin
from firebase_admin import credentials, firestore

_SA_FILE = os.path.join(os.path.dirname(__file__), "firebase_service_account.json")
_APP_NAME = "fluent_point"
_db = None


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

    # 이미 초기화된 앱 재사용 or 새로 초기화
    try:
        app = firebase_admin.get_app(_APP_NAME)
    except ValueError:
        info = _load_sa_info()
        cred = credentials.Certificate(info)
        app = firebase_admin.initialize_app(cred, name=_APP_NAME)

    _db = firestore.client(app=app)
    return _db


def find_student_by_name(name: str) -> dict | None:
    """이름으로 학생 찾기 (정확 일치)"""
    db = _get_db()
    docs = db.collection("students").where("name", "==", name).limit(1).stream()
    for doc in docs:
        return {"id": doc.id, **doc.to_dict()}
    return None


def add_points(student_id: str, student_name: str, point_change: int, reason: str, category: str = "수업포인트"):
    """포인트 추가/차감"""
    if point_change == 0:
        return 0
    db = _get_db()
    now = datetime.datetime.now()

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

    student_ref = db.collection("students").doc(student_id)
    student_snap = student_ref.get()
    student_data = student_snap.to_dict() or {}
    new_total = (student_data.get("total_points") or 0) + point_change
    student_ref.update({"total_points": new_total, "updated_at": now})

    return new_total
