`timescale 1ns/1ps
// Same stimuli are delivered to RTL and the synthesized complete macro.
// Internal RTL bus observations implement an independent arithmetic scoreboard;
// the netlist is checked exclusively through the actual logical top terminals.
module tb_full_game;
  parameter integer MemoryVariant = 0;
  reg clk = 0, rst_n = 1;
  reg [3:0] btn = 0;
  wire [3:0] leds;
  wire [6:0] seg1, seg2;
  wire miso;
  asic_top #(.MemoryVariant(MemoryVariant)) dut (
    .clk_i(clk), .rst_ni(rst_n), .btn_i(btn), .leds_o(leds),
    .seg1_o(seg1), .seg2_o(seg2), .spi_sclk_i(1'b0),
    .spi_mosi_i(1'b0), .spi_cs_n_i(1'b1), .spi_miso_o(miso)
  );
`ifdef WITH_NETLIST
  wire [3:0] syn_leds;
  wire [6:0] syn_seg1, syn_seg2;
  wire syn_miso;
  netlist_top syn (
    .clk_i(clk), .rst_ni(rst_n), .btn_i(btn), .leds_o(syn_leds),
    .seg1_o(syn_seg1), .seg2_o(syn_seg2), .spi_sclk_i(1'b0),
    .spi_mosi_i(1'b0), .spi_cs_n_i(1'b1), .spi_miso_o(syn_miso)
  );
`endif
  always #50 clk = ~clk; // Production clock is 10 MHz in all runs.

  integer wait_ticks = 3000, tenth_ticks = 100;
  integer cycle = 0, compared_cycles = 0, trace;
  integer phase = 0; // 0 initialization/wait, 1 reaction, 2 result, 3 wrong, 4 done
  integer correct = 0, wrongs = 0, attempts = 0, sum_tenths = 0;
  integer reaction_reads = 0, wait_reads = 0, capped = 0, average = -1;
  integer previous_result_cycle = 0, done_cycle = 0, first_active_cycle = 0;
  integer epoch = 0, resets = 0, held_checks = 0;
  reg waiting = 0, expect_wrong = 0, trace_enabled = 0;
  reg [31:0] wait_start = 0, reaction_start = 0, reaction_end = 0;
  reg [31:0] elapsed;
  integer tenths, expected_digit, captured_digit;
  string trace_path;

  function integer digit;
    input [6:0] segments;
    begin
      case (segments)
        7'h3f:digit=0; 7'h06:digit=1; 7'h5b:digit=2; 7'h4f:digit=3;
        7'h66:digit=4; 7'h6d:digit=5; 7'h7d:digit=6; 7'h07:digit=7;
        7'h7f:digit=8; 7'h6f:digit=9; 7'h77:digit=10; 7'h7c:digit=11;
        7'h39:digit=12; 7'h5e:digit=13; 7'h79:digit=14; 7'h71:digit=15;
        default:digit=-100;
      endcase
    end
  endfunction

  always @(negedge rst_n) begin
    phase = 0; correct = 0; wrongs = 0; attempts = 0;
    sum_tenths = 0; reaction_reads = 0; wait_reads = 0;
    capped = 0; average = -1; waiting = 0; first_active_cycle = 0;
    previous_result_cycle = 0; done_cycle = 0;
    resets = resets + 1;
  end

  // Sample requests before the active edge, exactly as the peripheral does.
  // The expected arithmetic is computed independently of firmware registers.
  always @(posedge clk) begin
    cycle = cycle + 1;
    if (dut.core_rst_ni && dut.u_soc.per_req) begin
      if (!dut.u_soc.data_we && dut.u_soc.data_addr == 32'h8000000c) begin
        if (phase == 1) begin
          if (reaction_reads == 0) reaction_start = dut.u_soc.u_periph.cycles_q;
          else if (reaction_reads == 1) reaction_end = dut.u_soc.u_periph.cycles_q;
          else $fatal(1, "Unexpected third reaction timer read");
          reaction_reads = reaction_reads + 1;
        end else if (waiting) begin
          if (wait_reads == 0) wait_start = dut.u_soc.u_periph.cycles_q;
          wait_reads = wait_reads + 1;
        end
      end
      if (dut.u_soc.data_we && dut.u_soc.data_addr == 32'h80000004) begin
        if (dut.u_soc.data_wdata[3:0] == 4'hf) begin
          if (correct >= 10) $fatal(1, "An eleventh round started");
          waiting = 1; wait_reads = 0; phase = 0;
        end else if (dut.u_soc.data_wdata[3:0] != 0) begin
          if (!waiting || wait_reads < 2) $fatal(1, "LED activated without timed wait");
          elapsed = dut.u_soc.u_periph.cycles_q - wait_start;
          if (elapsed < wait_ticks || elapsed > wait_ticks + 160)
            $fatal(1, "3s scaled wait wrong: %0d expected [%0d,%0d]", elapsed, wait_ticks, wait_ticks+160);
          if ((dut.u_soc.data_wdata[3:0] & (dut.u_soc.data_wdata[3:0] - 1)) != 0)
            $fatal(1, "Reaction LED is not one-hot");
          phase = 1; waiting = 0; reaction_reads = 0; attempts = attempts + 1;
          if (!first_active_cycle) first_active_cycle = cycle;
          $display("EVENT epoch=%0d cycle=%0d attempt=%0d active_led=%h wait=%0d", epoch, cycle, attempts, dut.u_soc.data_wdata[3:0], elapsed);
        end else if (!expect_wrong || phase != 1) begin
          $fatal(1, "Unexpected zero LED store");
        end
      end
      if (dut.u_soc.data_we && dut.u_soc.data_addr == 32'h80000000) begin
        captured_digit = dut.u_soc.data_wdata[7:0];
        if (captured_digit == 8'hee) begin
          if (!expect_wrong || phase != 1 || reaction_reads != 1)
            $fatal(1, "Unexpected error display or incorrect reaction reads");
          wrongs = wrongs + 1; phase = 3;
          if (dut.u_soc.u_core.u_rf.regs_q[10] !== correct || dut.u_soc.u_core.u_rf.regs_q[12] !== sum_tenths)
            $fatal(1, "Wrong input altered correct-round count or accumulated time");
          $display("EVENT epoch=%0d cycle=%0d wrong=%0d correct=%0d sum=%0d", epoch, cycle, wrongs, correct, sum_tenths);
        end else if (correct < 10) begin
          if (expect_wrong || phase != 1 || reaction_reads != 2)
            $fatal(1, "Unexpected round result");
          elapsed = reaction_end - reaction_start;
          tenths = elapsed / tenth_ticks;
          if (tenths > 99) begin tenths = 99; capped = capped + 1; end
          expected_digit = ((tenths / 10) << 4) | (tenths % 10);
          if (captured_digit != expected_digit)
            $fatal(1, "Round BCD wrong: got=%h expected=%h elapsed=%0d", captured_digit, expected_digit, elapsed);
          sum_tenths = sum_tenths + tenths;
          correct = correct + 1; phase = 2; previous_result_cycle = cycle;
          $display("EVENT epoch=%0d cycle=%0d correct=%0d tenths=%0d elapsed=%0d sum=%0d", epoch, cycle, correct, tenths, elapsed, sum_tenths);
        end else begin
          if (phase != 2 || average >= 0) $fatal(1, "Unexpected average write");
          average = sum_tenths / 10;
          expected_digit = ((average / 10) << 4) | (average % 10);
          if (captured_digit != expected_digit)
            $fatal(1, "Average BCD wrong: got=%h expected=%h sum=%0d", captured_digit, expected_digit, sum_tenths);
          phase = 4; done_cycle = cycle;
          $display("EVENT epoch=%0d cycle=%0d average=%0d sum=%0d", epoch, cycle, average, sum_tenths);
        end
        #1;
        if (((digit(seg1) << 4) | digit(seg2)) != captured_digit)
          $fatal(1, "Logical display encoding mismatch");
      end
    end
  end

  always @(posedge clk) begin
    #2;
    if (cycle > 1) begin
      if ((^{leds, seg1, seg2, miso}) === 1'bx)
        $fatal(1, "Unknown external RTL output after reset");
`ifdef WITH_NETLIST
      if ({leds,seg1,seg2,miso} !== {syn_leds,syn_seg1,syn_seg2,syn_miso})
        $fatal(1, "RTL/netlist mismatch cycle=%0d rtl=%h syn=%h", cycle, {leds,seg1,seg2,miso}, {syn_leds,syn_seg1,syn_seg2,syn_miso});
`endif
      compared_cycles = compared_cycles + 1;
    end
    if (trace_enabled)
      $fwrite(trace, "%0d,%0d,%h,%h,%h,%h,%h\n", cycle, rst_n, btn, leds, seg1, seg2, miso);
  end

  task wait_phase;
    input integer wanted;
    integer bound;
    begin
      bound = 0;
      while (phase != wanted && bound < 100000) begin @(negedge clk); bound = bound + 1; end
      if (phase != wanted) $fatal(1, "Timeout phase=%0d wanted=%0d correct=%0d", phase, wanted, correct);
    end
  endtask

  task reset_game;
    begin
      @(negedge clk); rst_n = 0; btn = 0; expect_wrong = 0;
      repeat (4) @(negedge clk);
      if (leds !== 0 || seg1 !== 7'h3f || seg2 !== 7'h3f)
        $fatal(1, "Reset logical outputs are not LEDs0/display00");
      rst_n = 1;
    end
  endtask

  task play_wrong;
    input integer multiple;
    reg [3:0] mask;
    integer held;
    begin
      wait_phase(1); mask = leds;
      repeat (2*tenth_ticks + 50) @(negedge clk);
      expect_wrong = 1;
      // Cover both one incorrect button and simultaneous correct+incorrect buttons.
      btn = ((mask == 4'h8) ? 4'h1 : (mask << 1));
      if (multiple) btn = btn | mask;
      wait_phase(3);
      for (held = 0; held < 400; held = held + 1) begin
        @(negedge clk);
        if (phase != 3 || leds !== 0 || seg1 !== 7'h79 || seg2 !== 7'h79)
          $fatal(1, "Held wrong button did not wait for release");
        held_checks = held_checks + 1;
      end
      btn = 0; expect_wrong = 0;
      wait_phase(1);
    end
  endtask

  task play_correct;
    input integer desired_tenths;
    reg [3:0] mask;
    reg [13:0] result_segments;
    integer held, prior_correct;
    begin
      wait_phase(1); mask = leds; prior_correct = correct;
      repeat (desired_tenths*tenth_ticks + tenth_ticks/2) @(negedge clk);
      btn = mask;
      wait_phase(2);
      if (correct != prior_correct + 1) $fatal(1, "Correct round count did not increment once");
      result_segments = {seg1,seg2};
      for (held = 0; held < 400; held = held + 1) begin
        @(negedge clk);
        if (phase != 2 || leds !== mask || {seg1,seg2} !== result_segments)
          $fatal(1, "Held correct button advanced game before release");
        held_checks = held_checks + 1;
      end
      btn = 0;
    end
  endtask

  initial begin
    if ($value$plusargs("WAIT_TICKS=%d", wait_ticks)) begin end
    if ($value$plusargs("TENTH_TICKS=%d", tenth_ticks)) begin end
    if (wait_ticks <= 0 || tenth_ticks < 20) $fatal(1, "Invalid accelerated timing profile");
    if ($value$plusargs("TRACE=%s", trace_path)) begin
      trace = $fopen(trace_path, "w");
      if (!trace) $fatal(1, "Cannot create trace");
      $fwrite(trace, "cycle,reset_n,buttons,leds,segment_high,segment_low,spi_miso\n");
      trace_enabled = 1;
    end
    #7 rst_n = 0;
    repeat (4) @(negedge clk); rst_n = 1;
    repeat (40) @(negedge clk); // Interrupt B's 144-cycle hardware loader.
    reset_game();
    wait_phase(1);
    // Reset an active round; all counters, game state and output values restart.
    repeat (50) @(negedge clk);
    epoch = 1;
    reset_game();
    play_correct(1);
    play_correct(2);
    play_wrong(0);
    play_wrong(1);
    play_correct(3);
    play_correct(4);
    play_correct(5);
    play_correct(6);
    play_correct(12);
    play_correct(23);
    play_correct(101); // Exercise saturation to 99 tenths.
    play_correct(7);
    wait_phase(4);
    repeat (1000) @(negedge clk);
    if (correct != 10 || wrongs != 2 || attempts != 12 || capped != 1 || resets != 3)
      $fatal(1, "Missing coverage correct=%0d wrong=%0d attempts=%0d capped=%0d resets=%0d", correct, wrongs, attempts, capped, resets);
    if (dut.u_soc.u_core.u_rf.regs_q[10] !== 10 || dut.u_soc.u_core.u_rf.regs_q[12] !== sum_tenths)
      $fatal(1, "Final firmware round count or accumulated tenths mismatch");
    $display("PASS full_game variant=%0d cycles=%0d compared=%0d correct=%0d wrong=%0d attempts=%0d capped=%0d average=%0d sum=%0d held_checks=%0d resets=%0d first_active=%0d last_result=%0d done=%0d", MemoryVariant, cycle, compared_cycles, correct, wrongs, attempts, capped, average, sum_tenths, held_checks, resets, first_active_cycle, previous_result_cycle, done_cycle);
    if (trace_enabled) $fclose(trace);
    $finish;
  end
  initial begin
    repeat (500000) @(posedge clk);
    $fatal(1, "Full game watchdog timeout");
  end
endmodule
