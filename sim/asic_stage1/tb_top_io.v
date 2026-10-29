`timescale 1ns/1ps
module tb_top_io;
  reg clk = 0, rst_n = 1;
  reg [3:0] btn = 4'h5;
  reg sclk = 0, mosi = 0, cs_n = 1;
  wire miso;
  wire [3:0] leds;
  wire [6:0] seg1, seg2;
  asic_top dut (
    .clk_i(clk), .rst_ni(rst_n), .btn_i(btn), .leds_o(leds),
    .seg1_o(seg1), .seg2_o(seg2), .spi_sclk_i(sclk),
    .spi_mosi_i(mosi), .spi_cs_n_i(cs_n), .spi_miso_o(miso)
  );
  always #50 clk = ~clk;
  reg [7:0] incoming = 8'h3c, outgoing = 0;
  integer bit_index;
  integer checked_timer = 0, checked_buttons = 0;
  reg saw_status_store = 0;
  reg [31:0] sampled_timer;
  always @(posedge clk) begin
    if (dut.u_soc.ram_req_o && dut.u_soc.ram_we_o && dut.u_soc.ram_addr_o == 32'd524)
      saw_status_store <= 1;
    if (dut.u_soc.per_req && !dut.u_soc.data_we) begin
      if (dut.u_soc.data_addr == 32'h8000000c) begin
        sampled_timer = dut.u_soc.u_periph.cycles_q;
        #1;
        if (dut.u_soc.data_rdata !== sampled_timer)
          $fatal(1, "Timer MMIO read latency or data changed");
        checked_timer = checked_timer + 1;
      end else if (dut.u_soc.data_addr == 32'h80000008) begin
        #1;
        if (dut.u_soc.data_rdata !== 32'h5)
          $fatal(1, "Button MMIO routing or latency changed");
        checked_buttons = checked_buttons + 1;
      end
    end
  end
  initial begin
    #7 rst_n = 0;
    #130 rst_n = 1;
    wait (dut.u_soc.u_spi.tx_hold === 8'h96);
    @(negedge clk);
    if (leds !== 4'ha || seg1 !== 7'h77 || seg2 !== 7'h6d)
      $fatal(1, "Logical display/LED mapping failed: expected A5 and LEDs A");
    if (dut.u_mem.mem[128] !== 32'h5 || dut.u_mem.mem[129] !== sampled_timer)
      $fatal(1, "CPU MMIO loads and ordinary-memory stores failed");
    cs_n = 0;
    repeat (10) @(negedge clk);
    // Slow SPI, mode 0, MSB first: each half-period is ten core cycles.
    for (bit_index = 7; bit_index >= 0; bit_index = bit_index - 1) begin
      mosi = incoming[bit_index];
      repeat (10) @(negedge clk);
      sclk = 1;
      #1 outgoing[bit_index] = miso;
      repeat (10) @(negedge clk);
      sclk = 0;
    end
    repeat (10) @(negedge clk);
    cs_n = 1;
    wait (dut.u_mem.mem[130] === 32'h3c);
    // Last program store proves a read from STATUS after PRICE cleared flag.
    wait (saw_status_store);
    @(posedge clk); #1;
    if (dut.u_mem.mem[131][0] !== 0 || outgoing !== 8'h96)
      $fatal(1, "SPI response/status mismatch: tx=%h status=%h", outgoing, dut.u_mem.mem[131]);
    if (checked_timer != 1 || checked_buttons != 1)
      $fatal(1, "Missing MMIO read checks");
    $display("PASS top_io display=A5 leds=A buttons=5 timer_reads=%0d spi_rx=3c spi_tx=%h", checked_timer, outgoing);
    $finish;
  end
  initial begin
    #300000;
    $fatal(1, "Top IO test timeout");
  end
endmodule
