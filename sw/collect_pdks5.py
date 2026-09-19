#!/usr/bin/env python3
"""Round 5 (E5): cross-node study at 5 MHz with the utilization policy: sp, m12, min32, min16 (+ lmin2 where hardened) on sky130,
GF180MCU, IHP SG13G2, NanGate45, ASAP7 RVT and ASAP7 SRAM-Vt (a hardening with the low-leakage library, not a liberty swap).
Reads the policy results (synthesis/pdk_gf180/*/runs/*_5m, OpenROAD-flow-scripts results/<plat>/<core>_5m[_sram]), the measurements
of sim/measure_pdk5.sh (tags pdk5_<kit>_<core>_{md0,idle}_full, _md0_sdf, and the low-voltage re-evaluations _<corner>) and, for
sky130, results/designs.json (sw/collect_designs5.py). Writes results/pdks5.json, paper/pdks_table.tex, paper/numbers_pdks.tex
(macros \\pdk<key><Kit><Core>; the unsuffixed \\pdk<key><Kit> are the min16 values, as in the previous rounds), results/pdks_pavg_vs_rate.csv."""
import json, re, sys, glob, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_designs import run_energy, run_idle, SESS
from collect_pdks import PDKS, LIBS, AREA_LIBS, ORFS, nom_voltage, netlist_stats, leakage_split, orfs_metrics, phys_leakage_from_liberty
from collect_results import parse_metrics, RATE, parse_group_table
ROOT = Path(__file__).resolve().parent.parent
TCLK = 200.0
CORES = {"sp": ("Sp", "hardwired 12-bit gated, 25 % synapses"), "m12": ("MinT", "hardwired 12-bit gated"), "min32": ("MinH", "hardwired 16-bit, $H{=}32$"),
         "min16": ("MinS", "hardwired 16-bit, $H{=}16$"), "lmin2": ("LmMinP", "latch memory, 12-bit gated, pipelined")}
PLAT = {"ihp": "ihp-sg13g2", "nangate45": "nangate45", "asap7": "asap7", "asap7sram": "asap7"}
LIBD_GF = "/media/pdk/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib"
VOLT_LIBS = {   # low-voltage re-evaluations of sim/measure_pdk5.sh: corner -> liberty (list) for the voltage
    "gf180": {"tt_025C_3v30": [f"{LIBD_GF}/gf180mcu_fd_sc_mcu7t5v0__tt_025C_3v30.lib"], "tt_025C_1v80": [f"{LIBD_GF}/gf180mcu_fd_sc_mcu7t5v0__tt_025C_1v80.lib"], "ss_125C_1v62": [f"{LIBD_GF}/gf180mcu_fd_sc_mcu7t5v0__ss_125C_1v62.lib"]},
    "ihp": {"slow_1p08V_125C": [str(ORFS / "platforms/ihp-sg13g2/lib/sg13g2_stdcell_slow_1p08V_125C.lib")]},
    "asap7": {"SS": sorted(glob.glob(str(ORFS / "platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_SS_nldm_*.lib*")))},
    "asap7sram": {"SS": sorted(glob.glob(str(ORFS / "platforms/asap7/lib/NLDM/asap7sc7p5t_*_SRAM_SS_nldm_*.lib*")))},
    "sky130": {"ss_n40C_1v28": ["/media/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_n40C_1v28.lib"], "ss_100C_1v40": ["/media/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v40.lib"]},
}
def util_of_link(link):
    try: m = re.search(r"_u(\d+)$", os.readlink(link)); return int(m.group(1)) if m else None
    except OSError: return None
def slack_of(d):
    f = ROOT / d / "slack.txt"
    if not f.exists(): return None, None
    v = dict(l.split() for l in f.read_text().split("\n") if l.strip())
    return (float(v["setup_ws"]) * 1e9 if "setup_ws" in v else None), (float(v["hold_ws"]) * 1e9 if "hold_ws" in v else None)   # sta::worst_slack_cmd returns seconds
D5 = json.load(open(ROOT / "results/designs.json"))
out = {}
for kit, cfg in PDKS.items():
    for core, (csh, clabel) in CORES.items():
        D = f"bmi_snn_{core}"; d = dict(cfg); d["core"] = core; d["core_sh"] = csh; d["core_label"] = clabel; d["voltage"], d["temperature"] = nom_voltage(LIBS[kit])
        libs = AREA_LIBS.get(kit, [LIBS[kit]])
        if kit == "sky130":
            s = D5.get(D)
            if not s or not s.get("pnr"): continue
            d["pnr"] = dict(s["pnr"]); d["pnr"]["util_target_pct"] = s["pnr"].get("util_target_pct")
            nl = ROOT / f"synthesis/{D}/runs/{D}_5m/final/nl/{D}.nl.v"
            for k in ("event", "event_sdf", "idle", "leak_split"):
                if s.get(k): d[k] = s[k]
            tag_idle = f"{D}_5m_idle_full"; tag_ev = f"{D}_5m_md0_full"
        else:
            if kit == "gf180":
                run = ROOT / f"synthesis/pdk_gf180/{D}/runs/{D}_5m"; mj = run / "final/metrics.json"
                if not mj.exists(): continue
                d["pnr"] = parse_metrics(mj); d["pnr"]["timing_met"] = (d["pnr"].get("setup_ws_ns") or 0) >= 0 and (d["pnr"].get("hold_ws_ns") or 0) >= 0
                d["pnr"]["util_target_pct"] = util_of_link(run); nl = run / f"final/nl/{D}.nl.v"
            else:
                nick = f"{D}_5m_sram" if kit == "asap7sram" else f"{D}_5m"; plat = f"{PLAT[kit]}/{nick}"
                link = ORFS / f"results/{PLAT[kit]}/{nick}"
                if not link.exists(): continue
                d["pnr"] = orfs_metrics(plat)
                if not d["pnr"]: continue
                d["pnr"]["util_target_pct"] = util_of_link(link); nl = ORFS / f"results/{plat}/base/6_final.v"
            if nl.exists():
                st = netlist_stats(nl, libs); d["pnr"].update(st); d["pnr"]["netlist"] = str(nl); d["pnr"]["stdcells"] = st["stdcells_netlist"]; d["pnr"]["instance_area_um2"] = st["instance_area_netlist_um2"]
            tag_ev = f"pdk5_{kit}_{core}_md0_full"; tag_idle = f"pdk5_{kit}_{core}_idle_full"
            e = run_energy(tag_ev, TCLK, None); i = run_idle(tag_idle, TCLK, e["power_avg_uW"] * 1e-6 if e else None); es = run_energy(f"pdk5_{kit}_{core}_md0_sdf", TCLK, None)
            if e: d["event"] = e
            if i: d["idle"] = i
            if es: d["event_sdf"] = es
            rpt = ROOT / f"power/out_vcd_{tag_idle}/power_vcd_by_instance.rpt"
            if rpt.exists() and nl.exists():
                ls = leakage_split(rpt, nl)
                if ls:
                    if kit == "nangate45" and ls["leak_phys_uW"] == 0:
                        v = phys_leakage_from_liberty(nl, libs, 1e-3); ls["leak_phys_uW"] = v; ls["phys_from_liberty"] = True
                    d["leak_split"] = ls
        # low-voltage re-evaluations (same activity, other liberty): energy per bin, leakage, worst setup slack at 200 ns -> f_max
        d["volt"] = {}
        for corner, vl in VOLT_LIBS.get(kit, {}).items():
            base = ROOT / f"power/out_vcd_{tag_ev}_{corner}"; idle = ROOT / f"power/out_vcd_{tag_idle}_{corner}"
            if not (base / "power_vcd.rpt").exists() or "event" not in d: continue
            g = parse_group_table(base / "power_vcd.rpt"); gi = parse_group_table(idle / "power_vcd.rpt") if (idle / "power_vcd.rpt").exists() else None
            P = g["Total"]["total"]; T = d["event"]["cycles_meas"] * TCLK * 1e-9; ws, wh = slack_of(f"power/out_vcd_{tag_ev}_{corner}")
            v, t = nom_voltage(vl[0])
            d["volt"][corner] = dict(voltage=v, temperature=t, energy_per_bin_nJ=P * T / d["event"]["tb"]["bins"] * 1e9, leakage_uW=(gi["Total"]["leakage"] if gi else g["Total"]["leakage"]) * 1e6,
                                     setup_ws_ns=ws, hold_ws_ns=wh, fmax_MHz=(1e3 / (TCLK - ws)) if (ws is not None and ws < TCLK) else None, timing_met=(ws or 0) >= 0)
            d["volt"][corner]["avg_power_uW_250Hz_clkstopped"] = d["volt"][corner]["energy_per_bin_nJ"] * RATE * 1e-3 + d["volt"][corner]["leakage_uW"]
        if d.get("event") and d.get("idle"):
            d["avg_power_uW_250Hz_clkstopped"] = d["event"]["energy_per_bin_nJ"] * RATE * 1e-3 + d["idle"]["leakage_uW"]
            d["energy_dyn_per_bin_nJ"] = (d["event"]["power_avg_uW"] - d["idle"]["leakage_uW"]) * 1e-6 * d["event"]["cycles_per_bin"] * TCLK * 1e-9 * 1e9
            if d.get("leak_split"): d["avg_power_uW_250Hz_clkstopped_logic"] = d["event"]["energy_per_bin_nJ"] * RATE * 1e-3 + d["leak_split"]["leak_logic_uW"]
        if d.get("event_sdf") and d.get("idle"): d["avg_power_uW_250Hz_clkstopped_sdf"] = d["event_sdf"]["energy_per_bin_nJ"] * RATE * 1e-3 + d["idle"]["leakage_uW"]
        out[f"{kit}/{core}"] = d
json.dump(out, open(ROOT / "results/pdks5.json", "w"), indent=1, default=float)
def f(x, nd=3): return "--" if x is None else (f"{x:,.0f}" if abs(x) >= 1000 else f"{x:.{nd}g}")
# ---- macros
M = ["% auto-generated by sw/collect_pdks5.py (round 5: 5 MHz, utilization policy; \\pdk<key><Kit> without core suffix = min16)"]
def macs(d, suf):
    pnr = d.get("pnr") or {}; e = d.get("event") or {}; i = d.get("idle") or {}; ls = d.get("leak_split") or {}
    area = pnr.get("instance_area_um2"); items = [("area", area / 1e6 if area else None), ("e", e.get("energy_per_bin_nJ")), ("eSdf", (d.get("event_sdf") or {}).get("energy_per_bin_nJ")),
        ("eDyn", d.get("energy_dyn_per_bin_nJ")), ("leak", i.get("leakage_uW")), ("pavg", d.get("avg_power_uW_250Hz_clkstopped")), ("pavgSdf", d.get("avg_power_uW_250Hz_clkstopped_sdf")),
        ("slack", pnr.get("setup_ws_ns")), ("hold", pnr.get("hold_ws_ns")), ("volt", d.get("voltage")), ("cells", pnr.get("stdcells")), ("drc", pnr.get("drc_errors")),
        ("leakLogic", ls.get("leak_logic_uW")), ("leakPhys", ls.get("leak_phys_uW")), ("pavgLogic", d.get("avg_power_uW_250Hz_clkstopped_logic")), ("util", pnr.get("util_target_pct")),
        ("leakEv", e.get("leakage_uW")), ("physcells", ls.get("n_phys")), ("cyc", e.get("cycles_per_bin")), ("lat", e.get("latency_us")), ("pdec", e.get("power_avg_uW"))]
    for k, v in items: M.append(f"\\newcommand{{\\pdk{k}{suf}}}{{{f(v, 4 if k in ('cells', 'physcells', 'slack') else 3)}}}")
    for corner, vd in (d.get("volt") or {}).items():
        cs = re.sub(r"[^A-Za-z]", "", corner.replace("0", "Zero").replace("1", "One").replace("2", "Two").replace("3", "Three").replace("4", "Four").replace("5", "Five").replace("6", "Six").replace("8", "Eight"))
        for k, v in (("e", vd["energy_per_bin_nJ"]), ("leak", vd["leakage_uW"]), ("pavg", vd["avg_power_uW_250Hz_clkstopped"]), ("slack", vd["setup_ws_ns"]), ("fmax", vd["fmax_MHz"]), ("volt", vd["voltage"])):
            M.append(f"\\newcommand{{\\pdk{k}{suf}{cs}}}{{{f(v, 4 if k == 'slack' else 3)}}}")
for key, d in out.items(): macs(d, d["sh"] + d["core_sh"])
LEGACY_VOLT = {"tt_025C_1v80": "Low", "tt_025C_3v30": "Mid"}    # names of the previous rounds for the GF180 supply variants
for kit, cfg in PDKS.items():
    d = out.get(f"{kit}/min16")
    if d:
        macs(d, cfg["sh"])
        for corner, vd in (d.get("volt") or {}).items():
            if corner in LEGACY_VOLT:
                cs = LEGACY_VOLT[corner]
                for k, v in (("e", vd["energy_per_bin_nJ"]), ("leak", vd["leakage_uW"]), ("slack", vd["setup_ws_ns"]), ("volt", vd["voltage"]), ("pavgLogic", vd["avg_power_uW_250Hz_clkstopped"])):
                    M.append(f"\\newcommand{{\\pdk{k}{cfg['sh']}{cs}}}{{{f(v, 4 if k == 'slack' else 3)}}}")
                s0 = out.get("sky130/min16") or {}; e0 = (s0.get("event") or {}).get("energy_per_bin_nJ")
                M.append(f"\\newcommand{{\\pdkRel{cfg['sh']}{cs}}}{{{f(vd['energy_per_bin_nJ'] / e0, 3) if e0 else '--'}}}")
        if kit == "gf180":                                          # placeholders for supply variants not measured yet
            for corner, cs in LEGACY_VOLT.items():
                if corner not in (d.get("volt") or {}):
                    for k in ("e", "leak", "slack", "volt", "pavgLogic", "Rel"): M.append(f"\\newcommand{{\\pdk{k}{cfg['sh']}{cs}}}{{--}}")
    else:                                                          # kit without a min16 result yet: placeholders so that the paper compiles
        for k in ("area", "e", "eSdf", "eDyn", "leak", "pavg", "pavgSdf", "slack", "hold", "volt", "cells", "drc", "leakLogic", "leakPhys", "pavgLogic", "util", "leakEv", "physcells", "cyc", "lat", "pdec",
                  "Rel", "LeakRel", "PavgRel", "LeakLogicRel", "PavgLogicRel"):
            M.append(f"\\newcommand{{\\pdk{k}{cfg['sh']}}}{{--}}")
        if kit == "gf180":
            for cs in ("Low", "Mid"):
                for k in ("e", "leak", "slack", "volt", "pavgLogic", "Rel"): M.append(f"\\newcommand{{\\pdk{k}{cfg['sh']}{cs}}}{{--}}")
# relative figures against sky130, same core
for key, d in out.items():
    s0 = out.get(f"sky130/{d['core']}") or {}; suf = d["sh"] + d["core_sh"]
    def rel(a, b): return f(a / b, 3) if (a and b) else "--"
    M.append(f"\\newcommand{{\\pdkRel{suf}}}{{{rel((d.get('event') or {}).get('energy_per_bin_nJ'), (s0.get('event') or {}).get('energy_per_bin_nJ'))}}}")
    M.append(f"\\newcommand{{\\pdkLeakRel{suf}}}{{{rel((d.get('idle') or {}).get('leakage_uW'), (s0.get('idle') or {}).get('leakage_uW'))}}}")
    M.append(f"\\newcommand{{\\pdkPavgRel{suf}}}{{{rel(d.get('avg_power_uW_250Hz_clkstopped'), s0.get('avg_power_uW_250Hz_clkstopped'))}}}")
    M.append(f"\\newcommand{{\\pdkLeakLogicRel{suf}}}{{{rel((d.get('leak_split') or {}).get('leak_logic_uW'), (s0.get('leak_split') or {}).get('leak_logic_uW'))}}}")
    M.append(f"\\newcommand{{\\pdkPavgLogicRel{suf}}}{{{rel(d.get('avg_power_uW_250Hz_clkstopped_logic'), s0.get('avg_power_uW_250Hz_clkstopped_logic'))}}}")
    if d["core"] == "min16":
        for k, a, b in (("Rel", (d.get('event') or {}).get('energy_per_bin_nJ'), (s0.get('event') or {}).get('energy_per_bin_nJ')), ("LeakRel", (d.get('idle') or {}).get('leakage_uW'), (s0.get('idle') or {}).get('leakage_uW')),
                        ("PavgRel", d.get('avg_power_uW_250Hz_clkstopped'), s0.get('avg_power_uW_250Hz_clkstopped')), ("LeakLogicRel", (d.get('leak_split') or {}).get('leak_logic_uW'), (s0.get('leak_split') or {}).get('leak_logic_uW')),
                        ("PavgLogicRel", d.get('avg_power_uW_250Hz_clkstopped_logic'), s0.get('avg_power_uW_250Hz_clkstopped_logic'))):
            M.append(f"\\newcommand{{\\pdk{k}{d['sh']}}}{{{rel(a, b)}}}")
(ROOT / "paper/numbers_pdks.tex").write_text("\n".join(M) + "\n")
# ---- table: one row per kit and core (E5 columns: node, supply, utilization, area, cells, slack, E zero-delay, E annotated or n/a,
# glitch factor, leakage logic, leakage total, P_avg at 250 bins/s from the annotated energy where available and the total leakage,
# E_bin / leakage / f_max at the lowest characterized supply with its temperature)
hdr = "Kit & Core & Node & $V$ & Util. & Area & Cells & Setup & $E_{\\mathrm{bin}}$ & $E_{\\mathrm{bin}}$ ann. & Glitch & Leak.\\ logic & Leak.\\ total & $P_{\\mathrm{avg}}$ & $V_{\\mathrm{low}}$ & $T$ & $E_{\\mathrm{bin}}$ & Leak. & $f_{\\max}$ \\\\"
units = " & & & V & \\% & mm$^2$ & & ns & nJ & nJ & & \\si{\\micro\\watt} & \\si{\\micro\\watt} & \\si{\\micro\\watt} & V & $^{\\circ}$C & nJ & \\si{\\micro\\watt} & MHz \\\\"
rows = []
for key, d in out.items():
    pnr = d.get("pnr") or {}; e = d.get("event") or {}; es = d.get("event_sdf") or {}; i = d.get("idle") or {}; ls = d.get("leak_split") or {}
    area = pnr.get("instance_area_um2"); flag = "" if pnr.get("timing_met", True) else "$^{\\dagger}$"; drcflag = "$^{\\ddagger}$" if (pnr.get("drc_errors") or 0) > 0 else ""
    lv = None
    for corner, vd in (d.get("volt") or {}).items():   # lowest supply
        if lv is None or (vd["voltage"] or 9) < (lv["voltage"] or 9): lv = vd
    ea = es.get("energy_per_bin_nJ"); ez = e.get("energy_per_bin_nJ"); glitch = (ea / ez) if (ea and ez) else None
    pav = (ea if ea else ez); pav = (pav * RATE * 1e-3 + i["leakage_uW"]) if (pav and i.get("leakage_uW") is not None) else None
    ann = f(ea) if ea else ("n/a" if d["flow"] == "ORFS" and key.split("/")[0] in ("nangate45", "ihp") else "--")
    phys_note = "$^{\\S}$" if ls.get("phys_from_liberty") else ""
    rows.append(f"{d['label']}{drcflag}{'' if d['fab'] else ' (pred.)'} & {d['core_sh']} & {d['node']} & {f(d['voltage'], 2)} & {f(pnr.get('util_target_pct'), 2)} & {f(area / 1e6 if area else None)} & {f(pnr.get('stdcells'), 4)} & {f(pnr.get('setup_ws_ns'), 4)}{flag} & "
                f"{f(ez)} & {ann} & {f(glitch)} & {f(ls.get('leak_logic_uW'))} & {f(i.get('leakage_uW'))}{phys_note} & {f(pav)} & "
                + (f"{f(lv['voltage'], 2)} & {f(lv['temperature'], 3)} & {f(lv['energy_per_bin_nJ'])} & {f(lv['leakage_uW'])} & {f(lv['fmax_MHz'])}" if lv else "-- & -- & -- & -- & --") + " \\\\")
    d["glitch_factor"] = glitch; d["avg_power_uW_250Hz_clkstopped_best"] = pav; d["bit_exact_500"] = e.get("pass")
(ROOT / "paper/pdks_table.tex").write_text("\\begin{tabular}{@{}lll cc rr r rr r rr r ccrrr@{}}\n\\toprule\n" + hdr + "\n" + units + "\n\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}%\n"
    "% $^{\\dagger}$ timing not met at 200 ns; $^{\\ddagger}$ route not DRC-clean; $^{\\S}$ physical-cell leakage from the liberty (the flow reports none for fillers); n/a: the kit ships no timed simulation models (zero-delay activity).\n")
json.dump(out, open(ROOT / "results/pdks5.json", "w"), indent=1, default=float)
# ---- average power vs decode rate (clock stopped between bins): P = E_dyn * rate + leakage
with open(ROOT / "results/pdks_pavg_vs_rate.csv", "w") as fh:
    fh.write("kit,core,voltage_V,rate_bins_per_s,energy_dyn_per_bin_nJ,leakage_total_uW,leakage_logic_uW,p_avg_uW,p_avg_logic_leak_uW\n")
    for key, d in out.items():
        if not (d.get("event") and d.get("idle")): continue
        ed = d["energy_dyn_per_bin_nJ"]; lk = d["idle"]["leakage_uW"]; ll = (d.get("leak_split") or {}).get("leak_logic_uW")
        for r in (1, 2, 5, 10, 20, 50, 100, 250, 500, 1000):
            fh.write(f"{d['label']},{d['core']},{d['voltage']},{r},{ed:.5g},{lk:.5g},{'' if ll is None else f'{ll:.5g}'},{ed * r * 1e-3 + lk:.5g},{'' if ll is None else f'{ed * r * 1e-3 + ll:.5g}'}\n")
for key, d in out.items():
    e = d.get("event") or {}; i = d.get("idle") or {}; pnr = d.get("pnr") or {}
    print(f"{key:18s} util {f(pnr.get('util_target_pct'),2):>3} area {f((pnr.get('instance_area_um2') or 0)/1e6):>8} mm2 cells {f(pnr.get('stdcells'),4):>7} setup {f(pnr.get('setup_ws_ns'),4):>6} E {f(e.get('energy_per_bin_nJ')):>6} nJ leak {f(i.get('leakage_uW')):>7} uW Pavg {f(d.get('avg_power_uW_250Hz_clkstopped')):>7} uW volt {list((d.get('volt') or {}).keys())}")
