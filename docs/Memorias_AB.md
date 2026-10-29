# Memorias ASIC A/B: implementación y evidencia

29 de octubre de 2026. El top utiliza ahora memorias de producción. El programa sigue siendo el original de 94 instrucciones; la recalibración a 10 MHz y la verificación completa del juego se abordarán después de esta etapa.

## Arquitecturas implementadas

| Propiedad | A | B |
|---|---|---|
| Programa | ROM combinacional de 128 palabras, 94 usadas y 34 NOP | Primeras 128 posiciones de un arreglo de FF reescribibles |
| Datos | RAM de 16 palabras | Últimas 16 posiciones del mismo arreglo de 144 |
| Inicialización | ROM por lógica; RAM a cero con reset | Cargador escribe una palabra por flanco, desde índice 0 hasta 143 |
| Disponibilidad tras reset de memoria | Primer flanco | Flanco 144 |
| Reprogramación de instrucciones | Escrituras descartadas | Permitida por bytes; lecturas toman el arreglo FF |
| Puerto de instrucciones | ROM 0x000..0x1FC; resto NOP | Arreglo completo 0x000..0x23C; resto NOP |
| Puerto de datos | ROM de solo lectura y RAM 0x200..0x23C | Arreglo completo reescribible |

Las direcciones de la tabla son comienzos de palabras de cuatro bytes. El rango total de bytes termina en 0x23F. Se comprueba la dirección completa y su alineación: una solicitud desalineada o fuera del rango no accede a un alias. Las lecturas de datos inválidas devuelven cero; las escrituras inválidas se descartan. El LSU ya entrega direcciones alineadas y expresa el byte seleccionado mediante `b_be_i`, por lo que no se pierde el acceso por bytes.

La lectura de instrucciones se registra cuando `a_req_i` está activo y se conserva al desactivarlo. La lectura de datos se registra cada flanco, incluso si no hay solicitud. En una colisión de lectura y escritura se observa el valor anterior (*read-first*). A no ejecuta su RAM de datos; B puede leerla como instrucciones por ser unificada. Esta diferencia se prueba y no afecta los accesos del juego actual.

`asic_top.MemoryVariant` selecciona A=0 o B=1 durante elaboración. Una netlist contiene una arquitectura. La selección inválida falla deliberadamente. El manifiesto `config/rtl_asic.f` reúne todas las fuentes de producción; no incluye la memoria de simulación de la primera etapa.

## Programa y generación

`scripts/generate_asic_memory.py` invoca la función del assembler original sobre `game.s`. Genera tres archivos en `rtl/asic/generated`: `game.hex`, `asic_program_rom.v` y un manifiesto con procedencia y huellas. El programa predeterminado se compara con ambas copias originales del hex y conserva sus 94 palabras y SHA256.

El contenido de la ROM es una función con `case` y asignación continua. No usa `initial`, archivos en tiempo de ejecución ni celdas FPGA. A usa esa lógica para sus lecturas; B la usa exclusivamente durante la carga. Las lecturas de B en funcionamiento salen del arreglo reescribible, no de la ROM de carga.

Una prueba descubrió que el generador inicial con `always @*` podía dejar indefinida la dirección cero si el índice permanecía constante desde el inicio en Icarus. Se corrigió con función y asignación continua, y se añadió una regresión con índices 0 y 127 conectados a constantes. La corrección está en el generador, no en un cambio artificial del estímulo.

## Reset y carga real

La memoria B no resetea simultáneamente sus 4608 bits. El reset solo inicializa controlador, disponibilidad y salidas; el cargador restaura todas las palabras por escrituras síncronas. Si el reset interrumpe la carga, vuelve al índice cero. Si hubo escrituras de programa o datos, un nuevo reset restaura la imagen y limpia datos.

Durante la carga B ignora solicitudes normales. Su última escritura y la disponibilidad se registran en el mismo flanco; la CPU se libera mediante el registro de reset posterior. Así no lee antes de completar la carga. La CPU, RF y contador del juego siguen detenidos mientras se prepara la memoria.

El cargador B tarda 144 ciclos, equivalentes a 14,4 microsegundos con reloj de 100 ns, además de la sincronización y liberación del reset. A anuncia disponibilidad al primer flanco: la diferencia de carga es 143 ciclos. La prueba comparativa retrasa la liberación externa de A esos 143 ciclos y verifica que ambos cores y contadores comiencen juntos.

## Pruebas terminadas

- Generador: ocho pruebas, incluidos límites 0/128/129, reproducción exacta, verificación sin escritura, archivos alterados/faltantes, protección de referencias e índices constantes.
- Interfaces de memoria: 5800 ciclos normales, 519 flancos de carga verificados, cinco resets y dos cargas completas. Se recorren las 144 palabras y las 16 máscaras de bytes; se comprueba modificación/restauración de código B e inmutabilidad de A.
- Cobertura de interfaces: 256 colisiones de datos en A, 2304 colisiones en B, 40 accesos inválidos, 144 escrituras sin solicitud, 288 retenciones del puerto de instrucciones y 3188 lecturas de datos sin solicitud.
- Top con juego original: dos arranques, 20000 ciclos de ejecución comparados entre A/B, con 2494 solicitudes de lectura MMIO y cero accesos a RAM ordinaria en ese intervalo. Esta observación dinámica cubre solo el intervalo ensayado.
- Diagnóstico de CPU en A y B: escritura y lectura real de RAM, botones, contador, display A5 y transacción SPI 3C/96. El firmware llega al LED de éxito solo después de comparar los datos leídos.
- Interfaces sobre netlists genéricas: el mismo ensayo de 5800 ciclos, 519 flancos de carga y cinco resets pasó tras síntesis, sin retardos. Es una prueba funcional de las memorias, no equivalencia formal ni validación post-síntesis del juego completo.
- Regresión de primera etapa: sus siete pruebas siguen pasando con la memoria de simulación aislada explícitamente, conservada como referencia de depuración.

Estas pruebas no sustituyen las rondas completas correctas/erróneas ni la equivalencia de juego RTL/netlist exigida en la entrega. El programa sigue con constantes para 25 MHz; durante estas pruebas a 100 ns no se afirma que la espera inicial dure tres segundos físicos.

## Síntesis

Las cuatro corridas con Yosys 0.62, revisión 7326bb7d6641500ecb285c291a54a662cb1e76cf, terminaron correctamente. Se utilizó la imagen fijada de LibreLane, `synth -noabc` y `check -assert`, sin mapeo a GF180 ni flujo físico.

| Síntesis genérica | Bits de almacenamiento comprobados | FF totales, incluidos salidas y control |
|---|---:|---:|
| memory_a aislada | 512 | 577 |
| memory_b aislada | 4608 | 4681 |
| asic_top con A | 512 en RAM | 1329 |
| asic_top con B | 4608 en memoria unificada | 5433 |

La comprobación recorre los nombres de todas las palabras de la netlist: exige 32 bits distintos por palabra, sin constantes ni alias entre posiciones, y un único conductor FF.Q para cada bit. Comprueba 512 y 4608 bits tanto en memorias aisladas como dentro de los respectivos macros. No se usaron atributos para conservar artificialmente esos arreglos. Los conteos totales recorren instancias, por lo que incluyen correctamente módulos repetidos.

Los 577 FF de A son 512 de datos, 64 de salidas y uno de disponibilidad. Los 4681 de B son 4608 de almacenamiento, 64 de salidas, ocho de índice de carga y uno de disponibilidad. La diferencia total es 4104 FF genéricos. Esto no determina la diferencia de área física: faltan mapeo, lógica combinacional, buffers y efectos de colocación/enrutamiento.

No se detectaron latches, primitivas FPGA, memorias sin mapear ni cajas negras. Cada top contiene exclusivamente la arquitectura seleccionada. Las advertencias de convertir `ram_ff` y `regs_q` a registros son coherentes con la implementación mediante FF y están conservadas con sus líneas en [resultados de síntesis](../evidence/asic_memory_synthesis/results.json). No se presentan todavía área GF180, Fmax, timing ni signoff.

## Reproducción

```sh
python3 scripts/generate_asic_memory.py
python3 scripts/generate_asic_memory.py --check
python3 scripts/check_asic_memories.py
python3 scripts/check_asic_memory_synthesis.py
python3 scripts/check_memory_netlist.py
```

La simulación requiere Python e Icarus. La síntesis usa la imagen Docker fijada, sin descargas ni red. Los resultados se guardan bajo `build`; la evidencia seleccionada se conserva junto con los archivos y hashes ensayados: [simulación](../evidence/asic_stage2/results.json), [síntesis](../evidence/asic_memory_synthesis/results.json) y [regresión anterior](../evidence/asic_stage2/stage1_regression/results.json).

El ensayo post-síntesis comprueba primero las huellas de fuentes y netlists, reutiliza el testbench de interfaces y compara con el hex original independiente. [Resultado y cobertura](../evidence/asic_memory_netlist/results.json). Las netlists permanecen intactas; solo se renombran módulos en copias temporales para poder simular A y B simultáneamente sin colisión de nombres.
