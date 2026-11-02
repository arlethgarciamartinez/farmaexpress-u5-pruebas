# ADR-001 — Domain Model como patrón principal de lógica de negocio

- **Estado:** Aceptada
- **Fecha:** 02/10/2026

## Contexto
FarmaExpress vende medicamentos y debe cumplir regulación sanitaria. El BRD establece que *ninguna venta de medicamento controlado puede completarse sin receta validada* y que un lote retirado debe bloquearse en todas las sucursales. El BPMN encadena cinco gateways exclusivos y tres finales por excepción; las historias combinan rol, tipo de producto, monto y piezas (US-04, US-06). Los umbrales aún cambian (supuestos por validar).

## Alternativas
| Opción | Consecuencia |
|---|---|
| Transaction Script | Rápido, pero las reglas se duplican entre scripts y es fácil omitir una validación en un script nuevo. |
| Table Module | Agrupa por tabla; las reglas que cruzan Venta, Lote y rol no tienen dueño. |
| **Domain Model** | Más diseño inicial; las invariantes quedan protegidas dentro de los objetos. |

## Decisión
Usar **Domain Model** para venta, inventario por lote, retiro de lote y resurtido. Usar **Transaction Script sólo en consultas/reportes** (Query Handlers). Table Module queda descartado. La razón concreta: las invariantes regulatorias cruzan varios conceptos y cambian; deben ser imposibles de saltar.

## Consecuencias
- (+) Reglas probadas sin base de datos; cambios de regla localizados; lenguaje ubicuo en el código.
- (−) Más clases e indirección; requiere Repository y Unit of Work; curva de aprendizaje.
- (−) Los reportes no se benefician del modelo → se separan (ADR-004).
- Trabajo posterior: implementaciones SQL de los Repository.

## Trazabilidad
BN-01, BN-02, BN-06, BN-10 · US-01…US-08 · BPMN (gateways) · Restricciones del BRD · Pruebas `test_cu0*` y `tests/test_arquitectura.py`.
