# Cuaderno de continuidad del Proyecto 3

Estado al 29 de octubre de 2026, zona horaria America/Santiago. Objetivo: desarrollar el Proyecto 3 ASIC a partir del Proyecto 2 de Espino y del juego de reacción, conservando el original.

## Ubicaciones y procedencia

La carpeta de trabajo es /Users/ics/Desktop/Universidad/UAndes/Segundo Semestre - 2026/Arquitectura de Computadores/Proyecto 3. El original está en la carpeta hermana Proyecto 2. Su commit de referencia es 4d94b4e2f63c91d248e68350cdf640c3f7a86356.

La copia portable está en baseline/proyecto2. Se excluyeron el historial Git, el informe PDF y el log de síntesis antiguo. El único cambio de RTL es la ruta de game.hex en game_top.v; evidence/portabilidad.patch registra la diferencia. evidence/proyecto2_original_sha256.json contiene las huellas de 38 archivos originales.

La conversación de procedencia se llama Planificar proyecto ASIC, identificador 6ae35b1c-d08c-83e9-8b83-fdcd6ec80b13. Se recuperaron sus mensajes recientes. Falta incorporar Kit_Continuidad_Proyecto3_Etapa5.zip y el enunciado del Proyecto 3 para preservar íntegramente la auditoría, las especificaciones y los cuadernos anteriores.

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

## Decisiones técnicas que deben revalidarse con el enunciado

Plan recuperado: memorias A con ROM y RAM, B unificada con flip-flops y controlador de carga; reset externo activo en bajo, liberación sincronizada, botones sincronizados; conservar latencia síncrona del banco de registros. Una arquitectura por corrida física.

El plan previo señala 100 ns de período y 40 por ciento de utilización final. La documentación de LibreLane identifica gf180mcuD como variante por defecto de GF180MCU. Falta confirmar biblioteca, versión de LibreLane y revisión del PDK con el enunciado, y fijarlas para reproducibilidad. Referencia: [PDK en LibreLane](https://librelane.readthedocs.io/en/stable/usage/about_pdks.html).

Las constantes del juego están calibradas a 25 MHz. Antes de adaptar RTL o programa, resolver su relación con el objetivo de 10 MHz. También investigar comparaciones con signo alrededor de 2^31 ciclos.

## Siguiente trabajo

Incorporar Kit_Continuidad_Proyecto3_Etapa5.zip y el enunciado del Proyecto 3. Revalidar las especificaciones de memorias y reloj antes de implementar la adaptación ASIC. El entorno Linux ARM64 y la prueba física GF180MCU ya funcionan.

## Entorno instalado y versiones fijadas

LibreLane 3.0.17 y Ciel 2.6.1 están instalados en .venv con Python 3.13.15. La comprobación de dependencias pasó. config/requirements-macos-arm64.lock.txt registra todas las versiones y config/environment.lock.json fija las principales.

Ciel descargó y habilitó GF180MCU 54435919abffb937387ec956209f9cf5fd2dfbee, revisión que requiere LibreLane 3.0.17. Para la prueba de entorno se prepararon gf180mcuD y gf180mcu_fd_sc_mcu7t5v0. Se comprobó la presencia de configuración, bibliotecas de tiempo, LEF, GDS y LEF tecnológico. Este PDK conserva la carpeta libs.tech/openlane; LibreLane admite explícitamente esa ubicación alternativa. La biblioteca final se confirmará con el enunciado. La prueba física del ejemplo ya se completó; sus resultados se detallan al final de este cuaderno.

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
