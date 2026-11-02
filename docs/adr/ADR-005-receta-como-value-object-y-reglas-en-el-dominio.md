# ADR-005 — `Receta` como Value Object de `Venta`; reglas de receta y autorización en el dominio

- **Estado:** Aceptada (con supuestos por validar)
- **Fecha:** 02/10/2026

## Contexto
BN-01 y US-02/US-03 exigen receta completa (paciente, médico, cédula, fecha de emisión) y vigente (30 días); BN-10 y US-04/US-06 restringen por rol quién autoriza excepciones. El BPMN asigna la validación al Responsable, mientras que las historias la piden automática (hallazgo H-02).

## Alternativas
| Opción | Consecuencia |
|---|---|
| Receta como Entidad con repositorio propio | Útil si una receta se surte en varias ventas; U2 no lo indica. |
| Validar receta y límites en el Application Service | Las reglas quedarían fuera del dominio y se duplicarían. |
| **Receta como Value Object dentro de `Venta`; `Venta.confirmar_cobro` valida; `Autorizacion` valida el rol** | La invariante "no se cobra un controlado sin receta válida" no se puede evadir. |

## Decisión
`Receta` es un Value Object inmutable con `faltantes()` y `esta_vigente(hoy)`. `Venta.confirmar_cobro` aplica las invariantes I1–I3. `Autorizacion` (VO) sólo puede construirse con el rol Responsable de farmacia. El Service Layer únicamente reacciona al resultado: rechaza y conserva (`Venta.rechazar`), retiene o cobra. La vigencia de 30 días y los límites se aíslan en un solo lugar (`Receta.VIGENCIA_EN_DIAS`, `LimitesDeVentaControlada`) porque son supuestos por validar.

## Consecuencias
- (+) Una invariante regulatoria no depende de que cada servicio la recuerde; mensajes de rechazo en lenguaje del negocio.
- (+) Cambiar umbrales no toca los servicios.
- (−) Si U2 permite surtidos parciales con una misma receta, habrá que convertirla en Entidad y crear un Repository.
- (−) El BPMN y el BRD deben actualizarse (H-02, H-03, H-04).

## Trazabilidad
BN-01, BN-10 · US-02, US-03, US-04, US-06 · Restricción BRD "ninguna venta de controlado sin receta validada" · CU-02, CU-03.
