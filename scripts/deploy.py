"""
Compila el sitio y sube el resultado a un repositorio Git conectado a
Cloudflare Pages o GitHub Pages (hosting y SSL gratuitos).

Requisitos previos (una sola vez):
  1. Tener git instalado y configurado (user.name / user.email).
  2. Crear un repositorio vacio en GitHub y anadirlo como remoto:
         git init
         git remote add origin https://github.com/tu-usuario/tu-repo.git
  3a. Cloudflare Pages: en el dashboard de Cloudflare, "Workers & Pages" ->
      "Create application" -> "Pages" -> "Connect to Git", elegir el repo.
      Cloudflare compilara y desplegara automaticamente en cada push
      (Build command: vacio, Output directory: dist).
  3b. GitHub Pages (alternativa aun mas simple, sin servicios externos):
      en el repo de GitHub -> Settings -> Pages -> Deploy from a branch,
      seleccionar la rama que uses (ver --branch) y la carpeta "/" (root)
      si publicas el propio contenido de dist/ como rama, por ejemplo gh-pages.

Uso:
    python scripts/deploy.py                       # build + commit + push a la rama actual
    python scripts/deploy.py --branch gh-pages      # publica el contenido de dist/ en una rama dedicada
    python scripts/deploy.py --no-build             # solo hace commit+push (no recompila)
    python scripts/deploy.py --dry-run              # compila y muestra que haria, sin tocar git
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"


def run(cmd: list, cwd: Path = ROOT, check: bool = True):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        if check:
            sys.exit(result.returncode)
    return result


def ensure_git_repo():
    if not (ROOT / ".git").exists():
        print("[ERROR] Este directorio no es un repositorio git todavía.")
        print("        Ejecuta primero:")
        print("        git init")
        print("        git remote add origin https://github.com/tu-usuario/tu-repo.git")
        sys.exit(1)

    remotes = run(["git", "remote"], check=False).stdout
    if "origin" not in remotes:
        print("[ERROR] No hay remoto 'origin' configurado.")
        print("        git remote add origin https://github.com/tu-usuario/tu-repo.git")
        sys.exit(1)


def build_site():
    print("== Compilando el sitio (build.py) ==")
    run([sys.executable, str(ROOT / "scripts" / "build.py")])


def deploy_same_branch(dry_run: bool):
    ensure_git_repo()
    run(["git", "add", "-A"])

    status = run(["git", "status", "--porcelain"], check=False).stdout
    if not status.strip():
        print("No hay cambios que subir.")
        return

    if dry_run:
        print("[DRY RUN] Cambios detectados, no se hace commit ni push:")
        print(status)
        return

    msg = f"Actualiza sitio: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    run(["git", "commit", "-m", msg])
    run(["git", "push", "origin", "HEAD"])
    print("[OK] Cambios subidos. Si tienes Cloudflare Pages / GitHub Pages conectado")
    print("     al repositorio, el despliegue se disparará automáticamente.")


def deploy_dist_branch(branch: str, dry_run: bool):
    """
    Publica SOLO el contenido de dist/ en una rama dedicada (util para
    GitHub Pages sirviendo directamente la raiz de esa rama).
    Requiere el paquete 'ghp-import' (pip install ghp-import) o git subtree;
    aqui usamos un enfoque simple con git worktree para no depender de mas
    herramientas externas.
    """
    ensure_git_repo()
    if dry_run:
        print(f"[DRY RUN] Publicaría el contenido de dist/ en la rama '{branch}'.")
        return

    worktree_dir = ROOT / f".worktree-{branch}"
    run(["git", "fetch", "origin"], check=False)

    branch_exists = run(["git", "ls-remote", "--heads", "origin", branch], check=False).stdout.strip() != ""

    if worktree_dir.exists():
        run(["git", "worktree", "remove", "--force", str(worktree_dir)], check=False)

    if branch_exists:
        run(["git", "worktree", "add", str(worktree_dir), branch])
    else:
        run(["git", "worktree", "add", "-B", branch, str(worktree_dir)])

    # Limpia el worktree y copia el contenido nuevo de dist/
    for item in worktree_dir.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            run(["cmd", "/c", "rmdir", "/s", "/q", str(item)], check=False)
        else:
            item.unlink()

    run(["xcopy", str(DIST_DIR), str(worktree_dir), "/E", "/I", "/Y"], check=False)

    run(["git", "add", "-A"], cwd=worktree_dir)
    status = run(["git", "status", "--porcelain"], cwd=worktree_dir, check=False).stdout
    if status.strip():
        msg = f"Deploy: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        run(["git", "commit", "-m", msg], cwd=worktree_dir)
        run(["git", "push", "origin", branch], cwd=worktree_dir)
        print(f"[OK] Contenido de dist/ publicado en la rama '{branch}'.")
    else:
        print("No hay cambios que publicar en la rama de despliegue.")

    run(["git", "worktree", "remove", "--force", str(worktree_dir)], check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", default=None, help="Publicar dist/ en una rama dedicada (ej. gh-pages)")
    parser.add_argument("--no-build", action="store_true", help="No recompilar, usar el dist/ existente")
    parser.add_argument("--dry-run", action="store_true", help="No hacer commit ni push, solo mostrar cambios")
    args = parser.parse_args()

    if not args.no_build:
        build_site()

    if args.branch:
        deploy_dist_branch(args.branch, args.dry_run)
    else:
        deploy_same_branch(args.dry_run)


if __name__ == "__main__":
    main()
