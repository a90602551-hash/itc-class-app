"""
서비스 계정 인증 헬퍼.
- 로컬: service_account.json 파일 사용
- Streamlit Cloud: st.secrets 사용
"""
import os
import json
import google.auth.transport.requests
from google.oauth2 import service_account

_SA_FILE = os.path.join(os.path.dirname(__file__), "service_account.json")
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_credentials():
    # Streamlit Cloud: secrets에서 읽기
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            creds = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
            creds.refresh(google.auth.transport.requests.Request())
            return creds
    except Exception:
        pass

    # 로컬: JSON 파일에서 읽기
    creds = service_account.Credentials.from_service_account_file(_SA_FILE, scopes=_SCOPES)
    creds.refresh(google.auth.transport.requests.Request())
    return creds


def get_token() -> str:
    return get_credentials().token


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {get_token()}"}
