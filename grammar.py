import re
import requests
import io
from docx import Document
from auth import auth_headers as _auth_headers
from config import GRAMMAR_FOLDER_IDS

DRIVE_API = "https://www.googleapis.com/drive/v3"

_folder_files_cache: dict[str, list[dict]] = {}


def _list_folder_files(folder_id: str) -> list[dict]:
    if folder_id in _folder_files_cache:
        return _folder_files_cache[folder_id]

    url = f"{DRIVE_API}/files"
    params = {
        "q": f"'{folder_id}' in parents and trashed=false",
        "fields": "files(id,name)",
        "pageSize": 200,
    }
    resp = requests.get(url, params=params, headers=_auth_headers(), timeout=10)
    resp.raise_for_status()
    files = resp.json().get("files", [])
    _folder_files_cache[folder_id] = files
    return files


def get_grammar_content(grammar_ref: str) -> str:
    if not grammar_ref:
        return ""

    m = re.match(r"([BPIAbpia])(\d+)-?(\d*)", grammar_ref)
    if not m:
        return ""

    prefix = m.group(1).upper()
    unit = m.group(2)
    sub = m.group(3)

    folder_id = GRAMMAR_FOLDER_IDS.get(prefix)
    if not folder_id:
        return f"({prefix} 폴더 없음)"

    files = _list_folder_files(folder_id)

    # 파일명 패턴: "3-1. xxx" 또는 "3-1 xxx" (점/공백 모두 허용)
    if sub:
        prefix_pattern = re.compile(rf"^{unit}-{sub}[\s\.]")
    else:
        prefix_pattern = re.compile(rf"^{unit}[\s\.]")

    target = next((f for f in files if prefix_pattern.match(f["name"])), None)

    if not target:
        return f"({grammar_ref} 파일 없음)"

    return _download_docx(target["id"], target["name"])


def _download_docx(file_id: str, file_name: str) -> str:
    url = f"{DRIVE_API}/files/{file_id}?alt=media"
    try:
        resp = requests.get(url, headers=_auth_headers(), timeout=15)
        resp.raise_for_status()
        doc = Document(io.BytesIO(resp.content))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs[:15])
    except Exception as e:
        return f"({file_name}: {str(e)[:50]})"
