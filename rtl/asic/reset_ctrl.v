// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
//
// Authors:
// - Nicolás Villegas <navillegas@miuandes.cl>

// External reset asserts asynchronously; each release is clocked.
// mem_boot_done_i must be synchronous to clk_i and stay high until reset.
module reset_ctrl (
  input  wire clk_i,
  input  wire rst_ni,
  input  wire mem_boot_done_i,
  output wire rst_sync_no,
  output reg  core_rst_no
);
  (* async_reg = "true" *) reg [1:0] release_q;
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) release_q <= 2'b00;
    else         release_q <= {release_q[0], 1'b1};
  end
  assign rst_sync_no = release_q[1];

  // The loader uses rst_sync_no, never core_rst_no: no circular wait.
  always @(posedge clk_i or negedge rst_sync_no) begin
    if (!rst_sync_no) core_rst_no <= 1'b0;
    else             core_rst_no <= mem_boot_done_i;
  end
endmodule
