# Proyecto 3 — Especificación de adaptación integral de FPGA a ASIC (Etapa 4)

**Fecha:** 29 de octubre de 2026.  
**Estado:** diseño técnico establecido sobre el ZIP ORIGINAL del Proyecto 2; **NO implementado, compilado, simulado ni sintetizado aún**.  
**Fuentes directas:** `Proyecto2-Arqui-main.zip`, `Proyecto_3_arquitectura.pdf` (secciones 3.1, 3.3–3.7), `Diseno_Memorias_ASIC_Proyecto3.md`. No se usó cuenta GitHub conectada.

## 0. Decisión arquitectónica central

Construir `asic_top.v` que exponga **puertos lógicos de macro** (no pads ESD, no capacidad física de manejar displays externos). Preservar el camino del procesador, el ensamblador, el mapa MMIO y las latencias originales. Convertir únicamente los elementos FPGA-específicos y añadir un reset ASIC explícito. Instalar A (ROM combinacional + RAM FF) o B (memoria unificada reescribible FF) por selección de **elaboración** en dos corridas separadas. La estrategia B tendrá un cargador secuencial de arranque que inicializa las palabras de programa desde literales generados por el assembler **en hardware**, manteniendo el procesador en reset hasta completar esa carga.

**Regla:** no corregir el supuesto fallo de arranque FPGA ni el error temporal de 85,9 s como parte oculta del port inicial. Conservar una referencia y tratar correcciones funcionales en commits identificados, con pruebas y explicación del efecto sobre ciclos del juego.

## 1. Inventario: pruebas del RTL original y respuesta técnica

| Elemento original | Evidencia en ZIP (líneas de archivo original) | Riesgo ASIC | Acción propuesta y evidencia exigida |
|---|---|---|---|
| `game_top.v` | `rtl/game_top.v:3–41`, ruta `C:/Users/wille/...` en `:18` | Top y rutas de desarrollo asociadas a FPGA/PC | Crear **nuevo** `asic_top.v`. Mantener `game_top.v` como wrapper FPGA de referencia; reemplazar rutas absolutas en copia portable. Guardar diff. |
| Reset POR dependiente de valor inicial | `rtl/pochoco_soc.v:34–40`: `reg [3:0] por_cnt = 4'b0` | No puede suponerse estado de encendido determinista de FF ASIC sin reset externo | Quitar POR de `pochoco_soc` ASIC; entrada externa `rst_ni`. Sincronizar **desaserción** y coordinar arranque. Mantener lógica POR antigua solo en wrapper FPGA aislado si se sigue compilando como referencia. |
| BRAM en register file | `rtl/espino_core/espino_register_file.v:11–71`: dos `espino_regbank32`, cada uno con dos `SB_RAM40_4K` | Celda específica Lattice, no existe en GF180MCU | Implementación con FF/celdas estándar, **2 puertos de lectura síncronos, 1 de escritura**. Mantener instancia del core `u_rf`; registros x0–x15, x0 siempre cero. Verificar colisiones. |
| Inicialización de memoria | `rtl/pochoco_ram.v:31–55`: `initial/$readmemh`, 512 palabras en SoC | Archivo externo no aparece al encender ASIC | Sustituir por alternativas A/B según `Diseno_Memorias_ASIC_Proyecto3.md`. Ningún `readmemh/initial` como requisito de encendido en jerarquía ASIC. |
| Tiempo y registros de periférico | `rtl/pochoco_periph.v:31–55`: `cycles_q` 32 bit + LEDs/digits | Un reset tardío puede desplazar cronómetro; si cambia reloj, constantes `game.s` quedan erróneas | Reset periférico y contador ligado a liberación de CPU. Conservar el contador 32 bits y MMIO para baseline. Reensamblar para 10 MHz final. |
| Botones asíncronos | `rtl/pochoco_periph.v:88–99`: `btn_i` muestreado directo en lectura MMIO | Metastabilidad, transiciones próximas al reloj y rebote | Insertar sincronizador de 2 FF por botón en frontera del macro, con reset a cero. **No añadir debounce automáticamente** (cambia la semántica temporal). Medir latencia visible frente al FPGA. |
| SPI externo | `rtl/pochoco_spi_slave.v:40–57` sincroniza SCLK/MOSI/CS con cadenas de 3 FF | Se debe respetar dominio y tasa SPI y definir STA | Conservar sincronizadores y lógica; mantener SPI lento frente a reloj de macro. Verificar SPI funcional si se utiliza; documentar que es un módulo marcado *work in progress* en fuente. |
| Displays 7 segmentos | `rtl/pochoco_soc.v:136–140`: inversión `~seg` porque la placa es active-low | Convención eléctrica específica de Go Board | Para `asic_top`, exponer preferentemente bits de segmentos **lógicos activos en 1** (`seg1_o[6:0]`,`seg2_o[6:0]`, bit A=0, G=6). Parametrizar polaridad o usar frontera separada; `game_top` FPGA conserva señales originales active-low. Verificar byte BCD y polaridades en TB. |
| Bitstream / pines | `pochoco_soc-main/Makefile:11–42` usa `synth_ice40`, `nextpnr-ice40`, `icepack`, `iceprog`; `goboard.pcf` fija pines | No aplica a macro ASIC | Crear directorio `asic/` y configuración LibreLane independiente. No incluir PCF ni flujo FPGA en síntesis ASIC. |
| Jerarquía para defensa | `espino_core.v:49,61,89,101`: `u_if`,`u_id`,`u_rf`,`u_lsu`; `espino_id_stage.v:115`: `u_alu`; `pochoco_soc.v:105`: `u_periph`, contador `cycles_q` | Flatten elimina la trazabilidad y áreas por módulo | Capturar estadísticas jerárquicas antes de flatten y mapeo a celdas; preservar nombres cuando sea posible. Anotar captura en layout siguiendo método documentado. |

**Obligación de la pauta 3.1:** para cada problema, el informe debe aportar el warning/error de LibreLane con **archivo de log y línea** si lo emite. Si no lo emite, explicar por qué el constructo no es físicamente válido aun si el flujo no advierte. No inventar logs. La tabla anterior es la auditoría previa, **no evidencia de log**.

## 2. `asic_top`: contrato lógico elegido

Interfaz sugerida; los nombres pueden ajustarse al integrarla con `pochoco_soc`, pero deben quedar fijos después de la primera compilación:

```verilog
module asic_top (
  input  wire       clk_i,
  input  wire       rst_ni,            // activo bajo externo, no POR artificial
  input  wire [3:0] btn_i,             // uno por botón, activo alto lógico
  output wire [3:0] leds_o,
  output wire [6:0] seg1_o,            // activos altos lógicos, bits A..G
  output wire [6:0] seg2_o,
  input  wire       spi_sclk_i,
  input  wire       spi_mosi_i,
  input  wire       spi_cs_n_i,
  output wire       spi_miso_o
);
  // frontera de reset, sincronización, instanciación SoC
endmodule
```

**Estos puertos NO representan pads de chip.** Excluyen ESD, buffers de alta corriente, oscilador, alimentación física de pads y encapsulado, como indica el enunciado. La inversión original de display solo corresponde al wrapper de FPGA, no a la representación lógica del macro, y debe verificarse. **No colocar resistencias/pull-ups ni comportamiento analógico de la placa dentro del RTL**.

### Ubicación racional de terminales para floorplan (propuesta, no layout conseguido)

- Agrupar `clk_i`, `rst_ni` cerca del borde asignado a control para evitar cruces innecesarios; escoger borde definitivo según placer/CTS, no anticiparlo arbitrariamente.
- Agrupar `btn_i[3:0]` como entradas y `leds_o[3:0]`, `seg1_o`,`seg2_o` como salidas para mantener conexiones periféricas localizadas.
- Agrupar `spi_sclk_i`, `spi_mosi_i`, `spi_cs_n_i`, `spi_miso_o` porque son señales de una interfaz común.
- La elección de lados/pin order queda **por justificar con capturas y efectos de congestión** durante las corridas. No confundir terminal del macro con pad I/O.

## 3. Estrategia de reset y secuencia de encendido

### 3.1 Señales separadas

1. `rst_ni`: entrada externa activa baja, **aserción asíncrona**. Las estructuras secuenciales cuya tecnología lo permita deben conservar el estado de reset definido.
2. `rst_sync_ni`: versión con **liberación sincronizada** al reloj (sincronizador de al menos dos etapas con reset asíncrono en sus FF) para evitar liberar lógica a mitad de un ciclo.
3. `mem_boot_done`: en A vale 1 cuando se ha completado la preparación de la memoria; en B sube solo al finalizar la carga sintetizable de sus 144 palabras.
4. `core_rst_ni`: habilitación/reset del core y periféricos derivado de reset sincronizado y **registro de liberación** tras `mem_boot_done`. Debe ser una señal sin glitches; revisar recovery/removal, y validar que no haya ciclo con fetch antes de memoria lista.

**Evitar bloqueo circular:** el controlador de carga de B NO puede estar reseteado por `core_rst_ni`, porque necesita funcionar mientras el core permanece detenido. Usar `rst_sync_ni` para el controlador; `core_rst_ni` solo para CPU/periféricos y sus registros de estado. En reset externo sucesivo, B debe regenerar el programa y limpiar datos antes de liberar CPU. El `cycles_q` de `u_periph` se mantiene en cero mientras CPU esté en reset; por ello el cronómetro del juego no cuenta ciclos de carga inicial.

### 3.2 Carga secuencial de memoria B — decisión de diseño refinada

**Antes** se propuso cargar miles de flip-flops simultáneamente en un reset. **Revisamos esa propuesta**: preferimos un controlador secuencial sintetizable que escribe una palabra en cada flanco durante 144 ciclos (o más si el controlador lo necesita). El proceso de síntesis no necesita miles de entradas de reset directas para inicializar `mem_ff`.

- Contador interno `boot_index`, recorrido 0..143. Cada ciclo se escribe `mem_ff[boot_index] <= boot_word(boot_index)`; `boot_word` se genera automáticamente desde las 94 palabras de `game.s`/assembler, con NOP para posiciones 94..127 y cero para datos 128..143. Debe comprobarse que el decoder realmente considere NOP el valor elegido.
- Durante boot, el puerto de escritura normal CPU está deshabilitado; lecturas de la CPU no se usan porque su reset sigue activo.
- Finalizar y registrar `mem_boot_done`. Liberar el core **después**, en fase sincronizada. El programa NO depende de `$readmemh` en tiempo de arranque.
- El contenido de la memoria B debe ser **verdaderamente reescribible** por el puerto de datos para que Yosys no optimice las instrucciones a constantes. Test específico: escribir en palabra de programa, comprobar lectura posterior, activar reset, comprobar restauración.
- Riesgo: controlador, muxes, prioridades y almacenamiento FF pueden ocupar área elevada. **No afirmar área menor/superior sin síntesis**.
- Capacidad provisional B: 144×32=4.608 bits de arreglo; un boot nominal de 144 ciclos equivale a **14,4 µs a 100 ns** por ciclo, antes de sincronización y liberación del core; cifra de diseño, no dato medido de corrida.

La variante A no necesita esa carga de 144 ciclos; para testbenches se alinearán los estímulos a `core_rst_ni` (inicio de ejecución), **no a un tiempo absoluto común desde reset externo**. La comparación post-síntesis requerida es A-RTL vs A-netlist y B-RTL vs B-netlist, con estímulos aplicados en iguales ciclos relativos a cada variante. Registrar además que A/B tienen distintas latencias de arranque, sin ocultarlas.

### 3.3 Register file: reset separado de la carga de B

Propuesta base: 16 registros lógicos RV32E x0..x15, escritos x1..x15. x0 siempre 32'h0 en cualquier lectura, aun si memoria RAM de FPGA original no garantizaba estado físico de x0. Resetear determinísticamente x1..x15 y registros de lectura (si no eleva excesivamente el costo). **Verificar** que la escritura y lectura simultáneas de misma dirección coincidan con la semántica observada de `SB_RAM40_4K` con `READ_MODE(0), WRITE_MODE(0)`. La implementación con FF puede usar 15×32=480 FF para registros útiles (sin contar 2×32 salidas registradas), no 16×32 si x0 se cablea como cero. Son **bits lógicos estimados**, no FF finales mapeados.

No cambiar `espino_id_stage.v:60–68` (`ops_valid_q`) sin test ciclo a ciclo; el controlador espera que los operandos sean válidos tras una lectura síncrona. No añadir forwarding ni pipeline por comodidad.

## 4. Restricciones físicas y de timing propuestas

- Configurar `DESIGN_NAME = asic_top`, `CLOCK_PORT = clk_i`, `CLOCK_PERIOD = 100` ns, `FP_CORE_UTIL = 40` en el flujo base; usar `gf180mcuD` como **variante PDK propuesta** si la distribución instalada es compatible, y **registrar** SCL real (7/9 tracks, por ejemplo), revisión exacta PDK y LibreLane. **No dar por instalada una versión específica.**
- Usar **un listado explícito** de `VERILOG_FILES` que incluya el top ASIC, SoC, core, periféricos, SPI, memoria A *o* B y módulos generados. No incluir por accidente `game_top.v` ni primitivas de FPGA.
- Proveer restricciones de entrada y salida razonables (drivers, delays, carga estimada) mediante configuración/SDC. Los puertos no son pads, pero sí deben modelarse los límites temporales del macro. Los sincronizadores SPI y botones cruzan desde señales externas asíncronas: identificar los *primeros* FF de sincronización y su política STA; **no declarar falsos todos los caminos externos para lograr cierre artificial**.
- Medir setup y hold en corners típico y más lento (y los exigidos por configuración). `WNS >= 0`, `TNS = 0` para ambos tipos. Registrar si una declaración de excepción de timing es usada y justificarla.
- Para la búsqueda de Fmax, probar al menos tres valores `CLOCK_PERIOD` incluyendo 100 ns; cada valor puede producir nueva síntesis/ubicación/área. Para la prueba de funcionamiento de tres segundos en 10 MHz, regenerar `game.s` con 30.000.000 ciclos de espera y 1.000.000 ciclos por décima. No confundir Fmax con frecuencia **elegida** del juego. Si el periodo de una exploración se cambia, las constantes no representan tres segundos físicos en esa corrida (salvo que se regenere programa).
- El plan de pin order/PDN/floorplan debe ser medido con al menos tres valores de utilización (o dimensiones DIE_AREA); conservar capturas, logs, violaciones y método de cálculo de costo con US$23.000/mm².

**Referencias oficiales para configuración (consultadas en octubre de 2026):** https://librelane.readthedocs.io/en/stable/reference/configuration.html, https://librelane.readthedocs.io/en/latest/usage/about_pdks.html, https://librelane.readthedocs.io/en/stable/usage/timing_closure/index.html. La documentación confirma los campos de configuración y que STA puede requerir SDC personalizado. Consultar el comando/versión concretos instalados antes de generar scripts finales.

## 5. Especificación por archivo / alcance de Codex

| Archivo destino tentativo | Trabajo | ¿Modificar original P2? |
|---|---|---|
| `rtl/asic/asic_top.v` | Crear nuevo macro top, puertos lógicos, conexión con reset y botones sincronizados | NO |
| `rtl/asic/reset_ctrl.v` | Generar sincronizador de liberación y core reset por boot readiness | NO |
| `rtl/asic/btn_sync.v` | 2 FF por entrada, reset a cero, sin debounce | NO |
| `rtl/pochoco_soc.v` (copia P3) | Añadir `rst_ni` externo, selección A/B por parámetro/generate, polaridad de segmentos configurable | Solo copia P3 |
| `rtl/espino_core/espino_register_file.v` (copia P3) | Reemplazar `SB_RAM40_4K` por FF con 2 lecturas síncronas | Solo copia P3 |
| `rtl/asic/memory_a.v` | ROM case + RAM FF 128/16, lecturas de un ciclo | Nuevo |
| `rtl/asic/memory_b.v` | Arreglo FF unificado 144 palabras, boot controlador, escritura por bytes | Nuevo |
| `rtl/asic/generated/*.v` | Generación automática de literales desde `game.s` | Nuevo generado |
| `scripts/generate_asic_memory.py` | Ejecutar assembler/parsear hex; emitir ROM A y boot B desde idénticas instrucciones | Nuevo |
| `asic/config_a.json`, `asic/config_b.json` | LibreLane configurado con misma PDK/SCL/timing/ocupación salvo top/variante específica | Nuevo |
| `testbench/*` | Validación reset, RF, memorias, SPI/LED/display, equivalencia por ciclos | Nuevo |
| `docs/*` | Informe de evidencia + cuaderno de estudio + continuidad | Nuevo |

Puede mantenerse inicialmente estructura interna `pochoco_soc-main/rtl`; reorganizar solo cuando las pruebas de portabilidad funcionen. Preservar encabezados de licencia y atribuciones del código original.

## 6. Criterios de aceptación antes de iniciar corridas ASIC grandes

1. **Lint/elaboración** del nuevo top: sin celdas sin definir ni `SB_RAM40_4K` en el alcance de síntesis ASIC; sin `initial/$readmemh` como dependencia de arranque; no se incluye `game_top` FPGA.
2. **Arranque/reset repetido:** A y B ponen registro LED/display/counter a estado conocido; B no presenta fetch antes de `mem_boot_done`; en cada nuevo reset B vuelve a cargar las instrucciones correctas; primera lectura de instrucción del core en 0x0.
3. **Banco de registros:** x0=0; escrituras en x1–x15, dos lecturas síncronas, comportamiento de colisión documentado, latencia de un ciclo; test del stall de `ops_valid_q`.
4. **Memoria A:** salida de ROM registrada, 94 instrucciones coincidentes con hex, 16 palabras RAM por byte, rango/alineación, read-first donde corresponda.
5. **Memoria B:** 144 posiciones de FF **comprobadas en netlist**, boot determinista, lectura de programa registrada, escrituras operativas en programa y datos y reset de restauración.
6. **Periféricos:** MMIO inalterado: `0x80000000` display; `+4` LEDs; `+8` botones; `+12` ciclos; SPI en ventana `0x80010000`. Confirmar display activo alto en `asic_top` y activo bajo en legacy FPGA.
7. **Equivalencia funcional:** ejecutar juego de referencia y A/B con estímulos definidos en ciclos; registrar diferencias de latencia por sincronización de botones; comparar **cada variante** RTL versus netlist post-síntesis en los mismos ciclos.
8. **Trazabilidad síntesis:** conservar jerarquía o método para asignar celdas/área a `u_rf`, `u_id.u_alu`, `u_periph.cycles_q`. Capturas de layout cuando exista.
9. **Documentación 3.1:** conservar logs reales de incompatibilidad y líneas, o justificar expresamente el silencio del flujo si un constructo no emite warning.
10. **Sin afirmaciones prematuras:** no indicar que el GDSII, DRC, LVS o setup/hold estén aprobados hasta tener reportes verificables.

## 7. Riesgos que requieren una política explícita

| Riesgo | Política |
|---|---|
| Cambiar simultáneamente reset, RF, memoria y juego dificulta depuración | Commits pequeños por capa, test unitario + integración antes de siguiente modificación |
| Primer intento de RF FF cambia ciclos | Test que compare lectura y RF ready/commit; evaluar semántica read-during-write; documentar cambios necesarios |
| Boot B no inicializa FF reales o es demasiado grande | Analizar FF mapeados y fanout; alternativas solo con evidencia; no sustituir B por ROM encubierta |
| Sincronizador de botón introduce 2 ciclos de desplazamiento | Aplicar el mismo front-end a RTL y post-síntesis; comparar desde flancos definidos; registrar latencia |
| SPI no funciona si SCLK externo demasiado rápido para 10 MHz | Establecer supuesto de frecuencia SPI y verificar en simulación; no asegurar soporte arbitrario |
| Reset externamente no disponible en juego original | En ASIC es **puerto lógico explícito**, no pad físico, y habrá reset controlado de testbench |
| Optimización aplana RF/ALU/contador | Reportar estadística jerárquica previa, nombres rastreables o reporte de mapeo de células por instancia |
| El usuario quiere completar en 29–30 oct. | Priorizar baseline verificable (GDSII A) antes de optimizar; sin omitir comparación B ni tests exigidos |

## 8. Resultado final de esta etapa y próxima

**Entregado aquí:** especificación de interfaces, secuencia de reset, nueva inicialización B, trazabilidad por archivos, restricciones y criterios de aceptación. **No entregado aún:** `asic_top.v` funcionando, testbench, configuración libre de errores, síntesis, GDSII o métricas medidas.

**Próxima etapa de la lista «ahora»:** diseñar la matriz concreta de pruebas/experimentos para cubrir la rúbrica, y después redactar los prompts de Codex con límites de edición, comandos y salidas exigidas. Al pasar al Mac, comenzar por portátil + tests baseline + contenedor LibreLane GF180.
