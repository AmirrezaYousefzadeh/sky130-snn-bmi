#!/usr/bin/env bash
# Round 10 (E10), as round 6 (E3b): rerun the OpenLane fill step of an accepted routed run without decap cells and assemble the views
# of the refilled netlist. Placement and routing are untouched (the run restarts from the state before OpenROAD.FillInsertion with
# DECAP_CELL: []); the later checker steps stop the partial run (they need the design LEF of the disabled Magic step), so the
# fill-step netlist, the RCX parasitics and the post-fill STA (SDF, metrics) are copied into <run>_nodecap/final/.
# Usage: refill_nodecap.sh <design dir> <run tag> [used config]     e.g. synthesis/bmi_snn_hw bmi_snn_hw_5m
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; DES="$(cd "$1" && pwd)"; RT="$2"; CFGU="${3:-$DES/config_5mhz_used.yaml}"
export PATH="/nix/var/nix/profiles/default/bin:$PATH"; source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null || true
export PDK_ROOT="${PDK_ROOT:-/media/pdk}"; export PDK="${PDK:-sky130A}"; OL2="${OPENLANE_ROOT:-/media/hardware_design_tools/openlane2}"
RUN="$(cd "$DES/runs/$RT" && pwd -P)"; D=$(python3 -c "import re,sys; print(re.search(r'^DESIGN_NAME:\s*(\S+)', open(sys.argv[1]).read(), re.M).group(1))" "$CFGU")
NEW="${RT}_nodecap"; OUT="$DES/runs/$NEW"
FILL=$(ls -d "$RUN"/*-openroad-fillinsertion | head -1); N=$(basename "$FILL" | cut -d- -f1); PREV=$(ls -d "$RUN"/$(printf "%02d" $((10#$N - 1)))-* | head -1)
[[ -f "$PREV/state_out.json" ]] || { echo "no state before the fill step in $RUN"; exit 1; }
CFG="$DES/config_nodecap.yaml"; grep -vE "^DECAP_CELL:|^# round (6|10)" "$CFGU" > "$CFG"; printf '# round 10 (E10): fill without decap cells (fill-only rerun from the routed state of %s)\nDECAP_CELL: []\n' "$RT" >> "$CFG"
echo "==== refill $D: $RT -> $NEW from $(basename $PREV) ($(date +%H:%M:%S))"; T0=$(date +%s)
rm -rf "$OUT"; cd "$DES"
nix --extra-experimental-features "nix-command flakes" develop --accept-flake-config "$OL2" -c \
  python3 -m openlane --pdk-root "$PDK_ROOT" --pdk "$PDK" --manual-pdk --run-tag "$NEW" --overwrite --from OpenROAD.FillInsertion --with-initial-state "$PREV/state_out.json" "$CFG" > "$ROOT/logs/refill_$NEW.log" 2>&1 || true
F=$(ls -d "$OUT"/*-openroad-fillinsertion 2>/dev/null | head -1); R=$(ls -d "$OUT"/*-openroad-rcx 2>/dev/null | head -1); S=$(ls -d "$OUT"/*-openroad-stapostpnr 2>/dev/null | head -1)
[[ -n "$F" && -f "$F/$D.nl.v" && -n "$R" && -n "$S" ]] || { echo "refill incomplete (fill=$F rcx=$R sta=$S); see logs/refill_$NEW.log"; tail -5 "$ROOT/logs/refill_$NEW.log"; exit 1; }
mkdir -p "$OUT/final/nl" "$OUT/final/pnl" "$OUT/final/spef" "$OUT/final/sdf" "$OUT/final/def"
cp "$F/$D.nl.v" "$OUT/final/nl/"; cp "$F/$D.pnl.v" "$OUT/final/pnl/" 2>/dev/null || true; cp "$F/$D.def" "$OUT/final/def/" 2>/dev/null || true
for c in nom min max; do [[ -d "$R/$c" ]] && { mkdir -p "$OUT/final/spef/$c"; cp "$R/$c"/*.spef "$OUT/final/spef/$c/"; }; done
for c in "$S"/*_*/; do cn=$(basename "$c"); [[ -f "$c/${D}__$cn.sdf" ]] && { mkdir -p "$OUT/final/sdf/$cn"; cp "$c/${D}__$cn.sdf" "$OUT/final/sdf/$cn/"; }; done
# metrics: timing of the refilled netlist (post-fill STA) next to the routing DRC of the original run (routing untouched)
python3 - "$RUN/final/metrics.json" "$S/or_metrics_out.json" "$OUT/final/metrics.json" "$F/or_metrics_out.json" <<'PY'
import json, sys
orig = json.load(open(sys.argv[1])); sta = json.load(open(sys.argv[2])) if __import__("os").path.exists(sys.argv[2]) else {}; fill = json.load(open(sys.argv[4])) if __import__("os").path.exists(sys.argv[4]) else {}
m = dict(orig); m.update({k: v for k, v in sta.items() if k.startswith("timing__") or k.startswith("design__")}); m.update({k: v for k, v in fill.items() if k.startswith("design__")})
m["refill__route_drc_errors_original"] = orig.get("route__drc_errors"); m["refill__note"] = "fill step rerun with DECAP_CELL: []; placement and routing unchanged"
json.dump(m, open(sys.argv[3], "w"), indent=1)
PY
python3 - "$RUN/final/nl/$D.nl.v" "$OUT/final/nl/$D.nl.v" <<'PY'
import re, sys, collections
def cnt(p):
    c = collections.Counter()
    for m in re.finditer(r"^\s*(sky130_fd_sc_\w+__(?:decap|fill|tap|diode)\w*)\s+\S+\s*\(", open(p, errors="ignore").read(), flags=re.M): c[m.group(1).split("__")[1].split("_")[0]] += 1
    return dict(c)
a, b = cnt(sys.argv[1]), cnt(sys.argv[2]); print(f"   physical cells: default fill {a} -> decap-free {b}")
import re as _r
la = len(_r.findall(r"^\s*sky130_fd_sc_\w+__(?!decap|fill|tap|diode)\w+\s+\S+\s*\(", open(sys.argv[1], errors="ignore").read(), flags=_r.M)); lb = len(_r.findall(r"^\s*sky130_fd_sc_\w+__(?!decap|fill|tap|diode)\w+\s+\S+\s*\(", open(sys.argv[2], errors="ignore").read(), flags=_r.M))
print(f"   logic cells: {la} -> {lb} ({'unchanged' if la == lb else 'CHANGED'})")
PY
echo "==== refill $NEW done ($(date +%H:%M:%S), $(( ($(date +%s) - T0) / 60 )) min): $OUT/final/{nl,spef,sdf,metrics.json}"
