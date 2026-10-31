> **Estado vigente:** B corregida en stage12 a10MHz, cero violaciones en los controles eléctricos y físicos ejecutados. Ver [Cierre_Electrico_B.md](Cierre_Electrico_B.md). Las decisiones y cifras previas de este documento se conservan como historial.

# Decisión aprobada: cierre de B a 100 ns / 40 %

Corrida revisada: stage8_t100_u40_b. Entradas intactas, nueve esquinas verificadas, setup mínimo+23,444650ns y hold mínimo+0,277806ns. Pasan DRC de ruteo, Magic DRC, LVS, antenas, XOR, desconexiones y solapamientos. KLayout DRC sigue omitido por ausencia de runset.

La comprobación eléctrica estricta falla: cuatro salidas distintas superan max_capacitance en alguna esquina, seis pines de dos redes superan max_transition y doce conductores superan el objetivo de fanout10. El máximo fanout es14. En esos doce casos los diodos de antena explican el aumento por encima de10; se mantienen contados como cargas reales, no se eliminan del análisis. Los límites eléctricos siguen comprobándose con sus cargas.

Peor exceso relativo de cap: u_mem.genblk1.gen_b.u_memory._21337_/ZN, 0.131652 frente a 0.1163 (13.200 %), celda nor4_2.

Peor exceso relativo de slew: wire1254/I, 7.408215 frente a 7.0 (5.832 %), celda buf_2.

## Alternativa adoptada para la entrega académica

Aceptar B con avisos eléctricos visibles, conservando como obligatorios setup/hold, DRC/LVS y antenas. No subir los valores de Liberty ni cambiar el circuito para ocultar los reportes. Documentar los cuatro conductores, los seis pines y el fanout con diodos; conservar el resultado estricto FAIL junto al criterio académico elegido. El usuario aprobó esta sustitución de nuestro criterio interno de cero avisos eléctricos.

La guía oficial de cierre de timing, punto10, admite excesos de máxima capacidad/transición cuando no hay fallos de setup/hold y recomienda examinarlos. No afirma que los excesos desaparezcan ni garantiza validez para fabricación. El fanout adicional de diodos es un análisis específico de este proyecto; no se atribuye a una autorización textual de la guía. El enunciado exige WNS/TNS, DRC/LVS limpios y antenas corregidas o justificadas, pero no exige explícitamente cero avisos eléctricos.

https://librelane.readthedocs.io/en/stable/usage/timing_closure/index.html

## Alternativa: otra corrección física acotada

Conservar el criterio estricto y preparar una corrección dirigida de los conductores/redes restantes, con nueva colocación/ruteo/extracción/STA y controles físicos. No se garantiza cierre en un intento: insertar diodos puede introducir nuevas cargas y fanouts. Esta alternativa añade trabajo físico; no se ha iniciado.

## Evidencias

- evidence/gf180_sweeps/stage8_t100_u40_b/results.json: controles y STA frescos.
- evidence/gf180_sweeps/b100_limits.json: contraste por pin, celda y esquina con Liberty.
- evidence/gf180_sweeps/b100_fanout_diodes.json: identificación exacta de diodos por red.
- La variante dirigida histórica B se conserva: cuatro salidas de capacidad, 21pines de transición y cero antenas; los IDs/áreas/layout no deben mezclarse con esta nueva receta trazable.

Estado: APROBADO por el usuario el30 de octubre de2026 tras revisar alcance y riesgo académico. Se autoriza cierre con avisos documentados, sin declarar cumplimiento eléctrico total. Los barridos en curso mantienen sus entradas originales; la aceptación académica se registra por separado del resultado estricto.


Implementación completada: stage9_100ns_u40_academic_b, código0, vistas físicas/lógicas idénticas por hash. Evidencia: evidence/gf180_final_b_academic/results.json. Esta decisión histórica fue superada por la reparación documentada en Cierre_Electrico_B.md; el final vigente tiene cero violaciones en los controles ejecutados.
