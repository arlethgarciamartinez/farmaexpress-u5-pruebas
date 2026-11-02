# Matriz de trazabilidad

| Necesidad (BRD) | Historias | Caso de uso | Componente(s) que la cumplen | ADR | Prueba |
|---|---|---|---|---|---|
| BN-01 Validar receta de controlados | US-02, US-03 | CU-02 | `Receta`, `Venta.confirmar_cobro` (I1), `VentaMostradorService.registrar_receta/confirmar_cobro` | ADR-001, ADR-005 | `test_cu02_controlado_sin_receta…`, `…receta_vencida…`, `…receta_incompleta…` |
| BN-02 Impedir caducados / lotes retirados | US-07 | CU-01, CU-04 | `Lote.verificar_vendible`, `SeleccionDeLote`, re-verificación en `confirmar_cobro` | ADR-002 | `test_cu04_producto_caducado…`, `…lote_retirado_despues_de_escanear…` |
| BN-03 Punto de reorden por rotación | US-11 | — (fuera del detalle) | `NivelesDeInventario` (el cálculo automático queda como trabajo posterior) | — | — |
| BN-04 Alertas de resurtido bajo mínimo | US-12, US-13 | CU-05 | `InventarioDeProducto.descontar` → `ExistenciaBajoMinimo` → `ResurtidoService` → `AlertaDeResurtido`, `OrdenDeCompra` | ADR-003 | `test_cu05_bajar_del_minimo…`, `…no_se_duplican_alertas…` |
| BN-05 Alertas 90/60/30 días | US-09 | (consulta) | `ConsultarCaducidadesProximasHandler` | ADR-004 | `test_query_caducidades_proximas…` |
| BN-06 Bloqueo inmediato en todas las sucursales | US-08 | CU-04 | `Lote` (Aggregate global), `RetiroDeLoteService`, evento `LoteRetirado` | ADR-002 | `test_cu04_retiro_bloquea_en_todas_las_sucursales…` |
| BN-07 Visibilidad entre sucursales | US-15 | (consulta) | `ConsultarDisponibilidadEnSucursalesHandler`, `LecturaDeInventario` | ADR-004 | `test_query_disponibilidad_en_otras_sucursales` |
| BN-08 Diferencias de inventario | US-17 | — (fuera del detalle) | Pendiente: `ConteoCiclico` | — | — |
| BN-09 Reportes | US-18 | (consulta) | Query Handlers (patrón Transaction Script en lectura) | ADR-001, ADR-004 | `test_query_*` (parcial) |
| BN-10 Restricción por rol | US-04, US-06, US-08 | CU-02, CU-03, CU-04 | `Autorizacion` (sólo Responsable), `RolSinPermiso` | ADR-005 | `test_cu02_exceder_limite…`, `test_cu04_solo_el_responsable…`, `test_cu03_sustituir_controlado…` |
| (Proceso) Venta sin restricciones | US-01 | CU-01 | `VentaMostradorService.agregar_producto/confirmar_cobro`, `Venta`, `InventarioDeProducto` | ADR-001, ADR-003 | `test_cu01_venta_sin_restricciones…` |
| (Proceso) Sustitución | US-05, US-06 | CU-03 | `Producto.sustitutos`, `Venta.agregar_sustituto` | ADR-005 | `test_cu03_*` |
| Restricción BRD: consistencia entre sucursales | — | CU-04 | Un solo `Lote` por (SKU, número) | ADR-002 | idem BN-06 |
| Integridad al cobrar | US-01 | CU-01 | `UnidadDeTrabajo` (Venta + Inventario) | ADR-003 | `test_si_falla_el_descuento_se_revierte_la_venta` |
| Regla de dependencias | — | — | `dominio` ← `aplicacion` ← `infraestructura` | ADR-001 | `tests/test_arquitectura.py` |

**Pendientes explícitos (fuera del diseño detallado de esta unidad):** US-10, US-11 (cálculo del punto de reorden), US-14 (recepción), US-16 (transferencias), US-17 (conteo cíclico), US-18 (reportes completos).
