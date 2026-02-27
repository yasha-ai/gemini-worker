#!/usr/bin/env python3
"""
Generate voice via Gemini TTS (Text-to-Speech).
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from google import genai


def main():
    parser = argparse.ArgumentParser(description='Generate voice via Gemini TTS')
    parser.add_argument('--text', required=True, help='Text to synthesize')
    parser.add_argument('--voice', default='Fenrir', help='Voice name (Fenrir, Kore, Charon, Aoede)')
    parser.add_argument('--model', default='gemini-2.5-flash-preview-tts', help='TTS model')
    parser.add_argument('--output', default='output.wav', help='Output WAV file')
    
    args = parser.parse_args()
    
    api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_GEMINI_API_KEY not set")
        sys.exit(1)
    
    print(f"🎙️ Generating speech with Gemini TTS...")
    print(f"   Model: {args.model}")
    print(f"   Voice: {args.voice}")
    print(f"   Text: {args.text[:100]}{'...' if len(args.text) > 100 else ''}")
    
    # Prepare request
    request_data = {
        "contents": [{
            "parts": [{"text": args.text}]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": args.voice
                    }
                }
            }
        }
    }
    
    # Call API via curl (google-genai SDK doesn't support TTS yet)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{args.model}:generateContent?key={api_key}"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as req_file:
        json.dump(request_data, req_file)
        req_path = req_file.name
    
    try:
        # Make request
        result = subprocess.run(
            ['curl', '-s', '-X', 'POST', url, 
             '-H', 'Content-Type: application/json',
             '-d', f'@{req_path}'],
            capture_output=True,
            text=True,
            check=True
        )
        
        response = json.loads(result.stdout)
        
        # Extract audio data
        if 'candidates' in response and len(response['candidates']) > 0:
            parts = response['candidates'][0].get('content', {}).get('parts', [])
            for part in parts:
                if 'inlineData' in part:
                    mime_type = part['inlineData'].get('mimeType', 'audio/L16')
                    audio_b64 = part['inlineData']['data']
                    
                    # Extract sample rate from MIME type
                    sample_rate = 24000  # default
                    if 'rate=' in mime_type:
                        try:
                            sample_rate = int(mime_type.split('rate=')[1].split(';')[0])
                        except:
                            pass
                    
                    print(f"   📦 MIME type: {mime_type}")
                    print(f"   🎵 Sample rate: {sample_rate}Hz")
                    
                    # Decode audio
                    audio_data = base64.b64decode(audio_b64)
                    
                    # Save as PCM temporarily
                    with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as pcm_file:
                        pcm_file.write(audio_data)
                        pcm_path = pcm_file.name
                    
                    print(f"   💾 Raw PCM size: {len(audio_data)} bytes")
                    
                    # Convert PCM to WAV using ffmpeg
                    subprocess.run(
                        ['ffmpeg', '-f', 's16le', '-ar', str(sample_rate), '-ac', '1',
                         '-i', pcm_path, '-y', args.output],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True
                    )
                    
                    os.unlink(pcm_path)
                    
                    wav_size = Path(args.output).stat().st_size
                    print(f"✅ Voice saved to: {args.output}")
                    print(f"   🔊 File size: {wav_size} bytes ({wav_size / 1024:.1f} KB)")
                    return
        
        # If no audio found, check for error
        if 'error' in response:
            print(f"❌ API Error: {response['error']}")
        else:
            print(f"❌ No audio in response")
            print(f"Response: {json.dumps(response, indent=2)[:500]}")
        sys.exit(1)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Request failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if os.path.exists(req_path):
            os.unlink(req_path)


if __name__ == "__main__":
    main()
