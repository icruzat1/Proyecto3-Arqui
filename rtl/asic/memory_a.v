// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
// Original Pochoco memory author: Nicolas Villegas <navillegas@miuandes.cl>
// Proyecto 3: generated combinational ROM plus a 16-word standard-cell RAM.

module memory_a (
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

  // Check the complete byte address before using the truncated word index.
  // The LSU already aligns requests; byte selection travels in b_be_i.
  wire a_rom_valid = (a_addr_i[31:9] == 23'b0) && (a_addr_i[1:0] == 2'b00);
  wire b_rom_valid = (b_addr_i[31:9] == 23'b0) && (b_addr_i[1:0] == 2'b00);
  wire b_ram_valid = (b_addr_i >= 32'h00000200) &&
                     (b_addr_i < 32'h00000240) && (b_addr_i[1:0] == 2'b00);
  wire [3:0] b_ram_index = b_addr_i[5:2];
  wire [31:0] instr_rom_word, data_rom_word;

  asic_program_rom u_instr_rom (
    .word_index_i(a_addr_i[8:2]), .word_o(instr_rom_word)
  );
  asic_program_rom u_data_rom (
    .word_index_i(b_addr_i[8:2]), .word_o(data_rom_word)
  );

  reg [31:0] ram_ff [0:15];
  integer index;
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      boot_done_o <= 1'b0;
      a_rdata_o <= NOP;
      b_rdata_o <= 32'b0;
      for (index = 0; index < 16; index = index + 1)
        ram_ff[index] <= 32'b0;
    end else begin
      // A requires no serial program load. Announce availability on a clock
      // edge, after reset has already cleared all data words.
      boot_done_o <= 1'b1;
      if (!boot_done_o) begin
        a_rdata_o <= NOP;
        b_rdata_o <= 32'b0;
      end else begin
        // The ROM itself is combinational; this output register preserves
        // the instruction-port latency and enable of the original SoC.
        if (a_req_i)
          a_rdata_o <= a_rom_valid ? instr_rom_word : NOP;

        // Preserve the unconditional, synchronous data-port read. Reading
        // code returns ROM contents; writes there are intentionally ignored.
        if (b_rom_valid)      b_rdata_o <= data_rom_word;
        else if (b_ram_valid) b_rdata_o <= ram_ff[b_ram_index];
        else                  b_rdata_o <= 32'b0;

        // Nonblocking assignments make a simultaneous RAM read/write
        // read-first: this cycle exposes the previous value of the word.
        if (b_req_i && b_we_i && b_ram_valid) begin
          if (b_be_i[0]) ram_ff[b_ram_index][7:0]   <= b_wdata_i[7:0];
          if (b_be_i[1]) ram_ff[b_ram_index][15:8]  <= b_wdata_i[15:8];
          if (b_be_i[2]) ram_ff[b_ram_index][23:16] <= b_wdata_i[23:16];
          if (b_be_i[3]) ram_ff[b_ram_index][31:24] <= b_wdata_i[31:24];
        end
      end
    end
  end
endmodule
