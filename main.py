"""
ReelGenerator — Automated Reel Factory
========================================
Main orchestrator that runs the full pipeline:

  Topic → Script → Visuals → Voice → Music → Assembly → MP4

Usage (AI-generated script):
    python main.py "morning routine of a dreamer" --mood inspirational
    python main.py "city life at midnight" --mood nostalgic --style cinematic
    python main.py "self-growth journey" --auto-approve

Usage (Custom script from JSON):
    python main.py --script scripts/glimpzo_frustration.json --auto-approve
    python main.py --script scripts/glimpzo_early_creators.json -o glimpzo_reel

All modules are free / no-cost:
    - OpenRouter free LLM models (script)
    - Pollinations.ai (visuals — free, no key)
    - edge-tts (voiceover — free, no key)
    - Synthesized ambient pads (music — no key)
    - MoviePy + FFmpeg (assembly)
"""

import argparse
import json
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
    topic: str = "",
    style: str = "cinematic",
    mood: str = "inspirational",
    auto_approve: bool = False,
    output_filename: str = None,
    custom_script: dict = None,
) -> Path:
    """
    Execute the full reel generation pipeline.

    Args:
        topic: What the reel is about (ignored if custom_script provided)
        style: Visual style (ignored if custom_script provided)
        mood: Emotional tone (ignored if custom_script provided)
        auto_approve: Skip manual approval gate
        output_filename: Custom output filename (without extension)
        custom_script: Pre-written script dict (skips LLM generation)

    Returns:
        Path to the final MP4 file
    """
    gen_log = GenerationLog()
    pipeline_start = time.time()

    mode = "CUSTOM SCRIPT" if custom_script else "AI GENERATED"

    print("\n" + "▓" * 60)
    print("▓  🎬  REELGENERATOR — AUTOMATED REEL FACTORY")
    print("▓" * 60)
    print(f"▓  Mode:   {mode}")
    if custom_script:
        print(f"▓  Title:  {custom_script.get('title', 'Custom')}")
    else:
        print(f"▓  Topic:  {topic}")
        print(f"▓  Style:  {style}")
        print(f"▓  Mood:   {mood}")
    print(f"▓  Run ID: {gen_log.run_id}")
    print("▓" * 60 + "\n")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1: SCRIPT (Load custom or generate via AI)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    gen_log.start_step("script_generation")
    try:
        if custom_script:
            script = custom_script
            logger.info(f"Using custom script: '{script.get('title', 'Untitled')}'")
            gen_log.complete_step("script_generation", {
                "title": script.get("title"),
                "scenes": len(script.get("scenes", [])),
                "source": "custom_json",
            })
        else:
            script = generate_script(topic=topic, style=style, mood=mood)
            gen_log.complete_step("script_generation", {
                "title": script.get("title"),
                "scenes": len(script.get("scenes", [])),
                "model": config.LLM_MODEL,
                "source": "openrouter_llm",
            })

        gen_log.set_script(script)

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
Examples (AI-generated script):
  python main.py "morning routine of a dreamer" --mood inspirational
  python main.py "city life at midnight" --mood nostalgic --style cinematic
  python main.py "self-growth journey" --auto-approve

Examples (Custom script from JSON):
  python main.py --script scripts/glimpzo_frustration.json --auto-approve
  python main.py --script scripts/glimpzo_early_creators.json -o glimpzo_reel
        """
    )

    parser.add_argument(
        "topic",
        type=str,
        nargs="?",
        default="",
        help="What the reel is about (e.g., 'morning routine of a dreamer')"
    )
    parser.add_argument(
        "--script", "-S",
        type=str,
        default=None,
        help="Path to a custom script JSON file (skips AI script generation)"
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

    # Validate: must provide either topic or --script
    if not args.topic and not args.script:
        parser.error("Provide a topic OR use --script <file.json>")

    setup_logging()

    # Load custom script if provided
    custom_script = None
    if args.script:
        script_path = Path(args.script)
        if not script_path.exists():
            logger.error(f"Script file not found: {script_path}")
            sys.exit(1)
        with open(script_path, "r", encoding="utf-8") as f:
            custom_script = json.load(f)
        logger.info(f"Loaded custom script: {script_path}")

    try:
        result = run_pipeline(
            topic=args.topic,
            style=args.style,
            mood=args.mood,
            auto_approve=args.auto_approve,
            output_filename=args.output,
            custom_script=custom_script,
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
