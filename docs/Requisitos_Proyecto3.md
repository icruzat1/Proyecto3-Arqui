# Requisitos y evidencias del Proyecto 3

Revisión del enunciado original completo, 29 de octubre de 2026. Fuente: [Proyecto 3](referencias/Etapa5/Proyecto_3_arquitectura.pdf). Esta matriz guía la implementación y la preparación de la defensa; los resultados del ejemplo spm solo verifican el entorno.

## Entrega y condiciones comunes

Entrega GitHub y defensa presencial: 4 de noviembre de 2026, 10:30. Se trabaja con el grupo y la entrega real del Proyecto 2. El producto es un macro digital de celdas estándar con terminales lógicos, usando LibreLane y GF180MCU.

La corrida final exige CLOCK_PERIOD de 100 ns y FP_CORE_UTIL de 40 por ciento. Cierre significa DRC y LVS limpios, antenas corregidas o justificadas con evidencia, WNS mayor o igual a cero y TNS igual a cero para setup y hold en los corners exigidos.

## Matriz de entrega

| Sección | Requisito y evidencia | Estado en Espino |
|---|---|---|
| 3.1 | asic_top con reloj, reset, LED, botones, displays y SPI. Identificar dependencias FPGA y registrar log y línea de cada warning/error; si no hubo aviso, explicar el problema físico. | Interfaz y memorias reales probadas; ambos macros pasan síntesis genérica. Primer mapeo/floorplan ejecutados; 13 avisos lint archivados. Mensajes finales de signoff pendientes. Ver Juego_10MHz.md; Memorias_AB.md conserva la etapa anterior. |
| 3.2 | A: ROM combinacional generada automáticamente por el assembler desde game.s y RAM reducida. B: memoria unificada en FF dimensionada por uso real. Comparar área de celdas, FF, utilización y Fmax. | A/B implementadas y probadas; 512/4608 bits de almacenamiento FF confirmados. Área mapeada y die inicial medidos; comparación final de utilización y Fmax pendiente. |
| 3.3 | Cinco celdas más usadas y explicación; módulo dominante; fracción de área del contador. Trazar RF, ALU y contador aun si se aplana la jerarquía. Comparar expectativas con síntesis. | Cinco celdas dominantes registradas; atribución por módulo/contador pendiente. |
| 3.4 | Al menos tres períodos incluyendo 100 ns; WNS/TNS de setup y hold en corner típico y más lento. Identificar extremos y función de ruta crítica. Implementar una mejora RTL y medir slack y área. Recalibrar game.s y regenerarlo. | Recalibración 10 MHz y corrección de espera probadas. Barridos físicos, ruta crítica y mejora RTL de esa ruta pendientes. |
| 3.5 | Al menos tres utilizaciones o tamaños de die; área mínima exitosa; gráfico utilización frente a violaciones o congestión; justificar terminales y alimentación. Estimar costo con el factor didáctico indicado. | Pendiente. |
| 3.6 | Reportes finales DRC, LVS y antena. Describir una violación observada, si la hubo, con ubicación y solución. Capturas de layout con RF, ALU y contador identificados. | Pendiente para Espino. |
| 3.7 | Netlist post-síntesis sin retardos: misma cantidad de ciclos que RTL en una ronda correcta; pulsación errónea reinicia la ronda. Mismo firmware y estímulos por ciclo. | PASS genérico en A/B: partida completa y prueba separada con solo la espera acelerada, ciclos de acierto/error y reintento coincidentes. Prueba acierto/error/reintento con GF180 mapeado también aprobada; repetir tras cambios finales. Ver Juego_10MHz.md. |
| 4 y 5 | Informe PDF, código y README reproducible; todos los integrantes deben poder defender RTL, assembler e informe. | Cuaderno integrado y guion de estudio disponibles; entrega final pendiente. |

## Memorias y programa

El enunciado recomienda como máximo 256 palabras de instrucciones y 64 de datos. Son recomendaciones de alcance; superar alguna requiere justificación previa a la comparación final. El bootloader SPI es opcional y no sustituye A y B.

El firmware ASIC actual tiene 95 instrucciones; la referencia FPGA conservada tiene 94. La corrección de la espera añade una instrucción. Se implementaron 128 palabras de programa y 16 de datos como capacidad provisionada, no impuesta por la pauta. El análisis estático identifica cero palabras de RAM ordinaria requeridas por el juego y las pruebas dinámicas comprueban sus transacciones MMIO; el ensayo wait_only registra cero accesos a RAM ordinaria. Un diagnóstico independiente escribe y lee la RAM para demostrar que funciona aunque el juego no la utilice.

## Tiempo del juego

Con T de 100 ns, la frecuencia es 10 MHz: tres segundos equivalen a 30000000 ciclos y una décima a 1000000. El programa original usa 75000000 y 2500000, coherentes con 25 MHz. La copia firmware/asic/game.s ya utiliza las constantes de 10 MHz y regenera automáticamente la ROM, conservando la base FPGA. Aumentar o reducir el período solicitado al flujo puede cambiar área, buffering y placement; Fmax se deriva del menor período probado que cierra en todos los corners exigidos.

Para acelerar la simulación se permite reducir la espera, siempre con el cambio documentado y la misma configuración en RTL y netlist. La prueba wait_only conserva 1 000 000 ciclos por décima y reduce únicamente la espera a 3000. La partida completa usa además un perfil de cobertura con ambos umbrales reducidos por 10 000; se informa por separado. Las netlists actuales son genéricas sin SDF, con pendientes de mapeo GF180 y cierre físico. La simulación post-PnR con SDF es opcional.

## Área y costo

El factor del ejercicio es 23000 USD por mm², bajo el supuesto de costo lineal. Se indicará qué área se utiliza y sus unidades: área en mm² = área en µm² dividida por 1000000. El cálculo es didáctico y debe discutir sus limitaciones; no representa una cotización de fabricación.

## Ponderación y preparación de la defensa

| Ítem | Puntaje |
|---|---:|
| Adaptación FPGA a ASIC | 0,5 |
| Memoria y assembler | 1,0 |
| Síntesis y trazabilidad | 0,4 |
| Timing y recalibración | 1,0 |
| Floorplan y costo | 0,5 |
| Signoff y layout | 0,5 |
| Simulación post-síntesis | 0,6 |
| Defensa presencial | 1,5 |
| Total | 6,0 |

El README final debe permitir instalar LibreLane, reproducir la corrida final, regenerar game.s y conocer versiones exactas de herramientas, revisión del PDK y biblioteca. La defensa no requiere explícitamente diapositivas en la pauta; el guion y las ayudas visuales pueden apoyar el estudio.


Primer punto físico 100 ns/40 % completado hasta terminales: [Mapeo y floorplan](Mapeo_Floorplan.md). No es cierre temporal ni signoff. Faltan los otros puntos del barrido y la mejora RTL medida.
