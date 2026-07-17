#!/usr/bin/env bash
# =============================================================================
# run_tests.sh – DER Standard-Testlauf: ALLE Suiten (RAG + CAD) in EINEM Befehl.
#
# Hintergrund: Die CAD-Suite (cad_processor/tests/, braucht das Conda-Env
# gear-copilot/PythonOCC) wird von `pytest tests/` NICHT mit eingesammelt.
# Dadurch war ein Bestandstest lange unbemerkt rot. Dieses Skript macht das
# Vergessen unmöglich: Es führt beide Suiten in ihren jeweiligen Containern
# aus und schlägt fehl, sobald IRGENDEINE Suite fehlschlägt.
#
# Aufruf:            ./run_tests.sh
# Mit Live-E2E-Test: ./run_tests.sh --live      (braucht laufenden Stack + Ollama;
#                    ohne Flag wird der Live-Test sichtbar als "skipped" gezählt)
# Mit Accuracy-Lauf: ./run_tests.sh --accuracy  (misst die CAD-Erkennung gegen die
#                    28 McMaster-Carr-Ground-Truth-Teile + Kronenrad; die STEP-Dateien
#                    müssen unter cad_processor/data/examples/ liegen — Dateinamen
#                    exakt wie die Keys in cad_processor/tests/ground_truth.json.
#                    Dauer ~10 min, braucht den laufenden cad_processor-Container.)
# =============================================================================
set -u
cd "$(dirname "$0")"

LIVE_ENV=()
RUN_ACCURACY=0
for arg in "$@"; do
    case "$arg" in
        --live)     LIVE_ENV=(-e "E2E_BASE_URL=http://app:8000") ;;
        --accuracy) RUN_ACCURACY=1 ;;
    esac
done

fail=0

echo "════════════════════════════════════════════════════════════"
echo " Suite 1/2: RAG-System (app-Container, tests/)"
echo "════════════════════════════════════════════════════════════"
docker compose run --rm --no-deps -T ${LIVE_ENV[@]+"${LIVE_ENV[@]}"} \
    -v "$PWD/tests:/app/tests" \
    app python -m pytest tests/ -q || fail=1

echo
echo "════════════════════════════════════════════════════════════"
echo " Suite 2/2: CAD-Prozessor (cad_processor-Container, conda gear-copilot)"
echo "════════════════════════════════════════════════════════════"
# --entrypoint überschreibt das uvicorn-ENTRYPOINT des Service-Images.
docker compose run --rm --no-deps -T \
    -v "$PWD/cad_processor/tests:/app/tests" \
    --entrypoint /opt/conda/envs/gear-copilot/bin/python \
    cad_processor -m pytest /app/tests/test_geometry.py -q || fail=1

if [[ $RUN_ACCURACY -eq 1 ]]; then
    echo
    echo "════════════════════════════════════════════════════════════"
    echo " Accuracy-Lauf: CAD-Erkennung vs. Ground Truth (~10 min)"
    echo "════════════════════════════════════════════════════════════"
    CAD_CONTAINER="$(docker compose ps -q cad_processor)"
    if [[ -z "$CAD_CONTAINER" ]]; then
        echo "❌ cad_processor-Container läuft nicht (docker compose up -d cad_processor)."
        fail=1
    elif [[ ! -d cad_processor/data/examples ]] || \
         [[ "$(find cad_processor/data/examples -iname '*.st*' | wc -l)" -lt 2 ]]; then
        echo "❌ Ground-Truth-STEP-Dateien fehlen unter cad_processor/data/examples/"
        echo "   (Dateinamen = Keys aus cad_processor/tests/ground_truth.json)."
        fail=1
    else
        docker compose exec -T cad_processor sh -c 'rm -rf /app/data/examples /tmp/acc_tests && mkdir -p /app/data/examples'
        docker cp -q cad_processor/data/examples/. "$CAD_CONTAINER":/app/data/examples/
        docker cp -q cad_processor/tests "$CAD_CONTAINER":/tmp/acc_tests
        docker compose exec -T -w /app cad_processor /opt/conda/envs/gear-copilot/bin/python \
            /tmp/acc_tests/accuracy_test.py --step-dir data/examples || fail=1
    fi
fi

echo
if [[ $fail -eq 0 ]]; then
    echo "✅ ALLE Suiten grün."
else
    echo "❌ MINDESTENS EINE Suite ist fehlgeschlagen."
fi
exit $fail
