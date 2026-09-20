#!/usr/bin/env python3
"""Round 5 (E1/E5): summarise the utilization-policy attempts of every design and kit from logs/policy_round5.log (OpenLane,
sky130 and GF180) and logs/orfs5_policy.log (OpenROAD-flow-scripts kits) into results/POLICY5.md: one row per attempt
(utilization, outcome, runtime, reason) and one table of the accepted utilizations. Stray lines are ignored."""
import re, json, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
att = collections.OrderedDict()          # (kit, design) -> list of attempts
def add(kit, design, util, outcome, tag, runtime, reason):
    att.setdefault((kit, design), []).append(dict(util=int(util), outcome=outcome, tag=tag, runtime_min=int(runtime) if runtime else None, reason=reason))
for line in (ROOT / "logs/policy_round5.log").read_text().splitlines():
    m = re.match(r"^(?:(pdk_gf180)/)?(bmi_\w+?) (ACCEPTED|REJECTED|LOWV) util=(\d+) tag=(\S+) runtime=(\d+)min(.*)$", line)
    if not m: continue
    pdk, d, out, u, tag, rt, rest = m.groups(); kit = "gf180" if pdk else "sky130"
    reason = ""
    for k in ("watchdog", "killed"):
        mm = re.search(k + r'="([^"]*)"', rest)
        if mm: reason = f"{k}: {mm.group(1)}"
    if not reason and out == "REJECTED":
        mm = re.search(r"drc=(\S+) pass=(\d)", rest)
        if mm: reason = "DRC violations" if mm.group(1) not in ("0", "NA") else ("timing/hold failure" if mm.group(2) == "0" else "")
    if out == "LOWV": out = "ACCEPTED (1.28 V signoff)" if "pass=1" in rest else "REJECTED (1.28 V signoff)"
    add(kit, d, u, out, tag, rt, reason)
for line in (ROOT / "logs/orfs5_policy.log").read_text().splitlines():
    m = re.match(r"^(\S+) (rvt|sram) (bmi_\w+) (ACCEPTED|REJECTED) util=(\d+) nick=(\S+) runtime=(\d+)min(.*)$", line)
    if not m: continue
    plat, flav, d, out, u, tag, rt, rest = m.groups(); kit = {"nangate45": "nangate45", "ihp-sg13g2": "ihp", "asap7": "asap7" + ("sram" if flav == "sram" else "")}[plat]
    reason = ""
    if out == "REJECTED":
        mm = re.search(r"rc=(\S+) drc=(\S+) setup=(\S+) hold=(\S+)", rest)
        if mm:
            rc, drc, s, h = mm.groups()
            reason = "flow exit / route did not finish" if drc == "NA" else ("DRC violations" if drc != "0" else ("setup failure" if s != "NA" and float(s) < 0 else "hold failure"))
    add(kit, d, u, out, tag, rt, reason)
KITN = {"sky130": "SkyWater sky130 (OpenLane)", "gf180": "GF180MCU (OpenLane)", "nangate45": "NanGate45 (ORFS)", "ihp": "IHP SG13G2 (ORFS)", "asap7": "ASAP7 RVT (ORFS)", "asap7sram": "ASAP7 SRAM-Vt (ORFS)"}
out = ["# Utilization policy, round 5: every attempt (from logs/policy_round5.log and logs/orfs5_policy.log)", "",
       "Policy: start at 60 % core utilization (placement density = utilization + 10 %), step down by 10 % until the run is DRC-clean and meets timing at every signoff corner. A watchdog aborts detailed routing that cannot converge (> 20 k violations after 3 iterations, > 3 k after 8, or no completed iteration for 3 h). Reruns with a hold-repair margin carry the suffix `h`; `lv` marks the 1.28 V signoff (E14).", "",
       "## Accepted utilizations", "", "| kit | design | accepted util % | attempts (util: outcome) | total runtime (h) |", "|---|---|---|---|---|"]
summary = {}
for (kit, d), L in att.items():
    acc = [a for a in L if a["outcome"].startswith("ACCEPTED")]
    accu = ", ".join(f"{a['util']}{' (1.28 V)' if '1.28' in a['outcome'] else ''}{'h' if a['tag'].endswith('h') else ''}" for a in acc) or "none"
    seq = "; ".join(f"{a['util']}{'h' if a['tag'].endswith('h') else ''}{' lv' if 'lv' in a['tag'] else ''}: {'ok' if a['outcome'].startswith('ACCEPTED') else 'x'}" for a in L)
    tot = sum(a["runtime_min"] or 0 for a in L) / 60
    out.append(f"| {KITN.get(kit, kit)} | {d} | {accu} | {seq} | {tot:.1f} |")
    summary[f"{kit}/{d}"] = dict(accepted=[a["util"] for a in acc], attempts=L)
out += ["", "## Every attempt", "", "| kit | design | util % | outcome | runtime (min) | reason / note | run tag |", "|---|---|---|---|---|---|---|"]
for (kit, d), L in att.items():
    for a in L: out.append(f"| {KITN.get(kit, kit)} | {d} | {a['util']} | {a['outcome']} | {a['runtime_min']} | {a['reason']} | `{a['tag']}` |")
(ROOT / "results/POLICY5.md").write_text("\n".join(out) + "\n")
json.dump(summary, open(ROOT / "results/policy5.json", "w"), indent=1)
n_acc = sum(1 for v in summary.values() if v["accepted"]); print(f"wrote results/POLICY5.md: {len(att)} kit/design pairs, {n_acc} with an accepted run, {sum(len(v['attempts']) for v in summary.values())} attempts")
