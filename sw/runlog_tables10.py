#!/usr/bin/env python3
"""Round 10: markdown tables for results/run_log_round10.md from results/round10.json, the policy log and the hardening metrics:
hardening records (E1-E5 and every core measured), decap-free refill records (E10), wall-clock of every annotated run, headline
ratios round 7 vs round 10. Usage: runlog_tables10.py [section ...]  (sections: hardening refill wallclock ratios; default all)"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); from fmt3 import sig
ROOT = Path(__file__).resolve().parent.parent; R = json.load(open(ROOT / "results/round10.json")); D = json.load(open(ROOT / "results/designs.json"))
def f(x, nd=3): return "--" if x is None else sig(x, nd)
def pct(x): return "--" if x is None else f"{x:+.1f} %"
POL = (ROOT / "logs/policy_round5.log").read_text(errors="ignore") if (ROOT / "logs/policy_round5.log").exists() else ""
def policy_history(design):
    """utilizations tried by harden_policy2.sh for <design>, in order, with the verdicts"""
    h = []
    for m in re.finditer(rf"^{re.escape(design)} (ACCEPTED|REJECTED|REJECTED-BY-OS)\s+util=(\d+)\s+tag=(\S+)(.*)$", POL, flags=re.M):
        h.append(f"{m.group(2)} % {m.group(1).lower()}" + (f" ({m.group(4).strip()[:60]})" if m.group(1) != "ACCEPTED" and m.group(4).strip() else ""))
    return "; ".join(h)
def hardening():
    L = ["| core | spec | run tag | utilization target | cells | area (mm^2) | setup slack worst corner (ns) | hold slack worst corner (ns) | route DRC | policy history |", "|---|---|---|---|---|---|---|---|---|---|"]
    new = {"bmi_snn_hwg": "E4: hardwired dense 20/24, gated", "bmi_snn_scmemg": "E2: register-file memory 20/24, gated", "bmi_snn_lmem2g": "E3: latch memory 20/24, gated", "bmi_snn_min32g": "E5: H = 32 dense 16/16, gated",
           "bmi_snn_g32": "E5: H = 32 dense 12/14, gated (grid point)", "bmi_snn_g16": "E5: H = 16 dense 12/14, gated (grid point)", "bmi_snn_topg": "E1: SRAM core, gated (round 7 netlist; dense mode = simulation only)"}
    seen = set()
    for r in R["table2"] + R["grid"]:
        d = r.get("design"); 
        if not d or d in seen or not d.startswith("bmi_snn_"): continue
        seen.add(d); rd = ROOT / f"synthesis/{d}/runs/{d}_5m"; tag = rd.resolve().name if rd.exists() else "(pending)"
        mj = rd / "final/metrics.json"; m = json.load(open(mj)) if mj.exists() else {}
        if r.get("util_pct") is None:                                   # round-5 designs without FP_CORE_UTIL in the used config: from the run tag (_u60)
            mu = re.search(r"_u(\d+)", tag); r = dict(r, util_pct=int(mu.group(1)) if mu else None)
        # worst setup/hold over the corners: metrics timing__setup__ws / timing__hold__ws are the worst over all corners of the run
        L.append(f"| {d} | {new.get(d, 'round 5-7 netlist')} | {tag} | {f(r.get('util_pct'), 2)} % | {r.get('cells') or '--'} | {f(r.get('area_mm2'), 4)} | {f(m.get('timing__setup__ws'), 4)} | {f(m.get('timing__hold__ws'), 4)} | {m.get('route__drc_errors', '--')} | {policy_history(d) or '--'} |")
    return "\n".join(L)
def refill():
    L = ["| design | run | route DRC (original / refill) | cells (default / decap-free) | decap cells | P_leak default (uW) | P_leak decap-free (uW) | leakage by class default: logic / fill / decap / tap (uW) | decap-free: logic / fill / decap / tap (uW) | P_dyn default / decap-free (uW) | E_bin default / decap-free (nJ) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in R["table2"] + R["grid"]:
        if r.get("nd_p_leak_uW") is None: continue
        L.append(f"| {r.get('design')} | {r.get('run_kind', 'sdf')}{' dense' if r.get('dense') else ''} w{r.get('window_bins')} | {r.get('refill_drc', '--')} / {r.get('refill_drc', '--')} | {r.get('cells') or '--'} / {r.get('refill_cells') or '--'} | {r.get('n_decap') or '--'} -> {r.get('nd_n_decap') or '--'} | {f(r.get('p_leak_uW'), 4)} | {f(r.get('nd_p_leak_uW'), 4)} | {f(r.get('leak_logic_uW'), 4)} / {f(r.get('leak_fill_uW'), 2)} / {f(r.get('leak_decap_uW'), 4)} / {f(r.get('leak_tap_uW'), 2)} | {f(r.get('nd_leak_logic_uW'), 4)} / {f(r.get('nd_leak_fill_uW'), 2)} / {f(r.get('nd_leak_decap_uW'), 4)} / {f(r.get('nd_leak_tap_uW'), 2)} | {f(r.get('p_dyn_uW'), 4)} / {f(r.get('nd_p_dyn_uW'), 4)} | {f(r.get('e_bin_nJ'), 4)} / {f(r.get('nd_e_bin_nJ'), 4)} |")
    return "\n".join(L)
def wallclock():
    L = ["| run | model | bins | cells | clock cycles in window | simulation wall-clock (min) | pins annotated |", "|---|---|---|---|---|---|---|"]
    for r in R["table2"] + R["table3"] + R["grid"]:
        t = r.get("tag")
        if not t or r.get("sim_wallclock_min") is None: continue
        L.append(f"| {t} | {r.get('run_kind') or ('func' if '_func_' in t else 'sdf')} | {r.get('window_bins') or r.get('bins')} | {r.get('cells') or '--'} | {r.get('clk_cycles') or '--'} | {f(r.get('sim_wallclock_min'), 3)} | {f((r.get('pins_annotated_frac') or 0) * 100, 4)} % |")
    return "\n".join(L)
def ratios():
    t2 = {r["key"]: r for r in R["table2"] if r.get("role") == "table" and r.get("status") == "ok"}
    def old_p(key):
        r = t2.get(key); return (r or {}).get("p_old_uW")
    L = ["| ratio | round 7 (sum of active-window energy x 250/s and leakage) | round 10 (real-time window) | round 10 with the state corrections |", "|---|---|---|---|"]
    pairs = [("SoC / pruned core", "soc_tuned", "sp"), ("SoC / 12-bit hardwired", "soc_tuned", "m12"), ("SRAM core, event mode / pruned core", "topg_event", "sp"), ("SRAM core, dense / event", "topg_dense", "topg_event"),
             ("register file / latch memory", "scmemg", "lmem2g"), ("latch 20-bit / latch 12-bit", "lmem2g", "lmin2"), ("hardwired 20-bit / 12-bit", "hwg", "m12"), ("12-bit dense / pruned core", "m12", "sp"), ("H = 64 / H = 32 (12-bit, gated)", "m12", "g32"), ("pruned core / front end", "sp", "fe")]
    for lab, a, b in pairs:
        ra, rb = t2.get(a), t2.get(b)
        if not ra or not rb: L.append(f"| {lab} | -- | -- | -- |"); continue
        o = (old_p(a) / old_p(b)) if (old_p(a) and old_p(b)) else None; n = ra["p_avg_uW"] / rb["p_avg_uW"]
        sa = ra.get("p_avg_mc_uW") or ra.get("p_avg_cond_uW") or ra["p_avg_uW"]; sb = rb.get("p_avg_mc_uW") or rb.get("p_avg_cond_uW") or rb["p_avg_uW"]
        L.append(f"| {lab} | {f(o, 3)} | {f(n, 3)} | {f(sa / sb, 3)} |")
    return "\n".join(L)
secs = sys.argv[1:] or ["hardening", "refill", "wallclock", "ratios"]
for sname in secs:
    print({"hardening": "### Hardening records\n\n", "refill": "### Decap-free refill records (E10)\n\n", "wallclock": "### Wall-clock of the annotated runs\n\n", "ratios": "### Headline ratios, round 7 vs round 10\n\n"}[sname] + globals()[sname]() + "\n")
