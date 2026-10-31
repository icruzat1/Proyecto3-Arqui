# Estado vigente: finales trazables A/B

A stage13_final_traceable_a y B stage12_electrical_route_b pasan controles físicos/eléctricos ejecutados y21.295muestras por netlist física. A: evidence/gf180_final_a_traceable/functional; B: evidence/gf180_final_b_electrical/functional. Pruebas de juego de la receta GF180 en game_wait_only de A y en evidence/gf180_final_b_academic/game_wait_only para B, cuya receta de síntesis no cambió al reparar físicamente. A dos aciertos/error/reintento:302/269ciclos, espera3000y décima1000000; sin SDF. Restauración de los checkpoints finales comprobada. Auditoría de entrega: evidence/gf180_delivery/audit.json.

Las secciones siguientes son historial y conservan los alcances originales; no sustituyen la selección en config/gf180/final_selection.json.

# Verificación funcional de las implementaciones elegidas

## Versión vigente revisada el 30 de octubre

B final es `stage12_electrical_route_b`, no la B académica descrita en el historial inferior. Su netlist postruteo pasó 21.295 muestras, 20.913 ciclos activos, dos épocas, cuatro tramas SPI, dos controles de reset y 178 cambios de botón. Los archivos y huellas están en [functional](../evidence/gf180_final_b_electrical/functional/provenance.json). Se comprobó identidad con la exportación final. La prueba es acotada y sin SDF; la prueba de rondas post-síntesis con firmware wait_only conserva su alcance separado.

La revisión final A/B verificó los archivos originales, 18 logs STA por esquina y los paquetes restaurables sin repetir corridas. Resultado: [auditoría](../evidence/gf180_final_review/results.json). A conserva la reutilización funcional justificada por identidad exacta de netlist.

## Historial y pruebas complementarias


Se distinguen el circuito de producción y el firmware acelerado de prueba. Ninguna simulación aquí usa SDF ni constituye equivalencia formal.

## A final

La netlist final A coincide byte por byte con la ECO3A ya simulada:21295muestras, arranque/reset/botones/SPI. La reutilización está justificada por SHA256 en evidence/gf180_final_a/functional_reuse.json. La receta original de síntesis flatten pasó dos aciertos, un error y reintento en el ensayo GF180 wait_only de evidence/gf180_stage4/mapped_game. Esa prueba usa una ROM de simulación distinta, no la netlist física de producción con esperas completas.

## B final

La comprobación post-ruteo de producción se repitió sobre stage8_t100_u40_b:21295muestras,20913ciclos activos, dos épocas, cuatro tramasSPI, dos controles de reset y178cambios de botón. La huella de su netlist es idéntica a stage9_100ns_u40_academic_b. Evidencia: evidence/gf180_final_b_academic/functional.

Además se sintetizó de nuevo la receta B vigente, deferred_flatten, con una copia de firmware wait_only: espera3000ciclos y décima1000000ciclos. La configuración deriva de b_academic_final.json cambiando exclusivamente la fuente de ROM. No se implementó otro layout ni se modificó producción.

La comparación contra RTL pasó10765muestras durante10766ciclos: dos aciertos, un error individual, tres intentos y600controles de botón mantenido. Ambas rondas correctas tomaron302ciclos desde LED activo; el error269ciclos. Se comparan salidas reales con los mismos estímulos y firmware; no se afirma comparar MMIO interno eliminado por mapeo. Evidencia: evidence/gf180_final_b_academic/game_wait_only.

## Reproducción

Desde la raíz del proyecto, en una copia sin el tag de prueba ni sus carpetas de salida:

```sh
.venv/bin/python -B scripts/generate_game_firmware.py --profile wait_only --output-dir build/gf180_game/firmware
.venv/bin/python -B scripts/run_final_b_game.py
```

El lanzador fija la imagen del proyecto, no descarga ni usa red en el contenedor y reserva1CPU/3GiB para la síntesis. Rechaza sobrescribir el tag stage10_trace_wait_only_b y los resultados existentes. Configuración: config/gf180/b_final_wait_only.json. Conserva hashes antes/después y utiliza el comprobador scripts/check_gf180_mapped_game_trial.py, derivado del ensayo anterior con salidas aisladas y selección de variante.

La prueba de producción post-ruteo se reproduce con check_gf180_routed.py --tag stage8_t100_u40 --variant b --output CARPETA_NUEVA. Requiere conservar la corrida fuente. Los excesos eléctricos B no desaparecen por pasar estas pruebas funcionales.
