# Módulo 1 · Imagen → texto plano digitalizado

Convierte cualquier foto de planilla (manuscrita o impresa, girada, oscura, grande o pequeña) en **texto plano fiel**.
No interpreta ni clasifica campos: eso es el módulo 2 (parser a las 12 columnas).

## Motores disponibles
| Motor | Costo | Letra manuscrita | Requisitos |
|---|---|---|---|
| `local` (por defecto) | Gratis, offline | Buena (depende del modelo) | Ollama + un modelo de visión |
| `tesseract` | Gratis | Floja (solo impreso) | Tesseract instalado |
| `gemini` | API de Google | Muy buena | Clave de API |

## Instalación (motor local)
```bash
# 1) Instala Ollama: https://ollama.com  y descarga un modelo de visión
ollama pull qwen2.5vl:7b        # ~6 GB; usa qwen2.5vl:3b si tu equipo es modesto, o qwen3-vl:8b
# 2) Dependencias de Python
pip install -r requirements.txt
cp .env.example .env
```
Con GPU de 8 GB o más va rápido; solo con CPU funciona, pero tarda minutos por foto.

## Probar con UNA imagen (recomendado antes de todo)
```bash
python probar_imagen.py foto.jpg                    # desde la carpeta que contiene ocr_module/
python probar_imagen.py foto.jpg --model qwen3-vl:8b
```
Muestra el texto leído, qué campos reconoce y un veredicto; abre un informe HTML con la foto al lado del texto.

## Uso
Desde la carpeta que contiene `ocr_module/`:
```bash
python -m ocr_module.cli fotos/ -o salida/                 # motor local
python -m ocr_module.cli fotos/ --model qwen3-vl:8b        # otro modelo
python -m ocr_module.cli fotos/ --engine tesseract         # sin IA, solo impreso
```
Genera un `.txt` por imagen y `resultados.jsonl` (source, text, ok, error, engine, model, seconds).

Desde Python (o desde Flask):
```python
from ocr_module import digitize, get_engine
r = digitize("planilla.jpg", get_engine("local"))
print(r.ok, r.text)
```

## Qué hace antes de enviar la imagen
Corrige rotación EXIF, quita transparencias, sube el contraste (papel gris / poca luz),
reduce fotos enormes (máx. 2600 px) y amplía las muy pequeñas (mín. 1200 px). Acepta JPG, PNG, WEBP, BMP, TIFF, GIF y HEIC (con `pillow-heif`).

## Contrato de salida
Un renglón de la imagen = una línea. Tablas: celdas separadas por ` | `. Números copiados tal cual
(`1.250.000`, `120k`). `[ilegible]`, `[?]` para dudas, `~~tachado~~`, `[SIN TEXTO]` si está vacía.

## Cambiar de motor
Crea una clase que herede de `OCREngine` (`base.py`), implementa `read(bytes, mime) -> str`
y regístrala en `get_engine()` (`__init__.py`). El resto del sistema no cambia.

## Otros servidores locales
`LOCAL_VLM_URL` acepta cualquier servidor compatible con OpenAI: LM Studio (`http://localhost:1234/v1`), vLLM, etc.
