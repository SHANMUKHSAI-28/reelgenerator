"""
Module 1 — Script Generator
============================
Uses OpenRouter free LLM models to generate a cinematic reel script.

Output JSON schema:
{
  "title": str,
  "emotional_core": str,
  "audio_tone": str,
  "scenes": [
    {
      "scene_number": int,
      "visual_prompt": str,       # Detailed cinematic prompt for image/video AI
      "text_overlay": str,        # Short text shown on screen
      "narration": str,           # Voiceover text for this scene
      "duration": float           # Seconds
    }
  ]
}
"""

import json
import logging
import requests
from typing import Optional

import config

logger = logging.getLogger("ScriptGenerator")


SYSTEM_PROMPT = """You are a cinematic reel scriptwriter for short-form vertical video content (Instagram Reels, TikTok, YouTube Shorts).

Your job is to generate a complete reel script as a JSON object. The reel should be emotional, visually stunning, and tell a micro-story in 15–30 seconds total.

OUTPUT FORMAT — Return ONLY valid JSON, no markdown, no explanation:
{
  "title": "A short catchy title",
  "emotional_core": "The core emotion/theme (e.g., nostalgia, hope, wonder, ambition)",
  "audio_tone": "Description of ideal background music mood (e.g., soft piano, epic cinematic, lo-fi ambient)",
  "scenes": [
    {
      "scene_number": 1,
      "visual_prompt": "Ultra-detailed cinematic image prompt. Include: subject, setting, lighting (golden hour/neon/moody), camera angle (close-up/wide/aerial), color palette, atmosphere. Must be photorealistic and vertical (9:16 aspect ratio). Example: 'Cinematic close-up of a young woman standing at a rain-soaked window at golden hour, warm amber light streaming through droplets, shallow depth of field, melancholic mood, 9:16 vertical frame'",
      "text_overlay": "Short impactful text shown on screen (max 10 words)",
      "narration": "Soft voiceover narration for this scene (1-2 sentences, poetic and atmospheric)",
      "duration": 4.0
    }
  ]
}

RULES:
- Generate exactly 4 scenes
- Each scene duration: 3–5 seconds (total reel: 15–25 seconds)
- Visual prompts must be EXTREMELY detailed and cinematic
- Text overlays must be punchy and emotional
- Narration should be soft, ambient, poetic
- Total narration should fit within the total reel duration
- Return ONLY the JSON object, nothing else"""


def generate_script(
    topic: str,
    style: str = "cinematic",
    mood: str = "inspirational",
    openrouter_key: Optional[str] = None
) -> dict:
    """
    Generate a complete reel script using OpenRouter free LLM.

    Args:
        topic: The reel topic/theme (e.g., "morning routine", "city life", "self-growth")
        style: Visual style (cinematic, anime, documentary, dreamy)
        mood: Emotional mood (inspirational, nostalgic, energetic, calm)
        openrouter_key: Optional API key override

    Returns:
        dict: Structured script with scenes, prompts, overlays, narration
    """
    api_key = openrouter_key or config.OPENROUTER_API_KEY
    if not api_key:
        raise ValueError(
            "OpenRouter API key not set. Add OPENROUTER_API_KEY to your .env file.\n"
            "Get a free key at: https://openrouter.ai"
        )

    user_prompt = (
        f"Create a cinematic reel script about: {topic}\n"
        f"Visual style: {style}\n"
        f"Mood/emotion: {mood}\n"
        f"Generate 4 scenes with ultra-detailed visual prompts, text overlays, and narration."
    )

    logger.info(f"Generating script | topic='{topic}' style='{style}' mood='{mood}'")
    logger.info(f"Using model: {config.LLM_MODEL}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://reelgenerator.local",
        "X-Title": "ReelGenerator"
    }

    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.85,
        "max_tokens": 2000,
        "top_p": 0.9
    }

    try:
        response = requests.post(
            config.OPENROUTER_BASE_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"].strip()
        logger.debug(f"Raw LLM response:\n{content}")

        # Parse JSON — handle markdown code blocks if model wraps it
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        script = json.loads(content)

        # Validate structure
        _validate_script(script)

        logger.info(f"Script generated: '{script.get('title', 'Untitled')}' — {len(script['scenes'])} scenes")
        return script

    except requests.exceptions.HTTPError as e:
        logger.error(f"OpenRouter API error: {e.response.status_code} — {e.response.text}")
        raise RuntimeError(f"OpenRouter API error: {e.response.status_code}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Raw content: {content}")
        raise RuntimeError("LLM returned invalid JSON. Try again or switch model.") from e
    except Exception as e:
        logger.error(f"Script generation failed: {e}")
        raise


def _validate_script(script: dict) -> None:
    """Validate the script structure and fill defaults."""
    required_keys = ["title", "emotional_core", "audio_tone", "scenes"]
    for key in required_keys:
        if key not in script:
            raise ValueError(f"Script missing required key: '{key}'")

    if not isinstance(script["scenes"], list) or len(script["scenes"]) == 0:
        raise ValueError("Script must contain at least one scene")

    for i, scene in enumerate(script["scenes"]):
        scene.setdefault("scene_number", i + 1)
        scene.setdefault("duration", config.SCENE_DURATION)

        for field in ["visual_prompt", "text_overlay", "narration"]:
            if field not in scene:
                raise ValueError(f"Scene {i+1} missing '{field}'")

    total_duration = sum(s["duration"] for s in script["scenes"])
    logger.info(f"Total reel duration: {total_duration:.1f}s across {len(script['scenes'])} scenes")


# ─── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format=config.LOG_FORMAT)
    script = generate_script("a solitary traveler finding peace in the mountains", mood="peaceful")
    print(json.dumps(script, indent=2))
