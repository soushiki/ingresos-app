// La UI nunca corre Python: solo habla con el Worker (ADR-028).
const salida = document.getElementById("salida");
const t0 = performance.now();
try { (0, eval)("1"); console.log("eval en página: permitido (MAL)"); } catch (e) { console.log("eval en página: bloqueado " + e.name); }
const w = new Worker("worker.js", { type: "module" });
const linea = (txt) => { salida.textContent += "\n" + txt; console.log(txt); };
w.onmessage = (e) => {
  if (e.data.error) linea("ERROR: " + e.data.error);
  else linea(`${e.data.paso}: ${e.data.valor} (${Math.round(performance.now() - t0)} ms)`);
  if (e.data.fin) { document.title = e.data.error ? "FALLA" : "PASS"; w.terminate(); }
};
w.onerror = (e) => { linea("ERROR worker: " + e.message); document.title = "FALLA"; };
