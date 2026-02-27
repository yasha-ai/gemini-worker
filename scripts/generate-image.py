#!/usr/bin/env python3
"""
Generate images via Gemini image models.
"""
import argparse
import base64
import os
import sys
import requests
from pathlib import Path
from google import genai


def main():
    parser = argparse.ArgumentParser(description='Generate image via Gemini')
    parser.add_argument('--prompt', required=True, help='Image prompt')
    parser.add_argument('--model', default='gemini-3-pro-image-preview', help='Model name')
    parser.add_argument('--output', default='output.png', help='Output file path')
    parser.add_argument('--reference', help='Reference image URL')
    
    args = parser.parse_args()
    
    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_GEMINI_API_KEY not set")
        sys.exit(1)
    
    client = genai.Client(api_key=api_key)
    
    print(f"🎨 Generating image...")
    print(f"   Model: {args.model}")
    print(f"   Prompt: {args.prompt}")
    
    # Build parts for request
    parts = []
    
    # Add reference image if provided
    if args.reference:
        print(f"   Reference: {args.reference}")
        try:
            response = requests.get(args.reference)
            response.raise_for_status()
            img_data = base64.b64encode(response.content).decode('utf-8')
            
            # Determine MIME type
            content_type = response.headers.get('content-type', 'image/jpeg')
            
            parts.append({
                "inlineData": {
                    "mimeType": content_type,
                    "data": img_data
                }
            })
        except Exception as e:
            print(f"⚠️  Failed to fetch reference image: {e}")
    
    # Add text prompt
    parts.append({"text": args.prompt})
    
    # Generate
    try:
        response = client.models.generate_content(
            model=args.model,
            contents=[{"parts": parts}]
        )
        
        # Extract image from response
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data'):
                    img_data = base64.b64decode(part.inline_data.data)
                    Path(args.output).write_bytes(img_data)
                    print(f"✅ Image saved to: {args.output}")
                    print(f"   Size: {len(img_data)} bytes")
                    return
        
        print("❌ No image in response")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
