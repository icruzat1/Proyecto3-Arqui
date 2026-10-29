// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
// Original author: Nicolás Villegas <navillegas@miuandes.cl>
// Proyecto 3: standard-cell register file with explicit ASIC reset.

module espino_register_file (
  input  wire        clk_i,
  input  wire        rst_ni,
  input  wire [3:0]  raddr_a_i,
  output reg  [31:0] rdata_a_o,
  input  wire [3:0]  raddr_b_i,
  output reg  [31:0] rdata_b_o,
  input  wire [3:0]  waddr_i,
  input  wire [31:0] wdata_i,
  input  wire        we_i
);
  // x0 is a constant, so only x1..x15 require storage.
  reg [31:0] regs_q [1:15];
  integer index;

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      for (index = 1; index < 16; index = index + 1)
        regs_q[index] <= 32'b0;
      rdata_a_o <= 32'b0;
      rdata_b_o <= 32'b0;
    end else begin
      // Preserve the original synchronous, continuously enabled read ports.
      // Nonblocking assignments make same-address read/write read-first:
      // the old word appears on this edge; the new word on the next read.
      rdata_a_o <= (raddr_a_i == 4'd0) ? 32'b0 : regs_q[raddr_a_i];
      rdata_b_o <= (raddr_b_i == 4'd0) ? 32'b0 : regs_q[raddr_b_i];
      if (we_i && (waddr_i != 4'd0))
        regs_q[waddr_i] <= wdata_i;
    end
  end
endmodule
