import streamlit as st
import datetime
from sheets import get_student_groups, get_student_progress, match_full_name, clear_cache, get_student_checks, write_freetalk_points, write_lesson_check, advance_student_lesson
from vocab import fetch_lesson_content
from grammar import get_grammar_content
from fluent import fetch_fluent_content
from supabase_points import find_student_by_name, add_points_bulk

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
if "checks" not in st.session_state:
    # 모든 그룹 학생 체크 상태 미리 로드
    all_full_names = list({
        match_full_name(n, list(progress.keys())) or n
        for g in groups for n in g["students"][:4]
    })
    wd_init = st.session_state.get("weekday", "월")
    st.session_state["checks"] = get_student_checks(wd_init, all_full_names)

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
div[data-testid="stVerticalBlock"] > div { gap: 0.15rem !important; }
.element-container { margin-bottom: 2px !important; }

/* 모든 버튼 작게 */
div[data-testid="column"] .stButton button {
    font-size: 0.82em !important;
    padding: 3px 8px !important;
    min-height: 28px !important;
    margin: 1px;
}
/* 컬럼 사이 간격 제거 */
div[data-testid="stHorizontalBlock"] { gap: 4px !important; }
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

# 체크 항목 + 프리토킹 포인트 일괄 집계 버튼
if st.button("✅ 오늘 수업 포인트 집계", help="과제완수/레슨통과/부스&클리닉 체크 + 프리토킹 포인트를 한꺼번에 반영"):
    wd = st.session_state.get("weekday", weekday)
    full_names = [match_full_name(n, list(progress.keys())) or n for n in students]
    checks = get_student_checks(wd, full_names)

    # 1단계: 학생 조회 및 포인트 계산
    entries = []
    skipped = []
    freetalk_to_write = []

    for name, full_name in zip(students, full_names):
        chk = checks.get(full_name, {})
        check_pts = int(chk.get("과제완수", False)) + int(chk.get("레슨통과", False)) + int(chk.get("부스클리닉", False))
        free_pts = st.session_state.get(f"ft_{name}_{selected_idx}", 0)
        total_pts = check_pts + free_pts

        if total_pts == 0:
            skipped.append(f"⬜ {full_name}: 포인트 없음")
            continue

        try:
            student_fb = find_student_by_name(full_name)
        except Exception as e:
            skipped.append(f"⚠️ {full_name}: 오류 — {e}")
            continue

        if not student_fb:
            skipped.append(f"❌ {full_name}: 포인트 앱에서 찾을 수 없음")
            continue

        reasons = []
        if chk.get("과제완수"): reasons.append("과제완수")
        if chk.get("레슨통과"): reasons.append("레슨통과")
        if chk.get("부스클리닉"): reasons.append("부스&클리닉")
        if free_pts > 0: reasons.append(f"프리토킹({free_pts}점)")

        entries.append({
            "student_id": student_fb["id"],
            "student_name": full_name,
            "point_change": total_pts,
            "reason": ", ".join(reasons),
        })
        if free_pts > 0:
            freetalk_to_write.append((full_name, free_pts))

    # 2단계: 한 번의 batch write로 전체 처리
    results = list(skipped)
    if entries:
        try:
            totals = add_points_bulk(entries)
            for e in entries:
                sname = e["student_name"]
                results.append(f"✅ {sname}: +{e['point_change']}점 → 누적 {totals.get(sname, '?')}점")
            for full_name, free_pts in freetalk_to_write:
                write_freetalk_points(wd, full_name, free_pts)
        except Exception as ex:
            for e in entries:
                results.append(f"⚠️ {e['student_name']}: 저장 실패 — {ex}")

    for r in results:
        st.write(r)

cols = st.columns(min(len(students), 2))

for i, name in enumerate(students):
    col = cols[i % 2]
    with col:
        full_name = match_full_name(name, list(progress.keys())) or name
        p = progress.get(full_name, {})
        source = p.get("source", "itc")
        level = p.get("level")
        lesson = p.get("lesson")
        unit = p.get("unit")
        grammar_ref = p.get("grammar_ref", "")
        is_fluent = source == "fluent"
        is_manual = "[수동]" in p.get("boothwork_raw", "")

        sentence_count = 2 if level == 1 else (3 if level == 2 else 5)
        wd = st.session_state.get("weekday", weekday)

        # ── 체크 상태 (과제완수는 시트에서, 나머지는 앱 상태) ──
        checks = st.session_state.get("checks", {})
        hw_done = checks.get(full_name, {}).get("과제완수", False)
        ls_key  = f"ls_{name}_{selected_idx}"
        cl_key  = f"cl_{name}_{selected_idx}"
        if ls_key not in st.session_state:
            st.session_state[ls_key] = checks.get(full_name, {}).get("레슨통과", False)
        if cl_key not in st.session_state:
            st.session_state[cl_key] = checks.get(full_name, {}).get("부스클리닉", False)

        current_mode = st.session_state["modes"].get(name, "words")
        free_key = f"ft_{name}_{selected_idx}"
        if free_key not in st.session_state:
            st.session_state[free_key] = 0

        # ── 헤더: 이름 + 진도 정보 ──
        hc1, hc2, hc3, hc4 = st.columns([4, 1, 1, 1])
        with hc1:
            if is_fluent and level and unit:
                st.markdown(f"**👤 {name}** <span style='color:#4CAF50;font-size:0.85em;'>🌟 플루언트 L{level} Unit {unit} | {sentence_count}문장</span>", unsafe_allow_html=True)
            elif level and lesson:
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
            typed = st.number_input("🏆 프리토킹", min_value=0, max_value=20, value=st.session_state[free_key],
                                    step=1, key=f"ft_input_{name}_{selected_idx}")
            st.session_state[free_key] = typed

        # ── 체크 UI: 과제완수(읽기전용) + 레슨통과 + 부스클리닉 ──
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            st.checkbox("✅ 과제완수", value=hw_done, disabled=True, key=f"hw_{name}_{selected_idx}")
        with cc2:
            new_ls = st.checkbox("🎯 레슨통과", value=st.session_state[ls_key], key=f"ls_cb_{name}_{selected_idx}")
            if new_ls != st.session_state[ls_key]:
                st.session_state[ls_key] = new_ls
                write_lesson_check(wd, full_name, "레슨통과", new_ls)
                st.rerun()
        with cc3:
            new_cl = st.checkbox("🏥 부스클리닉", value=st.session_state[cl_key], key=f"cl_cb_{name}_{selected_idx}")
            if new_cl != st.session_state[cl_key]:
                st.session_state[cl_key] = new_cl
                write_lesson_check(wd, full_name, "부스클리닉", new_cl)
                st.rerun()

        # ── 자동 진급 / 수동 리마인더 ──
        all_checked = hw_done and st.session_state[ls_key] and st.session_state[cl_key]
        if all_checked:
            if is_manual:
                st.warning(f"🔔 {full_name} — 수동 업데이트 필요 (시트에서 직접 진급 처리해 주세요)")
            else:
                adv_key = f"advanced_{name}_{selected_idx}"
                if not st.session_state.get(adv_key):
                    ok = advance_student_lesson(wd, full_name, is_fluent)
                    if ok:
                        st.session_state[adv_key] = True
                        next_num = (unit or 0) + 1 if is_fluent else (lesson or 0) + 1
                        label = f"Unit {next_num}" if is_fluent else f"Lesson {next_num}"
                        st.success(f"✅ {full_name} → {label}로 자동 진급 완료!")
                    else:
                        st.error(f"❌ {full_name} 진급 업데이트 실패 — 시트를 확인해 주세요")
                else:
                    next_num = (unit or 0) + 1 if is_fluent else (lesson or 0) + 1
                    label = f"Unit {next_num}" if is_fluent else f"Lesson {next_num}"
                    st.success(f"✅ {full_name} → {label}로 자동 진급 완료!")

        # ── 내용 로드 ──
        items = []
        all_items = []   # 풀 고갈 시 이전 레슨 복습용 전체 풀
        grammar_text = ""
        grammar_title = ""

        if is_fluent and level and unit:
            cache_key = f"fluent_L{level}_U{unit}"
            if cache_key not in st.session_state:
                with st.spinner(f"플루언트 L{level} Unit {unit} 로딩..."):
                    st.session_state[cache_key] = fetch_fluent_content(level, unit)
            fluent_content = st.session_state[cache_key]
            display_mode = st.session_state["modes"].get(name, "words")
            items = fluent_content.get("words" if display_mode == "words" else "expressions", [])
            grammar_title = fluent_content.get("grammarTitle", "")

        elif not is_fluent and level and lesson:
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

        # ── 단어 풀 표시 ──
        if items:
            display_mode = st.session_state["modes"].get(name, "words")
            shown_key = f"shown_{name}_{selected_idx}_{display_mode}"
            pool_key  = f"pool_{name}_{selected_idx}_{display_mode}"
            base_key  = f"base_{name}_{selected_idx}_{display_mode}"  # 전체 단어 원본 저장

            if shown_key not in st.session_state:
                words_clean = [item.split("(")[0].split("-")[0].strip() for item in items]
                st.session_state[base_key]  = list(words_clean)
                st.session_state[shown_key] = list(range(min(3, len(words_clean))))
                st.session_state[pool_key]  = list(range(3, len(words_clean)))

            shown      = st.session_state[shown_key]
            pool       = st.session_state[pool_key]
            words_all  = st.session_state[base_key]

            remaining = len(pool)
            if remaining:
                st.markdown(f"<span style='color:gray;font-size:0.78em;'>+{remaining}개 남음</span>", unsafe_allow_html=True)

            # 이전 레슨 복습 버튼 (풀 소진 시)
            if not pool:
                prev_offset_key = f"prev_offset_{name}_{selected_idx}_{display_mode}"
                cur_offset = st.session_state.get(prev_offset_key, 0)
                if is_fluent:
                    prev_ref = unit - 1 - cur_offset if unit else None
                    prev_label = f"Unit {prev_ref}" if prev_ref and prev_ref > 0 else None
                else:
                    prev_ref = lesson - 1 - cur_offset if lesson else None
                    prev_label = f"Lesson {prev_ref}" if prev_ref and prev_ref > 0 else None

                if prev_label:
                    if st.button(f"📚 이전 {prev_label} 복습 단어 추가", key=f"prev_{name}_{selected_idx}_{cur_offset}"):
                        if is_fluent:
                            pk = f"fluent_L{level}_U{prev_ref}"
                            if pk not in st.session_state:
                                st.session_state[pk] = fetch_fluent_content(level, prev_ref)
                            prev_items = st.session_state[pk].get("words" if display_mode == "words" else "expressions", [])
                        else:
                            pk = f"content_L{level}_L{prev_ref}"
                            if pk not in st.session_state:
                                st.session_state[pk] = fetch_lesson_content(level, prev_ref)
                            prev_items = st.session_state[pk].get("words" if display_mode == "words" else "expressions", [])

                        prev_words = [w.split("(")[0].split("-")[0].strip() for w in prev_items]
                        offset = len(words_all)
                        words_all.extend(prev_words)
                        st.session_state[base_key] = words_all
                        pool.extend(range(offset, len(words_all)))
                        st.session_state[pool_key] = pool
                        st.session_state[prev_offset_key] = cur_offset + 1
                        st.rerun()

            word_cols = st.columns(3)
            for slot, word_idx in enumerate(list(shown)):
                with word_cols[slot]:
                    st.markdown(f"<div style='font-size:1.7em;font-weight:bold;text-align:center;padding:8px 0 4px 0;line-height:1.3;'>{words_all[word_idx]}</div>", unsafe_allow_html=True)
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

        # ── 문법 표시 ──
        if grammar_title:
            # 플루언트: 주제명만 표시
            st.markdown(f"<div style='background:#E8F5E9;border-radius:8px;padding:6px 12px;font-size:1em;font-weight:bold;color:#2E7D32;margin-top:4px;'>📐 문법: {grammar_title}</div>", unsafe_allow_html=True)
        elif grammar_text:
            # ITC: 기존 텍스트 영역
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
