# Evidencia del juego ASIC a 10 MHz

El [índice de resultados](results.json) reúne las comprobaciones de esta etapa y las huellas de los archivos conservados. [Juego a 10 MHz](../../docs/Juego_10MHz.md) explica decisiones, perfiles, pruebas y límites.

| Carpeta | Alcance |
|---|---|
| full_game | Diez rondas, dos errores y reintentos, botones mantenidos, saturación, promedio y reset; ambos umbrales acelerados |
| wait_only | Dos aciertos y un error con reintento; solo la espera inicial reducida, divisor de reacción de producción intacto |
| timing | Constantes comprobadas en código máquina y veinte casos dirigidos de la ALU en los límites del contador |
| production_memories | Regresión de interfaces e integración con la ROM de producción a 10 MHz |
| production_synthesis | Cuatro síntesis genéricas y comprobación del almacenamiento FF con firmware de producción |
| production_memory_netlist | Ensayo de interfaces de ambas memorias después de síntesis |
| firmware_profiles | Fuentes derivadas, ROM, hex y manifiestos exactos usados por cada perfil |

Los archivos results.json internos conservan las rutas originales bajo build para facilitar la reproducción. El índice principal relaciona esas rutas con sus copias publicadas. Los logs y scripts de síntesis se conservan íntegros. Las netlists voluminosas y ejecutables se regeneran con las órdenes del informe; sus huellas quedan en los resultados.

Cada archivo equivalence_*.trace.csv.gz contiene la traza por ciclo de una corrida emparejada RTL/netlist. El verificador comparó ambos circuitos durante la ejecución; además comprobó la igualdad con la traza RTL independiente. El índice registra las huellas del CSV original y de su copia comprimida. Las trazas wait_only incluyen transacciones MMIO para observar una escritura de 00 aunque no cambien los segmentos.

Esta evidencia corresponde a síntesis y simulación genéricas, sin mapeo GF180 ni SDF. Las constantes de producción están verificadas, pero no se simuló una partida completa con esperas de treinta millones de ciclos. Debe repetirse la comprobación funcional sobre las netlists mapeadas del flujo final. No se presentan área GF180, Fmax ni signoff de Espino.

Los resultados anteriores de memorias, con el programa FPGA original de 94 instrucciones, se preservan en las carpetas históricas de evidence y en el commit d867d61. Esta etapa usa 95 instrucciones ASIC y no modifica Proyecto 2 ni baseline.
