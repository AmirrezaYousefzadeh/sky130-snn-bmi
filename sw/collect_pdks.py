#!/usr/bin/env python3
"""Multi-PDK study: the hardwired 16-bit H=16 core on sky130 (reference), GF180MCU (OpenLane), NanGate45 / FreePDK45, IHP SG13G2
and ASAP7 (OpenROAD-flow-scripts). Post-layout area / timing from the flow metrics, functional gate-level energy from
sim/build_pdk_<p>_min16_{md0,idle}_full + power/out_vcd_... (same per-pin OpenSTA method). -> results/pdks.json,
paper/pdks_table.tex, paper/numbers_pdks.tex."""
import json, os, re, sys, gzip
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_designs import run_energy, run_idle, TCLK, RATE
from collect_results import parse_metrics
ROOT = Path(__file__).resolve().parent.parent
ORFS = Path("/media/pdk/OpenROAD-flow-scripts/flow")
IHP_RUN = os.environ.get("IHP_RUN", "ihp-sg13g2/bmi_snn_min16_abc")   # <platform dir>/<design nickname> of the IHP run (see sim/measure_pdk.sh)
PDKS = {  # key: label, node, library, flow, voltage, predictive?, macro shorthand
    "sky130":    dict(label="SkyWater sky130", node="130 nm", lib="sky130\\_fd\\_sc\\_hd", flow="OpenLane", sh="Sky", fab=True),
    "gf180":     dict(label="GlobalFoundries GF180MCU", node="180 nm", lib="gf180mcu\\_fd\\_sc\\_mcu7t5v0", flow="OpenLane", sh="Gf", fab=True),
    "ihp":       dict(label="IHP SG13G2", node="130 nm", lib="sg13g2\\_stdcell", flow="ORFS", sh="Ihp", fab=True),
    "nangate45": dict(label="NanGate45 / FreePDK45", node="45 nm", lib="NangateOpenCellLibrary", flow="ORFS", sh="Nan", fab=False),
    "asap7":     dict(label="ASAP7 RVT", node="7 nm (FinFET)", lib="asap7sc7p5t RVT", flow="ORFS", sh="Asap", fab=False),
    "asap7sram": dict(label="ASAP7 SRAM-Vt (low leakage)", node="7 nm (FinFET)", lib="asap7sc7p5t SRAM", flow="ORFS", sh="AsapS", fab=False),   # liberty swap on the routed RVT netlist (same footprints)
}
UTIL = {"sky130": 40, "gf180": 40, "ihp": 25, "nangate45": 40, "asap7": 40, "asap7sram": 40}   # core utilization target of each run (%), see synthesis/*/config.*
# GF180 at other supply voltages: the routed netlist and its recorded activity re-evaluated with the 1.8 V and 3.3 V typical liberty files
GF_VOLT = {"Low": ("tt_025C_1v80", 1.8), "Mid": ("tt_025C_3v30", 3.3)}
_unused = {
}
LIBS = {"sky130": "/media/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib",
        "gf180": "/media/pdk/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__tt_025C_5v00.lib",
        "ihp": str(ORFS / f"platforms/{IHP_RUN.split('/')[0]}/lib/sg13g2_stdcell_typ_1p20V_25C.lib"),
        "nangate45": str(ORFS / "platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib"),
        "asap7": "/media/pdk/asap7sc7p5t_28/lib/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib",
        "asap7sram": str(ORFS / "platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_SRAM_TT_nldm_220123.lib")}
import glob
AREA_LIBS = {"asap7": sorted(glob.glob(str(ORFS / "platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*"))),
             "asap7sram": sorted(glob.glob(str(ORFS / "platforms/asap7/lib/NLDM/asap7sc7p5t_*_SRAM_TT_nldm_*.lib*")))}   # cell areas: ASAP7 splits its cells over several files
def nom_voltage(lib):
    op = gzip.open if lib.endswith(".gz") else open
    with op(lib, "rt", errors="replace") as f:
        head = f.read(200000)
    m = re.search(r"nom_voltage\s*:\s*([\d.]+)", head); t = re.search(r"nom_temperature\s*:\s*([\d.]+)", head)
    return (float(m.group(1)) if m else None), (float(t.group(1)) if t else None)
PHYS_RE = re.compile(r"(fill|decap|tap|antenna|diode|endcap)", re.I)   # physical-only cells, not counted as standard cells (fillers, decaps, taps, antenna diodes)
def liberty_areas(lib_paths):
    areas = {}
    for lp in lib_paths:
        op = gzip.open if str(lp).endswith(".gz") else open
        with op(lp, "rt", errors="ignore") as fh:
            cell = None
            for line in fh:
                m = re.match(r"\s*cell\s*\(\s*\"?([^\")]+)\"?\s*\)", line)
                if m: cell = m.group(1); continue
                m = re.match(r"\s*area\s*:\s*([0-9.eE+-]+)", line)
                if m and cell and cell not in areas: areas[cell] = float(m.group(1))
    return areas
def liberty_leakage(lib_paths):
    """cell -> cell_leakage_power (liberty unit, nW for NanGate45)"""
    leak = {}
    for lp in lib_paths:
        op = gzip.open if str(lp).endswith(".gz") else open
        with op(lp, "rt", errors="ignore") as fh:
            cell = None
            for line in fh:
                m = re.match(r"\s*cell\s*\(\s*\"?([^\")]+)\"?\s*\)", line)
                if m: cell = m.group(1); continue
                m = re.match(r"\s*cell_leakage_power\s*:\s*([0-9.eE+-]+)", line)
                if m and cell and cell not in leak: leak[cell] = float(m.group(1))
    return leak
def netlist_stats(netlist, lib_paths):
    """Standard-cell count and area (um2) of a routed netlist from the liberty areas, physical-only cells excluded."""
    areas = liberty_areas(lib_paths); n = 0; a = 0.0; phys = 0; unknown = set()
    for line in open(netlist, errors="ignore"):
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s+[\\A-Za-z_][^\s(]*\s*\(", line)
        if not m: continue
        c = m.group(1)
        if c in ("module", "wire", "input", "output", "assign", "reg", "endmodule"): continue
        if PHYS_RE.search(c): phys += 1; continue
        if c in areas: n += 1; a += areas[c]
        else: unknown.add(c)
    if unknown: print("  cells without liberty area:", sorted(unknown)[:8])
    return dict(stdcells_netlist=n, instance_area_netlist_um2=a, phys_cells=phys)
def phys_leakage_from_liberty(netlist, lib_paths, unit_to_uW):
    """Sum of the liberty cell_leakage_power of the physical-only cells of the netlist (uW)."""
    leak = liberty_leakage(lib_paths); tot = 0.0
    for m in re.finditer(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s+[\\A-Za-z_][^\s(]*\s*\(', open(netlist, errors="ignore").read(), flags=re.M):
        c = m.group(1)
        if PHYS_RE.search(c): tot += leak.get(c, 0.0)
    return tot * unit_to_uW
def leakage_split(rpt, netlist):
    """Leakage (uW) of the logic standard cells and of the physical-only cells (fillers, decaps, taps, antenna diodes) from the
    per-instance OpenSTA report of the idle run and the cell types of the routed netlist."""
    if not rpt.exists() or not netlist.exists(): return None
    cell_of = {}
    for m in re.finditer(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(\\?\S+)\s*\(', open(netlist, errors="ignore").read(), flags=re.M):
        if m.group(1) in ("module", "wire", "input", "output", "assign", "reg", "endmodule"): continue
        cell_of[m.group(2).lstrip("\\")] = m.group(1)
    logic = phys = 0.0; nl_ = np_ = 0; unknown = 0
    for line in open(rpt, errors="ignore"):
        f = line.split()
        if len(f) < 5:
            continue
        try: leak = float(f[2])
        except ValueError: continue
        inst = f[4].lstrip("\\"); c = cell_of.get(inst)
        if c is None: unknown += 1; continue
        if PHYS_RE.search(c): phys += leak; np_ += 1
        else: logic += leak; nl_ += 1
    return dict(leak_logic_uW=logic * 1e6, leak_phys_uW=phys * 1e6, n_logic=nl_, n_phys=np_, n_unmatched=unknown)
def uniform_stats(d, netlist, libs, p):
    """Replace the flow's own cell count / area by the netlist-based ones (same definition for every PDK: standard cells only)."""
    if not d.get("pnr") or not netlist.exists(): return
    st = netlist_stats(netlist, libs); d["pnr"].update(st); d["pnr"]["netlist"] = str(netlist)
    print(f"  {p}: flow metrics {d['pnr'].get('stdcells')} cells / {d['pnr'].get('instance_area_um2')} um2; netlist (physical cells excluded) {st['stdcells_netlist']} cells / {st['instance_area_netlist_um2']:.0f} um2, {st['phys_cells']} physical cells")
    d["pnr"]["stdcells"] = st["stdcells_netlist"]; d["pnr"]["instance_area_um2"] = st["instance_area_netlist_um2"]
def orfs_metrics(plat):
    f = ORFS / f"logs/{plat}/base/6_report.json"   # plat = <platform dir>/<design nickname>
    if not f.exists(): return None
    m = json.load(open(f)); g = lambda k: m.get(k)
    period = g("finish__clock__period") or g("clock__period")
    tu = 1e-3 if plat.startswith("asap7") else 1.0   # the ASAP7 liberty time unit is ps (plat = <platform dir>/<nickname>)
    sws = g("finish__timing__setup__ws"); hws = g("finish__timing__hold__ws")
    fr = ORFS / f"logs/{plat}/base/5_2_route.json"   # detail-route violations left when the router stopped (0 = DRC-clean route)
    drc = json.load(open(fr)).get("detailedroute__route__drc_errors") if fr.exists() else None
    return dict(drc_errors=drc, instance_area_um2=g("finish__design__instance__area"), stdcells=g("finish__design__instance__count__stdcell") or g("finish__design__instance__count"),
                setup_ws_ns=sws * tu if sws is not None else None, hold_ws_ns=hws * tu if hws is not None else None, clock_period=period * tu if period else None,
                power_total_W=g("finish__power__total"), timing_met=(g("finish__timing__setup__ws") or 0) >= 0 and (g("finish__timing__hold__ws") or 0) >= 0)
out = {}
D = json.load(open(ROOT / "results/designs.json")).get("bmi_snn_min16", {})
for p, cfg in PDKS.items():
    d = dict(cfg); d["voltage"], d["temperature"] = nom_voltage(LIBS[p])
    if p == "sky130":
        d["pnr"] = dict(D.get("pnr") or {}); d["event"] = D.get("event"); d["idle"] = D.get("idle"); d["event_sdf"] = D.get("event_sdf")
        uniform_stats(d, ROOT / "synthesis/bmi_snn_min16/runs/bmi_snn_min16/final/nl/bmi_snn_min16.nl.v", [LIBS[p]], p)
    else:
        if p == "gf180":
            f = ROOT / "synthesis/pdk_gf180/bmi_snn_min16/runs/bmi_snn_min16/final/metrics.json"
            if f.exists():
                d["pnr"] = parse_metrics(f); d["pnr"]["timing_met"] = (d["pnr"].get("setup_ws_ns") or 0) >= 0 and (d["pnr"].get("hold_ws_ns") or 0) >= 0
                uniform_stats(d, ROOT / "synthesis/pdk_gf180/bmi_snn_min16/runs/bmi_snn_min16/final/nl/bmi_snn_min16.nl.v", [LIBS[p]], p)
        else:
            run = {"ihp": IHP_RUN, "asap7sram": "asap7/bmi_snn_min16"}.get(p, f"{p}/bmi_snn_min16"); d["pnr"] = orfs_metrics(run)
            nlname = "6_final_sram.v" if p == "asap7sram" else "6_final.v"
            uniform_stats(d, ORFS / f"results/{run}/base/{nlname}", AREA_LIBS.get(p, [LIBS[p]]), p)
            if p == "asap7sram" and d.get("pnr"):   # timing of the liberty swap: worst setup slack printed by power_vcd_sta.tcl (ps)
                sl = None
                for line in open(ROOT / "power/out_vcd_pdk_asap7sram_min16_md0_full/sta.log", errors="ignore"):
                    if line.startswith("WORST_SETUP_SLACK"):
                        try: sl = float(line.split()[1]) * 1e-3
                        except ValueError: pass
                d["pnr"]["setup_ws_ns"] = sl; d["pnr"]["timing_met"] = (sl or 0) >= 0; d["pnr"]["drc_errors"] = 0
        e = run_energy(f"pdk_{p}_min16_md0_full", TCLK, None); i = run_idle(f"pdk_{p}_min16_idle_full", TCLK, e["power_avg_uW"] * 1e-6 if e else None)
        if e: d["event"] = e
        if i: d["idle"] = i
    if p == "gf180" and d.get("event"):
        d["volt"] = {}
        for k, (corner, v) in GF_VOLT.items():
            base = ROOT / f"power/out_vcd_pdk_gf180_min16_md0_full_{corner}"; idle = ROOT / f"power/out_vcd_pdk_gf180_min16_idle_full_{corner}"
            if not (base / "power_vcd.rpt").exists(): continue
            from collect_designs import parse_group_table
            g = parse_group_table(base / "power_vcd.rpt"); gi = parse_group_table(idle / "power_vcd.rpt") if (idle / "power_vcd.rpt").exists() else None
            P = g["Total"]["total"]; T = d["event"]["cycles_meas"] * TCLK * 1e-9
            sl = None
            for line in open(base / "sta.log", errors="ignore"):
                if line.startswith("WORST_SETUP_SLACK_NS"): sl = float(line.split()[1]) * 1e9
            d["volt"][k] = dict(voltage=v, corner=corner, energy_per_bin_nJ=P * T / d["event"]["tb"]["bins"] * 1e9, leakage_uW=(gi["Total"]["leakage"] if gi else g["Total"]["leakage"]) * 1e6, setup_ws_ns=sl)
    if d.get("pnr") and d["pnr"].get("netlist"):
        tag = "bmi_snn_min16_idle_full" if p == "sky130" else f"pdk_{p}_min16_idle_full"
        ls = leakage_split(ROOT / f"power/out_vcd_{tag}/power_vcd_by_instance.rpt", Path(d["pnr"]["netlist"]))
        if ls: d["leak_split"] = ls; print(f"  {p}: leakage logic {ls['leak_logic_uW']:.4g} uW ({ls['n_logic']} cells), physical {ls['leak_phys_uW']:.4g} uW ({ls['n_phys']} cells), unmatched instances {ls['n_unmatched']}")
        if ls and p in ("nangate45",) and ls["leak_phys_uW"] == 0:   # cross-check: do the fillers carry a cell_leakage_power attribute at all? (NanGate45: no)
            v = phys_leakage_from_liberty(Path(d["pnr"]["netlist"]), AREA_LIBS.get(p, [LIBS[p]]), 1e-3)
            if v > 0: ls["leak_phys_uW"] = v; ls["phys_from_liberty"] = True
            print(f"  {p}: physical-cell leakage according to the liberty: {v:.4g} uW (0 = no cell_leakage_power attribute on the fillers)")
    if d.get("event") and d.get("idle"):
        d["avg_power_uW_250Hz_clkstopped"] = d["event"]["energy_per_bin_nJ"] * RATE * 1e-3 + d["idle"]["leakage_uW"]
        if d.get("leak_split"):   # average power with the logic leakage only (the physical cells' leakage is a flow choice, reported separately)
            d["avg_power_uW_250Hz_clkstopped_logic"] = d["event"]["energy_per_bin_nJ"] * RATE * 1e-3 + d["leak_split"]["leak_logic_uW"]
    out[p] = d
(ROOT / "results/pdks.json").write_text(json.dumps(out, indent=1, default=float))
def f(x, nd=3): return "--" if x is None else (f"{x:,.0f}" if abs(x) >= 1000 else f"{x:.{nd}g}")
rows = []; M = ["% auto-generated by sw/collect_pdks.py"]
for p, d in out.items():
    pnr = d.get("pnr") or {}; e = d.get("event") or {}; i = d.get("idle") or {}; sh = d["sh"]
    area = pnr.get("instance_area_um2"); area_mm2 = area / 1e6 if area else None
    slack = pnr.get("setup_ws_ns"); flag = "" if pnr.get("timing_met", True) else "$^{\\dagger}$"
    drcflag = "$^{\\ddagger}$" if (pnr.get("drc_errors") or 0) > 0 else ""   # route not DRC-clean (see text)
    ls = d.get("leak_split") or {}
    physcell = f"\\textit{{{f(ls.get('leak_phys_uW'))}}}" if ls.get("phys_from_liberty") else f(ls.get('leak_phys_uW'))
    rows.append(f"{d['label']}{drcflag}{'' if d['fab'] else ' (predictive)'} & {d['node']} & {f(d['voltage'],2)} & {UTIL[p]} & {f(area_mm2)} & {f(pnr.get('stdcells'),4)} & {f(slack,2)}{flag} & {f(e.get('energy_per_bin_nJ'))} & {f(ls.get('leak_logic_uW'))} & {physcell} & {f(d.get('avg_power_uW_250Hz_clkstopped_logic'))} \\\\")
    for k, v in (("area", area_mm2), ("e", e.get("energy_per_bin_nJ")), ("leak", i.get("leakage_uW")), ("pavg", d.get("avg_power_uW_250Hz_clkstopped")), ("slack", slack), ("volt", d["voltage"]), ("cells", pnr.get("stdcells")), ("drc", pnr.get("drc_errors")),
                 ("leakLogic", ls.get("leak_logic_uW")), ("leakPhys", ls.get("leak_phys_uW")), ("pavgLogic", d.get("avg_power_uW_250Hz_clkstopped_logic")), ("util", UTIL[p]),
                 ("leakEv", e.get("leakage_uW")), ("physcells", ls.get("n_phys"))):
        M.append(f"\\newcommand{{\\pdk{k}{sh}}}{{{f(v, 4 if k == 'cells' else 3)}}}")
    e0 = out["sky130"].get("event", {}).get("energy_per_bin_nJ"); l0 = out["sky130"].get("idle", {}).get("leakage_uW"); p0 = out["sky130"].get("avg_power_uW_250Hz_clkstopped")
    M.append(f"\\newcommand{{\\pdkRel{sh}}}{{{f(e['energy_per_bin_nJ'] / e0, 3) if (e0 and e.get('energy_per_bin_nJ')) else '--'}}}")   # energy per bin relative to sky130
    M.append(f"\\newcommand{{\\pdkLeakRel{sh}}}{{{f(i['leakage_uW'] / l0, 3) if (l0 and i.get('leakage_uW')) else '--'}}}")           # leakage relative to sky130
    M.append(f"\\newcommand{{\\pdkPavgRel{sh}}}{{{f(d['avg_power_uW_250Hz_clkstopped'] / p0, 3) if (p0 and d.get('avg_power_uW_250Hz_clkstopped')) else '--'}}}")   # average power relative to sky130
    ls0 = out["sky130"].get("leak_split") or {}; pl0 = out["sky130"].get("avg_power_uW_250Hz_clkstopped_logic")
    M.append(f"\\newcommand{{\\pdkLeakLogicRel{sh}}}{{{f(ls['leak_logic_uW'] / ls0['leak_logic_uW'], 3) if (ls0.get('leak_logic_uW') and ls.get('leak_logic_uW')) else '--'}}}")   # logic leakage relative to sky130
    M.append(f"\\newcommand{{\\pdkPavgLogicRel{sh}}}{{{f(d['avg_power_uW_250Hz_clkstopped_logic'] / pl0, 3) if (pl0 and d.get('avg_power_uW_250Hz_clkstopped_logic')) else '--'}}}")   # average power (logic leakage) relative to sky130
    for k, vd in (d.get("volt") or {}).items():   # GF180 at 1.8 V / 3.3 V
        for kk, vv in (("e", vd["energy_per_bin_nJ"]), ("leak", vd["leakage_uW"]), ("slack", vd["setup_ws_ns"]), ("volt", vd["voltage"])):
            M.append(f"\\newcommand{{\\pdk{kk}{sh}{k}}}{{{f(vv, 3)}}}")
        M.append(f"\\newcommand{{\\pdkRel{sh}{k}}}{{{f(vd['energy_per_bin_nJ'] / e0, 3) if e0 else '--'}}}")
        M.append(f"\\newcommand{{\\pdkpavgLogic{sh}{k}}}{{{f(vd['energy_per_bin_nJ'] * RATE * 1e-3 + vd['leakage_uW'] * (ls.get('leak_logic_uW', 0) / i['leakage_uW'] if i.get('leakage_uW') else 1), 3)}}}")   # logic share of leakage assumed voltage-independent
    print(f"{d['label']:28s} V {f(d['voltage'],2):>5s}  area {f(area_mm2):>7s} mm2  cells {f(pnr.get('stdcells'),5):>7s}  slack {f(slack,2):>6s}{flag}  E {f(e.get('energy_per_bin_nJ')):>6s} nJ  leak {f(i.get('leakage_uW')):>7s} uW  Pavg {f(d.get('avg_power_uW_250Hz_clkstopped')):>6s} uW")
hdr = "PDK & Node & $V_{DD}$ (V) & Util.\\ (\\%) & Area (mm$^2$) & Cells & Slack (ns) & $E_{\\mathrm{bin}}$ (nJ) & \\multicolumn{2}{c}{Leakage (\\si{\\micro\\watt})} & $P_{\\mathrm{avg}}$ (\\si{\\micro\\watt}) \\\\\n & & & & & & & & logic & physical & \\\\"
(ROOT / "paper/pdks_table.tex").write_text("\\begin{tabular}{@{}llrrrrrrrrr@{}}\n\\toprule\n" + hdr + "\n\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}%\n")
(ROOT / "paper/numbers_pdks.tex").write_text("\n".join(M) + "\n")
