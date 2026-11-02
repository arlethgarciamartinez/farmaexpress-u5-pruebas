# Etapa 1 — Preparar el caso

**Empresa:** FarmaExpress (cadena de farmacias). **Proceso principal elegido para el diseño detallado:** *venta en mostrador con validación de receta, existencia, lote y caducidad, y disparo del resurtido* (BPMN de la U2). Se mantiene el alcance aprobado en el BRD; transferencias entre sucursales (US-16), conteo cíclico (US-17), recepción en almacén (US-14) y reportes (US-18) quedan **fuera del diseño detallado** de esta unidad y se listan como trabajo posterior.

## Casos de uso seleccionados

| ID | Caso de uso | Actor | Reglas relacionadas | Resultado esperado | Origen en U2 |
|---|---|---|---|---|---|
| CU-01 | Registrar la venta de un producto sin restricciones *(flujo normal)* | Cajero | Existencia disponible; lote vendible; descuento del lote; ticket | Existencia del lote descontada y ticket generado | US-01 · BPMN: ruta "¿Requiere receta? No" |
| CU-02 | Vender un medicamento controlado *(excepciones: rechazo y retención)* | Cajero, Responsable de farmacia | Receta completa (paciente, médico, cédula, fecha); vigencia ≤ 30 días; límite 10 piezas / $3,000 MXN requiere autorización; sólo el Responsable autoriza | Venta cobrada, **rechazada** (receta inválida) o **retenida** hasta autorización | US-02, US-03, US-04 · BN-01, BN-10 · BPMN: "¿Receta válida?" |
| CU-03 | Ofrecer un producto sustituto por falta de existencia | Cajero, Responsable de farmacia | Sustituto equivalente; aceptación del cliente; sustituir un controlado exige autorización | Sustituto en el ticket y su existencia descontada | US-05, US-06 · BPMN: "¿Hay existencia?" / "¿Cliente acepta sustituto?" |
| CU-04 | Impedir la venta de caducados/retirados y registrar el retiro de un lote *(excepción)* | Responsable de farmacia | Lote caducado o retirado no se vende; retiro bloquea **todas** las sucursales; se notifica a Almacén | Lote bloqueado globalmente; Almacén notificado | US-07, US-08 · BN-02, BN-06 · BPMN: "¿Caducado o lote retirado?" |
| CU-05 | Generar alerta de resurtido y orden de compra | Sistema (evento), Compras | Existencia cae por debajo del punto de reorden; cantidad sugerida = máximo − existencia; una orden por proveedor | Alerta pendiente y, luego, orden de compra confirmada | US-12, US-13 · BN-04 · BPMN: evento intermedio "Existencia menor al mínimo" |

**Comprobación:** los cinco casos aparecen en las historias de usuario y en el BPMN; ninguno es corrección de alcance. Incluyen flujo normal (CU-01) y flujos con excepción o rechazo (CU-02, CU-04).
