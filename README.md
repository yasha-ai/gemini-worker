# 🤖 Gemini Worker

Secure Gemini API worker via GitHub Actions. Prevents API key leaks by keeping secrets in GitHub and exposing only workflow triggers.

## 🎯 Purpose

Run Gemini API operations (playgrounds, images, text generation) without exposing API keys locally. Key lives in GitHub Secrets, workflows are triggered remotely.

## 🔧 Workflows

### 1. Generate Playgrounds
**File:** `.github/workflows/generate-playgrounds.yml`

Generates interactive Sandpack playgrounds for lessons.

**Trigger:**
```bash
gh workflow run generate-playgrounds.yml \
  -R yasha-ai/gemini-worker \
  -f section=html \
  -f limit=10 \
  -f model=gemini-3.1-pro-preview
```

**Outputs:** Commits playground files to target repo.

---

### 2. Generate Image
**File:** `.github/workflows/generate-image.yml`

Generates images via Gemini image models.

**Trigger:**
```bash
gh workflow run generate-image.yml \
  -R yasha-ai/gemini-worker \
  -f prompt="A futuristic AI workspace" \
  -f model=gemini-3-pro-image-preview
```

**Outputs:** Image uploaded as artifact.

---

### 3. Generate Text
**File:** `.github/workflows/generate-text.yml`

Generates text content via Gemini text models.

**Trigger:**
```bash
gh workflow run generate-text.yml \
  -R yasha-ai/gemini-worker \
  -f prompt="Write a short intro about AI" \
  -f model=gemini-3.1-pro-preview
```

**Outputs:** Text file uploaded as artifact.

---

### 4. Generate Voice (TTS)
**File:** `.github/workflows/generate-voice.yml`

Generates voice audio via Gemini TTS (Text-to-Speech).

**Trigger:**
```bash
gh workflow run generate-voice.yml \
  -R yasha-ai/gemini-worker \
  -f text="Привет! Это тест синтеза речи." \
  -f voice=Fenrir \
  -f model=gemini-2.5-flash-preview-tts
```

**Voices:** Fenrir (male, energetic), Kore, Charon, Aoede  
**Outputs:** WAV audio file uploaded as artifact.

---

### 5. YouTube Ideas
**File:** `.github/workflows/youtube-ideas.yml`

Generates YouTube video ideas.

**Trigger:**
```bash
gh workflow run youtube-ideas.yml \
  -R yasha-ai/gemini-worker \
  -f count=10 \
  -f topic="AI coding tools" \
  -f model=gemini-3.1-pro-preview
```

**Outputs:** JSON file with ideas uploaded as artifact.

---

## 🔐 Setup

### 1. Add GitHub Secret
Go to **Settings → Secrets → Actions** and add:
- Name: `GOOGLE_GEMINI_API_KEY`
- Value: Your Gemini API key

### 2. Grant Workflow Permissions
**Settings → Actions → General → Workflow permissions:**
- ✅ Read and write permissions
- ✅ Allow GitHub Actions to create and approve pull requests

---

## 🚀 Usage from OpenClaw

Trigger workflows via GitHub API:

```python
import subprocess

# Trigger playground generation
subprocess.run([
    "gh", "workflow", "run", "generate-playgrounds.yml",
    "-R", "yasha-ai/gemini-worker",
    "-f", "section=html",
    "-f", "limit=5"
])

# Wait for completion and download artifacts
# (implementation in scripts/)
```

---

## 📁 Scripts

All Python scripts in `scripts/` directory can be tested locally with `GOOGLE_GEMINI_API_KEY` env var, but production runs happen via GitHub Actions.

---

## 🛡️ Security

- ✅ API key never leaves GitHub Secrets
- ✅ No local key storage
- ✅ All operations audited in GitHub Actions logs
- ✅ Workflows can be triggered remotely without key access

---

## 📝 License

MIT
