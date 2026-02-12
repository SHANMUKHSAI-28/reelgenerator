"""
Module 2 — Visual Generator
============================
Generates cinematic AI images for each scene using Pollinations.ai (100% free, no API key).

Features:
- AI image generation via Pollinations.ai (Flux model)
- Post-processing pipeline: sharpening, contrast, color boost, vignette
- Falls back to gradient placeholder images if generation fails
- Each image is 1080x1920 (vertical 9:16 for reels)
"""

import logging
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps

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
            # Apply cinematic post-processing
            _post_process_image(image_path)
            logger.info(f"Scene {scene_num} visual saved + enhanced: {image_path}")
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
    Uses the Flux model with enhanced prompting for cinematic quality.
    """
    # Enhanced quality prompt — specific, structured for Flux
    enhanced_prompt = (
        f"((masterpiece)), ((best quality)), ((ultra-detailed)), "
        f"{prompt}, "
        f"cinematic lighting, volumetric light, ray tracing, "
        f"sharp focus, depth of field, bokeh, "
        f"photorealistic, 8K UHD, DSLR quality, "
        f"vertical portrait composition 9:16 aspect ratio, "
        f"color graded, film grain, professional photography"
    )

    encoded_prompt = urllib.parse.quote(enhanced_prompt)
    unique_seed = int(time.time() * 1000) + scene_num * 137
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={config.POLLINATIONS_WIDTH}"
        f"&height={config.POLLINATIONS_HEIGHT}"
        f"&seed={unique_seed}"
        f"&nologo=true"
        f"&enhance=true"
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

    # Resize to exact reel dimensions with high-quality resampling
    with Image.open(save_path) as img:
        if img.size != (config.REEL_WIDTH, config.REEL_HEIGHT):
            # Use LANCZOS for highest quality downscale
            img = img.resize(
                (config.REEL_WIDTH, config.REEL_HEIGHT),
                Image.Resampling.LANCZOS
            )
        # Save as high-quality PNG
        img.save(save_path, "PNG", optimize=True)

    return save_path


def _post_process_image(image_path: Path) -> None:
    """
    Apply cinematic post-processing to enhance image quality.

    Pipeline:
    1. Sharpening — recover detail lost in compression
    2. Contrast boost — cinematic punch
    3. Color saturation — vivid but not overdone
    4. Slight vignette — draws focus to center
    """
    with Image.open(image_path) as img:
        # 1. Sharpening (mild — enhance detail without artifacts)
        sharpener = ImageEnhance.Sharpness(img)
        img = sharpener.enhance(1.3)

        # 2. Contrast boost (subtle cinematic pop)
        contrast = ImageEnhance.Contrast(img)
        img = contrast.enhance(1.15)

        # 3. Color saturation (slightly richer colors)
        color = ImageEnhance.Color(img)
        img = color.enhance(1.12)

        # 4. Brightness — slight lift to avoid muddy darks
        brightness = ImageEnhance.Brightness(img)
        img = brightness.enhance(1.03)

        # 5. Vignette effect — darkens edges, focuses center
        img = _apply_vignette(img, intensity=0.35)

        img.save(image_path, "PNG", optimize=True)

    logger.debug(f"Post-processing applied: {image_path.name}")


def _apply_vignette(img: Image.Image, intensity: float = 0.3) -> Image.Image:
    """Apply a subtle vignette (darkened edges) for cinematic feel."""
    import numpy as np

    w, h = img.size
    arr = np.array(img, dtype=np.float32)

    # Create radial gradient mask
    Y, X = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    # Normalized distance from center (0 at center, 1 at corners)
    dist = np.sqrt((X - cx) ** 2 / (cx ** 2) + (Y - cy) ** 2 / (cy ** 2))
    # Vignette: darken beyond 60% radius
    vignette = np.clip(1.0 - intensity * np.maximum(dist - 0.6, 0) / 0.8, 0, 1)
    vignette = vignette[:, :, np.newaxis]  # broadcast to RGB

    result = (arr * vignette).astype(np.uint8)
    return Image.fromarray(result)


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
