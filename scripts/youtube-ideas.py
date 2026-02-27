#!/usr/bin/env python3
"""
Generate YouTube video ideas via Gemini.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from google import genai
from google.genai import types


def decode_unicode_in_object(obj):
    """Recursively decode Unicode escape sequences in object."""
    if isinstance(obj, dict):
        return {k: decode_unicode_in_object(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decode_unicode_in_object(item) for item in obj]
    elif isinstance(obj, str):
        # Decode \uXXXX sequences
        try:
            return obj.encode('utf-8').decode('unicode-escape')
        except:
            return obj
    return obj


def main():
    parser = argparse.ArgumentParser(description='Generate YouTube ideas')
    parser.add_argument('--count', type=int, default=10, help='Number of ideas')
    parser.add_argument('--topic', help='Topic/theme (optional)')
    parser.add_argument('--model', default='gemini-3.1-pro-preview', help='Model name')
    parser.add_argument('--output', default='youtube_ideas.json', help='Output file')
    
    args = parser.parse_args()
    
    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_GEMINI_API_KEY not set")
        sys.exit(1)
    
    client = genai.Client(api_key=api_key)
    
    topic_part = f" на тему '{args.topic}'" if args.topic else ""
    
    prompt = f"""Создай {args.count} идей для YouTube видео{topic_part}.

Канал: @sov-it (технологии, программирование, AI, инструменты для разработчиков).
Аудитория: разработчики, tech-энтузиасты, русскоязычные.

Формат ответа (СТРОГО JSON):

{{
  "ideas": [
    {{
      "title": "Название видео (цепляющее, на русском)",
      "description": "Краткое описание (1-2 предложения)",
      "hook": "Первые 10 секунд — чем зацепить зрителя",
      "keywords": ["ключевое", "слово", "для", "поиска"],
      "estimated_length": "8-12 минут",
      "difficulty": "начинающий|средний|продвинутый"
    }}
  ]
}}

ПРАВИЛА:
1. Все тексты на русском языке
2. Названия цепляющие, интригующие
3. Актуальные темы (2026)
4. Практическая польза для разработчиков
5. НЕ используй Unicode escape sequences (\\uXXXX) — пиши обычную кириллицу

Верни ТОЛЬКО валидный JSON, без дополнительного текста."""

    print(f"💡 Generating {args.count} YouTube ideas...")
    print(f"   Model: {args.model}")
    if args.topic:
        print(f"   Topic: {args.topic}")
    
    try:
        response = client.models.generate_content(
            model=args.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.9,  # Креативность
                max_output_tokens=8192,
            )
        )
        
        result_text = response.text
        
        # Remove markdown code fences if present
        result_text = result_text.strip()
        if result_text.startswith('```'):
            result_text = '\n'.join(result_text.split('\n')[1:-1])
        
        # Parse JSON
        try:
            ideas_json = json.loads(result_text)
            
            # Decode Unicode escapes
            ideas_json = decode_unicode_in_object(ideas_json)
            
            # Save
            Path(args.output).write_text(
                json.dumps(ideas_json, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            
            print(f"✅ Saved {len(ideas_json.get('ideas', []))} ideas to: {args.output}")
            
            # Preview
            for i, idea in enumerate(ideas_json.get('ideas', [])[:3], 1):
                print(f"\n{i}. {idea.get('title', 'N/A')}")
                print(f"   {idea.get('description', 'N/A')}")
            
            if len(ideas_json.get('ideas', [])) > 3:
                print(f"\n... и ещё {len(ideas_json['ideas']) - 3}")
                
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            print(f"Response:\n{result_text[:500]}")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
