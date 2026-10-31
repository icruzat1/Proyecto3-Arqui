# Síntesis y trazabilidad de los finales

Síntesis fuente: stage7_trace_ref_a/b. Finales seleccionados: stage13_final_traceable_a y stage12_electrical_route_b. Las áreas siguientes son de síntesis, antes del relleno y de los ECO.

| Medida | A | B |
|---|---:|---:|
| Área síntesis (µm²) | 208256.4288 | 828235.7888 |
| Celdas síntesis | 6598 | 23107 |
| Celdas contador, incluidas 32 FF | 110 | 110 |
| Área contador (µm²) | 3894.2848 | 3894.2848 |
| Fracción del contador | 1.869947 % | 0.470190 % |

El contador se identifica por 32 Q cycles_q y el cono combinacional exclusivo que alimenta sus D; excluye reloj, reset y mux MMIO. RF y ALU usan nombres jerárquicos cotejados con masters y coordenadas del ODB final.

## Celdas más usadas

**A**

| Celda | Cantidad |
|---|---:|
| dffrnq_1 | 1323 |
| mux2_2 | 1182 |
| nand2_1 | 800 |
| aoi22_1 | 784 |
| clkinv_1 | 287 |

**B**

| Celda | Cantidad |
|---|---:|
| mux2_2 | 5984 |
| dffq_1 | 4608 |
| nand2_1 | 1758 |
| mux4_1 | 1479 |
| oai21_1 | 1108 |

FF: estado de CPU, RF, contador y memoria. Mux: lecturas y retención/escritura. NAND/AOI/OAI: decodificación y lógica optimizada. Inversores: polaridades. B tiene más registros y muxes por su memoria FF.

## Módulos y área

En A, comparando CPU completa y memoria, domina CPU: 105.593,5104 frente a 83.132,224 µm². El SoC que incluye CPU, periféricos y SPI suma 124.057,3376 µm². En B domina memoria: 703.109,3888 µm². RF ocupa 71.587,6672 µm² y ALU 10.152,8 µm² en ambas síntesis. No sumar padres e hijos.

regions.json incluye particiones directas sin doble conteo y áreas inclusivas. all_instances.json registra todas las instancias físicas con master, módulo o soporte físico y coordenadas. Las celdas de reloj, relleno y reparación se distinguen de la jerarquía RTL.

## Rutas críticas finales

A: u_mem.gen_a.u_memory._2219_/Q (instr_rdata[6]) → u_mem.gen_a.u_memory._2264_/D (ram_ff[0][11]). B: u_mem.genblk1.gen_b.u_memory._31352_/Q (instr_rdata[2]) → ..._29664_/D (mem_ff[52][18]). Son caminos desde instrucción, pasando por control/datos del procesador, hacia escritura de memoria; no se atribuyen automáticamente a la ALU.

Reportes completos max.rpt de max_ss_125C_4v50: evidence/gf180_delivery/critical_paths. A setup +46,597294 ns y hold/removal +0,130822 ns; B +22,614665 ns y +0,293077 ns.

## Capturas

**A**: [general](../evidence/layout_captures/stage13_final_traceable_a_blocks/overview.png), [ALU](../evidence/layout_captures/stage13_final_traceable_a_blocks/alu.png), [RF](../evidence/layout_captures/stage13_final_traceable_a_blocks/rf.png), [contador](../evidence/layout_captures/stage13_final_traceable_a_blocks/counter.png).

**B**: [general](../evidence/layout_captures/stage12_electrical_route_b_blocks/overview.png), [ALU](../evidence/layout_captures/stage12_electrical_route_b_blocks/alu.png), [RF](../evidence/layout_captures/stage12_electrical_route_b_blocks/rf.png), [contador](../evidence/layout_captures/stage12_electrical_route_b_blocks/counter.png).

