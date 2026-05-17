"""
OCR Tool
--------
Used by the Analyst agent to extract text from company images, banners,
and screenshots. Powered by Tesseract via pytesseract.

Requirements: Tesseract must be installed on the host machine.
  macOS:   brew install tesseract
  Ubuntu:  sudo apt install tesseract-ocr
  Windows: https://github.com/UB-Mannheim/tesseract/wiki
           Add C:\Program Files\Tesseract-OCR to system PATH

CrewAI 1.x note: _run() accepts a single string argument (the image URL or path).
"""

import os
import httpx
import pytesseract
from PIL import Image
from io import BytesIO
from pathlib import Path
from crewai.tools import BaseTool
from loguru import logger

# Windows: set TESSERACT_PATH in .env if tesseract is not on system PATH
_tess_path = os.getenv("TESSERACT_PATH")
if _tess_path:
    pytesseract.pytesseract.tesseract_cmd = _tess_path


class OCRTool(BaseTool):
    name: str = "OCR Extractor"
    description: str = (
        "Extracts visible text from an image URL or local file path. "
        "Use this to read company banners, LinkedIn profile headers, "
        "or any image that contains text relevant to the lead. "
        "Input: an image URL (https://...) or absolute file path. "
        "Output: extracted text string."
    )

    def _run(self, image_source: str) -> str:
        if not image_source or not image_source.strip():
            return "No image source provided."

        logger.info(f"Analyst → running OCR on: {image_source}")

        try:
            image = self._load_image(image_source.strip())
            text  = pytesseract.image_to_string(image).strip()

            if not text:
                return "OCR completed but no text was detected in the image."

            logger.success(f"OCR extracted {len(text)} characters")
            return text

        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return f"OCR error: {str(e)}"

    def _load_image(self, source: str) -> Image.Image:
        if source.startswith("http://") or source.startswith("https://"):
            response = httpx.get(source, timeout=15, follow_redirects=True)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGB")
        else:
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"Image not found: {source}")
            return Image.open(path).convert("RGB")
