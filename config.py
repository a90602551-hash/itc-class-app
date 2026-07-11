import datetime

_month = datetime.datetime.now().month
_month_str = f"{_month}월"

SHEET_ID = "1b1zY-KRuOJPLeLH3lZ72RBpb8sLJyWAm0Q7KGZ4s5Y8"
GOOGLE_API_KEY = "AIzaSyBf•••••••••••••••••••••••••••••••"

# 요일별 시트 이름 (현재 월 자동 감지)
DAY_SHEETS = {
    "월": f"{_month_str} 월",
    "화": f"{_month_str} 화",
    "수": f"{_month_str} 수",
    "목": f"{_month_str} 목",
    "금": f"{_month_str} 금",
    "토": f"{_month_str} 토",
    "일": f"{_month_str} 일",
}

# 요일별 과제 시트 이름
HOMEWORK_SHEETS = {
    "월": "월 과제 and 온",
    "화": "화 과제 and 온",
    "수": "수 과제 and 온",
    "목": "목 과제 and 온",
    "금": "금 과제 and 온",
    "토": "토 과제 and 온",
    "일": "일 과제 and 온",
}

# 문법 폴더 ID (Google Drive)
GRAMMAR_FOLDER_IDS = {
    "B": "1GH2niGKZmp4cur6U57JZZ5dk02Fqvf5n",
    "P": "1OAGcZt9GdQhDNwFCaEYqyNK_YirDZ6Xu",
    "I": "1IrrWpokT8Dqpv6w3MzVMu9zIxjbk68sn",
    "A": "1YANU_NF0xMIEjbeYxbaw64d7DgppsWbQ",
}

# ITC 교재 웹사이트
ITC_URL = "https://www.itcenglish.com/textbook/teacher/?step_code=L{level}&lesson_no={lesson:02d}"

# PPT 템플릿 경로
TEMPLATE_PATH = r"C:\Users\최나영\OneDrive\바탕 화면\template.pptx"

# 학생 텍스트박스 shape 이름 (순서: 좌상, 좌하, 우상, 우하)
STUDENT_SHAPES = [
    "Google Shape;94;p1",
    "Google Shape;95;p1",
    "Google Shape;96;p1",
    "Google Shape;97;p1",
]
