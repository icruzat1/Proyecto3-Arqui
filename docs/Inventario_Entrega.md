# Inventario de entrega del Proyecto 3

La entrega técnica conserva fuentes, configuraciones, pruebas, evidencias seleccionadas y checkpoints finales. Su publicación en el repositorio personal está pendiente de autorización del usuario.

## Documentos para revisión

| Documento | Contenido |
|---|---|
| [README](../README.md) | Entrada del repositorio, instalación, resultados y reproducción. |
| [Entrega técnica](Entrega_Tecnica.md) | Arquitectura, resultados, comparación 2×2 y alcance de las verificaciones. |
| [Requisitos](Requisitos_Proyecto3.md) | Correspondencia entre enunciado y evidencia, con pendientes académicos. |
| [Reproducción final](Reproduccion_Final.md) | Versiones, cadena de implementación y restauración de checkpoints. |
| [Verificación final](Verificacion_Final.md) | Pruebas funcionales, físicas y sus límites. |
| [Violaciones a 10 MHz](Violaciones_Finales_10MHz.md) | Conteos de A/B en los controles ejecutados. |
| [Comparación final](Comparacion_Final_AB.md) | Área, terminales, alimentación y costo didáctico. |
| [Síntesis final](Sintesis_Final_Trazable.md) | Celdas, módulos, contador y rutas críticas. |
| [Capturas](Capturas_Layout.md) | Figura 2×2 y vistas individuales de todos los bloques. |
| [Barridos](Barridos_GF180.md) | Períodos, utilizaciones, gráfico y resultados históricos. |
| [Ensayo RTL](Ensayo_RTL_Trazabilidad.md) | Propuesta implementada, medición y decisión de no adoptarla. |
| [Cierre eléctrico de B](Cierre_Electrico_B.md) | Diagnóstico, reparación y resultado final. |

Los documentos de adaptación RTL, memorias y firmware enlazados desde esta documentación se mantienen como respaldo técnico. Los cuadernos internos, la checklist de trabajo y los documentos personales se conservan comprimidos fuera de la entrega publicable. Los finales vigentes son los de la selección canónica, no los candidatos históricos.

## Código y evidencia

Se incluyen `rtl`, `firmware`, `scripts`, las configuraciones de `config`, la referencia portable `baseline/proyecto2` y las evidencias seleccionadas de `evidence`. La selección vigente es `config/gf180/final_selection.json`. Los paquetes finales están en `evidence/gf180_final_replay/final` y la figura aprobada en `evidence/layout_captures/entrega_2x2`.

La imagen 2×2 incluye su manifiesto de huellas y las exportaciones individuales. Las leyendas identifican bloques funcionales; los colores de la fila superior corresponden a capas físicas, no a bloques.

## Archivos locales fuera de la publicación

No se incluyen PDK, entorno Python local, corridas descomprimidas, historial comprimido en `build`, archivos temporales ni imagen Docker. La carpeta `.git` administra el historial y no se entrega como un archivo del proyecto.

Las guías personales DOCX de defensa y explicación permanecen fuera del repositorio. El informe académico PDF queda pendiente para una etapa posterior y no se presenta como un archivo terminado.

## Estado de publicación

Preparado para revisión local. Esperar autorización explícita antes del push. El destino permitido es exclusivamente el repositorio privado `icruzat1/Proyecto3-Arqui`, mediante la sesión personal de VS Code.
