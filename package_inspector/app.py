import streamlit as st
import json
import os
import base64
import sys

sys.path.insert(0, os.path.dirname(__file__))
from utils.extractor import (
    extract_text_from_pdf, pdf_to_images, image_to_base64,
    detect_barcodes, get_file_info,
)
from utils.analyzer import (
    analyze_image_with_gemini, analyze_pdf_pages,
    generate_report_text,
)
from utils.designer import generate_package_design, refine_design_description
from utils.reporter import export_to_excel

st.set_page_config(
    page_title="패키지 AI 검수 & 디자인",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
html,body,[class*="css"]{font-family:'Noto Sans KR',sans-serif}

.main-header{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
  padding:1.4rem 2rem;border-radius:14px;color:white;margin-bottom:1.5rem}
.main-header h1{font-size:1.5rem;font-weight:700;margin:0 0 .3rem}
.main-header p{font-size:.85rem;opacity:.8;margin:0}

/* 사이드바 메뉴 */
.nav-btn {
    width:100%;text-align:left;padding:.75rem 1rem;border-radius:10px;
    border:none;cursor:pointer;font-size:.95rem;font-weight:500;
    margin-bottom:.3rem;transition:background .15s;
}
.nav-btn-active{background:#0f3460;color:white}
.nav-btn-inactive{background:transparent;color:#444}
.nav-btn-inactive:hover{background:#f0f2f6}

.score-card{padding:1.2rem;border-radius:12px;text-align:center;border:1px solid}
.score-high{background:#e8f5e9;border-color:#4caf50}
.score-mid{background:#fff8e1;border-color:#ff9800}
.score-low{background:#ffebee;border-color:#f44336}
.score-num{font-size:3rem;font-weight:700;line-height:1}
.score-label{font-size:.8rem;color:#666;margin-top:.2rem}

.field-row{display:flex;align-items:flex-start;gap:8px;padding:.5rem .8rem;
  border-radius:8px;margin-bottom:.3rem;font-size:.88rem}
.field-ok{background:#f1f8e9}.field-fail{background:#fce4ec}
.field-badge{width:20px;height:20px;border-radius:50%;display:inline-flex;
  align-items:center;justify-content:center;font-size:.7rem;font-weight:700;
  flex-shrink:0;margin-top:2px}
.badge-ok{background:#4caf50;color:white}.badge-fail{background:#f44336;color:white}

.violation-card{padding:.7rem 1rem;border-radius:8px;margin-bottom:.4rem;
  border-left:4px solid;font-size:.88rem}
.v-high{background:#ffebee;border-color:#f44336}
.v-medium{background:#fff8e1;border-color:#ff9800}
.v-low{background:#f3f9e7;border-color:#8bc34a}
.v-warn{background:#e3f2fd;border-color:#2196f3}
</style>
""", unsafe_allow_html=True)

# ── 헤더 ────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>🎨 패키지 AI 검수 &amp; 디자인 시스템</h1>
  <p>식품표기 AI 검수 · Gemini Imagen 패키지 디자인 생성 · Powered by Google Gemini</p>
</div>
""", unsafe_allow_html=True)

# ── 사이드바: API 키 + 메뉴 네비게이션 ──────────────────
with st.sidebar:
    st.markdown("### 🔑 API 설정")
    api_key = os.environ.get("GEMINI_API_KEY", "")
    input_key = st.text_input("Gemini API Key", value=api_key, type="password",
                              help="발급: aistudio.google.com")
    if input_key:
        os.environ["GEMINI_API_KEY"] = input_key

    st.markdown("---")
    st.markdown("### 📌 메뉴")

    if "menu" not in st.session_state:
        st.session_state["menu"] = "검수"

    menus = [
        ("🔍", "표기사항 검수"),
        ("🎨", "패키지 디자인 생성"),
        ("📖", "검수 기준 안내"),
    ]
    for icon, label in menus:
        is_active = st.session_state["menu"] == label
        if st.button(f"{icon}  {label}", key=f"nav_{label}",
                     use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state["menu"] = label
            st.rerun()

    # 검수 메뉴일 때만 설정 표시
    if st.session_state["menu"] == "표기사항 검수":
        st.markdown("---")
        st.markdown("### ⚙️ 검수 설정")
        export_type = st.selectbox("수출/내수 구분",
            ["내수용 (국내)", "수출용 - 미국 FDA", "수출용 - 유럽 EU", "수출용 - 중국"],
            key="export_type")
        check_barcode = st.checkbox("바코드 자동 감지", value=True, key="check_barcode")
        extra_context = st.text_area("추가 검수 지시사항", height=80,
            placeholder="예: 유기농 인증 제품입니다.", key="extra_context")

        st.markdown("---")
        st.markdown("### 📋 검수 항목")
        st.markdown("""
        ✅ 제품명 / 식품유형
        ✅ 원재료명 및 함량
        ✅ 영양성분표
        ✅ 유통기한/소비기한
        ✅ 알레르기 유발물질
        ✅ 원산지 / 제조자
        ✅ 보관방법
        ✅ 바코드 위치
        """)

menu = st.session_state.get("menu", "표기사항 검수")

# ══════════════════════════════════════════════════════
# 페이지 1 — 표기사항 검수
# ══════════════════════════════════════════════════════
if menu == "표기사항 검수":
    col_up, col_pre = st.columns([1, 1])

    with col_up:
        st.markdown("#### 파일 업로드")
        uploaded = st.file_uploader("PDF 또는 이미지를 업로드하세요",
            type=["pdf","png","jpg","jpeg","webp"], help="최대 50MB")

        if uploaded:
            file_bytes = uploaded.read()
            fi = get_file_info(file_bytes, uploaded.name)
            st.markdown(f"**📄 {fi['filename']}** — {fi['size_kb']} KB | {fi['extension'].upper()}")

            check_barcode = st.session_state.get("check_barcode", True)
            if check_barcode and fi["is_image"]:
                with st.spinner("바코드 감지 중..."):
                    barcodes = detect_barcodes(file_bytes)
                    if barcodes and "error" not in barcodes[0]:
                        st.success(f"✅ 바코드 {len(barcodes)}개 감지")
                        for bc in barcodes:
                            st.code(f"{bc['type']}: {bc['data']}")
                    else:
                        st.info("자동 감지 불가 (AI가 이미지에서 직접 확인합니다)")

            if st.button("🚀 검수 시작", type="primary", use_container_width=True):
                if not os.environ.get("GEMINI_API_KEY"):
                    st.error("API Key를 사이드바에서 입력해주세요.")
                else:
                    with st.spinner("Gemini가 분석 중입니다..."):
                        try:
                            export_type = st.session_state.get("export_type", "내수용 (국내)")
                            extra_context = st.session_state.get("extra_context", "")
                            ctx = f"[수출 구분: {export_type}]"
                            if extra_context:
                                ctx += f" {extra_context}"
                            if fi["is_pdf"]:
                                pages = pdf_to_images(file_bytes)
                                result = analyze_pdf_pages(pages, ctx)
                            else:
                                ext_map = {"jpg":"image/jpeg","jpeg":"image/jpeg",
                                           "png":"image/png","webp":"image/webp"}
                                mt = ext_map.get(fi["extension"], "image/png")
                                b64 = image_to_base64(file_bytes, mt)
                                result = analyze_image_with_gemini(b64, mt, ctx)
                            st.session_state["result"] = result
                            st.session_state["fi"] = fi
                            st.session_state["file_bytes"] = file_bytes
                            st.session_state["is_pdf"] = fi["is_pdf"]
                            st.success("✅ 검수 완료!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"오류: {e}")

    with col_pre:
        st.markdown("#### 미리보기")
        if "file_bytes" in st.session_state:
            if st.session_state.get("is_pdf"):
                imgs = pdf_to_images(st.session_state["file_bytes"])
                if imgs and "error" not in imgs[0]:
                    st.image(imgs[0]["bytes"], caption="PDF 첫 페이지", use_container_width=True)
            else:
                st.image(st.session_state["file_bytes"],
                         caption=st.session_state["fi"]["filename"],
                         use_container_width=True)
        elif uploaded and fi["is_image"]:
            st.image(file_bytes, caption=uploaded.name, use_container_width=True)
        else:
            st.markdown("""
            <div style="height:260px;display:flex;align-items:center;justify-content:center;
                background:#f8f9fa;border-radius:12px;color:#aaa;flex-direction:column">
                <div style="font-size:2.5rem">📦</div>
                <div style="margin-top:.5rem;font-size:.9rem">파일 업로드 후 미리보기</div>
            </div>""", unsafe_allow_html=True)

    if "result" in st.session_state:
        result = st.session_state["result"]
        fi = st.session_state["fi"]
        st.markdown("---")
        st.markdown("## 📊 검수 결과")

        score = result.get("overall_score", 0)
        sc = "score-high" if score >= 80 else "score-mid" if score >= 60 else "score-low"
        grade = "우수" if score >= 80 else "보통" if score >= 60 else "미흡"
        _, c2, _ = st.columns([1,2,1])
        with c2:
            st.markdown(f"""
            <div class="score-card {sc}">
              <div class="score-num">{score}</div>
              <div style="font-size:1.1rem;font-weight:600">{grade}</div>
              <div class="score-label">100점 만점</div>
            </div>""", unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:#f8f9fa;border-radius:10px;padding:.9rem 1rem;margin:1rem 0;font-size:.92rem">
          💬 <b>요약:</b> {result.get('summary','')}
        </div>""", unsafe_allow_html=True)

        field_names = {
            "product_name":"제품명","manufacturer":"제조자/수입자",
            "content_weight":"내용량","ingredients":"원재료명",
            "nutrition_facts":"영양성분표","expiry_date":"유통기한/소비기한",
            "storage_method":"보관방법","allergen":"알레르기 유발물질",
            "country_of_origin":"원산지","food_type":"식품유형","barcode":"바코드",
        }
        c_f, c_v = st.columns([1,1])
        with c_f:
            st.markdown("#### 📋 항목별 결과")
            detected = result.get("detected_fields", {})
            for fid, fname in field_names.items():
                fd = detected.get(fid, {})
                found = fd.get("found", False)
                issue = fd.get("issue")
                val = str(fd.get("value") or "")
                badge = "badge-ok" if found else "badge-fail"
                row = "field-ok" if found else "field-fail"
                icon = "✓" if found else "✗"
                val_html = f'<span style="color:#888;font-size:.78rem"> — {val[:28]}</span>' if val and found else ""
                issue_html = f'<br><span style="color:#c62828;font-size:.78rem">⚠ {issue}</span>' if issue and issue != "null" else ""
                st.markdown(f"""
                <div class="field-row {row}">
                  <span class="field-badge {badge}">{icon}</span>
                  <span><b>{fname}</b>{val_html}{issue_html}</span>
                </div>""", unsafe_allow_html=True)

        with c_v:
            violations = result.get("violations", [])
            warnings = result.get("warnings", [])
            st.markdown(f"#### ⚠️ 위반 사항 ({len(violations)}건)")
            if violations:
                for v in violations:
                    sev = v.get("severity","medium")
                    sl = {"high":"🔴 긴급","medium":"🟡 주의","low":"🟢 경미"}.get(sev,sev)
                    st.markdown(f"""
                    <div class="violation-card v-{sev}">
                      <div style="font-size:.78rem;font-weight:600">{sl} · {v.get('field','')}</div>
                      <div>{v.get('message','')}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.success("위반 사항 없음!")
            if warnings:
                st.markdown(f"#### 💡 주의사항 ({len(warnings)}건)")
                for w in warnings:
                    st.markdown(f"""
                    <div class="violation-card v-warn">
                      <div style="font-size:.78rem;font-weight:600">💡 {w.get('field','')}</div>
                      <div>{w.get('message','')}</div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📥 내보내기")
        d1, d2, d3 = st.columns(3)
        with d1:
            excel = export_to_excel(result, fi)
            st.download_button("📊 엑셀 다운로드", data=excel,
                file_name=f"검수결과_{fi['filename'].replace('.','_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
        with d2:
            st.download_button("📄 JSON 다운로드",
                data=json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=f"검수결과_{fi['filename'].replace('.','_')}.json",
                mime="application/json", use_container_width=True)
        with d3:
            if st.button("📝 리포트 생성", use_container_width=True):
                st.session_state["report"] = generate_report_text(result, fi)
        if "report" in st.session_state:
            st.text_area("상세 리포트", st.session_state["report"], height=200)

# ══════════════════════════════════════════════════════
# 페이지 2 — 패키지 디자인 생성
# ══════════════════════════════════════════════════════
elif menu == "패키지 디자인 생성":
    st.markdown("#### 🎨 패키지 디자인 AI 생성")
    st.markdown("원하는 패키지 디자인을 자유롭게 설명해주세요. AI가 이미지를 생성합니다.")

    example_prompts = [
        "가로로 긴 직사각형 인스턴트 커피 패키지, 기본 색상 노란색, 포인트 보라색",
        "원통형 과자 패키지, 민트색 배경에 흰색 로고, 프리미엄 느낌",
        "슬림한 초코바 패키지, 다크초콜릿 브라운과 골드 색상",
        "정사각형 녹차 음료 패키지, 연두색 그라디언트, 일본 감성",
        "파우치형 스낵 패키지, 빨간색 배경, 귀여운 캐릭터 스타일",
    ]
    st.markdown("**빠른 예시:**")
    cols_chip = st.columns(len(example_prompts))
    for i, ep in enumerate(example_prompts):
        with cols_chip[i]:
            if st.button(ep[:15] + "...", key=f"chip_{i}", use_container_width=True):
                st.session_state["design_prompt"] = ep

    st.markdown("---")

    design_input = st.text_area(
        "디자인 설명",
        value=st.session_state.get("design_prompt", ""),
        height=250,
        placeholder=(
            "예시:\n"
            "가로로 긴 직사각형의 인스턴트 커피 패키지\n"
            "제품명은 '커피빈 리치 블렌드 커피믹스'\n"
            "입수량 20STICKS\n"
            "색상은 노란색 배경에 보라색으로 포인트 줘. 그리고 캐릭터가 있음 좋겠어."
        ),
    )

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        show_brief = st.checkbox("디자인 브리프 먼저 생성 (추천)", value=True)
    with col_opt2:
        num_variants = st.selectbox("생성 수량", [1, 2, 3], index=0)

    if st.button("✨ 디자인 생성", type="primary", use_container_width=True):
        if not os.environ.get("GEMINI_API_KEY"):
            st.error("API Key를 사이드바에서 입력해주세요.")
        elif not design_input.strip():
            st.warning("디자인 설명을 입력해주세요.")
        else:
            if show_brief:
                with st.spinner("디자인 브리프 작성 중..."):
                    brief = refine_design_description(design_input)
                    st.session_state["design_brief"] = brief

            with st.spinner("AI가 패키지 디자인 이미지를 생성 중입니다... (30~60초 소요)"):
                import random
                results_design = []
                for i in range(num_variants):
                    seed = random.randint(1, 9999)
                    res = generate_package_design(design_input, seed=seed)
                    results_design.append(res)
                st.session_state["design_results"] = results_design
            st.rerun()

    if "design_brief" in st.session_state:
        with st.expander("📋 AI 디자인 브리프", expanded=True):
            st.markdown(st.session_state["design_brief"])

    if "design_results" in st.session_state:
        results_design = st.session_state["design_results"]
        st.markdown("---")
        st.markdown("#### 생성된 디자인")
        img_cols = st.columns(len(results_design))
        for i, res in enumerate(results_design):
            with img_cols[i]:
                if "error" in res:
                    st.error(f"생성 실패: {res['error']}")
                else:
                    img_bytes = base64.b64decode(res["image_b64"])
                    st.image(img_bytes, caption=f"디자인 {i+1}", use_container_width=True)
                    st.download_button(
                        f"⬇ 디자인 {i+1} 다운로드",
                        data=img_bytes,
                        file_name=f"package_design_{i+1}.png",
                        mime="image/png",
                        use_container_width=True,
                        key=f"dl_design_{i}",
                    )

# ══════════════════════════════════════════════════════
# 페이지 3 — 검수 기준 안내
# ══════════════════════════════════════════════════════
elif menu == "검수 기준 안내":
    st.markdown("### 📖 식품 표기사항 검수 기준")
    reg_path = os.path.join(os.path.dirname(__file__), "data/regulations.json")
    with open(reg_path, "r", encoding="utf-8") as f:
        regs = json.load(f)

    st.markdown("#### 필수 표기 항목")
    cols = st.columns(2)
    for i, field in enumerate(regs["required_fields"]):
        with cols[i % 2]:
            badge = "🔴 필수" if field["required"] else "🟡 권장"
            st.markdown(f"""
            <div style="background:white;border:1px solid #e0e0e0;border-radius:10px;
              padding:.9rem 1rem;margin-bottom:.5rem">
              <b>{field['name']}</b> <span style="font-size:.78rem">{badge}</span><br>
              <span style="font-size:.82rem;color:#666">{field['description']}</span>
            </div>""", unsafe_allow_html=True)

    st.markdown("#### 자주 발생하는 위반 사례")
    for v in regs["common_violations"]:
        st.markdown(f"- ⚠️ {v}")

    st.markdown("#### 수출 국가별 추가 요건")
    for country, fields in regs["export_requirements"].items():
        label = {"us_fda":"🇺🇸 미국 FDA","eu":"🇪🇺 유럽 EU","china":"🇨🇳 중국"}.get(country, country)
        st.markdown(f"**{label}**: {', '.join(fields)}")
