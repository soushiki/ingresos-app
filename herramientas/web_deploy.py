"""T11 · despliega el modo contador web en Netlify desde este PC (ADR-027, R5, R6, S4).

    python herramientas/web_deploy.py [--sitio libro-contable-web]

1. Corre probar_libro.py, probar_web.py y web/pruebas/contrato.mjs (este último arma web/dist/ y prueba ese mismo dist/).
   Si una falla, se detiene: no despliega nada.
2. `netlify deploy --dir web/dist --no-build` → borrador; imprime su URL para mirarla.
3. Producción solo si la versión ya está congelada en web/publicadas.lock (la URL /vX.Y.Z/ no cambia nunca: ADR-027),
   tras mostrar el checklist de la cuenta y con «si» escrito a mano. Entonces repite con `--prod`.
Token: nunca en el repo ni en argumentos; `netlify login` (una vez) o la variable de entorno NETLIFY_AUTH_TOKEN."""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP / "herramientas"))
import web_build as wb   # noqa: E402

NETLIFY = "netlify-cli@27.12.0"   # la misma del borrador de T7; fijada para no correr una versión nueva sin mirarla
SITIO = "libro-contable-web"
PRUEBAS = [
    [sys.executable, "probar_libro.py"],
    [sys.executable, "probar_web.py"],
    ["node", "web/pruebas/contrato.mjs"],
]
# S4: lo que el código no puede revisar; se mira en app.netlify.com antes de cada --prod.
CHECKLIST = [
    "La cuenta de Netlify tiene 2FA activa (User settings → Security).",
    "Site configuration → Build & deploy → Snippet injection: vacío.",
    "Analytics / Real User Metrics: apagados (no inyectan scripts; la CSP los bloquearía igual).",
    "Forms, Functions e Identity: sin usar (el sitio es solo archivos estáticos).",
]


def correr(cmd: list[str]) -> subprocess.CompletedProcess:
    "Corre en la raíz del repo; la salida pasa tal cual a la consola salvo la de netlify (se lee su JSON)."
    if cmd[0] == "npx":   # en Windows es npx.cmd
        cmd = [shutil.which("npx") or "npx", *cmd[1:]]
    captura = "netlify-cli" in " ".join(cmd)
    return subprocess.run(cmd, cwd=APP, text=True, encoding="utf8", capture_output=captura)


def netlify(sitio: str, prod: bool) -> list[str]:
    cmd = ["npx", "--yes", NETLIFY, "deploy", "--dir", "web/dist", "--no-build", "--site", sitio, "--json"]
    return cmd + ["--prod"] if prod else cmd


def url_de(salida: str, clave: str) -> str:
    "netlify --json imprime un objeto (a veces con avisos antes)."
    return json.loads(salida[salida.index("{"):]).get(clave, "")


def main(argv: list[str] | None = None, ejecutar=correr, preguntar=input, publicadas=None) -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--sitio", default=SITIO, help="nombre o id del sitio en Netlify")
    o = a.parse_args(argv)
    version = (APP / "VERSION").read_text(encoding="utf8").strip()

    for cmd in PRUEBAS:
        print(f"\n▶ {' '.join(cmd[1:] if cmd[0] == sys.executable else cmd)}", flush=True)
        if ejecutar(cmd).returncode != 0:
            print(f"\n✗ falló {cmd[-1]}: no se despliega nada.")
            return 1

    print(f"\n▶ netlify deploy (borrador) de web/dist/ al sitio {o.sitio}", flush=True)
    b = ejecutar(netlify(o.sitio, prod=False))
    if b.returncode != 0:
        print(f"✗ netlify deploy falló (¿falta `npx {NETLIFY} login`?):\n{(b.stderr or '')[-800:]}")
        return 1
    print(f"✓ borrador: {url_de(b.stdout, 'deploy_url')}/v{version}/")

    publicadas = wb.leer_publicadas() if publicadas is None else publicadas
    if version not in publicadas:
        print(f"· producción: no. v{version} no está en web/publicadas.lock; tras revisar el borrador, congélela con "
              f"`python herramientas/web_build.py --publicar` y vuelva a correr este script (ADR-027).")
        return 0
    print("\nAntes de producción, revise en app.netlify.com:\n" + "\n".join(f"  [ ] {c}" for c in CHECKLIST))
    if preguntar(f"\n¿Publicar v{version} en producción? Escriba «si» para seguir: ").strip().lower() not in ("si", "sí"):
        print("· producción: no (queda solo el borrador).")
        return 0
    p = ejecutar(netlify(o.sitio, prod=True))
    if p.returncode != 0:
        print(f"✗ netlify deploy --prod falló:\n{(p.stderr or '')[-800:]}")
        return 1
    print(f"✓ producción: {url_de(p.stdout, 'url')}/v{version}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
