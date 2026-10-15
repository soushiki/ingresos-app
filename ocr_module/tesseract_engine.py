"""Motor clásico Tesseract: rápido, sin GPU, sin IA. Bueno con texto IMPRESO; flojo con letra manuscrita."""
from __future__ import annotations
import io, os
from PIL import Image
from .base import OCREngine


class TesseractEngine(OCREngine):
    name = "tesseract"
    model = "tesseract"
    prep = {"max_side": 3200, "min_side": 2200, "enhance": False}   # con tus recibos: más tamaño y sin autocontraste leyó todas las cifras

    def __init__(self, lang: str | None = None, psm: int = 6):
        import pytesseract
        self._pt = pytesseract
        self.lang = lang or os.getenv("TESSERACT_LANG", "spa+eng")
        self.psm = psm
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("Tesseract no está instalado (Windows: winget install UB-Mannheim.TesseractOCR · "
                               "Linux: apt install tesseract-ocr tesseract-ocr-spa · Mac: brew install tesseract tesseract-lang)") from e

    def read(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        text = self._pt.image_to_string(img, lang=self.lang, config=f"--psm {self.psm}").strip()
        return text or "[SIN TEXTO]"
