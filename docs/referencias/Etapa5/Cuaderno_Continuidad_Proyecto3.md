# CUADERNO DE CONTINUIDAD — PROYECTO 3 DE ARQUITECTURA DE COMPUTADORES

**Documento operativo para reanudar una conversación de ChatGPT o sesión de Codex sin depender del historial.**

**Última actualización:** 29 de octubre de 2026 (Etapa 4). **Estado:** preparación sin Mac; auditoría, programa, memorias ASIC y **adaptación FPGA→ASIC diseñada**. No hay implementaciones ASIC nuevas ni corridas físicas verificadas.

> INSTRUCCIÓN PRIORITARIA DE REANUDACIÓN: leer este documento entero antes de modificar código. No confundir propuestas con pruebas aprobadas. Pedir/usar los archivos fuente originales o el paquete de continuidad para conocer el RTL exacto; este cuaderno registra contexto y decisiones pero no contiene el texto íntegro de todos los archivos Verilog. Respetar estrictamente la separación de la cuenta personal GitHub de las cuentas corporativas.

## 1. Objetivo, enunciado y calendario

Asignatura Arquitectura de Computadores, Universidad de los Andes, Proyecto 3 (2026-2). El profesor solicita llevar el **Pochoco SoC**, con el juego de reflejos entregado por el grupo en el Proyecto 2, de RTL hasta **GDSII** con **LibreLane** y **PDK GF180MCU**. El diseño final será macro digital estándar, no chip encapsulado. Partir de la entrega *real* del Proyecto 2 (RTL modificado, `game.s` y assembler), NO del repositorio base del curso.

**Entrega GitHub y defensa presencial:** 4 de noviembre de 2026, a las 10:30. El usuario quiere intentar terminar **todo el desarrollo entre el 29 y el 30 de octubre**, sin un plan de calendario por días; planificar por dependencias técnicas y resultados. **Corrida final requerida:** `CLOCK_PERIOD = 100 ns`, `FP_CORE_UTIL = 40%`; timing cerrado en corners requeridos (`WNS>=0`, `TNS=0` en setup/hold), **DRC y LVS limpios**, violaciones de antena inexistentes o justificadas según pauta. La comparación exigida incluye memoria A y B, síntesis por celdas, timing de al menos 3 períodos con corners típico y lento, optimización de ruta crítica, floorplan/ocupación en 3 alternativas, estimación costo usando US$23.000/mm², signoff, capturas señaladas del layout y simulación post-síntesis sin SDF. Defensa vale 1,5 de 6,0 puntos. README debe registrar versiones exactas de LibreLane, PDK y SCL y cómo regenerar el programa y reproducir todo.

## 2. Preferencias y modo de trabajo acordados

- **Este chat**: el asistente organiza y verifica ingeniería, redacta prompts precisos para Codex, revisa resultados y documenta. **Codex**: posteriormente edita código y ejecuta pruebas donde su entorno lo permita. El usuario ejecutará instrucciones locales cuando tenga el Mac.
- El usuario dispone de **MacBook Air M4, 24 GB RAM**, VS Code conectado a GitHub y herramientas Verilog instaladas. **Aún NO tiene entorno Linux ni contenedor LibreLane.** Se probará primero LibreLane en entorno Linux/contenedor compatible Apple Silicon (opción A); plan de respaldo Linux x86_64 remoto si no funciona. No prometer compatibilidad antes de probar.
- **GitHub personal:** `icruzat1`. Repositorio original: `https://github.com/icruzat1/Proyecto2-Arqui` (público en la consulta precedente, pero **NO acceder por la integración GitHub corporativa conectada en ChatGPT bajo ningún concepto**). Repositorio nuevo y separado a crear: `icruzat1/Proyecto3-Arqui`. Carpeta local a crear: `Arquitectura de Computadores/Proyecto 3` (mantener intacto Proyecto 2). No se han creado estos recursos todavía.
- **Cuentas GitHub de oficina son intocables**: no leer, consultar, escribir, inspeccionar ni usar su integración para este proyecto. El usuario aportó ZIP del código para trabajar offline. Nunca subir cambios a repo original ni cuenta corporativa. En GitHub personal usar VS Code/credenciales autorizadas por él.
- No necesita FPGA físicamente para el Proyecto 3 (trabajo por simulación + ASIC). El juego **sí funcionó en la FPGA** durante la defensa del Proyecto 2, pero a veces, al arrancar, LEDs se apagaban y el juego quedaba detenido hasta reiniciar. La FPGA también tenía fallas esporádicas sin explicación aparente. No adjudicar un cuelgue al código sin aislar hardware/reloj/reset/botones/alimentación/simulación.
- Regla permanente: **al FINAL de CADA RESPUESTA mostrar lista de tareas del trabajo «ahora» con marcas persistentes y, DESPUÉS, recomendación BREVE del nivel de pensamiento para los siguientes pasos** (Medium/High/Extra High). Al pasar al Mac, actualizar y mostrar allí la lista correspondiente.
- Dos documentos separados, **actualizados de forma acumulativa**: `Cuaderno_Proyecto3_Acumulativo.md` (para estudio, comprensión y defensa; PDF final al concluir, además del informe académico) y **este `Cuaderno_Continuidad_Proyecto3.md`** (para recuperar proyecto, decisiones, procedimientos, estado y próximos pasos). Mantener ambos en GitHub en cuanto se cree el repo. Actualizar después de cada etapa; no inventar resultados físicos.

## 3. Archivos recibidos y entregables actuales

**Fuentes subidas por el usuario** (copias en esta sesión; una nueva conversación puede exigir re-adjuntarlas):

1. `Proyecto_3_arquitectura.pdf` — enunciado auténtico 3 páginas, incluidas secciones 3.1–3.7, defensa y rúbrica.
2. `Proyecto2-Arqui-main.zip` — ZIP íntegro del repositorio entregado. SHA-256: `d9c8e6888f9968291bd3fda5f5afb619c7985f99c400261dc631f7aa987fdd2c`.
3. `Proyecto2_Compatibilidad_Portable.zip` — copia preparada anteriormente que cambia la ruta `C:/Users/wille/.../sw/game.hex` por `sw/game.hex`, agrega `scripts/prepare_game.py` y `PORTABILIDAD.md`. **No ha sido probada con simulación Verilog ni en el Mac.** Conserva `pochoco_soc-main` como directorio desde el cual resolver el archivo.
4. `Auditoria_Proyecto2_Etapa1.md` — auditoría estática anterior.
5. `Cuaderno_Proyecto3_Acumulativo.md` — documento de estudio por etapas 1, 2, 3 y 4.
6. `Diseno_Memorias_ASIC_Proyecto3.md` — especificación de ambas arquitecturas, interfaces, riesgos y pruebas. **Especificación NO código definitivo.**
7. `Adaptacion_FPGA_a_ASIC_Proyecto3.md` — especificación técnica de la etapa 4: top, reset, RF, periféricos, archivos y comprobaciones.
8. `Cuaderno_Continuidad_Proyecto3.md` — este documento.

**Paquete de recuperación recomendado:** `Kit_Continuidad_Proyecto3.zip` con enunciado, ZIP original, ZIP portable y todos los documentos anteriores. Adjuntar este ZIP en otra conversación si falta material; así no depender de rutas `sandbox:` caducas.

**Estado de comprobaciones:** ZIP e informe revisados estáticamente, assembler ejecutado bajo Python, 94 instrucciones generadas y hex coincidente. NO se ha ejecutado Icarus Verilog/Yosys/LibreLane en esta fase. NO se ha creado `asic_top.v`, layout ni GDSII. NO se han generado métricas reales de área/FF sintetizados/timing/DRC/LVS.

**Observación:** el archivo `Informe Proyecto2.pdf` que contiene el ZIP original tiene **cero bytes**, por lo que no aporta contenido. Si el usuario tiene el informe correcto, pedirlo al llegar al Mac para contrastar la auditoría.

## 4. Mapa comprobado de código fuente (carpeta original dentro del ZIP)

```
Proyecto2-Arqui-main/
  README.md
  Informe Proyecto2.pdf (0 bytes)
  assembler/
    assemble.py
    game.s
    game.hex
  pochoco_soc-main/
    Makefile
    rtl/
      game_top.v
      pochoco_soc.v
      pochoco_ram.v
      pochoco_periph.v
      pochoco_spi_slave.v
      espino_core/
        espino_core.v
        espino_if_stage.v
        espino_id_stage.v
        espino_decoder.v
        espino_alu.v
        espino_register_file.v
        espino_load_store_unit.v
        espino_controller.v
    sw/game.hex
```

- `game_top.v:17-41`: instancia SoC y mapea I/O juego; `:18` ruta absoluta de Wille.
- `pochoco_soc.v:11-13`: `NumWords=512` y `MemFile` en SoC; `:34-40`: reset FPGA mediante `reg por_cnt=0` sin pin externo, no robusto como reset ASIC; `:64-99`: direcciones bit31 = MMIO, 0 normal RAM, puertos instrucción/data, multiplexores con `rd_is_per`, `rd_is_spi`; `:105-140`: periféricos y SPI.
- `pochoco_ram.v:31-55`: arreglo `reg [31:0] mem [0:NumWords-1]`, `initial/$readmemh`, lectura de instrucción de un ciclo habilitada, lectura de datos registrada incondicionalmente, escritura por byte, read-first en colisión (asignaciones no bloqueantes).
- `espino_core.v`: `u_if`, `u_id`, `u_rf`, `u_lsu`, `u_ctrl`.
- `espino_register_file.v:11-71`: doble banco `SB_RAM40_4K` FPGA; implementar FF/lecturas síncronas dos puertos y x0 constante. El register file NO es la memoria de instrucciones/datos a comparar en 3.2.
- `espino_if_stage.v:37-52`: PC+4 y salida sincronizada de memoria; no cambiar latencia arbitrariamente.
- `espino_id_stage.v:60-68`: FSM `ops_valid_q` que espera lectura síncrona RF; controller deriva `stall` de rf_wait/lsu_busy; conservar comportamiento.
- `pochoco_periph.v`: LED, displays, contador 32 bits `cycles_q`, botones sin sincronizador explícito; SPI sí tiene sincronizadores.

## 5. Programa `game.s` y assembler — hechos confirmados

- `assembler/assemble.py`: dos pasadas, soporta un subconjunto de RV32E (x0–x15) con 11 mnemónicos; genera 94 palabras hex en `game.hex`.
- SHA-256 `assembler/game.s`: `f15cd22bb43172fc818828edcb78571d20f1a90e4bfd78fc170816d26f291e2a`.
- SHA-256 `assembler/game.hex`: `e5aca0ab29440ddbe4898a54ba2b0c3d79f43ca19bab1a78cafc0b0b1c3d28d6`.
- `game.s` `0x80000000` = display, `+4` LED, `+8` botones, `+12` contador de ciclos; todas las cargas/escrituras del juego son MMIO. Por tanto **RAM ordinaria utilizada actualmente: 0 palabras**, no significa que podamos omitir las dos alternativas requeridas.
- Inicializa 4 LEDs encendidos, contador de aciertos a 0 y semilla a 1. Hasta 10 aciertos: 3 s de espera, selecciona LED por `x11 & 3`, espera botón, compara máscara, calcula décimas con restas, muestra valor, incrementa aciertos y espera soltar. Error muestra EE, espera soltar y no incrementa. Tras 10 aciertos muestra promedio y se queda en bucle final.
- Nominal FPGA 25 MHz: 3 s = 75.000.000 ciclos; 0,1 s = 2.500.000 ciclos. Nominal ASIC con período T=100 ns (10 MHz): 3 s = 30.000.000 y 0,1 s = 1.000.000 ciclos. Reensamblar si se cambia el reloj realmente utilizado.
- Riesgo de tiempo: el código usa `blt` **con signo** para comparar ticks absolutos en `wait3`; contador de 32 bits cruza bit de signo en `2^31 / 25e6 = 85,89934592 s` después de reset. Una espera de 3s iniciada aproximadamente entre 82,9 y 85,9 s puede fallar. Hipótesis fuerte NO comprobada por simulación; tampoco explica necesariamente bloqueo de inicio de FPGA. Investigar comparación de diferencias sin signo y extensión de assembler si procede, con pruebas.
- Otros datos: lógica de LEDs pseudoaleatoria por recuento de lazos y semilla, por lo que el momento/ciclos por instrucción pueden modificar selección LED; no usar una secuencia LED predecida como única definición de equivalencia.

## 6. Decisión TÉCNICA acordada en esta fase: diseño memoria A/B

**Fuente desarrollada:** `Diseno_Memorias_ASIC_Proyecto3.md`. **Se trata de especificación PROPUESTA, NO implementación verificada.** La pauta exige:

A. **ROM combinacional generada por assembler a partir de `game.s`** y **RAM de datos reducida**.
B. **Memoria unificada de instrucciones/datos hecha con flip-flops**, cuyo programa se carga mediante hardware sintetizable (NO depende de `$readmemh`/`initial`).

**Capacidades comunes propuestas para comparación:** 94 palabras de programa real, ventana de 128 instrucciones reservadas (`0x00000000..0x000001FF`), 16 datos (`0x00000200..0x0000023F`), MMIO en `0x80000000` sin cambios. 94 es uso real; 16 datos es capacidad **provisionada**, el juego utiliza 0. La pauta recomienda máximo 256 instrucciones/64 datos. 128+16 se puede cambiar según mediciones, pero cambiar simultáneamente en A/B y justificar.

- **A**: generador reproducible `game.s → assemble.py → game.hex → Verilog ROM case`, 128 instrucciones lógicas (94 casos explícitos y valor default comprobable), lectura ROM **registrada un ciclo** ante `a_req` (Espino espera lectura síncrona), RAM separada 16x32 por FF con escrituras por byte y lectura registrada. Estimación de FF de RAM = `16×32 = 512` bits **más registros periféricos de lectura y CPU**. La ROM fija no requiere 4.096 FF como almacenamiento; su lógica física debe sintetizarse.
- **B**: un solo arreglo de 144x32 bits para instrucciones+datos (4.608 bits teóricos, más registros de lectura), con dos puertos lógicos de lectura síncrona y escritura de datos por byte. Propuesta de reset explícito sintetizable que establece literales de programa y limpia zona de datos. La región de programa debe poder ser escrita realmente desde el bus de datos (aunque el juego no lo haga), para que la síntesis **no optimice los FF como constantes ROM**. Comprobar en netlist Yosys si las palabras se implementan como FF; riesgo de gran fanout de reset y área. Si reset directo no es viable, explorar carga de programa por SPI sintetizable y secuencia de inicialización real (bootloader SPI opcional, no sustituye A/B).
- Las dos mantienen contrato síncrono actual de `pochoco_ram` (puerto instrucciones requiere `a_req`, salida retenida cuando no hay request; puerto datos muestrea cada flanco, escribe habilitado/BE, lectura antigua durante lectura/escritura concurrentes), con seguridad de direcciones; mantener MMIO y comportamiento CPU.
- **Register file**: reemplazar por FF sintetizables para ASIC con dos lecturas síncronas, x0=0, respetando stall; **separado de la comparación A/B**.
- **Prioridad de construcción**: A primero para conseguir un ASIC funcional cerrado pronto, luego B y comparar formalmente. NO decidir ganadora antes de corridas reales.
- **Presupuesto bits de memoria**: A ≈512 bits FF para RAM versus B ≈4.608 para memoria unificada (**4.096 diferencia teórica**, NO FF sintetizados totales ni área medida). Recuento físico debe salir de LibreLane/Yosys, sin inventar métricas.

**Pruebas a implementar:** igualdad 94 palabras; fetch posiciones 0/1/93/94/127; retención de lectura; acceso datos 0x200 y 0x23C; cuatro byte lanes; colisión read/write; reset B rellena programa; escritura B a instrucción y lectura posterior demuestra FF real; acceso fuera de rango; equivalencia A/B juego y RTL/pn-síntesis con botones idénticos por ciclo; estadísticas de FF y celdas reales. Los ensayos de boot deben tener reset ASIC explícito para no depender de estado de power-on indefinido.

**Documentación oficial externa consultada:**
- LibreLane config JSON y rutas `dir::`: https://librelane.readthedocs.io/en/latest/reference/configuration.html
- Uso de PDKs en LibreLane: https://librelane.readthedocs.io/en/latest/usage/about_pdks.html
- Síntesis de memoria Yosys: https://yosyshq.readthedocs.io/projects/yosys/en/v0.56/using_yosys/synthesis/memory.html

## 7. Lista 1: tareas «AHORA» sin Mac — estado persistente

**5/8 completadas al finalizar el diseño de memorias y redactar este cuaderno.**

- [x] **Auditar el código completo del Proyecto 2.** Auditoría estática completada (no simulación).
- [x] **Analizar el assembler y `game.s`.** Programa 94 palabras verificado, control del juego documentado.
- [x] **Diseñar las dos arquitecturas de memoria ASIC.** Especificación A/B redactada; aún no implementada.
- [x] **Crear el cuaderno técnico de continuidad.** Este archivo + kit de recuperación.
- [x] **Definir la adaptación FPGA → ASIC** (diseño propuesto concluido; ver `Adaptacion_FPGA_a_ASIC_Proyecto3.md`; implementar y probar después en el Mac).
- [ ] **Diseñar pruebas y experimentos** (testbenches y matriz timing/floorplan/corners del informe).
- [ ] **Preparar los prompts iniciales de Codex** (para Git nuevo, adaptación, tests, docs).
- [x] **Comenzar el documento de estudio y defensa** (etapas 1/2/3 en Markdown; PDF al final).

**Al finalizar cada respuesta mostrar esta lista actualizada y después recomendación de potencia**. No marcar implementación como hecha por haberse diseñado.

## 7b. DECISIONES DE LA ETAPA 4: ACTUALIZACIÓN PRIORITARIA

- Se creó el archivo `Adaptacion_FPGA_a_ASIC_Proyecto3.md`, con análisis **archivo/línea**, puertos `asic_top`, reset, sincronización, RF, MMIO, SPI, displays, constraints y criterios de aceptación. **LEERLO** antes de pedir implementación a Codex.
- **Revisión de la estrategia B**: se prefiere **carga secuencial del programa en FF mediante controlador sintetizable y `boot_index` durante 144 ciclos nominales**, manteniendo CPU/periféricos en reset hasta `mem_boot_done`, en lugar de resetear simultáneamente 4.608 FF. La propuesta anterior de inicialización masiva mediante reset queda marcada como obsoleta en `Diseno_Memorias_ASIC_Proyecto3.md`. El cargador no puede depender de `core_rst_ni` o se bloqueará circularmente.
- El `asic_top` expone reloj, reset externo activo bajo, 4 botones, 4 LED, 2×7 segmentos y SPI. Se propone que segmentos de macro sean activos altos lógicos, y que `game_top` preserve la inversión activa baja propia de la FPGA.
- Reset externo con aserción asíncrona y liberación sincronizada, contadores y periféricos liberados junto al core (nunca antes de boot de B); sincronizador 2 FF para botones (sin antirrebote automático), SPI ya tiene 3 FF de sincronización.
- Banco de registros `SB_RAM40_4K` debe reemplazarse por FF y **dos lecturas síncronas**, una escritura; x0 cableado a cero, 15×32=480 bits útiles teóricos; preservar `u_core.u_rf` y la espera de operandos en `espino_id_stage`.
- La selección de memoria A/B es de elaboración con una sola variante por corrida, top y restricciones iguales: `CLOCK_PERIOD=100 ns`, `FP_CORE_UTIL=40%`, LibreLane GF180MCU, biblioteca y versión verificadas al instalar. No reportar resultados aún.
- El enunciado requiere **logs y líneas de warnings** producidos por LibreLane durante el hallazgo de incompatibilidades FPGA; si el flujo no advierte, explicar el problema igualmente con justificación física. No inventar registros.
- No tocar la integración de oficina GitHub; solo ZIP original aportado y repositorio personal futuro. No modificar `Proyecto2-Arqui` original.

## 8. Lista 2: tareas «EN EL MAC» — TODO PENDIENTE

- [ ] Crear carpeta `Arquitectura de Computadores/Proyecto 3`.
- [ ] Crear repo personal nuevo `icruzat1/Proyecto3-Arqui`; no modificar repo anterior.
- [ ] Importar código portable y conectar Codex a cuenta personal adecuada.
- [ ] Verificar herramientas locales Verilog y Python instaladas.
- [ ] Preparar Linux/contenedores (ARM64 primero), confirmar acceso a volumen proyecto.
- [ ] Instalar, versionar y probar LibreLane + GF180MCU y biblioteca de celdas.
- [ ] Validar Proyecto 2: assembler, compilación RTL y juego con tests.
- [ ] Implementar `asic_top.v`, reset, reemplazo de primitivas FPGA.
- [ ] Implementar ambas memorias A/B y scripts generadores desde `game.s`.
- [ ] Ejecutar síntesis, comparar áreas, FF reales, top 5 celdas y módulos.
- [ ] Barrer al menos tres CLOCK_PERIOD, corners exigidos, ruta crítica y mejora.
- [ ] Explorar al menos tres ocupaciones / dimensiones floorplan y costo.
- [ ] Completar routing, GDSII, DRC/LVS/antena y capturas layout anotado.
- [ ] Simular netlist post-síntesis y comparar ciclos con RTL.
- [ ] Preparar informe académico requerido con logs, tablas y gráficos.
- [ ] Revisar y exportar PDF final de estudio/defensa.
- [ ] Verificar README, scripts, commits y entrega final GitHub.

No usar estimaciones como métricas reales ni saltarse validación de ambos diseños. Registrar siempre versiones exactas y referencia a commit.

## 9. Primeros pasos concretos cuando el usuario diga «Estoy en el Mac»

1. Mostrar lista 2 con estado sin pedir datos que ya constan aquí. Confirmar ubicación local sin presuponer nombre de usuario Mac.
2. Crear directorio y repositorio `Proyecto3-Arqui` **solo en GitHub personal**, importar copia del Proyecto 2, mantener referencia del ZIP original y hashes; **no alterar repo Proyecto 2**.
3. Ejecutar `python3 scripts/prepare_game.py` o el procedimiento equivalente portable y confirmar assembler. Corregir si el working directory rompe `$readmemh` para testbench (Python ya usa rutas derivadas de script).
4. Hacer compilar y simular Proyecto 2 antes de refactor; probar arranque y MMIO. Como el banco usa `SB_RAM40_4K`, quizás el simulador exija biblioteca/modelo FPGA, o crear versión equivalente para simulation sin tocar código original; registrar mecanismo.
5. Comprobar Linux (Docker Desktop o alternativa), arquitectura y compatibilidad con LibreLane; prueba pequeña GF180. Tener respaldo Linux x86_64 si falla.
6. Usar prompts progresivos de Codex redactados por ChatGPT; exigir cambios controlados, tests, evidencia, actualización de **ambos cuadernos**. En lo posible no automatizar una modificación grande sin revisar diff.
7. Implementar A y B, ejecutar y comparar. El usuario pretende finalizar 29–30, pero las corridas pueden tardar; priorizar flujo GDSII funcional sobre optimizaciones ornamentales.

## 10. Reglas para el trabajo futuro y el informe

- En cada prompt de Codex: **objetivo, alcance, archivos a tocar, archivos que NO se pueden tocar, criterios de aceptación, comandos para validar, evidencia y documento que debe actualizarse**.
- Nunca asumir que los errores intermitentes de FPGA se debían al RTL; investigar resets, botones, fuente de alimentación y reloj en pruebas.
- Comparar A/B con SAME workload, clock, floorplan target/PDK/library, corners y equipo; documentar cualquier diferencia. Tras síntesis es posible que cada `CLOCK_PERIOD` produzca distinta optimización, área y buffering.
- Confirmar el port map de `asic_top` del enunciado: reloj, reset, LEDs, botones, displays, SPI. Son **terminales lógicos** de macro, no pads de chip.
- Mantener jerarquía o trazabilidad de `u_rf`, `u_alu`, contador de ciclos. Capturar logs y líneas que evidencien incompatibilidades FPGA; cuando no haya advertencia explicar por qué igual eran un problema en ASIC.
- Capturar versiones exactas LibreLane, PDK, SCL; corridas DRC/LVS, antena, setup/hold típico/lento; layout con bloques identificados; justificar coste lineal US$23.000/mm² y límites del cálculo.
- **Informe académico PDF** aparte del **manual de estudio y defensa PDF** al término del proyecto.

## 11. Potencia de pensamiento recomendada

- Diseño RTL/memorias, compatibilidad ASIC y decisiones físicas: **Extra High**.
- Análisis funcional de testbenches, revisión de resultados y prompts Codex: **High**.
- Ordenar documentación, resúmenes: **Medium**.

## 12. Qué falta verificar antes de afirmar éxito

- No existe testbench completo reproducible entregado ni informe P2 legible en ZIP.
- No se han sintetizado memorias A/B ni validado reset B (riesgo: optimización de FF o problemas físicos).
- No se ha confirmado que la versión portable compile/funcione en Mac.
- No hay Linux/LibreLane en Mac ni PDK instalado confirmado.
- No hay valores reales de área, FF, WNS, TNS, DRC/LVS, antena, GDSII, máxima frecuencia ni costo.
- El problema de cruce signed a 85,9 s es una explicación probable del comentario sobre tiempos, no la causa demostrada de fallo en FPGA.

**Instrucción final de continuidad:** ante pérdida de contexto, tomar este archivo como la fuente principal de estado; complementarlo con `Proyecto2-Arqui-main.zip`, `Proyecto_3_arquitectura.pdf`, `Diseno_Memorias_ASIC_Proyecto3.md`, `Adaptacion_FPGA_a_ASIC_Proyecto3.md` y `Cuaderno_Proyecto3_Acumulativo.md` para recuperar RTL, requisitos y documentación explicativa exactos. Actualizar este archivo al finalizar cualquier nueva etapa importante.


---
## 13. ETAPA 5 — MATRIZ DE PRUEBAS Y EXPERIMENTOS (actualización 29-10-2026)

**Nuevo archivo obligatorio para continuidad:** `Plan_Pruebas_Experimentos_Proyecto3.md`. Contiene 22 casos funcionales/entorno/RTL (ENV-01, BUILD-01, ASM-01..03, RF-01..02, MEM-A1..A2, MEM-B1..B3, MMIO-01, SPI-01, GAME-01..06, EQ-01..02) y experimentos físicos SYN-01..03, TIM-01..04, PHY-01..04, SIGN-01..02, LAY-01, RPT-01..02. En documento original se encuentran objetivos, aserciones, evidencia y orden de ejecución.

**Decisiones:** pruebas aceleradas del juego con firmware explícito idéntico para cada par RTL/post-síntesis; reloj real a 100 ns, 40 % para corrida final; barrido inicial tentativo 100/80/60 ns más refinamientos según resultado; utilizaciones iniciales 30/40/50 %, sin inventar valores ni afirmar cierres. Cada corrida registra commit, hash firmware, versiones de herramientas y PDK/SCL, corners, WNS/TNS setup y hold, FF, área, congestión y DRC/LVS/antena.

**Riesgos nuevos explicitados:** `pochoco_ram.v` P2 registra lectura datos cada flanco aun cuando `b_req=0`; `SB_RAM40_4K` estaba duplicado por puertos de lectura y su semántica de colisión debe estudiarse; B debe aceptar reset a mitad de boot sin ejecutar firmware parcial. La sincronización de botones puede introducir latencia, por lo que los estímulos se alinearán por ciclo tras liberación del core. Prueba de cruce signed en ~85,9s se trata por separado y puede fallar en baseline por diseño; jamás etiquetar falsa equivalencia PASS.

**Estado listas «AHORA»: 7/8 completadas.**
- [x] Auditar RTL P2; [x] analizar assembler y game.s; [x] diseñar memorias A/B; [x] crear cuaderno técnico de continuidad; [x] definir adaptación FPGA→ASIC; **[x] diseñar pruebas y experimentos**; [ ] preparar prompts iniciales de Codex; [x] comenzar documento de estudio y defensa.

**No ejecutado:** compilación Verilog, testbenches, síntesis Yosys, LibreLane, GDSII, DRC/LVS, timing. Próximo paso sin Mac: construir prompts reproducibles por fases para Codex; con Mac iniciar Linux/LibreLane y baseline P2. Regla de usuario: imprimir la lista de ocho tareas al final de cada respuesta y, después, una tabla breve de potencia de pensamiento sugerida.
