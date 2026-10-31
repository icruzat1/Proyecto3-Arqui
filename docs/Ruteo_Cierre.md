> **Estado vigente:** B corregida en stage12 a10MHz, cero violaciones en los controles eléctricos y físicos ejecutados. Ver [Cierre_Electrico_B.md](Cierre_Electrico_B.md). Las decisiones y cifras previas de este documento se conservan como historial.

# Estado vigente: cierre académico B aprobado — 30 de octubre

B final es `stage9_100ns_u40_academic_b`, a 100 ns / 40 %. El flujo termina con código 0; conserva setup mínimo +23,444650 ns y hold +0,277806 ns en nueve esquinas, Magic DRC/LVS y antenas aprobados. Persisten cuatro salidas con exceso de capacidad, seis pines de transición y doce conductores con fanout superior a 10. La aceptación académica fue autorizada por el usuario; **no equivale a cumplimiento eléctrico total ni a aprobación para fabricar**.

Se repitieron únicamente los checkers finales sobre B trazable (`stage8_t100_u40_b`), sin alterar la netlist, el layout, Liberty ni SDC. Las vistas son idénticas por SHA256. Los resultados estrictos se conservan. Evidencia: [cierre B](../evidence/gf180_final_b_academic/results.json). Decisión: [justificación](Decision_Cierre_B.md). Explicación y siete respuestas a alternativas: [cierre eléctrico final](Cierre_Electrico_B.md).

A final anterior permanece aprobada (`evidence/gf180_final_a`). Los barridos de período siguen separados del cierre final; no se inicia otra reparación de B a 100 ns. KLayout DRC está omitido por falta de runset, no aprobado.

---

# Historial del intento dirigido B — 30 de octubre

A final permanece aprobada. B dirigido pasa setup/hold en nueve esquinas (mínimos +3,822947ns / +0,292626ns), Magic DRC/LVS, DRC del ruteador, conectividad, XOR y antenas. Quedan4conductores con exceso de capacidad y21pines con exceso de transición según Liberty, frente a9/49antes. Antenas1→0. El flujo termina con error eléctrico, sin cambiar el criterio de aceptación. Evidencia: `evidence/gf180_targeted_b`; auditoría: `evidence/gf180_targeted_review/audit.json`.

El intento cambió nueve fuerzas de celda y trasladó un diodo existente; el ruteo agregó89diodos para reparar antenas nuevas. Los nueve excesos de capacidad originales desaparecieron; los cuatro actuales pertenecen a otros conductores. No hay otra corrida de reparación iniciada.

Los apartados siguientes conservan el historial; sus estados de ejecución ya no son el estado vigente.

---

# Ruteo y cierre físico

Estado vigente, 30 de octubre: **A completó el flujo a 100 ns y 40 % con los límites eléctricos propios de la biblioteca y fanout máximo 10**. B cumple setup/hold, DRC y LVS, pero conserva nueve conductores fuera de los límites de la biblioteca y una infracción de antena. El usuario autorizó este criterio tras comparar los márgenes del flujo con los límites de las celdas. Los resultados históricos siguientes se conservan sin reinterpretarlos como PASS.

| Comprobación vigente | A final | B ECO3, pendiente de corrección |
|---|---:|---:|
| Peor setup extraído, ns | +10,907265 | +4,659079 |
| Peor hold extraído, ns | +0,110610 | +0,286206 |
| Pines de transición que superan Liberty, unión de esquinas | 0 | 49, en 7 redes |
| Conductores que superan capacidad Liberty | 0 | 9 |
| Antenas pendientes | 0 | 1 |
| Magic DRC / LVS | 0 / 0 | 0 / 0 |

A conserva la misma netlist binaria que su prueba funcional ECO3; se reutiliza esa evidencia mediante SHA256. El DRC del ruteador procede del estado DRT original, verificado como origen de la continuación; antenas, extracción, STA y los controles finales se ejecutaron de nuevo. KLayout DRC sigue omitido por falta de runset y el LVS usa extracción DEF/LEF: no se afirma signoff completo de fabricación.


## Primera implementación enrutada

| Resultado | A | B |
|---|---:|---:|
| DRC del ruteador | 0 | 0 |
| Magic DRC sobre GDS | 0 | 0 |
| Peor slack setup extraído, ns | −8,173274 | −20,777514 |
| Peor slack hold extraído, ns | positivo | −0,105311 |
| Redes/pines con infracción de antena, última comprobación | 0/0 | 3/3 |
| LVS | 0 errores | 0 errores |

No usar los ceros de DRC como prueba de timing. KLayout DRC se omite porque esta revisión del PDK no aporta su runset. La comparación XOR entre streamouts es una comprobación diferente. EQY no se ejecuta para esta configuración. La extracción usada para LVS parte de DEF/LEF; se documenta ese alcance y no se afirma validación completa de fabricación o alimentación.

## Por qué cambió el resultado después de colocar

El ruteador detallado de A añadió 25 diodos después de la última reparación de diseño y timing: el total pasó de 4 a 29. Esos diodos protegen frente a acumulación de carga durante fabricación, pero también añaden cargas a las redes. Ocho redes que tenían cuatro cargas pasaron a cinco; se observaron nueve violaciones finales de fanout.

También hay diferencias entre RC estimado y extraído. En una red A, _09113_/ZN, la capacidad pasó de 0,02433 pF estimada a 0,05238 pF extraída nominal. La transición típica pasó de 1,671 a 3,220 ns; en max-SS llegó a 6,667 ns, por encima del límite de 3 ns. No basta con volver a ejecutar el mismo análisis de colocación.

En el mismo camino típico _10465_→_10890_, el slack pasó de 49,571 a 43,812 ns al extraer. En la esquina lenta, con menos margen, aparecieron los valores negativos de la tabla. Estas son mediciones, no una reducción del período solicitado.

```mermaid
flowchart LR
  P[Colocación y reloj] --> R[Ruteo y diodos]
  R --> X[Extracción RC: SPEF]
  X --> T[STA en nueve esquinas]
  T --> C[Reparación del diseño]
  C --> R
```

## Corrección en curso

ECO1 empieza desde el estado posterior al ruteo detallado, conservando los diodos encontrados. Usa los pasos estándar de reparación y un nuevo tag; no modifica los artefactos de referencia. La reparación eléctrica apunta a márgenes de slew/cap del 40 %. El objetivo adicional de setup es 20 ns para A y 30 ns para B, para cubrir el deterioro observado al extraer. B añade un margen de reparación hold de 0,3 ns; A mantiene 0,05 ns.

Estos parámetros guían el optimizador. No cambian CLOCK_PERIOD=100 ns, los límites del SDC ni las comprobaciones finales. El resultado sigue pendiente hasta repetir ruteo, extracción, nueve esquinas y checks físicos. Las tres infracciones de antena restantes de B se están diagnosticando; no se dan por justificadas ni corregidas.

## Evidencias y continuidad

La primera reanudación ECO de A encontró rutas físicas antiguas incompatibles con las celdas recolocadas. Esa tentativa quedó archivada. La siguiente parte de una copia que elimina solo el cableado de señales, conserva conexiones lógicas, celdas, posiciones y alimentación, y regenera las rutas antes de reparar. No se modifican los ODB originales. La prueba real de la copia A retiró 11096 rutas regulares y conservó 14960 instancias, dos conjuntos de cableado especial de alimentación, conectividad y posiciones. La relectura del ODB y el DEF exportado coinciden; este control no sustituye las comprobaciones posteriores de timing, DRC y LVS.

Los runs viven bajo config/gf180/runs/stage6_100ns_u40_route_a/b y las correcciones bajo tags nuevos. Los registros del lanzador se guardan en build/gf180_stage5 también para esta etapa; el nombre de la carpeta no indica el alcance físico de cada corrida. summarize_gf180_stage6.py lee métricas emitidas por cada STA final, valida procedencia de SPEF, relojes propagados y anotación, y conserva errores incluso si el flujo termina con retorno distinto de cero.

Los resultados de colocación se conservan en [Colocacion_Timing.md](Colocacion_Timing.md). No se ha cambiado RTL, firmware, SDC ni Proyecto 2. La publicación por GitHub permanece exclusivamente mediante la sesión personal icruzat1 de VS Code.


## Comprobación funcional de las netlists enrutadas

La primera ruta A/B pasó la comparación acotada frente al RTL de producción con 21295 muestras por variante: dos épocas de arranque, cuatro tramas SPI, dos comprobaciones dirigidas de reset y 178 cambios de botones. A/B ejecutaron 21266/20913 ciclos activos. Se usaron los modelos FUNCTIONAL del PDK, conservando también diodos y celdas físicas; no se eliminó ninguna clase de celda para hacer pasar la simulación.

La prueba no usa SDF, no recorre la partida completa y no demuestra cierre temporal ni equivalencia formal. El resultado conserva explícitamente que ambos flujos físicos iniciales fallaron sus comprobaciones. Evidencia: evidence/gf180_stage6_functional_initial. La nueva corrección física se verificará de nuevo sobre su propia netlist.


## Resultado intermedio ECO2A

La reparación mejoró el peor setup extraído de −8,173274 a +9,233453 ns; hold mínimo +0,115517 ns. Setup y hold pasan las nueve esquinas. Persisten restricciones eléctricas: máximo de 532 violaciones de slew, 1 de capacidad y 5 de fanout por esquina. La simulación acotada se repitió sobre esta netlist y pasó 21295 muestras. La primera exportación Magic no pudo continuar por una propiedad DIE_AREA ausente en el estado reanudado; por ello no se atribuyen DRC/LVS finales a esta revisión.

La geometría se reconstruye del DEF actual en un estado derivado separado. ECO3 usa márgenes eléctricos del 70 % para compensar la diferencia entre estimación y extracción: la medición SS estimada de ECO2A tenía 3 violaciones de slew frente a 532 con parásitos extraídos. Este margen guía la optimización y no cambia los límites de aceptación. Resultados ECO3 pendientes.


## Estado ECO3A y pausa de análisis

ECO3A terminó con setup mínimo +10,907265 ns y hold mínimo +0,110610 ns. Pasan nueve esquinas de timing, Magic DRC, LVS, XOR, antenas, DRC del ruteador y conectividad. La simulación funcional repitió 21295 muestras sin diferencias. Persisten hasta 429 violaciones de slew, una de capacidad y dos de fanout por esquina: el cierre eléctrico sigue pendiente.

B sigue en ejecución; sus resultados se archivarán automáticamente. Se acordó una pausa antes de decidir la siguiente corrección con mayor potencia de razonamiento. No se preparó el informe final.
