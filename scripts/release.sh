#!/usr/bin/env bash
# ============================================================================
# Zaas — flujo de versionamiento semántico (SemVer 1.x.x) con GitHub CLI
# ----------------------------------------------------------------------------
# Uso interactivo:
#   ./scripts/release.sh
#
# Uso no interactivo:
#   ./scripts/release.sh --bump patch --yes
#   ./scripts/release.sh --bump minor --title "Zaas v1.4.0 - Perfiles" --yes
#   ./scripts/release.sh --initial --yes
#
# Reglas:
#   1.0.0  -> versión inicial de producción / breaking changes
#   1.X.0  -> nuevas características, módulos o epics
#   1.x.X  -> correcciones, UI/UX y refactorizaciones
#
# La versión se escribe en VERSION y frontend/package.json, se commitea como
# "chore(release): vX.Y.Z" y después se crea el tag/release en GitHub.
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------- colores
if [[ -t 1 ]]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
  BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

info()  { printf "${BLUE}ℹ${NC} %s\n" "$*"; }
ok()    { printf "${GREEN}✔${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}⚠${NC} %s\n" "$*"; }
die()   { printf "${RED}✖${NC} %s\n" "$*" >&2; exit 1; }

# ---------------------------------------------------------------- argumentos
BUMP=""
INITIAL=0
TITLE=""
NOTES_OVERRIDE=""
ASSUME_YES=0
DRY_RUN=0

usage() {
  cat <<EOF
${BOLD}Zaas release${NC}

Opciones:
  --bump <patch|minor|major>  Tipo de incremento (si se omite, se pregunta).
  --initial                   Fuerza la versión inicial 1.0.0.
  --title <texto>             Título de la release en GitHub.
  --notes <texto>             Notas manuales (omite la generación automática).
  --yes                       No pedir confirmación final.
  --dry-run                   Mostrar qué haría sin crear la release.
  -h, --help                  Mostrar esta ayuda.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bump) BUMP="${2:-}"; shift 2 ;;
    --initial) INITIAL=1; shift ;;
    --title) TITLE="${2:-}"; shift 2 ;;
    --notes) NOTES_OVERRIDE="${2:-}"; shift 2 ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Opción desconocida: $1 (usa --help)" ;;
  esac
done

# ---------------------------------------------------------------- precondiciones
command -v git >/dev/null 2>&1 || die "git no está instalado."
command -v gh  >/dev/null 2>&1 || die "GitHub CLI (gh) no está instalado."

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "No estás dentro de un repositorio git."

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

gh auth status >/dev/null 2>&1 || die "gh no está autenticado. Ejecuta: gh auth login"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$BRANCH" != "main" && "$BRANCH" != "develop" ]]; then
  warn "Estás en la rama '$BRANCH' (se recomienda main o develop)."
  if [[ "$ASSUME_YES" -ne 1 ]]; then
    read -rp "¿Continuar de todos modos? [y/N] " resp
    [[ "$resp" =~ ^[yY]$ ]] || { info "Cancelado."; exit 1; }
  fi
fi

# Solo bloquean los cambios en archivos rastreados. Los archivos sin seguimiento
# (por ejemplo, carpetas de skills locales) no se publican en la release.
if ! git diff --quiet || ! git diff --cached --quiet; then
  die "Hay cambios pendientes en archivos rastreados. Haz commit o stash primero."
fi

if [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
  warn "Hay archivos sin seguimiento; no se incluirán en el release."
fi

info "Actualizando tags remotos..."
git fetch --tags --prune --quiet

# ---------------------------------------------------------------- última versión
LATEST_TAG="$(git tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -n1 || true)"

if [[ -z "$LATEST_TAG" ]]; then
  BASE_VERSION="0.0.0"
  RANGE="HEAD"
  info "No hay tags SemVer previos. La primera versión será ${BOLD}v1.0.0${NC}."
else
  BASE_VERSION="${LATEST_TAG#v}"
  RANGE="${LATEST_TAG}..HEAD"
  info "Última versión publicada: ${BOLD}${LATEST_TAG}${NC}"
fi

# ---------------------------------------------------------------- tipo de bump
if [[ "$INITIAL" -eq 1 || -z "$LATEST_TAG" ]]; then
  BUMP="initial"
elif [[ -z "$BUMP" ]]; then
  echo
  echo "${BOLD}¿Qué tipo de release vas a publicar?${NC}"
  echo "  1) patch  -> correcciones, UI/UX, refactorizaciones (1.x.+1)"
  echo "  2) minor  -> nuevas características o módulos (1.+1.0)"
  echo "  3) major  -> cambios incompatibles / producción (2.0.0)"
  read -rp "Selecciona [1-3] (por defecto 1): " opcion
  case "${opcion:-1}" in
    1) BUMP="patch" ;;
    2) BUMP="minor" ;;
    3) BUMP="major" ;;
    *) die "Opción inválida." ;;
  esac
fi

case "$BUMP" in
  initial) BUMP="initial" ;;
  patch|minor|major) ;;
  *) die "Tipo de bump inválido: $BUMP (usa patch, minor o major)." ;;
esac

# ---------------------------------------------------------------- nueva versión
IFS='.' read -r MAJOR MINOR PATCH <<< "$BASE_VERSION"
MAJOR="${MAJOR:-0}"; MINOR="${MINOR:-0}"; PATCH="${PATCH:-0}"

if [[ "$BUMP" == "initial" ]]; then
  NEW_VERSION="1.0.0"
elif [[ "$BUMP" == "patch" ]]; then
  NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))"
elif [[ "$BUMP" == "minor" ]]; then
  NEW_VERSION="${MAJOR}.$((MINOR + 1)).0"
elif [[ "$BUMP" == "major" ]]; then
  NEW_VERSION="$((MAJOR + 1)).0.0"
fi

TAG="v${NEW_VERSION}"

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  die "El tag $TAG ya existe. Elige otro tipo de bump o elimínalo primero."
fi

# ---------------------------------------------------------------- sincronización
if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  UPSTREAM="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}')"
  read -r AHEAD BEHIND < <(git rev-list --left-right --count "HEAD...${UPSTREAM}")
  if (( BEHIND > 0 )); then
    die "Tu rama está $BEHIND commit(s) detrás de $UPSTREAM. Haz pull antes del release."
  fi
  if (( AHEAD > 0 )); then
    warn "Tienes $AHEAD commit(s) local(es) sin publicar en $UPSTREAM."
    if [[ "$ASSUME_YES" -ne 1 ]]; then
      read -rp "¿Hacer push antes de crear el release? [Y/n] " push_resp
    else
      push_resp="y"
    fi
    if [[ ! "${push_resp:-y}" =~ ^[nN]$ ]]; then
      git push
      ok "Push realizado."
    fi
  fi
fi

# ---------------------------------------------------------------- notas
build_notes() {
  local range="$1"
  local feat="" fix="" ui="" docs="" other="" line
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    case "$line" in
      feat:*|feat\(*)                 feat+="- ${line}"$'\n' ;;
      fix:*|fix\(*)                   fix+="- ${line}"$'\n' ;;
      docs:*|docs\(*)                 docs+="- ${line}"$'\n' ;;
      refactor:*|refactor\(*|perf:*|perf\(*|style:*|style\(*)
                                      ui+="- ${line}"$'\n' ;;
      *)                              other+="- ${line}"$'\n' ;;
    esac
  done < <(git log "$range" --no-merges --pretty=format:'%s')

  local notas=""
  if [[ -n "$feat" ]]; then
    notas+=$'### 🚀 Nuevas características\n'"${feat}"$'\n'
  fi
  if [[ -n "$ui" ]]; then
    notas+=$'### 🎨 UI/UX, rendimiento y refactorizaciones\n'"${ui}"$'\n'
  fi
  if [[ -n "$fix" ]]; then
    notas+=$'### 🐛 Correcciones\n'"${fix}"$'\n'
  fi
  if [[ -n "$docs" || -n "$other" ]]; then
    notas+=$'### 📚 Documentación y mantenimiento\n'"${docs}${other}"$'\n'
  fi

  if [[ -z "$notas" ]]; then
    notas="(Sin cambios nuevos desde el último release.)"
  fi

  printf '%s' "$notas"
}

if [[ -n "$NOTES_OVERRIDE" ]]; then
  NOTES="$NOTES_OVERRIDE"
else
  NOTES="$(build_notes "$RANGE")"
fi

DEFAULT_TITLE="Zaas ${TAG}"
[[ -z "$TITLE" ]] && TITLE="$DEFAULT_TITLE"

# ---------------------------------------------------------------- confirmación
echo
echo "${BOLD}Resumen de la release${NC}"
echo "  Rama:          $BRANCH"
echo "  Commit:        $(git rev-parse --short HEAD) — $(git log -1 --pretty=%s)"
echo "  Versión base:  ${LATEST_TAG:-<ninguna>}"
echo "  Nueva versión: ${TAG}"
echo "  Título:        ${TITLE}"
echo
echo "${BOLD}Notas generadas:${NC}"
echo "------------------------------------------------------------------"
echo "$NOTES"
echo "------------------------------------------------------------------"

if [[ "$DRY_RUN" -eq 1 ]]; then
  warn "Dry-run: no se creó ninguna release."
  exit 0
fi

if [[ "$ASSUME_YES" -ne 1 ]]; then
  read -rp "¿Crear el tag ${TAG} y publicar la release en GitHub? [y/N] " confirm
  [[ "$confirm" =~ ^[yY]$ ]] || { info "Cancelado."; exit 1; }
fi

# ---------------------------------------------------------------- versión
# Mantiene sincronizados VERSION y frontend/package.json con el tag.
printf '%s\n' "$NEW_VERSION" > VERSION
python3 - "$NEW_VERSION" <<'PY'
import json
import sys

path = 'frontend/package.json'
with open(path, encoding='utf-8') as archivo:
    datos = json.load(archivo)
datos['version'] = sys.argv[1]
with open(path, 'w', encoding='utf-8') as archivo:
    json.dump(datos, archivo, indent=2, ensure_ascii=False)
    archivo.write('\n')
PY

git add VERSION frontend/package.json
if ! git diff --cached --quiet; then
  git commit -m "chore(release): v${NEW_VERSION}"
  ok "Versión actualizada a ${NEW_VERSION}."
else
  info "La versión ya estaba en ${NEW_VERSION}."
fi

# El commit de versión debe estar en el remoto antes de crear la release.
if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  git push
  ok "Commit de versión publicado."
else
  warn "Sin upstream configurado: publica el commit de versión antes de crear la release."
fi

# ---------------------------------------------------------------- publicar
info "Creando tag y release ${TAG}..."
gh release create "$TAG" \
  --target "$BRANCH" \
  --title "$TITLE" \
  --notes "$NOTES"

ok "Release ${TAG} publicada correctamente."
gh release view "$TAG" --json url,isDraft,isPrerelease --jq '"URL: \(.url) | draft: \(.isDraft) | prerelease: \(.isPrerelease)"'
