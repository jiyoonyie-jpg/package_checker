import os
import json
import re
from google import genai
from google.genai import types

def _client():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    return genai.Client(api_key=api_key)

SYSTEM_PROMPT = """당신은 한국 식품위생법 및 식품 등의 표시기준 전문가입니다.
패키지 이미지를 분석하여 필수 표기사항을 검수하고, 반드시 아래 JSON 형식으로만 응답하세요.
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

def analyze_image_with_gemini(img_b64: str, media_type: str, context: str = "",
                               design_b64: str = None, design_media_type: str = None) -> dict:
    client = _client()
    user_msg = f"아래 패키지 이미지를 식품표기 기준으로 검수해주세요.\n추가 컨텍스트: {context}" if context else "아래 패키지 이미지를 식품표기 기준으로 검수해주세요."
    parts = [
        types.Part(text=SYSTEM_PROMPT),
        types.Part(text=user_msg),
        types.Part(inline_data=types.Blob(mime_type=media_type, data=img_b64)),
    ]
    if design_b64:
        parts.append(types.Part(text="아래는 참고용 디자인 시안 이미지입니다. 위 정보표시면과 제품명/문구/수치 등이 일치하는지 비교하여 불일치 사항을 design_consistency에 기록하세요."))
        parts.append(types.Part(inline_data=types.Blob(mime_type=design_media_type, data=design_b64)))
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[types.Content(role="user", parts=parts)]
    )
    return _parse_result(response.text)

def analyze_pdf_pages(pages: list, context: str = "",
                       design_b64: str = None, design_media_type: str = None) -> dict:
    if not pages or "error" in pages[0]:
        return {"overall_score": 0, "summary": "PDF 변환 실패", "detected_fields": {}, "violations": [], "warnings": [], "design_consistency": []}
    # 첫 페이지 분석 (필요시 여러 페이지 병합 가능)
    first = pages[0]
    result = analyze_image_with_gemini(first["base64"], "image/png", context, design_b64, design_media_type)
    if len(pages) > 1:
        result["summary"] += f" (총 {len(pages)}페이지 중 1페이지 기준)"
    return result

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
