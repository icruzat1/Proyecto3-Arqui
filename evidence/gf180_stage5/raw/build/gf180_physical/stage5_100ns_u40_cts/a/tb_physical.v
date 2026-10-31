`timescale 1ns/1ps
module tb_physical;
  reg clk=0, rst_n=1, enabled=0;
  reg [3:0] btn=0;
  reg sclk=0, mosi=0, cs_n=1;
  wire [3:0] r_led,g_led;
  wire [6:0] r_s1,r_s2,g_s1,g_s2;
  wire r_miso,g_miso;
  always #50 clk=~clk;
  asic_top #(.MemoryVariant(0)) reference (
    .clk_i(clk),.rst_ni(rst_n),.btn_i(btn),.leds_o(r_led),.seg1_o(r_s1),.seg2_o(r_s2),
    .spi_sclk_i(sclk),.spi_mosi_i(mosi),.spi_cs_n_i(cs_n),.spi_miso_o(r_miso));
  physical_top gate (
    .clk_i(clk),.rst_ni(rst_n),.btn_i(btn),.leds_o(g_led),.seg1_o(g_s1),.seg2_o(g_s2),
    .spi_sclk_i(sclk),.spi_mosi_i(mosi),.spi_cs_n_i(cs_n),.spi_miso_o(g_miso));
  integer samples=0,active_cycles=0,fetch_changes=0,spi_frames=0,epochs=0;
  integer reset_checks=0,button_changes=0,n,e;
  reg [31:0] last_pc=0;
  task compare_all;
    begin
      samples=samples+1;
      if ((^{r_led,r_s1,r_s2,r_miso,g_led,g_s1,g_s2,g_miso}) === 1'bx)
        $fatal(1,"Unknown external output at sample %0d",samples);
      if ({r_led,r_s1,r_s2,r_miso} !== {g_led,g_s1,g_s2,g_miso})
        $fatal(1,"External output mismatch at sample %0d",samples);
    if ((1) && reference.core_rst_ni !== gate.core_rst_ni )
      $fatal(1, "Diagnostic mismatch core_rst_ni at sample %0d", samples);
    if ((1) && reference.rst_sync_ni !== gate.rst_sync_ni )
      $fatal(1, "Diagnostic mismatch rst_sync_ni at sample %0d", samples);
    if ((1) && reference.mem_boot_done !== gate.mem_boot_done )
      $fatal(1, "Diagnostic mismatch mem_boot_done at sample %0d", samples);
    if ((1) && reference.instr_addr[0] !== gate.\instr_addr[0] )
      $fatal(1, "Diagnostic mismatch instr_addr[0] at sample %0d", samples);
    if ((1) && reference.instr_addr[1] !== gate.\instr_addr[1] )
      $fatal(1, "Diagnostic mismatch instr_addr[1] at sample %0d", samples);
    if ((1) && reference.instr_addr[2] !== gate.\instr_addr[2] )
      $fatal(1, "Diagnostic mismatch instr_addr[2] at sample %0d", samples);
    if ((1) && reference.instr_addr[3] !== gate.\instr_addr[3] )
      $fatal(1, "Diagnostic mismatch instr_addr[3] at sample %0d", samples);
    if ((1) && reference.instr_addr[4] !== gate.\instr_addr[4] )
      $fatal(1, "Diagnostic mismatch instr_addr[4] at sample %0d", samples);
    if ((1) && reference.instr_addr[5] !== gate.\instr_addr[5] )
      $fatal(1, "Diagnostic mismatch instr_addr[5] at sample %0d", samples);
    if ((1) && reference.instr_addr[6] !== gate.\instr_addr[6] )
      $fatal(1, "Diagnostic mismatch instr_addr[6] at sample %0d", samples);
    if ((1) && reference.instr_addr[7] !== gate.\instr_addr[7] )
      $fatal(1, "Diagnostic mismatch instr_addr[7] at sample %0d", samples);
    if ((1) && reference.instr_addr[8] !== gate.\instr_addr[8] )
      $fatal(1, "Diagnostic mismatch instr_addr[8] at sample %0d", samples);
    if ((1) && reference.instr_addr[9] !== gate.\instr_addr[9] )
      $fatal(1, "Diagnostic mismatch instr_addr[9] at sample %0d", samples);
    if ((1) && reference.instr_addr[10] !== gate.\instr_addr[10] )
      $fatal(1, "Diagnostic mismatch instr_addr[10] at sample %0d", samples);
    if ((1) && reference.instr_addr[11] !== gate.\instr_addr[11] )
      $fatal(1, "Diagnostic mismatch instr_addr[11] at sample %0d", samples);
    if ((1) && reference.instr_addr[12] !== gate.\instr_addr[12] )
      $fatal(1, "Diagnostic mismatch instr_addr[12] at sample %0d", samples);
    if ((1) && reference.instr_addr[13] !== gate.\instr_addr[13] )
      $fatal(1, "Diagnostic mismatch instr_addr[13] at sample %0d", samples);
    if ((1) && reference.instr_addr[14] !== gate.\instr_addr[14] )
      $fatal(1, "Diagnostic mismatch instr_addr[14] at sample %0d", samples);
    if ((1) && reference.instr_addr[15] !== gate.\instr_addr[15] )
      $fatal(1, "Diagnostic mismatch instr_addr[15] at sample %0d", samples);
    if ((1) && reference.instr_addr[16] !== gate.\instr_addr[16] )
      $fatal(1, "Diagnostic mismatch instr_addr[16] at sample %0d", samples);
    if ((1) && reference.instr_addr[17] !== gate.\instr_addr[17] )
      $fatal(1, "Diagnostic mismatch instr_addr[17] at sample %0d", samples);
    if ((1) && reference.instr_addr[18] !== gate.\instr_addr[18] )
      $fatal(1, "Diagnostic mismatch instr_addr[18] at sample %0d", samples);
    if ((1) && reference.instr_addr[19] !== gate.\instr_addr[19] )
      $fatal(1, "Diagnostic mismatch instr_addr[19] at sample %0d", samples);
    if ((1) && reference.instr_addr[20] !== gate.\instr_addr[20] )
      $fatal(1, "Diagnostic mismatch instr_addr[20] at sample %0d", samples);
    if ((1) && reference.instr_addr[21] !== gate.\instr_addr[21] )
      $fatal(1, "Diagnostic mismatch instr_addr[21] at sample %0d", samples);
    if ((1) && reference.instr_addr[22] !== gate.\instr_addr[22] )
      $fatal(1, "Diagnostic mismatch instr_addr[22] at sample %0d", samples);
    if ((1) && reference.instr_addr[23] !== gate.\instr_addr[23] )
      $fatal(1, "Diagnostic mismatch instr_addr[23] at sample %0d", samples);
    if ((1) && reference.instr_addr[24] !== gate.\instr_addr[24] )
      $fatal(1, "Diagnostic mismatch instr_addr[24] at sample %0d", samples);
    if ((1) && reference.instr_addr[25] !== gate.\instr_addr[25] )
      $fatal(1, "Diagnostic mismatch instr_addr[25] at sample %0d", samples);
    if ((1) && reference.instr_addr[26] !== gate.\instr_addr[26] )
      $fatal(1, "Diagnostic mismatch instr_addr[26] at sample %0d", samples);
    if ((1) && reference.instr_addr[27] !== gate.\instr_addr[27] )
      $fatal(1, "Diagnostic mismatch instr_addr[27] at sample %0d", samples);
    if ((1) && reference.instr_addr[28] !== gate.\instr_addr[28] )
      $fatal(1, "Diagnostic mismatch instr_addr[28] at sample %0d", samples);
    if ((1) && reference.instr_addr[29] !== gate.\instr_addr[29] )
      $fatal(1, "Diagnostic mismatch instr_addr[29] at sample %0d", samples);
    if ((1) && reference.instr_addr[30] !== gate.\instr_addr[30] )
      $fatal(1, "Diagnostic mismatch instr_addr[30] at sample %0d", samples);
    if ((1) && reference.instr_addr[31] !== gate.\instr_addr[31] )
      $fatal(1, "Diagnostic mismatch instr_addr[31] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[0] !== gate.\u_soc.u_periph.cycles_q[0] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[0] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[1] !== gate.\u_soc.u_periph.cycles_q[1] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[1] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[2] !== gate.\u_soc.u_periph.cycles_q[2] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[2] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[3] !== gate.\u_soc.u_periph.cycles_q[3] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[3] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[4] !== gate.\u_soc.u_periph.cycles_q[4] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[4] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[5] !== gate.\u_soc.u_periph.cycles_q[5] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[5] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[6] !== gate.\u_soc.u_periph.cycles_q[6] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[6] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[7] !== gate.\u_soc.u_periph.cycles_q[7] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[7] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[8] !== gate.\u_soc.u_periph.cycles_q[8] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[8] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[9] !== gate.\u_soc.u_periph.cycles_q[9] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[9] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[10] !== gate.\u_soc.u_periph.cycles_q[10] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[10] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[11] !== gate.\u_soc.u_periph.cycles_q[11] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[11] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[12] !== gate.\u_soc.u_periph.cycles_q[12] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[12] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[13] !== gate.\u_soc.u_periph.cycles_q[13] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[13] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[14] !== gate.\u_soc.u_periph.cycles_q[14] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[14] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[15] !== gate.\u_soc.u_periph.cycles_q[15] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[15] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[16] !== gate.\u_soc.u_periph.cycles_q[16] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[16] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[17] !== gate.\u_soc.u_periph.cycles_q[17] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[17] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[18] !== gate.\u_soc.u_periph.cycles_q[18] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[18] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[19] !== gate.\u_soc.u_periph.cycles_q[19] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[19] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[20] !== gate.\u_soc.u_periph.cycles_q[20] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[20] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[21] !== gate.\u_soc.u_periph.cycles_q[21] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[21] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[22] !== gate.\u_soc.u_periph.cycles_q[22] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[22] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[23] !== gate.\u_soc.u_periph.cycles_q[23] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[23] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[24] !== gate.\u_soc.u_periph.cycles_q[24] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[24] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[25] !== gate.\u_soc.u_periph.cycles_q[25] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[25] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[26] !== gate.\u_soc.u_periph.cycles_q[26] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[26] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[27] !== gate.\u_soc.u_periph.cycles_q[27] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[27] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[28] !== gate.\u_soc.u_periph.cycles_q[28] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[28] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[29] !== gate.\u_soc.u_periph.cycles_q[29] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[29] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[30] !== gate.\u_soc.u_periph.cycles_q[30] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[30] at sample %0d", samples);
    if ((1) && reference.u_soc.u_periph.cycles_q[31] !== gate.\u_soc.u_periph.cycles_q[31] )
      $fatal(1, "Diagnostic mismatch u_soc.u_periph.cycles_q[31] at sample %0d", samples);
    if ((1) && reference.u_soc.u_spi.price_q[0] !== gate.\u_soc.u_spi.price_q[0] )
      $fatal(1, "Diagnostic mismatch u_soc.u_spi.price_q[0] at sample %0d", samples);
    if ((1) && reference.u_soc.u_spi.price_q[1] !== gate.\u_soc.u_spi.price_q[1] )
      $fatal(1, "Diagnostic mismatch u_soc.u_spi.price_q[1] at sample %0d", samples);
    if ((1) && reference.u_soc.u_spi.price_q[2] !== gate.\u_soc.u_spi.price_q[2] )
      $fatal(1, "Diagnostic mismatch u_soc.u_spi.price_q[2] at sample %0d", samples);
    if ((1) && reference.u_soc.u_spi.price_q[3] !== gate.\u_soc.u_spi.price_q[3] )
      $fatal(1, "Diagnostic mismatch u_soc.u_spi.price_q[3] at sample %0d", samples);
    if ((1) && reference.u_soc.u_spi.price_q[4] !== gate.\u_soc.u_spi.price_q[4] )
      $fatal(1, "Diagnostic mismatch u_soc.u_spi.price_q[4] at sample %0d", samples);
    if ((1) && reference.u_soc.u_spi.price_q[5] !== gate.\u_soc.u_spi.price_q[5] )
      $fatal(1, "Diagnostic mismatch u_soc.u_spi.price_q[5] at sample %0d", samples);
    if ((1) && reference.u_soc.u_spi.price_q[6] !== gate.\u_soc.u_spi.price_q[6] )
      $fatal(1, "Diagnostic mismatch u_soc.u_spi.price_q[6] at sample %0d", samples);
    if ((1) && reference.u_soc.u_spi.price_q[7] !== gate.\u_soc.u_spi.price_q[7] )
      $fatal(1, "Diagnostic mismatch u_soc.u_spi.price_q[7] at sample %0d", samples);
    if ((1) && reference.u_soc.u_spi.new_price_q !== gate.\u_soc.u_spi.new_price_q )
      $fatal(1, "Diagnostic mismatch u_soc.u_spi.new_price_q at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[2] !== gate.\instr_rdata[2] )
      $fatal(1, "Diagnostic mismatch instr_rdata[2] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[3] !== gate.\instr_rdata[3] )
      $fatal(1, "Diagnostic mismatch instr_rdata[3] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[4] !== gate.\instr_rdata[4] )
      $fatal(1, "Diagnostic mismatch instr_rdata[4] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[5] !== gate.\instr_rdata[5] )
      $fatal(1, "Diagnostic mismatch instr_rdata[5] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[6] !== gate.\instr_rdata[6] )
      $fatal(1, "Diagnostic mismatch instr_rdata[6] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[7] !== gate.\instr_rdata[7] )
      $fatal(1, "Diagnostic mismatch instr_rdata[7] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[8] !== gate.\instr_rdata[8] )
      $fatal(1, "Diagnostic mismatch instr_rdata[8] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[9] !== gate.\instr_rdata[9] )
      $fatal(1, "Diagnostic mismatch instr_rdata[9] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[10] !== gate.\instr_rdata[10] )
      $fatal(1, "Diagnostic mismatch instr_rdata[10] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[11] !== gate.\instr_rdata[11] )
      $fatal(1, "Diagnostic mismatch instr_rdata[11] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[12] !== gate.\instr_rdata[12] )
      $fatal(1, "Diagnostic mismatch instr_rdata[12] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[13] !== gate.\instr_rdata[13] )
      $fatal(1, "Diagnostic mismatch instr_rdata[13] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[14] !== gate.\instr_rdata[14] )
      $fatal(1, "Diagnostic mismatch instr_rdata[14] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[15] !== gate.\instr_rdata[15] )
      $fatal(1, "Diagnostic mismatch instr_rdata[15] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[16] !== gate.\instr_rdata[16] )
      $fatal(1, "Diagnostic mismatch instr_rdata[16] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[17] !== gate.\instr_rdata[17] )
      $fatal(1, "Diagnostic mismatch instr_rdata[17] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[18] !== gate.\instr_rdata[18] )
      $fatal(1, "Diagnostic mismatch instr_rdata[18] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[19] !== gate.\instr_rdata[19] )
      $fatal(1, "Diagnostic mismatch instr_rdata[19] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[20] !== gate.\instr_rdata[20] )
      $fatal(1, "Diagnostic mismatch instr_rdata[20] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[21] !== gate.\instr_rdata[21] )
      $fatal(1, "Diagnostic mismatch instr_rdata[21] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[22] !== gate.\instr_rdata[22] )
      $fatal(1, "Diagnostic mismatch instr_rdata[22] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[23] !== gate.\instr_rdata[23] )
      $fatal(1, "Diagnostic mismatch instr_rdata[23] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[24] !== gate.\instr_rdata[24] )
      $fatal(1, "Diagnostic mismatch instr_rdata[24] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[25] !== gate.\instr_rdata[25] )
      $fatal(1, "Diagnostic mismatch instr_rdata[25] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[26] !== gate.\instr_rdata[26] )
      $fatal(1, "Diagnostic mismatch instr_rdata[26] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[27] !== gate.\instr_rdata[27] )
      $fatal(1, "Diagnostic mismatch instr_rdata[27] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[28] !== gate.\instr_rdata[28] )
      $fatal(1, "Diagnostic mismatch instr_rdata[28] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[29] !== gate.\instr_rdata[29] )
      $fatal(1, "Diagnostic mismatch instr_rdata[29] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[30] !== gate.\instr_rdata[30] )
      $fatal(1, "Diagnostic mismatch instr_rdata[30] at sample %0d", samples);
    if ((reference.core_rst_ni === 1'b1) && reference.instr_rdata[31] !== gate.\instr_rdata[31] )
      $fatal(1, "Diagnostic mismatch instr_rdata[31] at sample %0d", samples);
    end
  endtask
  always @(posedge clk) begin
    #1;
    if(enabled) begin
      compare_all;
      if(reference.core_rst_ni === 1'b1) begin
        active_cycles=active_cycles+1;
        if(reference.instr_addr !== last_pc) fetch_changes=fetch_changes+1;
        last_pc=reference.instr_addr;
      end
    end
  end
  task assert_reset;
    begin
      #17; rst_n=0; #1;
      compare_all;
      if(reference.core_rst_ni !== 0 || gate.core_rst_ni !== 0 ||
         reference.u_soc.u_periph.cycles_q !== 0)
        $fatal(1,"Asynchronous reset did not clear reset/counter");
      reset_checks=reset_checks+1;
    end
  endtask
  task spi_byte(input [7:0] value);
    integer bit_index;
    begin
      @(negedge clk); cs_n=0;
      repeat(10) @(negedge clk);
      for(bit_index=7;bit_index>=0;bit_index=bit_index-1) begin
        mosi=value[bit_index];
        repeat(10) @(negedge clk); sclk=1;
        repeat(10) @(negedge clk); sclk=0;
      end
      repeat(10) @(negedge clk); cs_n=1;
      repeat(10) @(negedge clk);
      if(reference.u_soc.u_spi.price_q !== value ||
         reference.u_soc.u_spi.new_price_q !== 1)
        $fatal(1,"SPI reference receive failed");
      spi_frames=spi_frames+1;
    end
  endtask
  initial begin
    #7; rst_n=0; #1; enabled=1;
    repeat(6) @(negedge clk); rst_n=1;
    // Interrupt B's actual loader; A has already booted at this point.
    repeat(70) @(negedge clk);
    if(0 == 1 && reference.mem_boot_done !== 0)
      $fatal(1,"B left its initial loading interval too early");
    assert_reset;
    for(e=0;e<2;e=e+1) begin
      repeat(6) @(negedge clk); rst_n=1;
      repeat(220) @(negedge clk);
      if(reference.core_rst_ni !== 1 || reference.mem_boot_done !== 1)
        $fatal(1,"Boot did not complete");
      spi_byte(8'h3c); spi_byte(8'ha5);
      for(n=0;n<10000;n=n+1) begin
        @(negedge clk);
        if(n%113 == 0) begin btn=(n/113+e)%16; button_changes=button_changes+1; end
      end
      if(r_led !== 4'hf || reference.u_soc.u_periph.cycles_q < 10000)
        $fatal(1,"Production startup or timer did not progress");
      epochs=epochs+1;
      if(e==0) assert_reset;
    end
    @(negedge clk);
    if(active_cycles < 20000 || fetch_changes < 1000 || spi_frames != 4 || reset_checks != 2)
      $fatal(1,"Insufficient startup coverage");
    $display("PASS physical_startup variant=%0d epochs=%0d samples=%0d active_cycles=%0d fetch_changes=%0d spi_frames=%0d reset_checks=%0d button_changes=%0d",
             0,epochs,samples,active_cycles,fetch_changes,spi_frames,reset_checks,button_changes);
    $finish;
  end
  initial begin #3000000; $fatal(1,"Physical startup timeout"); end
endmodule
