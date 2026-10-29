# Adaptación RTL a ASIC: primera etapa implementada

Verificación del 29 de octubre de 2026. Alcance: interfaz lógica, reset, botones y banco de registros. Se completó la elaboración y simulación con una memoria de prueba. **Las memorias ASIC A/B todavía no están implementadas; se sintetizaron genéricamente cuatro bloques, incluido el SoC con memoria externa. El macro completo y su implementación física siguen pendientes.**

## Cambios y procedencia

El RTL de desarrollo reside en `rtl`; `baseline/proyecto2` sigue como referencia FPGA. Siete archivos del pipeline Espino, más `pochoco_periph.v` y `pochoco_spi_slave.v`, son copias idénticas byte a byte. El assembler y `game.s` no cambiaron. Se conservaron las licencias y atribuciones. Las 38 huellas del Proyecto 2 original coinciden con las registradas.

| Bloque | Implementación y motivo |
|---|---|
| `rtl/asic/asic_top.v` | Reloj y reset externos; cuatro botones, cuatro LED, dos vectores de siete segmentos y SPI. Terminales lógicos de macro, sin pads. |
| `rtl/asic/reset_ctrl.v` | Aserción asíncrona; liberación del reset de sistema tras dos flancos de muestreo; liberación registrada del core después de disponibilidad de memoria. |
| `rtl/asic/btn_sync.v` | Dos FF por botón, activos altos, sin antirrebote. Se reinician con el reset del sistema, por lo que pueden estabilizarse mientras la memoria se prepara. |
| `rtl/espino_core/espino_register_file.v` | x1–x15 almacenados, x0 constante, dos lecturas síncronas, una escritura. Reset explícito y colisiones con lectura del valor anterior. |
| `rtl/pochoco_soc.v` | Sustituye el POR por entrada de reset. Expone la interfaz de memoria y bloquea solicitudes durante reset. Conserva la decodificación MMIO y su selección registrada. |

El RF tiene 480 bits de almacenamiento y 64 bits de salidas registradas: **544 bits secuenciales lógicos**, confirmados como 480 FF con habilitación y 64 FF de salida en síntesis genérica. No representan celdas GF180 mapeadas. Su reset determinista es una diferencia deliberada: el RF FPGA ignoraba el reset. No se introdujeron forwarding ni cambios en `ops_valid_q` o el pipeline.

El modelo iCE40 de simulación usa lectura síncrona del contenido anterior y escrituras no bloqueantes. La comparación comprueba esa semántica del modelo; no constituye una caracterización física de las colisiones de la FPGA.

## Secuencia de arranque

El entorno debe afirmar `rst_ni` al encender. No se presupone un estado inicial de los FF. El reset sincronizado alimenta al futuro cargador y a los botones. El reset del core alimenta CPU, RF, contador, periféricos y SPI. El cargador no depende del reset del core, evitando una espera circular.

`mem_boot_done` pertenece al dominio de `clk_i`, debe permanecer alto hasta reset y se captura en el registro de liberación. El core comienza en la siguiente arista activa. El contador permanece en cero durante la espera y cuenta desde el primer ciclo de ejecución. La validación física posterior debe revisar distribución del reset, recovery/removal y restricciones de los sincronizadores.

El IF original asigna `instr_req_o = ~stall_i` incluso durante reset. Por eso se inhibe la solicitud en la frontera del SoC, junto con las solicitudes de datos y MMIO. Se verificó que el primer fetch efectivo es la dirección cero y que ninguna solicitud sale durante la preparación.

Los displays del macro son activos altos: bit 0=A y bit 6=G, primer display=nibble alto. El reset muestra **00** (`7'h3f` en cada display), no segmentos apagados. El wrapper FPGA conserva su inversión original.

## Límite de memoria explícito

`asic_top` instancia el contrato `asic_memory`: puerto de instrucciones síncrono habilitado, puerto de datos síncrono, escritura por bytes y señal de disponibilidad. La implementación física se incorpora en la etapa A/B.

Solo para estas pruebas, `sim/asic_stage1/asic_memory.v` proporciona 512 palabras precargadas desde un archivo y una demora artificial de disponibilidad. Es un componente del banco de pruebas, no la memoria ASIC. Reiniciar el modelo reinicia su disponibilidad, **no restaura sus palabras**; estas pruebas no validan la restauración de B. El programa de juego no escribe RAM ordinaria durante el intervalo ensayado.

El manifiesto `config/rtl_stage1.f` enumera exclusivamente producción. Sin una implementación de `asic_memory`, elaborar el top falla expresamente; añadir el modelo de simulación sin `ASIC_STAGE1_SIM` también falla. Ambas protecciones se comprueban automáticamente. No hay `initial`, `$readmemh` ni primitivas `SB_*` en los fuentes de producción de esta etapa.

## Evidencia de simulación

Resultados y huellas de los archivos ensayados: [results.json](../evidence/asic_stage1/results.json). Todos los logs están en [evidence/asic_stage1](../evidence/asic_stage1).

| Prueba | Resultado medido |
|---|---|
| RF y modelo independiente | 1903 ciclos; todos los registros y las 256 combinaciones de direcciones de lectura. |
| RF frente al original iCE40 | 1872 comparaciones; 102 colisiones en A, 93 en B, 51 intentos de escritura en x0 en el ensayo completo. Se excluyen 31 ciclos de reset y realineación del original. |
| Reset y botones | 73 comprobaciones en 54 flancos; reloj detenido, pulsos de reset sin reloj, liberación exacta, interrupción del arranque y latencia de botones. |
| Top con tres demoras de memoria | Parámetro artificial 0, 5 y 144; dos ejecuciones de 2000 ciclos por caso, seis arranques efectivos en total. Reset durante sincronización, preparación y ejecución; primer fetch=0 y contador alineado. |
| Diagnóstico de entradas y salidas | CPU escribe display A5 y LED A; lee botones 5 y contador; comprueba rutas de RAM y MMIO. Transferencia SPI completa: recibe 3C y transmite 96, con semiperíodo de diez ciclos del core. |
| Comparación de pipeline | 10000 ciclos del juego original, 2505 ciclos con escritura RF, 1247 con solicitud de lectura y dos con solicitud de escritura; sin diferencias. Se rechazan valores desconocidos en control y datos válidos. |

Son **siete ejecuciones de prueba** más las comprobaciones estáticas y de protección de memoria. Las cifras de solicitudes indican ciclos de señal activa, no necesariamente instrucciones retiradas.

La comparación de pipeline usa el mismo wrapper ASIC y la misma memoria de prueba; cambia el RF por el original iCE40. El resto del pipeline se verifica idéntico al original. Esta prueba aísla la sustitución del RF y su interacción con el controlador: **no es equivalencia post-síntesis ni verificación del juego completo**. Se usa el juego sin recalibrar, dentro de sus primeros 10000 ciclos; no se interpretan sus constantes como tres segundos a 10 MHz.

## Reproducción

Desde la raíz del repositorio:

```sh
python3 scripts/check_asic_stage1.py --ice40-model RUTA_AL_MODELO_CELLS_SIM_V
```

Requiere Python e Icarus Verilog. El modelo corresponde a `share/yosys/ice40/cells_sim.v`; su SHA256 queda registrado. El script usa el assembler original para regenerar las 94 instrucciones, genera las copias de comparación únicamente bajo `build`, y guarda resultados en `build/asic_stage1`. El firmware `sim/asic_stage1/io_diagnostic.s` pertenece exclusivamente a pruebas.

Para reproducir la comprobación genérica de síntesis:

```sh
python3 scripts/check_asic_stage1_synthesis.py
```

Este segundo script necesita acceso al motor local de Docker. Utiliza solo la imagen fijada y ya descargada, con red deshabilitada, y comprueba reset, botones, RF y SoC con memoria externa. No mapea GF180 ni intenta sintetizar el modelo de memoria. **Los cuatro bloques pasaron** después de que el usuario volvió y concedió los accesos pendientes. El bloqueo anterior queda como antecedente en [docker_access_probe.log](../evidence/asic_stage1/docker_access_probe.log).

## Inventario para la sección 3.1 del informe

| Dependencia de la base FPGA | Evidencia fuente | Tratamiento actual / límite |
|---|---|---|
| `SB_RAM40_4K` | `baseline/proyecto2/pochoco_soc-main/rtl/espino_core/espino_register_file.v` | Sustituida por RF portable. Falta conservar diagnóstico del flujo de síntesis, si lo emite. |
| POR por valor inicial de declaración | `baseline/proyecto2/pochoco_soc-main/rtl/pochoco_soc.v`, bloque `por_cnt` | Retirado del SoC ASIC. Aunque una herramienta acepte el valor inicial, no establece por sí mismo un arranque físico determinista. |
| `initial` y `$readmemh` | `baseline/proyecto2/pochoco_soc-main/rtl/pochoco_ram.v` | Excluidos de producción; inicialización real de A/B pendiente. La carga de archivo del testbench no es una solución de silicio. |
| Lectura directa de botones | `baseline/proyecto2/pochoco_soc-main/rtl/pochoco_periph.v` | Frontera de dos FF. Simulación verifica latencia digital, no prueba ausencia física de metastabilidad. |
| Polaridad y pines de placa | `game_top.v`, inversión de segmentos en SoC, `goboard.pcf` | Interfaz lógica activa alta; PCF y flujo FPGA excluidos. |

Los logs de simulación son de Icarus y los nuevos logs de síntesis corresponden a Yosys ejecutado directamente dentro de la imagen fijada de LibreLane. **No son una corrida completa de LibreLane** ni sustituyen sus evidencias finales. La tabla distingue las causas físicas y la evidencia disponible.

## Pendientes y riesgo previo observado

La implementación A/B, su arranque real, la recalibración de `game.s`, las pruebas completas del juego, la equivalencia RTL/netlist y las corridas físicas siguen pendientes. También falta definir las restricciones STA de reset, botones y SPI para el macro completo.

En el SPI original, `byte_done` no está condicionado por `cs_active`. Una transferencia abortada tras siete bits seguida de actividad de reloj podría registrar un byte fuera de selección. Es un riesgo preexistente identificado en lectura del RTL, **todavía no reproducido con un ensayo dirigido**. Se conservó el módulo sin cambios; la prueba actual cubre una transferencia completa y no valida todas las condiciones SPI. Cualquier corrección posterior debe tener prueba y cambio identificables.

## Estado de guardado

El usuario volvió y concedió los accesos pendientes para Docker y Git. La cuenta personal icruzat1 fue comprobada nuevamente en VS Code; todas las publicaciones de esta etapa se realizan mediante esa sesión. Los errores previos de acceso se conservan como antecedentes, no como bloqueos actuales. El historial de main identifica el commit que incorpora esta implementación y sus resultados.


## Resultado de síntesis genérica

[Resultados y procedencia](../evidence/asic_stage1_synthesis/results.json). Herramienta: Yosys 0.62, revisión 7326bb7d6641500ecb285c291a54a662cb1e76cf, informada por el campo creator de los cuatro JSON de netlist. Se usó `synth -noabc` seguido de `check -assert`, sin biblioteca de celdas, restricciones temporales ni flujo físico.

| Bloque sintetizado | Resultado |
|---|---|
| reset_ctrl | 3 FF genéricos; comprobaciones sin problemas. |
| btn_sync | 8 FF genéricos; dos por botón. |
| espino_register_file | 480 FF con habilitación más 64 FF de salida = 544 FF. |
| pochoco_soc | Síntesis con interfaz externa de memoria y jerarquía conservada; comprobaciones sin problemas. |

No se encontraron latches, primitivas SB ni cajas negras en las netlists producidas. La comprobación del SoC no incluye asic_top ni la memoria A/B todavía pendiente. Los conteos agregados del JSON recorren definiciones de módulo; no deben presentarse como un análisis de área física o de instancias repetidas sin recorrer antes la jerarquía.

La única advertencia es la conversión de `regs_q` en una lista de registros, esperada para implementar el RF con FF. Aparece en la línea 52 de [espino_register_file.log](../evidence/asic_stage1_synthesis/espino_register_file.log) y de los otros tres logs, porque se leen todos los fuentes antes de recortar los módulos ajenos al bloque seleccionado. Apunta a `rtl/espino_core/espino_register_file.v:28`. No es un error de memoria ni una inferencia de BRAM.

Esta verificación confirma que los bloques se traducen a lógica genérica sin los problemas estructurales comprobados. No acredita equivalencia RTL/netlist, frecuencia máxima, área GF180, DRC, LVS ni cierre de setup/hold.
