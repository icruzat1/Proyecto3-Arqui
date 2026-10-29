# Proyecto 3 — Plan de pruebas y experimentos (Etapa 5)

**Fecha de diseño:** 29-10-2026. **Estado:** especificación de pruebas **completada**; las pruebas NO se han implementado ni ejecutado. Las cifras de timing/área/FF aún NO están medidas.  
**Base:** `Proyecto2-Arqui-main.zip`, enunciado `Proyecto_3_arquitectura.pdf`, `Diseno_Memorias_ASIC_Proyecto3.md`, `Adaptacion_FPGA_a_ASIC_Proyecto3.md`. No se ha usado GitHub de oficina.

## 1. Principio de verificación

Se congelará la entrega P2 en un directorio `reference/` (o commit de importación) y cada variante ASIC tendrá pruebas automatizadas comparables. Un *PASS* exige una aserción verificable y un log reproducible, no únicamente que termine el simulador. Codex documentará los comandos reales una vez existan y se conozca la versión de herramientas.

**Tres niveles de resultado:** (1) prueba escrita, (2) prueba ejecutada con log y (3) criterio satisfecho. No confundir ninguno de ellos. Si una prueba falla por causa conocida del P2, etiquetar `KNOWN_BASELINE_FAIL`, no silenciarla ni contarla como PASS. Registrar `SKIP_ENV` si el entorno no permite ejecutarla.

## 2. Condiciones comunes y trazabilidad

- **Fuente de verdad:** commit de código, `game.s`, hash `game.hex`, generador, configuración JSON/SDC, versiones LibreLane/Yosys/OpenROAD, revisión GF180MCU, biblioteca de celdas, fecha y plataforma (Mac M4 / Linux contenedor / respaldo).
- **Reloj físico de comparación final:** `CLOCK_PERIOD = 100 ns` (frecuencia nominal de 10 MHz); utilización final `FP_CORE_UTIL = 40%`. Son objetivos del enunciado, no resultados de frecuencia medida.
- **Firmware final a 10 MHz:** 30.000.000 ciclos para 3 s y 1.000.000 para 0,1 s. **Firmware de pruebas aceleradas:** constantes inferiores, idénticas en RTL y post-síntesis, generadas desde fuente parametrizada de forma reproducible; conservar `game.s` final sin alterar sus parámetros por accidente.
- **Convención de ciclo 0 para pruebas ASIC:** primer flanco activo del core después de que `core_rst_ni` se desactive. Para B debe esperar `mem_boot_done`. No comparar marcas temporales absolutas de A/B antes de este evento: el arranque de B tarda más.
- **Una variante por corrida:** A = ROM combinacional generada + RAM FF; B = memoria unificada FF de 144 palabras con inicializador secuencial. Los scripts impedirán mezclar sus fuentes o artefactos.
- **Misma carga de trabajo:** program ROM generado de las mismas 94 instrucciones (o mismo firmware de prueba acelerada), secuencia definida de botones y criterios iguales; registrar cualquier latencia de sincronización.
- **Reset / teclado:** reset activo bajo, aserción asíncrona y liberación sincronizada; los cuatro botones externos pueden ser asíncronos, con sincronizador 2FF. SPI ya dispone de 3FF internos.
- **No inferir resultados:** recuentos de FF, área, WNS/TNS, congestión, DRC/LVS y antena solo desde artefactos de corridas verificables.

## 3. Matriz de pruebas automatizables

| ID | Nivel | Estímulo / preparación | Condición de PASS | Evidencia |
|---|---|---|---|---|
| ENV-01 | Entorno | Registrar herramientas disponibles y `--version`; comprobar contenedor Linux y PDK | Versiones/revisión y SCL registrados; diseño pequeño GF180 completa el flujo | `reports/env/versions.txt`, log smoke test |
| BUILD-01 | Fuente | Elaborar top `asic_top` para A y B, sin hardware FPGA | Ninguna celda indefinida; ninguna referencia a `SB_RAM40_4K` ni archivo de inicio como requisito físico; sin latches inesperados | `reports/lint/{a,b}.log` |
| ASM-01 | Assembler P2 | Ensamblar `assembler/game.s` original | 94 instrucciones, 8 hex dígitos por línea, igualdad byte a byte con `game.hex` entregado | hash, diff y log |
| ASM-02 | Generación ASIC | Generar ROM A y constantes boot B desde un mismo `.hex` | Palabras 0..93 idénticas; posiciones reservadas definidas; generación repetida determinista | hashes, prueba Python |
| ASM-03 | Firmware ASIC | Generar a 10 MHz y versión acelerada | Constantes y formato correctos; fuentes, configuración y hashes identificados | archivos de ensamblado, test de constantes |
| RF-01 | Banco de registros | Leer x0, escribir/leer x1..x15 desde ambos puertos, reset | x0=0; datos coinciden tras latencia síncrona prevista; resultados simétricos entre puertos | `tb_rf`, VCD/CSV |
| RF-02 | Colisiones RF | Lectura y escritura de misma dirección en mismo flanco; stall | Semántica read-during-write definida según referencia o diferencias justificadas; `rf_ready`/`ops_valid_q` sin desalineamiento | trazas por ciclo |
| MEM-A1 | A, ROM | Pedir las 94 palabras (y reservas) con lectura habilitada/deshabilitada | Palabra correcta un ciclo después del pedido; sin cambio indebido cuando `a_req=0`; sin alias fuera de rango | test ROM, VCD |
| MEM-A2 | A, RAM | Escribir 16 palabras usando habilitación por byte; leer simultáneamente | Cada byte seleccionado cambia; lectura síncrona y prioridad de colisión según diseño P2; fuera de rango protegido | test RAM, log |
| MEM-B1 | B, carga | Aplicar reset y contar `boot_index` hasta `mem_boot_done` | CPU retenida durante carga; primer fetch desde PC 0 cuando termina; instrucciones y datos inicializados | VCD boot, log |
| MEM-B2 | B, reescritura | Escribir en palabra de programa y datos, leer, reiniciar | La escritura cambia el **mismo arreglo FF**; tras reset se restablece el programa; confirmar FF tras síntesis | test y `stat` FF real |
| MEM-B3 | B, reset interrumpido | Activar reset a mitad de carga, soltar y repetir | Carga reinicia desde posición inicial y no ejecuta firmware parcial | VCD reset, log |
| MMIO-01 | Periféricos | Acceder a base `0x80000000` y offsets 0,4,8,12 | Displays, LED, botones y contador corresponden; accesos MMIO no contaminan RAM | test periféricos |
| SPI-01 | SPI | Estímulos `SCLK/MOSI/CS` dentro de una frecuencia sustentable por sincronización | Bytes recibidos y status/registro de decisión correctos; anotar límite de SCLK | VCD SPI; test específico |
| GAME-01 | Juego, inicio | Reset repetido, arranque y espera acelerada | LED inicial `0xF`, contador incrementa y luego aparece máscara one-hot; nunca se queda indefinidamente en un estado inesperado | trazas RTL A/B |
| GAME-02 | Ronda correcta | Esperar máscara LED; aplicar botón coincidente en ciclo definido | Medición de tiempo, display BCD, incremento de aciertos y espera de liberación correctos | trazas, eventos MMIO |
| GAME-03 | Ronda incorrecta | Presionar botón distinto al LED; luego liberar | LEDs apagados, display `EE`, no se suma acierto y se repite ronda actual | trazas, eventos MMIO |
| GAME-04 | Pulsaciones | Prueba de botones simultáneos, pulsaciones muy breves y reset mientras están presionados | Respuesta definida y coherente con `game.s`; registrar efecto del sincronizador | tabla de ciclos, VCD |
| GAME-05 | Diez aciertos | Diez rondas correctas con delays deterministas | Promedio final correcto, display estable y lazo `hang`; no nuevos aciertos | CSV de rondas y valor final |
| GAME-06 | Borde temporal | Inyectar/alcanzar contador próximo a 2^31 y 2^32; ejecutar espera | Documentar fallo legado signed si se reproduce; una variante corregida debe aguantar el cruce sin perder duración | log del experimento, cálculo, VCD |
| EQ-01 | RTL vs netlist | Simular `asic_top` A y B post-síntesis **sin SDF** con mismos eventos en ciclos relativos a core listo | En cada variante, coincidencia de ciclos medidos para ronda correcta; error reinicia la ronda; observables iguales o diferencias explicadas | CSV comparado, VCD, comando, simulador |
| EQ-02 | Baseline vs ASIC | Aplicar estímulos equivalentes P2 vs ASIC | Señalar cualquier diferencia intencional debida a reset/sincronizador/boot; no exigir equivalencia temporal absoluta si cambió front-end | tabla de deltas por señal |

**Atención a `RF-02`:** el P2 usa dos bancos duplicados `SB_RAM40_4K` y el `espino_register_file.v` original ignora `rst_ni`; una memoria FF con x0 forzado y reset explícito NO es equivalente bit a bit a RAM indeterminada al encender. Por ello se separan equivalencia observable del juego y garantías nuevas del ASIC.

**Atención a `MEM-A2`:** `pochoco_ram.v` original registra `b_rdata_o` en cada flanco, aun si `b_req_i` es 0 (líneas 47–54). Los tests deben comprobar esa semántica o documentar su cambio, no asumir un enable de lectura inexistente.

**Atención a GAME-06:** el `blt` firmado de `game.s` puede fallar si una espera de 75 M ciclos a 25 MHz cruza 2^31 ≈ 85,899 s; no afirmar causa probada del fallo físico intermitente. Ese bug se prueba como regresión/defecto de referencia, por separado de los requisitos obligatorios.

## 4. Plan experimental de síntesis y diseño físico

| ID | Experimento | Configuración propuesta | Resultado obligatorio | Criterio de cierre |
|---|---|---|---|---|
| SYN-01 | Comparación A/B | Mismo GF180, SCL, 100 ns, 40%, misma carga | Área de celdas, FF reales, utilización, frecuencia máxima de cada variante | Ambos sintetizan; diferencias justificadas por arquitectura |
| SYN-02 | Celdas más frecuentes | Corrida final de la variante seleccionada | Cinco tipos de celdas más usados, cantidad y explicación | Tabla trazada a `stat` y netlist |
| SYN-03 | Área por módulo | RF, ALU, contador, total | Mayor módulo, área y fracción del contador de ciclos | Método trazable aun si Yosys aplana la jerarquía |
| TIM-01 | Barrido CLOCK_PERIOD | Partir en **100, 80 y 60 ns** como sondeo; añadir puntos mayores o intermedios según cierres | Para **cada** período: setup/hold WNS y TNS en corner típico y lento, más corners exigidos | Identificar menor período probado que cierra **todos** los corners; refinar frontera, no asumir que 60 ns cierra |
| TIM-02 | Ruta crítica | Reporte de trayecto de peor slack del diseño seleccionado | Celdas de inicio y fin, módulo y etapa Espino: fetch/decode/execute/memory/writeback | Captura y reporte con identificadores reales |
| TIM-03 | Optimización RTL | Solo una modificación de ruta crítica, comparada con baseline | Nuevo slack, área y explicación, mejore o empeore | Ambas corridas comparables, mismo PDK/SCL/corners y período |
| TIM-04 | Constantes de 3 s y décimas | `CLOCK_PERIOD = 100 ns`, firmware final | 30 M ciclos / 3 s y 1 M ciclos / 0,1 s, assembler regenerado | Fuente y hex verificables, cálculo en PDF |
| PHY-01 | Floorplan y congestión | **30%, 40%, 50%** de FP_CORE_UTIL (ampliar si falla) | Área física DIE/CORE, utilización real, congestión o número de violaciones por corrida | Al menos 3 configuraciones y gráfico solicitado |
| PHY-02 | Área mínima | Refinar alrededor del menor floorplan exitoso | Dimensión/área mínima **probada** que completa flujo, no mínimo matemático | Mismos criterios que signoff y timing |
| PHY-03 | Terminales y PDN | Macro sin pads I/O | Justificación de distribución de terminales; mapa PDN y capturas | Terminales señalados vs pads hipotéticos |
| PHY-04 | Costo de silicio | Área del diseño en mm² y US$23.000/mm² | Costo equivalente + límites del supuesto lineal | `costo_USD = area_mm2 * 23000`; explicar qué área se usó |
| SIGN-01 | DRC/LVS/antena | Corrida final de LibreLane | DRC 0, LVS 0; antena 0 o cada violación justificada con evidencia | No declarar final si DRC o LVS distinto de 0 |
| SIGN-02 | Historial de violación | Una violación observada durante el desarrollo, **si ocurrió** | Ubicación, captura, causa y resolución | Evidencia del caso, nunca inventarlo; si ninguna apareció, declarar eso |
| LAY-01 | Layout anotado | KLayout u OpenROAD GUI | Ubicar RF, ALU y contador por jerarquía o mapeo | Tres capturas anotadas y método de trazabilidad |
| RPT-01 | README reproducible | Commits y artefactos finales | Instalación, corrida final, regeneración `game.s`, versiones LibreLane/PDK/SCL | Otra persona puede seguir pasos sin rutas personales |
| RPT-02 | Logs FPGA incompatibles | Corrida de diagnóstico o referencia | Warning/error real + archivo + línea para cada dependencia; si no existe, explicar por qué era problema físico | Nunca inventar un warning ni referir una ruta inexistente |

### Precisión en mediciones de timing

El enunciado pide **WNS >= 0 y TNS = 0 tanto para setup como para hold en corners exigidos**. El período usado en el barrido puede cambiar las decisiones de síntesis, buffering y placement, así como el área, por lo que no basta extrapolar `Fmax = 1/T` desde una corrida sin probar ese período.

**Frecuencia máxima informada:** `Fmax = 1 / T_min_que_cierra_todos_los_corners` (si T en ns, `Fmax_MHz = 1000 / T_ns`). Si la frontera se sondea discretamente, describir como «frecuencia máxima observada entre los períodos probados», no óptimo absoluto demostrado. No inferir timing de RTL simulación.

**La métrica de área debe etiquetarse:** área de celdas (`um²`), área de core/die (`um²` o `mm²`), objetivo de utilización y utilización real. Para el ejercicio de costo declarar expresamente si el cálculo se realizó sobre `DIE_AREA` o `CORE_AREA`; no usar el área de celdas como si equivaliera directamente al chip físico.

### Captura de evidencia para una corrida

Cada corrida tendrá carpeta propia `reports/runs/<id>/` con:

- `manifest.json`: `git_commit`, variante A/B, fecha, comando, versión de herramienta, PDK revision, SCL, clock_ns, fp_core_util, corners, hash de firmware y definición de SDC.
- `synthesis/`: netlist, `stat` por tipo y por instancia/jerarquía, célula/FF/área.
- `timing/`: setup y hold WNS/TNS por corner, ruta crítica y excepción SDC si existe.
- `physical/`: floorplan, congestión, área efectiva, pin layout, PDN, capturas.
- `signoff/`: reporte DRC, LVS, antena y GDSII verificado.
- `functional/`: logs/VCD/CSV de prueba RTL y netlist, observables alineados por ciclo.

Evitar versionar archivos temporales voluminosos innecesariamente; **sí** conservar extractos auditables, script generador, métricas resumidas, configuraciones y referencia/hash a artefactos pesados.

## 5. Plantillas de resultados (sin datos inventados)

Archivo `reports/experiments.csv` a poblar al correr:

```csv
run_id,commit,variant,librelane_version,pdk_rev,scl,clock_ns,fp_core_util,corner,setup_wns_ns,setup_tns_ns,hold_wns_ns,hold_tns_ns,cell_area_um2,ff_count,core_area_um2,die_area_um2,congestion_metric,drc_errors,lvs_errors,antenna_violations,flow_complete,notes
```

Archivo `reports/tests.csv` a poblar:

```csv
case_id,variant,rtl_or_netlist,firmware_hash,run_id,cycle_zero_definition,result,log_path,wave_path,notes
```

## 6. Secuencia para Codex / Mac

1. **Previo a cambios RTL:** implementar y correr ASM-01 y una simulación baseline de P2 (si falta modelo `SB_RAM40_4K`, identificarlo, no disfrazar con equivalencia no probada).
2. **Adaptación por componentes:** RF-01/02; MEM-A1/02; MEM-B1/02/03; BUILD-01; MMIO-01; SPI-01.
3. **Integración juego:** GAME-01..05 con firmware acelerado, luego GAME-06 diagnóstico; registrar ciclo 0 con core listo. Nada de corregir silenciosamente el juego entregado.
4. **Primera implementación física A:** smoke test de LibreLane GF180, síntesis, corrida con período 100 ns/core 40%, registrar errores. **Asegurar cierre real** antes de grandes barridos.
5. **Implementación B y comparación:** misma versión/PDK/SCL y equivalencia funcional, analizar FF reales y área; no sustituir B por ROM fija.
6. **Exploración completa:** SYN/TIM/PHY/SIGN/LAY y optimización de ruta crítica, capturas y tablas.
7. **Post-síntesis obligatoria:** EQ-01 por variante, firmware idéntico y botón aplicado en mismos ciclos; no requiere SDF.
8. **Informe/defensa:** llenar las plantillas desde logs, adjuntar evidencia y actualizar `Cuaderno_Proyecto3_Acumulativo.md` y `Cuaderno_Continuidad_Proyecto3.md` después de cada fase.

## 7. Puertas de control de riesgos

- Si **RF-02 falla**, detener integración CPU: puede existir desfase de operandos/pipeline. Buscar causa por ciclo, no compensar con sleeps arbitrarios.
- Si **MEM-B1 falla**, CPU B debe permanecer en reset (nunca ejecutar código parcialmente cargado).
- Si **MEM-B2 falla**, la variante B podría no cumplir «unificada FF»; corregir inferencia antes de comparar área/Fmax.
- Si **GAME-01 falla**, inspeccionar core ready, PC, `instr_rdata`, MMIO, reset, RF y sincronizador; no atribuir automáticamente a placa FPGA.
- Si **EQ-01 falla**, conservar primer ciclo de discrepancia en VCD y comparar fetch/ALU/register file/MMIO. Una corrida física «sin DRC» no valida funcionalidad.
- Si **SIGN-01 falla**, el GDSII generado no cumple cierre final; registrar violaciones y plan de corrección.

## 8. Estado y siguiente paso

La matriz de pruebas y experimentos está **diseñada y documentada**. No se han ejecutado simulaciones, síntesis ni el flujo LibreLane. Siguiente tarea de la lista «AHORA»: **preparar prompts de Codex por fases, listos para ejecutar cuando el usuario esté en su Mac**, respetando separación de GitHub de oficina y el repositorio personal nuevo.
