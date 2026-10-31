# Violaciones de las versiones finales a 10 MHz

Ambas versiones usan100ns y utilización inicial40%. A: stage13_final_traceable_a. B: stage12_electrical_route_b. La B anterior académica se conserva como respaldo; esta tabla corresponde a la B corregida, no a la anterior.

| Control | A | B corregida |
|---|---:|---:|
| Setup | 0 | 0 |
| Hold (incluye recovery/removal) | 0 | 0 |
| DRC de ruteo | 0 | 0 |
| Magic DRC | 0 | 0 |
| LVS | 0 | 0 |
| Antenas (redes) | 0 | 0 |
| Capacidad (salidas únicas) | 0 | 0 |
| Transición (pines únicos) | 0 | 0 |
| Fanout > 10 (conductores únicos) | 0 | 0 |

Los ceros de setup, hold, capacidad, transición y fanout se verifican en las nueve esquinas. No se suman esquinas ni se mezclan unidades. Los límites Liberty y fanout10 se mantienen; todos los checkers eléctricos vuelven a estar habilitados. La B anterior tenía4salidas de capacidad,6pines de transición y12conductores con fanout excesivo: sus evidencias históricas se preservan.

**Alcance:** KLayout DRC está omitido por falta de runset. No se declara equivalencia formal EQY ni cierre IR/EM; LVS usa la extracción DEF/LEF documentada. Cero violaciones en los controles ejecutados no equivale a validación completa para fabricar.

Procedencia y conteos: [JSON](../evidence/gf180_final_comparison/violations_10mhz.json). Evidencia nuevaB: [resultados](../evidence/gf180_final_b_electrical/results.json). Historia y reparación: [Cierre_Electrico_B.md](Cierre_Electrico_B.md).
