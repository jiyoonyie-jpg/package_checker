import streamlit as st
import json, os, base64, sys, random
sys.path.insert(0, os.path.dirname(__file__))

from utils.extractor import pdf_to_images, image_to_base64, detect_barcodes, get_file_info
from utils.analyzer import analyze_image_with_gemini, analyze_pdf_pages, generate_report_text
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
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');

/* 전체 기본 */
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
    background-color: #F5F3FF;
}

/* Streamlit 기본 요소 숨기기 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stDecoration"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
.stDeployButton {display: none !important;}

/* 헤더 투명화 (토글 버튼 영역은 살림) */
header[data-testid="stHeader"] {
    background: transparent !important;
    box-shadow: none !important;
    height: 3rem !important;
}
/* 사이드바 토글 버튼 강제 표시 */
[data-testid="collapsedControl"],
section[data-testid="stSidebarCollapsedControl"],
.st-emotion-cache-1lna757,
button[title="Collapse sidebar"],
button[title="Expand sidebar"],
button[aria-label="Collapse sidebar"],
button[aria-label="Expand sidebar"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 9999 !important;
}

/* 사이드바 — 그라디언트 + 노이즈 텍스처 */
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(145deg,
        rgba(169,140,76,0.95),
        rgba(108,149,214,0.95),
        rgba(124,43,117,0.95)) !important;
    position: relative !important;
}
[data-testid="stSidebar"] > div:first-child::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='400' height='400' filter='url(%23n)' opacity='0.18'/%3E%3C/svg%3E");
    background-repeat: repeat;
    background-size: 400px 400px;
    mix-blend-mode: overlay;
    pointer-events: none;
    z-index: 0;
}
[data-testid="stSidebar"] {
    border-right: none;
}
[data-testid="stSidebar"] * {color: #EDE9FE !important;}
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.1) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: all .2s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.22) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(255,255,255,0.28) !important;
    border: 1px solid rgba(255,255,255,0.5) !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] hr {border-color: rgba(255,255,255,0.2) !important;}
[data-testid="stSidebar"] label {color: #DDD6FE !important;}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: white !important;
}
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: white !important;
}

/* 헤더 */
.main-header {
    position: sticky;
    top: 0;
    z-index: 999;
    width: 100%;
    padding: 1.1rem 2rem;
    border-radius: 0 0 16px 16px;
    margin-bottom: 1.5rem;
    background: linear-gradient(145deg,
        rgba(169,140,76,0.95),
        rgba(108,149,214,0.95),
        rgba(124,43,117,0.95));
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 4px 20px rgba(76,29,149,0.25);
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
        repeating-linear-gradient(
            45deg,
            rgba(255,255,255,0.04) 0px,
            rgba(255,255,255,0.04) 1px,
            transparent 1px,
            transparent 14px
        ),
        repeating-linear-gradient(
            -45deg,
            rgba(255,255,255,0.04) 0px,
            rgba(255,255,255,0.04) 1px,
            transparent 1px,
            transparent 14px
        );
    pointer-events: none;
}
.main-header h1 {
    font-size: 1.4rem;
    font-weight: 700;
    color: white;
    margin: 0;
    text-shadow: 0 1px 8px rgba(0,0,0,0.3);
    position: relative;
}
.main-header p {
    font-size: .8rem;
    color: rgba(255,255,255,.8);
    margin: .2rem 0 0;
    position: relative;
}

/* 메인 콘텐츠 배경 */
.main .block-container {
    background: #F5F3FF;
    padding-top: 0 !important;
}

/* 카드 */
.card {
    background: white;
    border: 1px solid #DDD6FE;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 12px rgba(109,40,217,0.07);
}

/* 점수 카드 */
.score-card {
    padding: 1.4rem;
    border-radius: 14px;
    text-align: center;
    border: 2px solid;
}
.score-high { background: #F0FDF4; border-color: #22C55E; }
.score-mid  { background: #FFFBEB; border-color: #F59E0B; }
.score-low  { background: #FFF1F2; border-color: #F43F5E; }
.score-num  { font-size: 3rem; font-weight: 700; line-height: 1; }

/* 항목 행 */
.field-row {
    display: flex; align-items: flex-start; gap: 8px;
    padding: .5rem .8rem; border-radius: 10px; margin-bottom: .3rem; font-size: .88rem;
}
.field-ok   { background: #F0FDF4; }
.field-fail { background: #FFF1F2; }
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
}
.v-high   { background: #FFF1F2; border-color: #F43F5E; }
.v-medium { background: #FFFBEB; border-color: #F59E0B; }
.v-low    { background: #F0FDF4; border-color: #22C55E; }
.v-warn   { background: #EFF6FF; border-color: #3B82F6; }

/* 버튼 */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6D28D9, #7C3AED) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 600 !important;
    padding: .6rem 1.2rem !important;
    box-shadow: 0 4px 14px rgba(109,40,217,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #5B21B6, #6D28D9) !important;
    box-shadow: 0 6px 18px rgba(109,40,217,0.45) !important;
}

/* 파일 업로더 */
[data-testid="stFileUploader"] {
    border: 2px dashed #A78BFA !important;
    border-radius: 12px !important;
    background: #FAF5FF !important;
}

/* 요약 박스 */
.summary-box {
    background: linear-gradient(135deg, #FAF5FF, #F3E8FF);
    border: 1px solid #C4B5FD;
    border-radius: 12px;
    padding: .9rem 1.1rem;
    font-size: .92rem;
    color: #4C1D95;
    margin: 1rem 0;
}

/* 다운로드 버튼 */
.stDownloadButton > button {
    background: white !important;
    border: 1.5px solid #A78BFA !important;
    color: #6D28D9 !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
}
.stDownloadButton > button:hover {
    background: #F5F3FF !important;
    border-color: #7C3AED !important;
}

/* 탭 스타일 제거 (페이지 방식이므로) */
.stTabs { display: none; }

/* expander */
[data-testid="stExpander"] {
    border: 1px solid #DDD6FE !important;
    border-radius: 12px !important;
    background: white !important;
}

/* selectbox, checkbox */
.stSelectbox > div > div {
    border-color: #C4B5FD !important;
    border-radius: 10px !important;
}
.stCheckbox > label { color: #EDE9FE !important; }
</style>
""", unsafe_allow_html=True)

# ── 메뉴 상태 ─────────────────────────────────────────────
if "menu" not in st.session_state:
    st.session_state["menu"] = "표기사항 검수"

# ── 사이드바 ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:.8rem 0 .5rem; text-align:center;">
      <div style="font-size:1.8rem">🎨</div>
      <div style="font-size:.85rem; color:#C4B5FD; margin-top:.2rem">커피빈 AI 시스템</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    menus = [("🔍", "표기사항 검수"), ("🎨", "패키지 디자인 생성"), ("📖", "검수 기준 안내")]
    for icon, label in menus:
        is_active = st.session_state["menu"] == label
        if st.button(f"{icon}  {label}", key=f"nav_{label}",
                     use_container_width=True,
                     type="primary" if is_active else "secondary"):
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
        st.markdown("""
        <div style='font-size:.78rem; opacity:.7; line-height:2'>
        ✅ 제품명 / 식품유형<br>
        ✅ 원재료명 및 함량<br>
        ✅ 영양성분표<br>
        ✅ 유통기한/소비기한<br>
        ✅ 알레르기 유발물질<br>
        ✅ 원산지 / 제조자<br>
        ✅ 보관방법 / 바코드
        </div>""", unsafe_allow_html=True)

# ── 헤더 + 설정 팝오버 ────────────────────────────────────
hcol1, hcol2 = st.columns([11, 1])
with hcol1:
    st.markdown("""
    <div class="main-header">
      <div>
        <h1>🎨 커피빈 유통 패키지 디자인 AI 검수 시스템</h1>
        <p>식품위생법 기반 AI 표기 검수 · 패키지 디자인 생성 · Powered by Google Gemini</p>
      </div>
    </div>
    """, unsafe_allow_html=True)
with hcol2:
    with st.popover("⚙️", use_container_width=True):
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

menu = st.session_state.get("menu", "표기사항 검수")

# ══════════════════════════════════════════════════════════
# 페이지 1 — 표기사항 검수
# ══════════════════════════════════════════════════════════
if menu == "표기사항 검수":
    col_up, col_pre = st.columns([1, 1], gap="medium")

    with col_up:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("##### 📁 파일 업로드")
        uploaded = st.file_uploader("PDF 또는 이미지를 업로드하세요",
            type=["pdf","png","jpg","jpeg","webp"], help="최대 50MB",
            label_visibility="collapsed")

        if uploaded:
            file_bytes = uploaded.read()
            fi = get_file_info(file_bytes, uploaded.name)
            st.markdown(f"""
            <div style="background:#FAF5FF;border:1px solid #DDD6FE;border-radius:10px;
              padding:.6rem 1rem;font-size:.88rem;margin:.5rem 0">
              📄 <b>{fi['filename']}</b> &nbsp;·&nbsp;
              <span style="color:#7C3AED">{fi['size_kb']} KB</span> &nbsp;·&nbsp;
              {fi['extension'].upper()}
            </div>""", unsafe_allow_html=True)

            if st.session_state.get("check_barcode", True) and fi["is_image"]:
                with st.spinner("바코드 감지 중..."):
                    barcodes = detect_barcodes(file_bytes)
                    if barcodes and "error" not in barcodes[0]:
                        st.success(f"✅ 바코드 {len(barcodes)}개 감지됨")
                        for bc in barcodes:
                            st.code(f"{bc['type']}: {bc['data']}")
                    else:
                        st.info("바코드 자동 감지 불가 (AI가 직접 확인)")

            if st.button("🚀 검수 시작", type="primary", use_container_width=True):
                if not os.environ.get("GEMINI_API_KEY"):
                    st.error("⚙️ 우측 상단 설정에서 API Key를 입력해주세요.")
                else:
                    with st.spinner("Gemini AI가 분석 중입니다..."):
                        try:
                            et = st.session_state.get("export_type", "내수용 (국내)")
                            ec = st.session_state.get("extra_context", "")
                            ctx = f"[수출 구분: {et}]" + (f" {ec}" if ec else "")
                            if fi["is_pdf"]:
                                pages = pdf_to_images(file_bytes)
                                result = analyze_pdf_pages(pages, ctx)
                            else:
                                mt = {"jpg":"image/jpeg","jpeg":"image/jpeg",
                                      "png":"image/png","webp":"image/webp"}.get(fi["extension"],"image/png")
                                result = analyze_image_with_gemini(image_to_base64(file_bytes, mt), mt, ctx)
                            st.session_state.update({"result": result, "fi": fi,
                                "file_bytes": file_bytes, "is_pdf": fi["is_pdf"]})
                            st.success("✅ 검수 완료!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"오류: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_pre:
        st.markdown('<div class="card" style="min-height:200px">', unsafe_allow_html=True)
        st.markdown("##### 🖼️ 미리보기")
        if "file_bytes" in st.session_state:
            if st.session_state.get("is_pdf"):
                imgs = pdf_to_images(st.session_state["file_bytes"])
                if imgs and "error" not in imgs[0]:
                    st.image(imgs[0]["bytes"], use_container_width=True)
            else:
                st.image(st.session_state["file_bytes"], use_container_width=True)
        elif uploaded and fi.get("is_image"):
            st.image(file_bytes, use_container_width=True)
        else:
            st.markdown("""
            <div style="height:200px;display:flex;align-items:center;justify-content:center;
              background:#FAF5FF;border-radius:12px;color:#A78BFA;flex-direction:column;gap:8px">
              <div style="font-size:2.5rem">📦</div>
              <div style="font-size:.88rem">파일을 업로드해주세요</div>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── 결과 ────────────────────────────────────────────────
    if "result" in st.session_state:
        result = st.session_state["result"]
        fi = st.session_state["fi"]
        score = result.get("overall_score", 0)
        sc = "score-high" if score >= 80 else "score-mid" if score >= 60 else "score-low"
        grade = "우수" if score >= 80 else "보통" if score >= 60 else "미흡"
        score_color = "#22C55E" if score >= 80 else "#F59E0B" if score >= 60 else "#F43F5E"

        st.markdown("---")
        _, c2, _ = st.columns([1,2,1])
        with c2:
            st.markdown(f"""
            <div class="score-card {sc}">
              <div class="score-num" style="color:{score_color}">{score}</div>
              <div style="font-size:1.1rem;font-weight:600;color:{score_color};margin:.3rem 0">{grade}</div>
              <div style="font-size:.8rem;color:#888">100점 만점 종합 점수</div>
            </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="summary-box">
          💬 <b>검수 요약:</b> {result.get('summary','')}
        </div>""", unsafe_allow_html=True)

        field_names = {
            "product_name":"제품명","manufacturer":"제조자/수입자","content_weight":"내용량",
            "ingredients":"원재료명","nutrition_facts":"영양성분표","expiry_date":"유통기한/소비기한",
            "storage_method":"보관방법","allergen":"알레르기 유발물질",
            "country_of_origin":"원산지","food_type":"식품유형","barcode":"바코드",
        }
        cf, cv = st.columns([1,1], gap="medium")
        with cf:
            st.markdown('<div class="card">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)

        with cv:
            violations = result.get("violations", [])
            warnings = result.get("warnings", [])
            st.markdown('<div class="card">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)

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
    st.markdown('<div class="card">', unsafe_allow_html=True)
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

    st.markdown('</div>', unsafe_allow_html=True)

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
    st.markdown('<div class="card">', unsafe_allow_html=True)
    for v in regs["common_violations"]:
        st.markdown(f"- ⚠️ {v}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("**수출 국가별 추가 요건**")
    for country, fields in regs["export_requirements"].items():
        label = {"us_fda":"🇺🇸 미국 FDA","eu":"🇪🇺 유럽 EU","china":"🇨🇳 중국"}.get(country, country)
        st.markdown(f"**{label}**: {', '.join(fields)}")
