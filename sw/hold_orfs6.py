#!/usr/bin/env python3
"""Round 6 (E7): worst hold (and setup) slack of every routed flow-scripts netlist at every corner the platform provides
(typical, slow, fast where available), OpenSTA with the SPEF and a propagated 200 ns clock. Writes results/hold6.json
{kit/core: {corner: {hold_ws_ns, setup_ws_ns, libs}}} and prints a table. Run inside the OpenLane nix shell (it calls `sta`)."""
import os, json, subprocess, glob, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; ORFS = "/media/pdk/OpenROAD-flow-scripts/flow"
def a7(fl, c): return sorted(glob.glob(f"{ORFS}/platforms/asap7/lib/NLDM/asap7sc7p5t_*_{fl}_{c}_nldm_*.lib*"))
KITS = {
 "nangate45": dict(plat="nangate45", tu=1.0, corners={"typical": [f"{ORFS}/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib"]}),
 "ihp":       dict(plat="ihp-sg13g2", tu=1.0, corners={c: [f"{ORFS}/platforms/ihp-sg13g2/lib/sg13g2_stdcell_{c}.lib"] for c in ("typ_1p20V_25C", "slow_1p08V_125C", "fast_1p32V_m40C")}),
 "asap7":     dict(plat="asap7", tu=1e-3, corners={c: a7("RVT", c) for c in ("TT", "SS", "FF")}),
 "asap7sram": dict(plat="asap7", tu=1e-3, corners={c: a7("SRAM", c) for c in ("TT", "SS", "FF")}, sfx="_sram"),
}
CORES = ["sp", "m12", "min32", "min16", "lmin2", "g32p50"]   # g32p50 added in round 6 (E4c)
out = {}
for kit, K in KITS.items():
    for c in CORES:
        nick = f"bmi_snn_{c}_5m{K.get('sfx','')}"; run = f"{ORFS}/results/{K['plat']}/{nick}/base"
        nl, spef = f"{run}/6_final.v", f"{run}/6_final.spef"
        if not os.path.exists(nl): continue
        res = {}
        for corner, libs in K["corners"].items():
            if not libs: continue
            oj = ROOT / f"results/explore/hold6_{kit}_{c}_{corner}.json"; oj.parent.mkdir(exist_ok=True)
            env = dict(os.environ, LIB_SC=" ".join(libs), NETLIST=nl, TOP=f"bmi_snn_{c}", SPEF=spef, PERIOD_NS=str(200.0 / K["tu"]), OUT=str(oj))
            import shutil
            OL2 = os.environ.get("OPENLANE_ROOT", "/media/hardware_design_tools/openlane2")
            cmd = ["sta", "-no_splash", "-exit", str(ROOT / "power/hold_sta.tcl")] if shutil.which("sta") else \
                  ["nix", "--extra-experimental-features", "nix-command flakes", "develop", "--accept-flake-config", OL2, "-c", "sta", "-no_splash", "-exit", str(ROOT / "power/hold_sta.tcl")]   # OpenSTA of the OpenLane 2 environment when not on PATH
            r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
            import re
            ws = re.findall(r"worst slack\s+(-?[\d.]+)", r.stdout)   # OpenSTA prints "worst slack <v>" for -min first, then for -max
            if len(ws) >= 2:
                res[corner] = dict(hold_ws_ns=float(ws[0]) * K["tu"], setup_ws_ns=float(ws[1]) * K["tu"], libs=[os.path.basename(l) for l in libs])
                (ROOT / f"results/explore/hold6_{kit}_{c}_{corner}.log").write_text(r.stdout)
                print(f"{kit:10s} {c:6s} {corner:16s} hold {res[corner]['hold_ws_ns']:8.3f} ns  setup {res[corner]['setup_ws_ns']:8.2f} ns", flush=True)
            else:
                print(f"{kit:10s} {c:6s} {corner:16s} FAILED: {(r.stderr.strip() or r.stdout.strip()).splitlines()[-1:]}", flush=True)
        if res:
            res["worst_hold_ws_ns"] = min(v["hold_ws_ns"] for k, v in res.items() if isinstance(v, dict)); res["worst_hold_corner"] = min(((v["hold_ws_ns"], k) for k, v in res.items() if isinstance(v, dict)))[1]
            out[f"{kit}/{c}"] = res
json.dump(out, open(ROOT / "results/hold6.json", "w"), indent=1); print("wrote results/hold6.json", len(out), "kit/core pairs")
