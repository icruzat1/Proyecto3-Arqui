`timescale 1ns/1ps
// Interface-level memory tests. Expected contents come from the independent
// assembler hex image and scoreboards, never from DUT internal storage.
module tb_memories;
  localparam [31:0] NOP = 32'h00000013;
  reg clk = 0, rst_n = 1;
  always #5 clk = ~clk;
  reg a_req = 0, b_req = 0, b_we = 0;
  reg [31:0] a_addr = 0, b_addr = 0, b_wdata = 0;
  reg [3:0] b_be = 0;
  wire ready_a, ready_b;
  wire [31:0] ai, ad, bi, bd;

  memory_a dut_a (
    .clk_i(clk), .rst_ni(rst_n), .boot_done_o(ready_a),
    .a_req_i(a_req), .a_addr_i(a_addr), .a_rdata_o(ai),
    .b_req_i(b_req), .b_we_i(b_we), .b_be_i(b_be),
    .b_addr_i(b_addr), .b_wdata_i(b_wdata), .b_rdata_o(ad)
  );
  memory_b dut_b (
    .clk_i(clk), .rst_ni(rst_n), .boot_done_o(ready_b),
    .a_req_i(a_req), .a_addr_i(a_addr), .a_rdata_o(bi),
    .b_req_i(b_req), .b_we_i(b_we), .b_be_i(b_be),
    .b_addr_i(b_addr), .b_wdata_i(b_wdata), .b_rdata_o(bd)
  );

  reg [31:0] image [0:127];
  reg [31:0] model_a [0:143];
  reg [31:0] model_b [0:143];
  reg [2047:0] image_path;
  reg [31:0] expected_ai = NOP, expected_bi = NOP;
  reg [31:0] expected_ad = 0, expected_bd = 0;
  reg [127:0] a_instruction_words = 0;
  reg [143:0] b_instruction_words = 0, data_read_words = 0, b_written_words = 0;
  reg [15:0] a_written_words = 0, byte_masks = 0;
  integer cycles_checked = 0, boot_edges_checked = 0;
  integer completed_boots = 0, resets_checked = 0;
  integer read_first_a = 0, read_first_b = 0;
  integer invalid_accesses = 0, request_disabled_writes = 0;
  integer instruction_holds = 0, unrequested_data_reads = 0;
  integer i, mask;
  reg [31:0] pattern;

  function valid_word;
    input [31:0] addr;
    begin valid_word = (addr[1:0] == 2'b00) && (addr < 32'd576); end
  endfunction
  function [31:0] read_a_instruction;
    input [31:0] addr;
    begin
      if (addr[1:0] == 2'b00 && addr < 32'd512)
        read_a_instruction = model_a[addr >> 2];
      else read_a_instruction = NOP;
    end
  endfunction
  function [31:0] read_b_instruction;
    input [31:0] addr;
    begin
      if (valid_word(addr)) read_b_instruction = model_b[addr >> 2];
      else read_b_instruction = NOP;
    end
  endfunction
  function [31:0] read_a_data;
    input [31:0] addr;
    begin
      if (valid_word(addr)) read_a_data = model_a[addr >> 2];
      else read_a_data = 0;
    end
  endfunction
  function [31:0] read_b_data;
    input [31:0] addr;
    begin
      if (valid_word(addr)) read_b_data = model_b[addr >> 2];
      else read_b_data = 0;
    end
  endfunction

  task initialize_models;
    integer index;
    begin
      for (index = 0; index < 144; index = index + 1) begin
        model_a[index] = index < 128 ? image[index] : 32'b0;
        model_b[index] = index < 128 ? image[index] : 32'b0;
      end
    end
  endtask

  // All normal-mode expected reads are computed before applying a write,
  // independently expressing read-first on both instruction and data ports.
  task step;
    input instruction_request;
    input [31:0] instruction_address;
    input data_request, write_enable;
    input [31:0] data_address;
    input [3:0] byte_enable;
    input [31:0] write_data;
    reg [31:0] old_ai, old_ad, old_bi, old_bd;
    integer index, lane;
    begin
      @(negedge clk);
      if (ready_a !== 1 || ready_b !== 1)
        $fatal(1, "Normal-mode test started before both memories ready");
      old_ai = ai; old_ad = ad; old_bi = bi; old_bd = bd;
      a_req = instruction_request;
      a_addr = instruction_address;
      b_req = data_request;
      b_we = write_enable;
      b_addr = data_address;
      b_be = byte_enable;
      b_wdata = write_data;
      #1;
      if ({ai,ad,bi,bd} !== {old_ai,old_ad,old_bi,old_bd})
        $fatal(1, "Memory outputs changed without a rising clock edge");

      if (instruction_request) begin
        expected_ai = read_a_instruction(instruction_address);
        expected_bi = read_b_instruction(instruction_address);
        if (instruction_address[1:0] == 0 && instruction_address < 512)
          a_instruction_words[instruction_address >> 2] = 1;
        if (valid_word(instruction_address))
          b_instruction_words[instruction_address >> 2] = 1;
      end else instruction_holds = instruction_holds + 1;
      expected_ad = read_a_data(data_address);
      expected_bd = read_b_data(data_address);
      if (!data_request) unrequested_data_reads = unrequested_data_reads + 1;
      if (valid_word(data_address)) data_read_words[data_address >> 2] = 1;
      else invalid_accesses = invalid_accesses + 1;

      if (write_enable && !data_request)
        request_disabled_writes = request_disabled_writes + 1;
      if (data_request && write_enable && valid_word(data_address)) begin
        index = data_address >> 2;
        byte_masks[byte_enable] = 1;
        if (byte_enable != 0) begin
          b_written_words[index] = 1;
          if (index >= 128) a_written_words[index-128] = 1;
          if (instruction_request && instruction_address == data_address) begin
            read_first_b = read_first_b + 1;
            if (index >= 128) read_first_a = read_first_a + 1;
          end
        end
        for (lane = 0; lane < 4; lane = lane + 1) begin
          if (byte_enable[lane]) begin
            model_b[index][8*lane +: 8] = write_data[8*lane +: 8];
            if (index >= 128)
              model_a[index][8*lane +: 8] = write_data[8*lane +: 8];
          end
        end
      end
      @(posedge clk); #1;
      if (ready_a !== 1 || ready_b !== 1)
        $fatal(1, "Availability dropped during normal access");
      if (ai !== expected_ai || ad !== expected_ad || bi !== expected_bi || bd !== expected_bd)
        $fatal(1, "Memory mismatch cycle=%0d a_addr=%08x b_addr=%08x req/we/be=%b/%b/%h A(i,d)=%08x,%08x expected=%08x,%08x B(i,d)=%08x,%08x expected=%08x,%08x",
               cycles_checked, a_addr, b_addr, b_req, b_we, b_be,
               ai,ad,expected_ai,expected_ad,bi,bd,expected_bi,expected_bd);
      cycles_checked = cycles_checked + 1;
    end
  endtask

  // Assert between edges while presenting a valid, hostile RAM write.
  // Every memory word is later checked after boot to detect reset corruption.
  task assert_reset;
    integer k;
    begin
      @(negedge clk);
      a_req = 1; a_addr = 0;
      b_req = 1; b_we = 1; b_addr = 32'd512;
      b_be = 4'hf; b_wdata = 32'hbad0_cafe;
      #2 rst_n = 0;
      #1;
      if ({ready_a,ready_b} !== 2'b00 ||
          {ai,ad,bi,bd} !== {NOP,32'b0,NOP,32'b0})
        $fatal(1, "Asynchronous memory reset did not clear outputs/readiness");
      for (k = 0; k < 3; k = k + 1) begin
        @(posedge clk); #1;
        if ({ready_a,ready_b} !== 2'b00 ||
            {ai,ad,bi,bd} !== {NOP,32'b0,NOP,32'b0})
          $fatal(1, "CPU accesses escaped asserted memory reset");
      end
      initialize_models;
      expected_ai = NOP; expected_bi = NOP;
      expected_ad = 0; expected_bd = 0;
      resets_checked = resets_checked + 1;
    end
  endtask

  task release_and_boot;
    input integer edges;
    integer k;
    begin
      @(negedge clk);
      rst_n = 1;
      // Writes to program word zero are ignored by A's ROM and must never
      // take priority over B's loader, including its final write cycle.
      a_req = 1; a_addr = 32'd512;
      b_req = 1; b_we = 1; b_addr = 0;
      b_be = 4'hf; b_wdata = 32'hdead_beef;
      for (k = 1; k <= edges; k = k + 1) begin
        @(posedge clk); #1;
        if (ready_a !== 1 || ready_b !== (k == 144))
          $fatal(1, "Boot availability mismatch at edge %0d: A=%b B=%b", k, ready_a, ready_b);
        if (ai !== NOP || bi !== NOP || bd !== 0)
          $fatal(1, "Instruction/data read escaped B boot at edge %0d", k);
        if (ad !== (k == 1 ? 32'b0 : image[0]))
          $fatal(1, "A ROM read during B boot mismatch at edge %0d: got=%h expected=%h", k, ad, k == 1 ? 32'b0 : image[0]);
        boot_edges_checked = boot_edges_checked + 1;
      end
      if (edges == 144) begin
        completed_boots = completed_boots + 1;
        expected_ai = NOP; expected_bi = NOP;
        expected_ad = image[0]; expected_bd = 0;
      end
    end
  endtask

  task scan_all_words;
    integer index;
    begin
      for (index = 0; index < 144; index = index + 1)
        step(1, index*4, 0, 0, index*4, 0, 0);
    end
  endtask

  task invalid_access;
    input [31:0] addr;
    begin
      step(1, addr, 1, 1, addr, 4'hf, 32'h1357_9bdf);
      step(1, addr, 0, 0, addr, 0, 0);
    end
  endtask

  initial begin
    if (!$value$plusargs("MEM_HEX=%s", image_path))
      $fatal(1, "Provide +MEM_HEX with the independently assembled, 128-word padded image");
    for (i = 0; i < 128; i = i + 1) image[i] = 32'bx;
    $readmemh(image_path, image);
    for (i = 0; i < 128; i = i + 1)
      if ((^image[i]) === 1'bx) $fatal(1, "Missing/undefined image word %0d", i);

    assert_reset;
    release_and_boot(17);
    assert_reset;
    release_and_boot(143);
    assert_reset;
    release_and_boot(144);
    scan_all_words;

    // Mask zero and disabled req/we must preserve storage. Port B reads must
    // still advance every cycle, while the instruction result holds.
    for (i = 0; i < 144; i = i + 1) begin
      step(0, 32'hffff_fffc, 0, 1, i*4, 4'hf, 32'hffff_ffff);
      step(0, 32'hffff_fffc, 1, 0, i*4, 4'hf, 32'habab_abab);
      step(1, i*4, 0, 0, i*4, 0, 0);
    end

    // Every B word is reprogrammed, including all instruction words and NOP
    // reserve. A must keep its ROM unchanged while allowing its 16 RAM words.
    for (i = 0; i < 144; i = i + 1) begin
      pattern = 32'h5a39_d6e8 ^ (i * 32'h0101_0101);
      step(1, i*4, 1, 1, i*4, 4'hf, pattern);
      step(1, i*4, 0, 0, i*4, 0, 0);
    end

    // Exhaust every lane-enable combination at every word. The read and
    // write use the same address to exercise the old-data collision result.
    for (i = 0; i < 144; i = i + 1) begin
      for (mask = 0; mask < 16; mask = mask + 1) begin
        pattern = 32'hcafe_09d3 ^ (i * 32'h0101_0101) ^ (mask * 32'h6d2b_79f5);
        step(1, i*4, 1, 1, i*4, mask, pattern);
        step(1, i*4, 0, 0, i*4, 0, 0);
      end
    end

    // Boundary words 0,127,128,143 were covered above. Invalid accesses may
    // not alias a low address merely because the low index bits match.
    invalid_access(32'h0000_0001);
    invalid_access(32'h0000_0002);
    invalid_access(32'h0000_0003);
    invalid_access(32'h0000_01fd);
    invalid_access(32'h0000_01fe);
    invalid_access(32'h0000_01ff);
    invalid_access(32'h0000_0201);
    invalid_access(32'h0000_0202);
    invalid_access(32'h0000_0203);
    invalid_access(32'h0000_023d);
    invalid_access(32'h0000_023e);
    invalid_access(32'h0000_023f);
    invalid_access(32'h0000_0240);
    invalid_access(32'h0000_0244);
    invalid_access(32'h0001_0000);
    invalid_access(32'h0001_0200);
    invalid_access(32'h8000_0000);
    invalid_access(32'h8000_0200);
    invalid_access(32'hffff_fffc);
    invalid_access(32'hffff_ffff);
    scan_all_words;

    // A warm reset must clear all data and rebuild all B code, including
    // the final word. Interrupt that rebuilding once more before completing.
    assert_reset;
    release_and_boot(71);
    assert_reset;
    release_and_boot(144);
    scan_all_words;

    if (a_instruction_words !== {128{1'b1}} ||
        b_instruction_words !== {144{1'b1}} || data_read_words !== {144{1'b1}} ||
        b_written_words !== {144{1'b1}} || a_written_words !== 16'hffff ||
        byte_masks !== 16'hffff || completed_boots != 2 || resets_checked != 5 ||
        read_first_a == 0 || read_first_b == 0 || invalid_accesses != 40 ||
        request_disabled_writes != 144 || instruction_holds != 288 || unrequested_data_reads == 0)
      $fatal(1, "Memory coverage incomplete");
    $display("PASS memories cycles=%0d boot_edges=%0d complete_boots=%0d resets=%0d words=144 masks=16 read_first_A=%0d read_first_B=%0d invalid_accesses=%0d req_disabled_writes=%0d instruction_holds=%0d unrequested_data_reads=%0d",
             cycles_checked,boot_edges_checked,completed_boots,resets_checked,
             read_first_a,read_first_b,invalid_accesses,request_disabled_writes,
             instruction_holds,unrequested_data_reads);
    $finish;
  end
  initial begin
    #1000000;
    $fatal(1, "Memory tests timed out");
  end
endmodule
