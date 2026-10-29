# Proyecto 3 — Cuaderno técnico acumulativo
## Etapa 1. Auditoría estática del Proyecto 2

**Origen:** ZIP `Proyecto2-Arqui-main.zip` proporcionado por el equipo. Auditoría de lectura; el repositorio original no se modificó. 29 de octubre de 2026.

### 1. Estado conocido
- El usuario confirma que el programa se presentó funcionando en FPGA; intermitentemente los LEDs se apagaban al comienzo y no se iniciaba la secuencia, requiriendo reiniciar.
- Se reportó una observación no verificada de un posible problema de conteo cerca de 80–85 segundos.
- No se puede atribuir el fallo al RTL ni a la placa sin pruebas adicionales.
- El archivo `Informe Proyecto2.pdf` del ZIP tiene **0 bytes**: no contiene un informe consultable.

### 2. Diagrama lógico
`game_top` → `pochoco_soc` → `espino_core` (`u_if`, `u_id` con `u_decoder` y `u_alu`, `u_rf`, `u_lsu`, `u_ctrl`), `u_ram`, `u_periph`, `u_spi`.

- `game_top.v:17-41`: instancia el SoC y expone I/O; contiene la ruta absoluta de Windows en la línea 18.
- `pochoco_soc.v:34-40`: genera un reset con contador inicializado por declaración; no recibe un reset externo.
- `pochoco_soc.v:64-99`: decodifica memoria frente a MMIO y conecta la RAM unificada de instrucciones/datos.
- `pochoco_periph.v:29-55,88-99`: controla LEDs, displays, contador libre de ciclos y lecturas de botones; no se aprecia sincronización ni antirrebote de `btn_i`.
- `espino_register_file.v:11-71`: register file de dos puertos de lectura por duplicación de bancos RAM. Utiliza `SB_RAM40_4K` (iCE40), elemento específico de FPGA. Una sustitución ASIC debe preservar lecturas sincrónicas y el registro x0.
- `pochoco_ram.v:31-55`: memoria unificada con dos puertos; `initial` + `$readmemh`; direcciones de palabra y acceso sincrónico. **Aunque el módulo declara 2048 palabras por defecto, la instancia real usa 512 palabras** mediante el parámetro `NumWords` de `pochoco_soc.v:12`.
- `espino_alu.v:72-77`: desplazamientos intencionadamente deshabilitados; el valor por defecto se calcula como ADD. No alterar sin necesidad.
- `espino_id_stage.v:60-68`: la CPU espera la lectura síncrona del banco de registros; cambiarla por lectura combinacional sin revisar la latencia alteraría el comportamiento.
- `pochoco_spi_slave.v`: dispone de sincronizadores para señales SPI, a diferencia de los botones.

### 3. Programa y assembler: comprobaciones directas
- `assembler/game.s`: lógica del juego, 10 rondas correctas, temporización, selección de LED, pulsaciones, medición en décimas, display y promedio final.
- `assembler/assemble.py`: assembler propio para un subconjunto de RV32E (registros x0–x15). El código entregado se ensambló sin errores mediante Python disponible en el entorno de auditoría.
- **94 instrucciones**, coinciden exactamente con `assembler/game.hex` y `pochoco_soc-main/sw/game.hex` existentes.
- Espera nominal: 75.000.000 ciclos (`game.s:31-34`), equivalente a 3 s a **25 MHz**.
- Décima: 2.500.000 ciclos (`game.s:64-66`), equivalente a 0,1 s a **25 MHz**.
- `game.s` utiliza `lw`/`sw` sobre direcciones MMIO derivadas de `0x80000000`; **no se observaron accesos explícitos a RAM de datos del juego**. Deberá distinguirse esta necesidad real de la RAM mínima que se implemente para la comparación obligatoria del Proyecto 3.
- El display obtiene códigos de siete segmentos a partir de dos nibbles del registro de dígitos. `EE` marca error; tras diez aciertos se muestra el promedio y se entra en un bucle de fin.

### 4. Riesgos clasificados
1. **Confirmado — incompatibilidad ASIC:** primitivas `SB_RAM40_4K` en el register file (`espino_register_file.v:22-41`), por ser tecnología iCE40.
2. **Confirmado — incompatibilidad ASIC:** carga de programa en RAM por `$readmemh` (`pochoco_ram.v:35-36`); no equivale a ROM no volátil fabricada en silicio.
3. **Confirmado — diseño de reset no portable tal cual:** `reg [3:0] por_cnt = 4'b0` y ausencia de reset externo (`pochoco_soc.v:34-40`, `game_top.v:3-15`). No puede confiarse en que los registros de un ASIC arranquen automáticamente en cero.
4. **Confirmado — dependencia de un computador:** ruta absoluta en `game_top.v:18` y comandos Windows en README.
5. **Riesgo de hardware a probar:** entradas `btn_i` leídas en `pochoco_periph.v:92` sin sincronización/debounce explícitos. No demuestra que fueran responsables de los cuelgues observados.
6. **Hallazgo fuerte sobre el tiempo:** `cycles_q` es contador de 32 bits (`pochoco_periph.v:33,46`) mientras `game.s:38` compara el contador con `blt` con signo. A 25 MHz el bit de signo cambia a 2^31/25e6 = **85,89934592 segundos**. Cerca del cruce, comparar instantes como enteros con signo puede saltarse parte de la espera. La coincidencia con el aviso de «80–85» es significativa, pero todavía requiere un testbench dirigido.
7. **Precaución de síntesis:** el diseño FPGA usa lectura síncrona en la RAM y el register file, a preservar al implementar ASIC.
8. **Capacidad actual de pruebas:** el ZIP no contiene testbench reproducible del juego y en el entorno de esta auditoría no hay `iverilog` ni `yosys`; se verificó ensamblado y análisis de fuentes, **no simulación RTL**.

### 5. Próximas pruebas necesarias
- Testbench de arranque que observe PC, reset, instrucciones válidas, LEDs y primeras escrituras MMIO.
- Simulación de botones: acierto, error, rebote, pulsación mantenida y reset intermitente.
- Testbench dirigido al cruce `2^31` del contador, sin esperar físicamente 85 s: sembrar un valor cercano al umbral en simulación.
- Comparar resultados RTL original, RTL ASIC y netlist post-síntesis con idénticos estímulos y configuración.
- Validar en el Mac la generación del hex y la simulación completa antes de atribuir fallos a la FPGA.

### 6. Decisiones provisionales (sujetas a resultados)
- Congelar el código original; trabajar en el nuevo repositorio personal `Proyecto3-Arqui`.
- Crear `asic_top.v` con reset externo y mapeo lógico apropiado; no incluir pads físicos.
- Reemplazar el register file iCE40 por descripción sintetizable a celdas estándar conservando latencia y x0.
- Evaluar las dos arquitecturas de memoria exigidas; conservar instrucciones y datos observables.
- Cambiar constantes de tiempo en una variante del programa para `CLOCK_PERIOD=100 ns` (10 MHz): 30.000.000 ciclos para 3 s y 1.000.000 para 0,1 s; recalcular y verificar en el assembler, no asumir que las corridas físicas siempre operan a esta frecuencia.

### 7. Glosario para la defensa
- **MMIO:** periféricos accesibles mediante direcciones de memoria.
- **Register file:** conjunto de registros de propósito general de la CPU. En el original, sus dos puertos de lectura usan bancos duplicados de RAM FPGA.
- **BRAM:** memoria interna configurable propia de la FPGA; no puede trasladarse tal cual a las celdas estándar del ASIC.
- **ROM combinacional:** lógica que implementa un contenido fijo a partir de la dirección.
- **Flip-flop:** celda secuencial que conserva un bit. Su uso masivo como memoria puede incrementar el área.
- **WNS / TNS:** métricas de cumplimiento temporal que mediremos con LibreLane.

### 8. Trazabilidad del documento
Actualización: Etapa 1, auditoría estática. Los resultados ASIC (área, celdas, timing, DRC/LVS, antena, layout) permanecen pendientes de corridas; no se han inventado métricas.
