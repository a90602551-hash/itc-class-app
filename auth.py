"""
서비스 계정 인증 헬퍼.
- 로컬: service_account.json 파일 사용
- Streamlit Cloud: st.secrets 사용
"""
import os
import datetime
import google.auth.transport.requests
from google.oauth2 import service_account

_SA_FILE = os.path.join(os.path.dirname(__file__), "service_account.json")
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

_creds = None


def get_credentials():
    global _creds
    # 만료 5분 전까지는 기존 토큰 재사용
    if _creds is not None and _creds.expiry:
        remaining = (_creds.expiry - datetime.datetime.utcnow()).total_seconds()
        if remaining > 300:
            return _creds

    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            _creds = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
            _creds.refresh(google.auth.transport.requests.Request())
            return _creds
    except Exception:
        pass

    _creds = service_account.Credentials.from_service_account_file(_SA_FILE, scopes=_SCOPES)
    _creds.refresh(google.auth.transport.requests.Request())
    return _creds


def get_token() -> str:
    return get_credentials().token


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {get_token()}"}
