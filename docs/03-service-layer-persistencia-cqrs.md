# Etapas 4, 5 y 6 — Service Layer, Repository, Unit of Work y CQRS básico

## Application Services (Service Layer)

Los servicios **coordinan**: cargan Aggregates, invocan comportamiento del dominio, piden persistencia y definen la transacción. No contienen reglas del negocio.

| Servicio | Método (caso de uso) | Entrada | Colaboradores | Salida | Reglas que delega |
|---|---|---|---|---|---|
| `VentaMostradorService` | `iniciar_venta` | `IniciarVenta` | UoW, Reloj | `Resultado(venta_id)` | — |
| | `agregar_producto` (CU-01, CU-03) | `AgregarProductoALaVenta` | UoW, `SeleccionDeLote`, Reloj | `Resultado` (o rechazo con sustitutos sugeridos) | Lote vendible y existencia → `SeleccionDeLote`/`Lote`; línea → `Venta` |
| | `aceptar_sustituto` (CU-03) | `AceptarSustituto` | UoW, `SeleccionDeLote` | `Resultado` | Equivalencia y autorización de controlados → `Venta`/`Producto`/`Autorizacion` |
| | `registrar_receta` (CU-02) | `RegistrarRecetaEnVenta` | UoW | `Resultado` | Estructura de receta → `Receta` |
| | `confirmar_cobro` (CU-01, CU-02) | `ConfirmarCobro` | UoW, Reloj, `LimitesDeVentaControlada` | `Resultado(folio, total)` / rechazo / retenida | Receta, vigencia, límite, estados → `Venta`; descuento → `InventarioDeProducto`; lote → `Lote` |
| `AutorizacionDeVentaService` | `otorgar` (CU-02) | `OtorgarAutorizacionDeVenta` | UoW, Reloj | `Resultado(estado)` | Quién puede autorizar → `Autorizacion` |
| `RetiroDeLoteService` | `registrar_retiro` (CU-04) | `RegistrarRetiroDeLote` | UoW, Reloj | `Resultado` | Rol y estado → `Autorizacion`, `Lote.retirar` |
| | `notificar_a_almacen` | evento `LoteRetirado` | `NotificadorDeAlmacen` | — | — |
| `ResurtidoService` | `generar_alerta_de_resurtido` (CU-05) | evento `ExistenciaBajoMinimo` | UoW | `Resultado` | Cantidad sugerida → `InventarioDeProducto.cantidad_a_resurtir` |
| | `generar_orden_de_compra` (CU-05) | `GenerarOrdenDeCompra` | UoW | `Resultado` | Un proveedor por orden, no vacía → `OrdenDeCompra` |

### Revisión obligatoria
- **¿El nombre expresa una acción del negocio?** Sí: `confirmar_cobro`, `registrar_retiro`, `aceptar_sustituto`.
- **¿Coordina o decide?** Las únicas decisiones de los servicios son de *flujo* (qué hacer con el resultado: rechazar y conservar, retener, hacer rollback). Las reglas (receta, límites, roles, caducidad) están en el dominio. **Responsabilidad dudosa:** que `ResurtidoService.generar_orden_de_compra` verifique que el rol sea Compras es una regla de permisos; se dejó en el servicio porque aún no existe un Aggregate de "usuario/permiso" (anotado como deuda; hoy el rol de Responsable sí está en `Autorizacion`).
- **¿Depende de interfaces?** Sí: sólo de `UnidadDeTrabajo`, `Reloj`, `NotificadorDeAlmacen` y los repositorios del dominio (verificado por `tests/test_arquitectura.py`).
- **¿Hay inicio y fin transaccional comprensible?** Sí: `with self._uow() as uow:` … `uow.confirmar()`.
- **¿Los errores se explican en términos del negocio?** Sí: `RecetaVencida`, `LoteRetirado`, `AutorizacionRequerida`, `RolSinPermiso`, etc., con mensaje y código.

## Repositories (interfaces del dominio)

| Repository | Necesidad del dominio | Métodos propuestos | Objeto que recupera o guarda |
|---|---|---|---|
| `RepositorioDeVentas` | Retomar una venta en captura/retenida | `siguiente_id`, `agregar`, `obtener` | `Venta` |
| `RepositorioDeLotes` | Verificar vendibilidad y retirar | `obtener(sku, número)`, `de_producto(sku)`, `agregar` | `Lote` |
| `RepositorioDeInventario` | Descontar existencia por sucursal | `obtener(sucursal, sku)`, `agregar` | `InventarioDeProducto` |
| `RepositorioDeProductos` | Precio, controlado, sustitutos, proveedor | `obtener(sku)`, `agregar` | `Producto` |
| `RepositorioDeAlertas` | Agrupar alertas pendientes por proveedor | `siguiente_id`, `agregar`, `pendientes_de_proveedor` | `AlertaDeResurtido` |
| `RepositorioDeOrdenesDeCompra` | Persistir la orden | `siguiente_id`, `agregar`, `obtener` | `OrdenDeCompra` |

**Implementación en infraestructura (propuesta):** en producción, una clase `...Sql` por interfaz sobre una base relacional: un Aggregate se mapea a un grupo de tablas y se guarda completo (p. ej. `Venta` + `lineas_de_venta`); el control de concurrencia puede ser optimista con columna de versión. Aquí se entregan implementaciones **en memoria** para poder probar el diseño sin base de datos. Los métodos no exponen SQL; todos lanzan `EntidadNoEncontrada` si el Aggregate no existe (mismo contrato para cualquier implementación).

## Unit of Work

- **Dónde inicia:** al entrar al bloque `with` del Application Service (`BEGIN`).
- **Qué incluye:** en `confirmar_cobro`: `Venta` **y** `InventarioDeProducto` de cada línea (y `Lote` si se marca caducado). En `registrar_retiro`: sólo `Lote`. En `generar_orden_de_compra`: `OrdenDeCompra` y las `AlertaDeResurtido` que atiende.
- **Cuándo termina:** `uow.confirmar()` hace commit y **después** publica los Domain Events recolectados de los Aggregates tocados.
- **Qué pasa ante un error:** si el bloque termina con excepción o sin `confirmar()`, se hace **rollback** (en memoria: se restaura la instantánea). Ejemplo cubierto por prueba: si otro cajero agotó el lote entre el escaneo y el cobro, `descontar` falla y la venta **no** queda cobrada.
- **Rechazos de negocio** (receta vencida, lote retirado) *no* son errores técnicos: se conserva el rechazo (`Venta.rechazar`) con commit, sin tocar inventario.
- **Eventos:** los manejadores corren en su **propia** Unit of Work; si fallan, la venta ya cobrada no se deshace (el bus los registra en `errores`). *Riesgo aceptado:* en producción se requeriría un *outbox* o reintentos para no perder la alerta de resurtido.

## CQRS básico (sin bases separadas)

| Tipo | Nombre | Datos de entrada | Handler | Resultado | Justificación |
|---|---|---|---|---|---|
| Command | `ConfirmarCobro` | `venta_id` | `VentaMostradorService.confirmar_cobro` | `Resultado` (folio/total, rechazo o retenida) | Cambia Venta e Inventario; necesita Aggregates, invariantes y transacción. |
| Command | `RegistrarRetiroDeLote` | sku, lote, motivo, quién, rol | `RetiroDeLoteService.registrar_retiro` | `Resultado` | Cambia el estado del Lote y emite `LoteRetirado`. |
| Query | `ConsultarDisponibilidadEnSucursales` | sucursal actual, sku | `ConsultarDisponibilidadEnSucursalesHandler` | `DisponibilidadEnSucursalDTO[]` (sucursal, cantidad) | US-15: el cajero sólo necesita ver cantidades; no cargar Aggregates. |
| Query | `ConsultarCaducidadesProximas` | sucursal | `ConsultarCaducidadesProximasHandler` | `CaducidadProximaDTO[]` (sku, lote, días, severidad 90/60/30, cantidad) | US-09/US-18: modelo de lectura calculado para pantalla/reporte. |

- **Handlers y dependencias:** los *Command Handlers* son los métodos de los Application Services (dependen de UoW y dominio); los *Query Handlers* son clases aparte que dependen sólo del puerto `LecturaDeInventario` y devuelven DTOs. Los DTOs de lectura **no** reutilizan el modelo de escritura.
- **Qué no necesita la separación:** el resurtido (`ResurtidoService`) se dispara por evento y es de baja frecuencia; aplicar CQRS completo allí sería sobre-ingeniería. Tampoco se separaron bases de datos.

*Registro formal: [ADR-003](adr/ADR-003-unit-of-work-venta-e-inventario-eventos-tras-commit.md) y [ADR-004](adr/ADR-004-cqrs-basico-sin-bases-separadas.md).*
