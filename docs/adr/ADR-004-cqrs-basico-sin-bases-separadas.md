# ADR-004 — CQRS básico: Commands y Queries separados, sin bases de datos separadas

- **Estado:** Aceptada
- **Fecha:** 02/10/2026

## Contexto
Hay operaciones que cambian estado y protegen invariantes (cobrar, retirar lote) y necesidades de sólo lectura (disponibilidad en otras sucursales, caducidades próximas, reportes de Gerencia: US-15, US-09, US-18, BN-09). Cargar Aggregates para mostrar una lista sería costoso y mezclaría responsabilidades.

## Alternativas
| Opción | Consecuencia |
|---|---|
| Un solo modelo para leer y escribir | Simple, pero las consultas cargan Aggregates y los DTO acaban moldeando el dominio. |
| **CQRS básico (mismo almacén, modelos de lectura distintos)** | Consultas ligeras con DTO propios; el dominio sólo sirve a los Commands. |
| CQRS completo con bases separadas y proyecciones asíncronas | Excesivo para el alcance y la escala descritos en U2. |

## Decisión
- **Commands** (`ConfirmarCobro`, `RegistrarRetiroDeLote`, …) → métodos de los Application Services, con Unit of Work y Aggregates.
- **Queries** (`ConsultarDisponibilidadEnSucursales`, `ConsultarCaducidadesProximas`) → Query Handlers que dependen sólo del puerto `LecturaDeInventario` y devuelven DTO de lectura (`DisponibilidadEnSucursalDTO`, `CaducidadProximaDTO`).
- No se separan bases de datos. El resurtido por evento no se separa en CQRS.

## Consecuencias
- (+) Consultas simples y rápidas; el modelo de escritura no se contamina con necesidades de pantalla; responsabilidades claras.
- (−) Dos caminos de código (escritura y lectura) y DTO adicionales.
- (−) Las consultas pueden devolver datos con ligero desfase si en el futuro se separan almacenes.
- Trabajo posterior: reportes completos de Gerencia (US-18).

## Trazabilidad
BN-05, BN-07, BN-09 · US-09, US-15, US-18 · CU-01, CU-04.
