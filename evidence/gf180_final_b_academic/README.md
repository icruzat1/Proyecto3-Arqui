# B cerrada con criterio académico aprobado

La continuación stage9_100ns_u40_academic_b termina con código0. A100ns/40%, setup/hold, DRC/LVS y antenas pasan. Persisten cuatro salidas de capacidad, seis pines de transición y doce conductores de fanout fuera del criterio estricto. No se declara cumplimiento eléctrico total.

El usuario autorizó aceptar esos avisos el30 de octubre. Solo cambió la selección de errores de los checkers de capacidad/transición; se conservaron límites Liberty, SDC y reportes. Netlist, DEF, GDS, LEF y SDC finales coinciden por SHA256 con los de la corrida medida. La continuación ejecutó los checkers finales, sin resintetizar ni rerutear. El detalle de fuentes y limitaciones está en results.json; justificación en docs/Decision_Cierre_B.md y docs/Cuaderno_Estudio_Defensa.md.
