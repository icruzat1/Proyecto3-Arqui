`timescale 1ns/1ps
// TEST FIXTURE ONLY. Never include this source in an ASIC synthesis list.
// Legacy-sized storage preserves the original read timing. A delayed ready
// signal exercises the future A/B loader handshake; it does not implement B.
module asic_memory (
  input wire clk_i, rst_ni,
  output reg boot_done_o,
  input wire a_req_i,
  input wire [31:0] a_addr_i,
  output reg [31:0] a_rdata_o,
  input wire b_req_i, b_we_i,
  input wire [3:0] b_be_i,
  input wire [31:0] b_addr_i, b_wdata_i,
  output reg [31:0] b_rdata_o
);
`ifndef ASIC_STAGE1_SIM
  ASIC_STAGE1_MEMORY_IS_FOR_SIMULATION_ONLY invalid_build();
`endif
  reg [31:0] mem [0:511];
  integer n, boot_cycles, boot_count;
  reg [2047:0] image_path;
  initial begin
    boot_cycles = 5;
    if ($value$plusargs("BOOT_CYCLES=%d", boot_cycles)) begin end
    if (boot_cycles < 0) $fatal(1, "Negative boot delay");
    if (!$value$plusargs("MEM_HEX=%s", image_path))
      $fatal(1, "MEM_HEX must select an explicit simulation image");
    for (n = 0; n < 512; n = n + 1) mem[n] = 32'h00000013;
    $readmemh(image_path, mem); // Runner supplies a padded 512-word file.
  end
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      boot_count <= 0;
      boot_done_o <= 1'b0;
    end else if (!boot_done_o) begin
      if (boot_count >= boot_cycles) boot_done_o <= 1'b1;
      else boot_count <= boot_count + 1;
    end
  end
  always @(posedge clk_i) begin
    if (a_req_i) a_rdata_o <= mem[a_addr_i[10:2]];
    if (b_req_i && b_we_i) begin
      if (b_be_i[0]) mem[b_addr_i[10:2]][7:0]   <= b_wdata_i[7:0];
      if (b_be_i[1]) mem[b_addr_i[10:2]][15:8]  <= b_wdata_i[15:8];
      if (b_be_i[2]) mem[b_addr_i[10:2]][23:16] <= b_wdata_i[23:16];
      if (b_be_i[3]) mem[b_addr_i[10:2]][31:24] <= b_wdata_i[31:24];
    end
    b_rdata_o <= mem[b_addr_i[10:2]];
  end
endmodule
