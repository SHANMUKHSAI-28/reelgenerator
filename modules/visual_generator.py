"""
Module 2 — Visual Generator
============================
Generates cinematic AI images for each scene using Pollinations.ai (100% free, no API key).

Falls back to gradient placeholder images if generation fails.
Each image is 1080x1920 (vertical 9:16 for reels).
"""

import logging
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import config

logger = logging.getLogger("VisualGenerator")


def generate_scene_images(script: dict, output_dir: Optional[Path] = None) -> list[Path]:
    """
    Generate one image per scene from the script's visual prompts.

    Args:
        script: The structured script dict from ScriptGenerator
        output_dir: Directory to save images (defaults to config.TEMP_DIR)

    Returns:
        List of file paths to generated images
    """
    output_dir = output_dir or config.TEMP_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    image_paths = []

    for scene in script["scenes"]:
        scene_num = scene["scene_number"]
        prompt = scene["visual_prompt"]
        logger.info(f"Generating visual for Scene {scene_num}...")

        image_path = output_dir / f"scene_{scene_num:02d}.png"

        try:
            image_path = _generate_pollinations_image(prompt, image_path, scene_num)
            logger.info(f"Scene {scene_num} visual saved: {image_path}")
        except Exception as e:
            logger.warning(f"Scene {scene_num} Pollinations failed ({e}), using gradient placeholder")
            image_path = _generate_placeholder(
                image_path, scene_num, scene.get("text_overlay", "")
            )

        image_paths.append(image_path)

    logger.info(f"Generated {len(image_paths)} scene visuals")
    return image_paths


def _generate_pollinations_image(prompt: str, save_path: Path, scene_num: int) -> Path:
    """
    Generate an image via Pollinations.ai free API.

    The API works by encoding the prompt in the URL — no key needed.
    """
    # Enhance the prompt for better quality
    enhanced_prompt = (
        f"{prompt}, ultra high quality, 8K, cinematic lighting, "
        f"photorealistic, vertical composition 9:16, stunning detail, "
        f"professional photography, dramatic atmosphere"
    )

    encoded_prompt = urllib.parse.quote(enhanced_prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={config.POLLINATIONS_WIDTH}"
        f"&height={config.POLLINATIONS_HEIGHT}"
        f"&seed={int(time.time()) + scene_num}"
        f"&nologo=true"
        f"&model=flux"
    )

    logger.debug(f"Pollinations URL length: {len(url)} chars")

    response = requests.get(url, timeout=config.IMAGE_GENERATION_TIMEOUT, stream=True)
    response.raise_for_status()

    # Verify we got an image
    content_type = response.headers.get("content-type", "")
    if "image" not in content_type and len(response.content) < 10000:
        raise ValueError(f"Response doesn't look like an image: {content_type}")

    save_path.write_bytes(response.content)

    # Verify and resize if needed
    with Image.open(save_path) as img:
        if img.size != (config.REEL_WIDTH, config.REEL_HEIGHT):
            img = img.resize(
                (config.REEL_WIDTH, config.REEL_HEIGHT),
                Image.Resampling.LANCZOS
            )
            img.save(save_path, "PNG", quality=95)

    return save_path


def _generate_placeholder(save_path: Path, scene_num: int, text: str) -> Path:
    """
    Generate a beautiful gradient placeholder image with text.
    Used as fallback when AI image generation fails.
    """
    w, h = config.REEL_WIDTH, config.REEL_HEIGHT

    # Create gradient based on scene number for visual variety
    gradients = [
        [(20, 20, 60), (80, 40, 120)],     # Deep blue to purple
        [(60, 20, 40), (140, 60, 80)],      # Dark rose to warm red
        [(10, 40, 50), (30, 100, 120)],     # Deep teal to ocean
        [(40, 30, 20), (120, 80, 40)],      # Dark brown to amber
        [(20, 30, 50), (60, 80, 140)],      # Navy to steel blue
    ]
    color_pair = gradients[scene_num % len(gradients)]

    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)

    # Draw vertical gradient
    for y in range(h):
        ratio = y / h
        r = int(color_pair[0][0] + (color_pair[1][0] - color_pair[0][0]) * ratio)
        g = int(color_pair[0][1] + (color_pair[1][1] - color_pair[0][1]) * ratio)
        b = int(color_pair[0][2] + (color_pair[1][2] - color_pair[0][2]) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Add subtle noise / grain for cinematic feel
    img = img.filter(ImageFilter.GaussianBlur(radius=2))

    # Add scene number and text
    try:
        font_large = ImageFont.truetype("arial.ttf", 72)
        font_small = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Scene number
    scene_text = f"SCENE {scene_num}"
    bbox = draw.textbbox((0, 0), scene_text, font=font_large)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((w - tw) // 2, h // 2 - 60),
        scene_text,
        fill=(255, 255, 255, 200),
        font=font_large
    )

    # Overlay text
    if text:
        bbox2 = draw.textbbox((0, 0), text, font=font_small)
        tw2 = bbox2[2] - bbox2[0]
        draw.text(
            ((w - tw2) // 2, h // 2 + 40),
            text,
            fill=(200, 200, 200),
            font=font_small
        )

    img.save(save_path, "PNG")
    return save_path


# ─── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format=config.LOG_FORMAT)

    test_script = {
        "scenes": [
            {
                "scene_number": 1,
                "visual_prompt": "Cinematic wide shot of misty mountains at sunrise, golden light breaking through clouds, serene lake reflection, 9:16 vertical",
                "text_overlay": "Find your peace",
                "narration": "In the silence of the mountains...",
                "duration": 4.0
            }
        ]
    }

    paths = generate_scene_images(test_script)
    print(f"Generated: {paths}")
