`timescale 1ns/1ps
module tb_proyecto2_startup;
  reg clk = 1'b0;
  wire [3:0] leds;
  integer cycle;
  reg saw_startup_leds = 1'b0;
  game_top dut (
    .i_Clk(clk), .o_LED(leds), .i_Switch(4'b0000),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1)
  );
  always #20 clk = ~clk;
  initial begin
    #1;
    if (dut.u_pochoco.u_ram.mem[0] !== 32'h80000137)
      $fatal(1, "No se cargo la primera instruccion de game.hex");
    if (dut.u_pochoco.u_ram.mem[93] !== 32'h0000006f)
      $fatal(1, "No se cargo la ultima instruccion de game.hex");
    for (cycle = 0; cycle < 2000; cycle = cycle + 1) begin
      @(negedge clk);
      if (cycle < 14 && dut.u_pochoco.rst_ni !== 1'b0)
        $fatal(1, "Reset inicial inesperado");
      if (cycle >= 15 && dut.u_pochoco.rst_ni !== 1'b1)
        $fatal(1, "Reset no liberado");
      if (cycle >= 20 && (^dut.u_pochoco.instr_addr === 1'bx))
        $fatal(1, "Direccion de instrucciones indefinida tras reset");
      if (leds === 4'b1111) saw_startup_leds = 1'b1;
    end
    if (!saw_startup_leds) $fatal(1, "No se observo el encendido inicial de cuatro LED");
    if (dut.u_pochoco.u_periph.cycles_q !== 32'd1985)
      $fatal(1, "El contador de ciclos no progreso desde el reset");
    $display("PASS: game.hex cargado, reset liberado, PC definido, cuatro LED y contador activo en 2000 ciclos");
    $finish;
  end
endmodule
