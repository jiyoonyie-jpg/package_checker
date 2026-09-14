import os
import base64
import urllib.request
import urllib.parse
import json
from google import genai

MODELS = ["gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash-latest"]

# Hugging Face SDXL 모델
HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

def _gemini_text(prompt: str) -> str:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
    last_err = None
    for model in MODELS:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text.strip()
        except Exception as e:
            last_err = e
            continue
    raise Exception(f"Gemini 실패: {last_err}")

def translate_to_english(user_input: str) -> str:
    try:
        return _gemini_text(
            f"아래 한국어 패키지 디자인 설명을 영어 이미지 생성 프롬프트로 변환하세요.\n"
            f"규칙: 색상 정확히 반영, 형태 명확히, 분위기 포함, 80단어 이내 영어만 출력.\n\n"
            f"설명: {user_input}"
        )
    except Exception:
        return f"product packaging design, {user_input}, studio white background"

def generate_package_design(user_input: str, seed: int = 42) -> dict:
    hf_token = os.environ.get("HF_TOKEN", "")
    if not hf_token:
        return {"error": "HF_TOKEN이 설정되지 않았습니다. Streamlit Secrets에 추가해주세요."}

    try:
        eng_prompt = translate_to_english(user_input)
        full_prompt = (
            f"{eng_prompt}, "
            f"professional product packaging design, commercial grade, "
            f"clean white studio background, high resolution, sharp details, "
            f"no people, product photography style"
        )

        payload = json.dumps({
            "inputs": full_prompt,
            "parameters": {
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "width": 1024,
                "height": 640,
                "seed": seed,
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            HF_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {hf_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            img_bytes = resp.read()

        # 오류 응답 체크 (JSON이면 에러)
        if img_bytes[:1] == b"{":
            err = json.loads(img_bytes)
            return {"error": err.get("error", str(err))}

        return {
            "image_b64": base64.b64encode(img_bytes).decode("utf-8"),
            "mime_type": "image/jpeg",
            "prompt": eng_prompt,
        }
    except Exception as e:
        return {"error": str(e)}

def refine_design_description(user_input: str) -> str:
    try:
        return _gemini_text(
            f"아래 패키지 디자인 요청을 구체적인 디자인 브리프로 정리해주세요. "
            f"색상, 형태, 소재감, 타이포그래피, 분위기를 포함해 400자 이내.\n\n"
            f"요청: {user_input}"
        )
    except Exception as e:
        return f"브리프 생성 실패: {e}"
