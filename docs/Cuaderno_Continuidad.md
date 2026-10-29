# Cuaderno de continuidad del Proyecto 3

Estado al 29 de octubre de 2026, zona horaria America/Santiago. Objetivo: desarrollar el Proyecto 3 ASIC a partir del Proyecto 2 de Espino y del juego de reacción, conservando el original.

## Ubicaciones y procedencia

La carpeta de trabajo es /Users/ics/Desktop/Universidad/UAndes/Segundo Semestre - 2026/Arquitectura de Computadores/Proyecto 3. El original está en la carpeta hermana Proyecto 2. Su commit de referencia es 4d94b4e2f63c91d248e68350cdf640c3f7a86356.

La copia portable está en baseline/proyecto2. Se excluyeron el historial Git, el informe PDF y el log de síntesis antiguo. El único cambio de RTL es la ruta de game.hex en game_top.v; evidence/portabilidad.patch registra la diferencia. evidence/proyecto2_original_sha256.json contiene las huellas de 38 archivos originales.

La conversación de procedencia se llama Planificar proyecto ASIC, identificador 6ae35b1c-d08c-83e9-8b83-fdcd6ec80b13. Se recuperaron sus mensajes recientes. Falta incorporar Kit_Continuidad_Proyecto3_Etapa5.zip y el enunciado del Proyecto 3 para preservar íntegramente la auditoría, las especificaciones y los cuadernos anteriores.

## Restricciones y autorizaciones

Usar exclusivamente GitHub icruzat1 desde su sesión de VS Code. La interfaz de VS Code mostró icruzat1 (GitHub), y el remoto del original es https://github.com/icruzat1/Proyecto2-Arqui.git. No se ha llamado al conector GitHub de oficina.

El usuario autorizó Docker Desktop para Apple Silicon, LibreLane y GF180MCU, y crear icruzat1/Proyecto3-Arqui privado. Los términos de Docker se presentarán antes de aceptarlos. Para nuevas acciones externas o cambios importantes, preguntar o comprobar según el alcance autorizado.

No modificar el Proyecto 2 original ni la configuración global de Git. El repositorio nuevo tiene main, sin commit inicial todavía. Su identidad local de commits usa icruzat1 y su dirección GitHub noreply basada en el identificador público 321519839. Se desactivó en este repositorio la reutilización de ayudantes globales de credenciales; las operaciones remotas se harán mediante VS Code personal.

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

Completar Docker Desktop, confirmar su acuerdo, asignar inicialmente 4 CPU y 12 GB de RAM, verificar Linux ARM64, instalar LibreLane en un entorno aislado y fijar GF180MCU. Crear y comprobar el repositorio privado mediante VS Code. Recuperar kit y enunciado antes de implementar la adaptación ASIC.
