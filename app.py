import streamlit as st
import datetime
from sheets import get_student_groups, get_student_progress, match_full_name, clear_cache
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

        # 포인트 입력 UI
        st.markdown("**🏆 포인트**")
        pc1, pc2, pc3, pc4 = st.columns(4)
        with pc1:
            hw_done = st.checkbox("과제완수 +1", key=f"hw_{name}_{selected_idx}")
        with pc2:
            lesson_done = st.checkbox("레슨통과 +1", key=f"lp_{name}_{selected_idx}")
        with pc3:
            clinic_done = st.checkbox("부스&클리닉 +1", key=f"cl_{name}_{selected_idx}")
        with pc4:
            free_pts = st.number_input("프리토킹", min_value=0, max_value=20, value=0,
                                       step=1, key=f"ft_{name}_{selected_idx}")

        total_pts = int(hw_done) + int(lesson_done) + int(clinic_done) + int(free_pts)
        save_key = f"saved_{name}_{selected_idx}"

        col_pts, col_btn = st.columns([3, 1])
        with col_pts:
            st.markdown(f"합계: **{total_pts}점**")
        with col_btn:
            if st.button("저장", key=f"save_pts_{name}_{selected_idx}"):
                if total_pts == 0:
                    st.warning("포인트가 0점입니다.")
                else:
                    student_fb = find_student_by_name(full_name)
                    if student_fb:
                        reasons = []
                        if hw_done: reasons.append("과제완수")
                        if lesson_done: reasons.append("레슨통과")
                        if clinic_done: reasons.append("부스&클리닉")
                        if free_pts > 0: reasons.append(f"프리토킹({free_pts}점)")
                        reason_str = ", ".join(reasons)
                        new_total = add_points(student_fb["id"], student_fb["name"],
                                               total_pts, reason_str)
                        st.success(f"✅ {student_fb['name']} +{total_pts}점 (누적: {new_total}점)")
                        st.session_state[save_key] = True
                    else:
                        st.error(f"포인트 앱에서 '{full_name}' 학생을 찾을 수 없습니다.")

        st.markdown("")
