> Finales posteriores: A stage13_final_traceable_a y B stage12_electrical_route_b pasan a100ns/40%. La tabla siguiente conserva los puntos originales y sus fallos; no fue reescrita como si esos puntos hubieran pasado. Ver Comparacion_Final_AB.md.

# Barridos medidos de período y utilización

RTL de producción y síntesis `deferred_flatten`. A100/60ns conserva margen adicional de optimización20ns; A40ns y los tres puntos B usan0ns, sin cambiar criterios de aceptación. No se atribuye toda diferencia de área exclusivamente al período. Cada período nuevo vuelve a sintetizar; cada utilización tiene una implementación física nueva. Ningún punto fallido se repara para forzar su aprobación. A final anterior y candidata RTL se conservan por separado.

| Variante | Período ns | Util. inicial % | Peor setup ns | Peor hold ns | Física | Eléctrica | Cierre estricto |
|---|---:|---:|---:|---:|---|---|---|
| A | 100 | 30 | 46.621023 | -0.087825 | PASS | PASS | FAIL |
| A | 40 | 40 | -6.946483 | -0.013482 | PASS | FAIL | FAIL |
| A | 60 | 40 | 13.115724 | -0.011749 | FAIL | PASS | FAIL |
| A | 100 | 40 | 46.597209 | -0.022720 | PASS | PASS | FAIL |
| A | 100 | 50 | 48.105940 | 0.173468 | PASS | PASS | PASS |
| B | 40 | 40 | -12.896305 | 0.292375 | PASS | FAIL | FAIL |
| B | 60 | 40 | -12.938067 | 0.289969 | PASS | FAIL | FAIL |
| B | 100 | 40 | 23.444650 | 0.277806 | PASS | FAIL | FAIL |

B100ns/40% tiene cierre académico aprobado con avisos eléctricos documentados; el FAIL eléctrico y estricto de esta tabla se conserva. No equivale a incumplimiento del objetivo temporal: B100 sí pasa setup/hold. Ver [decisión](Decision_Cierre_B.md) y [evidencia final](../evidence/gf180_final_b_academic/results.json). La aprobación no se extiende automáticamente a puntos con fallos de timing.

[Gráfico de utilización A](../evidence/gf180_sweeps/plots/utilizacion_A.png) · [SVG](../evidence/gf180_sweeps/plots/utilizacion_A.svg)

## WNS y TNS exigidos

TT corresponde a nom_tt_025C_5v00 y SS a max_ss_125C_4v50. También se comprueban las nueve esquinas: hold puede fallar en FF aunque TT y SS pasen. WNS se muestra recortado a cero cuando no hay violaciones; el margen positivo se muestra como slack en la tabla anterior.

| Corrida | Esquina | WNS setup | TNS setup | WNS hold | TNS hold |
|---|---|---:|---:|---:|---:|
| stage8_t100_u30_a | nom_tt_025C_5v00 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stage8_t100_u30_a | max_ss_125C_4v50 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stage8_t40_u40_nomargin_a | nom_tt_025C_5v00 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stage8_t40_u40_nomargin_a | max_ss_125C_4v50 | -6.946483 | -3928.434237 | 0.000000 | 0.000000 |
| stage8_t60_u40_a | nom_tt_025C_5v00 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stage8_t60_u40_a | max_ss_125C_4v50 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stage7_trace_physical_ref_a | nom_tt_025C_5v00 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stage7_trace_physical_ref_a | max_ss_125C_4v50 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stage8_t100_u50_a | nom_tt_025C_5v00 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stage8_t100_u50_a | max_ss_125C_4v50 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stage10_t40_u40_resumed_b | nom_tt_025C_5v00 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stage10_t40_u40_resumed_b | max_ss_125C_4v50 | -12.896305 | -38818.453692 | 0.000000 | 0.000000 |
| stage8_t60_u40_b | nom_tt_025C_5v00 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stage8_t60_u40_b | max_ss_125C_4v50 | -12.938067 | -18471.545058 | 0.000000 | 0.000000 |
| stage8_t100_u40_b | nom_tt_025C_5v00 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stage8_t100_u40_b | max_ss_125C_4v50 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

## Área y costo didáctico

| Corrida | Área stdcell µm² | Die mm² | Util. física % | FF secuenciales | Costo equivalente USD |
|---|---:|---:|---:|---:|---:|
| stage8_t100_u30_a | 294392 | 0.731937 | 42.54 | 1329 | 16834.55 |
| stage8_t40_u40_nomargin_a | 283727 | 0.553389 | 54.54 | 1329 | 12727.95 |
| stage8_t60_u40_a | 283839 | 0.553389 | 54.56 | 1329 | 12727.95 |
| stage7_trace_physical_ref_a | 284008 | 0.553389 | 54.59 | 1329 | 12727.95 |
| stage8_t100_u50_a | 280518 | 0.445850 | 67.64 | 1329 | 10254.55 |
| stage10_t40_u40_resumed_b | 1164950 | 2.135480 | 56.29 | 5433 | 49116.04 |
| stage8_t60_u40_b | 1164070 | 2.135480 | 56.24 | 5433 | 49116.04 |
| stage8_t100_u40_b | 1164940 | 2.135480 | 56.29 | 5433 | 49116.04 |

Área stdcell es la métrica post-PNR sin relleno; no es el área de síntesis. El costo usa área del die × 23.000 USD/mm²; no es una cotización y excluye rendimiento de fabricación, encapsulado, pruebas, máscaras y costos fijos.

La utilización se estudia en A, alternativa de menor área; ambas memorias tienen barrido de período. La tabla detallada por las nueve esquinas, controles separados y procedencia está en evidence/gf180_sweeps/summary.json.

Estado del lote: completo.

Frecuencia A observada con cierre estricto a40% en este barrido: ninguno de los puntos ensayados cumple todos los controles.
Frecuencia A observada solo por setup/hold a40%: ningún punto ensayado aprobado en las nueve esquinas.
Frecuencia B observada con cierre estricto a40% en este barrido: ninguno de los puntos ensayados cumple todos los controles.
Frecuencia B observada solo por setup/hold a40%: 10.000000 MHz.
Máxima frecuencia aprobada de A considerando todas las utilizaciones probadas: 10.000000 MHz.
Menor die A aprobado entre los tamaños ensayados: 0.445850 mm².

La A final histórica a100ns/40% sí está aprobada y se conserva fuera de esta serie deferred_flatten. B final a100ns/40% cumple timing y controles físicos ejecutados, con aceptación académica de sus avisos eléctricos. Los 10MHz comprobados de estas versiones no demuestran un máximo absoluto.
