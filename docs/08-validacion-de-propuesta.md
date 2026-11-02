# Etapa 9 — Validación de la propuesta

La guía pide poder explicar, para cada caso de uso, **quién recibe la solicitud, dónde se valida cada regla, qué cambia, cómo se guarda y qué se devuelve**, y después revisar la propuesta completa contra seis criterios.

## Recorrido de cada caso de uso

| CU | ¿Quién recibe la solicitud? | ¿Dónde se valida cada regla? | ¿Qué objetos cambian? | ¿Cómo se persiste? | ¿Qué se devuelve? |
|---|---|---|---|---|---|
| **CU-01** Venta sin restricciones | `VentaMostradorService.agregar_producto` y `.confirmar_cobro` | `SeleccionDeLote` + `Lote.verificar_vendible` (lote vendible, existencia, FEFO); `Venta.confirmar_cobro` (venta con productos, estado) | `Venta` → Cobrada con `Ticket`; `InventarioDeProducto` (existencia del lote) | **Una** Unit of Work con `Venta` + `InventarioDeProducto`; `VentaCobrada` se publica después del commit (ADR-003) | `VENTA_COBRADA` con folio y total. Errores: `SIN_EXISTENCIA` (con sustitutos sugeridos), `LOTE_CADUCADO`, `LOTE_RETIRADO` |
| **CU-02** Venta de controlado | `VentaMostradorService.registrar_receta` / `.confirmar_cobro`; `AutorizacionDeVentaService.otorgar` | `Receta` (completa, vigencia 30 días); `Venta.confirmar_cobro` (I1 receta, I2 límite con `LimitesDeVentaControlada`); `Autorizacion` (sólo Responsable de farmacia) | `Venta` → Rechazada, PendienteDeAutorización o Cobrada; inventario **sólo** si se cobra | Rechazo y retención se guardan (commit) **sin tocar inventario**; el cobro sigue la misma UoW de CU-01 | `RECETA_REQUERIDA`, `RECETA_INCOMPLETA` (indica qué falta), `RECETA_VENCIDA`, `AUTORIZACION_REQUERIDA`, `ROL_SIN_PERMISO` o `VENTA_COBRADA` |
| **CU-03** Sustituto por falta de existencia | `VentaMostradorService.aceptar_sustituto` | `Venta.agregar_sustituto` (equivalencia vía `Producto.sustitutos`; controlado ⇒ `Autorizacion`); `SeleccionDeLote` para el lote del sustituto | `Venta` (nueva línea con el sustituto, evento `SustitucionAceptada`) | `Venta` en su UoW; el descuento ocurre al cobrar | Número de lote asignado. Errores: `SUSTITUTO_NO_EQUIVALENTE`, `AUTORIZACION_REQUERIDA`, `ROL_SIN_PERMISO` |
| **CU-04** Caducados y retiro de lote | `RetiroDeLoteService.registrar_retiro` (retiro) · `VentaMostradorService.agregar_producto` (caducado detectado al escanear) | `Lote.retirar` (autorización de tipo `RETIRO_DE_LOTE` del Responsable; idempotente); `Lote.verificar_vendible` / `marcar_caducado` | `Lote` → Retirado o Caducado (registro **global**, ADR-002) | Sólo `Lote` en la UoW; `LoteRetirado` se publica tras el commit y `notificar_a_almacen` reacciona | `LOTE_BLOQUEADO_EN_TODAS_LAS_SUCURSALES`. Errores: `ROL_SIN_PERMISO`, `NO_ENCONTRADO`, `LOTE_CADUCADO` |
| **CU-05** Resurtido y orden de compra | `ResurtidoService.generar_alerta_de_resurtido` (por evento `ExistenciaBajoMinimo`) · `ResurtidoService.generar_orden_de_compra` (Compras) | `InventarioDeProducto.descontar` (emite el evento sólo al **cruzar** el mínimo); `cantidad_a_resurtir` (máximo − existencia); `OrdenDeCompra` (un proveedor, no vacía) | `AlertaDeResurtido` (nueva → Atendida); `OrdenDeCompra` (Borrador → Confirmada) | Alerta en su **propia** UoW (si falla, la venta no se deshace); orden + alertas atendidas en una sola UoW | `alerta_id` y cantidad sugerida; `orden_id` y número de líneas. Errores: `ROL_SIN_PERMISO`, `SIN_ALERTAS_PENDIENTES` |

## Tabla de validación

| Criterio | Pregunta | Resultado del equipo |
|---|---|---|
| **Trazabilidad** | ¿Cada componente importante responde a una necesidad, regla o caso de uso? | **Sí.** Ver `05-trazabilidad.md` y la tabla de componentes de abajo. Los únicos componentes sin necesidad directa son de soporte (`Reloj`, `Dinero`, `BusDeEventosEnMemoria`) y existen para que las fechas, los importes y los eventos sean probables. |
| **Lenguaje** | ¿Los mismos términos significan lo mismo en BRD, UML, código y ADR? | **Sí, con dos aclaraciones registradas:** "controlado" = "requiere receta" (H-01) y "Sistema de inventario" no es actor sino comportamiento del dominio (H-08). Los nombres de clases del diagrama coinciden con el código (`Venta`, `Lote`, `InventarioDeProducto`, `Receta`, `Autorizacion`…). |
| **Responsabilidad** | ¿Las reglas permanecen en el dominio o en el patrón elegido, con justificación? | **Sí.** Receta, vigencia, límites, roles de autorización, caducidad y existencia viven en el dominio. **Excepciones justificadas:** las consultas usan Transaction Script (ADR-001, ADR-004) y la verificación de que sólo Compras genera órdenes quedó en `ResurtidoService` (deuda anotada en `03-service-layer…`). |
| **Consistencia** | ¿Los diagramas de clases y de secuencia representan la misma arquitectura? | **Sí.** Todos los participantes de las dos secuencias existen en el diagrama de clases. **Corregido en esta revisión:** la secuencia 1 nombraba `BusDeEventos`, pero la clase es `BusDeEventosEnMemoria`; se renombró y se regeneró la imagen. |
| **Persistencia** | ¿El dominio evita depender directamente de SQL, ORM o infraestructura? | **Sí.** El dominio define las interfaces `Repositorio…`; la aplicación define los puertos; sólo `composicion.py` conoce las implementaciones en memoria. Se verifica automáticamente en `tests/test_arquitectura.py`. |
| **Transacción** | ¿El límite de la operación y su manejo de error están definidos? | **Sí.** Una UoW por caso de uso (`with uow:` … `confirmar()`), rollback si no se confirma. Los errores se dividen en **de negocio** (`ErrorDeDominio` con código; el rechazo se guarda) y **técnicos/de existencia** (rollback completo; prueba `test_si_falla_el_descuento_se_revierte_la_venta`). **Observación:** una cantidad no positiva o una autorización de tipo incorrecto lanzan `ValueError` (error de programación, no de negocio) y provocan rollback. |

## Trazabilidad de componentes

| Componente | Responde a |
|---|---|
| `Venta`, `LineaDeVenta`, `Ticket` | US-01 · CU-01, CU-02, CU-03 · Restricción del BRD (100 % con receta registrada) |
| `Receta`, `LimitesDeVentaControlada` | BN-01 · US-02, US-03, US-04 · CU-02 |
| `Autorizacion`, `Rol` | BN-10 · US-04, US-06, US-08 |
| `Lote`, `SeleccionDeLote`, `PoliticaDeOrdenDeLotes` | BN-02, BN-06 · US-07, US-08 · CU-04 |
| `InventarioDeProducto`, `NivelesDeInventario` | BN-04 · US-01, US-12 · CU-01, CU-05 |
| `Producto` (sustitutos) | US-05, US-06 · CU-03 |
| `AlertaDeResurtido`, `OrdenDeCompra` | BN-04 · US-12, US-13 · CU-05 |
| Application Services | CU-01 a CU-05 (un método por caso de uso) |
| Repositorios y Unit of Work | Integridad venta-inventario (ADR-003) · restricción de consistencia entre sucursales |
| Query Handlers y DTO | BN-05, BN-07, BN-09 · US-09, US-15, US-18 |

## Conclusión de la validación

La propuesta se puede recorrer de punta a punta para los cinco casos de uso sin encontrar reglas en la capa equivocada. Las 21 pruebas automatizadas (casos de uso y reglas de dependencia) pasan. Quedan pendientes de validar con el profesor los supuestos de `06-hallazgos-u2.md`: FEFO, vigencia de 30 días, "sucursales cercanas" y `Receta` como Value Object.
