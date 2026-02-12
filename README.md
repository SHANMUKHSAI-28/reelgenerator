# 🎬 ReelGenerator — Automated Reel Factory

A fully automated pipeline that generates cinematic short-form reels (Instagram/TikTok/YouTube Shorts) from a single text prompt.

**Topic → Script → Visuals → Voice → Music → Assembly → MP4**

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    main.py (Orchestrator)                     │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│  Script  │  Visual  │  Voice   │  Music   │   Assembly     │
│Generator │Generator │Generator │Generator │   Engine       │
│          │          │          │          │                │
│OpenRouter│Pollinat- │ edge-tts │ Synth    │  MoviePy +     │
│Free LLM  │ions.ai   │ (free)   │ Engine   │  FFmpeg        │
│          │ (free)   │          │ (built-in)│               │
└──────────┴──────────┴──────────┴──────────┴────────────────┘
                                                      │
                                              ┌───────▼──────┐
                                              │  Approval    │
                                              │  Gate +      │
                                              │  Audit Log   │
                                              └──────────────┘
```

## 💰 Cost: $0

Everything uses free APIs and tools:
- **Script**: OpenRouter free models (Llama 3.1, Mistral 7B, Gemma 2)
- **Visuals**: Pollinations.ai (free, no API key)
- **Voice**: edge-tts / Microsoft TTS (free, no API key)
- **Music**: Built-in synthesizer (no API needed)
- **Assembly**: MoviePy + FFmpeg (open source)

## 🚀 Quick Start

### 1. Install FFmpeg

```bash
# Windows (via Chocolatey)
choco install ffmpeg

# OR download from https://ffmpeg.org/download.html and add to PATH

# Mac
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### 2. Install Python Dependencies

```bash
cd reelgenerator
pip install -r requirements.txt
```

### 3. Set Up API Key

```bash
# Copy example env
copy .env.example .env

# Edit .env and add your OpenRouter API key
# Get free key at: https://openrouter.ai
```

### 4. Generate a Reel!

```bash
# Basic usage
python main.py "morning routine of a dreamer"

# With mood and style
python main.py "city life at midnight" --mood nostalgic --style cinematic

# Auto-approve (skip review)
python main.py "self-growth journey" --mood inspirational --auto-approve

# Custom output name
python main.py "ocean waves and peace" --mood calm --output my_reel
```

## 📁 Project Structure

```
reelgenerator/
├── main.py                    # 🎯 Entry point — runs full pipeline
├── config.py                  # ⚙️ All configuration settings
├── requirements.txt           # 📦 Python dependencies
├── .env                       # 🔑 API keys (create from .env.example)
├── .env.example               # 📋 Environment template
├── modules/
│   ├── script_generator.py    # 📄 LLM script generation
│   ├── visual_generator.py    # 🎨 AI image generation
│   ├── voice_generator.py     # 🎙️ TTS voiceover
│   ├── music_generator.py     # 🎵 Ambient music synthesis
│   ├── assembly_engine.py     # 🎬 Video assembly (MoviePy)
│   └── approval_gate.py       # ✅ Review gate + audit logging
├── output/                    # 📁 Final MP4 reels
├── temp/                      # 🗑️ Temporary assets (auto-cleaned)
├── logs/                      # 📋 Generation audit logs
└── assets/
    └── music/                 # 🎵 Custom music (optional)
```

## ⚙️ Configuration

All settings are in `config.py`. Key options:

| Setting | Default | Description |
|---------|---------|-------------|
| `LLM_MODEL` | `meta-llama/llama-3.1-8b-instruct:free` | OpenRouter model |
| `TTS_VOICE` | `en-US-AriaNeural` | Voice for narration |
| `REEL_WIDTH` | `1080` | Output width |
| `REEL_HEIGHT` | `1920` | Output height (9:16) |
| `SCENE_DURATION` | `4.0` | Default seconds per scene |
| `MUSIC_VOLUME` | `0.15` | Background music volume |
| `EXPORT_BITRATE` | `8M` | Video quality |

## 🎙️ Available Voices

```bash
# List all English voices
python -c "from modules.voice_generator import print_voices; print_voices('en')"
```

Popular voices:
- `en-US-AriaNeural` — Female, warm
- `en-US-GuyNeural` — Male, natural
- `en-GB-SoniaNeural` — British female
- `en-IN-NeerjaNeural` — Indian female

## 🎵 Custom Music

Drop any `.mp3` or `.wav` file into `assets/music/` and it will be used instead of the synthesized ambient music.

## 📋 Audit Logs

Every generation run is logged to `logs/run_YYYYMMDD_HHMMSS.json` with:
- Full script and prompts
- Asset file paths
- Per-step timings
- Approval status and reviewer notes
- Any errors encountered

## 🎬 Output

Reels are exported to `output/` as:
- Format: MP4 (H.264 + AAC)
- Resolution: 1080×1920 (9:16 vertical)
- FPS: 30
- Typical size: 5–15 MB
- Duration: 15–25 seconds

## 📝 Pipeline Flow

1. **Script Generation** → OpenRouter LLM creates 4 scenes with visual prompts, text overlays, narration
2. **Visual Generation** → Pollinations.ai generates cinematic images from prompts
3. **Voice Generation** → edge-tts creates soft voiceover narration
4. **Music Generation** → Ambient pads synthesized to match script mood
5. **Assembly** → MoviePy stitches everything with Ken Burns zoom, text overlays, crossfades
6. **Approval Gate** → Interactive review before finalizing

## CLI Options

```
python main.py --help

positional arguments:
  topic                 What the reel is about

options:
  --style, -s          cinematic|dreamy|documentary|anime|minimal|neon
  --mood, -m           inspirational|nostalgic|calm|epic|melancholic|dreamy|energetic
  --auto-approve, -a   Skip manual approval
  --output, -o         Custom output filename
```
