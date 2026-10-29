# Cuaderno de estudio y defensa del Proyecto 3

Continuación local del trabajo sobre Espino, el juego de reacción y su adaptación ASIC. Actualizado el 29 de octubre de 2026. Estas notas complementan los cuadernos acumulados de la conversación anterior, cuyo kit completo todavía debe incorporarse.

## Qué comprobamos en el Mac

El MacBook Air tiene chip M4, 10 núcleos y 24 GB de memoria. Dispone de Git e Icarus Verilog 13.0. Python 3.13.15 está instalado con Homebrew, aunque la terminal selecciona por defecto Python 3.9.6 de Apple. Usaremos explícitamente el Python adecuado para LibreLane.

El assembler propio transforma game.s en 94 instrucciones. El archivo regenerado coincide byte por byte con las dos copias de game.hex del Proyecto 2. Eso demuestra que podemos reproducir el programa sin depender del computador Windows donde se desarrolló.

La simulación de 2000 ciclos comprobó la carga de las instrucciones inicial y final, la liberación del reset FPGA, una dirección de instrucciones definida, el encendido inicial de los cuatro LED y el avance del contador. No cubre todavía las diez rondas, los botones ni un ASIC.

## Por qué había una ruta de Windows

El módulo superior referenciaba C:/Users/wille/Proyecto2/pochoco_soc-main/sw/game.hex. Esa dirección pertenece a otro computador. En la copia del Proyecto 3 se sustituyó por sw/game.hex y las pruebas se ejecutan desde pochoco_soc-main. El código original quedó intacto.

Icarus advierte que el archivo tiene 94 palabras para una memoria de 512. Las posiciones restantes no quedan definidas por ese archivo. La prueba de arranque utiliza las instrucciones cargadas; para el ASIC tendremos que definir explícitamente el contenido y el arranque de la memoria.

## Qué aporta Linux mediante Docker

macOS y Linux son sistemas distintos. Docker Desktop prepara una máquina Linux y permite ejecutar dentro de ella las herramientas del flujo. La versión Apple Silicon aprovecha la arquitectura ARM del M4. Un contenedor reúne herramientas y dependencias; no convierte automáticamente un diseño FPGA en ASIC.

Elegimos Docker Desktop por su interfaz gráfica y porque la guía de LibreLane para Mac lo utiliza. Colima también ofrece un motor Docker mediante una interfaz centrada en terminal. La elección facilita la operación; no es una medición comparativa de velocidad. Referencias: [Docker para Mac](https://docs.docker.com/desktop/setup/install/mac-install/), [Colima](https://github.com/abiosoft/colima) y [LibreLane para Mac](https://librelane.readthedocs.io/en/stable/installation/docker_installation/installation_macos.html).

## Qué debe cambiar para ASIC

El banco de registros usa memorias SB_RAM40_4K específicas de la FPGA iCE40. Su modelo de simulación permite comprobar el diseño FPGA; esas primitivas no son celdas de GF180MCU. La adaptación deberá conservar la latencia de lectura que espera Espino.

El reset actual depende de un contador inicializado al encender. El plan ASIC propone reset externo activo en bajo y liberación sincronizada. La memoria A separará ROM y RAM; la B usará memoria unificada de flip-flops con carga de arranque y CPU detenida mientras carga. Son diseños pendientes de implementación y verificación.

## Relación entre ciclos y segundos

El programa utiliza 75000000 ciclos para su espera inicial y 2500000 ciclos por décima. A 25 MHz corresponden a 3 segundos y 0,1 segundos. Con un reloj de 100 ns, equivalente a 10 MHz, esas mismas constantes representarían 7,5 segundos y 0,25 segundos. Debemos resolver con el enunciado si se recalibran las constantes o se conserva otro criterio de comparación. Estos tiempos se calcularon a partir del código; no son mediciones de una corrida ASIC.

El contador tiene 32 bits y el programa usa comparaciones con signo. El umbral 2^31 se alcanza aproximadamente a los 85,9 segundos a 25 MHz. Las pruebas completas deberán investigar el efecto de cruzarlo y el desbordamiento posterior.

## Preguntas para la defensa

- ¿Qué demuestra que el programa es reproducible? La igualdad byte por byte de los tres archivos hex tras ejecutar el assembler propio.
- ¿Qué demuestra la primera simulación? El arranque FPGA definido dentro del alcance indicado; todavía no el juego completo.
- ¿Por qué no basta con sintetizar el código FPGA? Contiene primitivas y supuestos de inicialización que deben sustituirse para GF180MCU.
- ¿Cómo se compararán las memorias A y B? Con el mismo programa, estímulos y referencia temporal definida, y resultados físicos separados por arquitectura.

## Versiones y comprobación física

LibreLane 3.0.17 y su revisión compatible de GF180MCU están descargados. Fijar versiones permite comparar corridas hechas con las mismas herramientas y bibliotecas. La instalación de LibreLane y la presencia de los archivos del PDK todavía no demuestran que el flujo físico funcione: necesitamos Docker activo y una corrida mínima GF180MCU completa.
