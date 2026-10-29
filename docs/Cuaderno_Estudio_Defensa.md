# Cuaderno de estudio y defensa del Proyecto 3

Actualizado el 29 de octubre de 2026. Reúne las etapas históricas 1 a 5 y las verificaciones del Mac. El firmware ASIC de 95 instrucciones está recalibrado a 10 MHz; la partida completa y la comparación RTL/netlist genérica pasan en A/B. El mapeo GF180 y la implementación física siguen pendientes. Las secciones históricas conservan los estados que tenían al redactarse. La prueba física completada corresponde al ejemplo oficial spm.

## Estado actual y forma de estudiar

Leer primero [Requisitos y evidencias](Requisitos_Proyecto3.md), que contrasta el plan con las tres páginas del enunciado. Leer también [Juego a 10 MHz](Juego_10MHz.md) y la actualización al final de este cuaderno. Después estudiar la arquitectura y el programa, y utilizar las preguntas de cada etapa para explicar las decisiones sin depender de memorizar el código.

La preparación anterior se conserva como una secuencia histórica. Los estados de ejecución de esas etapas describen el momento de su redacción; la sección de verificación en el Mac contiene los resultados posteriores. El original del cuaderno está archivado en referencias/Etapa5.

Dos precisiones: la inicialización de B por reset descrita en la etapa 3 fue sustituida, en la etapa 4, por el cargador secuencial como propuesta vigente. Se corrigió en este cuaderno una errata del hash de game.hex contrastándola con el archivo real; el documento original permanece intacto. Los 30 archivos de código recibidos coinciden con el Proyecto 2 del Mac. El informe PDF de ese proyecto también tiene cero bytes en el Mac, por lo que todavía no aporta material para contrastar la defensa anterior.

## Preparación anterior de las etapas 1 a 5

### Etapa 1. Auditoría estática del Proyecto 2

**Origen:** ZIP `Proyecto2-Arqui-main.zip` proporcionado por el equipo. Auditoría de lectura; el repositorio original no se modificó. 29 de octubre de 2026.

#### 1. Estado conocido
- El usuario confirma que el programa se presentó funcionando en FPGA; intermitentemente los LEDs se apagaban al comienzo y no se iniciaba la secuencia, requiriendo reiniciar.
- Se reportó una observación no verificada de un posible problema de conteo cerca de 80–85 segundos.
- No se puede atribuir el fallo al RTL ni a la placa sin pruebas adicionales.
- El archivo `Informe Proyecto2.pdf` del ZIP tiene **0 bytes**: no contiene un informe consultable.

#### 2. Diagrama lógico
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

#### 3. Programa y assembler: comprobaciones directas
- `assembler/game.s`: lógica del juego, 10 rondas correctas, temporización, selección de LED, pulsaciones, medición en décimas, display y promedio final.
- `assembler/assemble.py`: assembler propio para un subconjunto de RV32E (registros x0–x15). El código entregado se ensambló sin errores mediante Python disponible en el entorno de auditoría.
- **94 instrucciones**, coinciden exactamente con `assembler/game.hex` y `pochoco_soc-main/sw/game.hex` existentes.
- Espera nominal: 75.000.000 ciclos (`game.s:31-34`), equivalente a 3 s a **25 MHz**.
- Décima: 2.500.000 ciclos (`game.s:64-66`), equivalente a 0,1 s a **25 MHz**.
- `game.s` utiliza `lw`/`sw` sobre direcciones MMIO derivadas de `0x80000000`; **no se observaron accesos explícitos a RAM de datos del juego**. Deberá distinguirse esta necesidad real de la RAM mínima que se implemente para la comparación obligatoria del Proyecto 3.
- El display obtiene códigos de siete segmentos a partir de dos nibbles del registro de dígitos. `EE` marca error; tras diez aciertos se muestra el promedio y se entra en un bucle de fin.

#### 4. Riesgos clasificados
1. **Confirmado — incompatibilidad ASIC:** primitivas `SB_RAM40_4K` en el register file (`espino_register_file.v:22-41`), por ser tecnología iCE40.
2. **Confirmado — incompatibilidad ASIC:** carga de programa en RAM por `$readmemh` (`pochoco_ram.v:35-36`); no equivale a ROM no volátil fabricada en silicio.
3. **Confirmado — diseño de reset no portable tal cual:** `reg [3:0] por_cnt = 4'b0` y ausencia de reset externo (`pochoco_soc.v:34-40`, `game_top.v:3-15`). No puede confiarse en que los registros de un ASIC arranquen automáticamente en cero.
4. **Confirmado — dependencia de un computador:** ruta absoluta en `game_top.v:18` y comandos Windows en README.
5. **Riesgo de hardware a probar:** entradas `btn_i` leídas en `pochoco_periph.v:92` sin sincronización/debounce explícitos. No demuestra que fueran responsables de los cuelgues observados.
6. **Hallazgo fuerte sobre el tiempo:** `cycles_q` es contador de 32 bits (`pochoco_periph.v:33,46`) mientras `game.s:38` compara el contador con `blt` con signo. A 25 MHz el bit de signo cambia a 2^31/25e6 = **85,89934592 segundos**. Cerca del cruce, comparar instantes como enteros con signo puede saltarse parte de la espera. La coincidencia con el aviso de «80–85» es significativa, pero todavía requiere un testbench dirigido.
7. **Precaución de síntesis:** el diseño FPGA usa lectura síncrona en la RAM y el register file, a preservar al implementar ASIC.
8. **Capacidad actual de pruebas:** el ZIP no contiene testbench reproducible del juego y en el entorno de esta auditoría no hay `iverilog` ni `yosys`; se verificó ensamblado y análisis de fuentes, **no simulación RTL**.

#### 5. Próximas pruebas necesarias
- Testbench de arranque que observe PC, reset, instrucciones válidas, LEDs y primeras escrituras MMIO.
- Simulación de botones: acierto, error, rebote, pulsación mantenida y reset intermitente.
- Testbench dirigido al cruce `2^31` del contador, sin esperar físicamente 85 s: sembrar un valor cercano al umbral en simulación.
- Comparar resultados RTL original, RTL ASIC y netlist post-síntesis con idénticos estímulos y configuración.
- Validar en el Mac la generación del hex y la simulación completa antes de atribuir fallos a la FPGA.

#### 6. Decisiones provisionales (sujetas a resultados)
- Congelar el código original; trabajar en el nuevo repositorio personal `Proyecto3-Arqui`.
- Crear `asic_top.v` con reset externo y mapeo lógico apropiado; no incluir pads físicos.
- Reemplazar el register file iCE40 por descripción sintetizable a celdas estándar conservando latencia y x0.
- Evaluar las dos arquitecturas de memoria exigidas; conservar instrucciones y datos observables.
- Cambiar constantes de tiempo en una variante del programa para `CLOCK_PERIOD=100 ns` (10 MHz): 30.000.000 ciclos para 3 s y 1.000.000 para 0,1 s; recalcular y verificar en el assembler, no asumir que las corridas físicas siempre operan a esta frecuencia.

#### 7. Glosario para la defensa
- **MMIO:** periféricos accesibles mediante direcciones de memoria.
- **Register file:** conjunto de registros de propósito general de la CPU. En el original, sus dos puertos de lectura usan bancos duplicados de RAM FPGA.
- **BRAM:** memoria interna configurable propia de la FPGA; no puede trasladarse tal cual a las celdas estándar del ASIC.
- **ROM combinacional:** lógica que implementa un contenido fijo a partir de la dirección.
- **Flip-flop:** celda secuencial que conserva un bit. Su uso masivo como memoria puede incrementar el área.
- **WNS / TNS:** métricas de cumplimiento temporal que mediremos con LibreLane.

#### 8. Trazabilidad del documento
Actualización: Etapa 1, auditoría estática. Los resultados ASIC (área, celdas, timing, DRC/LVS, antena, layout) permanecen pendientes de corridas; no se han inventado métricas.


---
### Etapa 2. Auditoría detallada del programa `game.s` y del assembler

**Base examinada:** `assembler/game.s` (139 líneas), `assembler/assemble.py` (177 líneas), `assembler/game.hex` y `pochoco_soc-main/sw/game.hex`, archivos del ZIP original. Se usó Python para ejecutar el assembler y contar instrucciones; **no** se simuló el RTL.

#### 9. Secuencia funcional precisa del juego

| Paso | Código fuente | Efecto observable / estado |
|---|---|---|
| Inicialización | `game.s:13-21` | Construye el puntero MMIO `0x80000000`; enciende 4 LEDs escribiendo `0xF` en `0x80000004`; fija aciertos `x10=0`, semilla `x11=1`, total de décimas `x12=0`. |
| Inicio de ronda | `game.s:23-34` | Si `x10==10`, salta a `done`; mantiene encendidos los 4 LEDs; lee el contador y construye un plazo nominal de 75.000.000 ciclos. |
| Espera | `game.s:35-38` | Incrementa `x11`, lee el contador y compara el contador absoluto `x7` con el objetivo `x8` mediante `blt` con signo. |
| Selección de LED | `game.s:40-52` | Calcula `x11 & 3`; elige máscara 1, 2, 4 u 8; enciende solo el LED elegido. No es aleatoriedad criptográfica: depende de las iteraciones del lazo. |
| Espera de botón | `game.s:54-60` | Guarda tiempo inicial, incrementa semilla mientras espera, lee botones hasta obtener valor no cero. Solo acepta **exactamente** la máscara del LED. Pulsaciones simultáneas normalmente se interpretan como incorrectas. |
| Acierto: tiempo y décimas | `game.s:62-77` | Tiempo transcurrido por resta modular; división entera por 2.500.000 con restas repetidas; limita la cifra a 99; suma décimas a `x12`. |
| Acierto: visualización | `game.s:79-100` | Conversión decimal por restas de 10, decenas y unidades empaquetadas en dos nibbles BCD; incrementa aciertos `x10`; espera soltar botón y pasa a la siguiente ronda. |
| Error | `game.s:102-110` | Apaga LEDs, escribe `0xEE` en display, espera liberar botón y comienza otra ronda **sin incrementar** `x10`. No limpia el acumulado `x12`. |
| Fin | `game.s:112-138` | Al llegar a diez aciertos, calcula `floor(x12/10)` con restas repetidas, muestra el promedio como dos dígitos y entra al bucle permanente `hang`. |

El display muestra décimas *enteras* (`06` significa 0,6 s en el README), no dispone de punto decimal controlado por este código. El tope por ronda es 99 décimas (9,9 s).

#### 10. Direcciones y registros relevantes

- Base MMIO: `0x80000000` (`lui x2, 0x80000`).
- `0x80000000` — **escritura** del display (`sw ..., 0(x2)`), registro `digit_q`.
- `0x80000004` — **escritura** de los 4 LEDs (`sw ..., 4(x2)`), registro `led_q`.
- `0x80000008` — **lectura** de botones (`lw ..., 8(x2)`).
- `0x8000000C` — **lectura** del contador de 32 bits (`lw ..., 12(x2)`).
- Correspondencia verificada con `pochoco_periph.v:26-55,85-99`.
- `x10`: rondas correctas (0 a 10); `x11`: semilla dependiente de la temporización; `x12`: suma de décimas; `x13`: máscara esperada; `x14`: botones; `x15`: décimas de la ronda / promedio final.
- El programa **no contiene** cargas ni stores de RAM ordinaria: todas las 7 cargas y las 7 escrituras están destinadas a MMIO. Las operaciones de cálculo se realizan en registros.

#### 11. El assembler: capacidades y resultado verificado

1. `assemble.py:5-27` define las 11 instrucciones soportadas: `lui`, `addi`, `andi`, `add`, `sub`, `lw`, `sw`, `beq`, `bne`, `blt`, `jal`.
2. `assemble.py:30-44` codifica campos binarios y valida registros RV32E `x0`–`x15`.
3. `assemble.py:50-65` elimina comentarios y analiza operandos de memoria `desplazamiento(registro)`.
4. **Primera pasada** (`assemble.py:131-155`): etiqueta direcciones a partir de un PC que avanza en bytes de a 4.
5. **Segunda pasada** (`assemble.py:157-164`): transforma cada instrucción en una palabra de 32 bits en hexadecimal, una por línea.
6. `assemble.py:166-174`: escribe el archivo `.hex`.

**Comprobaciones ejecutadas:** 94 instrucciones, 376 bytes lógicos de instrucciones, 94 líneas de 8 dígitos hex. La salida regenerada es idéntica a los dos `game.hex` entregados. SHA-256 del texto regenerado: `e5aca0ab29440ddbe4898a54ba2b0c3d79f43ca19bab1a78cafc0b0b1c3d28d6`.

**Distribución de instrucciones (estática):** `addi` 38; `add` 12; `lw` 7; `sw` 7; `jal` 7; `blt` 6; `beq` 5; `sub` 5; `bne` 3; `lui` 3; `andi` 1. No representa frecuencias dinámicas de ejecución: los loops repiten instrucciones.

**Etiquetas importantes, direcciones byte:** `_start=0`, `round=32`, `wait3=68`, `show_led=120`, `wait_press=128`, `wrong=264`, `done=292`, `hang=372`. Última instrucción en dirección byte 372.

**Límites del assembler actual:** recorta operandos inmediatos usando máscaras de bits sin rechazar todos los desbordamientos de rango; ignora cualquier directiva que comience con punto; no implementa `bltu`, `bgeu`, `li` ni otras pseudoinstrucciones. Para una corrección robusta del reloj y salida ROM automatizada, conviene agregar instrucciones y validaciones mediante pruebas unitarias, conservando el resultado `game.hex` original como referencia. No introducir cambios ahora a la versión congelada.

#### 12. Constantes de reloj y riesgo del bit de signo

`game.s:31-34` construye `0x047868C0` = **75.000.000** ciclos para esperar 3 s a 25 MHz. `game.s:64-66` construye `0x002625A0` = **2.500.000** ciclos para una décima de segundo a 25 MHz. La frecuencia de 25 MHz es **deducida de esas constantes**, no explícitamente declarada en el archivo `game.s`.

El contador `cycles_q` de `pochoco_periph.v:33,46` incrementa en cada ciclo y se reinicia en reset. `wait3` compara **tiempos absolutos** con `blt`, que en Espino implementa una comparación **signed** (`espino_alu.v:46-47`).

- El signo de un contador de 32 bits cambia en `2^31=2.147.483.648` ciclos, equivalente a **85,89934592 s** a 25 MHz.
- Si una espera de 3 s comienza a partir de aprox. `(2^31-75.000.000)/25.000.000=82,89934592 s` y antes de 85,89934592 s, su objetivo `x8` cruza el límite signed mientras el contador inicial aún es positivo: `blt x7,x8,wait3` puede ser falso inmediatamente y saltarse la espera.
- La lógica de tiempos absolutos también tiene que contemplar el wrap de 32 bits en `2^32/25MHz≈171,8 s`. Una solución robusta emplea diferencia modular `elapsed = now-start`, luego compara `elapsed` **sin signo** frente a la duración, asumiendo duraciones menores que 2^32 y con pruebas para wrap. Esto requiere ampliar el assembler con `bltu` o instrucción equivalente, aunque Espino ya decodifica BLTU (`espino_decoder.v:212`, ALU unsigned `espino_alu.v:47,56`).
- La medición de reacción `sub x8,x8,x7` ya calcula una diferencia modular y resiste un único wrap para intervalos cortos, pero la división y topes posteriores usan comparaciones con signo; se deben validar tiempos anormalmente largos.

**Importante:** es una falla lógica deducida del código y de la aritmética signed, no una simulación de reproducción ni la causa comprobada del bloqueo de arranque. Para el ASIC debemos **cambiar la frecuencia efectiva esperada por `game.s`**: con `CLOCK_PERIOD=100 ns` (10 MHz) serían 30.000.000 ciclos/3 s y 1.000.000 ciclos/0,1 s. Se debe distinguir entre el período objetivo del análisis estático de timing y la frecuencia suministrada realmente en una simulación o sistema físico.

#### 13. Consecuencias para la memoria y la futura defensa

- Tamaño *real del programa*: **94 palabras de instrucción x 32 bits**, bajo el límite sugerido de 256 palabras.
- Necesidad de *datos RAM por `game.s` actual*: **0 palabras accedidas explícitamente** (fuera de MMIO), aunque la arquitectura de CPU y la segunda alternativa exigida pueden justificar memoria de datos implementada; debemos documentar la mínima elegida y garantizar la interfaz.
- Se necesita ROM combinacional generada por el assembler y adaptación de la interfaz a la CPU que espera lectura sincronizada en `pochoco_ram`.
- La alternativa unificada de FF debe ser realizable sin inicialización por `readmemh` en el chip fabricado. Conviene diferenciar ROM de instrucciones cableada y memoria reescribible sintetizada en FF.
- La pseudoaleatoriedad `x11 & 3` depende del conteo de iteraciones de polling; si la arquitectura ASIC cambia la cantidad de ciclos por instrucción, las secuencias pueden cambiar sin ser un fallo de funcionalidad. Para simulaciones comparativas, deberán establecerse estímulos idénticos **y criterios observables**, evitando exigir secuencias de LED idénticas por coincidencia si el ciclo de ejecución cambió.

#### 14. Pruebas derivadas de esta etapa

1. Test de assembler con salida exactamente igual a `game.hex` de referencia.
2. Test de ISA: etiquetas forward/backward, branch con signo, constantes construidas con LUI/ADDI, rango de inmediatos y decodificación.
3. Test de arranque: LED=0xF tras reset, contador avanza, final de espera LED one-hot.
4. Test de pulsación correcta: cada lectura de botón, captura de timestamp, conteo de décimas, display BCD y `x10++`.
5. Test de pulsación incorrecta/simultánea: `EE`, LEDs apagados, `x10` sin cambio y recuperación tras liberar el botón.
6. Test de 10 aciertos: promedio y lazo final; documentar que no se reinicia el juego sin reset/programación.
7. Test del cruce signed: inyectar valores de contador próximos a 82,9–85,9 s y verificar duración de espera; prueba posterior del wrap de 32 bits.
8. Test de equivalencia RTL frente a netlist post-síntesis con estímulos en ciclos definidos. Acortar 3 s por parámetro o variante controlada del programa para que sea rápido.

**Estado:** análisis estático `game.s`/assembler finalizado, generación y comparación de `.hex` confirmadas. Ejecución real del programa y simulación de comportamiento quedan pendientes de entorno con simulador Verilog. No se ha alterado código original.


---
### Etapa 3. Diseño de las dos arquitecturas de memoria ASIC

**Fecha:** 29 de octubre de 2026. **Estado:** diseño y justificación completos; implementación, simulación y síntesis pendientes. Documento complementario: [Diseno_Memorias_ASIC_Proyecto3.md](referencias/Etapa5/Diseno_Memorias_ASIC_Proyecto3.md).

#### 15. ¿Por qué cambiar la memoria original?

En una FPGA, las memorias integradas pueden cargar archivos hexadecimales como parte de la configuración. El RTL original de Pochoco utiliza `initial/$readmemh` para llenar una memoria unificada de 512 palabras. En un macro ASIC de celdas estándar, ese archivo no aparece mágicamente al conectar la alimentación: hay que hacer que el programa sea parte de la lógica física o cargarlo mediante un circuito real.

El enunciado exige estudiar **dos maneras de resolverlo**. La memoria de instrucciones y datos del SoC es distinta del *register file* de la CPU. Este último también necesita adaptación porque usa `SB_RAM40_4K` exclusivo de FPGA.

#### 16. Alternativa A — ROM combinacional + RAM pequeña

`game.s` pasa por `assemble.py`, genera `game.hex` y luego un generador emite código Verilog con una tabla `case` que relaciona direcciones con instrucciones constantes. La ROM propiamente tal es lógica combinacional; para respetar la interfaz del procesador se coloca un **registro de salida** que captura la instrucción en el flanco del reloj habilitado. Aparte queda una RAM pequeña de datos hecha con flip-flops, direccionada fuera de la ventana de instrucciones.

Elegimos provisionalmente **128 posiciones de 32 bits para ROM**, que contienen las 94 instrucciones y 34 posiciones de reserva, y **16 palabras de 32 bits para RAM**, aunque el juego actual accede a **0 palabras ordinarias de datos** (todo su `lw/sw` va a MMIO). La RAM existe para mantener la interfaz del procesador y probar una arquitectura general.

#### 17. Alternativa B — memoria unificada de flip-flops

El **mismo arreglo** almacena las 128 posiciones de instrucciones y 16 de datos: **144 palabras de 32 bits = 4.608 bits** de almacenamiento lógico. A diferencia de A, el programa también debe residir físicamente en flip-flops. Un reset externo sintetizable cargará las instrucciones constantes generadas desde `game.s` y reiniciará la RAM de datos. Después del reset la memoria debe aceptar escrituras normales desde el puerto de datos, incluyendo instrucciones, para que la síntesis no transforme las palabras de programa en constantes. Hay que verificar que el netlist efectivamente preserve el almacenamiento en flip-flops; esta estrategia puede causar fanout de reset y gran área.

**Advertencia:** el arranque de B mediante reset sintetizable es una propuesta y deberá demostrarse en Yosys/LibreLane. `$readmemh` y `initial` no son una solución física suficiente. Si no funciona, se evaluará una carga real por hardware (p. ej. SPI), sin reemplazar por ello el requisito de ambas arquitecturas.

#### 18. Comparación que podremos explicar en la defensa

| Parámetro | A: ROM + RAM FF | B: FF unificada |
|---|---|---|
| Programa real del juego | 94 palabras | 94 palabras |
| Capacidad de programa reservada | 128 palabras | 128 palabras |
| RAM reservada (no usada actualmente por `game.s`) | 16 palabras | 16 palabras |
| Almacenamiento FF solo del arreglo de memoria (teórico) | 512 bits | 4.608 bits |
| Instrucciones reprogramables por la CPU | No: ROM fija | Sí, si la interfaz de escritura se habilita |
| Registro de salida de lectura | Sí, para mantener latencia | Sí, para mantener latencia |
| Área y frecuencia reales | **Por medir** | **Por medir** |

**No confundir bits teóricos con el número exacto de flip-flops en el reporte:** el resultado depende de optimizaciones y de los registros auxiliares, decodificadores y muxes. Las dos alternativas deben pasar por el mismo PDK y condiciones de síntesis para comparar correctamente.

#### 19. Mapa de direcciones propuesto y compatibilidad

- Instrucciones: `0x00000000`–`0x000001FF` (128 palabras).
- Datos: `0x00000200`–`0x0000023F` (16 palabras).
- MMIO sin cambios: base `0x80000000` (display, LEDs, botones y contador).
- Lectura de instrucciones: sincronizada con flanco y habilitación.
- Lectura de datos: inicialmente preservar captura en cada flanco; escrituras por byte, respetando dato anterior en read-during-write.
- Accesos fuera de rango: bloquear alias y fijar una política comprobable para valor de retorno.

#### 20. Qué debemos probar y por qué

1. La ROM generada tiene las mismas **94 palabras hexadecimales** que el assembler, una a una.
2. El core observa cada instrucción en el mismo ciclo lógico que en el diseño original.
3. A y B ejecutan el juego con resultados equivalentes para estímulos de botones en los mismos ciclos.
4. En B, una escritura a una palabra de programa cambia su lectura posterior y un reset vuelve a poner la instrucción original. Eso permite demostrar que los FF son **reales**.
5. La RAM responde correctamente a escritura por bytes, lectura y colisiones lectura/escritura.
6. Los reportes de síntesis muestran la presencia de almacenamiento FF en B y permiten identificar register file, ALU, contador y módulos de memoria.

#### 21. Decisión de trabajo (no decisión final de mejor variante)

Desarrollar **A primero** por simplicidad de ejecución y probabilidades de cerrar pronto un flujo físico; continuar con **B** para cumplir la comparación obligatoria. **No declarar una ganadora sin área, frecuencia y resultados físicos reales.** Mantener el objetivo de `CLOCK_PERIOD=100 ns` y `FP_CORE_UTIL=40%` para las corridas base.

#### 22. Preguntas probables de defensa

- **¿Por qué la ROM combinacional tiene un registro de salida?** Porque el núcleo Espino estaba conectado a una memoria de lectura síncrona; el registro conserva la latencia esperada, pero el *contenido* ROM sigue siendo combinacional.
- **¿Por qué no basta `$readmemh` para un ASIC?** Porque es una acción del simulador/configuración FPGA, no un mecanismo no volátil que exista automáticamente en silicio fabricado.
- **¿Por qué hay RAM de datos si `game.s` no la usa?** Para preservar una arquitectura con acceso normal a memoria y poder comparar las dos estrategias con capacidad equivalente. Se reporta el uso real: cero palabras.
- **¿Por qué la unificada podría ocupar más área?** Porque almacenar 144×32 bits reescribibles requiere FF y lógica de selección/escritura, mientras las instrucciones fijas de A pueden sintetizarse como puertas lógicas. Debemos demostrarlo con métricas reales.
- **¿Qué significa que B sea unificada?** Que instrucciones y datos residen en el **mismo arreglo reescribible de FF**, no en una ROM de programa y una RAM separada.

**Trazabilidad:** los valores de capacidad propuestos son decisiones de diseño, no cifras impuestas por la pauta. No se ha escrito RTL definitivo ni realizado una corrida de síntesis.


---
### Etapa 4. De Pochoco FPGA a macro ASIC (diseño de adaptación)

**Fecha:** 29 de octubre de 2026. **Estado:** diseño revisado sobre archivos RTL reales, no compilado ni medido. Referencia de ingeniería: [Adaptacion_FPGA_a_ASIC_Proyecto3.md](referencias/Etapa5/Adaptacion_FPGA_a_ASIC_Proyecto3.md).

#### 23. ¿Qué es `asic_top.v`?

Un módulo superior orientado al macro digital, con terminales lógicos de reloj, reset, cuatro botones, cuatro LEDs, dos displays de 7 segmentos y SPI. No contiene pads de protección ESD, drivers físicos de LEDs, oscilador ni encapsulado. Es diferente de `game_top.v`, que fue preparado para pines físicos y convenciones de la Go Board. Para mantener clara esa separación, proponemos que los displays del ASIC expongan segmentos activos altos lógicos, mientras el antiguo wrapper FPGA mantiene la inversión que la placa necesita.

#### 24. Por qué cambia el reset

El SoC original genera `rst_ni` internamente con `reg [3:0] por_cnt = 0`, un estado inicial que en la FPGA puede provenir de la configuración del dispositivo. En un ASIC no podemos suponer que ese registro se encienda en cero. Se agrega un **puerto de reset externo activo bajo** y una **liberación sincronizada** al reloj. La CPU no debe ejecutar instrucciones hasta que la memoria esté preparada.

Para la memoria A, la ROM es fija y se puede arrancar al completar el reset. Para la B, un controlador programable en hardware escribe una palabra de instrucción por ciclo durante 144 ciclos nominales en el arreglo FF y solo entonces libera el procesador. La nueva secuencia evita resetear a la vez los 4.608 bits de memoria. A 100 ns por ciclo, 144 ciclos representan 14,4 microsegundos de carga nominal, sin contar sincronización. No es un tiempo de corrida medido. El contador de ciclos del juego permanecerá en reset durante esta carga para evitar descalibrar su cronómetro.

**Matiz importante:** el circuito de inicialización B debe funcionar mientras el procesador sigue reseteado, por lo que **no comparte exactamente el mismo reset efectivo del core**. Si el controlador también esperara `core_rst_ni`, se produciría un bloqueo circular.

#### 25. Qué hacemos con el banco de registros

`espino_register_file.v` original usa instancias de `SB_RAM40_4K`, que pertenecen a una familia de FPGA y no están disponibles como celdas estándar GF180. Se reemplazarán por registros con flip-flops; para RV32E solo necesitamos x0–x15, donde x0 es cero fijo y x1–x15 son 15 registros útiles de 32 bits (**480 bits lógicos**, sin incluir salidas y control). Deben preservarse **dos lecturas síncronas** y una escritura, así como el momento en que `espino_id_stage` libera su espera de operandos.

Una posible tentación es convertir las lecturas en combinacionales para simplificar el Verilog; eso **cambiaría la latencia del procesador** y es precisamente lo que evitaremos en la primera adaptación. Otro detalle es la colisión lectura/escritura en la misma dirección: debe caracterizarse antes de decidir forwarding.

#### 26. Botones, SPI y displays: tres decisiones distintas

- **Botones:** se agregará sincronización de dos flip-flops por entrada antes de la lógica MMIO. Esto reduce riesgo de metastabilidad, pero introduce latencia temporal. No se agregará antirrebote automáticamente: es otra función y podría modificar la medición del juego.
- **SPI:** `pochoco_spi_slave.v` ya sincroniza SCLK, MOSI y CS con tres etapas; preservaremos la lógica al principio y definiremos en las restricciones una velocidad SPI compatible con el reloj del ASIC.
- **Displays:** `pochoco_soc.v` invierte los siete segmentos por la polaridad *active-low* física de la placa. En el macro se proponen señales lógicas activas en alto y se mantiene aparte la conversión legacy de la FPGA. Los valores del juego y su codificación hexadecimal no cambian.

#### 27. Configuración de síntesis y consecuencias físicas

El enunciado fija `CLOCK_PERIOD=100 ns` (10 MHz) y `FP_CORE_UTIL=40%`; usaremos LibreLane + GF180MCU, con PDK exacto, biblioteca de celdas y versión de herramientas registrados cuando estén instalados. La configuración de LibreLane se construirá con `DESIGN_NAME=asic_top`, `CLOCK_PORT=clk_i`, fuentes Verilog ASIC explícitas y restricciones SDC para las entradas/salidas. **El `.pcf` de FPGA no define terminales del macro.**

El informe deberá justificar dónde se colocaron los terminales, reportar DRC/LVS/antena, corners y timing, y mostrar en layout las celdas del banco de registros, ALU y contador de ciclos. Conservaremos nombres `u_core.u_rf`, `u_core.u_id.u_alu` y `u_periph.cycles_q` o, si la síntesis aplana la jerarquía, un método verificable para localizarlos.

#### 28. Preguntas para comprender y defender

**¿Por qué no sirve el contador POR original?** Porque su valor inicial de encendido no está garantizado en un macro ASIC. Se necesita una fuente de reset real y una secuencia definida.

**¿Por qué B necesita cargador si es memoria de flip-flops?** Porque los FF son volátiles. La lógica de carga coloca físicamente el programa en los FF al salir de reset, sin depender de que el fabricante «incorpore» un `game.hex` a los FF.

**¿Por qué el register file no es una de las dos memorias del enunciado?** Porque la comparación A/B afecta el almacenamiento de **instrucciones y datos del SoC**, mientras que el banco de registros forma parte de la CPU y requiere un reemplazo común para ambas variantes.

**¿Se pueden conectar LEDs reales directamente al macro?** No: sus pines son terminales lógicos; un chip completo necesitaría pads, buffers y protección para manejar cargas externas.

**¿Por qué no eliminamos la sincronización SPI?** Porque SPI llega desde un dominio externo asíncrono respecto al reloj del procesador; los sincronizadores originales ya gestionan esa frontera bajo ciertos supuestos de frecuencia.

#### 29. Qué falta para llamar «implementada» a esta etapa

Crear el RTL y los scripts, ejecutar testbenches de reset/portabilidad/latencia de RF/boot B, comprobar celdas mapeadas y cerrar el flujo de LibreLane. **Ninguna de esas ejecuciones se ha hecho aún**; se ha concluido el diseño propuesto, no el desarrollo físico.


---
### Etapa 5 — Diseño de pruebas y experimentos (29-10-2026)

**Estado:** pruebas diseñadas, no ejecutadas. Referencia completa: [Plan_Pruebas_Experimentos_Proyecto3.md](referencias/Etapa5/Plan_Pruebas_Experimentos_Proyecto3.md).

#### Qué significa demostrar que el procesador funciona

El código sintetizable por sí solo no demuestra que un ASIC funcione. Habrá que combinar: pruebas unitarias (register file, memorias, reset, periféricos), simulación de integración (juego), equivalencia RTL/netlist sin retardos SDF y verificación física (timing, DRC, LVS, antena). Un resultado `PASS` exige que un test automático compare contra una condición esperada, con evidencia de la corrida.

La comparación de ciclos de una ronda correcta debe hacerse entre **RTL y post-síntesis de la misma variante**, con idéntico firmware y pulsaciones aplicadas en los mismos ciclos relativos a la salida de reset interno. B tarda ciclos adicionales en cargar su firmware: por eso no es correcto aplicar sus botones el mismo número de nanosegundos después del reset externo que a A y exigir equivalencia. El programa permite acelerar tres segundos **solo para simulación** si ambas se ejecutan con la misma configuración.

#### Casos esenciales para explicar en la defensa

- **Register file:** dos lecturas síncronas, una escritura; x0 constante cero; read-during-write y stalls de Espino. El RF P2 estaba duplicado físicamente por los dos puertos; la implementación ASIC debe conservar los resultados esperados, sin suponer condiciones no garantizadas.
- **Memorias:** A lee ROM constante con registro a la salida y escribe 16 palabras de RAM de datos. B carga el firmware en 144 palabras de FF antes de liberar CPU; se prueba reescritura de instrucciones y restauración tras reset.
- **Juego:** comienzo, LED one-hot, botón correcto, botón incorrecto (`EE`, repetir ronda), diez aciertos y promedio final. El bug del cruce signed en ~85,9 s (con 25 MHz) se prueba como diagnóstico histórico, **no** como causa confirmada del fallo físico.
- **Timing:** tres o más periodos incluyendo 100 ns, WNS y TNS de setup y hold por corners típico/lento; Fmax se deduce del menor período **probado** que cumple todos los corners. Una nueva configuración puede producir placement y área diferentes.
- **Physical design:** tres utilizaciones objetivo (propuesta 30/40/50 %), congestión vs utilización, área mínima exitosa, DRC/LVS limpios, antena justificada, layout con RF/ALU/contador identificados.
- **Costo:** multiplicar área física declarada en mm² por 23.000 USD/mm². Este método lineal ignora pads, márgenes, rendimiento de obleas, costos fijos y encapsulado.

#### Preguntas para preparar

1. **¿Por qué no basta un testbench RTL?** Porque no detecta fallos de mapeo físico/timing/layout; además necesitamos equivalencia con el netlist sintetizado.
2. **¿Por qué se usa ciclo cero tras reset interno?** Porque el cargador B agrega latencia de arranque independiente de las instrucciones del juego.
3. **¿Qué significan WNS y TNS?** WNS es el peor slack de los caminos comprobados y TNS suma slacks negativos; se requiere WNS≥0 y TNS=0 para setup y hold.
4. **¿Cómo demostrar que B utiliza FF?** Inspeccionando netlist y reporte de celdas tras síntesis, además de simular lectura/escritura.
5. **¿La frecuencia máxima equivale siempre al inverso del período solicitado?** No. Solo reportaremos Fmax derivada del menor período que haya cerrado timing en todos los corners probados.

**No registrar PASS, áreas, frecuencia o signoff sin logs.**

## Verificación posterior en el Mac

### Qué comprobamos en el Mac

El MacBook Air tiene chip M4, 10 núcleos y 24 GB de memoria. Dispone de Git e Icarus Verilog 13.0. Python 3.13.15 está instalado con Homebrew, aunque la terminal selecciona por defecto Python 3.9.6 de Apple. Usaremos explícitamente el Python adecuado para LibreLane.

El assembler propio transforma game.s en 94 instrucciones. El archivo regenerado coincide byte por byte con las dos copias de game.hex del Proyecto 2. Eso demuestra que podemos reproducir el programa sin depender del computador Windows donde se desarrolló.

La simulación de 2000 ciclos comprobó la carga de las instrucciones inicial y final, la liberación del reset FPGA, una dirección de instrucciones definida, el encendido inicial de los cuatro LED y el avance del contador. No cubre todavía las diez rondas, los botones ni un ASIC.

### Por qué había una ruta de Windows

El módulo superior referenciaba C:/Users/wille/Proyecto2/pochoco_soc-main/sw/game.hex. Esa dirección pertenece a otro computador. En la copia del Proyecto 3 se sustituyó por sw/game.hex y las pruebas se ejecutan desde pochoco_soc-main. El código original quedó intacto.

Icarus advierte que el archivo tiene 94 palabras para una memoria de 512. Las posiciones restantes no quedan definidas por ese archivo. La prueba de arranque utiliza las instrucciones cargadas; para el ASIC tendremos que definir explícitamente el contenido y el arranque de la memoria.

### Qué aporta Linux mediante Docker

macOS y Linux son sistemas distintos. Docker Desktop prepara una máquina Linux y permite ejecutar dentro de ella las herramientas del flujo. La versión Apple Silicon aprovecha la arquitectura ARM del M4. Un contenedor reúne herramientas y dependencias; no convierte automáticamente un diseño FPGA en ASIC.

Elegimos Docker Desktop por su interfaz gráfica y porque la guía de LibreLane para Mac lo utiliza. Colima también ofrece un motor Docker mediante una interfaz centrada en terminal. La elección facilita la operación; no es una medición comparativa de velocidad. Referencias: [Docker para Mac](https://docs.docker.com/desktop/setup/install/mac-install/), [Colima](https://github.com/abiosoft/colima) y [LibreLane para Mac](https://librelane.readthedocs.io/en/stable/installation/docker_installation/installation_macos.html).

### Qué debe cambiar para ASIC

El banco de registros usa memorias SB_RAM40_4K específicas de la FPGA iCE40. Su modelo de simulación permite comprobar el diseño FPGA; esas primitivas no son celdas de GF180MCU. La adaptación deberá conservar la latencia de lectura que espera Espino.

El reset actual depende de un contador inicializado al encender. El plan ASIC propone reset externo activo en bajo y liberación sincronizada. La memoria A separará ROM y RAM; la B usará memoria unificada de flip-flops con carga de arranque y CPU detenida mientras carga. Son diseños pendientes de implementación y verificación.

### Relación entre ciclos y segundos

El programa utiliza 75000000 ciclos para su espera inicial y 2500000 ciclos por décima. A 25 MHz corresponden a 3 segundos y 0,1 segundos. Con un reloj de 100 ns, equivalente a 10 MHz, esas mismas constantes representarían 7,5 segundos y 0,25 segundos. Debemos resolver con el enunciado si se recalibran las constantes o se conserva otro criterio de comparación. Estos tiempos se calcularon a partir del código; no son mediciones de una corrida ASIC.

El contador tiene 32 bits y el programa usa comparaciones con signo. El umbral 2^31 se alcanza aproximadamente a los 85,9 segundos a 25 MHz. Las pruebas completas deberán investigar el efecto de cruzarlo y el desbordamiento posterior.

### Preguntas para la defensa

- ¿Qué demuestra que el programa es reproducible? La igualdad byte por byte de los tres archivos hex tras ejecutar el assembler propio.
- ¿Qué demuestra la primera simulación? El arranque FPGA definido dentro del alcance indicado; todavía no el juego completo.
- ¿Por qué no basta con sintetizar el código FPGA? Contiene primitivas y supuestos de inicialización que deben sustituirse para GF180MCU.
- ¿Cómo se compararán las memorias A y B? Con el mismo programa, estímulos y referencia temporal definida, y resultados físicos separados por arquitectura.

### Versiones y comprobación física

LibreLane 3.0.17 y su revisión compatible de GF180MCU están descargados. Fijar versiones permite comparar corridas hechas con las mismas herramientas y bibliotecas. Docker ya ejecutó el ejemplo oficial spm con GF180MCU hasta generar GDS. Esa corrida comprueba el flujo físico para el ejemplo; Espino aún requiere implementación y verificación propias.

### Primera prueba de Docker

Docker Desktop 4.97.0 ejecutó hello-world correctamente como linux/arm64. Su motor informa Linux aarch64 y 4 CPU. Esto confirma que el entorno Linux funciona en la arquitectura del M4. Una prueba hello-world no verifica las herramientas de síntesis y diseño físico: para eso se ejecuta por separado el ejemplo oficial spm con GF180MCU.

Los espacios en las rutas provocaron un error al leer la configuración de GF180MCU. El lanzador del proyecto utiliza /work dentro del contenedor para ofrecer rutas sencillas a las herramientas. El proyecto conserva su ubicación habitual en el Mac.

### Resultado físico del ejemplo oficial

El ejemplo spm terminó con cero errores en Magic DRC, LVS, antena y enrutamiento. Setup y hold tuvieron márgenes positivos de aproximadamente 0,4411 ns y 0,3788 ns. El flujo generó GDS usando 24 ns de reloj y 38 por ciento de utilización objetivo.

DRC comprueba reglas geométricas; LVS compara la conectividad del layout con el circuito de referencia; antena analiza estructuras que pueden acumular carga durante fabricación. La revisión DRC de KLayout se omitió por falta de configuración en este PDK, por lo que no debe contarse como aprobada.

Estos resultados pertenecen al ejemplo de instalación. La comparación de las arquitecturas A y B de Espino, sus ciclos, áreas y condiciones finales de 100 ns y 40 por ciento sigue pendiente de implementar y cotejar con el enunciado.

## Guion provisional para la defensa

1. Presentar el juego, Espino y el objetivo de convertir Pochoco en un macro ASIC. Explicar la diferencia entre terminales lógicos y pads.
2. Mostrar las dependencias FPGA encontradas, los avisos reales del flujo y la solución de reset, banco de registros y memoria.
3. Explicar A y B, el uso real de instrucciones y datos, el cargador y la latencia. Incorporar las métricas A/B cuando existan.
4. Explicar las cinco celdas dominantes, el área por módulo y la contribución del contador, con trazabilidad de las instancias.
5. Presentar el barrido de reloj, la ruta crítica, la modificación RTL y su efecto medido. Derivar las constantes del juego para 10 MHz.
6. Presentar floorplan, alimentación, terminales, congestión y costo con las unidades y limitaciones del ejercicio.
7. Mostrar DRC, LVS, antenas y layout anotado de Espino. El ejemplo spm solo sirve como evidencia de instalación.
8. Demostrar la equivalencia RTL/netlist por ciclos y la recuperación de una ronda incorrecta. Cerrar con decisiones justificadas y limitaciones reales.

Este guion todavía necesita las tablas, capturas y resultados del ASIC. No se han creado diapositivas finales ni el informe académico final.


## Primera adaptación RTL implementada y probada en el Mac

El 29 de octubre se implementó la primera capa ASIC con autorización del usuario. El [informe de esta etapa](Adaptacion_RTL_Etapa1.md) contiene archivos, pruebas, resultados y límites. No confundir este resultado con las especificaciones históricas anteriores ni con un cierre físico del procesador.

### Cómo explicar el cambio en la defensa

El procesador conserva su pipeline. Se reemplaza el almacenamiento específico de FPGA del banco de registros por FF descritos de forma portable. Se preservan dos lecturas síncronas, una escritura y el ciclo de espera del controlador. En una colisión, la salida recibe el valor anterior; no añadimos forwarding. x0 es constante. Los otros quince registros y ambas salidas se ponen en cero mediante reset: esto hace explícito un comportamiento que el RF anterior no tenía, pues ignoraba esa entrada.

El reset externo sustituye al contador POR inicializado. Se afirma sin esperar reloj y se libera de forma sincronizada. Un segundo registro mantiene detenido al core hasta que la memoria indique disponibilidad. El contador del juego comparte el reset del core; por eso la espera de carga no altera la medición del juego. El cargador usa el reset anterior, no el del core, para poder trabajar mientras este permanece detenido.

Los botones atraviesan dos FF sin introducir antirrebote. Esta latencia se ensaya y deberá mantenerse igual en RTL y netlist. La simulación no reproduce la metastabilidad analógica. Los displays exponen segmentos activos altos y, tras reset, muestran 00. SPI conserva su implementación original y superó una transacción completa con reloj externo lento.

### Qué podemos sostener con evidencia

Pasaron siete ejecuciones: RF, reset/botones, tres casos de arranque, diagnóstico de entradas/salidas y comparación de pipeline. El RF pasó 1903 ciclos de modelo independiente y 1872 comparaciones contra iCE40. El pipeline pasó 10000 ciclos iniciales del juego con el RF antiguo y el nuevo, sin diferencias observadas en control, operandos válidos, escrituras y periféricos. Los archivos originales de Proyecto 2 conservan sus 38 huellas.

La comparación comparte wrapper y memoria de simulación: aísla la sustitución del RF. No prueba rondas completas, netlist, timing, DRC o LVS. En esa primera etapa todavía no existía la memoria ASIC; su modelo de pruebas usa un archivo y no debe llegar al flujo físico. Las memorias reales se implementaron después, como se describe a continuación. El script rechaza esa inclusión accidental sin una opción explícita de simulación.

La comprobación de síntesis genérica se completó después de resolver los permisos: reset, botones, RF y SoC con memoria externa pasaron con Yosys 0.62. El RF produjo 480 FF con habilitación y 64 FF de salida, confirmando los 544 bits previstos. Reset produjo tres FF y botones ocho. Son FF genéricos antes del mapeo a la biblioteca GF180; todavía no determinan área física, frecuencia o consumo.

### Preguntas de práctica de esta etapa

1. ¿Por qué cambiar la lectura del RF a combinacional puede romper el procesador? Porque ID y el controlador esperan un ciclo de lectura síncrona; conservar la interfaz no basta si cambia su tiempo.
2. ¿Por qué no sirve `$readmemh` como cargador de un ASIC? Porque leer un archivo durante simulación no crea un mecanismo físico de carga al encender.
3. ¿Por qué el contador del juego debe esperar a la memoria? Para medir desde el comienzo real de ejecución, sin sumar la preparación del programa.
4. ¿Por qué se bloquean solicitudes fuera del core? El IF original genera `~stall` incluso bajo reset; el SoC impide que esa señal acceda a la memoria antes de tiempo.
5. ¿El test de 10000 ciclos demuestra que el juego funciona completo? No: comprueba el arranque y la espera inicial y aísla el reemplazo del RF. Las rondas correctas/erróneas y la netlist requieren pruebas posteriores.


### Cómo defender la primera síntesis

La advertencia «Replacing memory regs_q with list of registers» indica que Yosys convirtió el arreglo del RF a registros, coherente con nuestra decisión de usar FF. No significa que se haya inferido una memoria FPGA. Está conservada con archivo y línea en el informe de etapa. Las comprobaciones no detectaron latches, primitivas SB ni cajas negras.

Es necesario distinguir tres niveles: descripción y simulación RTL; síntesis genérica, completada para estos bloques; y mapeo/implementación física GF180 del macro completo, todavía pendiente. No usar el recuento de FF para inventar área o timing. En esa primera síntesis faltaban las memorias A/B. Su síntesis genérica posterior se describe a continuación; las mediciones físicas siguen pendientes.


## Memorias A/B implementadas: argumentos para la defensa

Consultar [Memorias A/B](Memorias_AB.md) para la evidencia actual. A separa constantes de programa y datos; B almacena ambos en el mismo arreglo de FF. El juego utiliza 94 instrucciones; las capacidades provisionadas son 128 instrucciones y 16 datos. Las 34 posiciones de reserva contienen NOP. No afirmar que las 16 palabras de datos son una demanda medida del juego: las pruebas de su intervalo inicial observaron solo MMIO.

La ROM se genera automáticamente desde game.s mediante el assembler original. En A esa función combinacional alimenta una salida registrada para preservar la latencia del procesador. En B, la ROM solo proporciona palabras al cargador; las instrucciones ejecutadas después salen del arreglo que permite escrituras por bytes. Una prueba modifica las 144 palabras de B, verifica lo escrito y comprueba que el reset reconstruya programa y datos.

B carga una palabra por ciclo durante 144 ciclos. Eso evita resetear directamente todos sus 4608 bits; aun así hay lógica, control y multiplexores que deben medirse. El contador del juego espera a la CPU. La prueba comparativa alinea sus ejecuciones con 143 ciclos de diferencia entre resets externos y comprueba 20000 ciclos sin diferencias. Esto no demuestra todas las rondas ni equivalencia formal.

La síntesis comprobó cada bit de almacenamiento mediante su conductor FF.Q: 512 en A y 4608 en B, sin constantes o alias. Además de almacenamiento, A tiene 64 FF de salida y uno de disponibilidad; B añade 64 de salida, ocho de índice y uno de disponibilidad. Totales aislados 577/4681 y macros 1329/5433. Son FF genéricos. La lógica combinacional, los buffers y la colocación pueden cambiar la comparación de área; todavía no hay un ganador físico medido.

Preguntas útiles: ¿por qué una ROM combinacional necesita salida registrada? Para conservar el protocolo de fetch. ¿Por qué el reset no necesita alcanzar cada bit de B? Porque el cargador los reescribe antes de liberar el core. ¿Qué prueba que B es RAM? Escrituras y lecturas comprobadas y comprobación de 4608 salidas FF independientes en netlist. ¿La diferencia de FF es la diferencia de área? No; falta mapear y realizar el flujo físico con las mismas condiciones.

El mismo ensayo de interfaces pasó sobre RTL y netlists genéricas: 5800 ciclos, incluida reprogramación y restauración de B. Esto comprueba la conducta en los estímulos ensayados, no todas las secuencias posibles ni equivalencia formal. La prueba de juego RTL/netlist seguirá siendo necesaria con firmware y estímulos de rondas idénticos.


## Juego a 10 MHz: resultados actuales y defensa

El firmware de producción vive en `firmware/asic/game.s`; el assembler y la referencia FPGA se conservan. Tres segundos a 10 MHz equivalen a 30 000 000 ciclos y una décima a 1 000 000. La ROM usa ahora 95 instrucciones y 33 NOP; las capacidades ROM128/RAM16 y FF144 no cambiaron. El generador predeterminado toma esta copia ASIC. Se comprobaron los valores en las instrucciones codificadas, además de sus textos fuente.

### Qué corregimos y qué demuestra la prueba

La espera original comparaba instantes absolutos con signo. Un inicio 0x7FFFFFE0 más 30 000 000 produce un límite negativo 0x81C9C360; tras solo 24 ciclos el contador sigue siendo positivo y `BLT` deja de esperar. La copia ASIC guarda el inicio, resta módulo 2³² y compara el tiempo transcurrido. Añade una instrucción sin ampliar la ISA. Funciona para la duración configurada, menor que 2³¹, con sondeo continuo antes de ese transcurrido.

Veinte casos con la ALU real de Espino incluyen los límites 2³¹ y 2³²: dos fallos del algoritmo anterior y cero del corregido. La comprobación también decodifica la secuencia del hex. Esto demuestra el defecto aritmético; no prueba que causara los cuelgues históricos de la FPGA. La división de reacciones de al menos 2³¹ ciclos conserva su limitación heredada: alrededor de 214,75 s a 10 MHz puede interpretarse como negativa.

### Por qué hay dos pruebas del juego

La partida completa usa `simulation`: espera 3000 ciclos y décima 100. Ambos umbrales se dividen por 10 000, mientras las instrucciones conservan sus latencias. Se comprueban diez aciertos, dos errores/reintentos, botón mantenido, una saturación a 99, suma 162, promedio entero 16 y tres resets. Las salidas lógicas coinciden ciclo a ciclo con la netlist genérica del macro completo, en A y B.

La prueba `wait_only` responde específicamente a la autorización de acelerar solo la espera inicial: usa 3000 ciclos de espera, pero conserva 1 000 000 por décima. Verifica acierto/error/reintento y segundo acierto. Sus respuestas rápidas son cero décimas. Como escribir `00` no siempre cambia los segmentos, también compara solicitudes, direcciones y datos de MMIO y el ciclo de escritura del resultado. Se observaron 302 ciclos desde el LED activo al resultado correcto y 269 al resultado `EE`, iguales en RTL/netlist de cada arquitectura.

La referencia de corrección semántica calcula el resultado con muestras del contador real, no supone que el retardo externo de pulsación sea idéntico al tiempo que mide el programa. El error no debe aumentar `x10` ni la suma `x12`; mantener el botón no debe avanzar otra ronda. El promedio se trunca: 162 dividido por diez da 16.

### Cómo interpretar ciclos y flip-flops

La partida completa dura 65 291 ciclos en A y 65 577 en B incluyendo cargas y resets. El ensayo wait_only dura 10 623/10 766. Eso no significa que la CPU B ejecute el juego más lentamente: B carga 144 palabras y A anuncia disponibilidad al primer flanco. La comparación pertinente es RTL A/netlist A y RTL B/netlist B, con el mismo reset y los mismos botones por ciclo.

La síntesis de producción jerárquica registra 1329/5433 FF genéricos; las síntesis aplanadas con firmware de prueba registran 1327/5433. Cambian tanto las opciones como la ROM. No atribuimos los dos FF a una causa única ni interpretamos el conteo como área física. La capacidad de almacenamiento comprobada sigue siendo 512/4608 bits y los módulos de CPU, periféricos y memorias no cambiaron en esta etapa; la ROM sí se regeneró.

### Preguntas que debemos poder responder

1. ¿Qué prueba la comparación post-síntesis? Que para los estímulos ensayados el macro sintetizado conserva las salidas por ciclo; wait_only comprueba además los ciclos MMIO de las rondas. No es equivalencia formal ni cierre físico.
2. ¿Por qué no afirmamos haber simulado tres segundos reales por espera? Las pruebas del juego usan perfiles acelerados; las constantes de producción sí se verifican en el hex.
3. ¿Por qué conservar la unidad de reacción en una prueba separada? Porque la pauta permite acelerar la espera inicial; wait_only mantiene la décima de producción y comprueba acierto, error y reintento bajo esa condición.
4. ¿Por qué queda trabajo después de estos PASS? Las netlists son genéricas y sin SDF. Debemos repetir la prueba tras mapear a GF180, medir timing/área y completar DRC, LVS, antenas y layout.
5. ¿Qué sigue? Restricciones y mapeo, tres períodos, tres utilizaciones, mejora RTL de ruta crítica medida, cierre final a 100 ns/40 %, informe y defensa.

El [informe del juego](Juego_10MHz.md) y el [resumen de evidencia](../evidence/asic_game/results.json) contienen los resultados vigentes. Los nueve casos del generador ROM, seis de perfiles, cuatro simulaciones de producción, cuatro síntesis y el ensayo de interfaces post-síntesis también pasaron. La checklist queda en 16/17; el cierre físico y la entrega siguen pendientes.
