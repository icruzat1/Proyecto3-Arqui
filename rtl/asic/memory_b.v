// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
// Original Pochoco memory author: Nicolas Villegas <navillegas@miuandes.cl>
// Proyecto 3: unified writable FF memory with sequential hardware loading.

module memory_b (
  input  wire        clk_i,
  input  wire        rst_ni,
  output reg         boot_done_o,
  input  wire        a_req_i,
  input  wire [31:0] a_addr_i,
  output reg  [31:0] a_rdata_o,
  input  wire        b_req_i,
  input  wire        b_we_i,
  input  wire [3:0]  b_be_i,
  input  wire [31:0] b_addr_i,
  input  wire [31:0] b_wdata_i,
  output reg  [31:0] b_rdata_o
);
  localparam [31:0] NOP = 32'h00000013;

  wire a_valid = (a_addr_i < 32'h00000240) && (a_addr_i[1:0] == 2'b00);
  wire b_valid = (b_addr_i < 32'h00000240) && (b_addr_i[1:0] == 2'b00);
  wire [7:0] a_word_index = a_addr_i[9:2];
  wire [7:0] b_word_index = b_addr_i[9:2];

  reg [31:0] mem_ff [0:143];
  reg [7:0] boot_index;
  wire [31:0] program_word;
  wire [31:0] boot_word = (boot_index < 8'd128) ? program_word : 32'b0;
  asic_program_rom u_boot_rom (
    .word_index_i(boot_index[6:0]), .word_o(program_word)
  );

  // The array has no reset and no file-based initialization. Its sole writer
  // loads one word per clock, then accepts CPU writes to ALL 144 words,
  // including program words. Runtime reads never bypass this array via ROM.
  always @(posedge clk_i) begin
    if (rst_ni) begin
      if (!boot_done_o) begin
        mem_ff[boot_index] <= boot_word;
      end else if (b_req_i && b_we_i && b_valid) begin
        if (b_be_i[0]) mem_ff[b_word_index][7:0]   <= b_wdata_i[7:0];
        if (b_be_i[1]) mem_ff[b_word_index][15:8]  <= b_wdata_i[15:8];
        if (b_be_i[2]) mem_ff[b_word_index][23:16] <= b_wdata_i[23:16];
        if (b_be_i[3]) mem_ff[b_word_index][31:24] <= b_wdata_i[31:24];
      end
    end
  end

  // Reset only control and read outputs. Resetting during load restarts at
  // word zero; resetting after execution restores the entire image again.
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      boot_index <= 8'd0;
      boot_done_o <= 1'b0;
      a_rdata_o <= NOP;
      b_rdata_o <= 32'b0;
    end else if (!boot_done_o) begin
      if (boot_index == 8'd143)
        boot_done_o <= 1'b1;
      else
        boot_index <= boot_index + 8'd1;
      a_rdata_o <= NOP;
      b_rdata_o <= 32'b0;
    end else begin
      // The 144th write and ready assertion share an edge. A registered core
      // release must follow ready, so no CPU request precedes the last write.
      if (a_req_i)
        a_rdata_o <= a_valid ? mem_ff[a_word_index] : NOP;
      b_rdata_o <= b_valid ? mem_ff[b_word_index] : 32'b0;
      // Both ports sample pre-write data on collisions (read-first).
    end
  end
endmodule
