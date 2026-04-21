#!/usr/bin/env python3
"""
Fixed Gemini Image Generator using REST API
Handles C2PA metadata and proper response parsing
Retry logic with automatic model fallback on 503/timeout
"""
import argparse
import base64
import json
import os
import sys
import time
import requests


# Model fallback chain (in order of priority)
FALLBACK_MODELS = [
    "gemini-3-pro-image-preview",       # Nano Banana Pro - highest quality
    "gemini-3.1-flash-image-preview",   # Nano Banana 2 - fast fallback
    "gemini-2.5-flash-image",           # Nano Banana - last resort
]

MAX_RETRIES = 3
RETRY_DELAY = 15  # seconds between retries


def build_parts(prompt, reference=None):
    parts = []
    if reference:
        print(f"   Reference: {reference}")
        try:
            if reference.startswith('http'):
                resp = requests.get(reference, timeout=30)
                resp.raise_for_status()
                img_bytes = resp.content
                content_type = resp.headers.get('content-type', 'image/jpeg')
            else:
                with open(reference, 'rb') as f:
                    img_bytes = f.read()
                if reference.endswith('.png'):
                    content_type = 'image/png'
                else:
                    content_type = 'image/jpeg'

            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            parts.append({
                "inlineData": {
                    "mimeType": content_type,
                    "data": img_b64
                }
            })
        except Exception as e:
            print(f"⚠️  Failed to load reference image: {e}")

    parts.append({"text": prompt})
    return parts


def try_generate(api_key, model, parts, output_path):
    """Attempt image generation with a specific model. Returns True on success."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": parts}]}

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n   🔁 Попытка {attempt}/{MAX_RETRIES} — модель: {model}")
        try:
            response = requests.post(url, json=payload, timeout=90)

            if response.status_code == 503:
                print(f"   ❌ Попытка {attempt} провалилась: 503 — модель перегружена")
                if attempt < MAX_RETRIES:
                    print(f"   ⏳ Ждём {RETRY_DELAY}с перед следующей попыткой...")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"   ⛔ Все {MAX_RETRIES} попытки с моделью {model} исчерпаны")
                continue

            response.raise_for_status()
            data = response.json()

            if 'candidates' not in data:
                print(f"   ❌ Попытка {attempt} провалилась: нет candidates в ответе")
                print(f"   Ответ: {json.dumps(data, indent=2)}")
                return False

            for candidate in data.get('candidates', []):
                for part in candidate.get('content', {}).get('parts', []):
                    if 'inlineData' in part:
                        img_b64 = part['inlineData']['data']
                        img_bytes = base64.b64decode(img_b64)

                        if len(img_bytes) < 1000:
                            print(f"   ⚠️  Подозрительно маленький файл: {len(img_bytes)} байт")

                        with open(output_path, 'wb') as f:
                            f.write(img_bytes)

                        print(f"\n✅ Изображение сохранено: {output_path}")
                        print(f"   Модель: {model} (попытка {attempt}/{MAX_RETRIES})")
                        print(f"   Размер: {len(img_bytes):,} байт")
                        return True

                    if 'text' in part:
                        print(f"   💬 Текст от модели: {part['text']}")

            print(f"   ❌ Попытка {attempt} провалилась: изображение не найдено в ответе")
            return False

        except requests.exceptions.Timeout:
            print(f"   ❌ Попытка {attempt} провалилась: timeout (>90с)")
            if attempt < MAX_RETRIES:
                print(f"   ⏳ Ждём {RETRY_DELAY}с перед следующей попыткой...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"   ⛔ Все {MAX_RETRIES} попытки с моделью {model} исчерпаны")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Попытка {attempt} провалилась: HTTP ошибка — {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Ответ сервера: {e.response.text[:500]}")
            return False
        except Exception as e:
            print(f"   ❌ Попытка {attempt} провалилась: неожиданная ошибка — {e}")
            import traceback
            traceback.print_exc()
            return False

    return False


def main():
    parser = argparse.ArgumentParser(description='Generate image via Gemini REST API')
    parser.add_argument('--prompt', required=True, help='Image prompt')
    parser.add_argument('--model', default='gemini-3-pro-image-preview', help='Primary model name')
    parser.add_argument('--output', default='output.png', help='Output file path')
    parser.add_argument('--reference', help='Reference image URL or path')

    args = parser.parse_args()

    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_GEMINI_API_KEY not set")
        sys.exit(1)

    print(f"🎨 Generating image via REST API...")
    print(f"   Primary model: {args.model}")
    print(f"   Prompt: {args.prompt}")

    parts = build_parts(args.prompt, args.reference)

    # Build fallback chain starting from the requested model
    models_to_try = [args.model]
    for m in FALLBACK_MODELS:
        if m != args.model:
            models_to_try.append(m)

    for i, model in enumerate(models_to_try):
        if i > 0:
            print(f"\n🔄 Falling back to: {model}")
        success = try_generate(api_key, model, parts, args.output)
        if success:
            sys.exit(0)

    print("\n❌ All models exhausted. Image generation failed.")
    sys.exit(1)


if __name__ == "__main__":
    main()
