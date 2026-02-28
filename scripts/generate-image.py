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
import requests


def main():
    parser = argparse.ArgumentParser(description='Generate image via Gemini REST API')
    parser.add_argument('--prompt', required=True, help='Image prompt')
    parser.add_argument('--model', default='gemini-3-pro-image-preview', help='Model name')
    parser.add_argument('--output', default='output.png', help='Output file path')
    parser.add_argument('--reference', help='Reference image URL or path')
    
    args = parser.parse_args()
    
    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_GEMINI_API_KEY not set")
        sys.exit(1)
    
    print(f"🎨 Generating image via REST API...")
    print(f"   Model: {args.model}")
    print(f"   Prompt: {args.prompt}")
    
    # Build request parts
    parts = []
    
    # Add reference image if provided
    if args.reference:
        print(f"   Reference: {args.reference}")
        try:
            if args.reference.startswith('http'):
                response = requests.get(args.reference)
                response.raise_for_status()
                img_bytes = response.content
                content_type = response.headers.get('content-type', 'image/jpeg')
            else:
                with open(args.reference, 'rb') as f:
                    img_bytes = f.read()
                # Detect mime type
                if args.reference.endswith('.png'):
                    content_type = 'image/png'
                elif args.reference.endswith('.jpg') or args.reference.endswith('.jpeg'):
                    content_type = 'image/jpeg'
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
    
    # Add text prompt
    parts.append({"text": args.prompt})
    
    # Prepare request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{args.model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": parts
        }]
    }
    
    # Make request
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        # Debug: print response structure
        if 'candidates' not in data:
            print(f"❌ No candidates in response: {json.dumps(data, indent=2)}")
            sys.exit(1)
        
        # Extract image
        for candidate in data.get('candidates', []):
            for part in candidate.get('content', {}).get('parts', []):
                if 'inlineData' in part:
                    img_b64 = part['inlineData']['data']
                    img_bytes = base64.b64decode(img_b64)
                    
                    # Validate it's actually an image
                    if len(img_bytes) < 1000:
                        print(f"⚠️  Suspicious image size: {len(img_bytes)} bytes")
                        print(f"   First 200 bytes: {img_bytes[:200]}")
                    
                    with open(args.output, 'wb') as f:
                        f.write(img_bytes)
                    
                    print(f"✅ Image saved to: {args.output}")
                    print(f"   Size: {len(img_bytes):,} bytes")
                    return
                
                if 'text' in part:
                    print(f"💬 Model response: {part['text']}")
        
        print("❌ No image in response")
        print(f"   Response: {json.dumps(data, indent=2)}")
        sys.exit(1)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
