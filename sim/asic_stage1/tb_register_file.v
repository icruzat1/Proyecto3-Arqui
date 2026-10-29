`timescale 1ns/1ps

module tb_register_file;
  reg clk = 1'b0;
  always #5 clk = ~clk;

  reg rst_n = 1'b1;
  reg [3:0] raddr_a = 4'd0, raddr_b = 4'd0, waddr = 4'd0;
  reg [31:0] wdata = 32'b0;
  reg we = 1'b0;
  wire [31:0] rdata_a, rdata_b;
  espino_register_file dut (
    .clk_i(clk), .rst_ni(rst_n),
    .raddr_a_i(raddr_a), .rdata_a_o(rdata_a),
    .raddr_b_i(raddr_b), .rdata_b_o(rdata_b),
    .waddr_i(waddr), .wdata_i(wdata), .we_i(we)
  );

  // The runner may rename the two legacy modules in a build-only copy.
  // No changes to the baseline are required for this differential test.
`ifdef COMPARE_ICE40
  wire [31:0] legacy_a, legacy_b;
  espino_register_file_legacy legacy (
    .clk_i(clk), .rst_ni(rst_n),
    .raddr_a_i(raddr_a), .rdata_a_o(legacy_a),
    .raddr_b_i(raddr_b), .rdata_b_o(legacy_b),
    .waddr_i(waddr), .wdata_i(wdata), .we_i(we)
  );
`endif

  reg [31:0] expected_regs [0:15];
  reg compare_legacy = 1'b1;
  reg [31:0] prng = 32'h4a31_9d27;
  reg [15:0] reads_a_seen = 0, reads_b_seen = 0, writes_seen = 0;
  integer cycles_checked = 0, legacy_cycles_checked = 0;
  integer collision_a = 0, collision_b = 0, zero_writes = 0;
  integer i, j;

  task clear_model;
    integer k;
    begin
      for (k = 0; k < 16; k = k + 1)
        expected_regs[k] = 0;
    end
  endtask

  // Check both the absence of an asynchronous read and one-edge latency.
  // Expectations are sampled before applying the write to the scoreboard.
  task step;
    input [3:0] read_a, read_b, write_addr;
    input [31:0] write_data;
    input write_enable;
    reg [31:0] held_a, held_b, expected_a, expected_b;
    begin
      @(negedge clk);
      held_a = rdata_a;
      held_b = rdata_b;
      raddr_a = read_a;
      raddr_b = read_b;
      waddr = write_addr;
      wdata = write_data;
      we = write_enable;
      #1;
      if (rdata_a !== held_a || rdata_b !== held_b)
        $fatal(1, "RF outputs changed without a rising clock edge");
      @(posedge clk);
      expected_a = expected_regs[read_a];
      expected_b = expected_regs[read_b];
      if (write_enable && write_addr != 0)
        expected_regs[write_addr] = write_data;
      reads_a_seen[read_a] = 1'b1;
      reads_b_seen[read_b] = 1'b1;
      if (write_enable) begin
        writes_seen[write_addr] = 1'b1;
        if (write_addr == read_a) collision_a = collision_a + 1;
        if (write_addr == read_b) collision_b = collision_b + 1;
        if (write_addr == 0) zero_writes = zero_writes + 1;
      end
      #1;
      if (rdata_a !== expected_a || rdata_b !== expected_b)
        $fatal(1, "RF mismatch cycle=%0d A(x%0d)=%08x expected=%08x B(x%0d)=%08x expected=%08x",
               cycles_checked, read_a, rdata_a, expected_a,
               read_b, rdata_b, expected_b);
`ifdef COMPARE_ICE40
      if (compare_legacy) begin
        if (rdata_a !== legacy_a || rdata_b !== legacy_b)
          $fatal(1, "RF legacy mismatch cycle=%0d A=%08x/%08x B=%08x/%08x",
                 cycles_checked, rdata_a, legacy_a, rdata_b, legacy_b);
        legacy_cycles_checked = legacy_cycles_checked + 1;
      end
`endif
      cycles_checked = cycles_checked + 1;
    end
  endtask

  task random_steps;
    input integer count;
    integer k;
    begin
      for (k = 0; k < count; k = k + 1) begin
        // Explicit xorshift seed/recurrence is reproducible across simulators.
        prng = prng ^ (prng << 13);
        prng = prng ^ (prng >> 17);
        prng = prng ^ (prng << 5);
        step(prng[3:0], prng[7:4], prng[11:8],
             prng ^ 32'ha5c3_79e1, prng[12]);
      end
    end
  endtask

  initial begin
    clear_model;
    #2 rst_n = 1'b0;
    #1;
    if (rdata_a !== 0 || rdata_b !== 0)
      $fatal(1, "RF reset must clear outputs before any clock edge");
    @(negedge clk);
    rst_n = 1'b1;

    for (i = 0; i < 16; i = i + 1)
      step(i, 15-i, 0, 0, 0);
    for (i = 1; i < 16; i = i + 1)
      step(i, i, i, 32'hcafe_0000 + i, 1);
    for (i = 0; i < 16; i = i + 1)
      for (j = 0; j < 16; j = j + 1)
        step(i, j, 0, 0, 0);
    step(0, 0, 0, 32'hffff_ffff, 1);
    step(0, 0, 0, 32'ha5a5_a5a5, 1);
    for (i = 1; i < 16; i = i + 1) begin
      step(i, i, i, 32'h0123_4500 + i, 1);
      step(i, i, i, 32'hfedc_ba00 + i, 1);
      step(i, i, 0, 0, 0);
    end
    random_steps(1024);

    // Reset is an intentional ASIC addition: the legacy RF ignores rst_ni.
    // Assert it between clock edges, while both outputs contain nonzero data.
    step(1, 2, 1, 32'hdead_beef, 1);
    step(1, 1, 0, 0, 0);
    compare_legacy = 1'b0;
    #1 rst_n = 1'b0;
    clear_model;
    #1;
    if (rdata_a !== 0 || rdata_b !== 0)
      $fatal(1, "RF warm reset failed to clear outputs asynchronously");
    waddr = 4'd1;
    wdata = 32'hffff_ffff;
    we = 1'b1;
    repeat (2) begin
      @(posedge clk);
      #1;
      if (rdata_a !== 0 || rdata_b !== 0)
        $fatal(1, "RF outputs must remain zero during reset");
    end
    @(negedge clk);
    we = 1'b0;
    rst_n = 1'b1;
    for (i = 0; i < 16; i = i + 1)
      step(i, 15-i, 0, 0, 0);

    // Explicitly rewrite all legacy words to synchronize state after reset.
    for (i = 1; i < 16; i = i + 1)
      step(0, 0, i, 0, 1);
    compare_legacy = 1'b1;
    random_steps(512);

    if (reads_a_seen !== 16'hffff || reads_b_seen !== 16'hffff ||
        writes_seen !== 16'hffff || collision_a == 0 || collision_b == 0 ||
        zero_writes == 0)
      $fatal(1, "RF coverage incomplete");
    $display("PASS register_file cycles=%0d legacy_cycles=%0d collisions_a=%0d collisions_b=%0d x0_writes=%0d",
             cycles_checked, legacy_cycles_checked, collision_a, collision_b, zero_writes);
    $finish;
  end

  initial begin
    #100000;
    $fatal(1, "RF test timed out");
  end
endmodule
