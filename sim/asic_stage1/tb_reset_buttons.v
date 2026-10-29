`timescale 1ns/1ps

// Directed tests of the public frontend contract. The clock is driven manually
// so assertion with a stopped clock and exact release edges can be checked.
module tb_reset_buttons;
  reg clk = 1'b0;
  reg rst_n = 1'b1;
  reg boot_done = 1'b0;
  reg [3:0] buttons = 4'b0000;
  wire rst_sync_n, core_rst_n;
  wire [3:0] buttons_sync;
  integer checks = 0;
  integer rising_edges = 0;
  integer bit_index;
  integer phase_index;
  reg [3:0] one_button;

  reset_ctrl u_reset (
    .clk_i(clk), .rst_ni(rst_n), .mem_boot_done_i(boot_done),
    .rst_sync_no(rst_sync_n), .core_rst_no(core_rst_n)
  );

  btn_sync u_buttons (
    .clk_i(clk), .rst_ni(rst_sync_n), .btn_i(buttons),
    .btn_o(buttons_sync)
  );

  task check_state;
    input expected_sync;
    input expected_core;
    input [3:0] expected_buttons;
    input [8*120-1:0] label;
    begin
      checks = checks + 1;
      if ({rst_sync_n, core_rst_n, buttons_sync} !==
          {expected_sync, expected_core, expected_buttons}) begin
        $display("FAIL %0s time=%0t edge=%0d actual=%b/%b/%h expected=%b/%b/%h",
                 label, $time, rising_edges, rst_sync_n, core_rst_n,
                 buttons_sync, expected_sync, expected_core, expected_buttons);
        $fatal(1);
      end
    end
  endtask

  task tick;
    input expected_sync;
    input expected_core;
    input [3:0] expected_buttons;
    input [8*120-1:0] label;
    begin
      if (clk !== 1'b0) $fatal(1, "tick requires a low starting clock");
      #5 clk = 1'b1;
      rising_edges = rising_edges + 1;
      #1;
      check_state(expected_sync, expected_core, expected_buttons, label);
      #4 clk = 1'b0;
    end
  endtask

  initial begin
    // Ready memory and a held button: two reset synchronizer edges, then one
    // registered core-release edge. Button sampling starts after sync release.
    boot_done = 1'b1;
    buttons = 4'hf;
    #3 rst_n = 1'b0;
    #1 check_state(0, 0, 4'h0, "asynchronous assertion without any clock edge");
    #7 check_state(0, 0, 4'h0, "reset stays asserted with stopped low clock");
    rst_n = 1'b1;
    #3 check_state(0, 0, 4'h0, "external deassertion alone cannot release reset");
    tick(0, 0, 4'h0, "release edge 1");
    tick(1, 0, 4'h0, "release edge 2: synchronized reset only");
    tick(1, 1, 4'h0, "release edge 3: core ready; first button sample");
    tick(1, 1, 4'hf, "release edge 4: held buttons after two samples");
    tick(1, 1, 4'hf, "held buttons remain stable");

    // Exercise each channel, both transitions, and a pulse exactly one sample
    // wide. The pulse must pass through; there is no debounce filter.
    buttons = 4'h0;
    #2 check_state(1, 1, 4'hf, "button change cannot bypass registered output");
    tick(1, 1, 4'hf, "falling button first sample");
    tick(1, 1, 4'h0, "falling button second sample");
    for (bit_index = 0; bit_index < 4; bit_index = bit_index + 1) begin
      one_button = 4'b0001 << bit_index;
      buttons = one_button;
      tick(1, 1, 4'h0, "one-cycle button pulse first sample");
      buttons = 4'h0;
      tick(1, 1, one_button, "one-cycle pulse visible on second sample");
      tick(1, 1, 4'h0, "one-cycle pulse ends without debounce extension");
    end
    buttons = 4'hf;
    #2 buttons = 4'h0;
    #1 check_state(1, 1, 4'h0, "pulse entirely between edges is not sampled");
    tick(1, 1, 4'h0, "unsampled pulse first edge");
    tick(1, 1, 4'h0, "unsampled pulse second edge");

    // Alternating patterns on consecutive cycles prove there is no hidden
    // stability requirement and that all four channels are independent.
    buttons = 4'h5;
    tick(1, 1, 4'h0, "alternating inputs first sample");
    buttons = 4'ha;
    tick(1, 1, 4'h5, "alternating inputs preserve preceding sample");
    buttons = 4'h3;
    tick(1, 1, 4'ha, "alternating inputs do not require stability");
    buttons = 4'hc;
    tick(1, 1, 4'h3, "alternating inputs all channels");
    tick(1, 1, 4'hc, "final alternating input reaches output");

    // Restart during execution with clk stopped high. Assertion must propagate
    // through reset and buttons without another rising edge.
    #5 clk = 1'b1;
    rising_edges = rising_edges + 1;
    #1 check_state(1, 1, 4'hc, "running before high-clock reset");
    #3 rst_n = 1'b0;
    #1 check_state(0, 0, 4'h0, "asynchronous assertion with stopped high clock");
    boot_done = 1'b0;
    buttons = 4'h9;
    #8 check_state(0, 0, 4'h0, "held inputs cannot escape asserted reset");
    rst_n = 1'b1;
    #4 check_state(0, 0, 4'h0, "deassertion while clock remains high is not an edge");
    clk = 1'b0;
    tick(0, 0, 4'h0, "delayed memory release edge 1");
    tick(1, 0, 4'h0, "delayed memory release edge 2");
    tick(1, 0, 4'h0, "core held while memory is not ready");
    tick(1, 0, 4'h9, "buttons run independently during memory boot");
    tick(1, 0, 4'h9, "core remains held over extended boot");

    // Interrupt boot before it can release the core. A reset pulse with no
    // clock inside must restart the full synchronization sequence.
    #2 rst_n = 1'b0;
    #1 check_state(0, 0, 4'h0, "reset interrupts boot without a clock");
    #2 rst_n = 1'b1;
    #1 check_state(0, 0, 4'h0, "short external reset pulse requires fresh release");
    tick(0, 0, 4'h0, "restarted boot release edge 1");
    tick(1, 0, 4'h0, "restarted boot release edge 2");
    tick(1, 0, 4'h0, "restarted boot first button sample");
    tick(1, 0, 4'h9, "restarted boot held button returns");
    boot_done = 1'b1;
    #3 check_state(1, 0, 4'h9, "ready memory cannot release core between edges");
    tick(1, 1, 4'h9, "core releases at next edge after memory ready");
    tick(1, 1, 4'h9, "released core and held buttons stay stable");

    // Repeated assertions/deassertions at distinct offsets between edges.
    // These are digital phase tests, not analog metastability simulations.
    for (phase_index = 1; phase_index <= 4; phase_index = phase_index + 1) begin
      #(phase_index) rst_n = 1'b0;
      #1 check_state(0, 0, 4'h0, "repeated asynchronous reset during execution");
      #(5-phase_index) rst_n = 1'b1;
      #1 check_state(0, 0, 4'h0, "repeat release remains blocked without edge");
      tick(0, 0, 4'h0, "repeat synchronization edge 1");
      tick(1, 0, 4'h0, "repeat synchronization edge 2");
      tick(1, 1, 4'h0, "repeat registered core release");
      tick(1, 1, 4'h9, "held buttons recover after repeated reset");
    end

    $display("PASS reset/buttons: %0d state checks, %0d rising edges; async assertion, exact release, boot interruption, button latency/pulses/restarts",
             checks, rising_edges);
    $finish;
  end

  initial begin
    #100000;
    $fatal(1, "frontend test timeout");
  end
endmodule
