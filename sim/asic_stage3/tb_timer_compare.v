`timescale 1ns/1ps
// Directed arithmetic regression for the actual Espino ALU used by BLT.
// Old firmware compares signed absolute counter/deadline values. The ASIC
// firmware compares (counter - start) modulo 2^32 with a duration < 2^31.
module tb_timer_compare;
  reg [3:0] op;
  reg [31:0] a,b;
  wire [31:0] result;
  wire cmp;
  espino_alu dut (.operator_i(op),.operand_a_i(a),.operand_b_i(b),
                 .result_o(result),.cmp_result_o(cmp));
  integer checks=0, old_failures=0;
  reg [31:0] start, duration, now, deadline, elapsed;
  reg old_wait, new_wait;
  task check_case;
    input [31:0] start_value;
    input [31:0] duration_value;
    input [31:0] delta;
    input expected_wait;
    input expected_old_wait;
    begin
      start=start_value; duration=duration_value;
      op=0; a=start; b=duration; #1; deadline=result;
      op=0; a=start; b=delta; #1; now=result;
      op=12; a=now; b=deadline; #1; old_wait=cmp;
      op=1; a=now; b=start; #1; elapsed=result;
      if(elapsed!==delta) $fatal(1,"Modulo subtraction is wrong");
      op=12; a=elapsed; b=duration; #1; new_wait=cmp;
      if(old_wait!==expected_old_wait || new_wait!==expected_wait)
        $fatal(1,"Unexpected compare start=%h duration=%d delta=%d old=%b new=%b",start,duration,delta,old_wait,new_wait);
      if(old_wait!==expected_wait) old_failures=old_failures+1;
      checks=checks+1;
      $display("CASE start=%h duration=%0d delta=%0d counter=%h deadline=%h old_wait=%b elapsed_wait=%b expected=%b",start,duration,delta,now,deadline,old_wait,new_wait,expected_wait);
    end
  endtask
  initial begin
    // Production duration: 3 seconds at 10 MHz. Compare before, at and after
    // the target using an ordinary origin and both 32-bit sign/wrap borders.
    check_case(32'h00000010,30000000,24,1,1);
    check_case(32'h00000010,30000000,29999999,1,1);
    check_case(32'h00000010,30000000,30000000,0,0);
    check_case(32'h00000010,30000000,30000024,0,0);
    // This case fails in the original absolute-deadline algorithm: now is
    // positive while the future deadline is interpreted as negative.
    check_case(32'h7fffffe0,30000000,24,1,0);
    check_case(32'h7fffffe0,30000000,48,1,1);
    check_case(32'h7fffffe0,30000000,29999999,1,1);
    check_case(32'h7fffffe0,30000000,30000000,0,0);
    check_case(32'h7fffffe0,30000000,30000024,0,0);
    check_case(32'hffffffe0,30000000,24,1,1);
    check_case(32'hffffffe0,30000000,48,1,1);
    check_case(32'hffffffe0,30000000,29999999,1,1);
    check_case(32'hffffffe0,30000000,30000000,0,0);
    check_case(32'hffffffe0,30000000,30000024,0,0);
    // Same boundary conditions with the accelerated 3000-tick profile.
    check_case(32'h7fffffe0,3000,24,1,0);
    check_case(32'h7fffffe0,3000,2999,1,1);
    check_case(32'h7fffffe0,3000,3000,0,0);
    check_case(32'hffffffe0,3000,24,1,1);
    check_case(32'hffffffe0,3000,2999,1,1);
    check_case(32'hffffffe0,3000,3000,0,0);
    if(checks!=20 || old_failures!=2) $fatal(1,"Missing directed coverage");
    $display("PASS timer_compare checks=%0d old_algorithm_failures=%0d corrected_algorithm_failures=0",checks,old_failures);
    $finish;
  end
endmodule
