# Macros finales: comparación, terminales y alimentación

A usa stage13_final_traceable_a y B stage12_electrical_route_b. Ambas parten de la receta deferred_flatten y conservan identificación de todos los bloques funcionales. A añade un retardo local al reset; B conserva su reparación eléctrica. Los resultados físicos incluyen esas correcciones y no se atribuyen exclusivamente a la arquitectura de memoria. Las áreas de síntesis comparables están en Ensayo_RTL_Trazabilidad.md y las capturas y particiones verificadas en Capturas_Layout.md.

| Magnitud | A | B |
|---|---:|---:|
| Área stdcell post-PNR, µm² | 284044.000000 | 1166260.000000 |
| Área del die, mm² | 0.553389 | 2.135480 |
| Celdas secuenciales | 1329.000000 | 5433.000000 |
| Utilización física, % | 54.598000 | 56.349700 |
| Costo didáctico, USD | 12727.947000 | 49116.040000 |

Ambos usan 100 ns y utilización inicial 40 %. La utilización física final cambia al insertar buffers, reparar redes y construir el reloj. No confundirla con el objetivo de floorplan. Costo = área del die en mm² × 23.000 USD/mm²: no es una cotización e ignora máscaras, rendimiento, encapsulado, pruebas y costos fijos. Los barridos de las implementaciones anteriores están completos en Barridos_GF180.md; no se trasladan automáticamente sus resultados a estos finales corregidos. Esta corrección se valida a10MHz, sin declarar un máximo absoluto.

## Terminales verificados en los DEF finales

Cada macro tiene 28 terminales de señal y VDD/VSS. Son pines de macro; no se diseñó un anillo de pads de encapsulado. La agrupación facilita integración y lectura, sin afirmar que sea la única ubicación óptima.

**A**
- norte: clk_i, rst_ni.
- oeste: btn_i[0], btn_i[1], btn_i[2], btn_i[3], spi_cs_n_i, spi_mosi_i, spi_sclk_i.
- este: leds_o[0], leds_o[1], leds_o[2], leds_o[3], spi_miso_o.
- sur: seg1_o[0], seg1_o[1], seg1_o[2], seg1_o[3], seg1_o[4], seg1_o[5], seg1_o[6], seg2_o[0], seg2_o[1], seg2_o[2], seg2_o[3], seg2_o[4], seg2_o[5], seg2_o[6].

**B**
- norte: clk_i, rst_ni.
- oeste: btn_i[0], btn_i[1], btn_i[2], btn_i[3], spi_cs_n_i, spi_mosi_i, spi_sclk_i.
- este: leds_o[0], leds_o[1], leds_o[2], leds_o[3], spi_miso_o.
- sur: seg1_o[0], seg1_o[1], seg1_o[2], seg1_o[3], seg1_o[4], seg1_o[5], seg1_o[6], seg2_o[0], seg2_o[1], seg2_o[2], seg2_o[3], seg2_o[4], seg2_o[5], seg2_o[6].

## Alimentación y límites

Ambos usan rieles Metal1 de 0,6 µm y una malla Metal4 vertical / Metal5 horizontal de 1,6 µm de ancho. Los pasos de la malla son 153,6 µm vertical y 153,18 µm horizontal; separación configurada 1,7 µm. No se habilita anillo de núcleo. VDD/VSS aparecen como terminales especiales de alimentación en Metal4/Metal5. Se mantienen parámetros de la configuración GF180 utilizada para conectar filas y distribuir alimentación sin inventar una geometría ajena al PDK.

Los controles de conectividad y los DRC disponibles aprobados respaldan la implementación académica. No demuestran caída IR o electromigración aprobadas: no hay un contrato completo de fuentes de alimentación/corriente para declarar signoff de potencia. KLayout DRC está omitido por ausencia de runset. La nueva B presenta cero excesos de capacidad, transición y fanout en las nueve esquinas; el cierre académico anterior se conserva como historial.

Datos, coordenadas y huellas de DEF/config/STA: [evidence/gf180_final_comparison/results.json](../evidence/gf180_final_comparison/results.json).
