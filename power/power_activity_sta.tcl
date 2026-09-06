# Activity-based power for bmi_snn_top using VCD-derived rates (adapted from sky130_vex2_soc flow).
set ROOT $::env(ROOT)
set RUN  $::env(RUN_DIR)
set OUT  $::env(POWER_OUT)
set ACT  $::env(ACTIVITY_TCL)
source $ACT
set lib_sc   $::env(LIB_SC)
set lib_sram $::env(LIB_SRAM)
set netlist "$RUN/final/nl/bmi_snn_top.nl.v"
set spef    "$RUN/final/spef/nom/bmi_snn_top.nom.spef"
read_liberty $lib_sc
read_liberty $lib_sram
read_verilog $netlist
link_design bmi_snn_top
read_spef $spef

set period $::mnist_design_period_ns
set half   [expr {$period / 2.0}]
create_clock -name clk -period $period -waveform [list 0.0 $half] [get_ports clk]
set_propagated_clock [get_clocks clk]

source [file join $ROOT power power_icg_utils.tcl]
set ::power_core_icg_gate [power_find_core_icg_gate]
set en_duty [power_core_enable_duty_from_avg]
puts "core_icg_gate=$::power_core_icg_gate core_clk_en_duty=$en_duty"

set_power_activity -global -activity $::mnist_global_activity -duty 0.5
foreach p {reset ev_valid tick mode_dense} {
  if {[info exists ::mnist_act($p)] && [llength [get_ports -quiet $p]]} {
    set_power_activity -input_ports [get_ports $p] -activity $::mnist_act($p) -duty $::mnist_duty($p)
  }
}
if {[llength [get_pins -quiet u_wmem/ce]] && [info exists ::mnist_act(wmem_ce)]} {
  set_power_activity -pins [get_pins u_wmem/ce] -activity $::mnist_act(wmem_ce) -duty $::mnist_duty(wmem_ce)
}
if {[llength [get_pins -quiet u_wmem/we]] && [info exists ::mnist_act(wmem_we)]} {
  set_power_activity -pins [get_pins u_wmem/we] -activity $::mnist_act(wmem_we) -duty $::mnist_duty(wmem_we)
}

file mkdir $OUT
power_apply_core_clk_enable 1.0
report_power -digits 6 > $OUT/power_awake.rpt
report_power -instances [get_cells -hierarchical *] -digits 4 > $OUT/power_by_instance_awake.rpt
power_apply_core_clk_enable 0.0
report_power -digits 6 > $OUT/power_sleep.rpt
file copy -force $OUT/power_awake.rpt $OUT/power_activity.rpt
file copy -force $OUT/power_by_instance_awake.rpt $OUT/power_by_instance.rpt

power_apply_core_clk_enable 1.0
set clk_tree_cells {}
foreach cell [get_cells -quiet -hierarchical *] {
  set ref [get_property $cell ref_name]
  if {[string match {*clkbuf*} $ref] || [string match {*clkinv*} $ref] || [string match {*clkdly*} $ref] || [string match {*dlclkp*} $ref]} {
    lappend clk_tree_cells $cell
  }
}
if {[llength $clk_tree_cells] > 0} {
  report_power -instances $clk_tree_cells -digits 6 > $OUT/power_clock_tree.rpt
} else {
  set fp [open $OUT/power_clock_tree.rpt w]; puts $fp "no clock-tree cells matched"; close $fp
}
# macro alone (awake)
report_power -instances [get_cells u_wmem] -digits 6 > $OUT/power_macro_awake.rpt
power_apply_core_clk_enable 0.0
report_power -instances [get_cells u_wmem] -digits 6 > $OUT/power_macro_sleep.rpt
puts "WROTE $OUT/power_awake.rpt $OUT/power_sleep.rpt"
exit
