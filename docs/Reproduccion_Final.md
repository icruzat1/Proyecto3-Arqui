# Reproducción de los finales seleccionados

A: stage13_final_traceable_a. B: stage12_electrical_route_b. Consultar config/gf180/final_selection.json. Los perfiles academic/electrical anteriores son historial; para la entrega usar scripts/replay_delivery_checkpoint.py y evidence/gf180_final_replay/final.

## Instalación y comprobación

El README contiene instalación de imagen ARM64 y PDK fijados: LibreLane 3.0.17, Yosys 0.62, GF180MCU revisión 54435919abffb937387ec956209f9cf5fd2dfbee, gf180mcuD, biblioteca gf180mcu_fd_sc_mcu7t5v0. Corridas con cuatro núcleos y límite de 8 GiB por contenedor.

~~~sh
.venv/bin/python -B scripts/generate_asic_memory.py --check
.venv/bin/python -B scripts/replay_delivery_checkpoint.py --variant a --prepare-only
.venv/bin/python -B scripts/replay_delivery_checkpoint.py --variant b --prepare-only
~~~

SHA, CRC y restauración comprobados. Para repetir el tramo final, omitir --prepare-only y elegir --tag nuevo. Esa repetición no se ejecutó adicionalmente por rutina.

## Cadena real desde RTL

A parte de a_trace_ref.json, síntesis deferred_flatten stage7_trace_ref_a. La implementación stage7_trace_physical_ref_a conservaba los bloques, pero tenía removal de reset −0,022720 ns. prepare_reset_incremental_a.py añade una dlyb_1 a las dos RN del sincronizador, preserva instancias y posiciones originales y rerutea dos redes. stage13_reset_prepared_v2_a guarda la preparación; stage13_final_traceable_a ejecutó DetailedRouting hasta ReportManufacturability con a_final_traceable.json. El primer intento de preparación falló antes de editar el diseño por comparar objetos OpenDB en lugar de sus nombres; se conservó y corrigió esa comprobación.

B parte de b_trace_ref.json (stage7_trace_ref_b), implementada con b_sweep_t100_u40.json (stage8_t100_u40_b). Las reparaciones stage11/12 registradas en Cierre_Electrico_B.md corrigieron capacidad, transición y fanout. El final es stage12_electrical_route_b con b_electrical_eco.json.

Los scripts conservan verificaciones de conectividad, posiciones y hashes. Para reproducir el punto final sin repetir todo el desarrollo, usar los checkpoints que incluyen esas reparaciones. Ejecutar directamente desde RTL con a_trace_ref.json o b_trace_ref.json produce otra implementación: no se promete reproducir automáticamente sus ECO ni su PASS.

## Conservación y alcance

Los checkpoints guardan el estado ruteado para repetir extracción y controles. Resultados, pruebas, áreas y capturas están en evidence; RTL, firmware y configuraciones se conservan. La compresión del historial local se registra aparte y no forma parte del repositorio liviano.

KLayout DRC sin runset; sin equivalencia formal, SDF obligatorio ni signoff IR/EM. Restaurar archivos no se confunde con un nuevo signoff.

## Archivos de trabajo locales

PDK, entorno Python y corridas locales no forman parte de la entrega publicable. En un clon, preparar el entorno siguiendo el README y usar los checkpoints finales incluidos. El respaldo comprimido del equipo conserva las corridas y sus fuentes para una restauración local; esos archivos no se descargan desde Git. La auditoría de archivos originales requiere restaurar sus rutas de trabajo; la evidencia de su última ejecución aprobada está archivada.
