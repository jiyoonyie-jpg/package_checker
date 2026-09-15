import os
import json
import re
from google import genai
from google.genai import types

def _client():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    return genai.Client(api_key=api_key)

SYSTEM_PROMPT = """당신은 한국 식품위생법 및 식품 등의 표시기준 전문가입니다.
정보표시면, 품목제조보고서 등 함께 제공되는 여러 문서 이미지를 종합적으로 분석하여
필수 표기사항을 검수하고, 반드시 아래 JSON 형식으로만 응답하세요.
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
  ]
}
디자인 시안 이미지가 함께 제공된 경우에만 design_consistency를 채우고, 없으면 빈 배열로 두세요."""

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
        }

def analyze_images_with_gemini(images: list, context: str = "",
                                design_b64: str = None, design_media_type: str = None) -> dict:
    """images: [{"data": base64_str, "mime_type": "image/png"}, ...] — 정보표시면/품목제조보고서 등
    여러 문서를 한 번에 넘기면 함께 분석합니다."""
    client = _client()
    doc_note = f" (문서 {len(images)}장을 함께 검토)" if len(images) > 1 else ""
    user_msg = f"아래 패키지 문서{doc_note}를 식품표기 기준으로 검수해주세요.\n추가 컨텍스트: {context}" if context else f"아래 패키지 문서{doc_note}를 식품표기 기준으로 검수해주세요."
    parts = [
        types.Part(text=SYSTEM_PROMPT),
        types.Part(text=user_msg),
    ]
    for img in images:
        parts.append(types.Part(inline_data=types.Blob(mime_type=img["mime_type"], data=img["data"])))
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
    return "\n".join(lines)
