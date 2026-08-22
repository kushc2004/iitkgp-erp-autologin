#!/bin/zsh

set -u
cd -- "${0:A:h}"

PYTHON="${PWD}/venv/bin/python"
SCRIPT="${PWD}/open_erp.py"

if [[ ! -x "${PYTHON}" ]]; then
  print -u2 "ERP launcher error: virtualenv Python not found at ${PYTHON}"
  print -u2 "Run the setup steps from the README first."
  read -k 1 "?Press any key to close..."
  exit 1
fi

"${PYTHON}" "${SCRIPT}"
exit_code=$?

if (( exit_code != 0 )); then
  print -u2 "ERP login exited with status ${exit_code}."
  read -k 1 "?Press any key to close..."
fi

exit ${exit_code}
