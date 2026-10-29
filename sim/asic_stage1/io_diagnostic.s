# Test-only firmware. Does not replace or recalibrate game.s.
# Exercise the unchanged CPU and the real SoC memory/MMIO decoder.
    lui  x2, 0x80000
    addi x1, x0, 0xA5
    sw   x1, 0(x2)
    addi x1, x0, 10
    sw   x1, 4(x2)
    lw   x3, 8(x2)
    lw   x4, 12(x2)
    sw   x3, 512(x0)
    sw   x4, 516(x0)
    lui  x5, 0x80010
    addi x6, x0, 0x96
    sw   x6, 8(x5)
wait_price:
    lw   x7, 0(x5)
    andi x7, x7, 1
    beq  x7, x0, wait_price
    lw   x8, 4(x5)
    sw   x8, 520(x0)
    lw   x9, 0(x5)
    sw   x9, 524(x0)
hang:
    jal  x0, hang
