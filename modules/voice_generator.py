"""
Module 3 — Voice Generator
============================
Generates soft cinematic AI voiceover narration using edge-tts (100% free, no API key).

edge-tts uses Microsoft's Azure Cognitive Services TTS engine for free.
Supports 300+ voices across 50+ languages.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import edge_tts

import config

logger = logging.getLogger("VoiceGenerator")


async def _generate_voice_async(
    text: str,
    output_path: Path,
    voice: str,
    rate: str,
    pitch: str
) -> Path:
    """Async implementation of voice generation."""
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch
    )
    await communicate.save(str(output_path))
    return output_path


def generate_narration(
    script: dict,
    output_dir: Optional[Path] = None
) -> list[Path]:
    """
    Generate voiceover audio for each scene's narration text.

    Args:
        script: The structured script dict from ScriptGenerator
        output_dir: Directory to save audio files

    Returns:
        List of file paths to generated .mp3 narration files
    """
    output_dir = output_dir or config.TEMP_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_paths = []

    for scene in script["scenes"]:
        scene_num = scene["scene_number"]
        narration_text = scene.get("narration", "").strip()

        if not narration_text:
            logger.warning(f"Scene {scene_num} has no narration text, skipping voice")
            audio_paths.append(None)
            continue

        audio_path = output_dir / f"narration_{scene_num:02d}.mp3"
        logger.info(f"Generating voice for Scene {scene_num}: '{narration_text[:60]}...'")

        try:
            asyncio.run(_generate_voice_async(
                text=narration_text,
                output_path=audio_path,
                voice=config.TTS_VOICE,
                rate=config.TTS_RATE,
                pitch=config.TTS_PITCH
            ))
            logger.info(f"Scene {scene_num} narration saved: {audio_path}")
            audio_paths.append(audio_path)

        except Exception as e:
            logger.error(f"Scene {scene_num} voice generation failed: {e}")
            audio_paths.append(None)

    generated = sum(1 for p in audio_paths if p is not None)
    logger.info(f"Generated {generated}/{len(audio_paths)} narration audio files")
    return audio_paths


def generate_full_narration(
    script: dict,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Generate a single combined voiceover file for the entire script.
    Useful when you want one continuous narration track.

    Args:
        script: The structured script dict
        output_dir: Output directory

    Returns:
        Path to the combined narration .mp3 file
    """
    output_dir = output_dir or config.TEMP_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Combine all narration texts with pauses
    full_text = ""
    for scene in script["scenes"]:
        narration = scene.get("narration", "").strip()
        if narration:
            full_text += narration + " ... "  # Ellipsis creates a natural pause

    full_text = full_text.strip()
    if not full_text:
        raise ValueError("No narration text found in script")

    output_path = output_dir / "narration_full.mp3"
    logger.info(f"Generating full narration ({len(full_text)} chars)")

    asyncio.run(_generate_voice_async(
        text=full_text,
        output_path=output_path,
        voice=config.TTS_VOICE,
        rate=config.TTS_RATE,
        pitch=config.TTS_PITCH
    ))

    logger.info(f"Full narration saved: {output_path}")
    return output_path


async def list_available_voices(language_filter: str = "en") -> list[dict]:
    """List all available TTS voices, optionally filtered by language."""
    voices = await edge_tts.list_voices()
    if language_filter:
        voices = [v for v in voices if v["Locale"].startswith(language_filter)]
    return voices


def print_voices(language: str = "en"):
    """Print available voices for a language."""
    voices = asyncio.run(list_available_voices(language))
    print(f"\n{'Voice Name':<35} {'Gender':<10} {'Locale'}")
    print("─" * 60)
    for v in voices:
        print(f"{v['ShortName']:<35} {v['Gender']:<10} {v['Locale']}")


# ─── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format=config.LOG_FORMAT)

    test_script = {
        "scenes": [
            {
                "scene_number": 1,
                "narration": "In the silence of the mountains, you discover who you truly are.",
                "visual_prompt": "",
                "text_overlay": "",
                "duration": 4.0
            },
            {
                "scene_number": 2,
                "narration": "Every step forward is a step closer to the person you're becoming.",
                "visual_prompt": "",
                "text_overlay": "",
                "duration": 4.0
            }
        ]
    }

    paths = generate_narration(test_script)
    print(f"Generated narrations: {paths}")

    print("\nAvailable English voices:")
    print_voices("en")
