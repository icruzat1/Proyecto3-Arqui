`timescale 1ns/1ps
// Section 3.7 profile: shorten only the three-second wait. A tenth remains
// 1,000,000 clocks at 10 MHz. Short reactions therefore display 00.
module tb_game_wait_only;
  parameter integer MemoryVariant=0;
  reg clk=0, rst_n=1;
  reg [3:0] buttons=0;
  wire [3:0] leds;
  wire [6:0] seg1,seg2;
  wire miso;
  asic_top #(.MemoryVariant(MemoryVariant)) dut (
    .clk_i(clk),.rst_ni(rst_n),.btn_i(buttons),.leds_o(leds),
    .seg1_o(seg1),.seg2_o(seg2),.spi_sclk_i(1'b0),
    .spi_mosi_i(1'b0),.spi_cs_n_i(1'b1),.spi_miso_o(miso)
  );
`ifdef WITH_NETLIST
  wire [3:0] syn_leds;
  wire [6:0] syn_seg1,syn_seg2;
  wire syn_miso;
  netlist_top syn (
    .clk_i(clk),.rst_ni(rst_n),.btn_i(buttons),.leds_o(syn_leds),
    .seg1_o(syn_seg1),.seg2_o(syn_seg2),.spi_sclk_i(1'b0),
    .spi_mosi_i(1'b0),.spi_cs_n_i(1'b1),.spi_miso_o(syn_miso)
  );
`endif
  always #50 clk=~clk;
  integer cycle=0, compared=0, requests=0, stores=0;
  integer phase=0, attempts=0, correct=0, wrong=0, held_checks=0;
  integer timer_reads=0, wait_reads=0, active_cycle=0;
  integer first_correct_cycle=0, second_correct_cycle=0, wrong_cycle=0;
  integer first_round_cycles=0, second_round_cycles=0, wrong_round_cycles=0;
  integer ordinary_ram_accesses=0;
  reg waiting=0, expect_wrong=0;
  reg [31:0] wait_start=0, reaction_start=0, reaction_end=0, elapsed;
  integer trace=0;
  string trace_path;

  always @(posedge clk) begin
    cycle=cycle+1;
    if(dut.core_rst_ni) begin
      if(dut.data_req) ordinary_ram_accesses=ordinary_ram_accesses+1;
      if(dut.u_soc.per_req) begin
        requests=requests+1;
        if(trace) $fwrite(trace,"BUS,%0d,%0d,%h,%h,%h\n",cycle,dut.u_soc.data_we,dut.u_soc.data_addr,dut.u_soc.data_be,dut.u_soc.data_we ? dut.u_soc.data_wdata : 32'b0);
        if(!dut.u_soc.data_we && dut.u_soc.data_addr==32'h8000000c) begin
          if(phase==1) begin
            if(timer_reads==0) reaction_start=dut.u_soc.u_periph.cycles_q;
            else if(timer_reads==1) reaction_end=dut.u_soc.u_periph.cycles_q;
            else $fatal(1,"Too many timer reads during reaction");
            timer_reads=timer_reads+1;
          end else if(waiting) begin
            if(wait_reads==0) wait_start=dut.u_soc.u_periph.cycles_q;
            wait_reads=wait_reads+1;
          end
        end
        if(dut.u_soc.data_we) begin
          stores=stores+1;
          case(dut.u_soc.data_addr)
            32'h80000004: begin
              if(dut.u_soc.data_wdata[3:0]==15) begin
                if(correct>=2) $fatal(1,"Game advanced while last button held");
                phase=0; waiting=1; wait_reads=0;
              end else if(dut.u_soc.data_wdata[3:0]!=0) begin
                if(!waiting || wait_reads<2) $fatal(1,"LED lacks timed wait");
                elapsed=dut.u_soc.u_periph.cycles_q-wait_start;
                if(elapsed<3000 || elapsed>3160) $fatal(1,"Wrong shortened wait %0d",elapsed);
                if((dut.u_soc.data_wdata[3:0] & (dut.u_soc.data_wdata[3:0]-1))!=0)
                  $fatal(1,"Expected one active LED");
                waiting=0; phase=1; attempts=attempts+1; timer_reads=0; active_cycle=cycle;
                $display("EVENT cycle=%0d attempt=%0d active_led=%h wait_ticks=%0d",cycle,attempts,dut.u_soc.data_wdata[3:0],elapsed);
              end else if(!expect_wrong || phase!=1) $fatal(1,"Unexpected LED clear");
            end
            32'h80000000: begin
              if(dut.u_soc.data_wdata[7:0]==8'hee) begin
                if(!expect_wrong || phase!=1 || timer_reads!=1)
                  $fatal(1,"Unexpected error result");
                wrong=wrong+1; phase=3; wrong_cycle=cycle; wrong_round_cycles=cycle-active_cycle;
                if(dut.u_soc.u_core.u_rf.regs_q[10]!==correct || dut.u_soc.u_core.u_rf.regs_q[12]!==0)
                  $fatal(1,"Error changed correct count or sum");
                $display("EVENT cycle=%0d wrong=%0d correct=%0d result=EE round_cycles=%0d",cycle,wrong,correct,wrong_round_cycles);
              end else begin
                if(expect_wrong || phase!=1 || timer_reads!=2 || dut.u_soc.data_wdata[7:0]!=0)
                  $fatal(1,"Unexpected correct result");
                elapsed=reaction_end-reaction_start;
                if(elapsed>=1000000 || elapsed==0) $fatal(1,"Reaction is outside zero-tenth test interval");
                correct=correct+1; phase=2;
                if(correct==1) begin first_correct_cycle=cycle; first_round_cycles=cycle-active_cycle; end
                else if(correct==2) begin second_correct_cycle=cycle; second_round_cycles=cycle-active_cycle; end
                else $fatal(1,"Unexpected additional correct result");
                $display("EVENT cycle=%0d correct=%0d reaction_ticks=%0d divisor=1000000 result=00 round_cycles=%0d",cycle,correct,elapsed,cycle-active_cycle);
              end
            end
            default: $fatal(1,"Unexpected peripheral store");
          endcase
        end
      end
    end
  end

  always @(posedge clk) begin
    #2;
    if(cycle>1) begin
      if((^{leds,seg1,seg2,miso})===1'bx) $fatal(1,"Unknown logical output");
`ifdef WITH_NETLIST
      if({leds,seg1,seg2,miso} !== {syn_leds,syn_seg1,syn_seg2,syn_miso})
        $fatal(1,"Logical output mismatch cycle=%0d",cycle);
`endif
      compared=compared+1;
    end
    if(trace) $fwrite(trace,"IO,%0d,%0d,%h,%h,%h,%h,%h\n",cycle,rst_n,buttons,leds,seg1,seg2,miso);
  end

  task wait_phase;
    input integer target;
    integer count;
    begin
      count=0;
      while(phase!=target && count<10000) begin @(negedge clk); count=count+1; end
      if(phase!=target) $fatal(1,"Phase timeout wanted=%0d actual=%0d",target,phase);
    end
  endtask
  task held;
    input integer target;
    input [3:0] expected_led;
    input [6:0] expected_segment;
    integer n;
    begin
      for(n=0;n<200;n=n+1) begin
        @(negedge clk);
        if(phase!=target || leds!==expected_led || seg1!==expected_segment || seg2!==expected_segment)
          $fatal(1,"Held button advanced or changed the result");
        held_checks=held_checks+1;
      end
    end
  endtask
  task play_correct;
    input integer release_after;
    reg [3:0] mask;
    begin
      wait_phase(1); mask=leds;
      repeat(250) @(negedge clk);
      buttons=mask;
      wait_phase(2);
      held(2,mask,7'h3f);
      if(release_after) buttons=0;
    end
  endtask
  initial begin
    if($value$plusargs("TRACE=%s",trace_path)) begin
      trace=$fopen(trace_path,"w");
      if(!trace) $fatal(1,"Cannot create trace");
    end
    #7; rst_n=0;
    repeat(4) @(negedge clk);
    if(leds!==0 || seg1!==7'h3f || seg2!==7'h3f) $fatal(1,"Reset outputs wrong");
    rst_n=1;
    play_correct(1);
    wait_phase(1);
    repeat(250) @(negedge clk);
    expect_wrong=1;
    buttons=(leds==8) ? 1 : (leds<<1);
    wait_phase(3);
    held(3,0,7'h79);
    buttons=0; expect_wrong=0;
    play_correct(0);
    if(correct!=2 || wrong!=1 || attempts!=3 || held_checks!=600 || ordinary_ram_accesses!=0)
      $fatal(1,"Coverage incomplete");
    if(dut.u_soc.u_core.u_rf.regs_q[10]!==2 || dut.u_soc.u_core.u_rf.regs_q[12]!==0)
      $fatal(1,"Final correct count or sum wrong");
    if(first_correct_cycle>=wrong_cycle || wrong_cycle>=second_correct_cycle || first_round_cycles<=0 || second_round_cycles<=0)
      $fatal(1,"Incorrect event order");
    $display("PASS game_wait_only variant=%0d cycles=%0d compared=%0d correct=%0d wrong=%0d attempts=%0d held_checks=%0d requests=%0d stores=%0d ram_accesses=%0d first_correct=%0d wrong_cycle=%0d second_correct=%0d first_round_cycles=%0d wrong_round_cycles=%0d second_round_cycles=%0d",MemoryVariant,cycle,compared,correct,wrong,attempts,held_checks,requests,stores,ordinary_ram_accesses,first_correct_cycle,wrong_cycle,second_correct_cycle,first_round_cycles,wrong_round_cycles,second_round_cycles);
    if(trace) $fclose(trace);
    $finish;
  end
  initial begin repeat(40000) @(posedge clk); $fatal(1,"Wait-only watchdog"); end
endmodule
