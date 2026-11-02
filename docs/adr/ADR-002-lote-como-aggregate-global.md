# ADR-002 — `Lote` como Aggregate global, separado de `InventarioDeProducto`

- **Estado:** Aceptada
- **Fecha:** 02/10/2026

## Contexto
BN-06 y US-08 exigen bloquear de forma **inmediata y en todas las sucursales** un lote retirado; el BRD pide consistencia entre sucursales "en tiempo cercano al real". Al mismo tiempo, la existencia es por sucursal y por lote (BRD, glosario).

## Alternativas
| Opción | Consecuencia |
|---|---|
| Existencia y estado dentro de un Aggregate por sucursal | Retirar un lote implica modificar N Aggregates; ventana de inconsistencia entre sucursales. |
| Un único Aggregate "Producto" con todos los lotes de todas las sucursales | Contención enorme: cada venta bloquearía el producto para todas las sucursales. |
| **`Lote` global + `InventarioDeProducto` por (sucursal, SKU)** | Retiro = un solo cambio de estado; ventas de sucursales distintas no compiten. |

## Decisión
`Lote` (identidad SKU + número de lote) guarda su **estado** (Disponible, Retirado, Caducado) y es global. `InventarioDeProducto` guarda **cantidades** por lote en cada sucursal y referencia el lote sólo por `NumeroDeLote`. Un Domain Service (`SeleccionDeLote`) cruza ambos al vender.

## Consecuencias
- (+) El bloqueo es inmediato en todas las sucursales con una sola escritura; prueba `test_cu04_retiro_bloquea_en_todas_las_sucursales…`.
- (−) Vender exige leer dos Aggregates (Lote e Inventario) y re-verificar el lote antes de cobrar (BPMN).
- (−) Posible punto caliente de escritura si un lote muy vendido se actualiza con frecuencia (sólo cambia de estado, no de cantidad, así que es bajo).
- Trabajo posterior: validar con el stakeholder el tiempo máximo aceptable de bloqueo.

## Trazabilidad
BN-02, BN-06 · US-07, US-08 · Restricción BRD de consistencia entre sucursales · BPMN "¿Caducado o lote retirado?".
