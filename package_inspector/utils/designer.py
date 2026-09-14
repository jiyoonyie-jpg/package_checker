import os
import base64
import urllib.parse
import urllib.request
from google import genai

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width=1024&height=640&nologo=true&model=flux&seed={seed}"

def _gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    return genai.Client(api_key=api_key)

def translate_to_english(user_input: str) -> str:
    """Gemini로 한국어 설명을 상세한 영문 이미지 프롬프트로 변환"""
    try:
        client = _gemini_client()
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=(
                f"아래 한국어 패키지 디자인 설명을 영어 이미지 생성 프롬프트로 변환해주세요.\n"
                f"규칙:\n"
                f"- 색상을 정확히 반영하세요 (예: yellow background, purple accent)\n"
                f"- 형태를 명확히 하세요 (예: horizontal rectangular box, slim stick package)\n"
                f"- 분위기를 포함하세요 (예: modern, premium, cute)\n"
                f"- 80단어 이내 영어만 출력, 다른 말 없이\n\n"
                f"설명: {user_input}"
            ),
        )
        return response.text.strip()
    except Exception:
        return f"product packaging design, {user_input}, studio white background, photorealistic"

def generate_package_design(user_input: str, seed: int = 42) -> dict:
    """
    Pollinations.ai로 패키지 디자인 이미지 무료 생성.
    반환: {"image_b64": str, "mime_type": str, "prompt": str} 또는 {"error": str}
    """
    try:
        eng_prompt = translate_to_english(user_input)
        # 품질 향상 키워드 추가
        full_prompt = (
            f"{eng_prompt}, "
            f"professional product packaging design, commercial grade, "
            f"clean studio white background, sharp details, high resolution, "
            f"no people, product photography"
        )
        encoded = urllib.parse.quote(full_prompt)
        url = POLLINATIONS_URL.format(prompt=encoded, seed=seed)

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
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
            model="gemini-1.5-flash",
            contents=(
                f"아래 패키지 디자인 요청을 구체적인 디자인 브리프로 정리해주세요. "
                f"색상, 형태, 소재감, 타이포그래피, 분위기를 포함해 400자 이내로 작성하세요.\n\n"
                f"요청: {user_input}"
            ),
        )
        return response.text
    except Exception as e:
        return f"브리프 생성 실패: {e}"
