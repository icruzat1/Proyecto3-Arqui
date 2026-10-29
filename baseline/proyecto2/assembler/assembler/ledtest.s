.section .text
.global _start
_start:
    lui  x2, 0x80000
    addi x2, x2, 4
    addi x1, x0, 15
loop:
    sw   x1, 0(x2)
    jal  x0, loop
    