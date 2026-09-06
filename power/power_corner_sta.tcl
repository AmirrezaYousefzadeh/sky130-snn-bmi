# Same per-net VCD-activity power as power_vcd_sta.tcl, but with the liberty of another PVT corner (voltage scaling
# study) and a timing summary at that corner. Env: RUN_DIR TOP LIB_SC VCD_FILE VCD_SCOPE PERIOD_NS OUT
set RUN $::env(RUN_DIR); set TOP $::env(TOP); set OUT $::env(OUT)
read_liberty $::env(LIB_SC)
read_verilog "$RUN/final/nl/$TOP.nl.v"
link_design $TOP
read_spef "$RUN/final/spef/nom/$TOP.nom.spef"
set period $::env(PERIOD_NS); set half [expr {$period / 2.0}]
create_clock -name clk -period $period -waveform [list 0.0 $half] [get_ports clk]
set_propagated_clock [get_clocks clk]
file mkdir $OUT
puts "reading VCD $::env(VCD_FILE) scope $::env(VCD_SCOPE)"
read_power_activities -scope $::env(VCD_SCOPE) -vcd $::env(VCD_FILE)
report_power -digits 6 > $OUT/power_vcd.rpt
report_checks -path_delay max -format full_clock_expanded > $OUT/setup.rpt
report_checks -path_delay min -format full_clock_expanded > $OUT/hold.rpt
set ws [sta::worst_slack_cmd max]
puts "WORST_SETUP_SLACK_NS $ws"
set fh [open $OUT/slack.txt w]; puts $fh "setup_ws_ns $ws"; puts $fh "hold_ws_ns [sta::worst_slack_cmd min]"; close $fh
puts "WROTE $OUT/power_vcd.rpt"
exit
