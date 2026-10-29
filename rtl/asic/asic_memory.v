// Copyright 2026 Universidad de los Andes.
// SPDX-License-Identifier: SHL-0.51
// Memory architecture is a compile-time choice, not a runtime multiplexer.
module asic_memory #(
  parameter integer MemoryVariant = 0
) (
  input  wire        clk_i,
  input  wire        rst_ni,
  output wire        boot_done_o,
  input  wire        a_req_i,
  input  wire [31:0] a_addr_i,
  output wire [31:0] a_rdata_o,
  input  wire        b_req_i,
  input  wire        b_we_i,
  input  wire [3:0]  b_be_i,
  input  wire [31:0] b_addr_i,
  input  wire [31:0] b_wdata_i,
  output wire [31:0] b_rdata_o
);
  generate
    if (MemoryVariant == 0) begin : gen_a
      memory_a u_memory (
        .clk_i(clk_i), .rst_ni(rst_ni), .boot_done_o(boot_done_o),
        .a_req_i(a_req_i), .a_addr_i(a_addr_i), .a_rdata_o(a_rdata_o),
        .b_req_i(b_req_i), .b_we_i(b_we_i), .b_be_i(b_be_i),
        .b_addr_i(b_addr_i), .b_wdata_i(b_wdata_i), .b_rdata_o(b_rdata_o)
      );
    end else if (MemoryVariant == 1) begin : gen_b
      memory_b u_memory (
        .clk_i(clk_i), .rst_ni(rst_ni), .boot_done_o(boot_done_o),
        .a_req_i(a_req_i), .a_addr_i(a_addr_i), .a_rdata_o(a_rdata_o),
        .b_req_i(b_req_i), .b_we_i(b_we_i), .b_be_i(b_be_i),
        .b_addr_i(b_addr_i), .b_wdata_i(b_wdata_i), .b_rdata_o(b_rdata_o)
      );
    end else begin : gen_invalid
      // An invalid configuration must fail elaboration/hierarchy checking.
      ASIC_MEMORY_VARIANT_MUST_BE_0_OR_1 invalid_configuration();
    end
  endgenerate
endmodule
