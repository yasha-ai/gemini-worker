#!/usr/bin/env python3
"""
Fixed Gemini Image Generator using REST API
Handles C2PA metadata and proper response parsing
"""
import argparse
import base64
import json
import os
import sys
import time
import requests

FALLBACK_MODEL = "gemini-2.0-flash-preview-image-generation"


def generate(model, parts, api_key, output, attempt_label=""):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": parts}]}

    label = f"[{attempt_label}] " if attempt_label else ""
    print(f"{label}🎨 Requesting model: {model}...")

    response = requests.post(url, json=payload, timeout=90)

    if response.status_code == 503:
        raise OverloadedError(f"503 overloaded: {response.text[:200]}")
    if response.status_code == 404:
        raise ModelNotFoundError(f"404 model not found: {model}")

    response.raise_for_status()
    data = response.json()

    if "candidates" not in data:
        print(f"❌ No candidates in response: {json.dumps(data, indent=2)}")
        sys.exit(1)

    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if "inlineData" in part:
                img_bytes = base64.b64decode(part["inlineData"]["data"])
                with open(output, "wb") as f:
                    f.write(img_bytes)
                print(f"✅ Image saved to: {output} ({len(img_bytes):,} bytes)")
                return True
            if "text" in part:
                print(f"💬 {part['text']}")

    print("❌ No image in response")
    print(f"   Response: {json.dumps(data, indent=2)}")
    sys.exit(1)


class OverloadedError(Exception):
    pass

class ModelNotFoundError(Exception):
    pass


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

    print(f"   Prompt: {args.prompt[:80]}")

    # Build parts
    parts = []
    if args.reference:
        print(f"   Reference: {args.reference}")
        try:
            if args.reference.startswith('http'):
                r = requests.get(args.reference, timeout=30)
                r.raise_for_status()
                img_bytes = r.content
                content_type = r.headers.get('content-type', 'image/jpeg').split(';')[0]
            else:
                with open(args.reference, 'rb') as f:
                    img_bytes = f.read()
                content_type = 'image/png' if args.reference.endswith('.png') else 'image/jpeg'

            parts.append({"inlineData": {"mimeType": content_type, "data": base64.b64encode(img_bytes).decode()}})
        except Exception as e:
            print(f"⚠️  Failed to load reference image: {e}")

    parts.append({"text": args.prompt})

    # Try primary model with retries, then fallback
    model = args.model
    retries = 3
    retry_delay = 15

    for attempt in range(1, retries + 1):
        try:
            generate(model, parts, api_key, args.output, attempt_label=f"{attempt}/{retries}")
            return
        except OverloadedError as e:
            if attempt < retries:
                print(f"⏳ Model overloaded, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                if model != FALLBACK_MODEL:
                    print(f"⚠️  Primary model still overloaded after {retries} attempts, switching to fallback: {FALLBACK_MODEL}")
                    model = FALLBACK_MODEL
                    retries = 2
                    attempt = 0
                else:
                    print(f"❌ Fallback model also overloaded: {e}")
                    sys.exit(1)
        except ModelNotFoundError as e:
            print(f"❌ {e}")
            if model != FALLBACK_MODEL:
                print(f"   Trying fallback model: {FALLBACK_MODEL}")
                model = FALLBACK_MODEL
                retries = 2
                attempt = 0
            else:
                sys.exit(1)
        except requests.exceptions.Timeout:
            if attempt < retries:
                print(f"⏳ Timeout, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                if model != FALLBACK_MODEL:
                    print(f"⚠️  Timeout persists, switching to fallback: {FALLBACK_MODEL}")
                    model = FALLBACK_MODEL
                    retries = 2
                    attempt = 0
                else:
                    print("❌ Fallback model also timed out")
                    sys.exit(1)
        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text[:300]}")
            sys.exit(1)


if __name__ == "__main__":
    main()
