// T5 · contrato del Worker (R1, R5, S2, S3): `node web/pruebas/contrato.mjs`
// Arma web/dist/ con herramientas/web_build.py, corre el motor.worker.js de dist/ en Node (mismos manifiesto, wheels,
// nucleo.zip y Pyodide que baja el navegador) sobre crudo_v1.json y compara celda por celda con libro.generar en CPython.
import { spawnSync } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const APP = fileURLToPath(new URL("../../", import.meta.url));
const PY = process.env.PYTHON || "python";
const AHORA = "2026-10-26T09:30:00", NEG = "Restaurante de Prueba SAS", NIT = "900.123.456-7";
const fallos = [];
const chk = (ok, msg) => { console.log((ok ? "✓ " : "✗ ") + msg); if (!ok) fallos.push(msg); };
const python = (args) => spawnSync(PY, args, { cwd: APP, encoding: "utf8", env: { ...process.env, PYTHONIOENCODING: "utf8" } });

let p = python(["herramientas/web_build.py"]);
chk(p.status === 0, `build: ${(p.stdout + p.stderr).trim().split("\n").at(-1)}`);
if (p.status !== 0) process.exit(1);

const version = (await fs.readFile(path.join(APP, "VERSION"), "utf8")).trim();
const dirV = path.join(APP, "web", "dist", `v${version}`);
const src = await fs.readFile(path.join(APP, "web", "src", "motor.worker.js"));
chk(src.equals(await fs.readFile(path.join(dirV, "motor.worker.js"))), `dist/v${version}/motor.worker.js = web/src`);

// S3: el motor solo lee rutas dentro de web/dist/ (en el navegador: mismo origen).
const DIST = pathToFileURL(path.join(APP, "web", "dist") + path.sep).href;
const leidos = [];
const leer = async (u) => { leidos.push(u.href); return new Uint8Array(await fs.readFile(fileURLToPath(u))); };
const { crearMotor } = await import(pathToFileURL(path.join(dirV, "motor.worker.js")).href);
const motor = crearMotor({ base: pathToFileURL(dirV + path.sep), leer, indice: (u) => fileURLToPath(u), ahora: AHORA });

const crudo = await fs.readFile(path.join(APP, "web", "pruebas", "datos", "crudo_v1.json"));

// T10 · R5/ADR-027: cada versión publicada de dist/ sigue leyendo crudo v1 con su propio motor (su Excel puede diferir del
// núcleo actual si la lógica cambió después: aquí solo se exige que genere y que lea dentro de web/dist/).
const otras = (await fs.readdir(path.join(APP, "web", "dist"))).filter((d) => /^v\d+\.\d+\.\d+$/.test(d) && d !== `v${version}`);
for (const d of otras) {
  const dir = path.join(APP, "web", "dist", d), antes = leidos.length;
  const m = (await import(pathToFileURL(path.join(dir, "motor.worker.js")).href))
    .crearMotor({ base: pathToFileURL(dir + path.sep), leer, indice: (u) => fileURLToPath(u), ahora: AHORA });
  const ro = await m.generar({ tipo: "generar", crudo, negocio: NEG, nit: NIT }).catch((e) => ({ tipo: "error", mensaje: e.message }));
  const suyas = leidos.slice(antes);
  chk(ro.tipo === "listo" && ro.xlsx?.byteLength > 0 && ro.nucleo === d.slice(1) && suyas.length > 0 && suyas.every((u) => u.startsWith(DIST)),
      `R5 publicada ${d}: crudo_v1.json → Excel (${ro.xlsx?.byteLength ?? ro.mensaje}), ${suyas.length} lecturas dentro de web/dist/`);
}
chk(true, `R5: ${otras.length} versiones publicadas además de v${version}`);
const pasos = [];
const t0 = performance.now();
const r = await motor.generar({ tipo: "generar", crudo: crudo.buffer.slice(crudo.byteOffset, crudo.byteOffset + crudo.byteLength), negocio: NEG, nit: NIT },
                              (paso) => pasos.push(paso));
const ms = Math.round(performance.now() - t0);
chk(r.tipo === "listo" && r.xlsx instanceof ArrayBuffer && r.xlsx.byteLength > 0, `listo con xlsx como ArrayBuffer transferible (${r.xlsx?.byteLength} bytes, ${ms} ms con carga)`);
chk(r.nombre === "reporte_contable_20261026.xlsx" && Array.isArray(r.invalidos) && r.invalidos.length === 0 && r.extracto === null && r.nucleo === version,
    `nombre, inválidos [], extracto null, núcleo v${r.nucleo}`);
chk(pasos.join(" | ") === "Cargando motor… | Armando libro…", `avance: ${pasos.join(" | ")}`);
chk(leidos.length > 0 && leidos.every((u) => u.startsWith(DIST)), `S3: ${leidos.length} lecturas, todas dentro de web/dist/`);

// R1/R5: mismo Excel que CPython, celda por celda (valor y formato, como probar_libro.py).
const tmp = await fs.mkdtemp(path.join(os.tmpdir(), "contrato_"));
await fs.writeFile(path.join(tmp, "pyodide.xlsx"), new Uint8Array(r.xlsx));
const COMPARAR = `
import io, sys, json
from openpyxl import load_workbook
from parser_module.contable import libro
crudo, ext, pyo, neg, nit, ahora = sys.argv[1:]
def celdas(x):
    wb = load_workbook(io.BytesIO(x)); out = {"hojas": wb.sheetnames}
    for ws in wb:
        out[(ws.title, "merged")] = sorted(str(r) for r in ws.merged_cells.ranges)
        for fila in ws.iter_rows():
            for c in fila:
                if c.value is None and not c.has_style: continue
                out[(ws.title, c.coordinate)] = (c.value, c.number_format, c.font.b, c.font.color.rgb if c.font.color else None, c.fill.fgColor.rgb, c.alignment.horizontal)
    return out
a = celdas(libro.generar(open(crudo, "rb").read(), open(ext, "rb").read() if ext else None, None, neg, nit, ahora)["xlsx"])
b = celdas(open(pyo, "rb").read())
d = [str(k) for k in sorted(set(a) | set(b), key=str) if a.get(k) != b.get(k)]
print(json.dumps({"celdas": len(a), "distintas": len(d), "ejemplos": d[:5]}))
`;
const comparar = (ext = "") => {
  const q = python(["-c", COMPARAR, path.join(APP, "web", "pruebas", "datos", "crudo_v1.json"), ext, path.join(tmp, "pyodide.xlsx"), NEG, NIT, AHORA]);
  return q.status === 0 ? JSON.parse(q.stdout.trim().split("\n").at(-1)) : { distintas: -1, ejemplos: [q.stderr.slice(-300)] };
};
let cmp = comparar();
chk(cmp.distintas === 0, `R1/R5: crudo_v1.json → ${cmp.celdas} celdas, ${cmp.distintas} distintas frente a CPython ${JSON.stringify(cmp.ejemplos)}`);

// T8 · R2: crudo + el extracto sintético de probar_libro.py (generar.py) → mismo Excel y mismo resumen que CPython.
const rutaExt = path.join(tmp, "extracto.xlsx");
p = python(["-c", "import sys; sys.path.insert(0, 'web/pruebas/datos'); from generar import extracto_xlsx; open(sys.argv[1], 'wb').write(extracto_xlsx())", rutaExt]);
const ext = await fs.readFile(rutaExt);
const rx = await motor.generar({ tipo: "generar", crudo, extracto: ext, negocio: NEG, nit: NIT });
await fs.writeFile(path.join(tmp, "pyodide.xlsx"), new Uint8Array(rx.xlsx));
cmp = comparar(rutaExt);
chk(rx.tipo === "listo" && cmp.distintas === 0, `R2: crudo + extracto → ${cmp.celdas} celdas, ${cmp.distintas} distintas frente a CPython ${JSON.stringify(cmp.ejemplos)}`);
const res = rx.extracto ?? {};
chk(res.nuevas === 6 && res.ya_estaban === 0 && Number.isInteger(res.por_revisar) && JSON.stringify(res.dias_creados) === '["2026-09-18","2026-09-30"]',
    `R2: el resumen del extracto llega a la página: ${JSON.stringify(res)}`);
await fs.rm(tmp, { recursive: true, force: true });

// S2: entradas malas → error en español, sin traza ni rutas; el motor sigue sirviendo después.
async function error(msg) {
  try { await motor.generar({ tipo: "generar", negocio: NEG, nit: NIT, ...msg }); return null; }
  catch (e) { return { mensaje: e.message, detalle: e.detalle ?? "" }; }
}
const enc = (o) => new TextEncoder().encode(typeof o === "string" ? o : JSON.stringify(o));
const j = JSON.parse(crudo.toString("utf8"));
const casos = {
  "sin crudo": [{}, /Falta el archivo crudo/],
  "crudo vacío": [{ crudo: new ArrayBuffer(0) }, /Falta el archivo crudo/],
  "crudo no es archivo": [{ crudo: "texto" }, /no llegó como archivo/],
  "crudo > 20 MB (tope en JS)": [{ crudo: new ArrayBuffer(20 * 2 ** 20 + 1) }, /más de 20 MB/],
  "extracto > 5 MB (tope en JS)": [{ crudo: crudo, extracto: new ArrayBuffer(5 * 2 ** 20 + 1) }, /más de 5 MB/],
  "extracto que no es .xlsx": [{ crudo: crudo, extracto: enc("hola, no soy un excel") }, /^El extracto no sirve/],
  "memoria > 1 MB (tope en JS)": [{ crudo: crudo, memoria: new ArrayBuffer(2 ** 20 + 1) }, /más de 1 MB/],
  "JSON roto": [{ crudo: enc("{no es json") }, /./],
  "versión 2": [{ crudo: enc({ ...j, version: 2 }) }, /versi/i],
  "anidado 10⁴ (tope en JS, Pyodide moriría)": [{ crudo: enc("[".repeat(10000) + "]".repeat(10000)) }, /El crudo está demasiado anidado/],
  "anidado 65 (justo sobre el tope)": [{ crudo: enc("[".repeat(65) + "]".repeat(65)) }, /demasiado anidado/],
  "corchetes dentro de cadenas no cuentan": [{ crudo: enc({ x: "[".repeat(100) + '\\"' }) }, /^(?!.*anidado)/],
  "memoria anidada": [{ crudo: crudo, memoria: enc("{\"a\":".repeat(100) + "1" + "}".repeat(100)) }, /La memoria del extracto está demasiado anidada/],
  "NIT con fórmula": [{ crudo: crudo, nit: "=1+1" }, /NIT/],
  "negocio no es texto": [{ crudo: crudo, negocio: 7 }, /Negocio inválido/],
};
for (const [nombre, [msg, re]] of Object.entries(casos)) {
  const e = await error(msg);
  const limpio = e && !/Traceback|File "|\.py\b|[A-Za-z]:\\|file:/.test(e.mensaje + e.detalle);
  chk(e && re.test(e.mensaje) && limpio, `S2 ${nombre} → «${e?.mensaje}»${e?.detalle ? ` (detalle: ${e.detalle})` : ""}`);
}
const otra = await motor.generar({ tipo: "generar", crudo, negocio: NEG, nit: NIT });
chk(otra.tipo === "listo" && otra.xlsx.byteLength === r.xlsx.byteLength, "después de los errores el motor sigue generando (sin recargar Pyodide)");

// Una generación a la vez.
const [g1, g2] = await Promise.allSettled([motor.generar({ crudo, negocio: NEG, nit: NIT }), motor.generar({ crudo, negocio: NEG, nit: NIT })]);
chk(g1.status === "fulfilled" && g2.status === "rejected" && /Ya hay un Excel/.test(g2.reason.message), "S2: una generación a la vez (la segunda se rechaza)");

console.log(fallos.length ? `\n✗ ${fallos.length} fallos` : "\n✓ contrato del Worker verde");
process.exit(fallos.length ? 1 : 0);
