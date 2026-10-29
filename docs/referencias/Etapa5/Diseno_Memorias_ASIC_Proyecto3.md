# Proyecto 3 — Diseño de las dos arquitecturas de memoria ASIC

**Estado:** diseño técnico propuesto (29 de octubre de 2026). **No implementado ni validado todavía mediante simulación Verilog, Yosys o LibreLane.**

> **Revisión de arquitectura posterior (Etapa 4, 29/10/2026):** La inicialización de B por reset simultáneo de las 144 palabras se conserva abajo como **propuesta histórica preliminar**. La elección actual es **carga secuencial sintetizable**, una palabra por ciclo mediante `boot_index`, con `core_rst_ni` retenido hasta `mem_boot_done`. Consulta `Adaptacion_FPGA_a_ASIC_Proyecto3.md`, sección 3.2, antes de implementar. Los dos mecanismos no deben mezclarse accidentalmente.

## 1. Requisitos del profesor y línea base

El enunciado del Proyecto 3, sección 3.2, exige **las dos alternativas** siguientes: (A) ROM combinacional **generada automáticamente por el assembler a partir de `game.s`**, más RAM de datos reducida; y (B) **memoria unificada implementada con flip-flops**, dimensionada según el juego. Se recomienda no superar 256 palabras de instrucciones y 64 de datos. Para ambas deben medirse área de celdas, número de flip-flops, utilización y frecuencia máxima de corridas propias. El proyecto exige preservar la funcionalidad, comparar post-síntesis y generar GDSII.

En el ZIP original del Proyecto 2:
- `assembler/game.s` produce **94 instrucciones de 32 bits** (376 bytes; posiciones 0–93), verificadas frente a ambos archivos `game.hex` entregados.
- `pochoco_soc-main/rtl/pochoco_soc.v:11-13,89-100`: el SoC instancia `pochoco_ram` con **512 palabras** y un único arreglo físico lógico para instrucciones/datos.
- `pochoco_soc-main/rtl/pochoco_ram.v:31-55`: lectura de instrucciones con registro de salida habilitado (`a_req_i`), lectura de datos registrada **cada flanco**, escritura por byte, y contenido cargado mediante `initial/$readmemh` (solo útil como mecanismo de inicio de simulación/FPGA, NO como garantía de arranque de un ASIC).
- `pochoco_soc.v:64-87`: `data_addr[31]` selecciona MMIO y excluye las operaciones de periféricos de la RAM. `game.s` accede a **cero palabras de RAM de datos ordinaria**, porque todo `lw`/`sw` va a MMIO 0x80000000–0x8000000C.
- `espino_if_stage.v:37-52`: la CPU espera que el dato de instrucción aparezca **tras el flanco de reloj**; por eso la ROM combinacional necesita un **registro de lectura** en su interfaz, a pesar de que la matriz ROM sea combinacional.

## 2. Parámetros de comparación propuestos (no impuestos por el profesor)

| Propiedad | Valor propuesto | Motivo |
|---|---:|---|
| Instrucciones utilizadas | 94 palabras | Valor comprobado del juego |
| Ventana de instrucciones | 128 x 32 bits | Potencia de dos, 94 cabe y conserva 34 posiciones de reserva |
| Ventana de datos | 16 x 32 bits | Pequeña RAM real, aunque el juego no la utiliza; permite validar LSU/byte enables |
| Ventana de direcciones instrucciones | `0x00000000` a `0x000001FF` | 128 palabras (4 bytes por palabra) |
| Ventana de direcciones datos | `0x00000200` a `0x0000023F` | 16 palabras, separada del programa |
| MMIO original | `0x80000000` y offsets | No cambiar direccionamiento de juego |
| Profundidad física lógica A | ROM 128 + RAM 16 | ROM se sintetiza como lógica, RAM como FF |
| Profundidad física lógica B | Array único de 144 x 32 bits | En él residen tanto programa como datos; **debe preservarse FF en síntesis** |

Los tamaños de reserva no son 'uso real': escribir en el informe **94 palabras de programa y 0 palabras de RAM ordinaria usadas por el juego**, y adicionalmente **capacidades provisionadas 128+16**. No afirmar que 16 es la demanda observada del programa. Si la comparación favorece otras capacidades, cambiarlas **en ambas variantes** y registrar razón.

**Presupuesto de bits de almacenamiento (cálculo teórico, NO recuento de celdas finales):**
- A: 16×32 = **512 bits de RAM de datos**; 128×32 son constantes lógicas, no FF de almacenamiento ROM. Se agregan registros de salida de lectura y otros FF del SoC.
- B: 144×32 = **4.608 bits potenciales de flip-flops** para el arreglo completo, más registros de salida y otros FF del SoC. Estos 4.608 bits solo constituirán FF medidos si no han sido eliminados, fusionados ni transformados por síntesis.
- Diferencia de bits de almacenamiento: **4.096**. No convertir esto directamente en área de silicio ni número exacto de celdas, porque el mapeo tecnológico agrega controles, muxes y buffers y puede optimizar bits.

## 3. Arquitectura A: ROM combinacional generada + RAM de datos reducida

Diagrama textual:

```
game.s --> assemble.py --> game.hex --> generate_asic_rom.py --> rom_game.v
                                           [case(address) = literal]
                                          + registro síncrono en lectura
espino instr_addr/req ----------------------------------> instr_rdata

espino data_addr/req/we/be --> decodificador RAM 0x200..0x23F --> 16x32 FF RAM
                                                       |--> data_rdata
MMIO 0x8000.... sigue en pochoco_soc / periph / spi sin pasar por RAM
```

**Implementación propuesta:** generador Python reproducible que invoque/importe `assemble.py`, compruebe 94 palabras y emita en Verilog un `case` combinacional con **constantes de 32 bits** por dirección. No se permite `initial`, `$readmemh`, lectura de archivo en tiempo de operación ni recursos FPGA. Puede emitir caso por índices 0..93 y un valor por defecto definido (`32'h00000013`, NOP estándar `addi x0,x0,0`, sujeto a revisión del decoder), evitando 34 casos redundantes; la cobertura de 128 posiciones se conserva. La dirección de instrucción se indexa por `instr_addr[8:2]` **solo si está en 0x000–0x1FF**, evitando alias por truncación de bits altos. Se exige alineación de 4 bytes.

La lectura instrucción debe preservar el protocolo de `pochoco_ram`:

```verilog
always @(posedge clk_i)
  if (a_req_i)
    a_rdata_o <= rom_word_comb;
```

El registro NO hace que el contenido de ROM sea una RAM de flip-flops: son únicamente los 32 bits del resultado de lectura. Para RAM de datos, implementar 16 palabras de 32 bits con FF, direccionamiento 0x200..0x23F, escritura por byte `b_be_i[3:0]`, y lectura que registra el **valor anterior** si lectura y escritura apuntan a la misma palabra en un flanco (como en el código original por asignaciones no bloqueantes). En el diseño actual `b_rdata_o` se actualiza cada flanco incluso si `b_req_i=0`; preservar inicialmente esta semántica para no introducir desfasajes inesperados, o documentar equivalencia si se optimiza. Permitir reset de RAM de datos a cero para reproducibilidad, documentando que es un cambio respecto del comportamiento indefinido original; no afectar el juego actual, que no la lee.

**Ventaja esperada (hipótesis, pendiente de medición):** menor número de FF y menor área que B. **Riesgo:** la gran función `case` puede crear muxes/rutas profundas y afectar timing; Yosys normalmente simplifica lógica de constantes, pero no debemos predecir el resultado final.

## 4. Arquitectura B: memoria verdaderamente unificada con flip-flops

```
                        +-----------------------------+
espino instruction ----> |                             |--> instr_rdata registrada
                        | mem_ff [0..143] de 32 bits  |
espino data port ------> |  mismo arreglo para ambos   |--> data_rdata registrada
                        |  escritura por byte          |
                        +-----------------------------+
                           ^
                           | reset determinista: palabras 0..93 = game.hex;
                           | resto = NOP (reserva instrucciones) o 0 (datos)
```

**Restricción fundamental:** la ROM lógica A NO debe ocultarse como un módulo permanente de lectura de instrucciones B. Ambas lecturas (instrucción/dato) deben salir del **mismo arreglo de palabras modificables** con FF. Para que exista un programa al arrancar, se propone cargar los literales de `game.hex` **durante un reset explícito, sintetizable**, generado automáticamente por el assembler. Es una propuesta de ingeniería cuya síntesis debe validarse; no es equivalente a ejecutar `$readmemh` en silicio.

Un generador puede crear una función `boot_word(index)` cuyos valores son constantes en RTL (casos 0..93, NOP para 94..127, cero para 128..143). Un proceso secuencial con reset escribe esos valores en todas las palabras; en operación normal mantiene la memoria y permite escritura a través del puerto de datos, **incluidos los índices del programa** si se desea preservar reprogramabilidad (en el juego actual no se usan). La escritura debe tener enable por byte y acceso seguro fuera de rango. Esta capacidad de escritura real sobre los índices 0..93 es importante para evitar que el sintetizador propague las constantes y convierta el supuesto 'FF unificado' en ROM de nuevo.

**Alerta de ingeniería:** resetear simultáneamente miles de FF puede generar un gran árbol de reset, área, fanout y congestión; también puede haber limitaciones de inferencia de arrays con reset en Yosys. Es obligatorio inspeccionar el netlist y la estadística de FF: **no basta que el Verilog diga `reg mem[]` para certificar B**. No se aceptará una memoria B con `$readmemh` o `initial` como única forma de arranque físico. Si el esquema de reset directo no es viable, considerar un cargador de arranque sintetizable por SPI para escribir las instrucciones, con un testbench que cargue el programa antes de liberar la CPU; su mayor complejidad se documentará y la solución se revalidará con el requisito de dos estrategias. La implementación de un bootloader por SPI es opcional en el enunciado y no sustituye las dos estrategias.

**Aspecto de comparación:** permitir escribir código en B pero no en A es una diferencia inherente a ROM vs RAM; las dos variantes deben ejecutar **el mismo juego** y presentar la misma semántica observable de instrucciones/datos en los accesos que realiza `game.s`. Las pruebas de auto-modificación de B no son prueba de equivalencia con A, sino prueba de que el almacenamiento es realmente reescribible.

## 5. Interfaz común exigida (preservar el contrato del SoC)

```verilog
input  wire        clk_i;
input  wire        rst_ni;       // añadido en el ASIC, bajo reset externo definido
input  wire        a_req_i;
input  wire [31:0] a_addr_i;
output reg  [31:0] a_rdata_o;
input  wire        b_req_i;
input  wire        b_we_i;
input  wire [3:0]  b_be_i;
input  wire [31:0] b_addr_i;
input  wire [31:0] b_wdata_i;
output reg  [31:0] b_rdata_o;
```

Las versiones A y B deben instalarse con el mismo `asic_top` y el mismo Espino/SoC mediante una selección **de elaboración** (`parameter`, `generate`, o configuración), nunca ambas simultáneamente en una corrida medida. Las instrucciones se leen después de un flanco válido si `a_req_i` estaba activo; si no, el registro de salida queda retenido. La lectura B del modelo original es síncrona e incondicional, pero las escrituras requieren `b_req_i && b_we_i`, con `b_be_i` por byte. En caso de lectura/escritura concurrente de una palabra, comprobar comportamiento 'read-first' original; si cambia, justificar y agregar pruebas.

**Protección de direcciones:** manejar explícitamente accesos fuera de rango y desalineados, sin alias silencioso. Documentar la diferencia frente a la RAM original que truncaba direcciones; comparar exclusivamente las direcciones válidas del juego. La elección de valor por defecto de instrucción (NOP) y lectura de datos (cero) es propuesta sujeta a pruebas funcionales. No cambiar la ruta MMIO original.

## 6. El register file NO es ninguna de estas dos memorias

`espino_register_file.v:11-71` usa dos bancos `SB_RAM40_4K` replicados para dos lecturas síncronas y una escritura en ambos; x0 nunca se escribe. Independientemente de A/B, para el ASIC debe convertirse en almacenamiento estándar **16 registros de 32 bits** con dos puertos de lectura y uno de escritura, conservando salida registrada en lectura. Se recomienda usar **un único conjunto físico de registros con dos lecturas síncronas**, no duplicar 2×512 bits salvo que los resultados funcionales indiquen una necesidad. x0 debe leerse como cero. Conservar el nombre `u_rf` y trazabilidad de `u_alu`, contador de ciclos y jerarquía para el informe. No modificar la FSM de espera del ID antes de validar latencia.

## 7. Flujo de construcción propuesto para Codex

1. Importar el estado final y ejecutar `assemble.py` sobre `game.s`; crear check automático de 94 palabras/archivo de referencia.
2. Crear `scripts/generate_asic_memory.py` que produzca `generated/rom_game.v` y datos Verilog de inicialización FF de B **directamente de la misma fuente**; archivos generados rastreables en Git.
3. Crear módulos RTL A y B separados, con la interfaz común y comentarios de semántica síncrona.
4. Crear o adaptar `asic_top.v`, reset externo e integración de SoC preservando MMIO.
5. Diseñar y ejecutar testbenches unitarios de memoria antes de poner el core: fetch 0, 1, 93, 94, 127; enable/hold; leer y escribir todas las byte lanes; read/write same address; reset; límites y alias. Para B verificar además modificación de instrucciones por puerto de datos, reset restaura programa.
6. Ejecutar prueba completa del juego en RTL **con estímulos en los mismos ciclos** para A y B (si la temporización cambia, justificar).
7. Sintetizar A/B con versiones, reloj, PDK, biblioteca y utilización iguales. Guardar células, FF, área, utilización, WNS/TNS, frecuencia, logs y hashes de fuentes. Confirmar de manera explícita FF real en B.
8. Calcular área de síntesis y física de cada variante. Seleccionar una para corrida final; justificar con resultados y requisitos del profesor.
9. Registrar observaciones en `docs/cuaderno_estudio.md` y `docs/cuaderno_continuidad.md` **por cada cambio y cada corrida**.

**Criterio de validación:** en el entorno de esta fase no se ha ejecutado `iverilog`, Yosys ni LibreLane. Las propuestas pueden requerir ajustes según la síntesis real. No inventar números de área, utilización, WNS/TNS, FF mapeados ni GDSII.

## 8. Riesgos y mitigaciones prioritarias

| Riesgo | Por qué importa | Verificación / mitigación |
|---|---|---|
| ROM combinacional cambia la latencia | La CPU y el controlador usan lectura síncrona | Registrar salida de ROM ante `a_req` |
| B sintetizada como ROM de constantes | No cumpliría 'unificada con flip-flops' | Permitir escritura real y verificar estadística de FF |
| Reset de 4.608 bits, fanout y área | Puede provocar problemas físicos | Probar síntesis temprana, medir, plan B bootloader si necesario |
| Byte enables mal implementados | Corrupción de bytes de datos | Test unitario por byte lane, varias palabras |
| Pérdida de MMIO | El juego deja de funcionar | Preservar bit 31 y multiplexado de lecturas |
| Direcciones 0..127 vs 128..143 | Alias o acceso fuera de rango | Comparar dirección completa, tests límites |
| Banco de registros sigue siendo FPGA-specific | ASIC no sintetiza | Reemplazar por FF, conservar latencia |
| Falta de reproducibilidad | Invalida resultados de comparación | Generador único, hashes, versiones y scripts |

## 9. Conclusión provisional

**Propuesta inicial:** implementar **A (ROM combinacional 128 + RAM FF 16)** para obtener pronto un ASIC cerrado y funcional; implementar **B (144 palabras FF realmente reescribibles)** para la comparación formal y física. Esta es una prioridad de desarrollo, **NO** una elección de ganador: la corrida final se elige con métricas reales de los dos diseños. La disponibilidad de un reset ASIC explícito y las pruebas funcionales son condiciones previas.

## 10. Referencias

- Fuente primaria: `Proyecto_3_arquitectura.pdf`, sección 3.2.
- Fuente primaria: ZIP `Proyecto2-Arqui-main.zip` y rutas indicadas arriba.
- Documentación LibreLane: https://librelane.readthedocs.io/en/latest/reference/configuration.html y https://librelane.readthedocs.io/en/latest/usage/about_pdks.html
- Documentación Yosys sobre síntesis de memorias: https://yosyshq.readthedocs.io/projects/yosys/en/v0.56/using_yosys/synthesis/memory.html
