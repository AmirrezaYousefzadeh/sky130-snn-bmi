#!/usr/bin/env bash
# Round 5: RTL check (500 bins, bit-exact against the integer reference vectors) of the new grid and per-session variants.
cd "$(dirname "$0")/.."
chk() { local v=$1 inc=$2 vec=$3; printf "%-22s " "$v"; DUT=$v RTL=$PWD/rtl/gen/$v.v INCDIR=$PWD/rtl/$inc LOAD="" ./sim/run_rtl.sh sim/$vec 500 0 0 > logs/rtl5_$v.log 2>&1; grep -E "SUMMARY|PASS|FAIL" logs/rtl5_$v.log | tr '\n' ' ' | cut -c1-150; echo; }
for c in g128 g128p25 g128p125 g64p50 g64p125 g32p50 g32p25 g16p50; do chk bmi_snn_$c $c vecfull_${c}_indy_20160630_01; done
chk bmi_snn_sp_s622 sp_s622 vecfull_sp_indy_20160622_01; chk bmi_snn_sp_s131 sp_s131 vecfull_sp_indy_20170131_02
chk bmi_snn_min32_s622 h32_s622 vecfull_h32_indy_20160622_01; chk bmi_snn_min32_s131 h32_s131 vecfull_h32_indy_20170131_02
chk bmi_snn_m12_s622 m12_s622 vecfull_v12_indy_20160622_01; chk bmi_snn_m12_s131 m12_s131 vecfull_v12_indy_20170131_02
