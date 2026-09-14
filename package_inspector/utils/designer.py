import os
import base64
import urllib.parse
import urllib.request
from google import genai
from google.genai import types

MODELS = ["gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash-latest"]
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width=1024&height=640&nologo=true&model=flux&seed={seed}"

def _client():
    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))

def _text(prompt: str) -> str:
    client = _client()
    last_err = None
    for model in MODELS:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text.strip()
        except Exception as e:
            last_err = e
            continue
    raise Exception(f"모든 모델 실패: {last_err}")

def translate_to_english(user_input: str) -> str:
    try:
        return _text(
            f"아래 한국어 패키지 디자인 설명을 영어 이미지 생성 프롬프트로 변환하세요.\n"
            f"규칙: 색상 정확히 반영, 형태 명확히, 분위기 포함, 80단어 이내 영어만 출력.\n\n"
            f"설명: {user_input}"
        )
    except Exception:
        return f"product packaging design, {user_input}, studio white background, photorealistic"

def generate_package_design(user_input: str, seed: int = 42) -> dict:
    try:
        eng_prompt = translate_to_english(user_input)
        full_prompt = (
            f"{eng_prompt}, professional product packaging design, "
            f"clean studio white background, sharp details, high resolution, "
            f"no people, commercial grade product photography"
        )
        encoded = urllib.parse.quote(full_prompt)
        url = POLLINATIONS_URL.format(prompt=encoded, seed=seed)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            img_bytes = resp.read()
        return {"image_b64": base64.b64encode(img_bytes).decode("utf-8"),
                "mime_type": "image/jpeg", "prompt": eng_prompt}
    except Exception as e:
        return {"error": str(e)}

def refine_design_description(user_input: str) -> str:
    try:
        return _text(
            f"아래 패키지 디자인 요청을 구체적인 디자인 브리프로 정리해주세요. "
            f"색상, 형태, 소재감, 타이포그래피, 분위기를 포함해 400자 이내.\n\n"
            f"요청: {user_input}"
        )
    except Exception as e:
        return f"브리프 생성 실패: {e}"
