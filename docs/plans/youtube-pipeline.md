# Daily Threat — YouTube Pipeline Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan.

**Goal:** Transform Daily Threat from a simple voice memo into a fully autonomous daily YouTube video pipeline — fetch CVEs, write noir script, generate voice, render video, create thumbnail, upload to YouTube, notify via Telegram.

**Architecture:**
```
daily_threat/
  config.py          # All settings, paths, API keys
  fetcher.py         # CVE data from Shodan CVEDB + MCP tools
  writer.py          # Noir script generation via OpenRouter
  audio.py           # ElevenLabs TTS with chunking for long scripts
  video.py           # Video generation (moviepy + Pillow)
  thumbnail.py       # Auto-generate YouTube thumbnail
  youtube.py         # YouTube upload via Data API v3
  pipeline.py        # Orchestrate the full flow
```

**Tech Stack:** Python 3.11, moviepy, Pillow, google-api-python-client, google-auth-oauthlib, requests

---

## Phase 1: Refactor into modules

### Task 1: Create config.py
Central config — all paths, API keys, voice settings, video settings.

### Task 2: Create fetcher.py
Extract CVE fetching from daily_threat.py into standalone module.

### Task 3: Create writer.py
Extract script generation. Upgrade prompt for YouTube-length (5-7 min, ~800 words, 3-4 CVEs in depth).

### Task 4: Create audio.py
Extract TTS. Add text chunking for scripts >500 words to prevent voice drift. Chunk at paragraph breaks, generate each chunk, concatenate with ffmpeg.

## Phase 2: Video generation

### Task 5: Create video.py
Generate a full video from script text + audio file:
- Title card intro (3s)
- CVE segment cards with animated elements
- Waveform visualization synced to audio
- Scanline/CRT overlay
- Outro card (5s)

### Task 6: Test video pipeline end-to-end

## Phase 3: Thumbnail

### Task 7: Create thumbnail.py
1280x720 dramatic noir thumbnail with CVE IDs, severity badges, date.

## Phase 4: YouTube upload

### Task 8: Create youtube.py
OAuth2 flow + upload with metadata, tags, description, chapters.

### Task 9: First-time auth flow
Interactive OAuth2 consent to get refresh token.

## Phase 5: Orchestration

### Task 10: Create pipeline.py
Full flow: fetch → write → audio → video → thumbnail → upload → notify.

### Task 11: Set up cron job
