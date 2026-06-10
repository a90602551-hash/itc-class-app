"""
Firebase Firestore 포인트 연동 모듈
the-fluent-point 프로젝트와 연동
"""
import os
import datetime
import firebase_admin
from firebase_admin import credentials, firestore

_SA_FILE = os.path.join(os.path.dirname(__file__), "firebase_service_account.json")

_fb_app = None

def _get_db():
    global _fb_app
    if _fb_app is None:
        # Streamlit Cloud: secrets에서 읽기
        try:
            import streamlit as st
            if "firebase_service_account" in st.secrets:
                import json, tempfile
                info = dict(st.secrets["firebase_service_account"])
                # private_key 줄바꿈 복원
                info["private_key"] = info["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(info)
                _fb_app = firebase_admin.initialize_app(cred, name="fluent_point")
            else:
                raise KeyError
        except Exception:
            # 로컬: JSON 파일
            cred = credentials.Certificate(_SA_FILE)
            try:
                _fb_app = firebase_admin.initialize_app(cred, name="fluent_point")
            except ValueError:
                _fb_app = firebase_admin.get_app("fluent_point")

    return firestore.client(firebase_admin.get_app("fluent_point"))


def find_student_by_name(name: str) -> dict | None:
    """이름으로 학생 찾기 (부분 일치)"""
    db = _get_db()
    students = db.collection("students").stream()
    for doc in students:
        data = doc.to_dict()
        student_name = data.get("name", "")
        # 전체 이름 또는 부분 이름 매칭
        if name in student_name or student_name in name:
            return {"id": doc.id, **data}
    return None


def add_points(student_id: str, student_name: str, point_change: int, reason: str, category: str = "수업포인트"):
    """포인트 추가/차감"""
    if point_change == 0:
        return
    db = _get_db()
    now = datetime.datetime.now()

    # point_records에 기록
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

    # students total_points 업데이트
    student_ref = db.collection("students").doc(student_id)
    student = student_ref.get().to_dict()
    new_total = (student.get("total_points") or 0) + point_change
    student_ref.update({"total_points": new_total, "updated_at": now})

    return new_total
