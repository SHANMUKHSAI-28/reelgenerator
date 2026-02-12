"""
ReelGenerator — Automated Reel Factory
========================================
Main orchestrator that runs the full pipeline:

  Topic → Script → Visuals → Voice → Music → Assembly → MP4

Usage:
    python main.py "morning routine of a dreamer" --mood inspirational
    python main.py "city life at midnight" --mood nostalgic --style cinematic
    python main.py "self-growth journey" --auto-approve

All modules are free / no-cost:
    - OpenRouter free LLM models (script)
    - Pollinations.ai (visuals — free, no key)
    - edge-tts (voiceover — free, no key)
    - Synthesized ambient pads (music — no key)
    - MoviePy + FFmpeg (assembly)
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── Setup paths ──────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

import config
from modules.script_generator import generate_script
from modules.visual_generator import generate_scene_images
from modules.voice_generator import generate_narration
from modules.music_generator import generate_background_music
from modules.assembly_engine import assemble_reel
from modules.approval_gate import GenerationLog, request_approval, cleanup_temp_files


def setup_logging():
    """Configure logging for the pipeline."""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                config.LOGS_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                encoding="utf-8"
            ),
        ]
    )


logger = logging.getLogger("ReelFactory")


def run_pipeline(
    topic: str,
    style: str = "cinematic",
    mood: str = "inspirational",
    auto_approve: bool = False,
    output_filename: str = None,
) -> Path:
    """
    Execute the full reel generation pipeline.

    Args:
        topic: What the reel is about
        style: Visual style (cinematic, dreamy, documentary, anime)
        mood: Emotional tone (inspirational, nostalgic, calm, epic, melancholic)
        auto_approve: Skip manual approval gate
        output_filename: Custom output filename (without extension)

    Returns:
        Path to the final MP4 file
    """
    gen_log = GenerationLog()
    pipeline_start = time.time()

    print("\n" + "▓" * 60)
    print("▓  🎬  REELGENERATOR — AUTOMATED REEL FACTORY")
    print("▓" * 60)
    print(f"▓  Topic:  {topic}")
    print(f"▓  Style:  {style}")
    print(f"▓  Mood:   {mood}")
    print(f"▓  Run ID: {gen_log.run_id}")
    print("▓" * 60 + "\n")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1: SCRIPT GENERATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    gen_log.start_step("script_generation")
    try:
        script = generate_script(topic=topic, style=style, mood=mood)
        gen_log.set_script(script)
        gen_log.complete_step("script_generation", {
            "title": script.get("title"),
            "scenes": len(script.get("scenes", [])),
            "model": config.LLM_MODEL,
        })

        print(f"\n📄 Script: \"{script['title']}\"")
        print(f"   Emotion: {script.get('emotional_core', 'N/A')}")
        print(f"   Music tone: {script.get('audio_tone', 'N/A')}")
        for s in script["scenes"]:
            print(f"   Scene {s['scene_number']}: \"{s['text_overlay']}\" ({s['duration']}s)")
        print()

    except Exception as e:
        gen_log.fail_step("script_generation", str(e))
        gen_log.finalize("failed")
        logger.error(f"Pipeline failed at script generation: {e}")
        raise

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2: VISUAL GENERATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    gen_log.start_step("visual_generation")
    try:
        image_paths = generate_scene_images(script)
        gen_log.set_assets(images=image_paths)
        gen_log.complete_step("visual_generation", {
            "images_generated": len(image_paths),
        })
    except Exception as e:
        gen_log.fail_step("visual_generation", str(e))
        logger.warning(f"Visual generation had issues: {e}")
        image_paths = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 3: VOICE GENERATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    gen_log.start_step("voice_generation")
    try:
        narration_paths = generate_narration(script)
        gen_log.set_assets(narrations=narration_paths)
        gen_log.complete_step("voice_generation", {
            "narrations_generated": sum(1 for p in narration_paths if p),
            "voice": config.TTS_VOICE,
        })
    except Exception as e:
        gen_log.fail_step("voice_generation", str(e))
        logger.warning(f"Voice generation had issues: {e}")
        narration_paths = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 4: MUSIC GENERATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    gen_log.start_step("music_generation")
    try:
        music_path = generate_background_music(script)
        gen_log.set_assets(music=music_path)
        gen_log.complete_step("music_generation", {
            "music_file": str(music_path),
        })
    except Exception as e:
        gen_log.fail_step("music_generation", str(e))
        logger.warning(f"Music generation had issues: {e}")
        music_path = None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 5: ASSEMBLY
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    gen_log.start_step("assembly")
    try:
        if output_filename:
            output_path = config.OUTPUT_DIR / f"{output_filename}.mp4"
        else:
            output_path = None  # Let assembly engine generate name from title

        final_video = assemble_reel(
            script=script,
            image_paths=image_paths,
            narration_paths=narration_paths,
            music_path=music_path,
            output_path=output_path,
        )
        gen_log.set_assets(output_video=final_video)
        gen_log.complete_step("assembly", {
            "output_file": str(final_video),
            "file_size_mb": round(final_video.stat().st_size / (1024 * 1024), 2),
        })
    except Exception as e:
        gen_log.fail_step("assembly", str(e))
        gen_log.finalize("failed")
        logger.error(f"Pipeline failed at assembly: {e}")
        raise

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 6: APPROVAL GATE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    total_time = time.time() - pipeline_start
    logger.info(f"Pipeline completed in {total_time:.1f}s — entering approval gate")

    approved = request_approval(
        output_video=final_video,
        script=script,
        gen_log=gen_log,
        auto_approve=auto_approve,
    )

    if approved:
        print(f"\n🎬 Your reel is ready: {final_video}")
        print(f"⏱️  Total pipeline time: {total_time:.1f}s\n")
    else:
        print(f"\n🔄 Reel rejected. Adjust topic/mood and try again.\n")

    return final_video


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="🎬 ReelGenerator — Automated Reel Factory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "morning routine of a dreamer" --mood inspirational
  python main.py "city life at midnight" --mood nostalgic --style cinematic
  python main.py "self-growth journey" --auto-approve
  python main.py "ocean waves and peace" --mood calm --style dreamy
  python main.py "startup hustle" --mood epic --output my_reel
        """
    )

    parser.add_argument(
        "topic",
        type=str,
        help="What the reel is about (e.g., 'morning routine of a dreamer')"
    )
    parser.add_argument(
        "--style", "-s",
        type=str,
        default="cinematic",
        choices=["cinematic", "dreamy", "documentary", "anime", "minimal", "neon"],
        help="Visual style (default: cinematic)"
    )
    parser.add_argument(
        "--mood", "-m",
        type=str,
        default="inspirational",
        choices=["inspirational", "nostalgic", "calm", "epic", "melancholic", "dreamy", "energetic"],
        help="Emotional mood (default: inspirational)"
    )
    parser.add_argument(
        "--auto-approve", "-a",
        action="store_true",
        help="Skip manual approval gate"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Custom output filename (without .mp4 extension)"
    )

    args = parser.parse_args()

    setup_logging()

    try:
        result = run_pipeline(
            topic=args.topic,
            style=args.style,
            mood=args.mood,
            auto_approve=args.auto_approve,
            output_filename=args.output,
        )
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n⏹️  Pipeline cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
