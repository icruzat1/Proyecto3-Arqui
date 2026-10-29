.section .text
.global _start

# x2  = 0x80000000   display
# +4  LED            +8 botones           +12 timer
# x10 rondas correctas
# x11 semilla
# x12 suma de decimas
# x13 mascara LED
# x14 boton
# x15 decimas de la ronda / promedio

_start:
    lui  x2, 0x80000
    addi x2, x2, 4
    addi x1, x0, 15
    sw   x1, 0(x2)
    addi x2, x2, -4
    addi x10, x0, 0
    addi x11, x0, 1
    addi x12, x0, 0

round:
    addi x5, x0, 10
    beq  x10, x5, done

    addi x1, x0, 15
    sw   x1, 4(x2)

    lw   x7, 12(x2)
    lui  x9, 0x4786
    addi x9, x9, 0x7FF
    addi x9, x9, 0xC1
    add  x8, x7, x9
wait3:
    addi x11, x11, 1
    lw   x7, 12(x2)
    blt  x7, x8, wait3

    andi x4, x11, 3
    addi x13, x0, 1
    beq  x4, x0, show_led
    addi x13, x0, 2
    addi x5, x0, 1
    beq  x4, x5, show_led
    addi x13, x0, 4
    addi x5, x0, 2
    beq  x4, x5, show_led
    addi x13, x0, 8

show_led:
    sw   x13, 4(x2)

    lw   x7, 12(x2)

wait_press:
    addi x11, x11, 1
    lw   x14, 8(x2)
    beq  x14, x0, wait_press
    bne  x14, x13, wrong

    lw   x8, 12(x2)
    sub  x8, x8, x7
    lui  x9, 0x262
    addi x9, x9, 0x5A0
    addi x15, x0, 0
div_l:
    blt  x8, x9, div_d
    sub  x8, x8, x9
    addi x15, x15, 1
    jal  x0, div_l
div_d:
    addi x5, x0, 100
    blt  x15, x5, nocap
    addi x15, x0, 99
nocap:
    add  x12, x12, x15

    addi x3, x0, 0
    addi x4, x15, 0
    addi x5, x0, 10
bcd1:
    blt  x4, x5, bcd1d
    sub  x4, x4, x5
    addi x3, x3, 1
    jal  x0, bcd1
bcd1d:
    add  x1, x3, x3
    add  x1, x1, x1
    add  x1, x1, x1
    add  x1, x1, x1
    add  x1, x1, x4
    sw   x1, 0(x2)

    addi x10, x10, 1

wait_rel:
    lw   x14, 8(x2)
    bne  x14, x0, wait_rel
    jal  x0, round

wrong:
    addi x1, x0, 0
    sw   x1, 4(x2)
    addi x1, x0, 0xEE
    sw   x1, 0(x2)
wait_rel_b:
    lw   x14, 8(x2)
    bne  x14, x0, wait_rel_b
    jal  x0, round

done:
    addi x15, x0, 0
    addi x8, x12, 0
    addi x9, x0, 10
avg:
    blt  x8, x9, avg_d
    sub  x8, x8, x9
    addi x15, x15, 1
    jal  x0, avg
avg_d:
    addi x3, x0, 0
    addi x4, x15, 0
    addi x5, x0, 10
bcd2:
    blt  x4, x5, bcd2d
    sub  x4, x4, x5
    addi x3, x3, 1
    jal  x0, bcd2
bcd2d:
    add  x1, x3, x3
    add  x1, x1, x1
    add  x1, x1, x1
    add  x1, x1, x1
    add  x1, x1, x4
    sw   x1, 0(x2)
hang:
    jal  x0, hang
    