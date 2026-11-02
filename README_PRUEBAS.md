# FarmaExpress · Pruebas de la Unidad 5

Equipo 10 · UANL / FIME · Componentes de Lógica de Negocios

Suite de pruebas automatizadas sobre el dominio de FarmaExpress (ventas en mostrador de farmacia): TDD, integración con SQLite y SQLAlchemy, mocks de un servicio externo, seguridad por rol y estado, cobertura mínima del 80% y CI en GitHub Actions.

## Cómo ejecutar

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -v
python -m pytest --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=80
python -m ruff check src tests
python scripts\generar_matriz.py
```

Resultado actual: **74 pruebas pasan**, Ruff sin errores y cobertura cercana al 98% (reporte HTML en `htmlcov/index.html`).

## Reglas de negocio probadas

| Regla | Qué valida | Casos |
|---|---|---|
| R1 Receta vigente | Un controlado solo se cobra con receta completa y de hasta 30 días. | CP-01 a CP-06 |
| R2 Límite de venta controlada | Más de 10 piezas o más de $3,000 deja la venta retenida hasta que autorice el Responsable de farmacia. Exactamente 10 piezas o $3,000 no se retiene. | CP-07 a CP-12 |
| R3 Lote vendible | Un lote caducado o retirado no se vende. Un lote que caduca hoy todavía se vende. El retiro es idempotente. | CP-13 a CP-19 |
| BN-10 Seguridad | Solo el Responsable de farmacia autoriza. Una venta cobrada o rechazada no se modifica. | CP-20 a CP-23 |
| Persistencia | Commit, rollback y lectura desde una sesión nueva (SQLite en memoria con SQLAlchemy). | CP-24 a CP-30 |
| Aviso a Almacén | Mock del servicio externo: aprobado, rechazado, timeout. | CP-31 a CP-35 |

La matriz completa está en `matriz_casos_pruebas.csv` (35 casos: 9 de éxito, 14 de error, 10 de límite y 2 mixtos). Se genera con `scripts/generar_matriz.py` a partir de los docstrings de las pruebas y marca el estado según el resultado real de pytest.

## Estrategia

- **Dominio sin base de datos.** Las reglas R1, R2, R3 y la seguridad se prueban directamente sobre los agregados (`Venta`, `Lote`, `Receta`, `Autorizacion`), en patrón Arrange-Act-Assert. Son rápidas y no dependen de infraestructura.
- **Integración con SQLite en memoria.** `infraestructura/sql.py` implementa el repositorio de lotes y la unidad de trabajo sobre SQLAlchemy. Se prueba el commit, el rollback y que los eventos de dominio se publican solo después del commit.
- **Mocks.** El servicio externo es el puerto `NotificadorDeAlmacen`, que se simula con `Mock(spec=...)`: respuesta correcta, `ConnectionError` y `TimeoutError`. Se eligió este puerto porque el BRD de FarmaExpress no tiene pasarela de pago.
- **Seguridad de negocio.** Se prueban los 4 roles que no pueden autorizar contra los 3 tipos de autorización (12 combinaciones) y el estado final de la venta.
- **TDD.** Las reglas se desarrollaron con Rojo → Verde → Refactor y se conservó la prueba como regresión.

## CI (GitHub Actions)

`.github/workflows/ci.yml` corre en cada push: instala dependencias, Ruff, pytest con `--cov-fail-under=80` y compilación.

Historial comprobado: #1 verde, #2 rojo (cambio intencional de la vigencia de receta de 30 a 20 días, que rompió las pruebas de R1) y #3 verde (revert).

## Trazabilidad

| Requisito del BRD | Regla | Componente | Pruebas |
|---|---|---|---|
| US-01 / US-03 receta y vigencia | R1 | `Receta`, `Venta.confirmar_cobro` | CP-01 a CP-06 |
| US-04 límite de venta controlada | R2 | `LimitesDeVentaControlada`, `Venta` | CP-07 a CP-12 |
| CU-04 retirar lote | R3 | `Lote`, `RetiroDeLoteService` | CP-13 a CP-19, CP-29 |
| US-06 sustitución de controlado | Seguridad | `Venta.agregar_sustituto` | CP-23 |
| BN-06 avisar a Almacén | Mock | `NotificadorDeAlmacen` | CP-31 a CP-35 |
| BN-10 roles | Seguridad | `Autorizacion`, `Rol` | CP-20 a CP-22, CP-30 |

## Hallazgos y supuestos a validar

1. **Receta con fecha futura.** `Receta.esta_vigente` usa `(hoy - fecha).days <= 30`, por lo que una receta con fecha futura se acepta como vigente. El BRD no lo define: se documenta como supuesto a validar con el equipo.
2. **Aviso a Almacén perdido.** Si el aviso falla, el retiro del lote ya quedó guardado (decisión coherente con la prueba CP-32), pero el aviso solo queda en `bus.errores`. El ADR-003 menciona outbox y reintentos como mitigación futura, y BN-06 exige que Almacén se entere.
3. **Alcance de la unidad de trabajo SQL.** Solo expone el repositorio de lotes. Ventas, inventario y órdenes de compra siguen en memoria.
4. **Paquete de datos del profesor.** `datos.zip` modela pedidos de clientes, mientras que el BRD de FarmaExpress modela ventas en mostrador. Los casos del paquete se tomaron como referencia y se derivaron las pruebas de las reglas reales del BRD.

## Estructura

```
src/farmaexpress/        dominio, aplicación e infraestructura (SQL y memoria)
tests/                   reglas, persistencia, mocks, seguridad y arquitectura
scripts/                 generar_matriz.py
matriz_casos_pruebas.csv matriz de casos (35)
.github/workflows/       ci.yml
```