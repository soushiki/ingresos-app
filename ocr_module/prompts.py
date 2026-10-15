"""Instrucciones de transcripción y limpieza compartidas por todos los motores con IA."""
import re

SYSTEM = (
    "Eres un motor de OCR de alta precisión especializado en planillas manuscritas en español "
    "de negocios colombianos (cierres de caja, ventas diarias). Tu única tarea es TRANSCRIBIR "
    "fielmente lo que está escrito en la imagen. No resumas, no interpretes, no corrijas, no "
    "calcules y no agregues comentarios."
)

PROMPT = """Transcribe TODO el texto visible en la imagen a texto plano.

Reglas:
1. Respeta el orden de lectura y las líneas tal como se ven (arriba→abajo, izquierda→derecha). Un renglón de la imagen = una línea de texto.
2. Si hay tablas o columnas, escribe cada fila en una línea separando las celdas con " | ".
3. Si una etiqueta y su número están en la misma línea o uno junto al otro, déjalos juntos (ej.: "Propinas: 45.000").
4. Copia los números EXACTAMENTE como están escritos (con sus puntos, comas, $, "k", "mil" o palabras). No los conviertas ni los sumes.
5. Texto ilegible: [ilegible]. Lectura dudosa: escribe tu mejor lectura seguida de [?].
6. Texto tachado: ~~texto~~ y, si hay corrección al lado, transcríbela también.
7. Incluye fechas, nombres, sellos, membretes, notas al margen y textos impresos.
8. Ignora la orientación: si la imagen está girada o inclinada, léela igualmente.
9. Transcribe literalmente, incluso con errores de ortografía: no corrijas ni completes palabras.
10. Devuelve SOLO la transcripción, sin encabezados, sin comillas de código, sin razonamientos y sin explicaciones.
11. Si no hay ningún texto, responde exactamente: [SIN TEXTO]
12. Si la foto trae VARIOS papeles o recibos distintos (por ejemplo, varios papelitos sobre una mesa), transcribe cada uno completo y por separado, de arriba hacia abajo y de izquierda a derecha, y escribe una línea con exactamente === DOCUMENTO === antes de cada uno (también las notas a mano sobre un papel). Si es un solo papel, no escribas esa línea."""


def clean_text(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)   # modelos que "piensan en voz alta"
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()
