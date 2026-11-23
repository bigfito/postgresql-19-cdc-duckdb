#!/usr/bin/env bash
# =============================================================================
# ElastiFlix: publica las páginas de wiki/ en el wiki de GitHub del repositorio
# =============================================================================
# El wiki de GitHub es un repositorio aparte, <repositorio>.wiki.git. Las
# páginas se escriben y se revisan aquí, en wiki/, junto al resto de la
# documentación, y este script las copia allí.
#
# Uso, desde la raíz del repositorio:
#
#   bash wiki/publish.sh                  publica en el wiki de GitHub
#   bash wiki/publish.sh --dry-run DIR    deja en DIR lo que se publicaría
#
# Qué hace con cada página al copiarla:
#   - Las imágenes, que aquí apuntan a ../lab-design/diagrams/wiki-*.svg,
#     pasan a apuntar a images/, y los .svg se copian a esa carpeta del wiki.
#   - Los demás enlaces a ../ pasan a ser enlaces al repositorio en GitHub.
#   - Los enlaces entre páginas pierden el .md, que el wiki no usa.
#
# Publicar sustituye todas las páginas del wiki por las de esta carpeta: lo
# que se haya escrito a mano en el wiki y no esté aquí se pierde.

set -euo pipefail

fail() {
    echo "[wiki] ERROR: $*" >&2
    exit 1
}

[ -d wiki ] && [ -d lab-design/diagrams ] || fail "ejecuta el script desde la raíz del repositorio."

origin="$(git remote get-url origin)" || fail "el repositorio no tiene un remoto llamado origin."
repo_url="${origin%.git}"
wiki_url="${repo_url}.wiki.git"
blob_url="${repo_url}/blob/main"

dry_run_dir=""
if [ "${1:-}" = "--dry-run" ]; then
    dry_run_dir="${2:-}"
    [ -n "$dry_run_dir" ] || fail "--dry-run necesita un directorio de salida."
fi

if [ -n "$dry_run_dir" ]; then
    target="$dry_run_dir"
    mkdir -p "$target"
else
    target="$(mktemp -d)"
    trap 'rm -rf "$target"' EXIT
    git clone --quiet "$wiki_url" "$target" || fail "no se pudo clonar $wiki_url. Comprueba que el wiki esté activado en GitHub."
fi

# El contenido anterior se retira para que una página borrada aquí deje de
# existir también en el wiki.
find "$target" -maxdepth 1 -name '*.md' -delete
rm -rf "$target/images"
mkdir -p "$target/images"

pages=0
for page in wiki/*.md; do
    sed -E \
        -e 's#\]\(\.\./lab-design/diagrams/(wiki-[^)]+\.svg)\)#](images/\1)#g' \
        -e "s#\]\(\.\./#](${blob_url}/#g" \
        -e 's#\]\(([^)/:]+)\.md(\#[^)]*)?\)#](\1\2)#g' \
        "$page" > "$target/$(basename "$page")"
    pages=$((pages + 1))
done

images=0
for image in lab-design/diagrams/wiki-*.svg; do
    cp "$image" "$target/images/"
    images=$((images + 1))
done

echo "[wiki] $pages páginas y $images imágenes preparadas."

if [ -n "$dry_run_dir" ]; then
    echo "[wiki] Simulación: el resultado está en $dry_run_dir. No se publicó nada."
    exit 0
fi

git -C "$target" add -A
if git -C "$target" diff --cached --quiet; then
    echo "[wiki] El wiki ya está al día. No hay nada que publicar."
    exit 0
fi
commit="$(git rev-parse --short HEAD)"
git -C "$target" commit --quiet -m "Publica el wiki desde el commit $commit del repositorio"
git -C "$target" push --quiet
echo "[wiki] Publicado en ${repo_url}/wiki"
