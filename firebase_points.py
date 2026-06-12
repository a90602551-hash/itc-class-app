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


def _get_db():
    global _db
    if _db is not None:
        return _db

    # 이미 초기화된 Firebase 앱 재사용
    try:
        app = firebase_admin.get_app(_APP_NAME)
        _db = firestore.client(app)
        return _db
    except ValueError:
        pass  # 앱 아직 없음

    # Streamlit Cloud secrets 시도
    try:
        import streamlit as st
        sa = st.secrets.get("firebase_service_account")
        if sa is not None:
            info = {k: v for k, v in sa.items()}
            info["private_key"] = info["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(info)
            app = firebase_admin.initialize_app(cred, name=_APP_NAME)
            _db = firestore.client(app)
            return _db
    except Exception as e:
        raise RuntimeError(f"Firebase secrets 로드 실패: {e}")

    # 로컬 JSON 파일
    cred = credentials.Certificate(_SA_FILE)
    app = firebase_admin.initialize_app(cred, name=_APP_NAME)
    _db = firestore.client(app)
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
