#!/usr/bin/env python3
"""Round 10: collect the real-time power measurements (sim/measure_rt.sh, sim/measure_rt_pdk.sh, sim/run_riscv_rt.sh) into
results/table2_round10.csv (Table 2 rows: table and appendix), results/table3_round10.csv (kit rows), results/grid_round10.csv
(energy-accuracy grid) and the LaTeX bodies deliverables_round10/tables/table{2,3}_round10.tex. Every number comes from the OpenSTA
report of the real-time run (P_total, P_internal, P_switching, P_leakage), with the root-clock correction applied and reported
separately; E_bin = P_avg x 4 ms, E_dyn = (P_avg - P_leak) x 4 ms. The round-7 sums (active-window energy x 250/s + leakage) are
carried along for the consistency check only. Usage: collect_round10.py [--out deliverables_round10]"""
import json, csv, re, sys, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fmt3 import sig
from collect_results import parse_group_table, parse_metrics
ROOT = Path(__file__).resolve().parent.parent
OUTD = ROOT / (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "deliverables_round10")
BIN_S = 4e-3; RATE = 250.0
D = json.load(open(ROOT / "results/designs.json")); P5 = json.load(open(ROOT / "results/pdks5.json")); C5 = json.load(open(ROOT / "results/corners5.json")) if (ROOT / "results/corners5.json").exists() else {}
VB = {t: json.load(open(ROOT / f"results/explore/vbits_{t}.json")) for t in ("H64_th256_k44_drop", "H32_th256_k44_drop", "H16_th256_k44_drop", "H64_th256_k44_drop_p0.25") if (ROOT / f"results/explore/vbits_{t}.json").exists()}
PY = str(ROOT / ".venv/bin/python")

def rt_run(tag, netlist=None, out=None, build=None):
    """one real-time measurement: power/out_<tag>/ (+ _zero), sim/build_<tag>/vvp.log"""
    out = Path(out) if out else ROOT / f"power/out_{tag}"; build = Path(build) if build else ROOT / f"sim/build_{tag}"
    rpt = out / "power_vcd.rpt"
    if not rpt.exists(): return None
    if not (out / "root_clock_correction.json").exists(): return None      # the measurement chain is complete only once the correction has been written
    g = parse_group_table(rpt); tot = g["Total"]
    r = dict(tag=tag, p_total_unc_uW=tot["total"] * 1e6, p_int_unc_uW=tot["internal"] * 1e6, p_sw_unc_uW=tot["switching"] * 1e6, p_leak_uW=tot["leakage"] * 1e6,
             groups_unc={k: {q: v[q] * 1e6 for q in ("internal", "switching", "leakage", "total")} for k, v in g.items()})
    rc = out / "root_clock_correction.json"
    if rc.exists():
        j = json.load(open(rc)); c = j["corrected"]["Total"]; rem = j["removed_W"]
        # the corrected total is the OpenSTA report total (group table) minus the removed root-network power; the per-instance sum
        # that the correction script works on exceeds the group total by up to 1 % on the largest netlists (listed as p_total_bi_uW)
        ri = j.get("removed_internal_W"); rs_ = j.get("removed_switching_W")
        p_int = (tot["internal"] - (ri if ri is not None else rem * (c["internal"] and (j["reported"]["Total"]["internal"] - c["internal"]) / max(rem, 1e-30)))) * 1e6 if ri is not None else None
        r.update(root_corrected=True, root_duty=j["duty"], root_cells=j["root_cells"], root_removed_uW=rem * 1e6, p_total_bi_uW=c["total"] * 1e6,
                 p_total_uW=(tot["total"] - rem) * 1e6, p_int_uW=(tot["internal"] - (ri if ri is not None else (j["reported"]["Total"]["internal"] - c["internal"]))) * 1e6,
                 p_sw_uW=(tot["switching"] - (rs_ if rs_ is not None else (j["reported"]["Total"]["switching"] - c["switching"]))) * 1e6,
                 groups_corr={k: {q: v[q] * 1e6 for q in ("internal", "switching", "leakage", "total")} for k, v in j["corrected"].items()},
                 groups_rep={k: {q: v[q] * 1e6 for q in ("internal", "switching", "leakage", "total")} for k, v in j["reported"].items()})
    else:
        r.update(root_corrected=False, root_duty=None, root_cells={}, root_removed_uW=0.0, p_total_uW=r["p_total_unc_uW"], p_int_uW=r["p_int_unc_uW"], p_sw_uW=r["p_sw_unc_uW"])
    r["p_dyn_uW"] = r["p_int_uW"] + r["p_sw_uW"]; r["p_avg_uW"] = r["p_total_uW"]
    r["e_bin_nJ"] = r["p_avg_uW"] * 1e-6 * BIN_S * 1e9; r["e_dyn_nJ"] = (r["p_avg_uW"] - r["p_leak_uW"]) * 1e-6 * BIN_S * 1e9
    log = build / "vvp.log"
    if log.exists():
        s = log.read_text(errors="replace")
        m = re.search(r"SUMMARY: bins=(\d+) events=(\d+) errors=(\d+) cycles=(\d+) active_cycles=(\d+)", s)
        if m: r.update(bins=int(m.group(1)), events=int(m.group(2)), errors=int(m.group(3)), events_per_bin=int(m.group(2)) / int(m.group(1)))
        m = re.search(r"RT: bins=(\d+) clk_cycles_in_window=(\d+)(?: awake_cycles_in_window=(\d+))? active_ns_mean=(\d+) active_ns_max=(\d+) overruns=(\d+) window_ns=(\d+)", s)
        if m:
            r.update(bins=int(m.group(1)), clk_cycles=int(m.group(2)), active_ns_mean=int(m.group(4)), active_ns_max=int(m.group(5)), overruns=int(m.group(6)), window_s=int(m.group(7)) * 1e-9)
            r["cycles_per_bin"] = r["clk_cycles"] / r["bins"]
            if m.group(3): r["awake_cycles"] = int(m.group(3))
        m = re.search(r"SIM_WALLCLOCK_S (\d+)", s); r["sim_wallclock_min"] = int(m.group(1)) / 60 if m else None
        r["pass"] = "PASS" in s
    # round 10 (state-dependent tables under a stopped clock): the macro state correction (SRAM22 ce/we at the duty conditioned on the
    # macro clock running; power/macro_state_correction.py) and the conditional-duty evaluation (every duty from the clocked cycles,
    # power/out_<tag>_cond) are carried as separately reported corrections; the policy numbers above stay untouched
    msc = out / "macro_state_correction.json"
    if msc.exists():
        j = json.load(open(msc)); r["macro_corr_uW"] = j["added_W"] * 1e6
        r["macro_corr_pins"] = {n: {p: (v["duty_window"], v["duty_conditional"], v["v_idle"]) for p, v in rec["pins"].items()} for n, rec in (j.get("macro_cond") or {}).items()}
        r["p_avg_mc_uW"] = r["p_avg_uW"] + r["macro_corr_uW"]; r["p_dyn_mc_uW"] = r["p_dyn_uW"] + r["macro_corr_uW"]
        r["e_bin_mc_nJ"] = r["p_avg_mc_uW"] * 1e-6 * BIN_S * 1e9; r["e_dyn_mc_nJ"] = r["p_dyn_mc_uW"] * 1e-6 * BIN_S * 1e9
    cond = Path(str(out) + "_cond") / "root_clock_correction.json"
    if cond.exists() and (Path(str(out) + "_cond") / "power_vcd.rpt").exists():
        j = json.load(open(cond)); gc = parse_group_table(Path(str(out) + "_cond") / "power_vcd.rpt")["Total"]; asum = Path(str(out) + "_cond") / "activity_summary.json"
        r["p_dyn_cond_uW"] = (gc["internal"] + gc["switching"] - j["removed_W"]) * 1e6; r["p_leak_cond_uW"] = gc["leakage"] * 1e6          # leakage of the cond run is listed, not used
        r["p_avg_cond_uW"] = r["p_leak_uW"] + r["p_dyn_cond_uW"]; r["e_dyn_cond_nJ"] = r["p_dyn_cond_uW"] * 1e-6 * BIN_S * 1e9; r["e_bin_cond_nJ"] = r["p_avg_cond_uW"] * 1e-6 * BIN_S * 1e9
        if asum.exists(): a_ = json.load(open(asum)); r["cond_gate_var"] = a_.get("gate_var"); r["cond_gate_frac"] = (a_.get("gate_high_s") or 0) / a_["duration_s"] if a_.get("duration_s") else None
    cov = out / "annot_coverage.json"
    if not cov.exists() and netlist and Path(netlist).exists():
        subprocess.run([PY, str(ROOT / "sw/annot_coverage.py"), str(netlist), str(out)], capture_output=True)
    if cov.exists(): r["pins_annotated_frac"] = json.load(open(cov))["coverage"]
    return r

def nodecap(tag, run0=None, run1=None):
    """E10: the decap-free refill measured on the recorded real-time toggles (power/out_<tag>_nodecap), with the leakage by cell class of both fills"""
    out1 = ROOT / f"power/out_{tag}_nodecap"; out0 = ROOT / f"power/out_{tag}"
    if not (out1 / "root_clock_correction.json").exists(): return {}
    r1 = rt_run(f"{tag}_nodecap", out=out1, build=ROOT / f"sim/build_{tag}")
    res = dict(nd_p_total_unc_uW=r1["p_total_unc_uW"], nd_p_total_uW=r1["p_total_uW"], nd_p_leak_uW=r1["p_leak_uW"], nd_p_dyn_uW=r1["p_dyn_uW"], nd_p_avg_uW=r1["p_avg_uW"], nd_e_bin_nJ=r1["e_bin_nJ"], nd_e_dyn_nJ=r1["e_dyn_nJ"], nd_root_removed_uW=r1["root_removed_uW"], nd_pins_annotated_frac=r1.get("pins_annotated_frac"))
    r0 = rt_run(tag, out=out0, build=ROOT / f"sim/build_{tag}")
    for lab, o, rr in (("", out0, r0), ("nd_", out1, r1)):
        lc = o / "leak_classes.json"
        if lc.exists():
            j = json.load(open(lc)); ssum = sum((j.get(k, {}).get("leak_uW") or 0) for k in ("logic", "fill", "decap", "tap", "diode", "endcap"))
            sc = (rr["p_leak_uW"] / ssum) if (rr and ssum) else 1.0        # classes from the per-instance report, scaled to the report_power leakage (see run log)
            for k in ("logic", "fill", "decap", "tap", "diode"): res[f"{lab}leak_{k}_uW"] = (j.get(k, {}).get("leak_uW") or 0) * sc if k in j else None; res[f"{lab}n_{k}"] = j.get(k, {}).get("n")
            res[f"{lab}leak_class_scale"] = sc
    rf = out1 / "refill.json"
    if rf.exists():
        j = json.load(open(rf)); res.update(refill_drc=j.get("route_drc_errors_original"), refill_setup_ws_ns=j.get("setup_ws_ns_refill"), refill_hold_ws_ns=j.get("hold_ws_ns_refill"), refill_cells=j.get("cells_refill"))
    return res

def old_sum(d, kind):
    """round-7 sum for the consistency check: active-window energy (nJ) x 250/s + idle leakage; kind selects the window"""
    if not d or not d.get("idle"): return (None, None)
    lk = d["idle"]["leakage_uW"]; e = None
    fb = d.get("full", {}).get("indy_20160630_01", {})
    if kind == "sdf_block": e = (fb.get("sdf") or {}).get("energy_per_bin_nJ")
    elif kind == "func_block": e = (fb.get("func") or {}).get("energy_per_bin_nJ")
    elif kind == "sdf_short": e = ((fb.get("sdf_short") or {}).get("energy_per_bin_nJ")) or ((d.get("glitch") or {}).get("e_sdf_nJ"))
    elif kind == "func_short": e = (d.get("glitch") or {}).get("e_func_nJ")
    elif kind == "dense_sdf": e = (d.get("dense_sdf") or {}).get("energy_per_bin_nJ")
    elif kind == "dense_func": e = (d.get("dense") or {}).get("energy_per_bin_nJ")
    elif kind == "event_func500": e = (d.get("event") or {}).get("energy_per_bin_nJ")
    elif kind == "event_sdf200": e = (d.get("event_sdf") or {}).get("energy_per_bin_nJ")
    return (e, e * RATE * 1e-3 + lk) if e else (None, None)

def hardening(design, run_tag=None):
    run_tag = run_tag or f"{design}_5m"; rd = ROOT / f"synthesis/{design}/runs/{run_tag}"; mj = rd / "final/metrics.json"
    if not mj.exists(): return {}
    p = parse_metrics(mj); m = json.load(open(mj))
    cu = ROOT / f"synthesis/{design}/config_5mhz_used.yaml"; mu = re.search(r"^FP_CORE_UTIL:\s*(\d+)", cu.read_text(), flags=re.M) if cu.exists() else None
    return dict(util_pct=int(mu.group(1)) if mu else None, area_mm2=(p.get("instance_area_um2") or 0) / 1e6 or None, cells=p.get("stdcells"), setup_ws_ns=m.get("timing__setup__ws"), hold_ws_ns=m.get("timing__hold__ws"), drc=m.get("route__drc_errors"), run=str(rd.resolve().name))

def r2_of(src):
    kind = src[0]
    if kind == "design": return (D.get(src[1]) or {}).get("r2")
    if kind == "vbits": return (VB.get(src[1]) or {}).get(src[2], {}).get("mean")
    return None

# ---------------- Table 2 rows: (key, paper label, table/appendix, design, weights, bits, r2 source, runs [(kind, md, nb, role)])
NB_FULL = 5000
T2 = [
 ("soc_tuned", "1: RISC-V SoC", "table", "soc_tuned", "SRAM (data memory)", "32-bit int", ("vbits", "H64_th256_k44_drop", "v20_o24"), "soc"),
 ("soc_o2", "1: RISC-V SoC (-O2 firmware)", "appendix", "soc_o2", "SRAM (data memory)", "32-bit int", ("vbits", "H64_th256_k44_drop", "v20_o24"), "soc"),
 ("top_dense", "2: Sequential core, SRAM block, dense mode (ungated)", "appendix", "bmi_snn_top", "SRAM block", "20 / 24", ("design", "bmi_snn_top"), [("sdf", 1, 500, "table"), ("func", 1, 2000, "check"), ("func", 1, 100, "check"), ("sdf", 1, 40, "check")]),
 ("top_event", "2: Sequential core, SRAM block, event mode (ungated)", "appendix", "bmi_snn_top", "SRAM block", "20 / 24", ("design", "bmi_snn_top"), [("sdf", 0, 2000, "table")]),
 ("topg_dense", "2: Sequential core, SRAM block, dense mode", "table", "bmi_snn_topg", "SRAM block", "20 / 24", ("design", "bmi_snn_topg"), [("sdf", 1, 500, "table"), ("func", 1, 2000, "check"), ("func", 1, 100, "check"), ("sdf", 1, 40, "check")]),
 ("topg_event", "2: Sequential core, SRAM block, event mode", "table", "bmi_snn_topg", "SRAM block", "20 / 24", ("design", "bmi_snn_topg"), [("sdf", 0, 2000, "table")]),
 ("scmem", "3: Parallel core, flip-flop weight memory (ungated)", "appendix", "bmi_snn_scmem", "flip-flops", "20 / 24", ("design", "bmi_snn_scmem"), [("sdf", 0, 50, "table"), ("func", 0, NB_FULL, "check")]),
 ("scmemg", "3: Parallel core, flip-flop weight memory", "table", "bmi_snn_scmemg", "flip-flops", "20 / 24", ("design", "bmi_snn_scmem"), [("sdf", 0, 50, "table"), ("func", 0, NB_FULL, "check")]),
 ("lmem2", "4: Parallel core, latch weight memory (ungated)", "appendix", "bmi_snn_lmem2", "latches", "20 / 24", ("design", "bmi_snn_lmem2"), [("sdf", 0, 50, "table"), ("func", 0, NB_FULL, "check")]),
 ("lmem2g", "4: Parallel core, latch weight memory", "table", "bmi_snn_lmem2g", "latches", "20 / 24", ("design", "bmi_snn_lmem2"), [("sdf", 0, 50, "table"), ("func", 0, NB_FULL, "check")]),
 ("lmin2", "4: Parallel core, latch weight memory, 12-bit", "table", "bmi_snn_lmin2", "latches", "12 / 14", ("design", "bmi_snn_lmin2"), [("sdf", 0, 50, "table"), ("func", 0, NB_FULL, "check")]),
 ("hw", "5: Hardwired, 20-bit (ungated)", "appendix", "bmi_snn_hw", "constants", "20 / 24", ("design", "bmi_snn_hw"), [("sdf", 0, NB_FULL, "table")]),
 ("hwg", "5: Hardwired, 20-bit", "table", "bmi_snn_hwg", "constants", "20 / 24", ("design", "bmi_snn_hw"), [("sdf", 0, NB_FULL, "table")]),
 ("min", "5: Hardwired, 16-bit (ungated)", "appendix", "bmi_snn_min", "constants", "16 / 16", ("design", "bmi_snn_min"), [("sdf", 0, NB_FULL, "table")]),
 ("ming", "5: Hardwired, 16-bit", "table", "bmi_snn_ming", "constants", "16 / 16", ("design", "bmi_snn_ming"), [("sdf", 0, NB_FULL, "table")]),
 ("m12", "5: Hardwired, 12-bit", "table", "bmi_snn_m12", "constants", "12 / 14", ("design", "bmi_snn_m12"), [("sdf", 0, NB_FULL, "table")]),
 ("sp", "5: Hardwired, 12-bit, 25 % of synapses kept (pruned core)", "table", "bmi_snn_sp", "constants (25 %)", "12 / 14", ("design", "bmi_snn_sp"), [("sdf", 0, NB_FULL, "table")]),
 ("min32", "5: Hardwired, 16-bit, H=32 (ungated)", "appendix", "bmi_snn_min32", "constants", "16 / 16", ("design", "bmi_snn_min32"), [("sdf", 0, NB_FULL, "table")]),
 ("min32g", "5: Hardwired, 16-bit, H=32", "table", "bmi_snn_min32g", "constants", "16 / 16", ("vbits", "H32_th256_k44_drop", "v16_o16"), [("sdf", 0, NB_FULL, "table")]),
 ("g32", "5: Hardwired, 12-bit, H=32", "table", "bmi_snn_g32", "constants", "12 / 14", ("vbits", "H32_th256_k44_drop", "v12_o14"), [("sdf", 0, NB_FULL, "table")]),
 ("g32p50", "5: Hardwired, 12-bit, H=32, 50 % of synapses kept", "table", "bmi_snn_g32p50", "constants (50 %)", "12 / 14", ("design", "bmi_snn_g32p50"), [("sdf", 0, NB_FULL, "table")]),
 ("min16", "5: Hardwired, 16-bit, H=16", "appendix", "bmi_snn_min16", "constants", "16 / 16", ("design", "bmi_snn_min16"), [("sdf", 0, NB_FULL, "table")]),
 ("g16", "5: Hardwired, 12-bit, H=16 (grid point)", "appendix", "bmi_snn_g16", "constants", "12 / 14", ("vbits", "H16_th256_k44_drop", "v12_o14"), [("sdf", 0, NB_FULL, "table")]),
 ("fe", "Digital front end", "table", "bmi_fe", "--", "--", None, "fe"),
]
rows2 = []; CHECK = []
def consistency(design, kind, nb, md, r):
    d = D.get(design)
    if md == 1: ok = "dense_sdf" if kind == "sdf" else "dense_func"
    elif design in ("bmi_snn_scmem", "bmi_snn_lmem2", "bmi_snn_lmin2", "bmi_snn_scmemg", "bmi_snn_lmem2g"): ok = ("sdf_short" if kind == "sdf" else "func_block")
    else: ok = "sdf_block" if kind == "sdf" else "func_block"
    e_old, p_old = old_sum(d, ok)
    res = dict(old_kind=ok, e_old_nJ=e_old, p_old_uW=p_old, dev_pct=((r["p_avg_uW"] / p_old - 1) * 100) if (p_old and r) else None)
    if p_old and r:
        if r.get("p_avg_mc_uW") is not None: res["dev_mc_pct"] = (r["p_avg_mc_uW"] / p_old - 1) * 100
        if r.get("p_avg_cond_uW") is not None: res["dev_cond_pct"] = (r["p_avg_cond_uW"] / p_old - 1) * 100
        lk = (d.get("idle") or {}).get("leakage_uW")
        if lk is not None and e_old: res.update(leak_old_uW=lk, e_dyn_old_nJ=e_old, dev_leak_pct=(r["p_leak_uW"] / lk - 1) * 100 if lk else None)   # e_old: active-window energy (its leakage share < 0.3 %)
    return res
for key, label, where, design, weights, bits, r2src, runs in T2:
    base = dict(key=key, label=label, where=where, design=design, weights=weights, bits=bits, r2=r2_of(r2src) if r2src else None)
    if runs == "soc":
        fw = "tuned" if key == "soc_tuned" else "o2"; tag = f"riscv_rt_5m_{fw}_rt100"
        r = rt_run(tag, netlist=ROOT / "../skywater/synthesis/sky130_vex2_soc/runs/sky130_vex2_soc_5m/final/nl/sky130_vex2_soc.nl.v")
        h = {}
        mj = ROOT / "../skywater/synthesis/sky130_vex2_soc/runs/sky130_vex2_soc_5m/final/metrics.json"
        if mj.exists(): p = parse_metrics(mj); m = json.load(open(mj)); h = dict(area_mm2=(p.get("instance_area_um2") or 0) / 1e6, cells=p.get("stdcells"), setup_ws_ns=m.get("timing__setup__ws"), hold_ws_ns=m.get("timing__hold__ws"), drc=m.get("route__drc_errors"), util_pct=None)
        old = json.load(open(ROOT / "results/explore/software6.json")).get(f"{fw}_5m_100") if (ROOT / "results/explore/software6.json").exists() else None
        chk = dict(old_kind="soc_100bin_window", e_old_nJ=old["energy_per_bin_nJ"] if old else None, p_old_uW=old["avg_power_uW_250Hz_clkstopped"] if old else None)
        if r and chk["p_old_uW"]:
            chk["dev_pct"] = (r["p_avg_uW"] / chk["p_old_uW"] - 1) * 100
            if r.get("p_avg_mc_uW") is not None: chk["dev_mc_pct"] = (r["p_avg_mc_uW"] / chk["p_old_uW"] - 1) * 100
            if r.get("p_avg_cond_uW") is not None: chk["dev_cond_pct"] = (r["p_avg_cond_uW"] / chk["p_old_uW"] - 1) * 100
        if r: r["events_per_bin"] = 4.95; r["events"] = 495; r["cycles_per_bin"] = r.get("cycles_per_bin")
        st = "pending"
        if r:
            st = "ok" if r.get("pass") else "FAILED"
            if not r.get("pass") and r.get("overruns") and "tohost=00000001" in (ROOT / f"sim/build_{tag}/vvp.log").read_text(errors="replace"):
                st = f"real-time missed: {r['overruns']} of {r['bins']} bins overrun (decode correct, power evaluated over the same 0.4 s)"
        rows2.append(dict(base, run_kind="sdf", dense=0, window_bins=100, role="table", status=st, **h, **(r or {}), **chk, **(nodecap(tag) if r else {}))); continue
    if runs == "fe":
        out = ROOT / "power/out_rt_fe_v3_gls_5m"                               # round 10: the front end re-evaluated through the toggle chain (coverage, zero run, correction)
        if not (out / "root_clock_correction.json").exists(): out = ROOT / "power/out_vcd_fe_v3_gls_5m"
        if (out / "root_clock_correction.json").exists():
            r = rt_run("fe_v3_gls_5m", out=out, build=ROOT / "sim/build_fe_gls")
            F = json.load(open(ROOT / "results/frontend.json")); tb = F["tb"]
            r.update(bins=tb["bins"], events=tb["events"], events_per_bin=tb["events"] / tb["bins"], clk_cycles=tb["clk5_cycles"], cycles_per_bin=tb["clk5_cycles"] / tb["bins"], window_s=tb["bins"] * 131 / 32768.0, pass_=tb["pass"], root_duty=F["osc_duty"])
            h = dict(area_mm2=F["pnr"]["area_um2"] / 1e6, cells=F["pnr"]["cells"], util_pct=F["pnr"]["util_target_pct"], setup_ws_ns=F["pnr"]["setup_ws_ns"], hold_ws_ns=F["pnr"]["hold_ws_ns"], drc=F["pnr"]["drc"])
            chk = dict(old_kind="fe_round6", e_old_nJ=None, p_old_uW=F["power"]["total_uW"], dev_pct=(r["p_avg_uW"] / F["power"]["total_uW"] - 1) * 100)
            rows2.append(dict(base, run_kind="sdf_vcd", dense=0, window_bins=500, role="table", status="ok" if tb["pass"] else "FAILED", **h, **r, **chk))
        continue
    h = hardening(design)
    nl = ROOT / f"synthesis/{design}/runs/{design}_5m/final/nl/{design}.nl.v"
    for kind, md, nb, role in runs:
        tag = f"rt_{design}_5m_{kind}_md{md}_w{nb}_indy_20160630_01"; r = rt_run(tag, netlist=nl)
        if not r: rows2.append(dict(base, run_kind=kind, dense=md, window_bins=nb, role=role, status="pending", **h)); continue
        chk = consistency(design, kind, nb, md, r)
        if chk.get("leak_old_uW") is not None and chk.get("p_old_uW"):
            chk["e_dyn_old_nJ"] = (chk["p_old_uW"] - chk["leak_old_uW"]) / RATE * 1e3; chk["dev_dyn_pct"] = (r["e_dyn_nJ"] / chk["e_dyn_old_nJ"] - 1) * 100 if chk["e_dyn_old_nJ"] else None
            if r.get("e_dyn_mc_nJ") is not None and chk["e_dyn_old_nJ"]: chk["dev_dyn_mc_pct"] = (r["e_dyn_mc_nJ"] / chk["e_dyn_old_nJ"] - 1) * 100
            if r.get("e_dyn_cond_nJ") is not None and chk["e_dyn_old_nJ"]: chk["dev_dyn_cond_pct"] = (r["e_dyn_cond_nJ"] / chk["e_dyn_old_nJ"] - 1) * 100
        rows2.append(dict(base, run_kind=kind, dense=md, window_bins=nb, role=role, status="ok" if r.get("pass") else "FAILED", **h, **r, **chk, **nodecap(tag)))

# ---------------- Table 3: kits (pruned core)
T3 = [("sky130", "SkyWater sky130", "1.8", "rt_bmi_snn_sp_5m_sdf_md0_w5000_indy_20160630_01", "sky130/sp", None),
      ("sky130_lv", "SkyWater sky130, re-hardened at 1.28 V", "1.28", "rt_bmi_snn_sp_5m_lv_sdf_md0_w5000_indy_20160630_01", "sky130/sp", "lv"),
      ("sky130_nodecap", "SkyWater sky130, fill without decap cells", "1.8", "rt_bmi_snn_sp_5m_sdf_md0_w5000_indy_20160630_01_nodecap", "sky130/sp", "nodecap"),
      ("gf180", "GlobalFoundries GF180MCU", "5", "rt_pdk_gf180_sp_sdf_w5000", "gf180/sp", None),
      ("gf180_1v8", "GlobalFoundries GF180MCU, re-evaluated at 1.8 V", "1.8", "rt_pdk_gf180_sp_sdf_w5000_tt_025C_1v80", "gf180/sp", "1v8"),
      ("gf180_3v3", "GlobalFoundries GF180MCU, re-evaluated at 3.3 V", "3.3", "rt_pdk_gf180_sp_sdf_w5000_tt_025C_3v30", "gf180/sp", "3v3"),
      ("ihp", "IHP SG13G2", "1.2", "rt_pdk_ihp_sp_sdf_w5000", "ihp/sp", None),
      ("ihp_nodecap", "IHP SG13G2, fill without decap cells", "1.2", "rt_pdk_ihp_sp_nodecap_sdf_w5000", "ihp/sp", "nodecap"),
      ("nangate45", "NanGate45 / FreePDK45 (predictive, zero-delay)", "1.1", "rt_pdk_nangate45_sp_func_w5000", "nangate45/sp", None),
      ("asap7", "ASAP7 RVT (predictive)", "0.7", "rt_pdk_asap7_sp_sdf_w5000", "asap7/sp", None),
      ("asap7sram", "ASAP7 SRAM-Vt (predictive, low leakage)", "0.7", "rt_pdk_asap7sram_sp_sdf_w5000", "asap7sram/sp", None)]
rows3 = []
for key, label, volt, tag, pk, variant in T3:
    pd = P5.get(pk) or {}; pnr = pd.get("pnr") or {}
    build = None
    if tag.startswith("rt_pdk_"):
        m = re.match(r"rt_pdk_(\w+?)_(sp)(_nodecap)?_(sdf|func)_w(\d+)", tag); build = ROOT / f"sim/build_rt_pdk_{m.group(1)}_{m.group(2)}_{m.group(4)}_w{m.group(5)}"
    if variant == "nodecap" and key.startswith("sky130"): build = ROOT / "sim/build_rt_bmi_snn_sp_5m_sdf_md0_w5000_indy_20160630_01"
    r = rt_run(tag, build=build)
    row = dict(key=key, label=label, kit=pk.split("/")[0], supply_V=volt, design="bmi_snn_sp", util_pct=pnr.get("util_target_pct"), area_mm2=(pnr.get("instance_area_um2") or 0) / 1e6 or None, cells=pnr.get("stdcells"),
               r2=D.get("bmi_snn_sp", {}).get("r2"), e_dyn_func500_r7_nJ=pd.get("energy_dyn_per_bin_nJ"), leak_logic_r7_uW=(pd.get("leak_split") or {}).get("leak_logic_uW"))
    if variant == "lv":
        lv = (C5.get("bmi_snn_sp") or {}).get("lv") or {}; row.update(util_pct=lv.get("util_pct"), area_mm2=(lv.get("area_um2") or 0) / 1e6 or None, cells=lv.get("cells"), e_dyn_func500_r7_nJ=None, leak_logic_r7_uW=None)
        e_old = (lv.get("e_sdf_1v28") or {}).get("energy_per_bin_nJ"); p_old = (e_old * RATE * 1e-3 + lv["leak_1v28_uW"]) if (e_old and lv.get("leak_1v28_uW") is not None) else None
    elif variant == "nodecap":
        e_old = (pd.get("event_sdf_w5000") or {}).get("energy_per_bin_nJ"); p_old = (e_old * RATE * 1e-3 + pd["leak_nodecap_uW"]) if (e_old and pd.get("leak_nodecap_uW") is not None) else None
        row["leak_logic_r7_uW"] = (pd.get("leak_split") or {}).get("leak_logic_uW")
    elif variant in ("1v8", "3v3"):
        corner = "tt_025C_1v80" if variant == "1v8" else "tt_025C_3v30"; vd = (pd.get("volt") or {}).get(corner) or {}
        e_old = vd.get("energy_per_bin_nJ"); p_old = vd.get("avg_power_uW_250Hz_clkstopped"); row["e_dyn_func500_r7_nJ"] = vd.get("energy_dyn_per_bin_nJ")
    else:
        e_old = (pd.get("event_sdf_w5000") or {}).get("energy_per_bin_nJ"); p_old = pd.get("avg_power_uW_250Hz_clkstopped_sdfw")
    row.update(e_old_nJ=e_old, p_old_uW=p_old)
    row["old_kind"] = {"lv": "sdf 200 bins at 1.28 V (round 6; the first 200 bins carry 12.6 % more dynamic energy per bin than the 5,000-bin average)", "nodecap": "sdf 5000 bins + decap-free leakage (round 6)",
                       "1v8": "zero-delay 500 bins re-evaluated (round 6; annotated/zero-delay and 5,000/500-bin ratio 1.082 at 5 V)", "3v3": "zero-delay 500 bins re-evaluated (round 6; ratio 1.082)"}.get(variant, "sdf 5000 bins (round 7, sdfw)")
    # expected value of the new window from the old one (window and delay-model ratios measured on the 1.8 V sky130 pruned core / the 5 V GF180 core)
    row["old_window_factor"] = {"lv": 1.0 / 1.126, "1v8": 1.082, "3v3": 1.082}.get(variant, 1.0)
    if r:
        row.update(status="ok" if r.get("pass", True) else "FAILED", **r, dev_pct=((r["p_avg_uW"] / p_old - 1) * 100) if p_old else None)
        if p_old and r.get("p_avg_cond_uW") is not None: row["dev_cond_pct"] = (r["p_avg_cond_uW"] / p_old - 1) * 100
        e_dyn_old = pd.get("energy_dyn_per_bin_nJ_sdfw") or pd.get("energy_dyn_per_bin_nJ")
        if variant in ("1v8", "3v3"): e_dyn_old = ((pd.get("volt") or {}).get("tt_025C_1v80" if variant == "1v8" else "tt_025C_3v30") or {}).get("energy_dyn_per_bin_nJ")
        if variant == "lv": lv_ = (C5.get("bmi_snn_sp") or {}).get("lv") or {}; e_dyn_old = ((lv_.get("e_sdf_1v28") or {}).get("energy_per_bin_nJ") or 0) - (lv_.get("leak_1v28_uW") or 0) * 1e-6 * BIN_S * 1e9 * 0 or None
        if e_dyn_old and p_old: row.update(e_dyn_old_nJ=e_dyn_old, leak_old_uW=p_old - e_dyn_old * RATE * 1e-3)
        if row.get("leak_old_uW"): row["dev_leak_pct"] = (r["p_leak_uW"] / row["leak_old_uW"] - 1) * 100
        if row.get("e_dyn_old_nJ"): row["dev_dyn_pct"] = (r["e_dyn_nJ"] / row["e_dyn_old_nJ"] - 1) * 100; row["dev_dyn_windowadj_pct"] = (r["e_dyn_nJ"] / (row["e_dyn_old_nJ"] * row["old_window_factor"]) - 1) * 100
        if row.get("e_dyn_old_nJ") and r.get("e_dyn_cond_nJ") is not None: row["dev_dyn_cond_pct"] = (r["e_dyn_cond_nJ"] / row["e_dyn_old_nJ"] - 1) * 100; row["dev_dyn_cond_windowadj_pct"] = (r["e_dyn_cond_nJ"] / (row["e_dyn_old_nJ"] * row["old_window_factor"]) - 1) * 100
    else: row["status"] = "pending"
    # logic-only leakage of this run (per-instance report, as leak_split6): fill/decap/tap/diode excluded
    out = ROOT / f"power/out_{tag}"; rpt = out / "power_vcd_by_instance.rpt"
    if rpt.exists():
        phys = re.compile(r"(fill|decap|tap|antenna|diode|endcap|FILL|DECAP|TAP)", re.I); ll = 0.0
        for line in open(rpt, errors="ignore"):
            f = line.split()
            if len(f) == 5 and not phys.search(f[4]) and not f[4].startswith("ANTENNA"):
                try: ll += float(f[2])
                except ValueError: pass
        row["leak_logic_uW"] = ll * 1e6
    rows3.append(row)

# ---------------- grid (E8, v3): sixteen 12-bit gated cores; the dense H = 32 and H = 16 points are the E5 cores g32 and g16
GRID = [("bmi_snn_g128", 128, 100, "H128_th256_k44_drop"), ("bmi_snn_g128p25", 128, 25, "H128_th256_k44_drop_p0.25"), ("bmi_snn_g128p125", 128, 12.5, "H128_th256_k44_drop_p0.125"),
        ("bmi_snn_m12", 64, 100, "H64_th256_k44_drop"), ("bmi_snn_g64p50", 64, 50, "H64_th256_k44_drop_p0.5"), ("bmi_snn_sp", 64, 25, "H64_th256_k44_drop_p0.25"), ("bmi_snn_g64p125", 64, 12.5, "H64_th256_k44_drop_p0.125"),
        ("bmi_snn_g48", 48, 100, "H48_th256_k44_drop"), ("bmi_snn_g48p50", 48, 50, "H48_th256_k44_drop_p0.5"), ("bmi_snn_g48p25", 48, 25, "H48_th256_k44_drop_p0.25"),
        ("bmi_snn_g32", 32, 100, "H32_th256_k44_drop"), ("bmi_snn_g32p50", 32, 50, "H32_th256_k44_drop_p0.5"), ("bmi_snn_g32p25", 32, 25, "H32_th256_k44_drop_p0.25"), ("bmi_snn_g32p125", 32, 12.5, "H32_th256_k44_drop_p0.125"),
        ("bmi_snn_g16", 16, 100, "H16_th256_k44_drop"), ("bmi_snn_g16p50", 16, 50, "H16_th256_k44_drop_p0.5")]
TABLE2_GRID = {"bmi_snn_m12", "bmi_snn_sp", "bmi_snn_g32p50"}
def r2_seeds(tag):
    """five-seed mean and sd of the three-session integer-reference test R2 (results/models/<sess>_<tag>[_s<k>]/eval_int.json), as collect_pareto.py"""
    import numpy as np
    SESS = ["indy_20160622_01", "indy_20160630_01", "indy_20170131_02"]; means = []
    for seed in range(5):
        v = []
        for s_ in SESS:
            f = ROOT / "results/models" / (f"{s_}_{tag}" if seed == 0 else f"{s_}_{tag}_s{seed}") / "eval_int.json"
            if f.exists(): v.append(json.load(open(f))["test_r2_int"])
        if len(v) == 3: means.append(float(np.mean(v)))
    return (float(np.mean(means)) if means else None, float(np.std(means, ddof=1)) if len(means) > 1 else None, len(means))
rowsg = []
for design, H, dens, tag_ in GRID:
    h = hardening(design); nl = ROOT / f"synthesis/{design}/runs/{design}_5m/final/nl/{design}.nl.v"
    r2m, r2sd, nseed = r2_seeds(tag_)
    rs = rt_run(f"rt_{design}_5m_sdf_md0_w5000_indy_20160630_01", netlist=nl); rf = rt_run(f"rt_{design}_5m_func_md0_w5000_indy_20160630_01", netlist=nl)
    nd = nodecap(f"rt_{design}_5m_sdf_md0_w5000_indy_20160630_01") if rs else {}
    status = "measured" if rs else ("hardening pending" if not h else ("no 5 MHz netlist" if not nl.exists() else "real-time run pending"))
    row = dict(H=H, density_pct=dens, bits="12/14", gated=1, r2_mean=r2m, r2_std=r2sd, p_dyn_uW=rs["p_dyn_uW"] if rs else None, p_leak_uW=rs["p_leak_uW"] if rs else None, p_leak_nodecap_uW=nd.get("nd_p_leak_uW"),
               area_mm2=h.get("area_mm2"), table2=1 if design in TABLE2_GRID else 0, status=status,
               design=design, util_pct=h.get("util_pct"), cells=h.get("cells"), cycles_per_bin=rs.get("cycles_per_bin") if rs else None, p_total_uW=rs["p_avg_uW"] if rs else None, p_total_nodecap_uW=nd.get("nd_p_avg_uW"),
               e_bin_nJ=rs["e_bin_nJ"] if rs else None, e_bin_nodecap_nJ=nd.get("nd_e_bin_nJ"), e_dyn_nJ=rs["e_dyn_nJ"] if rs else None, p_total_unc_uW=rs["p_total_unc_uW"] if rs else None, root_removed_uW=rs["root_removed_uW"] if rs else None,
               r2_seed0=r2_of(("vbits", tag_, "v12_o14")) if tag_ in VB else D.get(design, {}).get("r2"), n_seeds=nseed, window_bins=5000, events_per_bin=rs.get("events_per_bin") if rs else None, pins_annotated_frac=rs.get("pins_annotated_frac") if rs else None, sim_wallclock_min=rs.get("sim_wallclock_min") if rs else None,
               func_p_total_uW=rf["p_avg_uW"] if rf else None, func_p_leak_uW=rf["p_leak_uW"] if rf else None, func_e_bin_nJ=rf["e_bin_nJ"] if rf else None)
    if rs: row.update({f"sdf_{k}": v for k, v in consistency(design, "sdf", 5000, 0, rs).items()})
    if rf: row.update({f"func_{k}": v for k, v in consistency(design, "func", 5000, 0, rf).items()})
    rowsg.append(row)

# ---------------- CSV output
def wcsv(path, rows, cols):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader()
        for r in rows: w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items() if k in cols})
C2 = ["key", "label", "where", "role", "status", "design", "weights", "bits", "r2", "util_pct", "area_mm2", "cells", "setup_ws_ns", "hold_ws_ns", "drc", "run_kind", "dense", "window_bins", "window_s", "events", "events_per_bin", "clk_cycles", "cycles_per_bin",
      "p_total_unc_uW", "p_int_unc_uW", "p_sw_unc_uW", "root_corrected", "root_duty", "root_removed_uW", "p_total_uW", "p_int_uW", "p_sw_uW", "p_leak_uW", "p_dyn_uW", "p_avg_uW", "e_bin_nJ", "e_dyn_nJ", "pins_annotated_frac", "active_ns_mean", "active_ns_max", "overruns", "sim_wallclock_min",
      "old_kind", "e_old_nJ", "p_old_uW", "dev_pct", "leak_old_uW", "dev_leak_pct", "e_dyn_old_nJ", "dev_dyn_pct",
      "macro_corr_uW", "p_dyn_mc_uW", "p_avg_mc_uW", "e_bin_mc_nJ", "e_dyn_mc_nJ", "dev_mc_pct", "dev_dyn_mc_pct", "p_dyn_cond_uW", "p_avg_cond_uW", "e_bin_cond_nJ", "e_dyn_cond_nJ", "cond_gate_frac", "dev_cond_pct", "dev_dyn_cond_pct",
      "nd_p_total_unc_uW", "nd_root_removed_uW", "nd_p_total_uW", "nd_p_leak_uW", "nd_p_dyn_uW", "nd_p_avg_uW", "nd_e_bin_nJ", "nd_e_dyn_nJ", "nd_pins_annotated_frac",
      "leak_logic_uW", "leak_fill_uW", "leak_decap_uW", "leak_tap_uW", "leak_diode_uW", "n_fill", "n_decap", "n_tap", "nd_leak_logic_uW", "nd_leak_fill_uW", "nd_leak_decap_uW", "nd_leak_tap_uW", "nd_leak_diode_uW", "nd_n_fill", "nd_n_decap", "nd_n_tap",
      "refill_drc", "refill_setup_ws_ns", "refill_hold_ws_ns", "refill_cells"]
(ROOT / "results").mkdir(exist_ok=True)
wcsv(ROOT / "results/table2_round10.csv", rows2, C2)
C3 = ["key", "label", "kit", "supply_V", "status", "design", "r2", "util_pct", "area_mm2", "cells", "run_kind", "window_bins", "window_s", "events", "events_per_bin", "clk_cycles", "cycles_per_bin", "p_total_unc_uW", "root_corrected", "root_duty", "root_removed_uW",
      "p_total_uW", "p_int_uW", "p_sw_uW", "p_leak_uW", "leak_logic_uW", "p_dyn_uW", "p_avg_uW", "e_bin_nJ", "e_dyn_nJ", "e_dyn_func500_r7_nJ", "leak_logic_r7_uW", "pins_annotated_frac", "sim_wallclock_min", "old_kind", "e_old_nJ", "p_old_uW", "dev_pct", "leak_old_uW", "dev_leak_pct", "e_dyn_old_nJ", "dev_dyn_pct",
      "p_dyn_cond_uW", "p_avg_cond_uW", "e_bin_cond_nJ", "e_dyn_cond_nJ", "cond_gate_frac", "dev_cond_pct", "dev_dyn_cond_pct", "old_window_factor", "dev_dyn_windowadj_pct", "dev_dyn_cond_windowadj_pct"]
wcsv(ROOT / "results/table3_round10.csv", rows3, C3)
CG = ["H", "density_pct", "bits", "gated", "r2_mean", "r2_std", "p_dyn_uW", "p_leak_uW", "p_leak_nodecap_uW", "area_mm2", "table2", "status",
      "design", "util_pct", "cells", "cycles_per_bin", "p_total_uW", "p_total_nodecap_uW", "e_bin_nJ", "e_bin_nodecap_nJ", "e_dyn_nJ", "p_total_unc_uW", "root_removed_uW", "r2_seed0", "n_seeds", "window_bins", "events_per_bin", "pins_annotated_frac", "sim_wallclock_min",
      "func_p_total_uW", "func_p_leak_uW", "func_e_bin_nJ", "sdf_e_old_nJ", "sdf_p_old_uW", "sdf_dev_pct", "func_e_old_nJ", "func_p_old_uW", "func_dev_pct"]
wcsv(ROOT / "results/grid_round10.csv", rowsg, CG)
for f in ("table2_round10.csv", "table3_round10.csv", "grid_round10.csv"):
    (OUTD / "results").mkdir(parents=True, exist_ok=True); (OUTD / "results" / f).write_bytes((ROOT / "results" / f).read_bytes())

# ---------------- LaTeX bodies
def f3(x, nd=3): return "--" if x is None else sig(x, nd)
def tex_table2(statecorr=False):
    L = []
    order = ["soc_tuned", "topg_dense", "topg_event", "scmemg", "lmem2g", "lmin2", "hwg", "ming", "m12", "sp", "min32g", "g32", "g32p50", "fe"]   # g32 (12-bit dense H = 32, E5) is listed as a table row in Section 2 of the specification; its label is not in the Section 8 list, so it can be dropped
    for key in order:
        rs = [r for r in rows2 if r["key"] == key and r.get("role") == "table"]
        if not rs: continue
        r = rs[0]; lab = r["label"]
        if r.get("status") == "pending": L.append(f"{lab} & {r['weights']} & {r['bits']} & {f3(r.get('r2'))} & {f3(r.get('area_mm2'))} & -- & -- & -- & -- & -- & -- \\\\   % pending"); continue
        pdn, eb, ebn, mark = r.get("p_dyn_uW"), r.get("e_bin_nJ"), r.get("nd_e_bin_nJ"), ""
        if statecorr and r.get("macro_corr_uW") is not None:           # SRAM22 macro: ce/we duties conditioned on the macro clock (separately reported correction)
            pdn = r["p_dyn_mc_uW"]; eb = r["e_bin_mc_nJ"]; ebn = (ebn + r["macro_corr_uW"] * 1e-6 * BIN_S * 1e9) if ebn is not None else None; mark = f"   % macro state correction +{r['macro_corr_uW']:.3f} uW included"
        L.append(f"{lab} & {r['weights']} & {r['bits']} & {f3(r.get('r2'))} & {f3(r.get('area_mm2'))} & {f3(r.get('cycles_per_bin'))} & {f3(pdn)} & {f3(r.get('p_leak_uW'))} & {f3(r.get('nd_p_leak_uW'))} & {f3(eb)} & {f3(ebn)} \\\\{mark}")
    note = ("% columns: Implementation & Weights & Bits V/o & R^2 (seed 0) & Area (mm^2) & Cycles/bin & P_dyn (uW) & P_leak default fill (uW) & P_leak decap-free fill (uW) & E_bin default fill (nJ) & E_bin decap-free fill (nJ)\n"
            "% P_dyn = P_internal + P_switching and P_leak = P_leakage of the OpenSTA report of the real-time run (root-clock correction applied), E_bin = (P_dyn + P_leak) x 4 ms; decap-free: E10 refill of the same routed placement (-- = refill pending);\n"
            "% windows: hardwired cores 5,000 bins annotated; SRAM core 2,000 bins (event) / 500 bins (dense) annotated; memory cores 50 bins annotated; SoC 100 bins; front end 500 bins\n")
    return note + "\n".join(L) + "\n"
def tex_table3():
    L = []
    for r in rows3:
        if r.get("status") == "pending": L.append(f"{r['label']} & {r['supply_V']} & {f3(r.get('area_mm2'))} & -- & -- & -- & -- & -- & -- \\\\   % pending"); continue
        L.append(f"{r['label']} & {r['supply_V']} & {f3(r.get('area_mm2'))} & {f3(r.get('cycles_per_bin'))} & {f3(r.get('p_dyn_uW'))} & {f3(r.get('p_leak_uW'))} & {f3(r.get('leak_logic_uW'))} & {f3(r.get('e_bin_nJ'))} & {f3(r.get('e_dyn_nJ'))} \\\\")
    note = ("% columns: Kit & V_DD (V) & Area (mm^2) & Cycles/bin & P_dyn (uW) & P_leak total (uW) & P_leak logic cells only (uW) & E_bin (nJ) & E_dyn (nJ)\n"
            "% pruned core, 5,000-bin real-time window annotated (NanGate45 zero-delay), root-clock correction applied; E_bin = (P_dyn + P_leak) x 4 ms, E_dyn = P_dyn x 4 ms\n")
    return note + "\n".join(L) + "\n"
(OUTD / "tables").mkdir(parents=True, exist_ok=True)
(OUTD / "tables/table2_round10.tex").write_text(tex_table2()); (OUTD / "tables/table3_round10.tex").write_text(tex_table3())
(OUTD / "tables/table2_round10_statecorr.tex").write_text("% variant of table2_round10.tex with the SRAM-macro state correction included in P_dyn and E_bin of the SRAM-core and SoC rows (see run_log_round10.md)\n" + tex_table2(statecorr=True))
json.dump(dict(table2=rows2, table3=rows3, grid=rowsg), open(ROOT / "results/round10.json", "w"), indent=1, default=str)
def md_consistency():
    def f(x, nd=3): return "--" if x is None else (f"{x:+.1f}" if nd == "pct" else sig(x, nd))
    L = ["| row | run | window | P_total new (uW) | round-7 sum (uW) | dev. | P_leak new / old (uW) | E_dyn new / old (nJ) | dev. E_dyn | with state corr.: P_total (uW, dev.) | E_dyn (nJ, dev.) | dev. E_dyn after window/model adj. |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows2 + rows3:
        if r.get("status") != "ok": continue
        sc = r.get("p_avg_mc_uW") if r.get("p_avg_mc_uW") is not None else r.get("p_avg_cond_uW"); scd = r.get("dev_mc_pct") if r.get("dev_mc_pct") is not None else r.get("dev_cond_pct")
        se = r.get("e_dyn_mc_nJ") if r.get("e_dyn_mc_nJ") is not None else r.get("e_dyn_cond_nJ"); sed = r.get("dev_dyn_mc_pct") if r.get("dev_dyn_mc_pct") is not None else r.get("dev_dyn_cond_pct")
        wa = r.get("dev_dyn_cond_windowadj_pct") if r.get("dev_dyn_cond_windowadj_pct") is not None else r.get("dev_dyn_windowadj_pct")
        L.append(f"| {r['key']} | {r.get('run_kind','')}{' dense' if r.get('dense') else ''} | {r.get('window_bins','')} | {f(r.get('p_avg_uW'), 4)} | {f(r.get('p_old_uW'), 4)} | {f(r.get('dev_pct'), 'pct')} % | {f(r.get('p_leak_uW'), 4)} / {f(r.get('leak_old_uW'), 4)} | {f(r.get('e_dyn_nJ'), 4)} / {f(r.get('e_dyn_old_nJ'), 4)} | {f(r.get('dev_dyn_pct'), 'pct')} % | {f(sc, 4)} ({f(scd, 'pct')} %) | {f(se, 4)} ({f(sed, 'pct')} %) | {f(wa, 'pct')} % |")
    return "\n".join(L) + "\n"
(ROOT / "results/consistency_round10.md").write_text(md_consistency())
done2 = sum(1 for r in rows2 if r.get("status") == "ok"); done3 = sum(1 for r in rows3 if r.get("status") == "ok"); doneg = sum(1 for r in rowsg if r.get("status") == "measured")
print(f"table2: {done2}/{len(rows2)} runs collected; table3: {done3}/{len(rows3)}; grid: {doneg}/{len(rowsg)}")
for r in rows2:
    if r.get("status") == "ok": print(f"  {r['key']:12s} {r['run_kind']}{r['dense']} w{r['window_bins']:<5} P_tot {r['p_total_unc_uW']:8.3f} -> {r['p_avg_uW']:8.3f} uW (root -{r['root_removed_uW']:.3f}) leak {r['p_leak_uW']:.3f} E_bin {r['e_bin_nJ']:.3f} nJ E_dyn {r['e_dyn_nJ']:.3f} | old {r.get('p_old_uW') or 0:.3f} dev {r.get('dev_pct') or 0:+.1f} % | cov {100*(r.get('pins_annotated_frac') or 0):.1f} % | {r.get('sim_wallclock_min') or 0:.0f} min")
for r in rows3:
    if r.get("status") == "ok": print(f"  kit {r['key']:14s} P_tot {r['p_total_unc_uW']:8.3f} -> {r['p_avg_uW']:8.3f} uW leak {r['p_leak_uW']:.3f} (logic {r.get('leak_logic_uW') or 0:.3f}) E_bin {r['e_bin_nJ']:.4f} E_dyn {r['e_dyn_nJ']:.4f} | old {r.get('p_old_uW') or 0:.3f} dev {r.get('dev_pct') or 0:+.1f} %")
