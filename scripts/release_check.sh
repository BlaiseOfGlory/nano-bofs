#!/usr/bin/env bash
set -euo pipefail

TAG=""
SKIP_DOCKER=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-docker)
            SKIP_DOCKER=1
            shift
            ;;
        -*)
            printf 'Unknown option: %s\n' "$1" >&2
            exit 2
            ;;
        *)
            if [[ -n "${TAG}" ]]; then
                printf 'Unexpected extra argument: %s\n' "$1" >&2
                exit 2
            fi
            TAG="$1"
            shift
            ;;
    esac
done

SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd -- "${SCRIPT_PATH%/*}" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

export UV_CACHE_DIR="${UV_CACHE_DIR:-${REPO_ROOT}/.local/uv-cache}"
UV_PYTHON=(uv run --no-project --python 3.11 python)

step() {
    printf '==> %s\n' "$1"
}

step "Reading project version"
VERSION="$("${UV_PYTHON[@]}" -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")"
EXPECTED_TAG="v${VERSION}"

if [[ -z "${TAG}" ]]; then
    TAG="${EXPECTED_TAG}"
fi

step "Checking release metadata contracts"
"${UV_PYTHON[@]}" scripts/release_contract_check.py --tag "${TAG}"

step "Checking working tree"
if [[ -n "$(git status --porcelain)" ]]; then
    git status --porcelain
    printf 'Working tree is not clean. Commit or stash changes before tagging a release.\n' >&2
    exit 1
fi

step "Checking current commit is on master"
git fetch origin master:refs/remotes/origin/master --depth=1
git merge-base --is-ancestor HEAD origin/master

step "Checking tag does not already exist"
if [[ -n "$(git tag --list "${TAG}")" ]]; then
    printf "Local tag '%s' already exists.\n" "${TAG}" >&2
    exit 1
fi

REMOTE_TAG="$(git ls-remote --tags origin "refs/tags/${TAG}")"
if [[ -n "${REMOTE_TAG}" ]]; then
    printf "Remote tag '%s' already exists on origin.\n" "${TAG}" >&2
    exit 1
fi

step "Syncing root dependencies from lockfile"
uv sync --locked --python 3.11

step "Clearing nano-bofs environment overrides"
unset NANO_BOFS_CONFIG
unset NANO_BOFS_DEFAULT_BACKEND
unset NANO_BOFS_DOCKER_IMAGE
unset NANO_BOFS_STATE_DIR

step "Running unit tests"
uv run python -m unittest

step "Building Python package"
uv build --python 3.11

step "Smoke testing built wheel"
WHEEL_ENV="${REPO_ROOT}/.local/wheel-smoke"
rm -rf "${WHEEL_ENV}"
"${UV_PYTHON[@]}" -m venv "${WHEEL_ENV}"
"${WHEEL_ENV}/bin/python" -m pip install --no-index --find-links dist nano-bofs
"${WHEEL_ENV}/bin/nano-bofs" list
"${WHEEL_ENV}/bin/python" - <<'PY'
import nano_bofs.template_catalog as catalog

names = set(catalog.discover_templates())
assert "probe" in names
assert "ldapsearch" in names
print(f"loaded {len(names)} templates from installed wheel")
PY

step "Syncing Mythic runtime dependencies from lockfile"
(
    cd Payload_Type/nano_bofs
    uv sync --locked --python 3.11
    step "Smoke testing Mythic runtime imports"
    uv run python - <<'PY'
import mythic_container
import nano_bofs.template_catalog as catalog

names = set(catalog.discover_templates())
assert "mythicSmoke" in names
assert "ldapsearch" in names
print(f"loaded {len(names)} Mythic runtime templates")
PY
)

if [[ "${SKIP_DOCKER}" -eq 0 ]]; then
    step "Building Docker image"
    docker build --pull=false --tag "nano-bofs-release-check:${VERSION}" --file Payload_Type/nano_bofs/Dockerfile .

    step "Smoke testing Docker image imports"
    docker run -i --rm --entrypoint python "nano-bofs-release-check:${VERSION}" - <<'PY'
import mythic_container
import nano_bofs.template_catalog as catalog

names = set(catalog.discover_templates())
assert "mythicSmoke" in names
assert "ldapsearch" in names
print(f"loaded {len(names)} Docker templates")
PY
fi

step "Release preflight passed for ${TAG}"
printf 'Next:\n'
printf '  git tag -a %s -m "%s"\n' "${TAG}" "${TAG}"
printf '  git push origin %s\n' "${TAG}"
