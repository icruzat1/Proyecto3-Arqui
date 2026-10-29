# Checklist del Proyecto 3 en el Mac

Actualizada el 29 de octubre de 2026. Progreso comprobado: 16 de 17 pasos completos. Las instalaciones y la creación del repositorio privado ya están autorizadas.

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
- [x] Verificar juego completo y comparar RTL con netlist genérica por arquitectura; repetir con netlists GF180 en el cierre final.
- [ ] Completar barridos de reloj y floorplan, mejora RTL de ruta crítica, métricas, signoff, layout anotado, informe y defensa.

El enunciado y la rúbrica están revisados en [Requisitos_Proyecto3.md](Requisitos_Proyecto3.md). Mantener ambos cuadernos tras cada resultado relevante y no redactar prompts futuros.

El firmware de producción está recalibrado a 10 MHz, con 95 instrucciones y espera por tiempo transcurrido. Se comprobaron las constantes codificadas, 20 casos dirigidos de la ALU, nueve pruebas del generador ROM y seis de perfiles. La regresión con firmware de producción pasó cuatro simulaciones, cuatro síntesis genéricas y las interfaces de memoria sobre netlist.

El juego completo pasó en A/B: diez aciertos, dos errores/reintentos, botones mantenidos, saturación, promedio y reset. Las salidas coinciden ciclo a ciclo entre RTL y netlists genéricas del macro completo. Una prueba adicional conserva la décima de producción, acelera solo la espera inicial y comprueba también los ciclos MMIO de acierto/error/reintento. Ver [Juego_10MHz.md](Juego_10MHz.md) y [evidencia](../evidence/asic_game/results.json).

El primer mapeo GF180 y floorplan a 100 ns/40 % ya se ejecutaron, y pasó la prueba funcional con celdas GF180. Sigue colocación y reparación, CTS/ruteo, barridos de período/utilización, mejora RTL, cierre y documentación final. Ver [Mapeo y floorplan](Mapeo_Floorplan.md). Ya hay área inicial medida; Fmax y signoff de Espino siguen pendientes. El timing previo a colocación muestra violaciones. El flujo físico aprobado anteriormente corresponde al ejemplo oficial spm: Magic DRC, LVS y antenas limpios; KLayout DRC omitido por falta de configuración.

El repositorio privado personal fue creado y se publica exclusivamente mediante icruzat1 en VS Code. Proyecto 2 y la base FPGA se conservan. Los informes de la primera adaptación y de memorias mantienen sus resultados históricos; el estado vigente está en el informe del juego.
