# Cuaderno de continuidad del Proyecto 3

Estado al 29 de octubre de 2026, zona horaria America/Santiago. Objetivo: desarrollar el Proyecto 3 ASIC a partir del Proyecto 2 de Espino y del juego de reacción, conservando el original. Estado vigente: firmware a 10 MHz, juego completo y comparación RTL/netlist genérica A/B aprobados; checklist 16/17. El mapeo GF180 y cierre físico siguen pendientes. Las secciones de preparación y memorias conservan sus antecedentes históricos; consultar la actualización al final.

## Ubicaciones y procedencia

La carpeta de trabajo es /Users/ics/Desktop/Universidad/UAndes/Segundo Semestre - 2026/Arquitectura de Computadores/Proyecto 3. El original está en la carpeta hermana Proyecto 2. Su commit de referencia es 4d94b4e2f63c91d248e68350cdf640c3f7a86356.

La copia portable está en baseline/proyecto2. Se excluyeron el historial Git, el informe PDF y el log de síntesis antiguo. El único cambio de RTL es la ruta de game.hex en game_top.v; evidence/portabilidad.patch registra la diferencia. evidence/proyecto2_original_sha256.json contiene las huellas de 38 archivos originales.

La conversación de procedencia se llama Planificar proyecto ASIC, identificador 6ae35b1c-d08c-83e9-8b83-fdcd6ec80b13. Se recuperaron sus mensajes recientes y el usuario aportó Proyecto3_Todos_los_Archivos.zip. El kit Etapa 5 y los documentos originales están incorporados en docs/referencias; las diez huellas de su manifiesto coinciden.

## Restricciones y autorizaciones

Usar exclusivamente GitHub icruzat1 desde su sesión de VS Code. La interfaz de VS Code mostró icruzat1 (GitHub), y el remoto del original es https://github.com/icruzat1/Proyecto2-Arqui.git. No se ha llamado al conector GitHub de oficina.

El usuario autorizó Docker Desktop para Apple Silicon, LibreLane y GF180MCU, y crear icruzat1/Proyecto3-Arqui privado. Los términos de Docker se presentarán antes de aceptarlos. Para nuevas acciones externas o cambios importantes, preguntar o comprobar según el alcance autorizado.

No modificar el Proyecto 2 original ni la configuración global de Git. El repositorio nuevo tiene main y el commit inicial a52aaa3, con la copia FPGA portable y la prueba de arranque. Su identidad local de commits usa icruzat1 y su dirección GitHub noreply basada en el identificador público 321519839. Se desactivó en este repositorio la reutilización de ayudantes globales de credenciales; las operaciones remotas se harán mediante VS Code personal.

No preparar prompts por adelantado. Conversar cada tarea y redactar su prompt justo antes de ejecutarla cuando sea necesario. Mantener ambos cuadernos y la checklist, y terminar las respuestas con una recomendación breve de potencia de pensamiento.

## Entorno comprobado

macOS 27.0.1, ARM64, MacBook Air M4 con 10 núcleos y 24 GB. Aproximadamente 283 GiB libres al comenzar. Git 2.54.0 e Icarus Verilog 13.0 disponibles. Python predeterminado 3.9.6; Python 3.13.15 disponible en /opt/homebrew/opt/python@3.13/bin/python3.13. No estaban disponibles Docker, Colima, GitHub CLI, Yosys ni Verilator en PATH.

## Verificaciones realizadas

El assembler regeneró 94 palabras idénticas a assembler/game.hex y pochoco_soc-main/sw/game.hex, SHA256 e5aca0ab29440ddbe4898a54ba2b0c3d79f43ca19bab1a78cafc0b0b1c3d28d6. La elaboración completa con Icarus terminó sin errores.

El modelo iCE40 se leyó del archivo local oss-cad-suite-darwin-arm64-20260826.tar, miembro oss-cad-suite/share/yosys/ice40/cells_sim.v. No se instalaron ni ejecutaron los binarios de ese archivo. El modelo temporal está fuera del repositorio.

scripts/check_baseline.py reproduce el programa y ejecuta sim/tb_proyecto2_startup.v. El arranque pasó en 2000 ciclos a 25 MHz: instrucciones cargadas, reset liberado, PC definido, LED iniciales y contador activo. Existe una advertencia por las 94 palabras del programa frente a las 512 de memoria. Falta verificar juego completo y memoria fuera del programa. evidence/baseline_results.json y evidence/startup.log conservan el resultado.

La comparación de las 38 huellas confirmó que el original no cambió durante la preparación y las pruebas.

## Decisiones técnicas y requisitos confirmados

Plan recuperado: memorias A con ROM y RAM, B unificada con flip-flops y controlador de carga; reset externo activo en bajo, liberación sincronizada, botones sincronizados; conservar latencia síncrona del banco de registros. Una arquitectura por corrida física.

El enunciado confirma 100 ns y 40 por ciento para la corrida final y exige GF180MCU; no impone una variante ni una biblioteca concretas. Se mantiene para el desarrollo gf180mcuD y gf180mcu_fd_sc_mcu7t5v0 con las versiones ya fijadas. La matriz docs/Requisitos_Proyecto3.md registra las exigencias completas.

La referencia FPGA conserva sus constantes de 25 MHz. La copia ASIC ya cumple la recalibración exigida para 100 ns: 30000000 ciclos por espera y 1000000 por décima. Se corrigió la comparación de espera alrededor de 2^31 mediante tiempo transcurrido; ver actualización actual e informe Juego_10MHz.md.

## Siguiente trabajo

Preparar restricciones y mapeo GF180 con firmware de producción, repetir la comparación funcional sobre las netlists mapeadas y avanzar al floorplan. Después ejecutar barridos de al menos tres períodos y tres utilizaciones, identificar y mejorar una ruta crítica RTL, medir resultados y cerrar timing/DRC/LVS/antenas. El punto final exigido es 100 ns y 40 %. Faltan layout anotado, área/costo e informe y defensa. No redactar prompts futuros.

## Entorno instalado y versiones fijadas

LibreLane 3.0.17 y Ciel 2.6.1 están instalados en .venv con Python 3.13.15. La comprobación de dependencias pasó. config/requirements-macos-arm64.lock.txt registra todas las versiones y config/environment.lock.json fija las principales.

Ciel descargó y habilitó GF180MCU 54435919abffb937387ec956209f9cf5fd2dfbee, revisión que requiere LibreLane 3.0.17. Para la prueba de entorno se prepararon gf180mcuD y gf180mcu_fd_sc_mcu7t5v0. Se comprobó la presencia de configuración, bibliotecas de tiempo, LEF, GDS y LEF tecnológico. Este PDK conserva la carpeta libs.tech/openlane; LibreLane admite explícitamente esa ubicación alternativa. El enunciado permite la biblioteca fijada para el desarrollo; habrá que documentar la empleada en las corridas finales. La prueba física del ejemplo ya se completó; sus resultados se detallan al final de este cuaderno.

## Docker Desktop instalado

Docker Desktop 4.97.0 está instalado en Aplicaciones. El usuario trasladó la aplicación desde el instalador y completó el inicio de sesión. El motor Docker 29.9.2 devuelve Linux aarch64 y 4 CPU. Se configuraron aproximadamente 12 GiB de memoria; el motor informa 12481122304 bytes disponibles. La prueba hello-world pasó en linux/arm64.

Se conservó el límite de disco mostrado por Docker, 460,4 GiB asignados según el uso. La propuesta de reducirlo a 80 GiB mostró una advertencia de borrado de imágenes, contenedores y volúmenes; esa reducción se canceló.

La imagen LibreLane 3.0.17 está descargada y su arquitectura es arm64. Su huella es sha256:24640bd645ae992fa22d4a3e18fde10d728763c78fb140184f9975aa6c7d3e5e. config/environment.lock.json fija esa imagen para las ejecuciones posteriores.

## Ruta del contenedor y prueba física de entorno

El lanzador predeterminado intentó utilizar la carpeta PDK predeterminada del usuario. Al indicar el PDK local apareció una incompatibilidad de la configuración antigua GF180MCU con los espacios de las rutas del Mac. Se resolvió preparando scripts/run_librelane.py: monta únicamente Proyecto 3 como /work dentro de Linux y utiliza /work/.pdk. No se modificaron LibreLane ni los archivos del PDK.

Se completó una corrida del ejemplo oficial spm de LibreLane 3.0.17, con gf180mcuD y gf180mcu_fd_sc_mcu7t5v0. El ejemplo usa 24 ns y 38 por ciento de utilización. Sus resultados verifican el entorno y no corresponden al procesador Espino ni a las condiciones finales del curso. Los archivos están en build/environment/spm, excluidos de Git.

## Repositorio personal

VS Code mostró de nuevo la única cuenta icruzat1 (GitHub). Se eligió explícitamente Publish to GitHub private repository para icruzat1/Proyecto3-Arqui, y VS Code creó el remoto origin con esa URL. La subida inicial pidió una contraseña.

Se retiró la opción local que imponía el nombre de usuario en las consultas de credenciales, para que el proveedor de autenticación de VS Code gestione su propia sesión. El ayudante global de credenciales permanece desactivado para este repositorio. La rama main se subió correctamente desde VS Code. El seguimiento origin/main está activado y se verificó que el commit inicial publicado coincide con el local: db4e93373b5d2ff493555a52296acfb0db7fe942. No se llamó al conector GitHub de oficina.

El original se llama Proyecto 2 por decisión del usuario. Sus 38 huellas se conservaron al renombrarlo.

## Modelo y aviso de aprobación

Para configurar el entorno se recomienda GPT-6.1 Sol con High. Para memorias, reset, equivalencia y depuración ASIC difícil, Astra con Extra High, si está disponible. Estas son recomendaciones; no se cambió el selector del usuario. Fuente: [Modelos en ChatGPT Work](https://learn.chatgpt.com/docs/models).

El usuario vio un aviso de aprobación pendiente sin una solicitud visible. El estado de este chat devolvió activo con activeFlags vacío. No quedó una solicitud abierta del agente. La causa del aviso no está confirmada. Ese aviso se investigó durante la preparación inicial; las pruebas y publicaciones posteriores se registran en sus secciones correspondientes.

## Resultado de la corrida GF180MCU

El flujo Classic del ejemplo spm completó su ejecución y generó GDS. El informe final aprobó antena, LVS y DRC mediante las comprobaciones disponibles. Magic DRC, LVS, antenas y DRC de enrutamiento terminaron con cero errores o redes infractoras. El peor margen setup fue 0,4411 ns y el peor margen hold fue 0,3788 ns.

KLayout DRC se omitió porque el PDK no define KLAYOUT_DRC_RUNSET; no se presenta como una comprobación aprobada. También se conservaron las otras advertencias del ejemplo en evidence/gf180_environment_summary.json. evidence/gf180_environment_metrics.json contiene las métricas completas y evidence/gf180_manufacturability.rpt conserva el informe final.

La imagen Linux contiene Python 3.13.9 y Ciel 2.4.0; el entorno de administración del Mac usa Python 3.13.15 y Ciel 2.6.1. LibreLane es 3.0.17 en ambos. La huella de la imagen fija sus herramientas internas.

El repositorio es https://github.com/icruzat1/Proyecto3-Arqui y se creó con la opción privada de VS Code. Todas las operaciones remotas se realizaron desde esa sesión personal; el conector GitHub de oficina no se usó.

## Integración del kit y requisitos

El kit Etapa 5 pasó la comprobación de integridad y sus diez entradas de manifiesto coinciden. Se compararon 30 archivos de código con Proyecto 2, sin diferencias. Se conservaron los documentos fuente sin modificar en docs/referencias/Etapa5 y el kit íntegro en docs/referencias. Sus instrucciones y estados antiguos son históricos; no sustituyen las preferencias actuales del usuario ni esta continuidad.

El cuaderno de estudio combina las cinco etapas anteriores y la verificación del Mac, con un guion provisional de ocho partes. Se corrigió una errata de hash en la copia integrada. La matriz de requisitos recoge las secciones 3.1 a 3.7 y la rúbrica completa. El informe anterior del Proyecto 2 tiene cero bytes tanto en el ZIP como en el Mac; no bloquear la implementación por ese informe, pero incorporarlo si el usuario dispone de una copia legible.

La entrega y defensa están fijadas para el 4 de noviembre de 2026 a las 10:30. El enunciado exige una mejora implementada de la ruta crítica, al menos tres puntos de reloj y tres utilizaciones o tamaños de die. Deben reportarse WNS y TNS de setup y hold en el corner típico y el más lento, además de cumplir los corners requeridos por el flujo. Fmax solo puede deducirse del menor período probado que cierre. La estimación 23000 USD/mm² es un supuesto didáctico, no una cotización.

La propuesta A de 128 instrucciones y 16 datos y la B de 144 palabras son capacidades provisionales. El enunciado recomienda máximos de 256 instrucciones y 64 datos; cualquier exceso debe justificarse. El SPI bootloader y la simulación SDF son opcionales. El programa actual tiene 94 instrucciones y cero palabras de RAM ordinaria observadas estáticamente; hay que aportar evidencia de ejecución y conservar las dos estrategias exigidas.

No se modificó RTL, assembler, configuración física ni firmware durante esta integración. No se prepararon prompts por adelantado. Al terminar esa integración documental, la checklist quedó en 13 de 17 pasos. El avance posterior de RTL se registra a continuación.


## Primera etapa RTL: registro histórico (commit 17456d4)

El usuario cambió a Astra Ultra y autorizó continuar con la primera adaptación. Se implementaron asic_top, reset_ctrl, btn_sync, el SoC con interfaz de memoria externa y el RF portable. Los siete archivos restantes del core y los dos periféricos son idénticos a baseline. No se modificaron firmware, assembler, original Proyecto 2, configuración global de Git ni las referencias del kit.

En esa primera etapa, la memoria asic_memory de producción quedó pendiente de A/B; la implementación posterior se registra al final. Para elaborar y simular el top se añade explícitamente sim/asic_stage1/asic_memory.v, protegido con ASIC_STAGE1_SIM. No sintetizar ese modelo ni interpretar su demora como carga real de B. El manifiesto config/rtl_stage1.f contiene solo producción y falla al elaborar asic_top sin una memoria real.

scripts/check_asic_stage1.py pasó siete pruebas: RF (1903 ciclos, 1872 diferenciales contra iCE40), reset/botones (73 comprobaciones), arranque con demoras 0/5/144 (dos arranques de 2000 ciclos por caso), diagnóstico MMIO/SPI y comparación de pipeline de 10000 ciclos. La comparación usa el mismo wrapper y sustituye solamente RF; no es post-síntesis ni juego completo. evidence/asic_stage1 conserva logs, hashes y resultados. El programa original sigue teniendo 94 instrucciones idénticas. Las 38 huellas del original coinciden y baseline no tiene diferencias Git.

scripts/check_asic_stage1_synthesis.py se ejecutó con éxito al regresar el usuario y conceder los permisos de comunicación y escritura necesarios. Usa la imagen fijada con red deshabilitada y sin descargar imágenes. Los cuatro bloques reset_ctrl, btn_sync, espino_register_file y pochoco_soc pasaron síntesis genérica con Yosys 0.62, revisión 7326bb7d6641500ecb285c291a54a662cb1e76cf. RF: 544 FF genéricos (480 con habilitación y 64 de salida); reset: tres; botones: ocho. No latches, primitivas SB ni cajas negras. Los check -assert terminaron sin problemas.

La advertencia de convertir regs_q a lista de registros es esperada; aparece en línea 52 de los cuatro logs porque se leen todos los fuentes antes de podar jerarquía. evidence/asic_stage1_synthesis conserva los logs, scripts Yosys, resultados, versión y hashes. Los conteos son genéricos por definición de módulo, no área GF180 ni timing. No se sintetizó el macro completo con memoria A/B, ni se comprobó equivalencia post-síntesis.

Al cerrar esa primera etapa, la checklist quedó en 14/17 y el trabajo siguiente eran las memorias A/B. El riesgo previo de SPI (byte_done sin condicionar por cs_active) sigue documentado y sin modificar; requiere reproducción dirigida antes de decidir una corrección.

### Permisos y publicación

Mientras el usuario estuvo AFK se guardaron las solicitudes y no se enviaron otras. Al volver autorizó explícitamente los permisos pendientes, la síntesis y la subida al repositorio personal. Ya se concedieron escritura para Proyecto 3 y .git, acceso al socket local y comunicación. Docker Engine 29.9.2 respondió correctamente; no fue necesario reinstalar ni cambiar su configuración.

Los errores anteriores de acceso se conservan en evidence/asic_stage1/*_access_probe.log como antecedentes históricos. No deben interpretarse como bloqueos actuales. La cuenta icruzat1 (GitHub) se volvió a comprobar en VS Code. El commit de esta etapa incorpora RTL, pruebas, evidencias y documentación; todas las operaciones remotas se realizan mediante esa sesión personal. Consultar el historial de main y su seguimiento origin/main para identificar el commit publicado. La conexión de oficina permanece excluida.


## Memorias A/B implementadas

El usuario autorizó continuar con A/B y pidió ver el trabajo en VS Code. Se abrió primero asic_top.v y después docs/Memorias_AB.md, que muestra resultados y decisiones. El usuario puede ver los cambios cuando se guardan archivos; no se simula escritura letra por letra.

Se implementaron rtl/asic/memory_a.v, memory_b.v y el selector asic_memory.v. asic_top ahora recibe MemoryVariant, 0=A y 1=B. A contiene ROM de 128 palabras y RAM de 16; B un único arreglo mem_ff de 144 palabras reescribible, con carga secuencial de 144 ciclos. La misma ROM generada alimenta A y el cargador de B. Las lecturas de B en operación normal salen siempre de su arreglo FF. Se mantienen latencias, byte enables, read-first, reset y MMIO. Direcciones inválidas no crean alias; puerto de datos A puede leer ROM pero no escribirla; B puede reescribir y ejecutar cualquiera de sus 144 palabras.

scripts/generate_asic_memory.py invoca el assembler original sin modificarlo. Genera ROM, game.hex y manifiesto en rtl/asic/generated. El juego conserva 94 palabras idénticas a los hex originales; todavía usa constantes de 25 MHz. Se corrigió una salida indefinida del primer generador combinacional en Icarus, sustituyendo always@* por función+assign; la regresión mantiene índices constantes 0/127. El generador pasó ocho pruebas.

scripts/check_asic_memories.py pasó cuatro simulaciones: interfaces de memorias de 5800 ciclos con cinco resets; top A/B dos épocas de 10000 ciclos alineadas con desfase de reset de 143 ciclos; y diagnóstico CPU RAM/MMIO/SPI para A y B. El intervalo de juego observado tuvo 2494 lecturas MMIO y cero accesos a RAM ordinaria, sin demostrar todavía su comportamiento completo. Las siete pruebas históricas de etapa 1 también pasan; su manifiesto es ahora un subconjunto explícito que sustituye las memorias reales por fixture.

scripts/check_asic_memory_synthesis.py pasó cuatro corridas: memory_a, memory_b, asic_top A y asic_top B. Yosys 0.62 de la imagen fijada; sin ABC ni mapeo PDK. Comprobación bit por bit del conductor FF.Q: 512 bits independientes A y 4608 en B, dentro y fuera del macro. FF genéricos totales: A 577/B 4681 aisladas; top A 1329/top B 5433. Sin latches, memorias sin mapear, SB ni cajas negras; solo la arquitectura elegida en cada top. Evidencia en evidence/asic_stage2 y evidence/asic_memory_synthesis. No interpretar estas cifras como área, Fmax o cierre físico.

config/rtl_asic.f es el manifiesto completo de producción. Los scripts verifican que incluya todas las fuentes y el generador esté actualizado. Las netlists genéricas voluminosas están en build/asic_memory_synthesis; sus hashes, logs y conteos se registran. No ejecutar el flujo físico con el fixture de sim/asic_stage1.

Checklist 15/17: pendientes juego completo/equivalencia y experimentos/signoff/informe. El original Proyecto 2 y baseline se conservan. Mantener memoria de las preguntas a la conversación anterior para cuando sean necesarias, sin preparar prompts por adelantado.

La prueba scripts/check_memory_netlist.py también pasó sobre las netlists genéricas de memory_a y memory_b: misma cobertura de 5800 ciclos y cinco resets que el ensayo RTL. Verifica huellas antes de ejecutar, y guarda resultados en evidence/asic_memory_netlist. No es equivalencia formal ni prueba post-síntesis del juego; ese requisito sigue pendiente.


## Actualización vigente: firmware y juego verificados

Se implementó `firmware/asic/game.s`: 10 MHz, espera 30000000, décima 1000000. La espera utiliza tiempo transcurrido módulo 2^32; se añadió una instrucción y el programa tiene 95, con 33 NOP de relleno. El assembler original y los módulos de CPU, periféricos y memorias no cambiaron; la ROM se regeneró. `generate_asic_memory.py` usa la fuente ASIC por defecto y permite pedir explícitamente la referencia FPGA; la regresión conserva esa comparación histórica.

`generate_game_firmware.py` produce tres perfiles trazables: production 30000000/1000000; simulation 3000/100, ambos umbrales acelerados 10000 veces; wait_only 3000/1000000, solo espera acelerada. Los perfiles de prueba no pueden escribirse bajo rtl. La generación ROM pasó nueve pruebas y los perfiles seis. `check_game_timing.py` verifica instrucciones codificadas y veinte casos de la ALU real, con dos fallos demostrados del algoritmo anterior y ninguno del corregido. No atribuir ese hallazgo al fallo físico histórico ni dar por resuelta la limitación de reacciones >=2^31 ciclos.

La regresión de producción pasó cuatro simulaciones de memorias/integración, cuatro síntesis genéricas y el ensayo de interfaces sobre netlists. `check_full_game.py` pasó RTL y comparación por ciclo con netlists genéricas completas en A/B: 65291/65577 ciclos, diez aciertos, dos errores, doce intentos, 4800 comprobaciones de botón mantenido, una saturación a 99, suma 162/promedio 16 y tres resets.

`check_game_wait_only.py` pasó A/B con solo la espera inicial acelerada: 10623/10766 ciclos, dos aciertos/un error/tres intentos, 600 comprobaciones de botón mantenido, 1118 solicitudes MMIO, once escrituras y cero accesos a RAM ordinaria. Compara terminales y también reset interno/transacciones MMIO de las netlists aplanadas. La ronda correcta desde escritura del LED al resultado toma 302 ciclos y el error 269, con coincidencia RTL/netlist. Es la prueba específica de sección 3.7; la partida completa con ambas escalas es cobertura adicional.

Las síntesis de producción jerárquicas cuentan 1329/5433 FF; las del juego aplanadas con firmware de prueba 1327/5433. Cambian opciones e imagen ROM: no atribuir la diferencia a una sola causa ni usar esos conteos como área física. El almacenamiento sigue en 512/4608 bits y la carga B en 144 ciclos.

La evidencia de esta etapa se conserva bajo evidence/asic_game: full_game, wait_only, timing, production_memories, production_synthesis, production_memory_netlist y firmware_profiles, con resumen results.json e índice README.md. Los resultados históricos de d867d61 siguen documentados en Memorias_AB.md; no sustituirlos por cifras nuevas. Los artefactos grandes están en build y se identifican mediante huellas.

El documento visible para seguir esta etapa en VS Code es docs/Juego_10MHz.md. Checklist 16/17: simulación genérica completa, cierre físico pendiente. Ningún PASS de esta etapa implica mapeo GF180, área, Fmax, STA o signoff. La próxima corrida física debe usar la ROM production y config/rtl_asic.f, nunca el fixture de etapa 1. Las operaciones remotas siguen limitadas a icruzat1 mediante VS Code; no usar el conector de oficina. Consultar git log y seguimiento origin/main para confirmar el commit publicado, sin asumir que preparar los archivos equivale a subirlos.
