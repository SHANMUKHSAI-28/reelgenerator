"""
Module 5 — Assembly Engine
============================
Stitches together all generated assets into a final 1080x1920 MP4 reel.

Uses MoviePy for composition:
- Scene images → video clips with Ken Burns effect (slow zoom/pan)
- Text overlays with animated fade-in
- Voiceover narration (composed as separate audio track)
- Background music layer
- Crossfade transitions
- Export as MP4 (H.264 + AAC)

Requires FFmpeg installed on system.
"""

import logging
from pathlib import Path
from typing import Optional

from moviepy import (
    ImageClip,
    TextClip,
    CompositeVideoClip,
    CompositeAudioClip,
    AudioFileClip,
    concatenate_videoclips,
    concatenate_audioclips,
    vfx,
)

import config

logger = logging.getLogger("AssemblyEngine")


def assemble_reel(
    script: dict,
    image_paths: list[Path],
    narration_paths: list[Optional[Path]],
    music_path: Optional[Path],
    output_path: Optional[Path] = None,
) -> Path:
    """
    Assemble all assets into a final MP4 reel.

    Args:
        script: The structured script dict
        image_paths: List of scene image file paths
        narration_paths: List of narration audio paths (None for silent scenes)
        music_path: Path to background music file
        output_path: Final MP4 output path

    Returns:
        Path to the exported MP4 file
    """
    if output_path is None:
        title_slug = script.get("title", "reel").lower().replace(" ", "_")[:30]
        # Remove special chars from filename
        title_slug = "".join(c for c in title_slug if c.isalnum() or c in "_- ")
        title_slug = title_slug.strip() or "reel"
        output_path = config.OUTPUT_DIR / f"{title_slug}.mp4"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    scenes = script["scenes"]
    crossfade = config.CROSSFADE_DURATION

    logger.info(f"Assembling reel: {len(scenes)} scenes → {output_path}")

    # ─── Build scene video clips (NO audio attached) ──────────────────────
    scene_clips = []
    scene_durations = []

    for i, scene in enumerate(scenes):
        scene_num = scene["scene_number"]
        duration = scene.get("duration", config.SCENE_DURATION)
        text_overlay = scene.get("text_overlay", "")

        logger.info(f"Building Scene {scene_num} clip ({duration}s)")

        # 1. Base image clip with Ken Burns effect (slow zoom)
        if i < len(image_paths) and image_paths[i] and image_paths[i].exists():
            img_clip = _create_scene_clip(image_paths[i], duration)
        else:
            logger.warning(f"Scene {scene_num}: No image found, using black frame")
            img_clip = ImageClip(
                _create_black_frame(), duration=duration
            ).with_fps(config.REEL_FPS)

        # 2. Text overlay
        if text_overlay:
            txt_clip = _create_text_overlay(text_overlay, duration)
            img_clip = CompositeVideoClip(
                [img_clip, txt_clip],
                size=(config.REEL_WIDTH, config.REEL_HEIGHT)
            )

        img_clip = img_clip.with_duration(duration)
        scene_clips.append(img_clip)
        scene_durations.append(duration)

    # ─── Concatenate scenes with crossfade (video only) ───────────────────
    if len(scene_clips) > 1:
        logger.info("Joining scenes with crossfade transitions...")
        for i in range(1, len(scene_clips)):
            scene_clips[i] = scene_clips[i].with_effects([
                vfx.CrossFadeIn(crossfade)
            ])
        final_video = concatenate_videoclips(
            scene_clips,
            method="compose",
            padding=-crossfade
        )
    else:
        final_video = scene_clips[0]

    total_video_duration = final_video.duration
    logger.info(f"Video track assembled: {total_video_duration:.1f}s")

    # ─── Build audio track separately ─────────────────────────────────────
    # Calculate the start time of each scene in the final timeline
    scene_start_times = []
    t = 0.0
    for i, dur in enumerate(scene_durations):
        scene_start_times.append(t)
        if i < len(scene_durations) - 1:
            t += dur - crossfade  # Each subsequent scene starts early by crossfade amount
        else:
            t += dur

    audio_clips = []

    # Add narration clips — prevent overlap by tracking when each ends
    narration_cursor = 0.0  # Earliest time the next narration can start
    NARRATION_GAP = 0.3     # Minimum silence gap between narrations (seconds)

    for i, scene in enumerate(scenes):
        if i < len(narration_paths) and narration_paths[i] and narration_paths[i].exists():
            try:
                narr = AudioFileClip(str(narration_paths[i]))

                # Ideal start = scene start time, but never before previous narration ends
                ideal_start = scene_start_times[i]
                safe_start = max(ideal_start, narration_cursor)

                # Ensure narration doesn't exceed this scene's visual end time
                scene_end = scene_start_times[i] + scene_durations[i]
                if safe_start + narr.duration > scene_end + 0.2:
                    # Trim narration to fit within scene bounds (+ tiny grace)
                    available = max(scene_end - safe_start, 0.5)
                    narr = narr.subclipped(0, min(narr.duration, available))
                    logger.debug(f"Scene {scene['scene_number']}: trimmed narration to {narr.duration:.1f}s")

                narr = narr.with_start(safe_start)
                audio_clips.append(narr)

                # Update cursor so next narration starts after this one + gap
                narration_cursor = safe_start + narr.duration + NARRATION_GAP

                logger.debug(
                    f"Scene {scene['scene_number']}: narration at t={safe_start:.1f}s "
                    f"({narr.duration:.1f}s) → ends at {safe_start + narr.duration:.1f}s"
                )
            except Exception as e:
                logger.warning(f"Scene {scene['scene_number']}: Failed to load narration: {e}")

    # Add background music
    if music_path and music_path.exists():
        logger.info("Mixing background music...")
        try:
            music_audio = AudioFileClip(str(music_path))

            # Loop music if shorter than video
            if music_audio.duration < total_video_duration:
                loops_needed = int(total_video_duration / music_audio.duration) + 1
                music_parts = [music_audio] * loops_needed
                music_audio = concatenate_audioclips(music_parts)

            # Trim to video length
            music_audio = music_audio.subclipped(0, total_video_duration)
            music_audio = music_audio.with_volume_scaled(config.MUSIC_VOLUME)
            audio_clips.append(music_audio)
        except Exception as e:
            logger.warning(f"Failed to add background music: {e}")

    # Compose all audio into one track
    if audio_clips:
        combined_audio = CompositeAudioClip(audio_clips)
        combined_audio = combined_audio.with_duration(total_video_duration)
        final_video = final_video.with_audio(combined_audio)
        logger.info(f"Audio track composed: {len(audio_clips)} clips")
    else:
        logger.warning("No audio clips available")

    # ─── Export ────────────────────────────────────────────────────────────
    logger.info(f"Exporting MP4: {output_path}")
    logger.info(f"Duration: {final_video.duration:.1f}s | Resolution: {config.REEL_WIDTH}x{config.REEL_HEIGHT} | FPS: {config.REEL_FPS}")

    final_video.write_videofile(
        str(output_path),
        fps=config.REEL_FPS,
        codec=config.EXPORT_CODEC,
        audio_codec=config.EXPORT_AUDIO_CODEC,
        bitrate=config.EXPORT_BITRATE,
        preset="medium",
        threads=4,
        logger="bar",
    )

    # Cleanup
    final_video.close()
    for clip in scene_clips:
        clip.close()

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"✅ Reel exported: {output_path} ({file_size_mb:.1f} MB)")

    return output_path


def _create_scene_clip(image_path: Path, duration: float) -> ImageClip:
    """
    Create a video clip from an image with subtle Ken Burns zoom effect.
    """
    clip = ImageClip(str(image_path), duration=duration)

    # Resize to reel dimensions
    clip = clip.resized((config.REEL_WIDTH, config.REEL_HEIGHT))

    # Ken Burns: start at 100%, slowly zoom to 110%
    # We scale up slightly and use resize over time
    def zoom_effect(get_frame, t):
        """Apply slow zoom from 1.0x to 1.08x over the clip duration."""
        import numpy as np
        from PIL import Image as PILImage

        frame = get_frame(t)
        h, w = frame.shape[:2]
        zoom = 1.0 + 0.08 * (t / duration)

        # Calculate crop for zoom
        new_w = int(w / zoom)
        new_h = int(h / zoom)
        x_start = (w - new_w) // 2
        y_start = (h - new_h) // 2

        cropped = frame[y_start:y_start + new_h, x_start:x_start + new_w]

        # Resize back to original dimensions
        img = PILImage.fromarray(cropped)
        img = img.resize((w, h), PILImage.Resampling.LANCZOS)

        return np.array(img)

    clip = clip.transform(zoom_effect)
    clip = clip.with_fps(config.REEL_FPS)

    return clip


def _create_text_overlay(text: str, duration: float) -> TextClip:
    """
    Create an animated text overlay with fade-in effect.
    """
    try:
        txt_clip = TextClip(
            text=text,
            font_size=config.OVERLAY_FONT_SIZE,
            color=config.OVERLAY_FONT_COLOR,
            font=config.OVERLAY_FONT,
            stroke_color=config.OVERLAY_STROKE_COLOR,
            stroke_width=config.OVERLAY_STROKE_WIDTH,
            text_align="center",
            size=(config.REEL_WIDTH - 100, None),  # Max width with padding
            method="caption",
        )
    except Exception:
        # Fallback if font not available
        txt_clip = TextClip(
            text=text,
            font_size=config.OVERLAY_FONT_SIZE,
            color=config.OVERLAY_FONT_COLOR,
            stroke_color=config.OVERLAY_STROKE_COLOR,
            stroke_width=config.OVERLAY_STROKE_WIDTH,
            text_align="center",
            size=(config.REEL_WIDTH - 100, None),
            method="caption",
        )

    # Position at lower third
    x_pos = "center"
    y_pos = int(config.REEL_HEIGHT * config.OVERLAY_POSITION[1])
    txt_clip = txt_clip.with_position((x_pos, y_pos))

    # Duration and fade-in
    txt_clip = txt_clip.with_duration(duration)
    txt_clip = txt_clip.with_effects([vfx.CrossFadeIn(0.8)])

    return txt_clip


def _create_black_frame():
    """Create a black frame as numpy array."""
    import numpy as np
    return np.zeros((config.REEL_HEIGHT, config.REEL_WIDTH, 3), dtype=np.uint8)


# ─── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format=config.LOG_FORMAT)
    logger.info("Assembly Engine loaded — ready for reel construction")
