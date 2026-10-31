# Ensayo RTL y trazabilidad — síntesis comparable

Resultados de la receta `deferred_flatten` a 100 ns / 40 %. Esta receta conserva nombres de módulos antes del aplanamiento final. No sustituye ni reinterpreta las corridas físicas anteriores.

| Variante | Referencia (µm²) | Candidata (µm²) | Cambio | FF referencia → candidata |
|---|---:|---:|---:|---:|
| A | 208256.4288 | 214389.8176 | +2.945 % | 1329 → 1411 |
| B | 828235.7888 | 833622.8096 | +0.650 % | 5433 → 5515 |

Las cuatro netlists pasaron la comparación funcional acotada contra RTL de producción: 21.295 muestras, dos arranques, cuatro tramas SPI y dos resets por prueba. No incluye SDF ni una nueva partida completa. Se conservan las nueve simulaciones anteriores del prototipo.

La ALU conserva 589 instancias y suma 10.152,8 µm² en las cuatro síntesis. En A referencia, el subsistema de memoria suma 83.132,224 µm² y el núcleo CPU 105.593,5104 µm²; dentro de este último, RF suma 71.587,6672 µm². En B referencia, memoria suma 703.109,3888 µm². Estos valores incluyen los hijos de cada módulo: no sumar CPU, RF y ALU entre sí. Las particiones directas sin doble conteo están en cada results.json.

Todavía no se concluye mejora de timing. La comparación física debe usar referencia y candidata con la misma receta; STA previo a colocación no determina Fmax. El circuito de producción y A final permanecen intactos.

Reproducción: scripts/run_gf180_synthesis_trial.py y scripts/evaluate_gf180_synthesis_trial.py; configuraciones a_trace_ref/candidate y b_trace_ref/candidate. Evidencia detallada: evidence/gf180_synthesis_trials/stage7_trace_*.


## Comparación física A a 100 ns / 40 %

| Medida | Referencia comparable | Candidata |
|---|---:|---:|
| Peor setup (nueve esquinas) | +46,597209 ns | +55,219948 ns |
| Peor hold/removal | −0,022720 ns | +0,015524 ns |
| Área de celdas post-PNR sin relleno (métrica stdcell) | 284.008 µm² | 294.043 µm² |
| Área die | 553.389 µm² | 569.198 µm² |
| Máxima capacidad / transición fuera de límite | 0 / 0 | 0 / 0 |
| Fanout fuera de límite | 0 | 1 (12 frente a 10) |

El candidato mejora el peor setup 8.622738 ns frente a la referencia de la misma receta, con costo de síntesis +2.945 % y área stdcell post-PNR +3.533 %. Una pareja de corridas demuestra esta diferencia medida; no establece una mejora independiente de la colocación ni Fmax. El cambio de hold no se atribuye por separado al RTL: también cambian colocación y reloj.

Ambas corridas pasan DRC del ruteador, Magic DRC, LVS, antenas, XOR y desconexiones. KLayout DRC continúa omitido por falta de runset. La referencia falla removal del reset externo en maxFF (rst_ni → u_reset._2_); no reemplaza A final aprobada. El candidato pasa setup/hold en nueve esquinas, pero fanout222/Z tiene 12 cargas frente al límite 10. LibreLane terminó con código cero, mientras la comprobación independiente detectó ese incumplimiento: completar el flujo no equivale a cumplir todos nuestros criterios.

Se conserva el candidato como experimento medido; no se adopta ni se inicia otra reparación. Su prueba funcional de este bloque corresponde a la netlist de síntesis, no a una nueva simulación post-ruteo. B solo tiene medición de síntesis en esta comparación. Evidencia y extractos reales de caminos: evidence/gf180_rtl_comparison; archivos completos: evidence/gf180_trace_physical_ref_a y evidence/gf180_trace_physical_candidate_a.
