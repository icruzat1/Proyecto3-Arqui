# Experimentos aislados

rtl_decode_pipeline_prototype.zip conserva un candidato que registra controles durante la espera existente del banco de registros. Pasó nueve simulaciones diferenciales (132457 ciclos), pero todavía no tiene síntesis ni medición física. No está incorporado al RTL de producción ni puede presentarse como una mejora de área o timing comprobada.

Las pruebas preservan la implementación actual; no certifican RV32E completo. La ALU original tiene desplazamientos desactivados y este candidato conserva ese comportamiento. Los scripts del prototipo registran rutas del entorno original; revisar esas rutas antes de reproducirlos fuera de este Mac.
