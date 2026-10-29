`timescale 1ns/1ps
module tb_top_memories;
  reg clk=0, rst_a=1, rst_b=1;
  wire [3:0] led_a,led_b;
  wire [6:0] seg1_a,seg2_a,seg1_b,seg2_b;
  wire miso_a,miso_b;
  always #50 clk=~clk;
  asic_top #(.MemoryVariant(0)) a (
    .clk_i(clk), .rst_ni(rst_a), .btn_i(4'b0), .leds_o(led_a),
    .seg1_o(seg1_a), .seg2_o(seg2_a), .spi_sclk_i(1'b0),
    .spi_mosi_i(1'b0), .spi_cs_n_i(1'b1), .spi_miso_o(miso_a)
  );
  asic_top #(.MemoryVariant(1)) b (
    .clk_i(clk), .rst_ni(rst_b), .btn_i(4'b0), .leds_o(led_b),
    .seg1_o(seg1_b), .seg2_o(seg2_b), .spi_sclk_i(1'b0),
    .spi_mosi_i(1'b0), .spi_cs_n_i(1'b1), .spi_miso_o(miso_b)
  );
  integer cycles=0, epochs=0, mmio_reads=0, ram_reads=0, ram_writes=0;
  reg compare_active=0, first_a=1, first_b=1;
  always @(negedge a.core_rst_ni) first_a=1;
  always @(negedge b.core_rst_ni) first_b=1;
  always @(posedge clk) begin
    if (a.core_rst_ni === 0)
      if (a.instr_req !== 0 || a.data_req !== 0 || a.data_we !== 0 ||
          a.u_soc.u_periph.cycles_q !== 0)
        $fatal(1,"A accessed memory/counter during reset");
    if (b.core_rst_ni === 0)
      if (b.instr_req !== 0 || b.data_req !== 0 || b.data_we !== 0 ||
          b.u_soc.u_periph.cycles_q !== 0)
        $fatal(1,"B accessed memory/counter before boot completed");
    if (a.core_rst_ni === 1 && first_a) begin
      if (a.instr_addr !== 0 || a.instr_req !== 1 || a.mem_boot_done !== 1)
        $fatal(1,"A first fetch/reset readiness failed");
      first_a=0;
    end
    if (b.core_rst_ni === 1 && first_b) begin
      if (b.instr_addr !== 0 || b.instr_req !== 1 || b.mem_boot_done !== 1)
        $fatal(1,"B first fetch/reset readiness failed");
      first_b=0;
    end
    if (compare_active && a.core_rst_ni) begin
      if (a.u_soc.data_req && !a.u_soc.data_we && a.u_soc.data_addr[31]) mmio_reads=mmio_reads+1;
      if (a.data_req && !a.data_we) ram_reads=ram_reads+1;
      if (a.data_req && a.data_we) ram_writes=ram_writes+1;
    end
  end
  task aligned_boot;
    begin
      // B writes 144 words, A is ready after one edge: align execution by
      // releasing A's external reset 143 clocks later. Record this offset.
      @(negedge clk); rst_b=1;
      repeat (143) @(negedge clk);
      rst_a=1;
      wait(a.core_rst_ni===1 || b.core_rst_ni===1);
      #1;
      if (a.core_rst_ni !== 1 || b.core_rst_ni !== 1)
        $fatal(1,"Expected 143-cycle A/B boot difference");
    end
  endtask
  task compare_game;
    integer n;
    begin
      compare_active=1;
      for(n=1;n<=10000;n=n+1) begin
        @(posedge clk); #1;
        if (a.u_soc.u_periph.cycles_q !== n || b.u_soc.u_periph.cycles_q !== n)
          $fatal(1,"Boot included in game counter");
        if ((^{a.instr_req,a.instr_addr,a.u_soc.u_core.pc_id,a.u_soc.u_core.instr_valid_id,
               miso_a,a.u_soc.u_core.stall,a.u_soc.u_core.rf_ready,
               a.u_soc.u_core.rf_we,a.u_soc.data_req,led_a,seg1_a,seg2_a}) === 1'bx)
          $fatal(1,"Unknown A controls");
        if ({a.instr_req,a.instr_addr,a.u_soc.u_core.pc_id,a.u_soc.u_core.instr_valid_id,
             a.u_soc.u_core.stall,a.u_soc.u_core.rf_ready,a.u_soc.u_core.rf_we,
             a.u_soc.data_req,led_a,seg1_a,seg2_a,miso_a} !==
            {b.instr_req,b.instr_addr,b.u_soc.u_core.pc_id,b.u_soc.u_core.instr_valid_id,
             b.u_soc.u_core.stall,b.u_soc.u_core.rf_ready,b.u_soc.u_core.rf_we,
             b.u_soc.data_req,led_b,seg1_b,seg2_b,miso_b})
          $fatal(1,"A/B control/IO mismatch at execution cycle %0d",n);
        if (a.u_soc.u_core.rf_we) begin
          if ((^{a.u_soc.u_core.rf_waddr,a.u_soc.u_core.rf_wdata})===1'bx ||
              {a.u_soc.u_core.rf_waddr,a.u_soc.u_core.rf_wdata} !==
              {b.u_soc.u_core.rf_waddr,b.u_soc.u_core.rf_wdata})
            $fatal(1,"A/B RF write mismatch");
        end
        if (a.u_soc.data_req) begin
          if ((^{a.u_soc.data_addr,a.u_soc.data_we,a.u_soc.data_be})===1'bx ||
              {a.u_soc.data_addr,a.u_soc.data_we,a.u_soc.data_be} !==
              {b.u_soc.data_addr,b.u_soc.data_we,b.u_soc.data_be})
            $fatal(1,"A/B data transaction mismatch");
          if (a.u_soc.data_we && ((^a.u_soc.data_wdata)===1'bx || a.u_soc.data_wdata !== b.u_soc.data_wdata))
            $fatal(1,"A/B store data mismatch");
        end
        cycles=cycles+1;
      end
      compare_active=0;
      if (led_a !== 4'hf) $fatal(1,"Game startup LEDs missing");
      epochs=epochs+1;
    end
  endtask
  initial begin
    #7; rst_a=0; rst_b=0;
    // Abort B's actual loader while A remains held in reset.
    @(negedge clk); rst_b=1;
    repeat(70) @(negedge clk);
    if(b.mem_boot_done!==0 || b.core_rst_ni!==0) $fatal(1,"B finished too early");
    #17 rst_b=0;
    aligned_boot;
    compare_game;
    #17; rst_a=0; rst_b=0;
    #1;
    if (a.u_soc.u_periph.cycles_q!==0 || b.u_soc.u_periph.cycles_q!==0)
      $fatal(1,"Repeated external reset not immediate");
    aligned_boot;
    compare_game;
    if (mmio_reads < 100 || ram_reads != 0 || ram_writes != 0)
      $fatal(1,"Unexpected memory use in sampled original game interval");
    $display("PASS top_memories epochs=%0d compared_cycles=%0d boot_offset_cycles=143 mmio_reads=%0d ordinary_ram_reads=%0d ordinary_ram_writes=%0d",epochs,cycles,mmio_reads,ram_reads,ram_writes);
    $finish;
  end
  initial begin #4000000; $fatal(1,"A/B top timeout"); end
endmodule
