#!/usr/bin/env bash
# Format edited Python files with autopep8 and run unit tests.
set -euo pipefail

input=$(cat)

file_path=$(python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('file_path') or data.get('path') or '')
" <<< "$input")

if [[ -z "$file_path" || "$file_path" != *.py ]]; then
  exit 0
fi

if [[ ! -f "$file_path" ]]; then
  exit 0
fi

if [[ -d .venv/bin ]]; then
  PYTHON=".venv/bin/python"
elif [[ -d .venv/Scripts ]]; then
  PYTHON=".venv/Scripts/python.exe"
else
  PYTHON="python3"
fi

"$PYTHON" -m autopep8 --in-place "$file_path" 2>/dev/null || true

test_output=$("$PYTHON" -m unittest test_run -v 2>&1) || test_status=$?
test_status=${test_status:-0}

if [[ "$test_status" -ne 0 ]]; then
  FILE_PATH="$file_path" TEST_OUTPUT="$test_output" python3 << 'PY'
import json, os
msg = f"Unit tests failed after editing {os.environ['FILE_PATH']}:\n{os.environ['TEST_OUTPUT']}"
print(json.dumps({"additional_context": msg[:4000]}))
PY
fi

exit 0
