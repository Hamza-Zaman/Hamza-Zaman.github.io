#!/usr/bin/env bash
# =============================================================================
# run_edgartools_eval.sh
# =============================================================================
# Companion script for test_edgartools_full.py
#
# Sets up the Python environment, installs dependencies, runs the
# comprehensive edgartools evaluation, and saves structured JSON results.
#
# Usage:
#   chmod +x run_edgartools_eval.sh
#   ./run_edgartools_eval.sh
#
# The script will:
#   1. Detect or create a Python virtual environment
#   2. Install edgartools (and dependencies) if not present
#   3. Run the evaluation test
#   4. Copy the JSON results to a timestamped file
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
PYTHON_SCRIPT="${SCRIPT_DIR}/test_edgartools_full.py"
RESULTS_FILE="${SCRIPT_DIR}/results_edgartools_full.json"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
RESULTS_ARCHIVE="${SCRIPT_DIR}/results_edgartools_full_${TIMESTAMP}.json"
LOG_FILE="${SCRIPT_DIR}/eval_edgartools_${TIMESTAMP}.log"

echo "============================================================"
echo "  edgartools Comprehensive Evaluation Runner"
echo "  $(date)"
echo "============================================================"

# ------------------------------------------------------------------
# Step 1: Ensure Python 3.9+ is available
# ------------------------------------------------------------------
echo ""
echo "[1/5] Checking Python version..."

PYTHON_CMD=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
            PYTHON_CMD="$candidate"
            echo "  Found: $candidate (v${version})"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "  [ERROR] Python 3.9+ is required but not found."
    echo "  Please install Python 3.9 or later and try again."
    exit 1
fi

# ------------------------------------------------------------------
# Step 2: Create/activate virtual environment
# ------------------------------------------------------------------
echo ""
echo "[2/5] Setting up virtual environment..."

if [ ! -d "$VENV_DIR" ]; then
    echo "  Creating virtual environment at ${VENV_DIR}..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    echo "  Virtual environment created."
else
    echo "  Using existing virtual environment at ${VENV_DIR}."
fi

# Activate
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
echo "  Activated: $(which python)"

# ------------------------------------------------------------------
# Step 3: Install dependencies
# ------------------------------------------------------------------
echo ""
echo "[3/5] Installing dependencies..."

pip install --quiet --upgrade pip

# Install edgartools and any extras
if python -c "import edgar" &>/dev/null; then
    echo "  edgartools is already installed."
    INSTALLED_VERSION=$(python -c "import importlib.metadata; print(importlib.metadata.version('edgartools'))" 2>/dev/null || echo "unknown")
    echo "  Installed version: ${INSTALLED_VERSION}"
else
    echo "  Installing edgartools..."
    pip install --quiet edgartools
    echo "  edgartools installed."
fi

# Ensure we have all needed standard-lib-compatible deps
pip install --quiet requests 2>/dev/null || true

# ------------------------------------------------------------------
# Step 4: Run the evaluation
# ------------------------------------------------------------------
echo ""
echo "[4/5] Running evaluation..."
echo "  Script: ${PYTHON_SCRIPT}"
echo "  Log:    ${LOG_FILE}"
echo "  This may take several minutes (SEC rate limits apply)."
echo ""

# Run and tee output to both console and log file
python "$PYTHON_SCRIPT" 2>&1 | tee "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}

if [ "$EXIT_CODE" -ne 0 ]; then
    echo ""
    echo "  [WARN] Script exited with code ${EXIT_CODE}."
    echo "         Check the log file for details: ${LOG_FILE}"
fi

# ------------------------------------------------------------------
# Step 5: Archive results
# ------------------------------------------------------------------
echo ""
echo "[5/5] Archiving results..."

if [ -f "$RESULTS_FILE" ]; then
    cp "$RESULTS_FILE" "$RESULTS_ARCHIVE"
    echo "  Results saved to:"
    echo "    Primary:  ${RESULTS_FILE}"
    echo "    Archive:  ${RESULTS_ARCHIVE}"
    echo "    Log:      ${LOG_FILE}"

    # Print a quick summary from the JSON
    echo ""
    echo "--- Quick Summary ---"
    python -c "
import json, sys
with open('${RESULTS_FILE}') as f:
    data = json.load(f)
s = data.get('summary', {})
print(f\"  Tests:     {s.get('total_tests', '?')}\")
print(f\"  Passed:    {s.get('passed', '?')}\")
print(f\"  Failed:    {s.get('failed', '?')}\")
print(f\"  Pass rate: {s.get('pass_rate', '?')}\")
print(f\"  Runtime:   {data.get('total_runtime_seconds', '?')}s\")
" 2>/dev/null || echo "  (Could not parse results JSON)"

else
    echo "  [WARN] Results file not found at ${RESULTS_FILE}."
    echo "         The evaluation may not have completed successfully."
fi

echo ""
echo "============================================================"
echo "  Evaluation complete."
echo "============================================================"

exit ${EXIT_CODE:-0}
