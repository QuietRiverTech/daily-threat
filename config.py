"""Central configuration for Daily Threat pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load env from ~/.hermes/.env
load_dotenv(Path.home() / '.hermes' / '.env')

# Paths
PROJECT_DIR = Path(__file__).parent
EPISODES_DIR = PROJECT_DIR / 'episodes'
EPISODES_DIR.mkdir(exist_ok=True)

# API Keys
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY') or os.getenv('OR_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
SHODAN_API_KEY = os.getenv('SHODAN_API_KEY')

# Voice Settings (tuned for consistency on long-form)
VOICE_ID = 'oNewkOzghH74whuAIBh0'  # Jelf
TTS_MODEL = 'eleven_multilingual_v2'
VOICE_SETTINGS = {
    'stability': 0.85,
    'similarity_boost': 0.80,
    'style': 0.15,
    'speed': 0.90,
}

# Script Settings
LLM_MODEL = 'anthropic/claude-sonnet-4'
SCRIPT_TARGET_WORDS = 800  # ~5-6 min YouTube video
MAX_CVES = 4

# Video Settings
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30
BG_COLOR = (10, 10, 15)  # #0a0a0f
GREEN = (0, 255, 65)  # #00ff41
AMBER = (255, 176, 0)  # #ffb000
RED = (255, 0, 64)  # #ff0040
DIM_GREEN = (13, 59, 13)  # #0d3b0d
WHITE = (230, 230, 230)

# YouTube
YOUTUBE_CATEGORY = '28'  # Science & Technology
CLIENT_SECRET_FILE = PROJECT_DIR / 'client_secret.json'
TOKEN_FILE = PROJECT_DIR / 'token.json'
