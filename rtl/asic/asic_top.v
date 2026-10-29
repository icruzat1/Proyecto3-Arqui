// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
//
// Authors:
// - Nicolás Villegas <navillegas@miuandes.cl>

// Logical macro terminals: no package pads or board polarity inversion.
// asic_memory is the stage-2 integration boundary. Stage-1 simulation
// explicitly supplies sim/asic_stage1/asic_memory.v; it is NOT ASIC storage.
module asic_top (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire [3:0] btn_i,
  output wire [3:0] leds_o,
  output wire [6:0] seg1_o,
  output wire [6:0] seg2_o,
  input  wire       spi_sclk_i,
  input  wire       spi_mosi_i,
  input  wire       spi_cs_n_i,
  output wire       spi_miso_o
);
  wire rst_sync_ni, core_rst_ni, mem_boot_done;
  wire [3:0] btn_sync;
  wire instr_req, data_req, data_we;
  wire [3:0] data_be;
  wire [31:0] instr_addr, instr_rdata;
  wire [31:0] data_addr, data_wdata, data_rdata;

  reset_ctrl u_reset (
    .clk_i(clk_i), .rst_ni(rst_ni), .mem_boot_done_i(mem_boot_done),
    .rst_sync_no(rst_sync_ni), .core_rst_no(core_rst_ni)
  );
  btn_sync u_buttons (
    .clk_i(clk_i), .rst_ni(rst_sync_ni), .btn_i(btn_i), .btn_o(btn_sync)
  );
  pochoco_soc u_soc (
    .clk_i(clk_i), .rst_ni(core_rst_ni), .btn_i(btn_sync),
    .leds_o(leds_o), .seg1_o(seg1_o), .seg2_o(seg2_o),
    .spi_sclk_i(spi_sclk_i), .spi_mosi_i(spi_mosi_i),
    .spi_cs_n_i(spi_cs_n_i), .spi_miso_o(spi_miso_o),
    .instr_req_o(instr_req), .instr_addr_o(instr_addr), .instr_rdata_i(instr_rdata),
    .ram_req_o(data_req), .ram_we_o(data_we), .ram_be_o(data_be),
    .ram_addr_o(data_addr), .ram_wdata_o(data_wdata), .ram_rdata_i(data_rdata)
  );
  asic_memory u_mem (
    .clk_i(clk_i), .rst_ni(rst_sync_ni), .boot_done_o(mem_boot_done),
    .a_req_i(instr_req), .a_addr_i(instr_addr), .a_rdata_o(instr_rdata),
    .b_req_i(data_req), .b_we_i(data_we), .b_be_i(data_be),
    .b_addr_i(data_addr), .b_wdata_i(data_wdata), .b_rdata_o(data_rdata)
  );
endmodule
