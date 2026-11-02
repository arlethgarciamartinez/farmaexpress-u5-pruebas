# ADR-003 — Unit of Work que abarca Venta e Inventario; eventos publicados tras el commit

- **Estado:** Aceptada
- **Fecha:** 02/10/2026

## Contexto
Al cobrar, la venta pasa a Cobrada y el inventario se descuenta (US-01). Si sólo uno de los dos cambios se guarda, se vende producto inexistente o se descuenta una venta no cobrada. Además, cuando la existencia cae del mínimo debe generarse una alerta de resurtido (US-12), pero ese resurtido no debe poder deshacer una venta ya cobrada.

## Alternativas
| Opción | Consecuencia |
|---|---|
| Una transacción por Aggregate + consistencia eventual para el descuento | Cumple la regla "un Aggregate por transacción", pero permite vender sin existencia real durante la ventana. |
| **Una transacción para `Venta` + `InventarioDeProducto`; efectos secundarios por eventos tras commit** | Evita vender sin stock; mantiene el resurtido desacoplado. |
| Todo (incluido el resurtido) en la misma transacción | El fallo de una alerta revertiría una venta válida. |

## Decisión
`confirmar_cobro` abre **una** Unit of Work que modifica `Venta` e `InventarioDeProducto` (y `Lote` si se marca caducado). `confirmar()` hace commit y **después** publica los Domain Events; sus manejadores (`ExistenciaBajoMinimo` → alerta, `LoteRetirado` → Almacén) corren en su propia Unit of Work. Los rechazos de negocio se guardan (commit) sin tocar el inventario; un error técnico o de existencia hace rollback.

## Consecuencias
- (+) Nunca queda una venta cobrada sin descuento; las alertas no afectan la venta; prueba `test_si_falla_el_descuento_se_revierte_la_venta`.
- (−) Se relaja la regla de un Aggregate por transacción; el alcance transaccional es mayor y puede generar contención por producto en horas pico.
- (−) Si el manejador de un evento falla, la alerta se pierde (el bus la registra en `errores`). **Mitigación futura:** patrón *outbox* o reintentos.
- Trabajo posterior: control de concurrencia optimista (versión) en `InventarioDeProducto`.

## Trazabilidad
US-01, US-12, US-13 · BN-04 · BPMN (evento intermedio "Existencia menor al mínimo") · CU-01, CU-05.
