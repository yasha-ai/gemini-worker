#!/usr/bin/env python3
"""
Generate music via Vertex AI Lyria model.
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path
import requests


def main():
    parser = argparse.ArgumentParser(description='Generate music via Vertex AI Lyria')
    parser.add_argument('--prompt', required=True, help='Music generation prompt')
    parser.add_argument('--negative-prompt', help='Negative prompt (optional)')
    parser.add_argument('--seed', type=int, help='Random seed (optional)')
    parser.add_argument('--duration', type=int, default=30, help='Duration in seconds (default: 30)')
    parser.add_argument('--output', default='music.wav', help='Output WAV file')
    
    args = parser.parse_args()
    
    project_id = os.environ.get("VERTEX_PROJECT_ID", "gen-lang-client-0851415172")
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not credentials_path or not os.path.exists(credentials_path):
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set or file not found")
        sys.exit(1)
    
    # Get access token from service account
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
        
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        credentials.refresh(Request())
        api_key = credentials.token
    except Exception as e:
        print(f"❌ Failed to get access token from service account: {e}")
        sys.exit(1)
    
    location = "us-central1"
    model = "lyria-002"
    endpoint = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model}:predict"
    
    print(f"🎵 Generating music with Lyria...")
    print(f"   Prompt: {args.prompt}")
    if args.negative_prompt:
        print(f"   Negative: {args.negative_prompt}")
    if args.seed:
        print(f"   Seed: {args.seed}")
    print(f"   Duration: {args.duration}s")
    
    # Build request
    instance = {
        "prompt": args.prompt,
        "duration": args.duration
    }
    
    if args.negative_prompt:
        instance["negative_prompt"] = args.negative_prompt
    
    if args.seed:
        instance["seed"] = args.seed
    
    request_data = {
        "instances": [instance],
        "parameters": {
            "sample_count": 1
        }
    }
    
    # Make API request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(endpoint, headers=headers, json=request_data)
        response.raise_for_status()
        
        result = response.json()
        
        # Check for errors
        if 'error' in result:
            print(f"❌ API Error: {result['error'].get('message', result['error'])}")
            sys.exit(1)
        
        # Extract audio
        if 'predictions' not in result or len(result['predictions']) == 0:
            print("❌ No predictions in response")
            print(f"Response: {json.dumps(result, indent=2)[:500]}")
            sys.exit(1)
        
        audio_content = result['predictions'][0].get('audioContent')
        
        if not audio_content:
            print("❌ No audioContent in response")
            print(f"Response: {json.dumps(result, indent=2)[:500]}")
            sys.exit(1)
        
        # Decode and save
        audio_data = base64.b64decode(audio_content)
        Path(args.output).write_bytes(audio_data)
        
        file_size = len(audio_data)
        print(f"✅ Music generated successfully!")
        print(f"   📁 Output: {args.output}")
        print(f"   📊 Size: {file_size / 1024 / 1024:.2f} MB")
        print(f"   ⏱️  Duration: {args.duration}s (48kHz WAV)")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
