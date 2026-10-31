# Cierre eléctrico de B a 10 MHz

Estado físico: **aprobado en todos los controles ejecutados**. Corrida `stage12_electrical_route_b`, período100ns, utilización inicial40%, biblioteca y objetivo fanout10 sin cambios. La comparación funcional de la netlist nueva se registra por separado en Verificacion_Final.md.

| Control | B anterior | B corregida |
|---|---:|---:|
| Setup / hold | 0 / 0 | 0 / 0 |
| DRC de ruteo / Magic / LVS | 0 / 0 / 0 | 0 / 0 / 0 |
| Antenas | 0 | 0 |
| Capacidad, salidas únicas | 4 | 0 |
| Transición, pines únicos | 6 | 0 |
| Fanout, conductores únicos | 12 | 0 |

Nueve esquinas completas, parasíticos extraídos y propagación/anotación verificadas. Peor setup **+22.614665ns**; peor hold **+0.293077ns**. Área stdcell post-PNR 1166260µm²; die 2.135480mm²; 5433 celdas secuenciales. No se extrapola aprobación a25MHz.

## Qué cambió y por qué

La primera corrección reforzó cuatro celdas sin cambiar su función lógica y dividió doce redes en24ramas con buffers. Se conservaron los diodos y se verificó que, al colapsar los buffers de identidad, las conexiones originales permanecían iguales. La nueva colocación y el ruteo completo resolvieron los avisos originales, pero dejaron1salida cap,5pines slew de esa misma red y2fanouts en tres redes distintas. Stage11 queda archivada como intento incompleto, sin ocultar sus fallos.

La segunda corrección introdujo cinco buffers: uno a la salida del NOR4 del RF y cuatro para repartir las cargas de las dos redes restantes. Se utilizó el mecanismo incremental de LibreLane: originales bloqueados durante la colocación y actualización de solo ocho redes de conexión. Esto conservó el resto del ruteo y evitó repetir la reparación general. Stage12 pasó después DRT, extracción, STA y los controles físicos ejecutados.

La preparación inicial del paso incremental falló por una ruta de importación de Python antes de modificar el diseño. Se corrigió el paso y se usó un directorio nuevo; no fue una corrida física fallida ni una alteración del respaldo.

## Decisión vigente y límites

El usuario reabrió explícitamente B para exigir cero violaciones. El cierre académico anterior con excepciones se conserva como historial, pero ya no es la versión elegida. Los checkers de capacidad y transición están habilitados en todas las esquinas; no se cambiaron los límites para conseguir este resultado.

KLayoutDRC sigue omitido por falta de runset. No se declara equivalencia formal EQY, simulaciónSDF ni cierreIR/EM. LVS usa extracciónDEF/LEF. El resultado es cero violaciones en los controles ejecutados, no una certificación completa para fabricar.

## Evidencias y reproducción

- [Resultado físico y nueve esquinas](../evidence/gf180_final_b_electrical/results.json).
- [Primer intento con avisos](../evidence/gf180_electrical_b_attempt1/results.json).
- Plan inicial: build/gf180_electrical_b/plan.json; preparación y conectividad verificadas en stage11_electrical_prepared_b.
- Corrección incremental: scripts/electrical_incremental_b.py y stage12_incremental_prepared_v2_b.
- [Tabla finalA/B](Violaciones_Finales_10MHz.md).
- Checkpoint nuevo: evidence/gf180_final_replay/electrical/b_checkpoint.zip. Restauración verificada con `scripts/replay_final_checkpoint.py --profile electrical --variant b --prepare-only`; reproduce un estado físico existente, no una nueva síntesis desdeRTL.

Referencia del mecanismo: [ECOs de LibreLane](https://librelane.readthedocs.io/en/stable/usage/using_ecos.html).
