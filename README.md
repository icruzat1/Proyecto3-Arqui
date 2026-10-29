# Proyecto 3 de Arquitectura de Computadores

Adaptación ASIC del procesador Espino y del juego del Proyecto 2, con LibreLane y GF180MCU. El desarrollo conserva el Proyecto 2 original y utiliza exclusivamente la cuenta personal icruzat1.

## Estado

La base FPGA portable reproduce las 94 instrucciones del juego y supera una simulación de arranque de 2000 ciclos. Docker Desktop funciona en ARM64 y el ejemplo oficial spm completó el flujo GF180MCU con GDS. La primera adaptación RTL de interfaz/reset/RF pasó siete pruebas, incluida una comparación de 10000 ciclos con el RF FPGA. La síntesis genérica de reset, botones, RF y SoC con memoria externa pasó; el RF contiene 544 FF genéricos. Las memorias ASIC A/B, el mapeo a GF180 y la validación física de Espino siguen pendientes.

## Archivos

- `baseline/proyecto2`: copia del código FPGA. Su único cambio funcional de preparación es usar `sw/game.hex` en lugar de una ruta absoluta de Windows.
- `sim/tb_proyecto2_startup.v`: prueba de carga, reset, PC, LED y contador del arranque FPGA.
- `scripts/check_baseline.py`: regeneración del programa y simulación con un modelo iCE40 oficial de Yosys.
- `docs`: cuadernos de estudio y continuidad, y checklist.
- `evidence`: resultados y huellas del original.
- `rtl`: interfaz, reset, sincronización de botones, RF portable y pipeline/periféricos conservados.
- `config/rtl_stage1.f`: fuentes de producción de esta etapa; aún requiere la futura memoria ASIC.
- `sim/asic_stage1` y `scripts/check_asic_stage1.py`: pruebas de la primera adaptación.

## Verificación local

Ejecutar `python3 scripts/check_baseline.py --ice40-model RUTA_AL_MODELO_CELLS_SIM_V` desde esta carpeta. El modelo puede obtenerse de `share/yosys/ice40/cells_sim.v` de OSS CAD Suite o Yosys. La prueba utiliza Icarus Verilog y crea sus salidas en `build/baseline`.

El archivo del programa contiene 94 palabras para una memoria de 512. Icarus informa esa diferencia durante la carga; la prueba de arranque comprueba las instrucciones utilizadas. Todavía falta definir el contenido del resto de la memoria y verificar todas las rondas.

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
