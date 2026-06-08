import re
import requests
import io
import zipfile
from openpyxl import load_workbook
from auth import auth_headers
from config import SHEET_ID, DAY_SHEETS, HOMEWORK_SHEETS

_xlsx_cache: bytes | None = None


def match_full_name(short_name: str, full_names: list[str]) -> str | None:
    """짧은 이름(서영)으로 전체 이름(이서영) 찾기"""
    for full in full_names:
        if full.endswith(short_name) or short_name in full:
            return full
    return None


def _get_xlsx(force_refresh: bool = False) -> bytes:
    global _xlsx_cache
    if _xlsx_cache is None or force_refresh:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"
        resp = requests.get(url, headers=auth_headers(), allow_redirects=True)
        resp.raise_for_status()
        _xlsx_cache = resp.content
    return _xlsx_cache


def clear_cache():
    global _xlsx_cache
    _xlsx_cache = None


def _fetch_sheet_data(sheet_name: str) -> list[list[str]]:
    xlsx_bytes = _get_xlsx()
    wb = load_workbook(io.BytesIO(xlsx_bytes), data_only=True)
    if sheet_name not in wb.sheetnames:
        return []
    ws = wb[sheet_name]
    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(cell) if cell is not None else "" for cell in row])
    return rows


def get_student_groups(day: str) -> list[dict]:
    """
    시간표 탭에서 시간대별 학생 그룹을 추출.
    반환: [{"time": "14:35", "students": ["배서준", ...]}, ...]
    """
    sheet_name = DAY_SHEETS.get(day)
    if not sheet_name:
        return []

    rows = _fetch_sheet_data(sheet_name)

    # 불필요한 키워드 (학생 이름이 아닌 것)
    NON_STUDENT = {"부스", "후방데스크", "플루언트", ""}

    def clean_names(bracket_text: str) -> list[str]:
        # 주석 및 부가설명 제거
        text = re.sub(r"\*[^,<>]*", "", bracket_text)   # *재희 6월 신규
        text = re.sub(r'"[^"]*"', "", text)              # "플루언트"
        text = re.sub(r'\([^)]*\)', "", text)            # (플루언트)
        text = re.sub(r'-\s*고등', "", text)             # -고등
        text = re.sub(r'/플루언트', "", text)            # /플루언트
        text = re.sub(r':\s*플루언트', "", text)         # :플루언트
        # 쉼표 또는 공백으로 분리
        parts = re.split(r'[,\s]+', text)
        names = []
        for name in parts:
            name = name.strip().strip("()")
            if name and name not in NON_STUDENT and not re.match(r"^\d", name) and len(name) >= 2:
                names.append(name)
        return names

    current_time = None
    groups = []

    for row in rows:
        time_cell = row[0].strip().split("\n")[0] if row else ""
        time_match = re.match(r"(\d{1,2}:\d{2})", time_cell)
        if time_match:
            current_time = time_match.group(1)

        # 학생 이름 추출: <이름,...> 패턴 (부스/후방 제외)
        all_text = " ".join(row)
        brackets = re.findall(r"<([^>]+)>", all_text)

        for bracket in brackets:
            if any(kw in bracket for kw in ["부스", "후방", "1,2강"]):
                continue
            names = clean_names(bracket)
            if not names:
                continue
            # 같은 시간대에 이미 같은 그룹이 있으면 추가 안 함
            existing = next((g for g in groups if g["time"] == current_time and set(g["students"]) == set(names)), None)
            if not existing and current_time:
                groups.append({"time": current_time, "students": names})

    return groups


def get_student_progress(day: str) -> dict[str, dict]:
    """
    모든 요일 과제 탭에서 학생별 진도 정보 추출.
    반환: {"학생명": {"lesson": 8, "level": 1, "grammar_ref": "B4-3"}, ...}
    """
    all_rows = []
    for sheet_name in HOMEWORK_SHEETS.values():
        all_rows.extend(_fetch_sheet_data(sheet_name))
    rows = all_rows
    progress = {}

    for row in rows:
        if len(row) < 3:
            continue
        name = row[0].strip()
        boothwork = row[1].strip() if len(row) > 1 else ""
        homework = row[2].strip() if len(row) > 2 else ""

        if not name or name in ("이름", ""):
            continue

        # C열(Homework): Level/Lesson 번호 추출
        # 형식1: "Level 2 - Lesson 4", "level4 lesson 16"
        # 형식2: "LV1-8과" → Level 1, Lesson 8
        lesson_num = None
        level_num = None

        lv_dash = re.search(r"[Ll][Vv](\d+)-(\d+)과?", homework)
        if lv_dash:
            level_num = int(lv_dash.group(1))
            lesson_num = int(lv_dash.group(2))
        else:
            level_match = re.search(r"[Ll]evel\s*(\d+)|LV\s*(\d+)|Lv\s*(\d+)|레벨\s*(\d+)", homework)
            if level_match:
                level_num = int(next(g for g in level_match.groups() if g))
            lesson_match = re.search(r"[Ll]esson\s*(\d+)|레슨\s*(\d+)", homework)
            if lesson_match:
                lesson_num = int(next(g for g in lesson_match.groups() if g))

        # B열(Boothwork): 문법 참조 추출 (예: B4-3, P1-2)
        grammar_match = re.search(r"문법\s*([BPIAbpia])(\d+)-?(\d*)", boothwork)
        if grammar_match:
            prefix = grammar_match.group(1).upper()
            unit = grammar_match.group(2)
            sub = grammar_match.group(3)
            grammar_ref = f"{prefix}{unit}-{sub}" if sub else f"{prefix}{unit}"
        else:
            grammar_ref = None

        progress[name] = {
            "lesson": lesson_num,
            "level": level_num,
            "grammar_ref": grammar_ref,
            "homework_raw": homework,
            "boothwork_raw": boothwork,
        }

    return progress
