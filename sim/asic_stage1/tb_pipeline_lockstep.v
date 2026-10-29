`timescale 1ns/1ps
module tb_pipeline_lockstep;
  reg clk = 0, rst_n = 1;
  wire [3:0] leds, ref_leds;
  wire [6:0] seg1, seg2, ref_seg1, ref_seg2;
  wire miso, ref_miso;
  asic_top dut (
    .clk_i(clk), .rst_ni(rst_n), .btn_i(4'b0), .leds_o(leds), .seg1_o(seg1), .seg2_o(seg2),
    .spi_sclk_i(1'b0), .spi_mosi_i(1'b0), .spi_cs_n_i(1'b1), .spi_miso_o(miso)
  );
  ref_asic_top reference (
    .clk_i(clk), .rst_ni(rst_n), .btn_i(4'b0), .leds_o(ref_leds), .seg1_o(ref_seg1), .seg2_o(ref_seg2),
    .spi_sclk_i(1'b0), .spi_mosi_i(1'b0), .spi_cs_n_i(1'b1), .spi_miso_o(ref_miso)
  );
  always #50 clk = ~clk;
  integer cycles = 0, commits = 0, writes = 0, reads = 0;
  initial begin
    #7 rst_n = 0;
    #130 rst_n = 1;
    wait (dut.core_rst_ni === 1);
    repeat (10000) begin
      @(negedge clk);
      if ((^{dut.core_rst_ni, dut.instr_req, dut.instr_addr,
              dut.u_soc.u_core.pc_id, dut.u_soc.u_core.instr_valid_id,
              dut.u_soc.u_core.stall, dut.u_soc.u_core.rf_ready,
              dut.u_soc.u_core.rf_we, dut.u_soc.data_req,
              leds,seg1,seg2,miso,dut.u_soc.u_periph.cycles_q}) === 1'bx)
        $fatal(1, "Undefined control/PC/output at cycle %0d", cycles);
      if (dut.core_rst_ni !== reference.core_rst_ni ||
          {leds,seg1,seg2,miso} !== {ref_leds,ref_seg1,ref_seg2,ref_miso} ||
          dut.u_soc.u_periph.cycles_q !== reference.u_soc.u_periph.cycles_q)
        $fatal(1, "Peripheral/reset lockstep failure at cycle %0d", cycles);
      if ({dut.instr_req, dut.instr_addr, dut.u_soc.u_core.pc_id,
           dut.u_soc.u_core.instr_valid_id, dut.u_soc.u_core.stall,
           dut.u_soc.u_core.rf_ready, dut.u_soc.u_core.rf_we} !==
          {reference.instr_req, reference.instr_addr, reference.u_soc.u_core.pc_id,
           reference.u_soc.u_core.instr_valid_id, reference.u_soc.u_core.stall,
           reference.u_soc.u_core.rf_ready, reference.u_soc.u_core.rf_we})
        $fatal(1, "Pipeline/control lockstep failure at cycle %0d", cycles);
      if (dut.u_soc.u_core.rf_we) begin
        if ((^{dut.u_soc.u_core.rf_waddr,dut.u_soc.u_core.rf_wdata}) === 1'bx)
          $fatal(1, "Undefined RF write at cycle %0d", cycles);
        if ({dut.u_soc.u_core.rf_waddr,dut.u_soc.u_core.rf_wdata} !==
            {reference.u_soc.u_core.rf_waddr,reference.u_soc.u_core.rf_wdata})
          $fatal(1, "RF commit lockstep failure at cycle %0d", cycles);
        commits = commits + 1;
      end
      if (dut.u_soc.u_core.rf_ready && dut.u_soc.u_core.instr_valid_id) begin
        if ((^{dut.u_soc.u_core.rf_rdata_a,dut.u_soc.u_core.rf_rdata_b}) === 1'bx)
          $fatal(1, "Undefined valid operands at cycle %0d", cycles);
        if ({dut.u_soc.u_core.rf_rdata_a,dut.u_soc.u_core.rf_rdata_b} !==
            {reference.u_soc.u_core.rf_rdata_a,reference.u_soc.u_core.rf_rdata_b})
          $fatal(1, "RF operand/handshake failure at cycle %0d", cycles);
      end
      if (dut.u_soc.data_req !== reference.u_soc.data_req)
        $fatal(1, "Data request lockstep failure at cycle %0d", cycles);
      if (dut.u_soc.data_req) begin
        if ((^{dut.u_soc.data_we,dut.u_soc.data_be,dut.u_soc.data_addr}) === 1'bx ||
            (dut.u_soc.data_we && ((^dut.u_soc.data_wdata) === 1'bx)))
          $fatal(1, "Undefined valid data request at cycle %0d", cycles);
        if ({dut.u_soc.data_we,dut.u_soc.data_be,dut.u_soc.data_addr,dut.u_soc.data_wdata} !==
            {reference.u_soc.data_we,reference.u_soc.data_be,reference.u_soc.data_addr,reference.u_soc.data_wdata})
          $fatal(1, "Data bus lockstep failure at cycle %0d", cycles);
        if (dut.u_soc.data_we) writes = writes + 1;
        else reads = reads + 1;
      end
      cycles = cycles + 1;
    end
    if (commits < 100 || reads < 100 || writes < 2 || leds !== 4'hf)
      $fatal(1, "Insufficient game-startup lockstep activity");
    $display("PASS pipeline_lockstep cycles=%0d rf_commit_cycles=%0d read_request_cycles=%0d write_request_cycles=%0d", cycles, commits, reads, writes);
    $finish;
  end
  initial begin
    #2000000;
    $fatal(1, "Lockstep timeout");
  end
endmodule
