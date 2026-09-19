current_design bmi_snn_lmin2
set clk_name clk
set clk_port_name clk
set clk_period 200
set clk_io_pct 0.2
set clk_port [get_ports $clk_port_name]
create_clock -name $clk_name -period $clk_period $clk_port
set non_clock_inputs [lsearch -inline -all -not -exact [all_inputs] $clk_port]
set_input_delay  [expr $clk_period * $clk_io_pct] -clock $clk_name $non_clock_inputs
set_output_delay [expr $clk_period * $clk_io_pct] -clock $clk_name [all_outputs]
set_false_path -from [get_ports reset]
set_false_path -from [get_ports mode_dense]
# latch-based weight memory: contents are static while decoding (writes only when idle) -> paths launched from the latches are
# false paths; the hold check at the latch data pins (data stable from the opening edge for a full cycle) is waived, as on sky130
set wlatches [all_registers -level_sensitive -cells]
if { [llength $wlatches] > 0 } { set_false_path -from $wlatches; set_false_path -hold -to [all_registers -level_sensitive -data_pins] }
