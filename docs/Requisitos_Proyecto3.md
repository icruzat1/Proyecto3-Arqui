# Requisitos del Proyecto 3 — estado final técnico

Fuente: enunciado original docs/referencias/Etapa5/Proyecto_3_arquitectura.pdf, releído completo. Entrega GitHub y defensa: 4 de noviembre de 2026, 10:30. El informe PDF está aplazado por decisión del usuario; no se presenta como terminado.

**Finales vigentes:** A stage13_final_traceable_a; B stage12_electrical_route_b. 100 ns / 40 %. Ambas pasan los controles ejecutados y tienen identificación física de RF, ALU, contador y otros bloques.

| Sección | Requisito | Evidencia vigente / estado |
|---|---|---|
| 3.1 | Partir del Proyecto 2 real; interfaz macro sin dependencias FPGA; avisos/log/línea y reemplazos | PASS técnico. baseline/proyecto2, Adaptacion_RTL_Etapa1.md y Memorias_AB.md; documentación de los 13 avisos lint. No modificar el original. |
| 3.2 | A ROM combinacional + RAM; B FF unificada; dimensionamiento y comparación | PASS. 95 instrucciones en ROM128; RAM16 provisionada, juego sin uso ordinario de RAM; diagnóstico separado de RAM. A 512 / B 4608 bits de almacenamiento. Comparacion_Final_AB.md. |
| 3.3 | Cinco celdas, módulo dominante, fracción del contador y trazabilidad | PASS. Sintesis_Final_Trazable.md usa las síntesis stage7_trace_ref_a/b que alimentan los finales. CPU domina frente a memoria en A; memoria domina B. Contador 1,869947 % / 0,470190 %. ALU589 y RF1804 identificados en ambas. |
| 3.4 | Tres períodos, WNS/TNS TT/SS, ruta crítica, cambio RTL medido, recalibración | PASS. Barridos100/60/40ns, nueve esquinas; Barridos_GF180.md. Rutas críticas actuales en Sintesis_Final_Trazable.md. Ensayo_RTL_Trazabilidad.md mide el cambio registrado sin adoptarlo. Juego_10MHz.md calcula 30.000.000 / 1.000.000 ciclos. |
| 3.5 | Tres utilizaciones, área mínima exitosa, gráfico, terminales, PDN, costo | PASS. A30/40/50%; mínimo die exitoso probado 0,445850 mm² a50%. El final exigido permanece40%. Gráfico y procedencia en Barridos_GF180.md; terminales y PDN cotejados con DEF finales; costo A12.727,947 / B49.116,04 USD didácticos. |
| 3.6 | DRC/LVS, antenas, ejemplo de violación y capturas anotadas | PASS en controles ejecutados. Capturas_Layout.md enlaza finales; RF/ALU/contador y demás grupos verificados contra ODB y netlist. Ejemplo de antena y reparaciones eléctricas preservados. |
| 3.7 | Ronda correcta con ciclos iguales RTL/netlist; error reinicia ronda; mismos estímulos | PASS. Receta GF180 de A y B con firmware wait_only: dos aciertos y error/reintento; 302 ciclos correctos y269 del intento erróneo. Espera3000, décima1000000, mismos estímulos. A/B físicas:21.295 muestras acotadas, separadas de la prueba del juego y sin SDF. |
| 4–5 | README reproducible, código, PDF y defensa grupal | README y paquetes finales completos y restauración verificada. Informe PDF y preparación oral pendientes fuera del cierre técnico. Publicación personal después de limpiar; guías personales por chat, fuera de Git. |

## Criterios y límites

WNS no negativo y TNS cero para setup/hold en nueve esquinas; DRC de ruteo, Magic DRC, LVS y antenas sin errores; capacidad, transición y fanout también cero. KLayout DRC omitido por falta de runset, sin equivalencia formal EQY, SDF obligatorio ni signoff IR/EM. LVS usa la extracción documentada; esto es un macro académico, no certificación completa de fabricación.

La frecuencia máxima observada con cierre de todos los controles exigidos es10MHz dentro del conjunto ensayado. Los puntos40/60ns conservan sus fallos, y cada período puede producir otra optimización. No se extrapola Fmax usando solamente slack. La corrección final de A resuelve el reset de su referencia100ns40%; no convierte retrospectivamente los puntos fallidos en PASS.

El informe y todos los integrantes deben explicar RTL, assembler, decisiones y límites; los artefactos técnicos no sustituyen la defensa presencial.
