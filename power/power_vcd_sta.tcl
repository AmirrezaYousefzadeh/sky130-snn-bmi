# Per-net activity power: OpenSTA read_power_activities from a gate-level VCD (no global median, no case analysis).
# Env: RUN_DIR TOP LIB_SC LIB_SRAM VCD_FILE VCD_SCOPE PERIOD_NS OUT MACRO_INST
set RUN $::env(RUN_DIR); set TOP $::env(TOP); set OUT $::env(OUT)
foreach l $::env(LIB_SC) { read_liberty $l }      ;# one or several liberty files (space-separated; gzip accepted)
if {[info exists ::env(LIB_SRAM)] && [file exists $::env(LIB_SRAM)]} { read_liberty $::env(LIB_SRAM) }
# NETLIST / SPEF may be preset (multi-PDK study: OpenROAD-flow-scripts result directories)
set nl [expr {[info exists ::env(NETLIST)] ? $::env(NETLIST) : "$RUN/final/nl/$TOP.nl.v"}]
set spef [expr {[info exists ::env(SPEF)] ? $::env(SPEF) : "$RUN/final/spef/nom/$TOP.nom.spef"}]
read_verilog $nl
link_design $TOP
read_spef $spef
set period $::env(PERIOD_NS); set half [expr {$period / 2.0}]
create_clock -name clk -period $period -waveform [list 0.0 $half] [get_ports clk]
set_propagated_clock [get_clocks clk]
file mkdir $OUT
puts "reading VCD $::env(VCD_FILE) scope $::env(VCD_SCOPE)"
read_power_activities -scope $::env(VCD_SCOPE) -vcd $::env(VCD_FILE)
report_power -digits 6 > $OUT/power_vcd.rpt
report_power -instances [get_cells -hierarchical *] -digits 4 > $OUT/power_vcd_by_instance.rpt
foreach inst [split $::env(MACRO_INST) " "] {
  if {[llength [get_cells -quiet $inst]]} { report_power -instances [get_cells $inst] -digits 6 > $OUT/power_vcd_$inst.rpt }
}
# clock-tree cells
set ct {}
foreach cell [get_cells -quiet -hierarchical *] {
  set ref [get_property $cell ref_name]
  if {[string match {*clkbuf*} $ref] || [string match {*clkinv*} $ref] || [string match {*clkdly*} $ref] || [string match {*dlclkp*} $ref]} { lappend ct $cell }
}
if {[llength $ct]} { report_power -instances $ct -digits 6 > $OUT/power_vcd_clock_tree.rpt }
if {[catch {report_activity_annotation > $OUT/activity_annotation.rpt} err]} { puts "NOTE: $err" }
puts "WROTE $OUT/power_vcd.rpt"
exit
