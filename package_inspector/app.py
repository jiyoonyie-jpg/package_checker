import streamlit as st
import json, os, base64, sys, random
sys.path.insert(0, os.path.dirname(__file__))

from utils.extractor import pdf_to_images, image_to_base64, detect_barcodes, get_file_info, extract_excel_text
from utils.analyzer import analyze_images_with_gemini, generate_report_text
from utils.designer import generate_package_design, refine_design_description
from utils.reporter import export_to_excel

st.set_page_config(
    page_title="커피빈 패키지 AI 검수 시스템",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;800&display=swap');

:root {
    --ivory: #FFFBF0;
    --lavender: #ECE6FB;
    --sky: #E2F1FB;
    --accent-1: #8B7CF6;
    --accent-2: #62A9EE;
    --text-dark: #1D1D1F;
    --mac-titlebar: #F0F0F3;
    --mac-border: rgba(0,0,0,0.08);
}

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Noto Sans KR', sans-serif;
}

/* Streamlit 기본 요소 숨기기 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stDecoration"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
.stDeployButton {display: none !important;}

/* 네이티브 헤더 완전히 제거 — 탭 바가 최상단에 오도록 */
header[data-testid="stHeader"] {
    display: none !important;
}

/* 전체 배경 — 차분한 밝은 그라데이션 (화이트/연보라/하늘색/상아색) */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(150deg, #FFFFFF 0%, var(--ivory) 25%, var(--lavender) 60%, var(--sky) 100%) !important;
    background-attachment: fixed !important;
    padding-top: 0 !important;
}
/* 앱 프레임 — 맥북 스타일 창(윈도우): 굵은 테두리 대신 은은한 그림자 + 얇은 선 */
[data-testid="stMain"],
.main {
    background: #FFFFFF !important;
    border: 1px solid var(--mac-border) !important;
    border-radius: 12px !important;
    margin: 1rem 1.5rem 1.5rem !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
    box-sizing: border-box !important;
    box-shadow: 0 20px 50px rgba(0,0,0,0.12), 0 2px 10px rgba(0,0,0,0.06) !important;
}
.main .block-container,
[data-testid="stMainBlockContainer"],
div.block-container {
    padding: 1rem 1.2rem 1.2rem !important;
    margin-top: 0 !important;
    background: transparent !important;
    max-width: 100% !important;
}

/* 사이드바 항상 펼쳐진 상태로 고정 (본문 공간 확보를 위해 폭을 살짝 줄임) */
[data-testid="stSidebar"] {
    min-width: 220px !important;
    width: 220px !important;
    transform: none !important;
    margin-left: 0 !important;
    visibility: visible !important;
    border-right: 1px solid rgba(139,124,246,0.15) !important;
}
[data-testid="stSidebar"][aria-expanded="false"] {
    transform: none !important;
    margin-left: 0 !important;
    min-width: 220px !important;
    width: 220px !important;
}
[data-testid="collapsedControl"],
section[data-testid="stSidebarCollapsedControl"],
button[title*="sidebar" i],
button[aria-label*="sidebar" i] {
    display: none !important;
}
[data-testid="stSidebarResizeHandle"] {
    display: none !important;
    pointer-events: none !important;
}

/* 사이드바 — 맥북 Finder 스타일 (연한 회색, 그라데이션 없음) */
[data-testid="stSidebar"] > div:first-child {
    background: #F5F5F7 !important;
}
[data-testid="stSidebar"] * { color: var(--text-dark) !important; }
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    color: #3A3A3C !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all .15s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(0,0,0,0.05) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent-1), var(--accent-2)) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 12px rgba(139,124,246,0.35) !important;
}
[data-testid="stSidebar"] hr { border-color: rgba(139,124,246,0.2) !important; }
[data-testid="stSidebar"] label { color: var(--text-dark) !important; }
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.7) !important;
    border: 1px solid rgba(139,124,246,0.25) !important;
    color: var(--text-dark) !important;
}

/* 탭 바 — 맥북 타이틀바 스타일 (신호등 버튼 + 사파리풍 탭) */
/* block-container의 상단/좌우 패딩을 상쇄해 창 테두리 끝까지 꽉 채움 */
.st-key-tabbar {
    background: var(--mac-titlebar) !important;
    border-bottom: 1px solid var(--mac-border) !important;
    border-radius: 12px 12px 0 0 !important;
    padding: .6rem .8rem .5rem !important;
    margin: -1rem -1.2rem 0 -1.2rem !important;
    width: calc(100% + 2.4rem) !important;
}
.st-key-tabbar [data-testid="column"] { padding: 0 2px !important; }

/* 신호등 버튼 (빨강/노랑/초록) */
.mac-dots { display: flex; align-items: center; gap: 8px; height: 100%; padding-left: 2px; }
.mac-dots span {
    width: 12px; height: 12px; border-radius: 50%; display: inline-block;
    box-shadow: inset 0 0 0 1px rgba(0,0,0,0.08);
}
.mac-dots .dot-red    { background: #FF5F57; }
.mac-dots .dot-yellow { background: #FEBC2E; }
.mac-dots .dot-green  { background: #28C840; }

/* 탭 그룹(라벨+닫기x) — 그룹 컨테이너 자체가 탭 모양의 배경을 갖고,
   안의 버튼 두 개는 배경 없이 투명하게 만들어 하나로 보이게 함 */
div[class*="st-key-tabgroup_"] {
    border-radius: 8px !important;
    padding: 0 !important;
    overflow: hidden !important;
}
div[class*="st-key-tabgroup_active_"] {
    background: #FFFFFF !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12) !important;
}
div[class*="st-key-tabgroup_inactive_"] { background: transparent !important; }
div[class*="st-key-tabgroup_"] [data-testid="column"] { padding: 0 !important; }
div[class*="st-key-tabgroup_"] [data-testid="stVerticalBlock"] { gap: 0 !important; }
div[class*="st-key-tabgroup_"] .stButton > button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all .15s !important;
    padding: .4rem .6rem !important;
    font-size: .88rem !important;
}
div[class*="st-key-tabgroup_active_"] .stButton > button {
    color: var(--text-dark) !important;
    font-weight: 600 !important;
}
div[class*="st-key-tabgroup_inactive_"] .stButton > button {
    color: #6E6E73 !important;
}
div[class*="st-key-tabgroup_inactive_"] .stButton > button:hover {
    background: rgba(0,0,0,0.05) !important;
}
/* 닫기(x) 버튼만 호버 시 빨간색으로 강조 */
div[class*="st-key-tabgroup_"] [data-testid="column"]:last-child .stButton > button {
    font-size: .75rem !important;
    padding: .4rem .6rem !important;
    color: #A1A1A6 !important;
}
div[class*="st-key-tabgroup_"] [data-testid="column"]:last-child .stButton > button:hover {
    background: rgba(239,68,68,0.9) !important;
    color: #FFFFFF !important;
}

/* 카드 — 맥북 스타일: 순백 배경 + 얇은 선 + 은은한 그림자 */
.card,
div[class*="st-key-card_"] {
    background: #FFFFFF;
    border: 1px solid var(--mac-border);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.04);
    box-sizing: border-box !important;
}

/* 컬럼이 내부 콘텐츠(파일 업로더 등)의 최소 너비 때문에
   비율을 무시하고 넘치지 않도록 함 — flex/grid 오버플로 방지 */
[data-testid="stHorizontalBlock"] > [data-testid="column"] {
    min-width: 0 !important;
}

/* 점수 카드 */
.score-card {
    padding: 1.4rem;
    border-radius: 16px;
    text-align: center;
    border: 2px solid;
    background: rgba(255,255,255,0.7);
}
.score-high { border-color: #22C55E; }
.score-mid  { border-color: #F59E0B; }
.score-low  { border-color: #F43F5E; }
.score-num  { font-size: 3rem; font-weight: 700; line-height: 1; }

/* 항목 행 */
.field-row {
    display: flex; align-items: flex-start; gap: 8px;
    padding: .5rem .8rem; border-radius: 10px; margin-bottom: .3rem; font-size: .88rem;
}
.field-ok   { background: rgba(34,197,94,0.08); }
.field-fail { background: rgba(244,63,94,0.08); }
.field-badge {
    width: 20px; height: 20px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: .7rem; font-weight: 700; flex-shrink: 0; margin-top: 2px;
}
.badge-ok   { background: #22C55E; color: white; }
.badge-fail { background: #F43F5E; color: white; }

/* 위반 카드 */
.violation-card {
    padding: .7rem 1rem; border-radius: 10px;
    margin-bottom: .4rem; border-left: 4px solid; font-size: .88rem;
    background: rgba(255,255,255,0.6);
}
.v-high   { border-color: #F43F5E; }
.v-medium { border-color: #F59E0B; }
.v-low    { border-color: #22C55E; }
.v-warn   { border-color: #3B82F6; }

/* 버튼 */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent-1), var(--accent-2)) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 600 !important;
    padding: .6rem 1.2rem !important;
    box-shadow: 0 4px 14px rgba(139,124,246,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 18px rgba(139,124,246,0.5) !important;
    filter: brightness(1.05);
}

/* 검수 시작 버튼 — 타이틀바보다 진한 자주색 */
.st-key-card_start .stButton > button[kind="primary"] {
    background: #9C5A87 !important;
    box-shadow: 0 4px 14px rgba(156,90,135,0.45) !important;
}
.st-key-card_start .stButton > button[kind="primary"]:hover {
    background: #874A75 !important;
    box-shadow: 0 6px 18px rgba(156,90,135,0.55) !important;
    filter: none;
}

/* 파일 업로더 — 드롭존 자체를 크게 키워서 전체가 업로드 가능한 영역이 되도록 */
[data-testid="stFileUploader"] {
    border: 2px dashed #B4A7F0 !important;
    border-radius: 14px !important;
    background: rgba(255,255,255,0.55) !important;
}
[data-testid="stFileUploaderDropzone"] {
    min-height: 170px !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
}

/* 요약 박스 */
.summary-box {
    background: linear-gradient(135deg, rgba(255,255,255,0.7), rgba(226,241,251,0.6));
    border: 1px solid rgba(139,124,246,0.25);
    border-radius: 14px;
    padding: .9rem 1.1rem;
    font-size: .92rem;
    color: var(--text-dark);
    margin: 1rem 0;
}

/* 다운로드 버튼 */
.stDownloadButton > button {
    background: rgba(255,255,255,0.8) !important;
    border: 1.5px solid #B4A7F0 !important;
    color: #6D5FD8 !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
}
.stDownloadButton > button:hover {
    background: white !important;
    border-color: var(--accent-1) !important;
}

/* 탭 스타일 제거 (페이지 방식이므로) */
.stTabs { display: none; }

/* expander */
[data-testid="stExpander"] {
    border: 1px solid rgba(139,124,246,0.2) !important;
    border-radius: 14px !important;
    background: rgba(255,255,255,0.6) !important;
}

/* selectbox, checkbox */
.stSelectbox > div > div {
    border-color: rgba(139,124,246,0.3) !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

MENUS = [("🔍", "표기사항 검수"), ("🎨", "패키지 디자인 생성"), ("📖", "검수 기준 안내")]
MENU_ICON = dict(MENUS)

# ── 메뉴 / 탭 상태 ─────────────────────────────────────────
if "menu" not in st.session_state:
    st.session_state["menu"] = "표기사항 검수"
if "open_tabs" not in st.session_state:
    st.session_state["open_tabs"] = ["표기사항 검수"]

# ── 사이드바 ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:.8rem 0 .5rem; text-align:center;">
      <div style="font-size:1.8rem">🎨</div>
      <div style="font-size:.85rem; color:#8B7CF6; margin-top:.2rem; font-weight:700">커피빈 AI 시스템</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    for icon, label in MENUS:
        is_active = st.session_state["menu"] == label
        if st.button(f"{icon}  {label}", key=f"nav_{label}",
                     use_container_width=True,
                     type="primary" if is_active else "secondary"):
            if label not in st.session_state["open_tabs"]:
                st.session_state["open_tabs"].append(label)
            st.session_state["menu"] = label
            st.rerun()

    if st.session_state["menu"] == "표기사항 검수":
        st.markdown("---")
        st.markdown("<div style='font-size:.8rem;opacity:.7;margin-bottom:.5rem'>⚙️ 검수 설정</div>", unsafe_allow_html=True)
        export_type = st.selectbox("수출/내수 구분",
            ["내수용 (국내)", "수출용 - 미국 FDA", "수출용 - 유럽 EU", "수출용 - 중국"],
            key="export_type")
        check_barcode = st.checkbox("바코드 자동 감지", value=True, key="check_barcode")
        extra_context = st.text_area("추가 지시사항", height=70,
            placeholder="예: 유기농 인증 제품", key="extra_context")

    st.markdown("---")
    with st.popover("⚙️ API / 설정", use_container_width=True):
        st.markdown("### 🔑 API 설정")
        api_key = os.environ.get("GEMINI_API_KEY", "")
        input_key = st.text_input("Gemini API Key", value=api_key, type="password",
                                  help="aistudio.google.com에서 발급")
        if input_key:
            os.environ["GEMINI_API_KEY"] = input_key
        st.markdown("---")
        st.markdown("### 📎 링크")
        st.markdown("[🤖 Google AI Studio](https://aistudio.google.com)")
        st.markdown("[🐙 GitHub 저장소](https://github.com/jiyoonyie-jpg/package_checker)")
        st.markdown("---")
        st.markdown("<div style='font-size:.75rem; color:#888'>커피빈 유통사업팀 전용 시스템<br>문의: coffeebeankorea01@gmail.com</div>", unsafe_allow_html=True)

# ── 탭 바 — 메뉴를 누르면 폴더처럼 열려서 쌓임 ──────────────
with st.container(key="tabbar"):
    tabs = st.session_state["open_tabs"]
    all_cols = st.columns([1.2] + [3] * len(tabs) + [12])
    with all_cols[0]:
        st.markdown("""
        <div class="mac-dots">
          <span class="dot-red"></span><span class="dot-yellow"></span><span class="dot-green"></span>
        </div>""", unsafe_allow_html=True)
    tab_cols = all_cols[1:]
    for i, label in enumerate(tabs):
        is_active = st.session_state["menu"] == label
        group_key = f"tabgroup_active_{i}" if is_active else f"tabgroup_inactive_{i}"
        with tab_cols[i]:
            with st.container(key=group_key):
                lbl_col, x_col = st.columns([5, 1])
                with lbl_col:
                    if st.button(f"{MENU_ICON.get(label,'')} {label}", key=f"tabbtn_{i}",
                                 use_container_width=True):
                        st.session_state["menu"] = label
                        st.rerun()
                with x_col:
                    if st.button("✕", key=f"tabclose_{i}", use_container_width=True):
                        tabs.remove(label)
                        if not tabs:
                            tabs.append("표기사항 검수")
                        if st.session_state["menu"] == label:
                            st.session_state["menu"] = tabs[-1]
                        st.rerun()

menu = st.session_state.get("menu", "표기사항 검수")

# ══════════════════════════════════════════════════════════
# 페이지 1 — 표기사항 검수
# ══════════════════════════════════════════════════════════
if menu == "표기사항 검수":
    col_info, col_design = st.columns([1, 1], gap="medium")

    with col_info:
        with st.container(key="card_info_upload"):
            st.markdown("##### 📋 정보표시면 업로드")
            info_uploaded_list = st.file_uploader("정보표시면 (필수)",
                type=["pdf","png","jpg","jpeg","webp","xlsx","xls"],
                help="정보표시면, 품목제조보고서 등 여러 문서를 함께 올리면 한 번에 분석합니다. · 최대 50MB · 엑셀 가능",
                label_visibility="collapsed", key="info_uploader", accept_multiple_files=True)

            if info_uploaded_list:
                for uf in info_uploaded_list:
                    ub = uf.getvalue()
                    ufi = get_file_info(ub, uf.name)
                    chip_col, view_col = st.columns([4, 1])
                    file_icon = "📊" if ufi["is_excel"] else "📄"
                    with chip_col:
                        st.markdown(f"""
                        <div style="background:#FAF5FF;border:1px solid #DDD6FE;border-radius:10px;
                          padding:.5rem .8rem;font-size:.85rem;margin:.4rem 0">
                          {file_icon} <b>{ufi['filename']}</b>
                          <span style="color:#7C3AED">· {ufi['size_kb']} KB</span>
                        </div>""", unsafe_allow_html=True)
                    with view_col:
                        with st.popover("👁 보기", use_container_width=True):
                            if ufi["is_pdf"]:
                                imgs = pdf_to_images(ub)
                                if imgs and "error" not in imgs[0]:
                                    st.image(imgs[0]["bytes"], use_container_width=True)
                            elif ufi["is_excel"]:
                                st.text(extract_excel_text(ub))
                            else:
                                st.image(ub, use_container_width=True)

                if st.session_state.get("check_barcode", True):
                    all_barcodes = []
                    for uf in info_uploaded_list:
                        fi_chk = get_file_info(uf.getvalue(), uf.name)
                        if fi_chk["is_image"]:
                            bc_result = detect_barcodes(uf.getvalue())
                            if bc_result and "error" not in bc_result[0]:
                                all_barcodes.extend(bc_result)
                    if all_barcodes:
                        st.success(f"✅ 바코드 {len(all_barcodes)}개 감지됨")
                        for bc in all_barcodes:
                            st.code(f"{bc['type']}: {bc['data']}")
                    else:
                        st.info("바코드 자동 감지 불가 (AI가 직접 확인)")

    with col_design:
        with st.container(key="card_design_upload"):
            st.markdown("##### 🎨 디자인 시안 업로드")
            design_uploaded = st.file_uploader("디자인 시안",
                type=["pdf","png","jpg","jpeg","webp"], help="최대 50MB · 승인된 디자인 시안과 비교 검증",
                label_visibility="collapsed", key="design_uploader")

            if design_uploaded:
                design_bytes = design_uploaded.getvalue()
                design_fi = get_file_info(design_bytes, design_uploaded.name)
                dchip_col, dview_col = st.columns([4, 1])
                with dchip_col:
                    st.markdown(f"""
                    <div style="background:#FAF5FF;border:1px solid #DDD6FE;border-radius:10px;
                      padding:.5rem .8rem;font-size:.85rem;margin:.4rem 0">
                      📄 <b>{design_fi['filename']}</b>
                      <span style="color:#7C3AED">· {design_fi['size_kb']} KB</span>
                    </div>""", unsafe_allow_html=True)
                with dview_col:
                    with st.popover("👁 보기", use_container_width=True):
                        if design_fi["is_pdf"]:
                            imgs = pdf_to_images(design_bytes)
                            if imgs and "error" not in imgs[0]:
                                st.image(imgs[0]["bytes"], use_container_width=True)
                        else:
                            st.image(design_bytes, use_container_width=True)
    if "result" in st.session_state:
        _top_result = st.session_state["result"]
        _top_score = _top_result.get("overall_score", 0)
        _top_sc = "score-high" if _top_score >= 80 else "score-mid" if _top_score >= 60 else "score-low"
        _top_grade = "우수" if _top_score >= 80 else "보통" if _top_score >= 60 else "미흡"
        _top_color = "#22C55E" if _top_score >= 80 else "#F59E0B" if _top_score >= 60 else "#F43F5E"
        with st.container(key="card_summary_top"):
            sc1, sc2 = st.columns([1, 3])
            with sc1:
                st.markdown(f"""
                <div class="score-card {_top_sc}" style="padding:.8rem;">
                  <div class="score-num" style="font-size:2.2rem;color:{_top_color}">{_top_score}</div>
                  <div style="font-size:.85rem;font-weight:600;color:{_top_color};margin-top:.2rem">{_top_grade}</div>
                </div>""", unsafe_allow_html=True)
            with sc2:
                st.markdown(f"""
                <div class="summary-box" style="margin:0;height:100%;display:flex;align-items:center;">
                  💬 <b>검수 요약:</b> {_top_result.get('summary','')}
                </div>""", unsafe_allow_html=True)

    with st.container(key="card_start"):
        if st.button("🚀 검수 시작", type="primary", use_container_width=True):
            if not info_uploaded_list:
                st.error("📋 정보표시면 파일을 먼저 업로드해주세요.")
            elif not design_uploaded:
                st.error("🎨 디자인 시안 파일을 먼저 업로드해주세요.")
            elif not os.environ.get("GEMINI_API_KEY"):
                st.error("⚙️ 우측 상단 설정에서 API Key를 입력해주세요.")
            else:
                with st.spinner("Gemini AI가 분석 중입니다..."):
                    try:
                        et = st.session_state.get("export_type", "내수용 (국내)")
                        ec = st.session_state.get("extra_context", "")
                        ctx = f"[수출 구분: {et}]" + (f" {ec}" if ec else "")

                        design_b64, design_mt = None, None
                        if design_uploaded:
                            design_bytes = design_uploaded.getvalue()
                            design_fi = get_file_info(design_bytes, design_uploaded.name)
                            if design_fi["is_pdf"]:
                                dpages = pdf_to_images(design_bytes)
                                if dpages and "error" not in dpages[0]:
                                    design_b64, design_mt = dpages[0]["base64"], "image/png"
                            else:
                                dmt = {"jpg":"image/jpeg","jpeg":"image/jpeg",
                                       "png":"image/png","webp":"image/webp"}.get(design_fi["extension"],"image/png")
                                design_b64, design_mt = image_to_base64(design_bytes, dmt), dmt

                        info_images = []
                        info_texts = []
                        for uf in info_uploaded_list:
                            ub = uf.getvalue()
                            ufi = get_file_info(ub, uf.name)
                            if ufi["is_pdf"]:
                                upages = pdf_to_images(ub)
                                if upages and "error" not in upages[0]:
                                    info_images.append({"data": upages[0]["base64"], "mime_type": "image/png"})
                            elif ufi["is_excel"]:
                                info_texts.append({"filename": ufi["filename"], "text": extract_excel_text(ub)})
                            else:
                                umt = {"jpg":"image/jpeg","jpeg":"image/jpeg",
                                       "png":"image/png","webp":"image/webp"}.get(ufi["extension"],"image/png")
                                info_images.append({"data": image_to_base64(ub, umt), "mime_type": umt})

                        result = analyze_images_with_gemini(info_images, ctx, design_b64, design_mt, info_texts)

                        first_bytes = info_uploaded_list[0].getvalue()
                        first_fi = get_file_info(first_bytes, info_uploaded_list[0].name)
                        st.session_state.update({"result": result, "fi": first_fi,
                            "file_bytes": first_bytes, "is_pdf": first_fi["is_pdf"],
                            "has_design": design_uploaded is not None})
                        st.success("✅ 검수 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    # ── 결과 ────────────────────────────────────────────────
    if "result" in st.session_state:
        result = st.session_state["result"]
        fi = st.session_state["fi"]

        st.markdown("---")

        field_names = {
            "product_name":"제품명","manufacturer":"제조자/수입자","content_weight":"내용량",
            "ingredients":"원재료명","nutrition_facts":"영양성분표","expiry_date":"유통기한/소비기한",
            "storage_method":"보관방법","allergen":"알레르기 유발물질",
            "country_of_origin":"원산지","food_type":"식품유형","barcode":"바코드",
        }
        cf, cv = st.columns([1,1], gap="medium")
        with cf:
            with st.container(key="card_fields"):
                st.markdown("##### 📋 항목별 결과")
                detected = result.get("detected_fields", {})
                for fid, fname in field_names.items():
                    fd = detected.get(fid, {})
                    found = fd.get("found", False)
                    issue = fd.get("issue")
                    val = str(fd.get("value") or "")
                    badge = "badge-ok" if found else "badge-fail"
                    row = "field-ok" if found else "field-fail"
                    val_html = f'<span style="color:#888;font-size:.78rem"> — {val[:26]}</span>' if val and found else ""
                    issue_html = f'<br><span style="color:#F43F5E;font-size:.78rem">⚠ {issue}</span>' if issue and issue not in ("null", None) else ""
                    st.markdown(f"""
                    <div class="field-row {row}">
                      <span class="field-badge {'badge-ok' if found else 'badge-fail'}">{'✓' if found else '✗'}</span>
                      <span><b>{fname}</b>{val_html}{issue_html}</span>
                    </div>""", unsafe_allow_html=True)

        with cv:
            with st.container(key="card_violations"):
                violations = result.get("violations", [])
                warnings = result.get("warnings", [])
                st.markdown(f"##### ⚠️ 위반 사항 ({len(violations)}건)")
                if violations:
                    for v in violations:
                        sev = v.get("severity","medium")
                        sl = {"high":"🔴 긴급","medium":"🟡 주의","low":"🟢 경미"}.get(sev,sev)
                        st.markdown(f"""
                        <div class="violation-card v-{sev}">
                          <div style="font-size:.78rem;font-weight:600">{sl} · {v.get('field','')}</div>
                          <div style="margin-top:.2rem">{v.get('message','')}</div>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.success("위반 사항이 없습니다!")
                if warnings:
                    st.markdown(f"##### 💡 주의사항 ({len(warnings)}건)")
                    for w in warnings:
                        st.markdown(f"""
                        <div class="violation-card v-warn">
                          <div style="font-size:.78rem;font-weight:600">💡 {w.get('field','')}</div>
                          <div style="margin-top:.2rem">{w.get('message','')}</div>
                        </div>""", unsafe_allow_html=True)

        if st.session_state.get("has_design") and result.get("design_consistency"):
            with st.container(key="card_design_consistency"):
                st.markdown(f"##### 🔍 디자인 시안 대비 일치성 ({len(result['design_consistency'])}건)")
                for d in result["design_consistency"]:
                    st.markdown(f"""
                    <div class="violation-card v-warn">
                      <div style="font-size:.78rem;font-weight:600">🔍 {d.get('item','')}</div>
                      <div style="margin-top:.2rem">{d.get('issue','')}</div>
                    </div>""", unsafe_allow_html=True)

        if result.get("typos"):
            with st.container(key="card_typos"):
                st.markdown(f"##### ✏️ 오탈자/맞춤법 ({len(result['typos'])}건)")
                for t in result["typos"]:
                    st.markdown(f"""
                    <div class="violation-card v-medium">
                      <div style="font-size:.78rem;font-weight:600">✏️ {t.get('location','')} · "{t.get('found_text','')}"</div>
                      <div style="margin-top:.2rem">{t.get('issue','')}</div>
                      <div style="margin-top:.2rem;color:#7C3AED">💡 제안: {t.get('suggestion','')}</div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("##### 📥 내보내기")
        d1, d2, d3 = st.columns(3)
        with d1:
            st.download_button("📊 엑셀 다운로드",
                data=export_to_excel(result, fi),
                file_name=f"검수결과_{fi['filename'].replace('.','_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
        with d2:
            st.download_button("📄 JSON 다운로드",
                data=json.dumps(result, ensure_ascii=False, indent=2).encode(),
                file_name=f"검수결과_{fi['filename'].replace('.','_')}.json",
                mime="application/json", use_container_width=True)
        with d3:
            if st.button("📝 상세 리포트", use_container_width=True):
                st.session_state["report"] = generate_report_text(result, fi)
        if "report" in st.session_state:
            st.text_area("상세 리포트", st.session_state["report"], height=200)

# ══════════════════════════════════════════════════════════
# 페이지 2 — 패키지 디자인 생성
# ══════════════════════════════════════════════════════════
elif menu == "패키지 디자인 생성":
    with st.container(key="card_design_input"):
        st.markdown("##### 🎨 패키지 디자인 AI 생성")
        st.markdown("<span style='font-size:.9rem;color:#7C3AED'>원하는 패키지 디자인을 자유롭게 설명해주세요. AI가 이미지를 생성합니다.</span>", unsafe_allow_html=True)

        design_input = st.text_area(
            "디자인 설명",
            value=st.session_state.get("design_prompt", ""),
            height=250,
            placeholder=(
                "예시:\n"
                "가로로 긴 직사각형의 인스턴트 커피 패키지\n"
                "제품명은 '커피빈 리치 블렌드 커피믹스'\n"
                "입수량 20STICKS\n"
                "색상은 노란색 배경에 보라색으로 포인트. 캐릭터가 있으면 좋겠어."
            ),
            label_visibility="collapsed"
        )

        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            show_brief = st.checkbox("디자인 브리프 먼저 생성 (추천)", value=True)
        with col_opt2:
            num_variants = st.selectbox("생성 수량", [1, 2, 3], index=0)

        if st.button("✨ 디자인 생성", type="primary", use_container_width=True):
            if not os.environ.get("GEMINI_API_KEY"):
                st.error("⚙️ 우측 상단 설정에서 API Key를 입력해주세요.")
            elif not design_input.strip():
                st.warning("디자인 설명을 입력해주세요.")
            else:
                if show_brief:
                    with st.spinner("디자인 브리프 작성 중..."):
                        st.session_state["design_brief"] = refine_design_description(design_input)
                with st.spinner("AI가 패키지 이미지를 생성 중입니다... (30~60초 소요)"):
                    st.session_state["design_results"] = [
                        generate_package_design(design_input, seed=random.randint(1,9999))
                        for _ in range(num_variants)
                    ]
                st.rerun()

    if "design_brief" in st.session_state:
        with st.expander("📋 AI 디자인 브리프", expanded=True):
            st.markdown(st.session_state["design_brief"])

    if "design_results" in st.session_state:
        st.markdown("---")
        st.markdown("##### 생성된 디자인")
        img_cols = st.columns(len(st.session_state["design_results"]))
        for i, res in enumerate(st.session_state["design_results"]):
            with img_cols[i]:
                if "error" in res:
                    st.error(f"생성 실패: {res['error']}")
                else:
                    img_bytes = base64.b64decode(res["image_b64"])
                    st.image(img_bytes, caption=f"디자인 {i+1}", use_container_width=True)
                    st.download_button(f"⬇ 다운로드 {i+1}", data=img_bytes,
                        file_name=f"package_design_{i+1}.png", mime="image/png",
                        use_container_width=True, key=f"dl_{i}")

# ══════════════════════════════════════════════════════════
# 페이지 3 — 검수 기준 안내
# ══════════════════════════════════════════════════════════
elif menu == "검수 기준 안내":
    st.markdown("##### 📖 식품 표기사항 검수 기준")
    reg_path = os.path.join(os.path.dirname(__file__), "data/regulations.json")
    with open(reg_path, "r", encoding="utf-8") as f:
        regs = json.load(f)

    st.markdown("**필수 표기 항목**")
    cols = st.columns(2)
    for i, field in enumerate(regs["required_fields"]):
        with cols[i % 2]:
            badge = "🔴 필수" if field["required"] else "🟡 권장"
            st.markdown(f"""
            <div class="card" style="margin-bottom:.5rem">
              <b>{field['name']}</b> <span style="font-size:.78rem">{badge}</span><br>
              <span style="font-size:.82rem;color:#7C3AED">{field['description']}</span>
            </div>""", unsafe_allow_html=True)

    st.markdown("**자주 발생하는 위반 사례**")
    with st.container(key="card_common_violations"):
        for v in regs["common_violations"]:
            st.markdown(f"- ⚠️ {v}")

    st.markdown("**수출 국가별 추가 요건**")
    for country, fields in regs["export_requirements"].items():
        label = {"us_fda":"🇺🇸 미국 FDA","eu":"🇪🇺 유럽 EU","china":"🇨🇳 중국"}.get(country, country)
        st.markdown(f"**{label}**: {', '.join(fields)}")
