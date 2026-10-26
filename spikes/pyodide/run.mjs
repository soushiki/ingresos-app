import { loadPyodide } from "pyodide";
import fs from "node:fs"; import path from "node:path";
const [S, APP] = process.argv.slice(2);
const t0 = performance.now();
const py = await loadPyodide();   // núcleo local (node_modules), sin red
const t1 = performance.now();
for (const w of fs.readdirSync(`${S}/wheels`)) py.unpackArchive(new Uint8Array(fs.readFileSync(`${S}/wheels/${w}`)), "wheel");
py.FS.mkdirTree("/app");
const copiar = (src, dst) => { for (const e of fs.readdirSync(src, { withFileTypes: true })) {
  if (e.name === "__pycache__") continue; const s = path.join(src, e.name), d = `${dst}/${e.name}`;
  if (e.isDirectory()) { py.FS.mkdirTree(d); copiar(s, d); } else if (/\.(py|json)$/.test(e.name)) py.FS.writeFile(d, fs.readFileSync(s)); } };
py.FS.mkdirTree("/app/parser_module"); copiar(`${APP}/parser_module`, "/app/parser_module");
py.FS.writeFile("/app/nucleo.py", fs.readFileSync(`${S}/nucleo.py`));
py.FS.writeFile("/ext.xlsx", fs.readFileSync("D:/Claude/image_to_text/data/SEPTIEMBRE/202609 - Movimientos banco 1-30Sept2026.xlsx"));
py.FS.writeFile("/crudo.json", fs.readFileSync(`${S}/crudo_sept.json`));
const t2 = performance.now();
const out = py.runPython(`
import sys, time; sys.path.insert(0, "/app")
from nucleo import libro_desde_crudo
t = time.time(); x = libro_desde_crudo(open("/crudo.json","rb").read()); print("pyodide calc s", round(time.time()-t,2), sys.version.split()[0])
from parser_module.contable.extracto import leer_xlsx
t=time.time(); L=leer_xlsx(open("/ext.xlsx","rb").read()); print("extracto lineas", len(L), "s", round(time.time()-t,2), "hash", __import__("hashlib").sha256(repr(L).encode()).hexdigest()[:12])
x`).toJs();
fs.writeFileSync(`${S}/pyo.xlsx`, out);
console.log("load ms", Math.round(t1 - t0), "setup ms", Math.round(t2 - t1), "xlsx KB", out.length >> 10);
