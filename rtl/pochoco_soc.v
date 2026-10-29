// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
//
// Authors:
// - Nicolás Villegas <navillegas@miuandes.cl>

// ASIC adaptation: explicit reset and external synchronous memory interface.
// Core, peripheral map and SPI logic retain the Proyecto 2 implementation.
module pochoco_soc (
  input  wire        clk_i,
  input  wire        rst_ni,
  input  wire [3:0]  btn_i,
  output wire [3:0]  leds_o,
  output wire [6:0]  seg1_o,
  output wire [6:0]  seg2_o,
  input  wire        spi_sclk_i,
  input  wire        spi_mosi_i,
  input  wire        spi_cs_n_i,
  output wire        spi_miso_o,
  output wire        instr_req_o,
  output wire [31:0] instr_addr_o,
  input  wire [31:0] instr_rdata_i,
  output wire        ram_req_o,
  output wire        ram_we_o,
  output wire [3:0]  ram_be_o,
  output wire [31:0] ram_addr_o,
  output wire [31:0] ram_wdata_o,
  input  wire [31:0] ram_rdata_i
);
  wire core_instr_req;
  wire data_req, data_we;
  wire [3:0] data_be;
  wire [31:0] data_addr, data_wdata, data_rdata;

  espino_core #(.BootAddr(32'h0000_0000)) u_core (
    .clk_i(clk_i), .rst_ni(rst_ni),
    .instr_req_o(core_instr_req), .instr_addr_o(instr_addr_o),
    .instr_rdata_i(instr_rdata_i),
    .data_req_o(data_req), .data_we_o(data_we), .data_be_o(data_be),
    .data_addr_o(data_addr), .data_wdata_o(data_wdata), .data_rdata_i(data_rdata)
  );
  // The legacy IF stage may assert its request during reset. Suppress all
  // bus side effects until the registered core reset has been released.
  assign instr_req_o = core_instr_req & rst_ni;
  wire is_mmio = data_addr[31];
  wire per_sel = is_mmio & ~data_addr[16];
  wire spi_sel = is_mmio &  data_addr[16];
  wire per_req = data_req & per_sel & rst_ni;
  wire spi_req = data_req & spi_sel & rst_ni;
  assign ram_req_o   = data_req & ~is_mmio & rst_ni;
  assign ram_we_o    = data_we & rst_ni;
  assign ram_be_o    = data_be;
  assign ram_addr_o  = data_addr;
  assign ram_wdata_o = data_wdata;

  wire [31:0] per_rdata, spi_rdata;
  reg rd_is_per, rd_is_spi;
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      rd_is_per <= 1'b0;
      rd_is_spi <= 1'b0;
    end else if (data_req & ~data_we) begin
      rd_is_per <= per_sel;
      rd_is_spi <= spi_sel;
    end
  end
  assign data_rdata = rd_is_per ? per_rdata :
                     rd_is_spi ? spi_rdata : ram_rdata_i;

  pochoco_periph u_periph (
    .clk_i(clk_i), .rst_ni(rst_ni), .sel_i(per_sel), .req_i(per_req),
    .we_i(data_we), .addr_i(data_addr[7:0]), .wdata_i(data_wdata),
    .rdata_o(per_rdata), .leds_o(leds_o), .btn_i(btn_i),
    .seg1_o(seg1_o), .seg2_o(seg2_o)
  );
  pochoco_spi_slave u_spi (
    .clk_i(clk_i), .rst_ni(rst_ni), .sel_i(spi_sel), .req_i(spi_req),
    .we_i(data_we), .addr_i(data_addr[7:0]), .wdata_i(data_wdata),
    .rdata_o(spi_rdata), .spi_sclk_i(spi_sclk_i), .spi_mosi_i(spi_mosi_i),
    .spi_cs_n_i(spi_cs_n_i), .spi_miso_o(spi_miso_o)
  );
endmodule
