"""
Module 4 — Music Generator
============================
Generates ambient background music for reels.

Strategy:
1. Primary: Generate ambient music using sine wave synthesis (no API needed)
2. The generated ambient tracks are royalty-free by nature
3. Supports custom music files placed in assets/music/

The synthesized music creates soft, cinematic ambient pads 
perfect for reel backgrounds.
"""

import logging
import math
import random
import struct
import wave
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger("MusicGenerator")

# ─── Musical Constants ───────────────────────────────────────────────────────
SAMPLE_RATE = 44100
CHANNELS = 2  # Stereo

# Mood-based chord progressions (frequencies in Hz)
MOOD_CHORDS = {
    "calm": [
        [261.63, 329.63, 392.00],  # C major
        [349.23, 440.00, 523.25],  # F major
        [293.66, 369.99, 440.00],  # D minor
        [392.00, 493.88, 587.33],  # G major
    ],
    "inspirational": [
        [261.63, 329.63, 392.00],  # C major
        [293.66, 369.99, 440.00],  # D minor
        [349.23, 440.00, 523.25],  # F major
        [392.00, 493.88, 587.33],  # G major
    ],
    "nostalgic": [
        [220.00, 261.63, 329.63],  # A minor
        [349.23, 440.00, 523.25],  # F major
        [261.63, 329.63, 392.00],  # C major
        [329.63, 392.00, 493.88],  # E minor
    ],
    "epic": [
        [293.66, 369.99, 440.00],  # D minor
        [174.61, 220.00, 261.63],  # F2 major
        [261.63, 329.63, 392.00],  # C major
        [196.00, 246.94, 293.66],  # G2 minor
    ],
    "melancholic": [
        [220.00, 261.63, 329.63],  # A minor
        [329.63, 392.00, 493.88],  # E minor
        [293.66, 349.23, 440.00],  # D minor7
        [220.00, 277.18, 329.63],  # A min
    ],
    "dreamy": [
        [261.63, 392.00, 493.88],  # C sus
        [349.23, 523.25, 659.25],  # F sus
        [293.66, 440.00, 554.37],  # D sus
        [392.00, 587.33, 739.99],  # G sus
    ],
}


def generate_background_music(
    script: dict,
    output_dir: Optional[Path] = None,
    duration: Optional[float] = None
) -> Path:
    """
    Generate ambient background music based on the script's mood.

    Args:
        script: The structured script dict
        output_dir: Where to save the music file
        duration: Override total duration (auto-calculated from scenes if None)

    Returns:
        Path to generated .wav music file
    """
    output_dir = output_dir or config.TEMP_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check for user-provided music first
    custom_music = _find_custom_music()
    if custom_music:
        logger.info(f"Using custom music: {custom_music}")
        return custom_music

    # Calculate duration from scenes
    if duration is None:
        duration = sum(s.get("duration", config.SCENE_DURATION) for s in script["scenes"])
        duration += 2.0  # Add buffer for fade out

    # Determine mood from script
    audio_tone = script.get("audio_tone", "calm").lower()
    mood = _detect_mood(audio_tone)
    logger.info(f"Generating {duration:.1f}s ambient music | mood='{mood}' | tone='{audio_tone}'")

    output_path = output_dir / "background_music.wav"
    _synthesize_ambient(output_path, duration, mood)

    logger.info(f"Background music saved: {output_path}")
    return output_path


def _find_custom_music() -> Optional[Path]:
    """Look for user-provided music in assets/music/."""
    music_dir = config.MUSIC_DIR
    if not music_dir.exists():
        return None

    for ext in ["*.mp3", "*.wav", "*.ogg", "*.m4a"]:
        files = list(music_dir.glob(ext))
        if files:
            return files[0]  # Use first found

    return None


def _detect_mood(audio_tone: str) -> str:
    """Map script's audio_tone description to a mood key."""
    tone = audio_tone.lower()

    mood_keywords = {
        "calm": ["calm", "peaceful", "soft", "gentle", "ambient", "lo-fi", "lofi", "chill"],
        "inspirational": ["inspirational", "uplifting", "hope", "motivational", "bright"],
        "nostalgic": ["nostalgic", "memory", "vintage", "retro", "warm"],
        "epic": ["epic", "cinematic", "dramatic", "powerful", "intense", "orchestral"],
        "melancholic": ["sad", "melancholic", "emotional", "piano", "somber", "dark"],
        "dreamy": ["dreamy", "ethereal", "floating", "spacey", "atmospheric"],
    }

    for mood, keywords in mood_keywords.items():
        if any(kw in tone for kw in keywords):
            return mood

    return "calm"  # Default


def _synthesize_ambient(output_path: Path, duration: float, mood: str) -> None:
    """
    Synthesize ambient pad music using sine wave harmonics.
    Creates smooth, evolving chord pads — perfect for reel backgrounds.
    """
    chords = MOOD_CHORDS.get(mood, MOOD_CHORDS["calm"])
    total_samples = int(duration * SAMPLE_RATE)
    chord_duration = duration / len(chords)
    samples_per_chord = int(chord_duration * SAMPLE_RATE)

    audio_data = []
    random.seed(42)  # Reproducible

    for chord_idx, chord_freqs in enumerate(chords):
        # Repeat chords if needed to fill duration
        actual_chord = chords[chord_idx % len(chords)]

        for i in range(samples_per_chord):
            t = i / SAMPLE_RATE
            sample = 0.0

            for freq in actual_chord:
                # Main tone
                sample += 0.15 * math.sin(2 * math.pi * freq * t)
                # Soft overtone
                sample += 0.05 * math.sin(2 * math.pi * freq * 2 * t)
                # Sub bass
                sample += 0.08 * math.sin(2 * math.pi * freq * 0.5 * t)

            # Add very subtle LFO wobble for organic feel
            lfo = 1.0 + 0.03 * math.sin(2 * math.pi * 0.2 * t)
            sample *= lfo

            # Crossfade between chords
            crossfade_samples = int(0.5 * SAMPLE_RATE)  # 0.5s crossfade
            if i < crossfade_samples:
                sample *= i / crossfade_samples
            elif i > samples_per_chord - crossfade_samples:
                sample *= (samples_per_chord - i) / crossfade_samples

            # Soft clamp
            sample = max(-0.8, min(0.8, sample))

            # Stereo: slight delay for width
            left = sample
            right = sample * 0.95  # Subtle stereo difference
            audio_data.append((left, right))

    # Fill any remaining samples
    while len(audio_data) < total_samples:
        audio_data.append((0.0, 0.0))

    # Global fade in / fade out
    fade_in_samples = int(config.MUSIC_FADE_IN * SAMPLE_RATE)
    fade_out_samples = int(config.MUSIC_FADE_OUT * SAMPLE_RATE)

    for i in range(min(fade_in_samples, len(audio_data))):
        ratio = i / fade_in_samples
        audio_data[i] = (audio_data[i][0] * ratio, audio_data[i][1] * ratio)

    for i in range(min(fade_out_samples, len(audio_data))):
        idx = len(audio_data) - 1 - i
        ratio = i / fade_out_samples
        audio_data[idx] = (audio_data[idx][0] * ratio, audio_data[idx][1] * ratio)

    # Write WAV file
    with wave.open(str(output_path), "w") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(SAMPLE_RATE)

        for left, right in audio_data[:total_samples]:
            left_int = int(left * 32767)
            right_int = int(right * 32767)
            left_int = max(-32768, min(32767, left_int))
            right_int = max(-32768, min(32767, right_int))
            wav_file.writeframes(struct.pack("<hh", left_int, right_int))


# ─── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format=config.LOG_FORMAT)

    test_script = {
        "audio_tone": "soft cinematic piano",
        "scenes": [
            {"scene_number": 1, "duration": 4.0, "visual_prompt": "", "text_overlay": "", "narration": ""},
            {"scene_number": 2, "duration": 4.0, "visual_prompt": "", "text_overlay": "", "narration": ""},
            {"scene_number": 3, "duration": 4.0, "visual_prompt": "", "text_overlay": "", "narration": ""},
            {"scene_number": 4, "duration": 4.0, "visual_prompt": "", "text_overlay": "", "narration": ""},
        ]
    }

    path = generate_background_music(test_script)
    print(f"Music generated: {path}")
