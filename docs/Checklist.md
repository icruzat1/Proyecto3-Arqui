# Checklist del Proyecto 3 en el Mac

Actualizada el 29 de octubre de 2026. Progreso comprobado: 12 de 17 pasos completos. Las instalaciones y la creación del repositorio privado ya están autorizadas.

- [x] Comprobar hardware, macOS, herramientas y espacio disponible.
- [x] Crear Proyecto 3 e inicializar Git local sin modificar Proyecto 2.
- [x] Confirmar icruzat1 en VS Code y mantener excluida la conexión de oficina.
- [x] Crear y verificar icruzat1/Proyecto3-Arqui privado mediante VS Code.
- [x] Importar una copia FPGA portable y registrar procedencia y huellas.
- [x] Regenerar las 94 instrucciones y comparar los archivos hex.
- [x] Elaborar el diseño y comprobar su arranque en simulación.
- [ ] Incorporar el kit Etapa 5 y el enunciado del Proyecto 3.
- [x] Instalar y configurar Docker Desktop para Apple Silicon.
- [x] Verificar el motor Docker y un contenedor Linux ARM64.
- [x] Preparar el entorno aislado y fijar la versión de LibreLane.
- [x] Descargar la revisión GF180MCU compatible y su biblioteca para la prueba de entorno.
- [x] Completar una prueba física mínima con GF180MCU.
- [ ] Implementar y verificar interfaz ASIC, reset y banco de registros portable.
- [ ] Implementar y verificar las memorias A y B y su arranque.
- [ ] Verificar juego completo y comparar RTL con netlist por arquitectura.
- [ ] Completar corridas físicas, métricas, informe y preparación de defensa.

Antes de implementar el ASIC: resolver la calibración temporal a 25 MHz frente al objetivo de 10 MHz y recuperar los requisitos exactos del enunciado. Mantener los dos cuadernos después de cada resultado relevante. No redactar prompts futuros.

Docker Desktop y hello-world funcionan en ARM64. El ejemplo oficial de LibreLane 3.0.17 con GF180MCU completó el flujo y generó GDS: Magic DRC, LVS y antenas sin errores; KLayout DRC omitido por falta de configuración. El repositorio privado fue creado y la rama main se subió desde VS Code. Faltan el kit y el enunciado para continuar la implementación ASIC y confirmar la biblioteca definitiva.
