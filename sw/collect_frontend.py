#!/usr/bin/env python3
"""Round 5 (E10) / round 6 (E6): figures of the digital front end (rtl/bmi_fe.v, v3 with the held tick) -> paper/numbers_frontend.tex, results/frontend.json.
Round 6 adds the front end + core co-simulation (sim/measure_sys.sh: power/out_vcd_sys_sp_gls_5m) and keeps the v2 figures as reference.
Sources: synthesis/bmi_fe/runs/bmi_fe_5m/final/metrics.json (hardening), sim/build_fe_gls/vvp.log (500-bin gate-level run, real time),
power/out_vcd_fe_5m_gls (per-pin power with the oscillator-gated clock taken from the waveform), power/out_vcd_fe_v1_gls_5m (v1,
free-running 5 MHz clock), results/designs.json (cores, for the combined figures)."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_results import parse_group_table, RATE
ROOT = Path(__file__).resolve().parent.parent
from fmt3 import sig as _sig
def _f(x, nd=3): return _sig(x, nd)   # round 7
out = {}
m = json.load(open(ROOT / "synthesis/bmi_fe/runs/bmi_fe_5m/final/metrics.json"))
out["pnr"] = {"cells": m.get("design__instance__count__stdcell"), "area_um2": m.get("design__instance__area"), "setup_ws_ns": m.get("timing__setup__ws"),
              "hold_ws_ns": m.get("timing__hold__ws"), "drc": m.get("route__drc_errors"), "util": m.get("design__instance__utilization")}
cu = (ROOT / "synthesis/bmi_fe/config_5mhz_used.yaml").read_text() if (ROOT / "synthesis/bmi_fe/config_5mhz_used.yaml").exists() else ""
mu = re.search(r"^FP_CORE_UTIL:\s*(\d+)", cu, flags=re.M); out["pnr"]["util_target_pct"] = int(mu.group(1)) if mu else None
log = (ROOT / "sim/build_fe_gls/vvp.log").read_text()
s = re.search(r"SUMMARY: bins=(\d+) events=(\d+) recorded=(\d+) ticks=(\d+) errors=(\d+) clk5_cycles=(\d+) core_clk_cycles=(\d+) slow_cycles=(\d+) osc_on_cycles=(\d+)", log)
tb = dict(zip(["bins", "events", "recorded", "ticks", "errors", "clk5_cycles", "core_clk_cycles", "slow_cycles", "osc_on_cycles"], map(int, s.groups())))
tb["pass"] = "PASS" in log; out["tb"] = tb
T_bin = 131 / 32768.0                                   # s per bin (131 slow cycles)
out["osc_duty"] = tb["osc_on_cycles"] * 200e-9 / (tb["bins"] * T_bin); out["osc_us_per_bin"] = tb["clk5_cycles"] / tb["bins"] * 0.2
out["core_clk_per_bin"] = tb["core_clk_cycles"] / tb["bins"]
def power(d):
    g = parse_group_table(ROOT / d / "power_vcd.rpt"); t = g["Total"]
    r = {"total_uW": t["total"] * 1e6, "leakage_uW": t["leakage"] * 1e6, "internal_uW": t["internal"] * 1e6, "switching_uW": t["switching"] * 1e6}
    for k in ("Sequential", "Combinational", "Clock"): r[k.lower() + "_uW"] = g[k]["total"] * 1e6
    return r
# OpenSTA gives every pin of the root clock network (clock port to the first clock gate) the activity of the clock definition,
# although the oscillator runs for 3 % of the time; power/root_clock_correction.py scales the clock-driven dynamic power of those
# cells (4 clock buffers, the clock gate's clock pin, 5 flip-flops) by the measured oscillator duty (see the run log). Downstream of
# the clock gate the annotated activity is used by OpenSTA itself.
FE_RUN = "power/out_vcd_fe_v3_gls_5m" if (ROOT / "power/out_vcd_fe_v3_gls_5m/root_clock_correction.json").exists() else "power/out_vcd_fe_v2_gls_5m"   # round 6: v3
out["fe_version"] = "v3" if "v3" in FE_RUN else "v2"
rep = power(FE_RUN); out["power_reported"] = rep; out["power_v1_freerunning"] = power("power/out_vcd_fe_v1_gls_5m")
rc = json.load(open(ROOT / FE_RUN / "root_clock_correction.json")); out["root_clock_correction"] = rc
if (ROOT / "power/out_vcd_fe_v2_gls_5m/root_clock_correction.json").exists():
    c2 = json.load(open(ROOT / "power/out_vcd_fe_v2_gls_5m/root_clock_correction.json"))["corrected"]["Total"]; out["power_v2_total_uW"] = c2["total"] * 1e6
c = rc["corrected"]; cor = {"total_uW": c["Total"]["total"] * 1e6, "leakage_uW": c["Total"]["leakage"] * 1e6, "internal_uW": c["Total"]["internal"] * 1e6, "switching_uW": c["Total"]["switching"] * 1e6}
for k in ("Sequential", "Combinational", "Clock"): cor[k.lower() + "_uW"] = c.get(k, {}).get("total", 0) * 1e6
out["power"] = cor
# domain split from the instance report: clock buffers of each domain, the clock gate, sequential cells by clock net is not in the report;
# report the clock-tree power of each domain instead
dom = {"clk32k": 0.0, "clk5": 0.0, "icg": 0.0}
for line in open(ROOT / FE_RUN / "power_vcd_by_instance.rpt"):
    f = line.split()
    if len(f) < 5: continue
    try: tot = float(f[3])
    except ValueError: continue
    n = f[4]
    if "clk5" in n and "clkbuf" in n: dom["clk5"] += tot * 1e6 * out["osc_duty"]      # clk5 clock tree at the measured oscillator duty
    elif n == "u_icg": dom["icg"] += tot * 1e6 * out["osc_duty"]
for line in open(ROOT / FE_RUN / "power_vcd_by_instance.rpt"):
    f = line.split()
    if len(f) < 5: continue
    try: tot = float(f[3])
    except ValueError: continue
    if "clk32k" in f[4] and "clkbuf" in f[4]: dom["clk32k"] += tot * 1e6
out["clock_tree_uW"] = dom
D = json.load(open(ROOT / "results/designs.json"))
comb = {}
for core, sh in (("bmi_snn_sp", "Sp"), ("bmi_snn_lmin2", "LmMinP"), ("bmi_snn_m12", "MinT"), ("bmi_snn_min32", "MinH")):
    d = D.get(core, {})
    if not d.get("event") or not d.get("idle"): continue
    e = d.get("event_sdf", d["event"])["energy_per_bin_nJ"]; leak = d["idle"]["leakage_uW"]
    pc = e * RATE * 1e-3 + leak; comb[sh] = {"core_uW": pc, "frontend_uW": out["power"]["total_uW"], "total_uW": pc + out["power"]["total_uW"], "frontend_share": out["power"]["total_uW"] / (pc + out["power"]["total_uW"])}
out["combined_250Hz"] = comb
# ---- round 6 (E6): front end + core co-simulated over the routed netlists (sim/measure_sys.sh), 500 bins in real time;
#      round 7 (fix 7): also the gated 12-bit latch core (CORE=lmin2, weights loaded through the write port before the power window)
SYS_CORES = (("sp", "Sp", "bmi_snn_sp"), ("lmin2", "LmMinP", "bmi_snn_lmin2"))
out["system_cosim"] = {}; sysd = None
for core, csh, dname in SYS_CORES:
    SYS = ROOT / f"power/out_vcd_sys_{core}_gls_5m"
    if not (SYS / "root_clock_correction.json").exists(): continue
    slog = (ROOT / f"sim/build_sys_{core}_gls_5m/vvp.log").read_text()
    ss = re.search(r"SUMMARY: bins=(\d+) events=(\d+) recorded=(\d+) ticks=(\d+) errors=(\d+) out_bins=(\d+) out_errors=(\d+) clk5_cycles=(\d+) core_clk_cycles=(\d+) slow_cycles=(\d+) osc_on_cycles=(\d+)", slog)
    stb = dict(zip(["bins", "events", "recorded", "ticks", "errors", "out_bins", "out_errors", "clk5_cycles", "core_clk_cycles", "slow_cycles", "osc_on_cycles"], map(int, ss.groups()))); stb["pass"] = "PASS" in slog
    inst = {}
    for line in open(SYS / "power_vcd_by_instance.rpt"):
        f = line.split()
        if len(f) == 5 and f[4] in ("u_fe", "u_core"):
            try: inst[f[4]] = dict(internal_uW=float(f[0]) * 1e6, switching_uW=float(f[1]) * 1e6, leakage_uW=float(f[2]) * 1e6, total_uW=float(f[3]) * 1e6)
            except ValueError: pass
    src = json.load(open(SYS / "root_clock_correction.json"))
    fe_cor = src["corrected"]["Total"]["total"] * 1e6                       # front end after the root-clock correction (its clk5 root network)
    cr = inst["u_core"]; T_sim = stb["bins"] * T_bin
    sd = dict(core=dname, tb=stb, osc_duty=src["duty"], frontend_reported_uW=inst["u_fe"]["total_uW"], frontend_uW=fe_cor, core_uW=cr["total_uW"], core_leakage_uW=cr["leakage_uW"],
              core_dyn_uW=cr["total_uW"] - cr["leakage_uW"], core_energy_per_bin_nJ=(cr["total_uW"] - cr["leakage_uW"]) * 1e-6 * T_sim / stb["bins"] * 1e9,
              total_uW=fe_cor + cr["total_uW"], core_clk_per_bin=stb["core_clk_cycles"] / stb["bins"], bins_per_s=1 / T_bin)
    # the same core measured alone (results/designs.json: 500-bin zero-delay window; 5,000-bin annotated block where measured) at the co-simulation's rate
    dc = D.get(dname, {})
    if dc.get("event") and dc.get("idle"):
        sd["core_alone_uW_func"] = dc["event"]["energy_per_bin_nJ"] * sd["bins_per_s"] * 1e-3 + dc["idle"]["leakage_uW"]
        sd["core_alone_energy_per_bin_nJ_func"] = dc["event"]["energy_per_bin_nJ"]
        fb = dc.get("full", {}).get("indy_20160630_01", {}).get("sdf")
        if fb: sd["core_alone_uW_sdf_w5000"] = fb["energy_per_bin_nJ"] * sd["bins_per_s"] * 1e-3 + dc["idle"]["leakage_uW"]
        w500 = ROOT / f"power/out_{dname}_5m_func_w500_indy_20160630_01/power_vcd.rpt"
        if w500.exists():
            from collect_designs5 import run_energy
            e5 = run_energy(f"{dname}_5m_func_w500_indy_20160630_01", 200.0, None)
            if e5: sd["core_alone_energy_per_bin_nJ_func_w500"] = e5["energy_per_bin_nJ"]; sd["core_alone_uW_func_w500"] = e5["energy_per_bin_nJ"] * sd["bins_per_s"] * 1e-3 + dc["idle"]["leakage_uW"]
        sd["sum_separate_uW"] = out["power"]["total_uW"] + sd["core_alone_uW_func"]
        sd["sum_separate_ann_uW"] = out["power"]["total_uW"] + (sd.get("core_alone_uW_sdf_w5000") or sd["core_alone_uW_func"])   # the paper's sum (front end + annotated block energy x rate + leakage)
    out["system_cosim"][core] = sd
    if core == "sp": sysd = sd
json.dump(out, open(ROOT / "results/frontend.json", "w"), indent=1)
L = ["% auto-generated by sw/collect_frontend.py (round 5, E10)"]
def mac(n, v, nd=3): L.append(f"\\newcommand{{\\{n}}}{{{_f(v, nd)}}}")
p = out["pnr"]; mac("feCells", p["cells"], 4); mac("feArea", p["area_um2"] / 1e6 if p["area_um2"] else None, 3); mac("feUtil", p["util_target_pct"], 2)
mac("feSlack", p["setup_ws_ns"], 3); mac("feHold", p["hold_ws_ns"], 3)
mac("feBins", tb["bins"], 3); mac("feEvents", tb["events"], 4); mac("feOscDutyPct", out["osc_duty"] * 100, 3); mac("feOscUsPerBin", out["osc_us_per_bin"], 3)
mac("feCoreClkPerBin", out["core_clk_per_bin"], 3); mac("feClkFiveCyclesPerBin", tb["clk5_cycles"] / tb["bins"], 3)
pw = out["power"]; mac("fePower", pw["total_uW"], 3); mac("feLeak", pw["leakage_uW"], 3); mac("feSeq", pw["sequential_uW"], 3); mac("feClk", pw["clock_uW"], 3); mac("feComb", pw["combinational_uW"], 3)
mac("feClkSlow", dom["clk32k"], 3); mac("feClkFast", dom["clk5"], 3); mac("feIcg", dom["icg"], 3)
mac("fePowerVone", out["power_v1_freerunning"]["total_uW"], 3); mac("feClkVone", out["power_v1_freerunning"]["clock_uW"], 3)
mac("fePowerReported", rep["total_uW"], 3); mac("feRootRemoved", rc["removed_W"] * 1e6, 3)
for sh, c in comb.items(): mac(f"feWith{sh}", c["total_uW"], 3); mac(f"feShare{sh}Pct", c["frontend_share"] * 100, 3); mac(f"coreOnly{sh}", c["core_uW"], 3)
mac("fePowerVtwo", out.get("power_v2_total_uW"), 3)
for core, csh, dname in SYS_CORES:                                        # round 6 (E6) / round 7 (fix 7)
    sd = out["system_cosim"].get(core)
    if not sd: continue
    mac(f"pSys{csh}", sd["total_uW"], 3); mac(f"pSysFe{csh}", sd["frontend_uW"], 3); mac(f"pSysCore{csh}", sd["core_uW"], 3); mac(f"pSysCoreDyn{csh}", sd["core_dyn_uW"], 3)
    mac(f"eSysCore{csh}", sd["core_energy_per_bin_nJ"], 3); mac(f"sysCoreClkPerBin{csh}", sd["core_clk_per_bin"], 3)
    mac(f"pSysSumSeparate{csh}", sd.get("sum_separate_uW"), 3); mac(f"pSysSumSeparateAnn{csh}", sd.get("sum_separate_ann_uW"), 3)
    mac(f"pSysCoreAlone{csh}", sd.get("core_alone_uW_func"), 3); mac(f"eSysCoreAlone{csh}", sd.get("core_alone_energy_per_bin_nJ_func"), 3)
    mac(f"pSysCoreAloneWFive{csh}", sd.get("core_alone_uW_func_w500"), 3); mac(f"eSysCoreAloneWFive{csh}", sd.get("core_alone_energy_per_bin_nJ_func_w500"), 3)
    mac(f"pSysVsSumPct{csh}", (sd["total_uW"] / sd["sum_separate_uW"] - 1) * 100 if sd.get("sum_separate_uW") else None, 2)
    mac(f"pSysVsSumAnnPct{csh}", (sd["total_uW"] / sd["sum_separate_ann_uW"] - 1) * 100 if sd.get("sum_separate_ann_uW") else None, 2)
    if core == "sp":                                                       # round-6 names kept
        mac("sysBins", sd["tb"]["bins"], 3); mac("sysEvents", sd["tb"]["events"], 4); mac("sysCoreClkPerBin", sd["core_clk_per_bin"], 3)
        mac("sysOscDutyPct", sd["osc_duty"] * 100, 3); mac("pSysVsSumPct", (sd["total_uW"] / sd["sum_separate_uW"] - 1) * 100 if sd.get("sum_separate_uW") else None, 2)
(ROOT / "paper/numbers_frontend.tex").write_text("\n".join(L) + "\n")
print(json.dumps({k: v for k, v in out.items() if k != "tb"}, indent=1)); print("bins", tb["bins"], "pass", tb["pass"])
