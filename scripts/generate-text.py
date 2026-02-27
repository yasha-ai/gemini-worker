#!/usr/bin/env python3
"""
Generate text via Gemini text models.
"""
import argparse
import os
import sys
from pathlib import Path
from google import genai
from google.genai import types


def main():
    parser = argparse.ArgumentParser(description='Generate text via Gemini')
    parser.add_argument('--prompt', required=True, help='Text prompt')
    parser.add_argument('--model', default='gemini-3.1-pro-preview', help='Model name')
    parser.add_argument('--output', default='output.txt', help='Output file path')
    parser.add_argument('--max-tokens', type=int, default=8192, help='Max output tokens')
    parser.add_argument('--temperature', type=float, default=0.7, help='Temperature (0.0-2.0)')
    
    args = parser.parse_args()
    
    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_GEMINI_API_KEY not set")
        sys.exit(1)
    
    client = genai.Client(api_key=api_key)
    
    print(f"📝 Generating text...")
    print(f"   Model: {args.model}")
    print(f"   Prompt: {args.prompt[:100]}{'...' if len(args.prompt) > 100 else ''}")
    print(f"   Max tokens: {args.max_tokens}")
    print(f"   Temperature: {args.temperature}")
    
    try:
        response = client.models.generate_content(
            model=args.model,
            contents=args.prompt,
            config=types.GenerateContentConfig(
                temperature=args.temperature,
                max_output_tokens=args.max_tokens,
            )
        )
        
        result_text = response.text
        
        Path(args.output).write_text(result_text, encoding='utf-8')
        
        print(f"✅ Text saved to: {args.output}")
        print(f"   Characters: {len(result_text)}")
        print(f"   Words: {len(result_text.split())}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
