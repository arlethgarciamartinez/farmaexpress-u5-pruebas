# Etapa 2 — Elección del patrón de lógica de negocio

## Tabla comparativa con criterios propios de FarmaExpress

| Criterio del caso | Transaction Script | Table Module | Active Record | Domain Model | Evidencia U2 |
|---|---|---|---|---|---|
| **Complejidad de reglas** | Un script por caso de uso con muchos `if` anidados (receta → vigencia → límite → sustituto → lote). Las mismas reglas se repiten en `confirmar cobro`, `sustituir` y `retiro`. | Reglas agrupadas por tabla (Ventas, Lotes). Las reglas que cruzan tablas (receta + límite + rol) no tienen dueño claro. | Cada clase = una fila (`Venta.save()`); las reglas de una sola fila caben, pero receta + límite + rol + lote cruzan varias filas y terminan en servicios. | Cada regla vive en el concepto que la protege (`Receta`, `Venta`, `Lote`, `Autorizacion`). | 10 necesidades (BN-01…BN-10) y 18 historias; 5 gateways exclusivos encadenados en el BPMN. |
| **Cambios esperados** | Cada cambio (otro umbral, otra política de lote) obliga a editar varios scripts. | Cambios localizados por tabla, pero no por regla. | Cambiar el esquema de la tabla cambia el objeto de negocio (acoplamiento a la BD). | Un cambio de regla se hace en un solo lugar (p. ej. `LimitesDeVentaControlada`, política FEFO). | Puntos "a validar con el stakeholder" en el BRD (umbral de diferencia de 2 %, meta de reducción de quiebres, marco legal exacto) y datos que sólo aparecen en una historia (vigencia de 30 días, límite 10 piezas / $3,000) → ver hallazgos H-03 y H-05. |
| **Interacción entre conceptos** | Los scripts coordinan Venta, Lote, Existencia y Receta a mano; el orden de validaciones queda disperso. | Cada módulo ve su tabla; la interacción Venta↔Lote↔Inventario se resuelve fuera de los módulos. | Los objetos se cargan y guardan solos; coordinar Venta + Inventario en una sola transacción queda fuera del modelo. | Los objetos colaboran con mensajes del lenguaje del negocio (`venta.confirmar_cobro`, `inventario.descontar`, `lote.retirar`). | BPMN: Cajero, Responsable, Compras/Almacén participan en la misma venta; glosario con 28 términos relacionados. |
| **Estados e invariantes** | Los estados (Cobrada, Retenida, Rechazada; Lote Disponible/Retirado/Caducado) se verifican manualmente en cada script; fácil olvidar una validación. | El estado es una columna; nada impide cobrar una venta ya rechazada. | Puede validar antes de `save()`, pero sólo dentro de su propia fila. | La invariante se **protege dentro del objeto**: una venta de controlado no puede cobrarse sin receta válida. | Restricción BRD: *"Ninguna venta de medicamento controlado puede completarse sin receta validada"*; criterio de éxito: 100 % con receta registrada. |
| **Criterio adicional: reportes y consultas** | **Muy adecuado** para reportes/consultas planas. | Adecuado para reportes tabulares. | Adecuado para CRUD y listados simples. | Costoso para reportes (cargar Aggregates para sumar). | US-18, US-09, US-15, BN-09 (sólo lectura, sin reglas). |
| **Criterio adicional: equipo y tiempo** | Rápido de empezar. | Rápido si el diseño es de datos. | Muy rápido con un ORM (Django, Rails). | Requiere más diseño inicial y disciplina. | Curso orientado a lógica de negocio; el equipo debe poder defender el diseño. |

## Ventajas, riesgos y consecuencias en FarmaExpress

| Alternativa | Ventajas | Riesgos | Consecuencia si se elige |
|---|---|---|---|
| Transaction Script | Simple, rápido, fácil de seguir para un solo flujo. | Reglas duplicadas entre CU-02, CU-03 y CU-04; la regla de receta podría omitirse en un nuevo script; difícil de probar por regla. | Se incumpliría el riesgo regulatorio principal con facilidad: basta un script nuevo sin la validación. |
| Table Module | Una clase por tabla, buena para datos y reportes. | La regla "controlado + límite + rol" no pertenece a una sola tabla; lógica queda en servicios. | Termina siendo Transaction Script con apariencia de módulos. |
| Active Record | Muy productivo con un ORM; cada objeto se guarda solo. | Mezcla persistencia y reglas en la misma clase; las pruebas necesitan base de datos; las reglas entre Aggregates no tienen dónde vivir. | Las invariantes que cruzan Venta, Lote e Inventario acabarían dispersas en servicios, igual que con Transaction Script. |
| **Domain Model** | Invariantes protegidas por objeto; reglas probadas sin base de datos; lenguaje ubicuo reflejado en el código. | Más clases y conceptos; hay que mapear a persistencia (Repository/Unit of Work); riesgo de sobre-diseño. | Aceptamos mayor complejidad inicial a cambio de seguridad regulatoria y cambios localizados. |

## Decisión

**Patrón principal: Domain Model** para el proceso de venta, inventario por lote, retiro de lote y resurtido.
**Uso acotado de Transaction Script:** únicamente en el lado de **consultas/reportes** (disponibilidad en otras sucursales, caducidades próximas, reportes de gerencia), implementados como Query Handlers que leen datos planos (ver CQRS). **Table Module** y **Active Record:** descartados (Active Record acopla el dominio a la base de datos y no protege reglas que cruzan varios objetos).

**Problema concreto que resuelve:** el sistema debe garantizar que un medicamento controlado no se venda sin receta válida, que un lote retirado se bloquee en todas las sucursales y que sólo el Responsable autorice excepciones. Esas garantías son *invariantes que cruzan varios conceptos y cambian con el tiempo*; en un script se pueden olvidar, en un objeto de dominio no se pueden saltar.

**Costo aceptado:** más clases e indirección (Repository, Unit of Work, eventos) y una curva de aprendizaje mayor; los reportes no se benefician del modelo y por eso se separan (ADR-004).

*Registro formal: [ADR-001](adr/ADR-001-domain-model-como-patron-principal.md).*
