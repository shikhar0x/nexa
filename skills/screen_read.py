"""Phase 4b: read and understand what's on the user's screen.

Two local backends, auto-detected at call time — neither is a hard dependency:

  1. OCR fast path: tesseract via pytesseract (~1-3s text extraction).
     Preferred whenever present: fast, and phi4-mini grounds answers in the
     extracted text like any other tool result.
  2. Vision Q&A: a local vision model served by Ollama
     (settings.vision_model, default "llava-phi3"). Slower on CPU (tens of
     seconds) but understands non-textual content and answers visual
     questions. Used when OCR is missing or finds no readable text.

The capture itself reuses the proven Wayland-safe screenshot chain, written
to a temp file that is deleted immediately after reading — nothing is stored.
"""
import os
import shutil
import tempfile
from typing import Any

import ollama

from skills.base import BaseSkill, SkillResult, Capability
from config.logger import logger
from config.settings import settings
from skills.screenshot import capture_screen_image


def ocr_available() -> bool:
    """True only when both the tesseract binary and pytesseract are present."""
    if not shutil.which("tesseract"):
        return False
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return True


def extract_text(image_path: str) -> str:
    """Run OCR over a captured screen image and return the raw text."""
    import pytesseract
    text = pytesseract.image_to_string(image_path)
    return (text or "").strip()


def vision_available() -> bool:
    """True when the configured vision model is served by the local Ollama."""
    try:
        base = settings.vision_model.split(":")[0]
        return any(m.model.split(":")[0] == base for m in ollama.list().models)
    except Exception as e:
        logger.debug(f"Vision-model availability check failed: {e}")
        return False


def _prepare_image_for_vision(image_path: str, max_edge: int = 1280) -> str:
    """Normalize a raw capture for the vision model.

    Full-resolution portal captures (multi-megapixel RGBA PNGs) can make
    small local vision models degenerate — observed live: moondream answered
    the garbage token "urn:1.0.0.0" to a hi-res portal PNG. Downscaling to a
    sane edge and converting to RGB JPEG makes the input reliably digestible
    and is significantly faster on CPU. Returns the path to send; falls back
    to the original path if normalization is not possible.
    """
    try:
        from PIL import Image
    except ImportError:
        return image_path
    try:
        with Image.open(image_path) as img:
            w, h = img.size
            if max(w, h) <= max_edge and img.mode == "RGB":
                return image_path
            img = img.convert("RGB")
            img.thumbnail((max_edge, max_edge), Image.LANCZOS)
            out = os.path.join(os.path.dirname(image_path), "vision-input.jpg")
            img.save(out, format="JPEG", quality=88)
            return out
    except Exception as e:
        logger.warning(f"Vision image normalization failed, sending original: {e}")
        return image_path


def describe_screen(image_path: str, question: str = "") -> str:
    """Ask the local vision model about the captured screen image."""
    prompt = (
        question.strip()
        or "Describe what is on this screen in two or three sentences, quoting any important text."
    )
    response = ollama.chat(
        model=settings.vision_model,
        messages=[{"role": "user", "content": prompt, "images": [_prepare_image_for_vision(image_path)]}],
        stream=False,
    )
    return (response.get("message", {}).get("content") or "").strip()


class ScreenReadSkill(BaseSkill):
    """Reads/describes the current screen (OCR fast path + vision fallback)."""

    name = "SCREEN_READ"
    description = "Reads the user's screen with local OCR or a local vision model."
    permissions = []  # read-only; capture is transient and deleted after reading
    capability = Capability(
        name="screen_read",
        description="Reads text from the user's screen or describes what is on it",
        supports=[
            "what's on my screen",
            "read my screen",
            "what error is on my screen",
        ],
        requires_confirmation=False,
        deterministic=False,
    )

    def execute(self, args: dict[str, Any], context: Any) -> SkillResult:
        query = (args.get("query") or "").strip()
        tmpdir = tempfile.mkdtemp(prefix="nexa-screen-")
        png_path = os.path.join(tmpdir, "screen.png")
        try:
            ok, err = capture_screen_image(png_path)
            if not ok:
                return SkillResult(
                    success=False,
                    message=f"I couldn't capture your screen: {err}",
                    data={"error": err},
                    use_llm=False,
                )

            if ocr_available():
                try:
                    text = extract_text(png_path)
                except Exception as e:
                    logger.warning(f"OCR failed: {e}")
                    text = ""
                if text:
                    excerpt = text if len(text) <= 4000 else text[:4000] + "\n… [truncated]"
                    return SkillResult(
                        success=True,
                        data={
                            "Extracted screen text": excerpt,
                            "Screen reader backend": "local OCR (tesseract)",
                            "Reading the data": (
                                "the text above is raw OCR — silently ignore small "
                                "recognition glitches and answer the user's question from it"
                            ),
                        },
                        message="Text read from the user's screen (local OCR).",
                        use_llm=True,
                        allow_interpretation=True,
                    )
                # Nothing readable on screen — vision (if present) can still describe it.
                if vision_available():
                    description = describe_screen(png_path, query)
                    if description:
                        return SkillResult(
                            success=True,
                            message=f"I found no clearly readable text on the screen; the vision model sees: {description}",
                            data={"Screen description": description, "backend": "vision"},
                            use_llm=False,
                        )
                return SkillResult(
                    success=True,
                    message="I captured your screen but couldn't find any readable text on it.",
                    data={"Extracted screen text": "", "backend": "ocr"},
                    use_llm=False,
                )

            if vision_available():
                try:
                    description = describe_screen(png_path, query)
                except Exception as e:
                    logger.warning(f"Vision model failed: {e}")
                    description = ""
                if description:
                    return SkillResult(
                        success=True,
                        message=description,
                        data={"Screen description": description, "backend": "vision"},
                        use_llm=False,
                    )
                return SkillResult(
                    success=False,
                    message="The vision model returned nothing useful from your screen.",
                    data={"error": "vision_empty", "backend": "vision"},
                    use_llm=False,
                )

            return SkillResult(
                success=False,
                message=(
                    "I captured your screen but have nothing to read it with yet. "
                    "Fast text OCR:\n  sudo apt install -y tesseract-ocr\n  venv/bin/pip install pytesseract\n"
                    f"Deeper visual understanding (optional):\n  ollama pull {settings.vision_model}"
                ),
                data={"error": "no_reader_backend"},
                use_llm=False,
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
