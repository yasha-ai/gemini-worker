#!/usr/bin/env python3
"""
Gemini Image Generator using REST API
Retry logic with automatic model fallback chain on 503/timeout/404
Sends final Telegram notification on success or failure
"""
import argparse
import base64
import json
import os
import sys
import time
import requests


# Model fallback chain per docs (Nano Banana family)
FALLBACK_MODELS = [
    "gemini-3-pro-image-preview",        # Nano Banana Pro
    "gemini-3.1-flash-image-preview",    # Nano Banana 2 - fast
    "gemini-2.5-flash-image",            # Nano Banana - last resort
]

MAX_RETRIES = 3
RETRY_DELAY = 15


def tg(text):
    """Send a Telegram message. Silently skips if credentials not set."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except Exception:
        pass


def build_parts(prompt, reference=None):
    parts = []
    if reference:
        print(f"   Reference: {reference}")
        try:
            if reference.startswith('http'):
                resp = requests.get(reference, timeout=30)
                resp.raise_for_status()
                img_bytes = resp.content
                content_type = resp.headers.get('content-type', 'image/jpeg').split(';')[0]
            else:
                with open(reference, 'rb') as f:
                    img_bytes = f.read()
                content_type = 'image/png' if reference.endswith('.png') else 'image/jpeg'

            parts.append({"inlineData": {
                "mimeType": content_type,
                "data": base64.b64encode(img_bytes).decode('utf-8'),
            }})
        except Exception as e:
            print(f"⚠️  Failed to load reference image: {e}")

    parts.append({"text": prompt})
    return parts


def try_generate(api_key, model, parts, output_path):
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
                msg = f"❌ Попытка {attempt}/{MAX_RETRIES} провалилась: модель {model} перегружена (503)"
                print(f"   {msg}")
                if attempt < MAX_RETRIES:
                    wait_msg = f"⏳ Жду {RETRY_DELAY}с и пробую снова..."
                    print(f"   {wait_msg}")
                    time.sleep(RETRY_DELAY)
                continue

            response.raise_for_status()
            data = response.json()

            if 'candidates' not in data:
                msg = f"❌ Попытка {attempt}/{MAX_RETRIES} провалилась: нет candidates в ответе"
                print(f"   {msg}")
                return False

            for candidate in data.get('candidates', []):
                for part in candidate.get('content', {}).get('parts', []):
                    if 'inlineData' in part:
                        img_bytes = base64.b64decode(part['inlineData']['data'])

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

            msg = f"❌ Попытка {attempt}/{MAX_RETRIES} провалилась: изображение не найдено в ответе"
            print(f"   {msg}")
            return False

        except requests.exceptions.Timeout:
            msg = f"❌ Попытка {attempt}/{MAX_RETRIES} провалилась: timeout >90с"
            print(f"   {msg}")
            if attempt < MAX_RETRIES:
                wait_msg = f"⏳ Жду {RETRY_DELAY}с и пробую снова..."
                print(f"   {wait_msg}")
                time.sleep(RETRY_DELAY)
        except requests.exceptions.RequestException as e:
            msg = f"❌ Попытка {attempt}/{MAX_RETRIES} провалилась: HTTP ошибка — {e}"
            print(f"   {msg}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Ответ сервера: {e.response.text[:500]}")
            return False
        except Exception as e:
            msg = f"❌ Попытка {attempt}/{MAX_RETRIES} провалилась: неожиданная ошибка — {e}"
            print(f"   {msg}")
            import traceback
            traceback.print_exc()
            return False

    return False


def main():
    parser = argparse.ArgumentParser(description='Generate image via Gemini REST API')
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--model', default='gemini-3-pro-image-preview')
    parser.add_argument('--output', default='output.png')
    parser.add_argument('--reference', help='Reference image URL or path')

    args = parser.parse_args()

    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_GEMINI_API_KEY not set")
        sys.exit(1)

    print(f"🎨 Generating image via REST API...")
    print(f"   Primary model: {args.model}")
    print(f"   Prompt: {args.prompt[:80]}")

    parts = build_parts(args.prompt, args.reference)

    models_to_try = [args.model]
    for m in FALLBACK_MODELS:
        if m != args.model:
            models_to_try.append(m)

    for i, model in enumerate(models_to_try):
        if i > 0:
            print(f"\n🔄 Переключаюсь на следующую модель: {model}")
        success = try_generate(api_key, model, parts, args.output)
        if success:
            tg(f"✅ Изображение сгенерировано через {model}")
            sys.exit(0)

    tg("❌ Все модели исчерпаны. Генерация провалилась.")
    print("\n❌ All models exhausted. Image generation failed.")
    sys.exit(1)


if __name__ == "__main__":
    main()
