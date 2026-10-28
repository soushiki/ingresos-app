// T5 · Worker módulo del modo contador web (03 §3, ADR-028): Pyodide + wheels + nucleo.zip solo desde rutas propias,
// y `libro.generar` con código fijo: los archivos entran como objetos de Pyodide, nunca como texto de `runPython` (S2).
// Entra {tipo:"generar", crudo, extracto?, memoria?, negocio, nit}; sale {tipo:"avance", paso} | {tipo:"listo", ...} | {tipo:"error", mensaje, detalle}.
// `crearMotor` se exporta para que web/pruebas/contrato.mjs lo corra en Node con los mismos archivos de web/dist/.

const MB = 2 ** 20;
// S2: los mismos topes de libro.generar, antes de copiar nada a Python.
const TOPES = { crudo: [20 * MB, "El crudo pesa más de 20 MB"], extracto: [5 * MB, "El extracto pesa más de 5 MB"],
                memoria: [1 * MB, "La memoria del extracto pesa más de 1 MB"] };
// Un crudo real llega a 7 niveles (ADR-004: MAX_HONDO 6 por documento). En Pyodide un JSON muy hondo desborda la pila de JS
// dentro de json.loads (error fatal, mata el motor) antes de llegar al RecursionError que atrapa la app: se corta aquí.
const MAX_HONDO_JSON = 64;
const VERSION = /^\d+\.\d+\.\d+$/;
const WHEEL = /^[A-Za-z0-9_.]+-[A-Za-z0-9_.]+-py[23](\.py3)?-none-any\.whl$/;

// Texto fijo: define el puente una sola vez. Lo de afuera llega por argumentos (JsProxy de Uint8Array → bytes).
const PUENTE = `
import re, sys
sys.path.insert(0, "/nucleo")
from parser_module.contable import libro

def _bytes(x):
    return None if x is None else x.to_bytes()

def _sin_rutas(t):
    return re.sub(r"/[^\\s'\\"]*\\.py", "…", t[:2000])[:500]

def puente(crudo, extracto, memoria, negocio, nit, ahora):
    try:
        r = libro.generar(_bytes(crudo), _bytes(extracto), _bytes(memoria), negocio, nit, ahora)
    except libro.EntradaInvalida as e:
        return {"error": str(e), "detalle": ""}
    except Exception as e:
        return {"error": "El motor falló con este archivo", "detalle": _sin_rutas(f"{type(e).__name__}: {e}")}
    return r
puente
`;

const leerFetch = async (url) => {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status} en ${new URL(url).pathname}`);
  return new Uint8Array(await r.arrayBuffer());
};

// «2026-10-26T09:30:00» en hora local (Colombia), como `libro._ahora` en la app.
function ahoraLocal(d = new Date()) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

// S4: el detalle plegado no lleva rutas del PC ni direcciones.
function sinRutas(t) {
  return String(t).replace(/[a-z][a-z0-9+.-]*:\/\/[^\s'")]+/gi, "…").replace(/[A-Za-z]:\\[^\s'")]+/g, "…").slice(0, 500);
}

async function sha256(bytes) {
  const h = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  return Array.from(h, (b) => b.toString(16).padStart(2, "0")).join("");
}

class ErrorMotor extends Error {
  constructor(mensaje, detalle = "") { super(mensaje); this.detalle = detalle; }
}

function bytesDe(v, campo) {
  if (v === undefined || v === null) return undefined;
  const b = v instanceof ArrayBuffer ? new Uint8Array(v) : ArrayBuffer.isView(v) ? new Uint8Array(v.buffer, v.byteOffset, v.byteLength) : null;
  if (!b) throw new ErrorMotor(`El ${campo} no llegó como archivo`);
  const [tope, msg] = TOPES[campo];
  if (b.byteLength > tope) throw new ErrorMotor(msg);
  return b.byteLength ? b : undefined;
}

// Cuenta [ y { fuera de cadenas, sobre los bytes UTF-8 (un byte de un carácter multibyte nunca vale « " », « \ » ni corchete).
function hondoJson(b) {
  let n = 0, max = 0, cadena = false;
  for (let i = 0; i < b.length; i++) {
    const c = b[i];
    if (cadena) { if (c === 0x5c) i++; else if (c === 0x22) cadena = false; }
    else if (c === 0x22) cadena = true;
    else if (c === 0x5b || c === 0x7b) { if (++n > max) max = n; if (max > MAX_HONDO_JSON) return max; }
    else if (c === 0x5d || c === 0x7d) n--;
  }
  return max;
}

function textoDe(v, campo) {
  if (v === undefined || v === null) return "";
  if (typeof v !== "string") throw new ErrorMotor(`${campo} inválido`);
  return v;
}

/** base = carpeta /vX.Y.Z/ (URL); leer(url) → Uint8Array; indice(url) → lo que Pyodide acepta como indexURL. */
export function crearMotor({ base = new URL("./", import.meta.url), leer = leerFetch, indice = (u) => u.href, ahora = null } = {}) {
  let cargado = null;   // promesa: Pyodide se carga una vez por Worker
  let ocupado = false;  // S2: una generación a la vez

  async function cargar(avisar) {
    avisar("Cargando motor…");
    const m = JSON.parse(new TextDecoder().decode(await leer(new URL("manifiesto.json", base))));
    if (!VERSION.test(m.pyodide) || !Array.isArray(m.wheels) || !m.wheels.every((w) => WHEEL.test(w)))
      throw new ErrorMotor("El manifiesto de esta versión está dañado");
    const dirPy = new URL(`../pyodide/${m.pyodide}/`, base);
    const { loadPyodide } = await import(new URL("pyodide.mjs", dirPy).href);
    const py = await loadPyodide({ indexURL: indice(dirPy) });
    for (const w of m.wheels) py.unpackArchive(await leer(new URL(`../py/${w}`, base)), "wheel");
    const zip = await leer(new URL("nucleo.zip", base));
    if ((await sha256(zip)) !== m.nucleo_sha256) throw new ErrorMotor("El núcleo descargado no coincide con su manifiesto; recargue la página");
    py.unpackArchive(zip, "zip", { extractDir: "/nucleo" });
    return { py, puente: py.runPython(PUENTE), version: m.version };
  }

  async function generar(msg, avisar = () => {}) {
    if (ocupado) throw new ErrorMotor("Ya hay un Excel generándose; espere a que termine");
    ocupado = true;
    try {
      const crudo = bytesDe(msg.crudo, "crudo");
      if (!crudo) throw new ErrorMotor("Falta el archivo crudo (.json)");
      const extracto = bytesDe(msg.extracto, "extracto"), memoria = bytesDe(msg.memoria, "memoria");
      for (const [b, quien] of [[crudo, "El crudo está demasiado anidado"], [memoria, "La memoria del extracto está demasiado anidada"]])
        if (b && hondoJson(b) > MAX_HONDO_JSON) throw new ErrorMotor(quien);
      const negocio = textoDe(msg.negocio, "Negocio"), nit = textoDe(msg.nit, "NIT");
      cargado ??= cargar(avisar);
      let motor;
      try { motor = await cargado; } catch (e) {
        cargado = Promise.reject(e); cargado.catch(() => {});
        throw e instanceof ErrorMotor ? e : new ErrorMotor("No se pudo cargar el motor; recargue la página", sinRutas(e));
      }
      avisar("Armando libro…");
      let r;
      try { r = motor.puente(crudo, extracto, memoria, negocio, nit, ahora ?? ahoraLocal()); } catch (e) {
        if (!e?.pyodide_fatal_error) throw e;
        const muerto = new ErrorMotor("El motor se detuvo; recargue la página", sinRutas(e));
        cargado = Promise.reject(muerto); cargado.catch(() => {});
        throw muerto;
      }
      let o;
      try { o = r.toJs({ dict_converter: Object.fromEntries }); } finally { r.destroy(); }
      if (o.error) throw new ErrorMotor(o.error, o.detalle);
      const xlsx = o.xlsx.byteOffset === 0 && o.xlsx.byteLength === o.xlsx.buffer.byteLength ? o.xlsx : o.xlsx.slice();
      return { tipo: "listo", xlsx: xlsx.buffer, nombre: o.nombre, invalidos: o.invalidos, extracto: o.extracto ?? null, nucleo: motor.version };
    } finally {
      ocupado = false;
    }
  }
  return { generar };
}

// Solo dentro del navegador: en Node (contrato.mjs) se usa crearMotor directo.
if (typeof WorkerGlobalScope !== "undefined" && self instanceof WorkerGlobalScope) {
  const motor = crearMotor();
  self.onmessage = async ({ data }) => {
    if (!data || data.tipo !== "generar") return;
    try {
      const r = await motor.generar(data, (paso) => postMessage({ tipo: "avance", paso }));
      postMessage(r, [r.xlsx]);
    } catch (e) {
      const propio = e instanceof ErrorMotor;
      postMessage({ tipo: "error", mensaje: propio ? e.message : "Algo falló en el motor; recargue la página",
                    detalle: propio ? sinRutas(e.detalle) : sinRutas(e) });
    }
  };
}
