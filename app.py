import streamlit as st
import datetime
from sheets import get_student_groups, get_student_progress, match_full_name, clear_cache, get_student_checks
from vocab import fetch_lesson_content
from grammar import get_grammar_content
from firebase_points import find_student_by_name, add_points

st.set_page_config(page_title="ITC 수업", layout="wide")

# --- 비밀번호 확인 ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 ITC 수업")
    pw = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("확인"):
        if pw == "1206":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

st.title("📚 ITC 수업")

# --- 날짜 선택 ---
col1, col2 = st.columns([2, 1])
with col1:
    selected_date = st.date_input("수업 날짜 선택", value=datetime.date.today())
with col2:
    day_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    weekday = day_map[selected_date.weekday()]
    st.markdown(f"### {selected_date.strftime('%Y년 %m월 %d일')} ({weekday}요일)")

col_btn1, col_btn2 = st.columns([1, 1])
with col_btn1:
    load_btn = st.button("🔄 시간표 불러오기", type="primary")
with col_btn2:
    refresh_btn = st.button("🔃 시트 새로고침", help="학생 추가/변경 시 사용")

if refresh_btn:
    clear_cache()
    for key in ["groups", "progress", "weekday", "modes"]:
        st.session_state.pop(key, None)

if load_btn or refresh_btn:
    with st.spinner("구글 시트에서 데이터 불러오는 중..."):
        groups = get_student_groups(weekday)
        progress = get_student_progress(weekday)
        st.session_state["groups"] = groups
        st.session_state["progress"] = progress
        st.session_state["weekday"] = weekday
        st.session_state["modes"] = {}
        st.session_state["removed"] = {}  # 클릭으로 지워진 항목

if "groups" not in st.session_state:
    st.info("날짜를 선택하고 '시간표 불러오기'를 눌러주세요.")
    st.stop()

groups = st.session_state["groups"]
progress = st.session_state["progress"]

if not groups:
    st.warning("해당 요일 시간표 데이터가 없습니다.")
    st.stop()

if "removed" not in st.session_state:
    st.session_state["removed"] = {}
if "modes" not in st.session_state:
    st.session_state["modes"] = {}

st.markdown("---")

# 수업 그룹 선택
group_labels = [f"{g['time']} | {', '.join(g['students'])}" for g in groups]
selected_idx = st.selectbox("수업 그룹 선택", range(len(groups)), format_func=lambda i: group_labels[i])
selected_group = groups[selected_idx]
students = selected_group["students"][:4]

# 그룹 변경 시 removed 초기화
group_key = f"group_{selected_idx}"
if st.session_state.get("current_group") != group_key:
    st.session_state["current_group"] = group_key
    st.session_state["removed"] = {}
    st.session_state["modes"] = {}

st.markdown("---")

# 레이아웃 압축 스타일
st.markdown("""
<style>
/* 전체 여백 축소 */
.block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; }
div[data-testid="stVerticalBlock"] > div { gap: 0rem !important; }
.element-container { margin-bottom: 0px !important; }
/* 컬럼 내부 수직 간격 제거 */
div[data-testid="stVerticalBlock"] { gap: 0px !important; }

/* 모든 버튼 작게 */
div[data-testid="column"] .stButton button {
    font-size: 0.82em !important;
    padding: 3px 8px !important;
    min-height: 28px !important;
    margin: 1px;
}
/* 구분선 여백 */
hr { margin: 3px 0 !important; }
/* 문법 텍스트 영역 폰트 크게 */
.stTextArea textarea { font-size: 1.15em !important; line-height: 1.5 !important; }
/* number input 여백 제거 */
.stNumberInput { margin-bottom: 0 !important; }
/* 단어 표시 영역 위아래 패딩 제거 */
.word-display { margin: 0 !important; padding: 0 !important; }
</style>
""", unsafe_allow_html=True)

# 오늘의 대화 주제 (진도 가장 낮은 학생 기준)
lowest = None
for name in students:
    full_name = match_full_name(name, list(progress.keys())) or name
    p = progress.get(full_name, {})
    lv, ls = p.get("level"), p.get("lesson")
    if lv and ls:
        if lowest is None or (lv, ls) < (lowest[0], lowest[1]):
            lowest = (lv, ls)

if lowest:
    topic_key = f"content_L{lowest[0]}_L{lowest[1]}"
    if topic_key not in st.session_state:
        st.session_state[topic_key] = fetch_lesson_content(lowest[0], lowest[1])
    topic_title = st.session_state[topic_key].get("title", "")
    if topic_title:
        st.markdown(f"### 💬 오늘의 대화 주제: {topic_title}")

# 체크 항목 포인트 일괄 집계 버튼
if st.button("✅ 이 수업 체크 포인트 집계", help="과제완수/레슨통과/부스&클리닉 체크 항목을 읽어 포인트 앱에 반영"):
    weekday = st.session_state.get("weekday", "")
    full_names = [match_full_name(n, list(progress.keys())) or n for n in students]
    checks = get_student_checks(weekday, full_names)
    results = []
    for full_name in full_names:
        chk = checks.get(full_name)
        if not chk:
            results.append(f"❌ {full_name}: 시트에서 찾을 수 없음")
            continue
        pts = int(chk["과제완수"]) + int(chk["레슨통과"]) + int(chk["부스클리닉"])
        if pts == 0:
            results.append(f"⬜ {full_name}: 체크 없음 (0점)")
            continue
        student_fb = find_student_by_name(full_name)
        if not student_fb:
            results.append(f"❌ {full_name}: 포인트 앱에서 찾을 수 없음")
            continue
        reasons = []
        if chk["과제완수"]: reasons.append("과제완수")
        if chk["레슨통과"]: reasons.append("레슨통과")
        if chk["부스클리닉"]: reasons.append("부스&클리닉")
        new_total = add_points(student_fb["id"], full_name, pts, ", ".join(reasons))
        results.append(f"✅ {full_name}: +{pts}점 → 누적 {new_total}점")
    for r in results:
        st.write(r)

cols = st.columns(min(len(students), 2))

for i, name in enumerate(students):
    col = cols[i % 2]
    with col:
        full_name = match_full_name(name, list(progress.keys())) or name
        p = progress.get(full_name, {})
        level = p.get("level")
        lesson = p.get("lesson")
        grammar_ref = p.get("grammar_ref", "")

        sentence_count = 2 if level == 1 else (3 if level == 2 else 5)

        current_mode = st.session_state["modes"].get(name, "words")

        # 이름 + 문장수 + 단어/표현 토글 + 프리토킹 한 줄에
        free_key = f"ft_{name}_{selected_idx}"
        if free_key not in st.session_state:
            st.session_state[free_key] = 0

        hc1, hc2, hc3, hc4, hc5 = st.columns([4, 1, 1, 1, 1])
        with hc1:
            if level and lesson:
                st.markdown(f"**👤 {name}** <span style='color:gray;font-size:0.85em;'>— {sentence_count}문장 | L{level} Lesson {lesson} | 문법:{grammar_ref or '없음'}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"**👤 {name}** <span style='color:gray;font-size:0.85em;'>— 진도 없음</span>", unsafe_allow_html=True)
        with hc2:
            if st.button("단어", key=f"word_{name}_{selected_idx}", type="primary" if current_mode == "words" else "secondary"):
                st.session_state["modes"][name] = "words"
                st.rerun()
        with hc3:
            if st.button("표현", key=f"expr_{name}_{selected_idx}", type="primary" if current_mode == "expressions" else "secondary"):
                st.session_state["modes"][name] = "expressions"
                st.rerun()
        with hc4:
            typed = st.number_input("🏆", min_value=0, max_value=20, value=st.session_state[free_key],
                                    step=1, key=f"ft_input_{name}_{selected_idx}", label_visibility="collapsed")
            st.session_state[free_key] = typed
        with hc5:
            if st.button("저장", key=f"save_pts_{name}_{selected_idx}"):
                free_pts = st.session_state[free_key]
                if free_pts == 0:
                    st.warning("0점입니다.")
                else:
                    student_fb = find_student_by_name(full_name)
                    if student_fb:
                        new_total = add_points(student_fb["id"], student_fb["name"],
                                               free_pts, f"프리토킹({free_pts}점)")
                        st.success(f"✅ +{free_pts}점 (누적: {new_total}점)")
                        st.session_state[free_key] = 0
                    else:
                        st.error(f"포인트 앱에서 '{full_name}' 학생을 찾을 수 없습니다.")

        # 내용 로드
        items = []
        grammar_text = ""

        if level and lesson:
            cache_key = f"content_L{level}_L{lesson}"
            if cache_key not in st.session_state:
                with st.spinner(f"L{level} Lesson {lesson} 로딩..."):
                    st.session_state[cache_key] = fetch_lesson_content(level, lesson)
            lesson_content = st.session_state[cache_key]
            display_mode = st.session_state["modes"].get(name, "words")
            items = lesson_content.get("words" if display_mode == "words" else "expressions", [])

            if grammar_ref:
                grammar_cache_key = f"grammar_{grammar_ref}"
                cached = st.session_state.get(grammar_cache_key, "")
                if not cached or "파일" in cached:
                    with st.spinner(f"문법 {grammar_ref} 로딩..."):
                        cached = get_grammar_content(grammar_ref)
                        if "없음" not in cached:
                            st.session_state[grammar_cache_key] = cached
                grammar_text = cached

        # 단어 표시: 3개씩 보여주고 클릭 시 사라짐 / 교체 버튼으로 풀에서 다음 단어 가져오기
        if items:
            display_mode = st.session_state["modes"].get(name, "words")
            shown_key = f"shown_{name}_{selected_idx}_{display_mode}"
            pool_key = f"pool_{name}_{selected_idx}_{display_mode}"

            # 초기화: 처음 3개 표시, 나머지는 풀로 (단어/표현 각각 독립)
            if shown_key not in st.session_state:
                words_clean = [item.split("(")[0].split("-")[0].strip() for item in items]
                st.session_state[shown_key] = list(range(min(3, len(words_clean))))
                st.session_state[pool_key] = list(range(3, len(words_clean)))

            shown = st.session_state[shown_key]
            pool = st.session_state[pool_key]
            words_clean = [item.split("(")[0].split("-")[0].strip() for item in items]

            remaining = len(pool)
            if remaining:
                st.markdown(f"<span style='color:gray;font-size:0.78em;'>+{remaining}개 남음</span>", unsafe_allow_html=True)

            # 단어: 큰 텍스트 + 작은 ✕ 🔄 버튼
            word_cols = st.columns(3)
            for slot, word_idx in enumerate(list(shown)):
                with word_cols[slot]:
                    st.markdown(f"<div style='font-size:1.7em;font-weight:bold;text-align:center;padding:2px 0;line-height:1.2;'>{words_clean[word_idx]}</div>", unsafe_allow_html=True)
                    btn_c1, btn_c2 = st.columns(2)
                    with btn_c1:
                        if st.button("✕ 지우기", key=f"del_{name}_{selected_idx}_{slot}"):
                            shown.pop(slot)
                            st.session_state[shown_key] = shown
                            st.rerun()
                    with btn_c2:
                        if pool and st.button("🔄 바꾸기", key=f"swap_{name}_{selected_idx}_{slot}"):
                            pool.append(shown[slot])
                            shown[slot] = pool.pop(0)
                            st.session_state[shown_key] = shown
                            st.session_state[pool_key] = pool
                            st.rerun()

        # 문법 항목 (편집 가능한 텍스트박스)
        if grammar_text:
            grammar_edit_key = f"grammar_edit_{name}_{selected_idx}"
            if grammar_edit_key not in st.session_state:
                st.session_state[grammar_edit_key] = grammar_text
            st.session_state[grammar_edit_key] = st.text_area(
                label="",
                value=st.session_state[grammar_edit_key],
                height=70,
                key=f"grammar_box_{name}_{selected_idx}",
                label_visibility="collapsed"
            )


        st.markdown("")
