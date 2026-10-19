# Libro contable y documento soporte · instalación en el PC del contador

Esta app corre **solo en tu computador** (nada sale a internet). En tu PC **no lee fotos**: las fotos se leen en el PC del
negocio, que te manda cada semana un archivo de **datos crudos** (`ingresos_crudo_….json`). Tú lo importas, revisas el libro
y preparas los **documentos soporte**. La app no firma ni transmite a la DIAN: eso lo haces en la solución gratuita de la DIAN.

Tiempo de la instalación: unos 20 minutos, una sola vez.

## 1. Instalar Python (una vez, ≈ 5 min)
1. Entra a https://www.python.org/downloads/ y descarga la versión más reciente para Windows (3.12 o más nueva).
2. Abre el instalador y, **antes** de «Install Now», marca la casilla **«Add python.exe to PATH»**. Luego «Install Now».
3. Para comprobarlo: abre el menú Inicio, escribe `cmd`, abre «Símbolo del sistema» y escribe:
   ```
   python --version
   ```
   Debe responder `Python 3.12…` o más. Si dice que «no se reconoce», repite el paso 2 (opción «Modify» → marca «Add to PATH»).

## 2. Copiar la app (una vez, ≈ 2 min)
1. El negocio te pasa la carpeta de la app en un `.zip`. Descomprímela en `C:\ingresos_app`.
2. Debe **no** traer la carpeta `datos` del otro PC. Si la trae, pide otra copia sin ella: en tu PC la carpeta `datos` guarda
   la numeración de los documentos soporte (CTG) y solo debe existir aquí.

## 3. Instalar lo que la app necesita (una vez, ≈ 5–10 min, necesita internet)
En el «Símbolo del sistema», escribe estas tres líneas, una por una, y espera a que cada una termine:
```
cd /d C:\ingresos_app
python -m pip install -r requirements.txt
echo SIN_OCR=1> .env
```
La última crea el archivo `.env` que le dice a la app que en este PC no se leen fotos.

## 4. Abrir la app (cada vez)
1. Doble clic en **`iniciar.bat`** (dentro de `C:\ingresos_app`). Se abre una ventana negra y, a los segundos, el navegador
   en http://127.0.0.1:5050.
2. **No cierres la ventana negra** mientras trabajas: es la app. Para salir, ciérrala.
3. Si el navegador no se abre solo, escribe http://127.0.0.1:5050 en la barra de direcciones.

## 5. El trabajo de cada semana
1. **Importar.** En ① pulsa **⬆ Importar datos** (o en ② Libro contable, **⬆ Importar datos crudos**) y elige el `.json` que te
   mandaron. La app dice qué días entraron (*nuevos*), cuáles ya tenías (*iguales*) y cuáles cambiaron (*conflictos*: tú eliges si
   se reemplazan). Un día con compras de un documento ya transmitido no se cambia (*bloqueado*).
2. **Revisar** en ② Libro contable los días y bajar el **Excel** del rango si lo necesitas.
3. **Documento soporte** (pestaña ③): ves las compras a proveedores no obligados a facturar, agrupadas por proveedor y semana,
   con su fecha límite.
   - La primera vez, **Registrar proveedor** (tipo y número de documento, DV, dirección, municipio). Se guarda para siempre.
   - **Generar documento soporte**: la app le da el número siguiente (CTG-1, CTG-2…).
   - Baja el **Excel** y transcribe cada documento en la solución gratuita de la DIAN.
   - Cuando la DIAN lo acepte, márcalo **Transmitido** (puedes pegar el CUDS). Desde ahí ya no se puede cambiar; si hay un error,
     se corrige con una **Nota de ajuste**.

## 6. Copia de seguridad (cada semana, 1 min)
Copia la carpeta **`C:\ingresos_app\datos`** a una memoria USB o a tu nube. El archivo `datos\soporte.db` lleva la numeración
CTG y tus proveedores: si se pierde, la app no sabe qué números ya usaste.

## 7. Fotos de los recibos (para quien las toma; ≈ 1 min por foto)
La app lee mejor cuanto más grande y nítida llega la foto. Esto vale para las fotos nuevas: las de septiembre ya están en
≈ 1600 px y no hay originales.
1. **Enviar sin comprimir.** Por WhatsApp, mándala como **documento** (📎 → Documento), no como foto; o activa la calidad **HD**.
2. **CamScanner:** exporta en calidad **alta u original**, nunca «pequeña» ni «media».
3. **Nombre del archivo:** con los números completos de los recibos (p. ej. `85297 al 85302`), no acortados como `3341`.
4. Lo que la app no pueda leer con seguridad queda **dudoso** en la pestaña **④ Revisión** con su recorte; un recibo del nombre
   que no encontró aparece como **«Falta 85388»** con la foto entera para anotarlo a mano.

### Cómo tomar la foto (consejos, no obligatorios)
- **Fondo oscuro y liso** (tela o cartulina negra, sin vetas ni dibujos): el papel blanco se separa mejor del fondo.
- **Una sola columna** de recibos, uno debajo del otro, sin encimarse ni tocarse.
- **Cerca:** que los recibos llenen casi toda la foto; mejor dos fotos que una lejana.
- **Sin cortar el pie:** que se vea el canto de abajo del último recibo, con un poco de fondo alrededor.
- De frente y derecha, con luz pareja, sin flash ni sombra de la mano.

## Si algo falla
| Lo que ves | Qué hacer |
|---|---|
| `python` no se reconoce | Paso 1.2: falta «Add python.exe to PATH». |
| La ventana negra se cierra sola | Abre `cmd`, escribe `cd /d C:\ingresos_app` y luego `python app.py`: el mensaje de error queda a la vista; mándalo al negocio. |
| «Address already in use» o el puerto 5050 ocupado | Ya hay otra ventana de la app abierta; ciérrala. O añade la línea `PORT=5051` al archivo `.env` y abre http://127.0.0.1:5051. |
| En ① aparece «▶ Leer pendientes» en vez de «⬆ Importar datos» | Falta el archivo `.env` con `SIN_OCR=1` (paso 3). |
| «La huella sha256 no coincide» o «El archivo no es un .json válido» | El `.json` se dañó o se editó. Pide que lo exporten de nuevo; no lo abras ni lo cambies. |

Opcional: en `datos\contable.json` se configuran el nombre y NIT del negocio, los festivos y el plazo de los documentos
(`regla_plazo`: `misma_semana` o `semana_siguiente`). Si no existe, la app usa los valores por defecto.
