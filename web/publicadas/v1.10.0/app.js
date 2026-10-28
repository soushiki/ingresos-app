// T6 · vista del modo contador web (03 §3.4): nunca corre Python ni lee el contenido de los archivos, solo pasa bytes
// al Worker (ADR-028). Todo texto que viene de afuera (nombre del archivo, mensajes del motor) entra con textContent (S2).

const MB = 2 ** 20;
const TOPE_CRUDO = 20 * MB, TOPE_EXTRACTO = 5 * MB;   // S2: los mismos topes del Worker y de libro.generar, antes de leer el archivo
const CLAVE = "ingresos.contador";   // 03 §4: lo único que se guarda (negocio y NIT)

const $ = (id) => document.getElementById(id);
const form = $("form"), negocio = $("negocio"), nit = $("nit"), crudo = $("crudo"), extracto = $("extracto"), boton = $("generar");

// R6: la carpeta /vX.Y.Z/ es la versión de la página; el núcleo la confirma el Worker con su manifiesto.
const vRuta = location.pathname.match(/\/v(\d+\.\d+\.\d+)\//);
$("v-pagina").textContent = vRuta ? `v${vRuta[1]}` : "sin versión";

// R4: si el navegador no deja guardar (modo privado, bloqueado), la página sigue y los pide de nuevo.
function leerGuardado() {
  try {
    const o = JSON.parse(localStorage.getItem(CLAVE) || "{}");
    if (typeof o.negocio === "string") negocio.value = o.negocio.slice(0, 120);
    if (typeof o.nit === "string") nit.value = o.nit.slice(0, 20);
  } catch { /* sin almacenamiento: campos vacíos */ }
}
function guardar() {
  try { localStorage.setItem(CLAVE, JSON.stringify({ negocio: negocio.value, nit: nit.value })); }
  catch { $("nota-memoria").textContent = "Este navegador no deja recordarlos: escríbalos cada vez."; }
}
leerGuardado();
negocio.addEventListener("input", guardar);
nit.addEventListener("input", guardar);

let motor = null, ocupado = false, urlExcel = null;

function mostrar(id, si) { $(id).hidden = !si; }
function limpiar() { mostrar("error", false); mostrar("listo", false); mostrar("estado", false); }

function error(mensaje, detalle = "") {
  mostrar("estado", false);
  $("error-mensaje").textContent = mensaje;
  $("error-detalle").textContent = detalle;
  $("error-plegado").hidden = !detalle;
  $("error-plegado").open = false;
  mostrar("error", true);
}

function puedeGenerar() { boton.disabled = ocupado || !crudo.files.length; }

const tamano = (f) => f.size < MB ? `${Math.max(1, Math.round(f.size / 1024))} KB` : `${(f.size / MB).toFixed(1).replace(".", ",")} MB`;

crudo.addEventListener("change", () => {
  limpiar();
  const f = crudo.files[0];
  $("archivo").textContent = f ? `${f.name} · ${tamano(f)}` : "";
  mostrar("archivo", !!f);
  if (f && f.size > TOPE_CRUDO) error("El crudo pesa más de 20 MB; revise que sea el archivo .json que exporta la captura.");
  puedeGenerar();
});

// R2: el extracto es opcional; si no sirve se quita solo él y el crudo elegido se queda.
function quitarExtracto() {
  extracto.value = "";
  mostrar("archivo-extracto", false);
}
extracto.addEventListener("change", () => {
  limpiar();
  const f = extracto.files[0];
  if (f && f.size > TOPE_EXTRACTO) {
    quitarExtracto();
    return error(`El extracto «${f.name}» pesa más de 5 MB; revise que sea el .xlsx que baja del banco. El crudo sigue elegido.`);
  }
  $("archivo-extracto-nombre").textContent = f ? `${f.name} · ${tamano(f)}` : "";
  mostrar("archivo-extracto", !!f);
});
$("quitar-extracto").addEventListener("click", () => { quitarExtracto(); limpiar(); });

function nuevoMotor() {
  const w = new Worker("motor.worker.js", { type: "module" });
  w.onerror = (e) => {
    e.preventDefault();
    terminar();
    w.terminate();
    if (motor === w) motor = null;   // el próximo clic arranca uno nuevo
    error("No se pudo cargar el motor; recargue la página.", String(e.message || "").replace(/[a-z][a-z0-9+.-]*:\/\/\S+/gi, "…"));
  };
  w.onmessage = ({ data }) => {
    if (!data) return;
    if (data.tipo === "avance") { $("paso").textContent = data.paso; return; }
    terminar();
    if (data.tipo === "error") {
      const delExtracto = /^El extracto/.test(data.mensaje);
      error(delExtracto ? `${data.mensaje}. El crudo sigue elegido: quite el extracto o elija otro.` : data.mensaje, data.detalle);
      // El Worker dice «recargue» cuando su Pyodide murió: uno nuevo evita pedirle al contador que recargue.
      if (/recargue/i.test(data.mensaje)) { w.terminate(); if (motor === w) motor = null; }
    } else if (data.tipo === "listo") listo(data);
  };
  return w;
}

function terminar() { ocupado = false; boton.textContent = "Generar Excel"; puedeGenerar(); }

// R2: lo que hizo el extracto, para que el contador sepa qué revisar en el Excel.
const cuenta = (x, uno, varios) => `${x} ${x === 1 ? uno : varios}`;
function resumenExtracto(r) {
  if (!r) return "";
  const partes = [cuenta(r.nuevas, "línea nueva", "líneas nuevas"), `${r.por_revisar} por revisar`];
  if (r.ya_estaban) partes.push(cuenta(r.ya_estaban, "repetida", "repetidas"));
  const creados = r.dias_creados || [];
  partes.push(creados.length ? `${cuenta(creados.length, "día creado", "días creados")} (${creados.join(", ")})` : "ningún día creado");
  return `Extracto: ${partes.join(" · ")}.`;
}

function listo({ xlsx, nombre, invalidos, extracto: resumen, nucleo }) {
  mostrar("estado", false);
  if (urlExcel) URL.revokeObjectURL(urlExcel);
  urlExcel = URL.createObjectURL(new Blob([xlsx], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }));
  const a = $("descarga");
  a.href = urlExcel;
  a.download = nombre;
  $("listo-texto").textContent = `Listo: ${nombre}. Si la descarga no empezó, use el botón.`;
  $("v-nucleo").textContent = `v${nucleo}`;
  $("resumen-extracto").textContent = resumenExtracto(resumen);
  mostrar("resumen-extracto", !!resumen);
  const lista = $("invalidos-lista");
  lista.replaceChildren(...(invalidos || []).map(({ fecha, motivo }) => {
    const li = document.createElement("li");
    li.textContent = `${fecha}: ${motivo}`;
    return li;
  }));
  mostrar("invalidos", lista.children.length > 0);
  mostrar("listo", true);
  a.click();
}

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = crudo.files[0];
  if (ocupado || !f) return;
  limpiar();
  if (f.size > TOPE_CRUDO) return error("El crudo pesa más de 20 MB; revise que sea el archivo .json que exporta la captura.");
  ocupado = true;
  boton.disabled = true;
  boton.textContent = "Generando…";
  $("paso").textContent = "Leyendo archivo…";
  mostrar("estado", true);
  const fe = extracto.files[0];
  let bytes, bytesExt;
  try { bytes = await f.arrayBuffer(); }
  catch { terminar(); return error("No se pudo leer el crudo; vuelva a elegirlo."); }
  try { bytesExt = fe ? await fe.arrayBuffer() : undefined; }
  catch { terminar(); quitarExtracto(); return error("No se pudo leer el extracto; vuelva a elegirlo. El crudo sigue elegido."); }
  motor ??= nuevoMotor();
  motor.postMessage({ tipo: "generar", crudo: bytes, extracto: bytesExt, negocio: negocio.value.trim(), nit: nit.value.trim() },
                    bytesExt ? [bytes, bytesExt] : [bytes]);
});

puedeGenerar();
