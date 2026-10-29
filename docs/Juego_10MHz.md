# Juego ASIC a 10 MHz y comparación después de síntesis

29 de octubre de 2026. Esta etapa adapta las constantes de tiempo y verifica una partida completa en las memorias A y B antes de comenzar el floorplan.

## Estado comprobado

El firmware ASIC está recalibrado y el macro completo pasó las pruebas del juego en ambas arquitecturas, antes y después de síntesis genérica. Se verificaron una partida de diez rondas y, por separado, acierto/error/reintento acelerando únicamente la espera inicial. La implementación física y la repetición con netlists mapeadas a GF180 siguen pendientes. [Resumen verificable](../evidence/asic_game/results.json).

`firmware/asic/game.s` contiene las constantes de producción: 30 000 000 ciclos por espera de tres segundos y 1 000 000 por décima. Se comprobaron en el código máquina. No se presenta una simulación de treinta millones de ciclos por espera como resultado de esta etapa.

La revisión reprodujo el salto de la espera al cruzar el límite signed del contador. La copia ASIC ahora compara el tiempo transcurrido. Las veinte pruebas aritméticas con la ALU real detectan dos fallos del algoritmo anterior y ninguno del corregido. El programa original de Proyecto 2 se conserva.

El firmware ASIC ocupa 95 instrucciones; las 33 posiciones restantes de la ROM devuelven NOP. El generador usa esta copia por defecto. La capacidad de datos y los 144 ciclos de carga de B se mantienen.

## Perfiles de tiempo

| Perfil | Espera en ciclos | Ciclos por décima | Uso |
|---|---:|---:|---|
| production | 30 000 000 | 1 000 000 | Firmware que se llevará al flujo físico a 10 MHz |
| simulation | 3000 | 100 | Partida completa y casos de promedio y saturación |
| wait_only | 3000 | 1 000 000 | Prueba que acelera únicamente la espera inicial permitida por el enunciado |

El reloj de simulación sigue siendo de 100 ns. En el perfil completo se dividen ambos umbrales por 10 000; las latencias de instrucciones y periféricos permanecen iguales. No equivale a acelerar exactamente por ese factor la duración total de la partida. Los perfiles de prueba se generan bajo `build` y no sustituyen la ROM de producción; el generador impide escribirlos bajo `rtl`. En `wait_only` se registran factores separados: espera 10 000 y reacción 1; no existe un factor común.

Cada perfil se genera desde la misma fuente, con el assembler original. `timing.json` registra constantes, etiquetas/PC y procedencia; el manifiesto registra las huellas del programa y ROM. La verificación decodifica las instrucciones reales, comprueba sus constantes y exige que las imágenes difieran únicamente en los operandos de temporización.

## Corrección de la espera

El algoritmo anterior comparaba el contador actual con un límite absoluto mediante BLT, que interpreta los operandos con signo. Con inicio 0x7FFFFFE0 y duración 30 000 000, el límite es 0x81C9C360. Tras solo 24 ciclos el contador vale 0x7FFFFFF8: el positivo ya no es menor que el límite negativo, por lo que termina prematuramente la espera.

La copia ASIC guarda el inicio y calcula `actual - inicio` módulo 2³². Compara ese transcurrido con la duración. La corrección usa las instrucciones existentes y añade una instrucción; no modifica el assembler ni la ALU. Es válida para la espera configurada, menor que 2³¹ ciclos, con sondeo continuo antes de alcanzar ese transcurrido.

La prueba dirigida utiliza la ALU real de Espino: **20 casos, dos fallos reproducidos del algoritmo anterior y cero del corregido**, incluidos orígenes próximos a 2³¹ y 2³². Además comprueba en el hex la secuencia de guardar inicio, restar y comparar. Esto confirma el defecto aritmético; no atribuye a él los fallos físicos de la FPGA reportados anteriormente. [Prueba y límites](../evidence/asic_game/timing/results.json).

Permanece una limitación distinta del juego heredado: una reacción de al menos 2³¹ ciclos puede interpretarse como negativa durante la división, aproximadamente 214,75 segundos a 10 MHz. Esta etapa corrige la espera inicial y no altera esa política de reacción prolongada.

## Partida completa y correspondencia por ciclo

La prueba completa usa `simulation`, con idéntico firmware, reset y botones para RTL y netlist de una misma variante. Un comprobador calcula la respuesta esperada a partir de las muestras reales del contador y verifica aciertos, errores, liberación del botón, saturación y promedio. Compara todas las salidas lógicas después de cada flanco, incluyendo carga y reset. SPI permanece inactivo en estas pruebas de juego; su transferencia ya se probó en el diagnóstico RAM/MMIO/SPI.

| Prueba completa | A | B |
|---|---:|---:|
| Ciclos de corrida, incluidos arranque y resets | 65 291 | 65 577 |
| Aciertos | 10 | 10 |
| Errores con reintento de la misma ronda | 2 | 2 |
| Intentos | 12 | 12 |
| Comprobaciones con botón mantenido | 4800 | 4800 |
| Casos que saturan en 99 décimas | 1 | 1 |
| Suma de resultados / promedio entero | 162 / 16 | 162 / 16 |
| Resets ejercitados | 3 | 3 |
| RTL y netlist del macro completo | PASS | PASS |

Los ciclos totales incluyen las cargas de arranque distintas. La comparación exigida se realiza **RTL A contra netlist A** y **RTL B contra netlist B**, sin confundir la carga B con la ejecución de instrucciones. Las trazas de la ejecución RTL independiente coinciden con las de la ejecución emparejada RTL/netlist. [Resultados de partida completa](../evidence/asic_game/full_game/results.json).

## Prueba con únicamente la espera acelerada

La sección 3.7 permite reducir la espera inicial para simular. Se ejecutó además `wait_only`, que conserva el divisor de reacción de producción de 1 000 000 ciclos. Comprueba un acierto, un botón incorrecto, el reintento y un segundo acierto. Las reacciones de este ensayo son menores que una décima y su resultado correcto es `00`.

Como escribir `00` puede dejar sin cambio un display que ya mostraba cero, aquí se comparan también por ciclo el reset interno y las transacciones MMIO: solicitud, escritura, dirección, byte enables y datos escritos. Esto hace observable el ciclo exacto en que termina una ronda. Se inspeccionan esas señales de diagnóstico en la netlist aplanada y se verifica su existencia; no se agregan terminales al macro.

| Prueba `wait_only` | A | B |
|---|---:|---:|
| Ciclos de corrida | 10 623 | 10 766 |
| Aciertos / errores / intentos | 2 / 1 / 3 | 2 / 1 / 3 |
| Comprobaciones con botón mantenido | 600 | 600 |
| Solicitudes MMIO / escrituras | 1118 / 11 | 1118 / 11 |
| Accesos a RAM ordinaria | 0 | 0 |
| Acierto: desde escritura del LED activo hasta escritura del resultado | 302 ciclos | 302 ciclos |
| Error: desde escritura del LED activo hasta escritura de `EE` | 269 ciclos | 269 ciclos |
| RTL y netlist: terminales y ciclos MMIO | PASS | PASS |

La pulsación equivocada no incrementa aciertos ni suma; tras soltarla se inicia nuevamente la ronda pendiente. El botón mantenido tampoco produce rondas adicionales. [Resultados y trazabilidad](../evidence/asic_game/wait_only/results.json).

## Regresión y síntesis

- Generador de ROM: nueve pruebas; generador de perfiles: seis pruebas.
- Firmware de producción: cuatro simulaciones de memorias/integración, cuatro síntesis genéricas y ensayo de interfaces sobre las netlists de memoria aprobados.
- Cada prueba de juego sintetiza el macro completo en A y B con su propia imagen de prueba, usando Yosys 0.62 de la imagen Docker fijada, `synth -noabc` y `check -assert`.
- La comprobación de almacenamiento conserva 512 bits FF independientes en A y 4608 en B. La arquitectura de memoria y el protocolo no cambiaron al recalibrar el programa.

La síntesis jerárquica de producción cuenta 1329 FF genéricos en top A y 5433 en top B. Las síntesis aplanadas con firmware de prueba cuentan 1327/5433. En esa comparación cambian tanto las opciones de síntesis como las constantes de la imagen ROM; no se atribuyen los dos FF de diferencia a una causa aislada. Las optimizaciones genéricas pueden dar conteos distintos; los módulos de CPU, periféricos y memorias no cambiaron, mientras que la ROM sí se regeneró. Hay que comparar conteos con el mismo firmware y las mismas opciones; estos números no son áreas de celdas GF180.

Los resultados históricos de memorias del commit `d867d61` permanecen en [Memorias A/B](Memorias_AB.md). La evidencia de producción recalibrada está separada en [simulación](../evidence/asic_game/production_memories/results.json), [síntesis](../evidence/asic_game/production_synthesis/results.json) e [interfaces post-síntesis](../evidence/asic_game/production_memory_netlist/results.json).

## Reproducción

Desde la raíz del repositorio, con Python, Icarus y Docker Desktop disponibles y la imagen fijada ya descargada:

```sh
python3 scripts/generate_asic_memory.py --check
python3 -m unittest discover -s sim/asic_stage3 -p 'test_generate_game_firmware.py' -v
python3 scripts/check_game_timing.py
python3 scripts/check_asic_memories.py
python3 scripts/check_asic_memory_synthesis.py
python3 scripts/check_memory_netlist.py
python3 scripts/check_full_game.py
python3 scripts/check_game_wait_only.py
```

`--rtl-only` en los dos últimos comandos omite síntesis y comparación de netlists; una corrida con esa opción no demuestra el resultado post-síntesis. Los scripts registran entradas, huellas, logs y resultados bajo `build`. La evidencia seleccionada y su índice están en [evidence/asic_game](../evidence/asic_game/README.md). Las corridas Docker usan la imagen por digest, sin descarga y con red deshabilitada.

## Límites y trabajo siguiente

Una vez comprobado el funcionamiento se preparan las restricciones de reloj y entrada/salida, se mapea el diseño a GF180 y se trabaja en el floorplan. El punto de referencia del enunciado es 100 ns y 40 % de ocupación. Después se completan colocación, árbol de reloj, ruteo, análisis temporal y verificaciones físicas.

La comparación es simulación funcional de escenarios concretos del macro completo sintetizado a celdas genéricas. No es equivalencia formal, no usa SDF y no demuestra comportamiento eléctrico ni timing físico. La prueba aritmética de bordes no es una partida completa iniciada cerca del desbordamiento. La partida de diez rondas utiliza ambos umbrales acelerados; la prueba separada `wait_only` conserva la unidad de reacción de producción y cubre acierto, error y reintento.

Falta mapear a GF180 y repetir la comprobación con las netlists mapeadas del flujo final. Deben completarse al menos tres períodos y tres utilizaciones, mejora RTL de la ruta crítica y comparación, cierre temporal, DRC/LVS/antenas, layout anotado, área/costo e informe. Todavía no se reportan Fmax, área GF180 ni signoff de Espino.
