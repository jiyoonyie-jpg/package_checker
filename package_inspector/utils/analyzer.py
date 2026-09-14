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
  ]
}"""

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
        }

def analyze_image_with_gemini(img_b64: str, media_type: str, context: str = "") -> dict:
    client = _client()
    user_msg = f"아래 패키지 이미지를 식품표기 기준으로 검수해주세요.\n추가 컨텍스트: {context}" if context else "아래 패키지 이미지를 식품표기 기준으로 검수해주세요."
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=[
            types.Content(role="user", parts=[
                types.Part(text=SYSTEM_PROMPT),
                types.Part(text=user_msg),
                types.Part(inline_data=types.Blob(mime_type=media_type, data=img_b64)),
            ])
        ]
    )
    return _parse_result(response.text)

def analyze_pdf_pages(pages: list, context: str = "") -> dict:
    if not pages or "error" in pages[0]:
        return {"overall_score": 0, "summary": "PDF 변환 실패", "detected_fields": {}, "violations": [], "warnings": []}
    first = pages[0]
    result = analyze_image_with_gemini(first["base64"], "image/png", context)
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
