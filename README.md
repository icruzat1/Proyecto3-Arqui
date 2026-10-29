# Proyecto 3 de Arquitectura de Computadores

Adaptación ASIC del procesador Espino y del juego del Proyecto 2, con LibreLane y GF180MCU. El desarrollo conserva el Proyecto 2 original y utiliza exclusivamente la cuenta personal icruzat1.

## Estado

El firmware ASIC está recalibrado a 10 MHz y ocupa 95 instrucciones. A usa ROM128 + RAM16 y B una memoria FF144 con carga de 144 ciclos. Ambas arquitecturas pasaron la partida completa y la comparación por ciclo entre RTL y netlists genéricas del macro completo. Una prueba adicional conserva la décima de producción y acelera únicamente la espera inicial, comprobando los ciclos de acierto, error y reintento. Ver [Juego a 10 MHz](docs/Juego_10MHz.md) y [resultados](evidence/asic_game/results.json).

La base FPGA conservada reproduce sus 94 instrucciones originales. La comprobación de almacenamiento confirma 512 bits FF de RAM en A y 4608 bits reescribibles en B. El primer mapeo GF180 y floorplan A/B están completados y pasó una prueba funcional con celdas GF180. El timing previo a colocación no cierra; barridos físicos, Fmax y signoff siguen pendientes. Ver [Mapeo y floorplan](docs/Mapeo_Floorplan.md). La prueba física ya completada corresponde exclusivamente al ejemplo oficial spm.

## Archivos

- `baseline/proyecto2`: copia del código FPGA. Su único cambio funcional de preparación es usar `sw/game.hex` en lugar de una ruta absoluta de Windows.
- `sim/tb_proyecto2_startup.v`: prueba de carga, reset, PC, LED y contador del arranque FPGA.
- `scripts/check_baseline.py`: regeneración del programa y simulación con un modelo iCE40 oficial de Yosys.
- `docs`: cuadernos de estudio y continuidad, y checklist.
- `evidence`: resultados y huellas del original.
- `rtl`: interfaz ASIC, memorias A/B, ROM de producción generada, reset, sincronización de botones, RF portable y pipeline/periféricos conservados.
- `firmware/asic/game.s`: copia ASIC a 10 MHz; no modifica el programa original.
- `sim/asic_stage3`: pruebas de temporización, perfiles y juego antes/después de síntesis.
- `config/rtl_asic.f`: manifiesto completo; asic_top.MemoryVariant=0 selecciona A y 1 selecciona B.
- `config/rtl_stage1.f`: subconjunto de regresión para aislar la memoria de simulación de la primera etapa.
- `sim/asic_stage1` y `scripts/check_asic_stage1.py`: pruebas de la primera adaptación.

## Verificación local

Ejecutar `python3 scripts/check_baseline.py --ice40-model RUTA_AL_MODELO_CELLS_SIM_V` desde esta carpeta. El modelo puede obtenerse de `share/yosys/ice40/cells_sim.v` de OSS CAD Suite o Yosys. La prueba utiliza Icarus Verilog y crea sus salidas en `build/baseline`.

En la referencia FPGA, el archivo contiene 94 palabras para una memoria de 512; su prueba de arranque comprueba las instrucciones utilizadas. La implementación ASIC actual tiene 95 palabras de programa y 33 NOP explícitos en una ROM128; sus rondas se verifican con los comandos del informe del juego.

Consultar `docs/Checklist.md` para los pasos pendientes. No ejecutar el Makefile FPGA por defecto: su destino final intenta programar la placa.

## LibreLane mediante Docker

Docker Desktop debe estar iniciado. Ejecutar `python3 scripts/run_librelane.py --pdk gf180mcuD --scl gf180mcu_fd_sc_mcu7t5v0 ruta/relativa/config.yaml` desde el proyecto. El lanzador utiliza la imagen ARM64 fijada en config/environment.lock.json y monta esta carpeta como /work, evitando problemas con espacios en las rutas del Mac.

El ejemplo oficial de prueba está en build/environment/spm. Se ejecuta con sus propios parámetros de 24 ns y 38 por ciento de utilización; es una comprobación del entorno, separada de la implementación ASIC del Proyecto 3.

La prueba del entorno terminó con cero errores de Magic DRC, LVS y antena. KLayout DRC se omitió por falta de configuración del PDK. Consultar evidence/gf180_environment_summary.json para los resultados y límites de esa prueba.

## Documentación y enunciado

Los cuadernos principales integran las etapas 1 a 5 y las verificaciones del Mac. docs/Requisitos_Proyecto3.md relaciona las exigencias con la evidencia pendiente. Los originales y el kit recuperado están en docs/referencias. Entrega y defensa: 4 de noviembre de 2026, 10:30.


## Adaptación RTL de la primera etapa

Ejecutar `python3 scripts/check_asic_stage1.py --ice40-model RUTA_AL_MODELO_CELLS_SIM_V`. Comprueba RF, reset, botones, reinicios, MMIO, display, SPI y los primeros 10000 ciclos del juego frente al RF original. Usa una memoria exclusivamente de simulación; no constituye una implementación de A/B ni equivalencia post-síntesis. Los resultados están en `evidence/asic_stage1` y el detalle en [Adaptación RTL](docs/Adaptacion_RTL_Etapa1.md).

La comprobación genérica `python3 scripts/check_asic_stage1_synthesis.py` pasó para los cuatro bloques, con Yosys 0.62 de la imagen fijada. No descarga imágenes ni ejecuta el flujo físico; utiliza red deshabilitada. `evidence/asic_stage1_synthesis` conserva logs, scripts de síntesis, conteos y huellas. Estos conteos son de lógica genérica, no área ni celdas GF180 mapeadas.


## Memorias A/B y firmware vigente

El [informe histórico de memorias](docs/Memorias_AB.md) conserva la etapa del commit d867d61. El [informe actual del juego](docs/Juego_10MHz.md) documenta firmware, perfiles, pruebas y resultados vigentes.

Regenerar la ROM de producción con `python3 scripts/generate_asic_memory.py`; comprobar sus archivos con `python3 scripts/generate_asic_memory.py --check`. El origen predeterminado es `firmware/asic/game.s`, con 30 000 000 ciclos de espera y 1 000 000 por décima. El assembler original permanece sin modificaciones.

Ejecutar `python3 scripts/check_asic_memories.py`, `python3 scripts/check_asic_memory_synthesis.py` y `python3 scripts/check_memory_netlist.py` para validar interfaces, integración y almacenamiento. La primera orden incluye nueve pruebas del generador. Estas regresiones también pasaron con el firmware recalibrado; la evidencia preservada está en [evidence/asic_game](evidence/asic_game/README.md).

## Juego y comparación post-síntesis

```sh
python3 -m unittest discover -s sim/asic_stage3 -p 'test_generate_game_firmware.py' -v
python3 scripts/check_game_timing.py
python3 scripts/check_full_game.py
python3 scripts/check_game_wait_only.py
```

El generador de perfiles pasó seis pruebas. El ensayo temporal comprueba código máquina y 20 casos dirigidos con la ALU de Espino: reproduce dos fallos del límite absoluto anterior y ninguno con tiempo transcurrido. La partida completa cubre diez aciertos, dos errores, botón mantenido, saturación, promedio y resets. Usa un perfil con ambos umbrales divididos por 10 000. La prueba `wait_only` conserva la décima de producción y acelera solo la espera, para comprobar la sección 3.7.

Ambas pruebas de juego sintetizan y comparan A/B con estímulos idénticos por ciclo. Requieren Python, Icarus y Docker Desktop con la imagen fijada en `config/environment.lock.json`; no descargan imágenes ni usan red dentro del contenedor. La opción `--rtl-only` permite ejecutar únicamente la parte RTL y no demuestra comparación post-síntesis. Los artefactos de trabajo se generan en `build`, y las evidencias seleccionadas incluyen huellas, logs y resultados.

Son netlists del macro completo con celdas genéricas, sin mapeo GF180 ni SDF. Debe repetirse la comprobación tras el mapeo del flujo final. La configuración final exigida es 100 ns y 40 %; sus restricciones, barridos, mejora de ruta crítica y cierre físico son el siguiente bloque de trabajo.
