#!/usr/bin/env bash
#
# notifynl-admin — testrunner
set -euo pipefail

VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements_nl_test.txt"

MINIO_SERVICE="svc/minio"
MINIO_LOCAL_PORT=9000
MINIO_REMOTE_PORT=9000

MINIO_PORT_FORWARD_PID=""

cleanup() {
    if [[ -n "$MINIO_PORT_FORWARD_PID" ]]; then
        echo "Stopping MinIO kubectl port-forward (pid $MINIO_PORT_FORWARD_PID)..."
        kill "$MINIO_PORT_FORWARD_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "==> Step 1: Activating virtual environment"
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Virtual environment not found, creating one at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Step 2: Installing requirements from $REQUIREMENTS_FILE"
# Overslaan kan met SKIP_INSTALL=1 ./run_tests.sh
if [[ "${SKIP_INSTALL:-0}" == "1" ]]; then
    echo "SKIP_INSTALL=1, install overgeslagen"
elif command -v uv >/dev/null 2>&1; then
    echo "uv gevonden, installeren met uv pip"
    uv pip install -r "$REQUIREMENTS_FILE"
elif python -m pip --version >/dev/null 2>&1; then
    python -m pip install --upgrade pip >/dev/null
    python -m pip install -r "$REQUIREMENTS_FILE"
else
    if python -m ensurepip --upgrade >/dev/null 2>&1; then
        python -m pip install -r "$REQUIREMENTS_FILE"
    else
        echo "ERROR: kan de requirements niet installeren."
        exit 1
    fi
fi

echo "==> Step 3: Generating app/version.py"
make generate-version-file

echo "==> Step 4: Building frontend assets"
if [[ ! -f "app/static/images/favicon.ico" ]]; then
    npm ci
    npm run build
else
    echo "app/static already present, skipping npm build"
fi

echo "==> Step 5: Port-forwarding MinIO from Minikube ($MINIO_SERVICE -> localhost:$MINIO_LOCAL_PORT)"
kubectl port-forward "$MINIO_SERVICE" "${MINIO_LOCAL_PORT}:${MINIO_REMOTE_PORT}" \
    >/tmp/minio-port-forward.log 2>&1 &
MINIO_PORT_FORWARD_PID=$!

sleep 2
if ! kill -0 "$MINIO_PORT_FORWARD_PID" 2>/dev/null; then
    echo "ERROR: MinIO kubectl port-forward failed to start. Log output:"
    cat /tmp/minio-port-forward.log
    exit 1
fi
echo "MinIO port-forward running with pid $MINIO_PORT_FORWARD_PID"

echo "==> Step 6: Exporting environment variables"
export MINIO_URL="http://localhost:${MINIO_LOCAL_PORT}"


echo "    MINIO_URL=$MINIO_URL"

echo "==> Step 7: Running pytest"
if [[ $# -eq 0 ]]; then
    pytest
else
    pytest "$@"
fi

echo "==> Done."
