#!/usr/bin/env python3
"""
Generate Sandpack playgrounds for lessons via Gemini API.
Designed to run in GitHub Actions with secrets.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from google import genai
from google.genai import types

SECTIONS = {
    "javascript": "vanilla",
    "typescript": "vanilla-ts",
    "css": "vanilla",
    "html": "vanilla",
    "php": "vanilla",
    "react": "react",
}


def has_playground(content):
    return "<Sandpack" in content or "## Интерактивный пример" in content


def get_lesson_title(content):
    m = re.search(r'^#+ (.+)$', content, re.MULTILINE)
    return m.group(1) if m else "урок"


def get_prompt(content, section, template, filename):
    """Generate simplified prompt for playground"""
    title = get_lesson_title(content)
    short_content = content[:2000] if len(content) > 2000 else content
    
    if template == "react":
        file_name = "/App.tsx"
        file_desc = "один файл App.tsx с React компонентом"
    else:
        file_name = "/index.html"
        file_desc = "один HTML файл со встроенными стилями и скриптом"
    
    return f"""Создай МИНИМАЛЬНЫЙ рабочий Sandpack playground для урока.

Тема: {title}
Секция: {section}

Фрагмент урока:
{short_content}

ФОРМАТ (верни ТОЛЬКО этот блок):

## Интерактивный пример

<Sandpack
  template="{template}"
  files={{{{
    "{file_name}": `
[КОД ФАЙЛА - 20-50 строк макс]
`
  }}}}
/>

ПРАВИЛА:
1. {file_desc}
2. Код МИНИМАЛЬНЫЙ и ИНТЕРАКТИВНЫЙ
3. Escape: \\${{}} для template literals, <\\/script> для тегов
4. Тёмная тема: background #282c34, color white
5. Блок ДОЛЖЕН заканчиваться на `/>` 
"""


def extract_sandpack_block(text):
    """Extract Sandpack block from response"""
    text = re.sub(r'```(?:html|jsx|mdx|tsx)?\n', '', text)
    text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()
    
    patterns = [
        r'(## Интерактивный пример\s*\n+<Sandpack[\s\S]*?/>)',
        r'(<Sandpack[\s\S]*?/>)',
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            block = m.group(1).strip()
            if not block.endswith("/>"):
                return None
            if not block.startswith("##"):
                block = "## Интерактивный пример\n\n" + block
            return "\n\n" + block
    return None


def generate_playground(client, model, content, section, template, filename, retries=3):
    """Generate playground with retry"""
    prompt = get_prompt(content, section, template, filename)
    
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=16384,
                )
            )
            result = response.text
            block = extract_sandpack_block(result)
            
            if block and "<Sandpack" in block and block.endswith("/>"):
                return block
            
            if attempt < retries - 1:
                print(f"  ⚠️  Попытка {attempt + 1}/{retries}: блок неполный, повтор...")
                time.sleep(2)
            else:
                print(f"  ❌ Не получен полный блок после {retries} попыток")
                
        except Exception as e:
            if attempt < retries - 1:
                print(f"  ⚠️  Попытка {attempt + 1}/{retries}: {e}, повтор...")
                time.sleep(2)
            else:
                print(f"  ❌ API ошибка: {e}")
    
    return None


def main():
    parser = argparse.ArgumentParser(description='Generate Sandpack playgrounds')
    parser.add_argument('--section', required=True, help='Section to process')
    parser.add_argument('--limit', type=int, default=0, help='Max lessons (0=all)')
    parser.add_argument('--model', default='gemini-3.1-pro-preview', help='Gemini model')
    parser.add_argument('--target', required=True, help='Target repo path')
    
    args = parser.parse_args()
    
    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_GEMINI_API_KEY not set")
        sys.exit(1)
    
    if args.section not in SECTIONS:
        print(f"❌ Unknown section: {args.section}")
        print(f"   Available: {', '.join(SECTIONS.keys())}")
        sys.exit(1)
    
    template = SECTIONS[args.section]
    client = genai.Client(api_key=api_key)
    
    pages_dir = Path(args.target) / "pages" / args.section
    if not pages_dir.exists():
        print(f"❌ Section directory not found: {pages_dir}")
        sys.exit(1)
    
    mdx_files = sorted([
        f for f in pages_dir.glob("*.mdx")
        if not f.name.startswith("_")
    ])
    
    # Filter files needing playgrounds
    needs_playground = []
    for fpath in mdx_files:
        content = fpath.read_text(encoding='utf-8')
        if not has_playground(content):
            needs_playground.append(fpath)
    
    if args.limit > 0:
        needs_playground = needs_playground[:args.limit]
    
    print(f"🚀 Generating playgrounds for {args.section}")
    print(f"   Model: {args.model}")
    print(f"   Total files: {len(mdx_files)}")
    print(f"   Need playgrounds: {len(needs_playground)}")
    print()
    
    if not needs_playground:
        print("✅ All lessons already have playgrounds")
        return
    
    success = 0
    failed = 0
    
    for i, fpath in enumerate(needs_playground, 1):
        lesson_name = fpath.stem
        print(f"[{i}/{len(needs_playground)}] {lesson_name}")
        
        content = fpath.read_text(encoding='utf-8')
        playground = generate_playground(
            client, args.model, content, args.section, template, fpath.name
        )
        
        if playground:
            with open(fpath, 'a', encoding='utf-8') as f:
                f.write("\n" + playground + "\n")
            print(f"  ✅ Added")
            success += 1
        else:
            print(f"  ❌ Failed")
            failed += 1
        
        time.sleep(1.5)
    
    print()
    print(f"{'='*60}")
    print(f"🎉 Done!")
    print(f"   Success: {success}")
    print(f"   Failed: {failed}")


if __name__ == "__main__":
    main()
