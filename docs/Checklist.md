# Checklist del Proyecto 3 en el Mac

Actualizada el 29 de octubre de 2026. Progreso comprobado: 15 de 17 pasos completos. Las instalaciones y la creación del repositorio privado ya están autorizadas.

- [x] Comprobar hardware, macOS, herramientas y espacio disponible.
- [x] Crear Proyecto 3 e inicializar Git local sin modificar Proyecto 2.
- [x] Confirmar icruzat1 en VS Code y mantener excluida la conexión de oficina.
- [x] Crear y verificar icruzat1/Proyecto3-Arqui privado mediante VS Code.
- [x] Importar una copia FPGA portable y registrar procedencia y huellas.
- [x] Regenerar las 94 instrucciones y comparar los archivos hex.
- [x] Elaborar el diseño y comprobar su arranque en simulación.
- [x] Incorporar el kit Etapa 5 y el enunciado del Proyecto 3.
- [x] Instalar y configurar Docker Desktop para Apple Silicon.
- [x] Verificar el motor Docker y un contenedor Linux ARM64.
- [x] Preparar el entorno aislado y fijar la versión de LibreLane.
- [x] Descargar la revisión GF180MCU compatible y su biblioteca para la prueba de entorno.
- [x] Completar una prueba física mínima con GF180MCU.
- [x] Implementar y verificar interfaz ASIC, reset y RF portable: simulación RTL y síntesis genérica de bloques.
- [x] Implementar y verificar las memorias A y B, su carga real y almacenamiento FF en síntesis genérica.
- [ ] Verificar juego completo y comparar RTL con netlist por arquitectura.
- [ ] Completar barridos de reloj y floorplan, mejora RTL de ruta crítica, métricas, signoff, layout anotado, informe y defensa.

El enunciado y la rúbrica están revisados en Requisitos_Proyecto3.md. La recalibración temporal a 10 MHz está calculada y todavía debe implementarse y probarse. Mantener los dos cuadernos después de cada resultado relevante. No redactar prompts futuros.

Docker Desktop y hello-world funcionan en ARM64. El ejemplo oficial de LibreLane 3.0.17 con GF180MCU completó el flujo y generó GDS: Magic DRC, LVS y antenas sin errores; KLayout DRC omitido por falta de configuración. El repositorio privado fue creado y la rama main se subió desde VS Code. El kit y el enunciado están incorporados. La primera adaptación RTL pasó siete pruebas. La síntesis genérica de cuatro bloques también pasó después de resolver los permisos de Docker. Las memorias A/B y el macro completo en ambas variantes también pasaron síntesis genérica.

La primera adaptación queda como referencia histórica; la etapa A/B añade memorias reales y síntesis genérica del macro completo, todavía sin flujo físico GF180. Ver Adaptacion_RTL_Etapa1.md, evidence/asic_stage1/results.json y evidence/asic_stage1_synthesis/results.json.

El usuario volvió y concedió los permisos de Docker y Git. La cuenta personal icruzat1 de VS Code se verificó nuevamente para publicar el avance. El siguiente paso técnico es recalibrar el juego a 10 MHz y verificar rondas completas y equivalencia de juego RTL/netlist.

Memorias A/B: generador con ocho pruebas, cuatro simulaciones de interfaces/integración y cuatro corridas de síntesis. B carga 144 palabras en 144 ciclos; se verificaron 4608 bits FF reescribibles. Ver Memorias_AB.md.

También pasó el ensayo funcional post-síntesis de las interfaces de memoria. No marca como completada la prueba de juego RTL/netlist, que es más amplia y sigue pendiente.
