# Etapa 3 — Mapa de dominio

Diagrama: `diagrams/01-mapa-de-dominio.dot` (fuente) → `01-mapa-de-dominio.png/.svg`.

## Lenguaje ubicuo (nombre del glosario → nombre en el código)

| Glosario U2 | Código | Nota |
|---|---|---|
| Lote / Fecha de caducidad | `Lote`, `NumeroDeLote`, `fecha_caducidad` | |
| Medicamento controlado / Receta médica | `Producto.es_controlado`, `Receta` | "Controlado" y "requiere receta" se tratan como sinónimos (H-01 de hallazgos) |
| Existencia / Punto de reorden / Máximo | `InventarioDeProducto`, `NivelesDeInventario(minimo, maximo)` | |
| Producto sustituto / Sustitución | `Producto.sustitutos`, `Venta.agregar_sustituto` | |
| Autorización | `Autorizacion` | Sólo Responsable de farmacia |
| Retiro de lote | `Lote.retirar`, evento `LoteRetirado` | |
| Resurtido / Orden de compra | `AlertaDeResurtido`, `OrdenDeCompra` | |
| Quiebre de stock | evento `ProductoAgotado` | |
| Sucursal, SKU | `sucursal_id`, `Sku` | Sucursal es sólo identificador en este alcance |

## Glosario actualizado (términos nuevos o corregidos)

| Término | Definición propuesta | Tipo de cambio |
|---|---|---|
| Venta | Operación de mostrador que agrupa líneas de producto, receta (si aplica), autorizaciones y termina cobrada o rechazada. | Nuevo |
| Línea de venta | Producto, lote y cantidad dentro de una venta. | Nuevo |
| Ticket | Comprobante interno de la venta cobrada (no es factura fiscal; la facturación está fuera de alcance). | Nuevo |
| Venta retenida | Venta de controlados que excede el límite (10 piezas o $3,000 MXN) y espera autorización del Responsable. | Nuevo (US-04) |
| Estado del lote | Disponible, Retirado o Caducado. | Nuevo |
| Alerta de resurtido | Aviso a Compras con producto, sucursal y cantidad sugerida cuando la existencia cae bajo el punto de reorden. | Nuevo (US-12) |
| Cantidad sugerida | Máximo de inventario menos la existencia actual. | Nuevo (deriva del glosario) |
| Proveedor | Origen del producto; una orden de compra pertenece a un solo proveedor. | Nuevo |
| Política de selección de lote | Criterio para elegir de qué lote se descuenta (supuesto FEFO). | Nuevo — **por validar** |
| Medicamento controlado | Se aclara que equivale a "producto que requiere receta" para este diseño. | Corregido |

## Fichas de Aggregates

### Venta (raíz: `Venta`)
- **Contiene:** `LineaDeVenta` (entidad), `Receta`, `Autorizacion`, `Ticket` (Value Objects).
- **Responsabilidades:** capturar productos y sustitutos, recibir la receta, recibir autorizaciones, cobrar o rechazar.
- **Invariantes:** **I1** controlado ⇒ receta completa y vigente para cobrar; **I2** exceder límite ⇒ autorización del Responsable; **I3** sustituir un controlado ⇒ autorización; **I4** venta cobrada o rechazada no se modifica.
- **Eventos:** `VentaCobrada`, `VentaRechazada`, `VentaRetenidaPorAutorizacion`, `SustitucionAceptada`.

### Lote (raíz: `Lote`) — *global, no por sucursal*
- **Responsabilidades:** saber si es vendible hoy, marcarse caducado, retirarse con autorización.
- **Invariantes:** lote Retirado/Caducado no es vendible; retirar exige `Autorizacion` de tipo `RETIRO_DE_LOTE` del Responsable; retirar es idempotente.
- **Eventos:** `LoteRetirado`, `LoteMarcadoComoCaducado`.

### InventarioDeProducto (raíz; identidad = sucursal + SKU)
- **Contiene:** existencia por lote y `NivelesDeInventario`.
- **Invariantes:** la existencia nunca es negativa; el evento de mínimo se emite sólo al **cruzar** el punto de reorden (evita alertas duplicadas).
- **Eventos:** `ExistenciaBajoMinimo`, `ProductoAgotado`.

### Producto (raíz; catálogo)
- SKU, nombre, precio, ¿controlado?, proveedor y sustitutos equivalentes. Casi sólo lectura.

### AlertaDeResurtido y OrdenDeCompra (raíces)
- **Alerta:** Pendiente → Atendida. **Orden:** Borrador → Confirmada; pertenece a un único proveedor y no se confirma vacía.
- **Eventos:** `AlertaDeResurtidoGenerada`, `OrdenDeCompraConfirmada`.

## Domain Service
- **`SeleccionDeLote`:** decide de qué lote se descuenta y detecta lotes caducados/retirados. Cruza `Lote` e `InventarioDeProducto`, por eso no pertenece a ninguno. La política de orden (`PoliticaDeOrdenDeLotes`) es intercambiable; la implementación inicial es FEFO (**supuesto por validar**).

## Value Objects
`Sku`, `NumeroDeLote`, `Dinero`, `Receta`, `Autorizacion`, `Ticket`, `LimitesDeVentaControlada`, `NivelesDeInventario`, `LineaDeOrden`.

## Domain Events y quién reacciona
| Evento | Lo emite | Reacciona |
|---|---|---|
| `ExistenciaBajoMinimo` | `InventarioDeProducto` | `ResurtidoService.generar_alerta_de_resurtido` |
| `LoteRetirado` | `Lote` | `RetiroDeLoteService.notificar_a_almacen` |
| `ProductoAgotado` | `InventarioDeProducto` | Sin consumidor por ahora (indicador de quiebres de stock, BRD) |
| `VentaCobrada`, `VentaRechazada`, `VentaRetenidaPorAutorizacion` | `Venta` | Sin consumidor por ahora (auditoría/reportes futuros) |
| `AlertaDeResurtidoGenerada`, `OrdenDeCompraConfirmada` | Alerta / Orden | Sin consumidor por ahora |

## Decisiones dudosas o descartadas
| Decisión | Resultado | Razón |
|---|---|---|
| ¿`Receta` es Entidad o Value Object? | **Value Object** | U2 no le da ciclo de vida propio ni la reutiliza entre ventas; la "receta retenida" es una copia asociada a la venta. Si se permite surtido parcial en varias ventas, pasaría a Entidad. *(por validar)* |
| ¿Existencia dentro del `Lote`? | Descartado | Retirar un lote tendría que modificar N registros por sucursal; BN-06 exige bloqueo inmediato en todas. |
| ¿`Sucursal` como Aggregate? | Descartado | Sin comportamiento en este alcance; sólo identificador. |
| ¿`Cliente`/`Paciente` como entidad? | Descartado | U2 no registra clientes; los datos del paciente viven en `Receta`. |
| ¿`Ticket` como Entidad? | Value Object | Sin ciclo de vida; la facturación fiscal está fuera de alcance. |
| ¿Un Aggregate por tabla de datos? | No | El mapa nace de reglas y lenguaje, no de tablas. |
| Transferencias (US-16) y conteo cíclico (US-17) | Fuera del detalle | Serían `TransferenciaEntreSucursales` y `ConteoCiclico`; trabajo posterior. |
