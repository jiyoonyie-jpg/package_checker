import os
import base64
import urllib.parse
import urllib.request
from google import genai

# ── Pollinations.ai 무료 이미지 생성 ─────────────────────
# API 키 불필요, 완전 무료
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width=1024&height=640&nologo=true&model=flux"

def _gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    return genai.Client(api_key=api_key)

def build_design_prompt(user_input: str) -> str:
    """한국어 설명을 영문 이미지 프롬프트로 변환"""
    return (
        f"Professional product packaging design, commercial package illustration. "
        f"{user_input}. "
        f"Clean modern packaging, studio white background, high quality product photography, "
        f"photorealistic render, no people, no text."
    )

def translate_to_english(user_input: str) -> str:
    """Gemini로 한국어 설명을 영문 이미지 프롬프트로 변환"""
    try:
        client = _gemini_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=(
                f"아래 한국어 패키지 디자인 설명을 영어 이미지 생성 프롬프트로 변환해주세요. "
                f"50단어 이내의 영어 설명문만 출력하세요. 다른 말은 하지 마세요.\n\n"
                f"설명: {user_input}"
            ),
        )
        return response.text.strip()
    except Exception:
        return build_design_prompt(user_input)

def generate_package_design(user_input: str) -> dict:
    """
    Pollinations.ai로 패키지 디자인 이미지 무료 생성.
    반환: {"image_b64": str, "mime_type": str, "prompt": str} 또는 {"error": str}
    """
    try:
        # Gemini로 한국어 → 영문 프롬프트 변환
        eng_prompt = translate_to_english(user_input)
        encoded = urllib.parse.quote(eng_prompt)
        url = POLLINATIONS_URL.format(prompt=encoded)

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            img_bytes = resp.read()

        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        return {"image_b64": img_b64, "mime_type": "image/jpeg", "prompt": eng_prompt}
    except Exception as e:
        return {"error": str(e)}

def refine_design_description(user_input: str) -> str:
    """Gemini로 디자인 브리프 구체화"""
    try:
        client = _gemini_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=(
                f"아래 패키지 디자인 요청을 구체적인 디자인 브리프로 정리해주세요. "
                f"색상, 형태, 소재감, 타이포그래피, 분위기를 포함해 400자 이내로 작성하세요.\n\n"
                f"요청: {user_input}"
            ),
        )
        return response.text
    except Exception as e:
        return f"브리프 생성 실패: {e}"
