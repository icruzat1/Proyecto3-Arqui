#!/usr/bin/env python3
import re
import sys

OP = {
    "lui":  "0110111",
    "addi": "0010011",
    "andi": "0010011",
    "add":  "0110011",
    "sub":  "0110011",
    "lw":   "0000011",
    "sw":   "0100011",
    "beq":  "1100011",
    "bne":  "1100011",
    "blt":  "1100011",
    "jal":  "1101111",
}

F3 = {
    "addi": "000",
    "andi": "111",
    "add":  "000",
    "lw":   "010",
    "sw":   "010",
    "beq":  "000",
    "bne":  "001",
    "blt":  "100",
}

def bits(n, w):
    if n < 0:
        n = (1 << w) + n
    return format(n & ((1 << w) - 1), f"0{w}b")

def reg(tok):
    tok = tok.lower().rstrip(",")
    if tok == "zero":
        tok = "x0"
    if not tok.startswith("x"):
        raise ValueError(f"registro raro: {tok}")
    n = int(tok[1:])
    if n < 0 or n > 15:
        raise ValueError(f"RV32E solo x0-x15: {tok}")
    return n

def imm(tok):
    tok = tok.rstrip(",")
    return int(tok, 0)

def strip_comment(line):
    if "//" in line:
        line = line[: line.index("//")]
    if "#" in line:
        line = line[: line.index("#")]
    return line.strip()

def tokenize(s):
    s = s.replace(",", " ")
    return [t for t in s.split() if t]

def parse_mem(tok):
    m = re.match(r"(-?(?:0x[0-9a-fA-F]+|\d+))\((x\d+)\)", tok)
    if not m:
        raise ValueError(f"memoria rara: {tok}")
    return imm(m.group(1)), m.group(2)

def encode(mnemonic, args, pc, labels):
    op = mnemonic.lower()

    def lab_or_imm(tok):
        t = tok.rstrip(",")
        if t in labels:
            return labels[t] - pc
        return imm(t)

    if op == "lui":
        rd, im = reg(args[0]), imm(args[1])
        return bits(im, 20) + bits(rd, 5) + OP[op]

    if op in ("addi", "andi"):
        rd, rs1, im = reg(args[0]), reg(args[1]), imm(args[2])
        return bits(im, 12) + bits(rs1, 5) + F3[op] + bits(rd, 5) + OP[op]

    if op == "add":
        rd, rs1, rs2 = reg(args[0]), reg(args[1]), reg(args[2])
        return "0000000" + bits(rs2, 5) + bits(rs1, 5) + "000" + bits(rd, 5) + OP[op]

    # //
    if op == "sub":
        rd, rs1, rs2 = reg(args[0]), reg(args[1]), reg(args[2])
        return "0100000" + bits(rs2, 5) + bits(rs1, 5) + "000" + bits(rd, 5) + "0110011"

    if op == "blt":
        rs1, rs2 = reg(args[0]), reg(args[1])
        off = lab_or_imm(args[2])
        if off % 2:
            raise ValueError("branch no alineado")
        im = bits(off, 13)
        return im[0] + im[2:8] + bits(rs2, 5) + bits(rs1, 5) + "100" + im[8:12] + im[1] + "1100011"
    # //

    if op == "lw":
        rd = reg(args[0])
        off, rs1 = parse_mem(args[1])
        return bits(off, 12) + bits(reg(rs1), 5) + F3[op] + bits(rd, 5) + OP[op]

    if op == "sw":
        rs2 = reg(args[0])
        off, rs1 = parse_mem(args[1])
        im = bits(off, 12)
        return im[:7] + bits(rs2, 5) + bits(reg(rs1), 5) + F3[op] + im[7:] + OP[op]

    if op in ("beq", "bne"):
        rs1, rs2 = reg(args[0]), reg(args[1])
        off = lab_or_imm(args[2])
        if off % 2:
            raise ValueError("branch no alineado")
        im = bits(off, 13)
        return im[0] + im[2:8] + bits(rs2, 5) + bits(rs1, 5) + F3[op] + im[8:12] + im[1] + OP[op]

    if op == "jal":
        rd = reg(args[0])
        off = lab_or_imm(args[1])
        if off % 2:
            raise ValueError("jal no alineado")
        im = bits(off, 21)
        return im[0] + im[10:20] + im[9] + im[1:9] + bits(rd, 5) + OP[op]

    raise ValueError(f"instruccion no soportada: {op}")

def assemble(src):
    raw = []
    for lineno, line in enumerate(src.splitlines(), 1):
        line = strip_comment(line)
        if not line:
            continue
        if line.startswith("."):
            continue
        raw.append((lineno, line))

    labels = {}
    insts = []
    pc = 0
    for lineno, line in raw:
        while True:
            m = re.match(r"([A-Za-z_][\w]*):\s*(.*)$", line)
            if not m:
                break
            labels[m.group(1)] = pc
            line = m.group(2).strip()
        if not line:
            continue
        toks = tokenize(line)
        insts.append((lineno, pc, toks[0], toks[1:]))
        pc += 4

    out = []
    for lineno, pc, mnem, args in insts:
        try:
            word = int(encode(mnem, args, pc, labels), 2)
        except Exception as e:
            raise SystemExit(f"linea {lineno}: {e}")
        out.append(f"{word:08x}")
    return out

def main():
    if len(sys.argv) != 3:
        print("uso: python assemble.py entrada.s salida.hex")
        sys.exit(1)
    src = open(sys.argv[1], encoding="utf-8").read()
    hexlines = assemble(src)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write("\n".join(hexlines) + "\n")
    print(f"{len(hexlines)} instrucciones -> {sys.argv[2]}")

if __name__ == "__main__":
    main()