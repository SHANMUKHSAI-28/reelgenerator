"""
ReelGenerator Configuration
===========================
Central configuration for the automated reel factory pipeline.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
LOGS_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"
MUSIC_DIR = ASSETS_DIR / "music"

# Create dirs on import
for d in [OUTPUT_DIR, TEMP_DIR, LOGS_DIR, ASSETS_DIR, MUSIC_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── OpenRouter API (Free Models) ────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free models on OpenRouter (pick one)
# Options: "meta-llama/llama-3.1-8b-instruct:free",
#          "mistralai/mistral-7b-instruct:free",
#          "google/gemma-2-9b-it:free",
#          "qwen/qwen-2-7b-instruct:free"
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b:free")

# ─── Visual Generation ────────────────────────────────────────────────────────
# Pollinations.ai — completely free, no API key needed
POLLINATIONS_IMAGE_URL = "https://image.pollinations.ai/prompt/{prompt}"
POLLINATIONS_WIDTH = 1080
POLLINATIONS_HEIGHT = 1920
IMAGE_GENERATION_TIMEOUT = 120  # seconds

# ─── Voice Generation (edge-tts — free, no API key) ─────────────────────────
# Voices: en-US-AriaNeural, en-US-GuyNeural, en-GB-SoniaNeural,
#         en-IN-NeerjaNeural, en-AU-NatashaNeural
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")
TTS_RATE = os.getenv("TTS_RATE", "-10%")  # Slower = more cinematic
TTS_PITCH = os.getenv("TTS_PITCH", "-5Hz")

# ─── Music ────────────────────────────────────────────────────────────────────
# Duration of background music fade-in/out in seconds
MUSIC_FADE_IN = 1.0
MUSIC_FADE_OUT = 2.0
MUSIC_VOLUME = 0.15  # Background music volume (0.0 to 1.0)

# ─── Assembly / Export ────────────────────────────────────────────────────────
REEL_WIDTH = 1080
REEL_HEIGHT = 1920
REEL_FPS = 30
SCENE_DURATION = 5.0  # Default seconds per scene (gives narration room to breathe)
CROSSFADE_DURATION = 0.4
EXPORT_CODEC = "libx264"
EXPORT_AUDIO_CODEC = "aac"
EXPORT_BITRATE = "8M"

# ─── Text Overlays ───────────────────────────────────────────────────────────
OVERLAY_FONT_SIZE = 56
OVERLAY_FONT_COLOR = "white"
OVERLAY_FONT = "Arial-Bold"
OVERLAY_STROKE_COLOR = "black"
OVERLAY_STROKE_WIDTH = 3
OVERLAY_POSITION = ("center", 0.70)  # (x, y%) from top - moved higher to prevent cutoff

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s"
