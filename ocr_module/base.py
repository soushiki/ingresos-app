"""Contrato común de todos los motores de OCR."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict


@dataclass
class OCRResult:
    """Resultado de digitalizar UNA imagen. Es lo único que el módulo 2 necesita leer."""
    source: str                 # ruta o nombre de la imagen
    text: str = ""              # texto plano digitalizado (sin interpretar)
    ok: bool = True
    error: str = ""
    engine: str = ""
    model: str = ""
    seconds: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class OCREngine(ABC):
    """Para añadir otro motor (Azure, Mistral, local...) basta con heredar y implementar read()."""
    name = "base"
    model = ""

    @abstractmethod
    def read(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        """Recibe la imagen ya preparada y devuelve el texto plano. Lanza excepción si falla."""
