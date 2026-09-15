import os
import json
import re
from google import genai
from google.genai import types

def _client():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    return genai.Client(api_key=api_key)

SYSTEM_PROMPT = """당신은 한국 식품위생법 및 식품 등의 표시기준 전문가입니다.
정보표시면, 품목제조보고서 등 함께 제공되는 여러 문서(이미지 또는 엑셀에서 추출한 텍스트)를
종합적으로 분석하여 필수 표기사항을 검수하고, 반드시 아래 JSON 형식으로만 응답하세요.
문서가 여러 장이면 서로 다른 문서의 내용을 교차 검증해 하나의 결과로 합쳐서 판단하세요.
마크다운 코드블록 없이 순수 JSON만 출력하세요.

{
  "overall_score": 0~100 정수,
  "summary": "한 문장 요약",
  "detected_fields": {
    "product_name": {"found": true/false, "value": "값 또는 null", "issue": "문제점 또는 null"},
    "manufacturer": {"found": true/false, "value": "값 또는 null", "issue": "문제점 또는 null"},
    "content_weight": {"found": true/false, "value": "값 또는 null", "issue": "문제점 또는 null"},
    "ingredients": {"found": true/false, "value": "값 또는 null", "issue": "문제점 또는 null"},
    "nutrition_facts": {"found": true/false, "value": "값 또는 null", "issue": "문제점 또는 null"},
    "expiry_date": {"found": true/false, "value": "값 또는 null", "issue": "문제점 또는 null"},
    "storage_method": {"found": true/false, "value": "값 또는 null", "issue": "문제점 또는 null"},
    "allergen": {"found": true/false, "value": "값 또는 null", "issue": "문제점 또는 null"},
    "country_of_origin": {"found": true/false, "value": "값 또는 null", "issue": "문제점 또는 null"},
    "food_type": {"found": true/false, "value": "값 또는 null", "issue": "문제점 또는 null"},
    "barcode": {"found": true/false, "value": "값 또는 null", "issue": "문제점 또는 null"}
  },
  "violations": [
    {"field": "항목명", "severity": "high/medium/low", "message": "위반 내용"}
  ],
  "warnings": [
    {"field": "항목명", "message": "주의 내용"}
  ],
  "design_consistency": [
    {"item": "항목명", "issue": "정보표시면과 디자인 시안이 다른 점"}
  ],
  "typos": [
    {"location": "오탈자가 있는 위치 (예: 원재료명, 보관방법 등)", "found_text": "실제 표기된 문구", "issue": "문제 설명", "suggestion": "수정 제안"}
  ],
  "weight_check": {
    "applicable": true/false,
    "unit_weight": "1개입 중량 (예: 5.5g) 또는 null",
    "unit_count": "입수량/개수 (예: 10T, 20 STICKS, 10개입) 또는 null",
    "expected_total": "unit_weight × unit_count로 계산한 총 중량 (예: 55g) 또는 null",
    "labeled_total": "정보표시면에 실제로 표기된 총 내용량 또는 null",
    "match": true/false,
    "note": "계산 근거와 결과를 한 문장으로 설명"
  }
}
디자인 시안 이미지가 함께 제공된 경우에만 design_consistency를 채우고, 없으면 빈 배열로 두세요.

weight_check: 스틱커피처럼 "1개입 중량 × 입수량 = 총 내용량" 형태로 표기되는 제품인지 확인하세요.
- 1개입 중량은 정보표시면에서, 입수량(개수)은 디자인 시안에 표기된 수량(예: 10T, 20 STICKS)이나
  정보표시면 자체의 입수량 표기 중 확인 가능한 값을 사용하세요.
- unit_weight와 unit_count를 모두 찾을 수 있으면 applicable을 true로 하고 expected_total을 계산하세요.
- expected_total과 정보표시면에 실제 표기된 labeled_total을 비교해 일치 여부를 match에 기록하고,
  불일치하면 반드시 violations에도 "내용량" 항목으로 추가하세요.
- 해당 사항이 없는 제품(스틱/낱개 단위 표기가 없는 경우)은 applicable을 false로 하고 나머지는 null로 두세요.
- unit_weight, expected_total, labeled_total을 적을 때도 숫자와 단위 사이 띄어쓰기 규칙(아래 typos 항목 참고)을
  지켜서 "16 g"처럼 표기하세요.

typos에는 기본적인 맞춤법/오탈자 문제를 찾아 기록하세요. 다음을 반드시 확인하세요:
- 쉼표(,) 다음에 띄어쓰기가 빠진 경우
- 문장이 마침표 없이 끝나는 경우
- 브랜드명이나 제품명의 영문 이니셜/철자 오타 (예: 같은 브랜드명이 문서마다 다르게 표기됨)
- 띄어쓰기 오류, 중복 공백, 오타로 보이는 단어
- 숫자와 단위(g, kg, mg, mL, L, kcal 등) 사이 띄어쓰기 누락. 숫자 바로 뒤에 단위가 붙어 있으면
  (예: "16g", "500mL") 반드시 지적하고, "16 g", "500 mL"처럼 숫자와 단위 사이에 띄어쓰기 한 칸이
  있어야 한다고 명시하세요. 내용량(content_weight)과 영양성분표(nutrition_facts)에 나오는 모든
  숫자+단위 표기를 특히 꼼꼼히 확인하세요.
문제가 없으면 typos는 빈 배열로 두세요."""

def _parse_result(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        return {
            "overall_score": 0,
            "summary": "결과 파싱 오류 — 원본: " + text[:200],
            "detected_fields": {},
            "violations": [],
            "warnings": [],
            "design_consistency": [],
            "typos": [],
            "weight_check": {"applicable": False},
        }

def analyze_images_with_gemini(images: list, context: str = "",
                                design_b64: str = None, design_media_type: str = None,
                                extra_texts: list = None) -> dict:
    """images: [{"data": base64_str, "mime_type": "image/png"}, ...] — 정보표시면/품목제조보고서 등
    여러 문서를 한 번에 넘기면 함께 분석합니다.
    extra_texts: [{"filename": str, "text": str}, ...] — 엑셀 등 텍스트로 추출된 문서."""
    client = _client()
    total_docs = len(images) + len(extra_texts or [])
    doc_note = f" (문서 {total_docs}건을 함께 검토)" if total_docs > 1 else ""
    user_msg = f"아래 패키지 문서{doc_note}를 식품표기 기준으로 검수해주세요.\n추가 컨텍스트: {context}" if context else f"아래 패키지 문서{doc_note}를 식품표기 기준으로 검수해주세요."
    parts = [
        types.Part(text=SYSTEM_PROMPT),
        types.Part(text=user_msg),
    ]
    for img in images:
        parts.append(types.Part(inline_data=types.Blob(mime_type=img["mime_type"], data=img["data"])))
    for et in (extra_texts or []):
        parts.append(types.Part(text=f"[엑셀 문서: {et['filename']}]\n{et['text']}"))
    if design_b64:
        parts.append(types.Part(text="아래는 참고용 디자인 시안 이미지입니다. 위 문서들과 제품명/문구/수치 등이 일치하는지 비교하여 불일치 사항을 design_consistency에 기록하세요."))
        parts.append(types.Part(inline_data=types.Blob(mime_type=design_media_type, data=design_b64)))
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[types.Content(role="user", parts=parts)]
    )
    return _parse_result(response.text)

def generate_report_text(result: dict, file_info: dict) -> str:
    lines = [
        f"# 패키지 표기사항 검수 리포트",
        f"파일: {file_info.get('filename', '')}",
        f"종합 점수: {result.get('overall_score', 0)}점",
        f"",
        f"## 검수 요약",
        result.get("summary", ""),
        f"",
        f"## 항목별 결과",
    ]
    for fid, fd in result.get("detected_fields", {}).items():
        status = "✅" if fd.get("found") else "❌"
        val = f" — {fd.get('value')}" if fd.get("value") else ""
        issue = f"\n   ⚠ {fd.get('issue')}" if fd.get("issue") and fd.get("issue") != "null" else ""
        lines.append(f"{status} {fid}{val}{issue}")
    lines += ["", "## 위반 사항"]
    for v in result.get("violations", []):
        lines.append(f"[{v.get('severity','').upper()}] {v.get('field')}: {v.get('message')}")
    if not result.get("violations"):
        lines.append("위반 사항 없음")
    lines += ["", "## 주의사항"]
    for w in result.get("warnings", []):
        lines.append(f"💡 {w.get('field')}: {w.get('message')}")
    if not result.get("warnings"):
        lines.append("주의사항 없음")
    lines += ["", "## 오탈자/맞춤법"]
    for t in result.get("typos", []):
        lines.append(f"✏ [{t.get('location')}] \"{t.get('found_text')}\" — {t.get('issue')} (제안: {t.get('suggestion')})")
    if not result.get("typos"):
        lines.append("발견된 오탈자 없음")
    return "\n".join(lines)
