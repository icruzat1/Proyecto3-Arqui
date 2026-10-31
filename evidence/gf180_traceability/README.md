# Trazabilidad recuperada sin nuevas corridas físicas

Se leen exclusivamente los resultados de síntesis stage4_100ns_u40_floorplan_a/b y los DEF existentes final A / ECO3 B. El script no ejecuta Yosys, OpenROAD ni Docker y no modifica entradas. Las áreas son de síntesis, no las áreas tras reparación física.

## Resultados

- B: los 4608 FF de mem_ff y sus 4608 multiplexores privados de retención suman 445081,1904 µm², el 58,9471 % del área total sintetizada. Cada mux conduce únicamente D de su FF y recibe su propio Q como una entrada de datos. Son componentes de almacenamiento con habilitación de escritura, inequívocamente asociados a memory_b. Esta cota inferior ya supera la mitad del macro: memory_b domina cualquier bloque competidor disjunto. No se afirma que ese sea el área completa de memory_b; faltan lectura, decodificación y cargador/ROM.
- A: el mismo método da 55073,1776 µm², el 27,2435 %. Esa cota no prueba el módulo dominante.
- RF: se recuperan los 544 FF (480 bits almacenados más 64 salidas registradas) usando atributos de origen del JSON y la red Q común con la netlist renombrada. No se asume que los nombres automáticos del JSON coincidan con los nombres del Verilog físico. El área excluye lógica combinacional de lectura/escritura.
- Contador: 32 FF más 66 celdas combinacionales de su cono D exclusivo. Se rechazan entradas desde otros FF y consumidores ajenos al contador. Los 98 nombres físicos están disponibles.
- Los 544 nombres del RF y los 98 del contador aparecen en el DEF enrutado de ambas variantes y mantienen la familia funcional de su master, aunque pueda cambiar su fuerza. Se exportan sus orígenes físicos en micrómetros, orientación y master. Esto prepara una selección/captura GUI, pero no sustituye la captura anotada solicitada.

## Limitación ALU y siguiente decisión concreta

En los JSON mapeados no sobrevive ninguna red u_id.u_alu.* ni atributo de red procedente de espino_alu.v. Los reportes pre_techmap/post_dff/stat también contienen únicamente asic_top. No se guardó una red ABC intermedia con correspondencia suficiente para recuperar aquella frontera. La ausencia se informa; el resto del diseño no se etiqueta ALU.

LibreLane instalado admite SYNTH_HIERARCHY_MODE=deferred_flatten. Su implementación de synthesize.py:524 guarda una netlist *.hierarchy.nl.v antes de aplanar y resintetizar. Los reportes stat se vuelven a escribir, por lo que hay que preservar/extraer explícitamente estadísticas de esa netlist jerárquica, no asumir que stat.json final conserva jerarquía. Una síntesis auxiliar con keep permite medir módulos, pero sus áreas no se pueden presentar como la partición exacta de la corrida actual sin demostrar correspondencia.

Para futuras corridas comparables, conservar la jerarquía durante mapeo y los nombres ALU/RF/contador al aplanar permite preparar el mapa antes de PNR. Esto cambia la receta de síntesis y debe verificarse en la comparación correspondiente. Hacer únicamente una síntesis auxiliar no identifica automáticamente la ALU en el layout actual; para usar nombres de esa nueva síntesis en capturas hace falta su implementación física o una correspondencia demostrada. Conviene integrar esta decisión con el experimento RTL obligatorio, evitando otra campaña separada sin propósito.

## Reproducción

Desde la raíz del repositorio, después de copiar el helper a scripts:

    python3 -B scripts/trace_gf180_regions.py --root . --output evidence/gf180_traceability/results_reproduced.json

Los tags físicos se pueden indicar con --physical-a-tag y --physical-b-tag. El script falla si una región seleccionada falta en el DEF o cambia de familia funcional. La salida exige nombre nuevo. Conserva hashes de biblioteca, netlists, reportes y DEF, además del propio helper; verifica que las entradas no cambiaron durante lectura.
