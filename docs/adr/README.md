# Architecture Decision Records (ADR)

Cada ADR sigue el mismo formato: **Contexto → Alternativas → Decisión → Consecuencias → Trazabilidad**.

| ADR | Decisión | Estado |
|---|---|---|
| [ADR-001](ADR-001-domain-model-como-patron-principal.md) | Domain Model como patrón principal de lógica de negocio (Transaction Script sólo en consultas) | Aceptada |
| [ADR-002](ADR-002-lote-como-aggregate-global.md) | `Lote` como Aggregate global, separado de `InventarioDeProducto` | Aceptada |
| [ADR-003](ADR-003-unit-of-work-venta-e-inventario-eventos-tras-commit.md) | Unit of Work que abarca Venta e Inventario; eventos publicados tras el commit | Aceptada |
| [ADR-004](ADR-004-cqrs-basico-sin-bases-separadas.md) | CQRS básico: Commands y Queries separados, sin bases de datos separadas | Aceptada |
| [ADR-005](ADR-005-receta-como-value-object-y-reglas-en-el-dominio.md) | `Receta` como Value Object de `Venta`; reglas de receta y autorización en el dominio | Aceptada (con supuestos por validar) |

Para agregar una decisión nueva: copiar el formato, usar el siguiente número (`ADR-006-...`) y, si reemplaza a otra, marcar la anterior como *Reemplazada por ADR-00X*.
