#!/usr/bin/env python3
"""Collect all measured numbers into results/results.json and produce the hardware figures.

Inputs (produced by the flow scripts):
  synthesis/bmi_snn_top/runs/bmi_snn_top/final/metrics.json          area / timing
  sim/build_gls_md0/{vvp.log,stats.txt}, sim/build_gls_md1/...      cycles, latency, per-bin activity
  power/out_gls_md0/power_energy.txt (+ power_awake.rpt, power_sleep.rpt, power_macro_*.rpt), power/out_gls_md1/...
  power/out_gls_md0_time/power_vs_time.csv + windows.json             power timeline
  power/out_riscv/power_energy.txt, sim/build_riscv_gls/riscv_gls.vcd  RISC-V baseline
  results/models/*_drop/eval_int.json                                  accuracy + activity statistics
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "paper" / "figures"; FIG.mkdir(exist_ok=True)
BIN_S = 0.004; RATE = 1 / BIN_S            # 250 bins per second
TCLK_NS = 20.0   # core clock (50 MHz)
TCLK_CPU_NS = 20.0  # the RISC-V SoC runs at 50 MHz
SESS = ["indy_20160622_01", "indy_20160630_01", "indy_20170131_02"]
TAG = "_H64_th256_k44_drop"
GLS_SESSION = "indy_20160630_01"

def num(pattern, text, default=None, flags=re.M):
    m = re.search(pattern, text, flags)
    return float(m.group(1)) if m else default

def parse_power_energy(p: Path) -> dict:
    t = p.read_text()
    d = {"power_total_mW": num(r"^power_total\s*:\s*([0-9.eE+-]+) mW", t),
         "power_awake_mW": num(r"^power_awake\s*:\s*([0-9.eE+-]+) mW", t),
         "power_sleep_mW": num(r"^power_sleep\s*:\s*([0-9.eE+-]+) mW", t),
         "duty": num(r"^core_clk_en_duty\s*:\s*([0-9.]+)", t),
         "cycles": num(r"^cycles\s*:\s*(\d+)", t),
         "runtime_ms": num(r"^runtime_one_infer\s*:\s*([0-9.]+) ms", t),
         "energy_uJ": num(r"^energy_one_infer\s*:\s*([0-9.]+) µJ", t)}
    for g in ("sequential", "combinational", "clock", "macro"):
        d[f"{g}_mW"] = num(rf"^\s*{g}\s*:\s*([0-9.eE+-]+) mW", t)
    return d

def parse_group_table(p: Path) -> dict:
    """OpenSTA report_power group table -> {group: {internal, switching, leakage, total}} in W."""
    out = {}
    for line in p.read_text(errors="replace").splitlines():
        m = re.match(r"^\s*(Sequential|Combinational|Clock|Macro|Pad|Total)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)", line)
        if m:
            out[m.group(1)] = dict(internal=float(m.group(2)), switching=float(m.group(3)), leakage=float(m.group(4)), total=float(m.group(5)))
    return out

def parse_instance_report(p: Path, inst: str) -> dict:
    """OpenSTA report_power -instances row -> {internal, switching, leakage, total} in W."""
    for line in p.read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[-1] == inst or (len(parts) >= 5 and parts[0] == inst):
            nums = [x for x in parts if re.match(r"^[-0-9.eE+]+$", x)]
            if len(nums) >= 4:
                return dict(internal=float(nums[0]), switching=float(nums[1]), leakage=float(nums[2]), total=float(nums[3]))
    return {}

def parse_tb_summary(p: Path) -> dict:
    t = p.read_text(errors="replace")
    m = re.search(r"SUMMARY: bins=(\d+) events=(\d+) errors=(\d+) cycles=(\d+) active_cycles=(\d+) avg_latency_cyc=(\d+) max_latency_cyc=(\d+)", t)
    keys = ["bins", "events", "errors", "cycles", "active_cycles", "avg_latency_cyc", "max_latency_cyc"]
    d = dict(zip(keys, map(int, m.groups()))) if m else {}
    d["pass"] = "PASS" in t
    return d

def parse_metrics(p: Path) -> dict:
    m = json.loads(p.read_text())
    def g(*keys):
        for k in keys:
            if k in m: return m[k]
        return None
    return {"instance_area_um2": g("design__instance__area"), "stdcell_area_um2": g("design__instance__area__stdcell"),
            "macro_area_um2": g("design__instance__area__macros"), "instances": g("design__instance__count"),
            "stdcells": g("design__instance__count__stdcell"), "macros": g("design__instance__count__macros"),
            "die_area_um2": g("design__die__area"), "core_area_um2": g("design__core__area"),
            "setup_ws_ns": g("timing__setup__ws", "timing__setup__ws__corner:nom_tt_025C_1v80"),
            "hold_ws_ns": g("timing__hold__ws", "timing__hold__ws__corner:nom_tt_025C_1v80"),
            "setup_viol": g("timing__setup_vio__count"), "hold_viol": g("timing__hold_vio__count"),
            "clock_period_ns": g("clock__period"), "wirelength_um": g("route__wirelength"),
            "drc": g("route__drc_errors"), "utilisation": g("design__instance__utilization")}

def main():
    R = {"sessions": {}, "core": {}, "riscv": {}}
    # ---------------- accuracy / activity
    for s in SESS:
        e = json.load(open(ROOT / "results/models" / f"{s}{TAG}" / "eval_int.json"))
        R["sessions"][s] = e
    R["mean_test_r2"] = float(np.mean([R["sessions"][s]["test_r2_int"] for s in SESS]))
    R["mean_events_per_bin"] = float(np.mean([R["sessions"][s]["events_per_bin"] for s in SESS]))
    R["mean_hidden_spikes_per_bin"] = float(np.mean([R["sessions"][s]["hidden_spikes_per_bin"] for s in SESS]))
    # ---------------- area / timing
    mp = ROOT / "synthesis/bmi_snn_top/runs/bmi_snn_top/final/metrics.json"
    if mp.exists(): R["core"]["pnr"] = parse_metrics(mp)
    # ---------------- GLS + power, both modes
    for md, name in ((0, "event"), (1, "dense")):
        d = {}
        log = ROOT / f"sim/build_gls_md{md}/vvp.log"
        if log.exists():
            d["tb"] = parse_tb_summary(log)
            st = ROOT / f"sim/build_gls_md{md}/stats.txt"
            if st.exists():
                a = np.loadtxt(st, ndmin=2)   # bin, cycles, active_cycles, latency
                d["per_bin"] = {"active_cycles_mean": float(a[:, 2].mean()), "active_cycles_std": float(a[:, 2].std()),
                                "latency_cycles": float(a[:, 3].mean())}
        pe = ROOT / f"power/out_gls_md{md}/power_energy.txt"
        if pe.exists():
            d["power"] = parse_power_energy(pe)
            d["groups_awake"] = parse_group_table(ROOT / f"power/out_gls_md{md}/power_awake.rpt")
            d["groups_sleep"] = parse_group_table(ROOT / f"power/out_gls_md{md}/power_sleep.rpt")
            ma = ROOT / f"power/out_gls_md{md}/power_macro_awake.rpt"
            if ma.exists(): d["macro_awake"] = parse_group_table(ma)
            ms = ROOT / f"power/out_gls_md{md}/power_macro_sleep.rpt"
            if ms.exists(): d["macro_sleep"] = parse_group_table(ms)
            # derived: energy per bin = P_awake * active cycles * Tclk / bins  (+ P_sleep during the forced idle gaps is idle power)
            tb = d.get("tb", {})
            if tb.get("bins"):
                P_aw = d["power"]["power_awake_mW"] * 1e-3; P_sl = d["power"]["power_sleep_mW"] * 1e-3
                act_cyc = tb["active_cycles"] / tb["bins"]
                d["energy_per_bin_nJ_active"] = P_aw * act_cyc * TCLK_NS * 1e-9 * 1e9
                d["energy_per_bin_nJ_blended_sim"] = d["power"]["power_total_mW"] * 1e-3 * (tb["cycles"] / tb["bins"]) * TCLK_NS * 1e-9 * 1e9
                d["active_cycles_per_bin"] = act_cyc
                d["latency_us"] = tb["avg_latency_cyc"] * TCLK_NS * 1e-3
                d["edp_nJ_us"] = d["energy_per_bin_nJ_active"] * d["latency_us"]
                d["idle_power_uW_50MHz"] = P_sl * 1e6
                leak = d["groups_sleep"].get("Total", {}).get("leakage", 0.0)
                d["leakage_uW"] = leak * 1e6
                d["avg_power_uW_realtime_50MHz_idle_clock"] = d["energy_per_bin_nJ_active"] * RATE * 1e-3 + P_sl * 1e6
                d["avg_power_uW_realtime_leak_only"] = d["energy_per_bin_nJ_active"] * RATE * 1e-3 + leak * 1e6
                d["duty_realtime"] = act_cyc * TCLK_NS * 1e-9 * RATE
                # method (a): per-pin VCD annotation on the back-to-back (gap 0) full-depth runs
                pv = ROOT / f"power/out_vcd_gls_md{md}_full/power_vcd.rpt"
                lg = ROOT / f"sim/build_gls_md{md}_full/vvp.log"
                if pv.exists() and lg.exists():
                    g = parse_group_table(pv); d["groups_vcd"] = g; tbf = parse_tb_summary(lg); d["tb_full"] = tbf
                    mv = ROOT / f"power/out_vcd_gls_md{md}_full/power_vcd_u_wmem.rpt"
                    if mv.exists():
                        r = parse_instance_report(mv, "u_wmem")
                        if r: d["macro_vcd"] = {"Total": r}
                    P_tot = g["Total"]["total"]
                    T_sim = tbf["cycles"] * TCLK_NS * 1e-9
                    d["power_vcd_avg_uW"] = P_tot * 1e6
                    d["energy_per_bin_nJ_vcd"] = P_tot * T_sim / tbf["bins"] * 1e9      # bins back-to-back: all cycles belong to bins
                    d["active_cycles_per_bin_full"] = tbf["cycles"] / tbf["bins"]
                    d["energy_per_bin_nJ_ref"] = d["energy_per_bin_nJ_active"]
                    d["energy_per_bin_nJ_active"] = d["energy_per_bin_nJ_vcd"]           # headline = per-pin method
                    d["edp_nJ_us"] = d["energy_per_bin_nJ_active"] * d["latency_us"]
                    d["leakage_uW_vcd"] = g["Total"]["leakage"] * 1e6
                    for tag in ("gls_idle2_full", "gls_idle_full"):
                        pi = ROOT / f"power/out_vcd_{tag}/power_vcd.rpt"; li = ROOT / f"sim/build_{tag}/vvp.log"
                        if pi.exists() and li.exists():
                            gi = parse_group_table(pi); tbi = parse_tb_summary(li)
                            # remove the small active share: E_active ~ (17 n_ev + 83) cycles at the measured decoding power
                            T_i = tbi["cycles"] * TCLK_NS * 1e-9
                            E_active_i = (17 * tbi["events"] + 83 * tbi["bins"]) * TCLK_NS * 1e-9 * P_tot
                            T_idle_i = (tbi["cycles"] - tbi["active_cycles"]) * TCLK_NS * 1e-9
                            est = (gi["Total"]["total"] * T_i - E_active_i) / T_idle_i * 1e6
                            if est > 0:
                                d["idle_power_uW_vcd"] = est; d["idle_power_uW_50MHz"] = est; d["groups_idle_vcd"] = gi; d["idle_run"] = tag
                                break
                    if d.get("idle_power_uW_50MHz", 0) <= 0:
                        d["idle_power_uW_50MHz"] = P_sl * 1e6; d["idle_run"] = "reference case analysis"
                    P_idle = d["idle_power_uW_50MHz"] * 1e-6
                    d["avg_power_uW_realtime_50MHz_idle_clock"] = d["energy_per_bin_nJ_active"] * RATE * 1e-3 + P_idle * 1e6
                    d["avg_power_uW_realtime_leak_only"] = d["energy_per_bin_nJ_active"] * RATE * 1e-3 + d["leakage_uW_vcd"]
                    d["leakage_uW"] = d["leakage_uW_vcd"]
                    d["duty_realtime"] = d["active_cycles_per_bin_full"] * TCLK_NS * 1e-9 * RATE
        R["core"][name] = d
    if "idle_power_uW_vcd" in R["core"].get("event", {}) and "energy_per_bin_nJ_active" in R["core"].get("dense", {}):
        e, dn_ = R["core"]["event"], R["core"]["dense"]
        dn_["idle_power_uW_50MHz"] = e["idle_power_uW_50MHz"]; dn_["idle_run"] = e["idle_run"]
        dn_["avg_power_uW_realtime_50MHz_idle_clock"] = dn_["energy_per_bin_nJ_active"] * RATE * 1e-3 + e["idle_power_uW_50MHz"]
    # ---------------- RISC-V
    pe = ROOT / "power/out_riscv/power_energy.txt"
    if pe.exists():
        d = {"power": parse_power_energy(pe), "groups_awake": parse_group_table(ROOT / "power/out_riscv/power_awake.rpt"),
             "groups_sleep": parse_group_table(ROOT / "power/out_riscv/power_sleep.rpt")}
        cyc = ROOT / "results/riscv_cycles.json"
        if cyc.exists():
            c = json.load(open(cyc)); d["cycles"] = c
            P_aw = d["power"]["power_awake_mW"] * 1e-3; P_sl = d["power"]["power_sleep_mW"] * 1e-3
            d["energy_per_bin_nJ_active"] = P_aw * c["cycles_per_bin"] * TCLK_CPU_NS
            d["latency_us"] = c["cycles_per_bin"] * TCLK_CPU_NS * 1e-3     # software: the whole bin is processed after the tick
            d["edp_nJ_us"] = d["energy_per_bin_nJ_active"] * d["latency_us"]
            d["idle_power_uW_50MHz"] = P_sl * 1e6
            d["leakage_uW"] = d["groups_sleep"].get("Total", {}).get("leakage", 0.0) * 1e6
            d["avg_power_uW_realtime_50MHz_idle_clock"] = d["energy_per_bin_nJ_active"] * RATE * 1e-3 + P_sl * 1e6
            d["avg_power_uW_realtime_leak_only"] = d["energy_per_bin_nJ_active"] * RATE * 1e-3 + d["leakage_uW"]
            pv = ROOT / "power/out_vcd_riscv_gls/power_vcd.rpt"
            if pv.exists():
                g = parse_group_table(pv); d["groups_vcd"] = g
                P_tot = g["Total"]["total"]
                T_sim = c["total_cycles"] * TCLK_CPU_NS * 1e-9
                # whole run: init + 2 sleeps (10k cycles each, gated) + decode; attribute non-decode awake cycles to init
                T_sleep = (c["total_cycles"] - c["awake_cycles"]) * TCLK_CPU_NS * 1e-9
                E_decode_share = c["decode_cycles"] / c["awake_cycles"]
                d["power_vcd_avg_mW"] = P_tot * 1e3
                d["energy_per_bin_nJ_ref"] = d["energy_per_bin_nJ_active"]
                d["energy_per_bin_nJ_vcd"] = (P_tot * T_sim - P_sl * T_sleep) * E_decode_share / c["n_bins"] * 1e9
                d["energy_per_bin_nJ_active"] = d["energy_per_bin_nJ_vcd"]
                d["edp_nJ_us"] = d["energy_per_bin_nJ_active"] * d["latency_us"]
                d["avg_power_uW_realtime_50MHz_idle_clock"] = d["energy_per_bin_nJ_active"] * RATE * 1e-3 + P_sl * 1e6
                d["avg_power_uW_realtime_leak_only"] = d["energy_per_bin_nJ_active"] * RATE * 1e-3 + d["leakage_uW"]
        R["riscv"] = d
    (ROOT / "results/results.json").write_text(json.dumps(R, indent=1, default=float))
    write_numbers_tex(R)
    print(json.dumps({k: v for k, v in R.items() if k != "sessions"}, indent=1, default=float)[:6000])
    make_figures(R)

def _fmt(x, nd=3):
    if x is None or (isinstance(x, float) and not np.isfinite(x)): return "?"
    if abs(x) >= 100: return f"{x:,.0f}"
    return f"{x:.{nd}g}"

def write_numbers_tex(R):
    """LaTeX macros with the measured numbers (paper/numbers.tex)."""
    L = []
    defined = set()
    def mac(name, val, nd=3):
        defined.add(name); L.append(f"\\newcommand{{\\{name}}}{{{_fmt(val, nd)}}}")
    S = R["sessions"]
    for i, s in enumerate(SESS):
        tag = ["A", "B", "C"][i]
        mac(f"rTwo{tag}", S[s]["test_r2_int"], 3); mac(f"evBin{tag}", S[s]["events_per_bin"], 3); mac(f"hidBin{tag}", S[s]["hidden_spikes_per_bin"], 3)
    mac("rTwoMean", R["mean_test_r2"], 3); mac("evBinMean", R["mean_events_per_bin"], 3); mac("hidBinMean", R["mean_hidden_spikes_per_bin"], 3)
    p = R["core"].get("pnr", {})
    if p:
        mac("coreAreaMM", (p["instance_area_um2"] or 0) / 1e6, 3); mac("coreLogicAreaMM", (p["stdcell_area_um2"] or 0) / 1e6, 3)
        mac("coreMacroAreaMM", (p["macro_area_um2"] or 0) / 1e6, 3); mac("coreCells", p["stdcells"], 4)
        mac("coreSetupWS", p["setup_ws_ns"], 3); mac("coreHoldWS", p["hold_ws_ns"], 3)
        if p.get("setup_ws_ns") is not None:
            mac("coreFmax", 1e3 / ((p.get("clock_period_ns") or TCLK_NS) - p["setup_ws_ns"]), 3)
    for name, key in (("Ev", "event"), ("Dn", "dense")):
        d = R["core"].get(key, {})
        if "energy_per_bin_nJ_active" in d:
            mac(f"e{name}", d["energy_per_bin_nJ_active"], 3); mac(f"lat{name}", d["latency_us"], 3); mac(f"edp{name}", d["edp_nJ_us"], 3)
            mac(f"cyc{name}", d["active_cycles_per_bin"], 3); mac(f"pAwake{name}", d["power"]["power_awake_mW"] * 1e3, 3)
            mac(f"pIdle{name}", d["idle_power_uW_50MHz"], 3); mac(f"pLeak{name}", d["leakage_uW"], 3)
            mac(f"pAvg{name}", d["avg_power_uW_realtime_50MHz_idle_clock"], 3); mac(f"pAvgLeak{name}", d["avg_power_uW_realtime_leak_only"], 3)
            mac(f"duty{name}", d["duty_realtime"] * 100, 3)
            g = d.get("groups_vcd", d["groups_awake"]); tot = g["Total"]["total"]
            for grp in ("Sequential", "Combinational", "Clock", "Macro"):
                mac(f"frac{grp}{name}", 100 * g[grp]["total"] / tot, 3)
            if "macro_vcd" in d and "Total" in d["macro_vcd"]:
                mac(f"pMacroLeak{name}", d["macro_vcd"]["Total"]["leakage"] * 1e6, 3)
            elif "macro_sleep" in d and "Total" in d["macro_sleep"]:
                mac(f"pMacroLeak{name}", d["macro_sleep"]["Total"]["leakage"] * 1e6, 3)
    ev, dn, cpu = R["core"].get("event", {}), R["core"].get("dense", {}), R.get("riscv", {})
    if "energy_per_bin_nJ_active" in ev and "energy_per_bin_nJ_active" in dn:
        mac("ratioDnEv", dn["energy_per_bin_nJ_active"] / ev["energy_per_bin_nJ_active"], 3)
        mac("ratioEdpDnEv", dn["edp_nJ_us"] / ev["edp_nJ_us"], 3)
    if "energy_per_bin_nJ_active" in cpu:
        mac("eCpu", cpu["energy_per_bin_nJ_active"], 3); mac("latCpu", cpu["latency_us"], 3); mac("edpCpu", cpu["edp_nJ_us"], 3)
        mac("cycCpu", cpu["cycles"]["cycles_per_bin"], 4); mac("pAwakeCpu", cpu["power"]["power_awake_mW"], 3)
        mac("pIdleCpu", cpu["idle_power_uW_50MHz"], 3); mac("pLeakCpu", cpu["leakage_uW"], 3)
        mac("pAvgCpu", cpu["avg_power_uW_realtime_50MHz_idle_clock"], 4); mac("pAvgLeakCpu", cpu["avg_power_uW_realtime_leak_only"], 4)
        if "energy_per_bin_nJ_active" in ev:
            mac("ratioCpuEv", cpu["energy_per_bin_nJ_active"] / ev["energy_per_bin_nJ_active"], 3)
            mac("ratioEdpCpuEv", cpu["edp_nJ_us"] / ev["edp_nJ_us"], 3)
    for name, d in (("Ev", ev), ("Dn", dn), ("Cpu", cpu)):
        if "energy_per_bin_nJ_ref" in d: mac(f"e{name}Ref", d["energy_per_bin_nJ_ref"], 3)
        if "power_vcd_avg_uW" in d: mac(f"pVcd{name}", d["power_vcd_avg_uW"], 3)
    if "energy_per_bin_nJ_active" in ev:
        mac("pDynEv", ev["energy_per_bin_nJ_active"] * RATE * 1e-3, 3)      # µW of dynamic decoding power at 250 bins/s
    if "energy_per_bin_nJ_active" in cpu and "energy_per_bin_nJ_active" in dn:
        mac("ratioCpuDn", cpu["energy_per_bin_nJ_active"] / dn["energy_per_bin_nJ_active"], 3)
    ALL = ["rTwoA","evBinA","hidBinA","rTwoB","evBinB","hidBinB","rTwoC","evBinC","hidBinC","rTwoMean","evBinMean","hidBinMean",
           "coreAreaMM","coreLogicAreaMM","coreMacroAreaMM","coreCells","coreSetupWS","coreHoldWS","coreFmax",
           "eEv","latEv","edpEv","cycEv","pAwakeEv","pIdleEv","pLeakEv","pAvgEv","pAvgLeakEv","dutyEv",
           "fracSequentialEv","fracCombinationalEv","fracClockEv","fracMacroEv","pMacroLeakEv",
           "eDn","latDn","edpDn","cycDn","pAwakeDn","pIdleDn","pLeakDn","pAvgDn","pAvgLeakDn","dutyDn",
           "fracSequentialDn","fracCombinationalDn","fracClockDn","fracMacroDn","pMacroLeakDn",
           "ratioDnEv","ratioEdpDnEv","eCpu","latCpu","edpCpu","cycCpu","pAwakeCpu","pIdleCpu","pLeakCpu","pAvgCpu",
           "ratioCpuEv","ratioEdpCpuEv","pDynEv","ratioCpuDn","pAvgLeakCpu","eEvRef","eDnRef","eCpuRef","pVcdEv","pVcdDn"]
    for n in ALL:
        if n not in defined: L.append(f"\\newcommand{{\\{n}}}{{\\textcolor{{red}}{{?}}}}")
    (ROOT / "paper/numbers.tex").write_text("% auto-generated by sw/collect_results.py\n" + "\n".join(L) + "\n")
    print("wrote paper/numbers.tex with", len(L), "macros")

def make_figures(R):
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    ev, dn, cpu = R["core"].get("event", {}), R["core"].get("dense", {}), R.get("riscv", {})
    if "energy_per_bin_nJ_active" in ev and "energy_per_bin_nJ_active" in dn:
        # --- energy / latency / EDP bars (log)
        try:    # hand-tuned firmware (E4 of the referee experiments): results/explore/software.json
            tuned = json.load(open(ROOT / "results/explore/software.json"))["_tuned"]
        except Exception: tuned = {}
        names = ["software\n(-O2)", "software\n(tuned)", "dense\nengine", "event-driven\ncore"]
        vals = [[cpu.get("energy_per_bin_nJ_active", np.nan), tuned.get("energy_per_bin_nJ_ref", np.nan), dn["energy_per_bin_nJ_active"], ev["energy_per_bin_nJ_active"]],
                [cpu.get("latency_us", np.nan), tuned.get("latency_us", np.nan), dn["latency_us"], ev["latency_us"]],
                [cpu.get("avg_power_uW_realtime_leak_only", np.nan), tuned.get("avg_power_uW_250Hz_leak", np.nan), dn["avg_power_uW_realtime_leak_only"], ev["avg_power_uW_realtime_leak_only"]]]
        titles = ["energy per 4 ms bin (nJ)", "decode latency (µs)", "avg. power @250 bins/s (µW), clock stopped"]
        fig, axs = plt.subplots(1, 3, figsize=(7.6, 2.6))
        cols = ["#999999", "#bbbbbb", "#7f9fbf", "#c0504d"]
        for ax, v, t in zip(axs, vals, titles):
            b = ax.bar(range(4), v, color=cols); ax.set_yscale("log"); ax.set_title(t, fontsize=7.5)
            ax.set_xticks(range(4)); ax.set_xticklabels(names, fontsize=6.5)
            for i, x in enumerate(v):
                if np.isfinite(x): ax.text(i, x * 1.15, f"{x:,.0f}" if x >= 100 else f"{x:.3g}", ha="center", fontsize=7)
            ax.set_ylim(top=max([x for x in v if np.isfinite(x)]) * 4)
        fig.tight_layout(); fig.savefig(FIG / "energy_bars.pdf"); fig.savefig(FIG / "energy_bars.png", dpi=200)
        # --- power breakdown (awake), event vs dense
        fig, ax = plt.subplots(figsize=(4.2, 2.6))
        groups = ["Sequential", "Combinational", "Clock", "Macro"]
        for i, (d, lab) in enumerate(((ev, "event mode, active"), (dn, "dense mode, active"))):
            g = d.get("groups_vcd", d["groups_awake"]); tot = sum(g[k]["total"] for k in groups)
            bottom = 0
            for k, c in zip(groups, ["#c0504d", "#f0a070", "#7f9fbf", "#5b9b6b"]):
                val = g[k]["total"] * 1e3
                ax.bar(i, val, bottom=bottom, color=c, label=k if i == 0 else None, width=0.6); bottom += val
        ax.set_xticks([0, 1]); ax.set_xticklabels(["event mode", "dense mode"]); ax.set_ylabel("power while decoding, 50 MHz (mW)")
        ax.legend(fontsize=7, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0)); fig.tight_layout(); fig.savefig(FIG / "power_breakdown.pdf"); fig.savefig(FIG / "power_breakdown.png", dpi=200)
    # --- energy vs. events per bin (event mode), from per-bin cycle stats and P_awake
    st = ROOT / "sim/build_gls_md0/stats.txt"; vec = ROOT / f"sim/vec_{GLS_SESSION}/stream.hex"
    if st.exists() and "power" in ev:
        a = np.loadtxt(st, ndmin=2); toks = vec.read_text().split()
        nev = []; c = 0
        for t in toks:
            if t == "ff": nev.append(c); c = 0
            else: c += 1
        nev = np.array(nev[:a.shape[0]])
        P_dec = ev.get("power_vcd_avg_uW", ev["power"]["power_awake_mW"] * 1e3) * 1e-6
        e_bin = P_dec * a[:, 2] * TCLK_NS                      # nJ: active cycles of the bin x average decoding power
        # linear fit over the per-bin points (the evidence for the E = a + b n_ev model): slope, intercept, RMS residual, R^2
        b_, a_ = np.polyfit(nev, e_bin, 1); res = e_bin - (a_ + b_ * nev)
        fit = {"slope_nJ_per_event": float(b_), "intercept_nJ": float(a_), "rms_resid_nJ": float(np.sqrt(np.mean(res ** 2))),
               "max_resid_nJ": float(np.abs(res).max()), "r2": float(1 - np.sum(res ** 2) / np.sum((e_bin - e_bin.mean()) ** 2)), "bins": int(len(nev))}
        json.dump(fit, open(ROOT / "results/explore/perbin_fit.json", "w"), indent=1)
        with open(ROOT / "paper/numbers_perbin.tex", "w") as fh:
            fh.write("% auto-generated by sw/collect_results.py (per-bin linear fit of Figure energy-vs-events)\n")
            for k, v in (("evFitSlope", b_), ("evFitIntercept", a_), ("evFitRms", fit["rms_resid_nJ"]), ("evFitMaxResid", fit["max_resid_nJ"])):
                fh.write(f"\\newcommand{{\\{k}}}{{{v:.3g}}}\n")
            fh.write(f"\\newcommand{{\\evFitRsq}}{{{fit['r2']:.4f}}}\n\\newcommand{{\\evFitBins}}{{{fit['bins']}}}\n")
        fig, ax = plt.subplots(figsize=(4.2, 2.6))
        ax.scatter(nev, e_bin, s=6, color="#c0504d", alpha=0.5, label="event mode, per bin (cycles × decoding power)")
        if "energy_per_bin_nJ_active" in dn:
            ax.axhline(dn["energy_per_bin_nJ_active"], color="#7f9fbf", ls="--", label=f"dense mode ({dn['energy_per_bin_nJ_active']:.0f} nJ, input independent)")
        ax.set_xlabel("active input channels in the bin"); ax.set_ylabel("energy per bin (nJ)"); ax.set_ylim(0, dn.get("energy_per_bin_nJ_active", 400) * 1.15)
        ax.legend(fontsize=7, frameon=False, loc="center right"); fig.tight_layout()
        fig.savefig(FIG / "energy_vs_events.pdf"); fig.savefig(FIG / "energy_vs_events.png", dpi=200)
    # --- power timeline
    csv = ROOT / "power/out_gls_md0_time/power_vs_time.csv"
    if csv.exists():
        import csv as _csv
        rows = list(_csv.DictReader(open(csv)))
        t0 = np.array([float(r["t0"]) for r in rows]); t1 = np.array([float(r["t1"]) for r in rows])
        top = np.array([float(r["top_total_uW"]) for r in rows]); mem = np.array([float(r["u_imem_total_uW"]) for r in rows])
        logic = np.array([float(r["logic_total_uW"]) for r in rows]); stat = np.array([float(r["top_static_uW"]) for r in rows])
        tm = (t0 + t1) / 2 * 1e-3   # ns -> us
        # input events per window from the stream (approximate mapping by bin index using stats.txt cycle counts)
        fig, axs = plt.subplots(2, 1, figsize=(6.4, 3.4), sharex=True, gridspec_kw={"height_ratios": [1, 2]})
        if st.exists():
            a = np.loadtxt(st, ndmin=2); toks = vec.read_text().split()
            nev = []; c = 0
            for t in toks:
                if t == "ff": nev.append(c); c = 0
                else: c += 1
            # bin end times in us: cumulative cycles * 20 ns (approx: stats give cycles per bin incl. gap)
            bin_end = np.cumsum(a[:, 1]) * TCLK_NS * 1e-3
            nb = min(len(bin_end), len(nev))
            axs[0].step(bin_end[:nb], nev[:nb], where="post", color="k", lw=0.7); axs[0].set_ylabel("events / bin")
        axs[1].fill_between(tm, 0, mem, color="#5b9b6b", alpha=0.5, label="weight SRAM", step="mid")
        axs[1].fill_between(tm, mem, mem + logic, color="#c0504d", alpha=0.5, label="logic + clock", step="mid")
        axs[1].plot(tm, stat, color="k", lw=0.8, ls=":", label="static")
        axs[1].set_ylabel("power (µW)"); axs[1].set_xlabel("time (µs), 40 MHz clock, bins back-to-back with 64-cycle idle gaps")
        axs[1].legend(fontsize=7, frameon=False, ncol=3, loc="upper right")
        xmax = min(tm[-1], 400); axs[1].set_xlim(0, xmax)
        fig.tight_layout(); fig.savefig(FIG / "power_timeline.pdf"); fig.savefig(FIG / "power_timeline.png", dpi=200)
    print("figures done")

if __name__ == "__main__":
    main()
