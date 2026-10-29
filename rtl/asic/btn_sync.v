// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
//
// Authors:
// - Nicolás Villegas <navillegas@miuandes.cl>

// Two sampling stages per active-high button. No debounce is added.
module btn_sync (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire [3:0] btn_i,
  output wire [3:0] btn_o
);
  (* async_reg = "true" *) reg [3:0] meta_q;
  (* async_reg = "true" *) reg [3:0] sync_q;
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      meta_q <= 4'b0;
      sync_q <= 4'b0;
    end else begin
      meta_q <= btn_i;
      sync_q <= meta_q;
    end
  end
  assign btn_o = sync_q;
endmodule
