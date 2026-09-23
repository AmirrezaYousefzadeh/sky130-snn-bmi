# Per-pin activity power from accumulated toggle counts (tools/vcd_toggles + power/toggles_to_activity.py) instead of a stored VCD.
# Env: RUN_DIR TOP LIB_SC LIB_SRAM VCD_FILE VCD_SCOPE PERIOD_NS OUT MACRO_INST
set RUN $::env(RUN_DIR); set TOP $::env(TOP); set OUT $::env(OUT)
if {[info exists ::env(ORD_LEFS)]} { foreach l $::env(ORD_LEFS) { read_lef $l } }   ;# OpenROAD (not sta) needs the technology and cell LEF before read_verilog
foreach l $::env(LIB_SC) { read_liberty $l }      ;# one or several liberty files (space-separated; gzip accepted)
if {[info exists ::env(LIB_SRAM)] && [file exists $::env(LIB_SRAM)]} { read_liberty $::env(LIB_SRAM) }
# NETLIST / SPEF may be preset (multi-PDK study: OpenROAD-flow-scripts result directories)
set nl [expr {[info exists ::env(NETLIST)] ? $::env(NETLIST) : "$RUN/final/nl/$TOP.nl.v"}]
set spef [expr {[info exists ::env(SPEF)] ? $::env(SPEF) : "$RUN/final/spef/nom/$TOP.nom.spef"}]
foreach f $nl { read_verilog $f }                  ;# round 6 (E6): several netlists (blocks of a system plus the structural wrapper) may be listed
link_design $TOP
foreach sp $spef {                                 ;# a SPEF entry "inst:path" annotates the block instance inst (read_spef -path), a plain path the top
  if {[regexp {^([^:]+):(.+)$} $sp -> inst path]} { read_spef -path $inst $path; puts "SPEF $path -> $inst" } else { read_spef $sp }
}
set period $::env(PERIOD_NS); set half [expr {$period / 2.0}]
set clkport [expr {[info exists ::env(CLK_PORT)] ? $::env(CLK_PORT) : "clk"}]      ;# round 5: designs whose clock port is not "clk" (front end: clk5)
create_clock -name clk -period $period -waveform [list 0.0 $half] [get_ports $clkport]
if {[info exists ::env(CLK2_PORT)]} {                                               ;# optional second (asynchronous) clock, e.g. the 32.768 kHz clock of the front end
  create_clock -name clk2 -period $::env(CLK2_PERIOD) [get_ports $::env(CLK2_PORT)]
  set_clock_groups -asynchronous -group [get_clocks clk] -group [get_clocks clk2]
}
set_propagated_clock [all_clocks]
# Round 5: OpenSTA (2.6.0 and the OpenROAD build) takes the activity of every clock-network pin from the clock definition, not
# from the annotation, so gated clock subtrees would be counted as always toggling. CLK_STOP_ICG=1 stops the clock propagation at
# the outputs of all clock-gate cells (their subtrees are then annotated from the waveform); CLK_STOP_PINS lists further pins or
# ports (e.g. an oscillator-gated clock port) where the propagation stops. Timing is not reported in the power runs.
if {[info exists ::env(CLK_STOP_PINS)]} { foreach p $::env(CLK_STOP_PINS) { set o [get_pins -quiet $p]; if {![llength $o]} { set o [get_ports -quiet $p] }
  if {[llength $o]} { set_clock_sense -stop_propagation $o; puts "CLK_STOP_PINS: $p" } } }
if {[info exists ::env(CLK_STOP_ICG)] && $::env(CLK_STOP_ICG) != 0} { set __icg {}
  foreach c [get_cells -hierarchical *] { set r [get_property $c ref_name]
    if {[string match {*dlclkp*} $r] || [string match {ICGx*} $r] || [string match {*icgt*} $r] || [string match {*lgcp*} $r] || [string match {CLKGATE*} $r]} {
      foreach p [get_pins -of_objects $c] { if {[get_property $p direction] eq "output"} { lappend __icg $p } } } }
  if {[llength $__icg]} { set_clock_sense -stop_propagation $__icg; puts "CLK_STOP_ICG: [llength $__icg] clock-gate outputs" } }
file mkdir $OUT
puts "sourcing activities $::env(ACT_TCL)"
source $::env(ACT_TCL)
# GLOBAL_ZERO=1 (round 5, clock correction): all data activities zero -> the report contains the clock-driven power only
if {[info exists ::env(GLOBAL_ZERO)]} { set __gd [expr {[info exists ::env(GLOBAL_ZERO_DUTY)] ? $::env(GLOBAL_ZERO_DUTY) : 0.5}]; set_power_activity -global -activity 0 -duty $__gd; puts "GLOBAL_ZERO: data activities set to zero, duty $__gd" }
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
# timing at this liberty (liberty time unit): worst setup and hold slack of the annotated design (round 5: low-voltage re-evaluation)
catch { set __ws [sta::worst_slack_cmd max]; set __wh [sta::worst_slack_cmd min]; puts "WORST_SETUP_SLACK $__ws"; puts "WORST_HOLD_SLACK $__wh"
        set __fh [open $OUT/slack.txt w]; puts $__fh "setup_ws $__ws"; puts $__fh "hold_ws $__wh"; close $__fh }
puts "WROTE $OUT/power_vcd.rpt"
exit

# timing summary at this liberty (multi-PDK study: liberty swaps on a routed netlist)
catch { report_worst_slack -max -digits 3 }   ;# prints "worst slack max <value>" in the liberty time unit
