import streamlit as st
import datetime
from sheets import get_student_groups, get_student_progress, match_full_name, clear_cache
from vocab import fetch_lesson_content
from grammar import get_grammar_content

st.set_page_config(page_title="ITC 수업", layout="wide")
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

# 클릭 시 사라지는 단어 버튼 스타일
st.markdown("""
<style>
div[data-testid="column"] .stButton button {
    margin: 3px;
    border-radius: 20px;
    font-size: 1.1em;
    font-weight: bold;
    padding: 6px 16px;
    transition: all 0.2s;
}
</style>
""", unsafe_allow_html=True)

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

        # 이름 + 문장수 + 단어/표현 토글 한 줄에
        hc1, hc2, hc3 = st.columns([4, 1, 1])
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
            label = f"단어/표현: " + (f"<span style='color:gray;font-size:0.8em;'>+{remaining}개 남음</span>" if remaining else "")
            st.markdown(label, unsafe_allow_html=True)

            # 단어 3개를 가로로 배치
            word_cols = st.columns(3)
            for slot, word_idx in enumerate(list(shown)):
                with word_cols[slot]:
                    if st.button(f"✕ {words_clean[word_idx]}", key=f"del_{name}_{selected_idx}_{slot}"):
                        shown.pop(slot)
                        st.session_state[shown_key] = shown
                        st.rerun()
                    if pool and st.button("🔄", key=f"swap_{name}_{selected_idx}_{slot}"):
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
            st.markdown("**문법:**")
            st.session_state[grammar_edit_key] = st.text_area(
                label="",
                value=st.session_state[grammar_edit_key],
                height=90,
                key=f"grammar_box_{name}_{selected_idx}",
                label_visibility="collapsed"
            )

        st.markdown("")
