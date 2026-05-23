#!/bin/bash
# delete_dead_code.sh — Remove 10 dead engine files from MacroRegime v39
# Run this from the repo root: bash delete_dead_code.sh

echo "========================================="
echo "MacroRegime v39 — Dead Code Deletion"
echo "========================================="
echo ""

DEAD_FILES=(
    "engines/playbook_engine.py"
    "engines/signal_decay_engine.py"
    "engines/regime_predictor_engine.py"
    "engines/reflexivity_coefficient.py"
    "engines/cri_v2_engine.py"
    "engines/duration_hmm_engine.py"
    "engines/bayesian_fusion_engine.py"
    "engines/defillama_api.py"
    "engines/trend_signal_engine.py"
    "engines/greeks_proxy_vanna_charm_EXTENSION.py"
)

TOTAL_LINES=0

for f in "${DEAD_FILES[@]}"; do
    if [ -f "$f" ]; then
        LINES=$(wc -l < "$f")
        TOTAL_LINES=$((TOTAL_LINES + LINES))
        echo "DELETING: $f ($LINES lines)"
        rm "$f"
    else
        echo "ALREADY GONE: $f"
    fi
done

echo ""
echo "========================================="
echo "Deleted $TOTAL_LINES lines of dead code"
echo "Remaining engines: $(ls engines/*.py 2>/dev/null | wc -l) files"
echo "========================================="
