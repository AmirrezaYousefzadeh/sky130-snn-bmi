#!/usr/bin/env python3
"""Round 5 (E1/E4/E9): collect the 5 MHz hardenings and measurements of every core.

Reads, per design D (sw/collect_designs.DESIGNS plus the round-5 grid and per-session variants):
  synthesis/D/runs/D_5m/final/metrics.json (+ config_5mhz_used.yaml)          area, cells, utilization, slacks per corner, DRC
  sim/build_D_5m_{md0,md1,idle}_{full,sdf} + power/out_vcd_...                500/200-bin windows (as at 50 MHz), idle run
  power/out_vcd_D_5m_idle_full/power_vcd_by_instance.rpt                       leakage split logic / physical cells
  sim/build_D_5m_func_full_<session> + power/out_D_5m_func_full_<session>     full test blocks (E4), zero-delay
  sim/build_D_5m_sdf_w5000_<session> + power/out_D_5m_sdf_w5000_<session>     5,000-bin annotated windows (E4)
Idle strategies at 250 bins/s: clock stopped (leakage only), 32.768 kHz always-on clock, 5 MHz clock running.
Writes results/designs.json, results/DESIGNS.md, paper/numbers2.tex (same macro names as before, now the 5 MHz values, plus
leakLogic/leakPhys/pavgSlow/pavgFive/util/eFull*/eSdfW*), paper/designs_table.tex; the 50 MHz macros are kept in
paper/numbers2_50mhz.tex with the suffix AtFifty (generated from the superseded numbers2.tex)."""
import json, re, sys, os
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_designs import DESIGNS, D, r2_of, run_energy, run_idle, _f, SESS
from collect_pdks import leakage_split, netlist_stats
from collect_results import RATE, parse_metrics
ROOT = Path(__file__).resolve().parent.parent
TCLK = 200.0; SUF = "_5m"; SH_S = {"indy_20160622_01": "A", "indy_20160630_01": "B", "indy_20170131_02": "C"}
CORNERS = ["nom_tt_025C_1v80", "nom_ss_100C_1v60", "nom_ff_n40C_1v95", "min_tt_025C_1v80", "min_ss_100C_1v60", "min_ff_n40C_1v95", "max_tt_025C_1v80", "max_ss_100C_1v60", "max_ff_n40C_1v95"]
# round-5 additions to the design table: E2 grid (hardwired 12-bit gated template) and E3 per-session netlists
G = lambda label, sh, H, dens, r2tag: D(label, sh, f"constants ({dens})" if dens != "100 %" else "constants", f"{H} / 1", "12 / 14", "no", ("eval", r2tag), "hw")
DESIGNS5 = dict(DESIGNS)
DESIGNS5.update({
    "bmi_snn_g128":     G("hardwired 12-bit, gated, $H{=}128$",                 "GaDense",   128, "100 %",  "H128_th256_k44_drop"),
    "bmi_snn_g128p25":  G("hardwired 12-bit, gated, $H{=}128$, 25\\,\\% synapses", "GaQuarter", 128, "25 %",   "H128_th256_k44_drop_p0.25"),
    "bmi_snn_g128p125": G("hardwired 12-bit, gated, $H{=}128$, 12.5\\,\\% synapses", "GaEighth", 128, "12.5 %", "H128_th256_k44_drop_p0.125"),
    "bmi_snn_g64p50":   G("hardwired 12-bit, gated, $H{=}64$, 50\\,\\% synapses",  "GbHalf",    64,  "50 %",   "H64_th256_k44_drop_p0.5"),
    "bmi_snn_g64p125":  G("hardwired 12-bit, gated, $H{=}64$, 12.5\\,\\% synapses", "GbEighth", 64,  "12.5 %", "H64_th256_k44_drop_p0.125"),
    "bmi_snn_g32p50":   G("hardwired 12-bit, gated, $H{=}32$, 50\\,\\% synapses",  "GcHalf",    32,  "50 %",   "H32_th256_k44_drop_p0.5"),
    "bmi_snn_g32p25":   G("hardwired 12-bit, gated, $H{=}32$, 25\\,\\% synapses",  "GcQuarter", 32,  "25 %",   "H32_th256_k44_drop_p0.25"),
    "bmi_snn_g16p50":   G("hardwired 12-bit, gated, $H{=}16$, 50\\,\\% synapses",  "GdHalf",    16,  "50 %",   "H16_th256_k44_drop_p0.5"),
    "bmi_snn_sp_s622":    D("pruned core, weights of indy\\_20160622\\_01", "SpSA", "constants (25 %)", "64 / 1", "12 / 14", "no", ("vbits", "H64_th256_k44_drop_p0.25", "v12_o14"), "hw"),
    "bmi_snn_sp_s131":    D("pruned core, weights of indy\\_20170131\\_02", "SpSC", "constants (25 %)", "64 / 1", "12 / 14", "no", ("vbits", "H64_th256_k44_drop_p0.25", "v12_o14"), "hw"),
    "bmi_snn_min32_s622": D("32-neuron core, weights of indy\\_20160622\\_01", "MinHSA", "constants", "32 / 1", "16 / 16", "no", ("eval", "H32_th256_k44_drop"), "hw"),
    "bmi_snn_min32_s131": D("32-neuron core, weights of indy\\_20170131\\_02", "MinHSC", "constants", "32 / 1", "16 / 16", "no", ("eval", "H32_th256_k44_drop"), "hw"),
    "bmi_snn_m12_s622":   D("12-bit gated core, weights of indy\\_20160622\\_01", "MinTSA", "constants", "64 / 1", "12 / 14", "no", ("vbits", "H64_th256_k44_drop", "v12_o14"), "hw"),
    "bmi_snn_m12_s131":   D("12-bit gated core, weights of indy\\_20170131\\_02", "MinTSC", "constants", "64 / 1", "12 / 14", "no", ("vbits", "H64_th256_k44_drop", "v12_o14"), "hw"),
})
TL5 = {n: cfg["label"] for n, cfg in DESIGNS5.items()}
SKY_LIB = "/media/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
# per-session window runs (E4): vectors of the session's own weights for the hardwired cores
SESSION_OF = {"bmi_snn_sp_s622": "indy_20160622_01", "bmi_snn_sp_s131": "indy_20170131_02", "bmi_snn_min32_s622": "indy_20160622_01", "bmi_snn_min32_s131": "indy_20170131_02",
              "bmi_snn_m12_s622": "indy_20160622_01", "bmi_snn_m12_s131": "indy_20170131_02"}

def perbin_stats(tag):
    """per-bin energy (nJ) from the testbench's per-bin active-cycle statistics and the run's average decoding power"""
    st = ROOT / f"sim/build_{tag}/stats.txt"; e = run_energy(tag, TCLK, None)
    if not st.exists() or not e: return None
    try: a = np.loadtxt(st, ndmin=2)
    except Exception: return None
    if a.shape[0] < 2: return None
    act = a[:, 2]; T_act = act.sum() * TCLK * 1e-9
    P = e["power_avg_uW"] * 1e-6; T = e["cycles_meas"] * TCLK * 1e-9
    P_dec = P * T / T_act if T_act > 0 else P               # decoding power = total energy / active time
    eb = P_dec * act * TCLK * 1e-9 * 1e9
    return {"bins": int(a.shape[0]), "e_bin_min_nJ": float(eb.min()), "e_bin_max_nJ": float(eb.max()), "e_bin_mean_nJ": float(eb.mean()), "e_bin_sd_nJ": float(eb.std())}

def collect():
    out = {}
    for name, cfg in DESIGNS5.items():
        rd = ROOT / f"synthesis/{name}/runs/{name}{SUF}"
        if not (rd / "final/metrics.json").exists(): continue
        d = {"label": cfg["label"], "tclk_ns": TCLK, "r2": r2_of(cfg["r2"]), "family": cfg["fam"], "weights": cfg["weights"], "lanes": cfg["lanes"], "bits": cfg["bits"], "dense_logic": cfg["dense"]}
        m = json.load(open(rd / "final/metrics.json")); p = parse_metrics(rd / "final/metrics.json"); p["run_dir"] = str(rd.resolve())
        p["setup_ws_ns"] = m.get("timing__setup__ws"); p["hold_ws_ns"] = m.get("timing__hold__ws")   # worst over all corners
        p["timing_met"] = (p["setup_ws_ns"] or 0) >= 0 and (p["hold_ws_ns"] or 0) >= 0
        p["per_corner"] = {c: {"setup_ws_ns": m.get(f"timing__setup__ws__corner:{c}"), "hold_ws_ns": m.get(f"timing__hold__ws__corner:{c}")} for c in CORNERS}
        cu = ROOT / f"synthesis/{name}/config_5mhz_used.yaml"
        if cu.exists():
            mu = re.search(r"^FP_CORE_UTIL:\s*(\d+)", cu.read_text(), flags=re.M); p["util_target_pct"] = int(mu.group(1)) if mu else None
        p["utilization_pct"] = (m.get("design__instance__utilization") or 0) * 100
        nl = rd / f"final/nl/{name}.nl.v"
        if nl.exists():
            st = netlist_stats(nl, [SKY_LIB]); p["logic_cells"] = st["stdcells_netlist"]; p["logic_area_um2"] = st["instance_area_netlist_um2"]; p["phys_cells"] = st["phys_cells"]
        d["pnr"] = p
        macro = cfg["macro"]
        for mode in ("event", "dense"):
            r = run_energy(f"{name}{SUF}_md{0 if mode=='event' else 1}_full", TCLK, macro)
            if r: d[mode] = r
            rs = run_energy(f"{name}{SUF}_md{0 if mode=='event' else 1}_sdf", TCLK, macro)
            if rs: d[mode + "_sdf"] = rs
        P_dec = d["event"]["power_avg_uW"] * 1e-6 if "event" in d else None
        r = run_idle(f"{name}{SUF}_idle_full", TCLK, P_dec) or run_idle(f"{name}{SUF}_idle_sdf", TCLK, P_dec)
        if r: d["idle"] = r
        rpt = ROOT / f"power/out_vcd_{name}{SUF}_idle_full/power_vcd_by_instance.rpt"
        if rpt.exists() and nl.exists():
            ls = leakage_split(rpt, nl)
            if ls: d["leak_split"] = ls
        # full test blocks (E4) and 5,000-bin annotated windows, per session (the hardwired per-session netlists have one session)
        d["full"] = {}
        # session policy (E4): hardwired cores carry one session's weights -> own session only; programmable cores load every session
        PROG = ("bmi_snn_top", "bmi_snn_topg", "bmi_snn_scmem", "bmi_snn_lmem", "bmi_snn_lmem2", "bmi_snn_lmin", "bmi_snn_lmin2")
        sess = [SESSION_OF[name]] if name in SESSION_OF else (SESS if name in PROG else ["indy_20160630_01"])
        for s in sess:
            e = run_energy(f"{name}{SUF}_func_full_{s}", TCLK, macro)
            if e: d["full"][s] = {"func": e, "func_perbin": perbin_stats(f"{name}{SUF}_func_full_{s}")}
            if not e:                                                    # programmable cores: 20,000-bin windows of the other sessions
                for w in ("w20000", "w10000", "w5000"):
                    e = run_energy(f"{name}{SUF}_func_{w}_{s}", TCLK, macro)
                    if e: d["full"][s] = {"func": e, "func_perbin": perbin_stats(f"{name}{SUF}_func_{w}_{s}"), "window": w}; break
            for w in ("w5000", "w2000", "w1000", "w500", "w200", "w50", "w20", "full"):
                es = run_energy(f"{name}{SUF}_sdf_{w}_{s}", TCLK, macro)
                if es: d["full"].setdefault(s, {})["sdf"] = es; d["full"][s]["sdf_perbin"] = perbin_stats(f"{name}{SUF}_sdf_{w}_{s}"); break
        if "event" in d and "idle" in d:
            E = d.get("event_sdf", d["event"])["energy_per_bin_nJ"]; leak = d["idle"]["leakage_uW"]
            idle_dyn = max(d["idle"]["idle_power_uW"] - leak, 0)                   # dynamic part of the idle power with the 5 MHz clock running
            d["avg_power_uW_250Hz_clkstopped"] = d["event"]["energy_per_bin_nJ"] * RATE * 1e-3 + leak
            d["avg_power_uW_250Hz_clkstopped_sdf"] = E * RATE * 1e-3 + leak
            d["avg_power_uW_250Hz_clk32k"] = E * RATE * 1e-3 + leak + idle_dyn * (0.032768 / 5.0)
            d["avg_power_uW_250Hz_clk5MHz"] = E * RATE * 1e-3 + leak + idle_dyn
            d["avg_power_uW_250Hz_clk50MHz"] = None; d["avg_power_uW_250Hz_clk1MHz"] = None
        out[name] = d
    return out

def write_outputs(out):
    json.dump(out, open(ROOT / "results/designs.json", "w"), indent=1, default=float)
    L = ["% auto-generated by sw/collect_designs5.py (round 5: 5 MHz hardenings; the 50 MHz values are in numbers2_50mhz.tex with the suffix AtFifty)"]
    def mac(n, v, nd=3): L.append(f"\\newcommand{{\\{n}}}{{{_f(v, nd)}}}")
    for name, cfg in DESIGNS5.items():
        d = out.get(name, {}); sh = cfg["sh"]; p = d.get("pnr", {}); e = d.get("event", {}); es = d.get("event_sdf", {}); i = d.get("idle", {}); ls = d.get("leak_split", {})
        mac(f"area{sh}", p["instance_area_um2"] / 1e6 if p else None); mac(f"cells{sh}", p.get("stdcells") if p else None, 4)
        mac(f"logicCells{sh}", p.get("logic_cells") if p else None, 4); mac(f"util{sh}", p.get("util_target_pct") if p else None, 2)
        mac(f"slack{sh}", p.get("setup_ws_ns") if p else None, 4); mac(f"hold{sh}", p.get("hold_ws_ns") if p else None, 3)
        mac(f"cyc{sh}", e.get("cycles_per_bin"), 3); mac(f"pdec{sh}", e.get("power_avg_uW"), 3); mac(f"e{sh}", e.get("energy_per_bin_nJ"), 3)
        mac(f"lat{sh}", e.get("latency_us"), 3); mac(f"eSdf{sh}", es.get("energy_per_bin_nJ"), 3); mac(f"eDense{sh}", d.get("dense", {}).get("energy_per_bin_nJ"), 3)
        mac(f"eDenseSdf{sh}", d.get("dense_sdf", {}).get("energy_per_bin_nJ"), 3)
        mac(f"leak{sh}", i.get("leakage_uW"), 3); mac(f"idle{sh}", i.get("idle_power_uW"), 3)
        mac(f"leakLogic{sh}", ls.get("leak_logic_uW"), 3); mac(f"leakPhys{sh}", ls.get("leak_phys_uW"), 3)
        mac(f"pavgStop{sh}", d.get("avg_power_uW_250Hz_clkstopped"), 3); mac(f"pavgStopSdf{sh}", d.get("avg_power_uW_250Hz_clkstopped_sdf"), 3)
        mac(f"pavgSlow{sh}", d.get("avg_power_uW_250Hz_clk32k"), 3); mac(f"pavgFive{sh}", d.get("avg_power_uW_250Hz_clk5MHz"), 3)
        mac(f"pavgFifty{sh}", None); mac(f"pavgOne{sh}", None)
        ef = e.get("energy_per_bin_nJ"); es_ = es.get("energy_per_bin_nJ")
        same = es.get("tb", {}).get("bins") == e.get("tb", {}).get("bins")
        mac(f"sdfRatio{sh}", (es_ / ef) if (ef and es_ and same) else None, 3); mac(f"sdfRatioMixed{sh}", (es_ / ef) if (ef and es_) else None, 3)
        for key, suf in (("event", "evWin"), ("event_sdf", "evWinSdf")):
            tb = d.get(key, {}).get("tb", {}); mac(f"{suf}{sh}", (tb["events"] / tb["bins"]) if tb.get("bins") else None, 3); mac(f"nb{suf}{sh}", tb.get("bins"), 4)
        mac(f"evWinF{sh}", None); mac(f"nbevWinF{sh}", None)
        mac(f"rsq{sh}", d.get("r2"), 3)
        for s, ss in SH_S.items():                          # E4 per-session full-block figures
            f = d.get("full", {}).get(s, {})
            mac(f"eFull{sh}{ss}", f.get("func", {}).get("energy_per_bin_nJ"), 3); mac(f"nbFull{sh}{ss}", f.get("func", {}).get("tb", {}).get("bins"), 6)
            tb = f.get("func", {}).get("tb", {}); mac(f"evFull{sh}{ss}", (tb["events"] / tb["bins"]) if tb.get("bins") else None, 3)
            pb = f.get("func_perbin") or {}; mac(f"eFullMin{sh}{ss}", pb.get("e_bin_min_nJ"), 3); mac(f"eFullMax{sh}{ss}", pb.get("e_bin_max_nJ"), 3)
            mac(f"eSdfW{sh}{ss}", f.get("sdf", {}).get("energy_per_bin_nJ"), 3); mac(f"nbSdfW{sh}{ss}", f.get("sdf", {}).get("tb", {}).get("bins"), 5)
            tbs = f.get("sdf", {}).get("tb", {}); mac(f"evSdfW{sh}{ss}", (tbs["events"] / tbs["bins"]) if tbs.get("bins") else None, 3)
            ffe = f.get("func", {}).get("energy_per_bin_nJ"); fse = f.get("sdf", {}).get("energy_per_bin_nJ")
            mac(f"gFull{sh}{ss}", None)
        fs = [v["func"]["energy_per_bin_nJ"] for v in d.get("full", {}).values() if "func" in v]
        mac(f"eFullMean{sh}", float(np.mean(fs)) if len(fs) == 3 else None, 3)
    e0 = out.get("bmi_snn_top", {}).get("event", {}).get("energy_per_bin_nJ")
    for name, cfg in DESIGNS5.items():
        if name == "bmi_snn_top": continue
        e1 = out.get(name, {}).get("event", {}).get("energy_per_bin_nJ"); mac(f"gain{cfg['sh']}", (e0 / e1) if (e0 and e1) else None, 3)
    def _area(n): return out.get(n, {}).get("pnr", {}).get("instance_area_um2")
    def _leak(n): return out.get(n, {}).get("idle", {}).get("leakage_uW")
    def _e(n, k="event"): return out.get(n, {}).get(k, {}).get("energy_per_bin_nJ")
    def _esdf(n): return _e(n, "event_sdf") or _e(n)
    def ratio(a, b): return (a / b) if (a and b) else None
    mac("areaRatioRf", ratio(_area("bmi_snn_scmem"), _area("bmi_snn_top")), 2); mac("leakRatioRf", ratio(_leak("bmi_snn_scmem"), _leak("bmi_snn_top")), 2)
    mac("areaRatioLmRf", ratio(_area("bmi_snn_lmem"), _area("bmi_snn_scmem")), 2); mac("leakRatioLmRf", ratio(_leak("bmi_snn_lmem"), _leak("bmi_snn_scmem")), 2)
    mac("gainGate", ratio(_e("bmi_snn_min"), _e("bmi_snn_ming")), 2); mac("gainTwelve", ratio(_e("bmi_snn_ming"), _e("bmi_snn_m12")), 3)
    mac("gainSpVsTwelve", ratio(_e("bmi_snn_m12"), _e("bmi_snn_sp")), 2); mac("gainSpEVsTwelve", ratio(_e("bmi_snn_m12"), _e("bmi_snn_g64p125")), 2)
    mac("gainMinSp", ratio(_e("bmi_snn_min"), _e("bmi_snn_sp")), 2); mac("gainMinSpE", ratio(_e("bmi_snn_min"), _e("bmi_snn_g64p125")), 2)
    sw = {}
    try: sw = json.load(open(ROOT / "results/explore/software.json"))
    except Exception: pass
    ecpu_tuned = (sw.get("_tuned_5m") or sw.get("_tuned") or {}).get("energy_per_bin_nJ_ref"); ecpu_o2 = (sw.get("o2_5m") or sw.get("o2") or {}).get("energy_per_bin_nJ_ref")
    mac("gainCpuMinH", ratio(ecpu_tuned, _esdf("bmi_snn_min32")), 3); mac("gainCpuBest", ratio(ecpu_tuned, _esdf("bmi_snn_sp")), 3)
    mac("gainCpuIso", ratio(ecpu_tuned, _esdf("bmi_snn_m12")), 3)                       # iso-accuracy ratio (12-bit gated dense core, R2 0.582)
    mac("gainCpuOtwoMinH", ratio(ecpu_o2, _esdf("bmi_snn_min32")), 3); mac("gainCpuOtwoBest", ratio(ecpu_o2, _esdf("bmi_snn_sp")), 3)
    mac("gainSeqSpSdf", ratio(_esdf("bmi_snn_top"), _esdf("bmi_snn_sp")), 3); mac("gainSeqIsoSdf", ratio(_esdf("bmi_snn_top"), _esdf("bmi_snn_m12")), 3)
    L.append("\\newcommand{\\bestCore}{hardwired 12-bit, gated, weights pruned to 25 \\%}")
    (ROOT / "paper/numbers2.tex").write_text("\n".join(L) + "\n")
    # 50 MHz macros with the suffix AtFifty, from the superseded file
    old = ROOT / "paper/_superseded/2026-09-19_before_round5/numbers2.tex"
    if old.exists():
        txt = re.sub(r"\\newcommand\{\\([A-Za-z]+)\}", r"\\newcommand{\\\1AtFifty}", old.read_text())
        (ROOT / "paper/numbers2_50mhz.tex").write_text("% 50 MHz values of the previous round (numbers2.tex before round 5), macro names with the suffix AtFifty\n" + txt)
    # ---- table (E1 point 3): one row per core
    hdr = ["Core", "Weights", "Bits", "$\\Rsq$", "Util.", "Area", "Cells", "Setup", "Hold", "Cyc.", "$E_{\\mathrm{bin}}$", "$E_{\\mathrm{bin}}$ ann.", "Leak.\\ logic", "Leak.\\ total", "$P_{\\mathrm{stop}}$", "$P_{\\mathrm{32k}}$", "$P_{\\mathrm{5M}}$"]
    units = ["", "", "$V$/$o$", "", "\\%", "mm$^2$", "", "ns", "ns", "/bin", "nJ", "nJ", "\\si{\\micro\\watt}", "\\si{\\micro\\watt}", "\\si{\\micro\\watt}", "\\si{\\micro\\watt}", "\\si{\\micro\\watt}"]
    rows = []
    for name, cfg in DESIGNS5.items():
        d = out.get(name, {})
        if "pnr" not in d: continue
        p = d["pnr"]; e = d.get("event", {}); ls = d.get("leak_split", {})
        rows.append([TL5[name], cfg["weights"].replace("%", "\\%"), cfg["bits"], _f(d.get("r2"), 3), _f(p.get("util_target_pct"), 2), _f(p["instance_area_um2"] / 1e6), _f(p.get("stdcells"), 4),
                     _f(p.get("setup_ws_ns"), 3), _f(p.get("hold_ws_ns"), 3), _f(e.get("cycles_per_bin"), 3), _f(e.get("energy_per_bin_nJ")), _f(d.get("event_sdf", {}).get("energy_per_bin_nJ")),
                     _f(ls.get("leak_logic_uW")), _f(d.get("idle", {}).get("leakage_uW")), _f(d.get("avg_power_uW_250Hz_clkstopped_sdf")), _f(d.get("avg_power_uW_250Hz_clk32k")), _f(d.get("avg_power_uW_250Hz_clk5MHz"))])
    body = " & ".join(hdr) + " \\\\\n" + " & ".join(units) + " \\\\\n\\midrule\n" + "\n".join(" & ".join(r) + " \\\\" for r in rows)
    (ROOT / "paper/designs_table.tex").write_text("\\begin{tabular}{@{}llcc r rr rr r rr rr rrr@{}}\n\\toprule\n" + body + "\n\\bottomrule\n\\end{tabular}%\n")
    # ---- markdown
    md = ["| core | util % | area mm2 | cells | setup ns | hold ns | cyc/bin | E nJ | E ann. nJ | leak logic uW | leak total uW | P_stop uW | P_32k uW | P_5M uW | E full blocks (A/B/C) nJ |", "|---" * 15 + "|"]
    for name, d in out.items():
        p = d["pnr"]; e = d.get("event", {}); ls = d.get("leak_split", {}); fb = [_f(d["full"].get(s, {}).get("func", {}).get("energy_per_bin_nJ")) for s in SESS]
        md.append(f"| {name} | {_f(p.get('util_target_pct'),2)} | {_f(p['instance_area_um2']/1e6)} | {_f(p.get('stdcells'),4)} | {_f(p.get('setup_ws_ns'),3)} | {_f(p.get('hold_ws_ns'),3)} | {_f(e.get('cycles_per_bin'))} | {_f(e.get('energy_per_bin_nJ'))} | {_f(d.get('event_sdf',{}).get('energy_per_bin_nJ'))} | {_f(ls.get('leak_logic_uW'))} | {_f(d.get('idle',{}).get('leakage_uW'))} | {_f(d.get('avg_power_uW_250Hz_clkstopped_sdf'))} | {_f(d.get('avg_power_uW_250Hz_clk32k'))} | {_f(d.get('avg_power_uW_250Hz_clk5MHz'))} | {'/'.join(fb)} |")
    (ROOT / "results/DESIGNS.md").write_text("# Core variants, round 5 (sky130 TT 1.8 V 25 C, 5 MHz, per-pin OpenSTA power)\n\n" + "\n".join(md) + "\n"); print("\n".join(md))

def write_compare_50_vs_5(out):
    """E1 point 3: change table against the 50 MHz hardenings (macros of the superseded numbers2.tex) -> results/DESIGNS_50_vs_5.md"""
    old = ROOT / "paper/_superseded/2026-09-19_before_round5/numbers2.tex"
    if not old.exists(): return
    mac = dict(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}\{([^}]*)\}", old.read_text()))
    def g(k):
        v = mac.get(k, "--").replace(",", "")
        try: return float(v)
        except ValueError: return None
    L = ["| core | util 50->5 % | area mm2 50 -> 5 | cells 50 -> 5 | E_bin nJ 50 -> 5 (zero-delay) | E_bin ann. nJ 50 -> 5 | leak uW 50 -> 5 | P_avg uW 50 -> 5 (clock stopped) |", "|---" * 8 + "|"]
    for name, cfg in DESIGNS5.items():
        d = out.get(name)
        if not d or "pnr" not in d: continue
        sh = cfg["sh"]; p = d["pnr"]; e = d.get("event", {}); es = d.get("event_sdf", {}); i = d.get("idle", {})
        def pair(a, b, nd=3): return f"{_f(a, nd)} -> {_f(b, nd)}" + (f" ({(b / a - 1) * 100:+.0f} %)" if (a and b) else "")
        L.append(f"| {name} | {_f(g('util' + sh) or None, 2)} -> {_f(p.get('util_target_pct'), 2)} | {pair(g('area' + sh), p['instance_area_um2'] / 1e6)} | {pair(g('cells' + sh), p.get('stdcells'), 4)} | "
                 f"{pair(g('e' + sh), e.get('energy_per_bin_nJ'))} | {pair(g('eSdf' + sh), es.get('energy_per_bin_nJ'))} | {pair(g('leak' + sh), i.get('leakage_uW'))} | {pair(g('pavgStop' + sh), d.get('avg_power_uW_250Hz_clkstopped'))} |")
    (ROOT / "results/DESIGNS_50_vs_5.md").write_text("# 50 MHz (rounds 1-4) against 5 MHz with the utilization policy (round 5)\n\n" + "\n".join(L) + "\n")

if __name__ == "__main__":
    out = collect(); write_outputs(out); write_compare_50_vs_5(out)
