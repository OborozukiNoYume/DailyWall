#!/usr/bin/env bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
LOG_FILE="${LOG_DIR}/systemd-crawl.log"
RUN_LABEL="${1:-systemd}"

mkdir -p "${LOG_DIR}"

cd "${ROOT_DIR}" || exit 1

echo "[$(date --iso-8601=seconds)] ${RUN_LABEL} crawl start" >> "${LOG_FILE}"
"${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/scripts/crawl.py" >> "${LOG_FILE}" 2>&1
code=$?
echo "[$(date --iso-8601=seconds)] ${RUN_LABEL} crawl exit=${code}" >> "${LOG_FILE}"

exit "${code}"
