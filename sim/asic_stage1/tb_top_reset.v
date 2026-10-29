`timescale 1ns/1ps
module tb_top_reset;
  reg clk = 0, rst_n = 1;
  wire [3:0] leds;
  wire [6:0] seg1, seg2;
  wire miso;
  asic_top dut (
    .clk_i(clk), .rst_ni(rst_n), .btn_i(4'b0), .leds_o(leds),
    .seg1_o(seg1), .seg2_o(seg2), .spi_sclk_i(1'b0),
    .spi_mosi_i(1'b0), .spi_cs_n_i(1'b1), .spi_miso_o(miso)
  );
  always #50 clk = ~clk;
  integer first_fetches = 0, executions = 0, cycle;
  reg first_pending = 1;
  reg saw_leds;
  always @(negedge dut.core_rst_ni) first_pending = 1;
  always @(posedge clk) begin
    if (rst_n === 0 || dut.core_rst_ni === 0) begin
      if (dut.instr_req !== 0 || dut.data_req !== 0 || dut.data_we !== 0 ||
          dut.u_soc.per_req !== 0 || dut.u_soc.spi_req !== 0)
        $fatal(1, "Bus request escaped core reset");
      if (dut.u_soc.u_periph.cycles_q !== 0 || leds !== 0 ||
          seg1 !== 7'h3f || seg2 !== 7'h3f || miso !== 0)
        $fatal(1, "Peripheral reset values incorrect (display must show 00)");
    end else if (dut.core_rst_ni === 1) begin
      if (dut.mem_boot_done !== 1) $fatal(1, "CPU ran before memory ready");
      if (first_pending) begin
        if (dut.instr_req !== 1 || dut.instr_addr !== 0)
          $fatal(1, "First fetch must request address 0");
        if (dut.u_soc.u_periph.cycles_q !== 0)
          $fatal(1, "Counter includes boot latency");
        first_pending = 0;
        first_fetches = first_fetches + 1;
      end
    end
  end
  task check_execution;
    begin
      wait (dut.core_rst_ni === 1);
      saw_leds = 0;
      for (cycle = 1; cycle <= 2000; cycle = cycle + 1) begin
        @(posedge clk); #1;
        if (dut.u_soc.u_periph.cycles_q !== cycle)
          $fatal(1, "Counter misaligned: got %0d expected %0d", dut.u_soc.u_periph.cycles_q, cycle);
        if ((^dut.instr_addr) === 1'bx) $fatal(1, "Undefined instruction PC");
        if (leds == 4'hf) saw_leds = 1;
      end
      if (!saw_leds) $fatal(1, "Game startup did not light all LEDs");
      executions = executions + 1;
    end
  endtask
  initial begin
    #7 rst_n = 0;
    #1;
    if (dut.core_rst_ni !== 0 || dut.rst_sync_ni !== 0)
      $fatal(1, "Asynchronous assertion failed");
    #123 rst_n = 1;
    // Interrupt the release before its second sampling edge.
    @(posedge clk); #13 rst_n = 0;
    #1;
    if (dut.core_rst_ni !== 0) $fatal(1, "Premature release");
    #63 rst_n = 1;
    // Interrupt boot independently of the programmable ready delay.
    wait (dut.rst_sync_ni === 1);
    #13 rst_n = 0;
    #1;
    if (dut.mem_boot_done !== 0 || dut.core_rst_ni !== 0)
      $fatal(1, "Reset during boot failed");
    #173 rst_n = 1;
    check_execution;
    // Warm reset after the program has modified RF and peripheral state.
    #17 rst_n = 0;
    #1;
    if (leds !== 0 || dut.u_soc.u_periph.cycles_q !== 0)
      $fatal(1, "Warm reset did not clear peripheral state immediately");
    #157 rst_n = 1;
    check_execution;
    if (first_fetches != 2) $fatal(1, "Unexpected first fetch count");
    $display("PASS top_reset executions=%0d first_fetches=%0d active_cycles_each=2000", executions, first_fetches);
    $finish;
  end
  initial begin
    #2000000;
    $fatal(1, "Top reset test timeout");
  end
endmodule
