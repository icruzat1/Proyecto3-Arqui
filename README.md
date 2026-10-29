# Proyecto 3 de Arquitectura de Computadores

Adaptación ASIC del procesador Espino y del juego del Proyecto 2, con LibreLane y GF180MCU. El desarrollo conserva el Proyecto 2 original y utiliza exclusivamente la cuenta personal icruzat1.

## Estado

La base FPGA portable reproduce las 94 instrucciones del juego y supera una simulación de arranque de 2000 ciclos. La implementación ASIC y su validación física están pendientes.

## Archivos

- `baseline/proyecto2`: copia del código FPGA. Su único cambio funcional de preparación es usar `sw/game.hex` en lugar de una ruta absoluta de Windows.
- `sim/tb_proyecto2_startup.v`: prueba de carga, reset, PC, LED y contador del arranque FPGA.
- `scripts/check_baseline.py`: regeneración del programa y simulación con un modelo iCE40 oficial de Yosys.
- `docs`: cuadernos de estudio y continuidad, y checklist.
- `evidence`: resultados y huellas del original.
- `rtl` y `config`: destinos para el desarrollo ASIC posterior.

## Verificación local

Ejecutar `python3 scripts/check_baseline.py --ice40-model RUTA_AL_MODELO_CELLS_SIM_V` desde esta carpeta. El modelo puede obtenerse de `share/yosys/ice40/cells_sim.v` de OSS CAD Suite o Yosys. La prueba utiliza Icarus Verilog y crea sus salidas en `build/baseline`.

El archivo del programa contiene 94 palabras para una memoria de 512. Icarus informa esa diferencia durante la carga; la prueba de arranque comprueba las instrucciones utilizadas. Todavía falta definir el contenido del resto de la memoria y verificar todas las rondas.

Consultar `docs/Checklist.md` para los pasos pendientes. No ejecutar el Makefile FPGA por defecto: su destino final intenta programar la placa.
