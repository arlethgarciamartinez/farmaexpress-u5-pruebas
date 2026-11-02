# Hallazgos sobre la Unidad 2 (regla de continuidad)

No se inventaron reglas para acomodar la arquitectura. Cada punto siguiente es una contradicción o un dato faltante detectado al cruzar BRD, historias, BPMN y glosario; se indica la decisión tomada **y que debe validarse**.

| ID | Hallazgo | Evidencia | Decisión en U3 | Estado |
|---|---|---|---|---|
| H-01 | "Medicamento controlado" y "requiere receta" se usan como si fueran lo mismo. | Glosario (controlado = requiere receta); BPMN gateway "¿Requiere receta?"; BRD "controlados". | Un solo atributo `Producto.es_controlado` que implica receta. | Por validar |
| H-02 | ¿Quién valida la receta? El BPMN lo asigna al Responsable de farmacia; BN-01/US-02/US-03 piden validación automática del sistema. | BPMN tarea "Responsable valida receta"; BN-01 "automáticamente". | El **dominio valida** (completitud y vigencia); el Responsable **autoriza excepciones**. Se propone actualizar la tarea del BPMN. | Cambio propuesto al BPMN |
| H-03 | El límite de 10 piezas o $3,000 MXN (US-04) no está en el BRD ni en el BPMN. | US-04 vs BRD/BPMN. | Se modela como `LimitesDeVentaControlada`. Agregar al BRD y un gateway "¿Excede límite?" al BPMN. | Cambio propuesto |
| H-04 | La autorización para sustituir controlados (US-06) no aparece en el BPMN (sólo "Cajero ofrece producto sustituto"). | US-06 vs BPMN. | `Venta.agregar_sustituto` exige `Autorizacion`. Actualizar BPMN. | Cambio propuesto |
| H-05 | La vigencia de 30 días de la receta sólo aparece en US-03; el BRD pide validar el marco legal. | US-03 vs BRD (Restricciones). | Constante `Receta.VIGENCIA_EN_DIAS = 30`, aislada en un solo lugar. | **Supuesto por validar** (asesor legal) |
| H-06 | No se define de qué lote se descuenta ("el lote correspondiente", US-01). | US-01. | Política intercambiable; se implementa FEFO (primero en caducar, primero en salir). | **Supuesto por validar** |
| H-07 | "Sucursales cercanas" (US-15) no se define. | US-15, BN-07. | Se consultan **todas las demás** sucursales. | Por validar |
| H-08 | "Sistema de inventario" figura como rol en US-07, US-09 y US-11, pero no es un stakeholder del BRD. | Historias vs tabla de stakeholders. | Se trata como comportamiento automático del dominio/proceso, no como actor. | Aclaración |
| H-09 | "Receta retenida" está en el glosario, pero ninguna historia dice cuándo se conserva. | Glosario vs historias. | `Venta` conserva la `Receta` (cumple "100 % con receta registrada"). | Por validar |
| H-10 | El glosario no incluye términos que el diseño necesita (Venta, Línea de venta, Ticket, Alerta de resurtido, Proveedor…). Además "FarmaExpres" aparece mal escrito en BRD, historias y glosario. | Glosario U2. | Glosario ampliado (ver `02-mapa-de-dominio.md`); corregir el nombre en los documentos. | Corregido en U3 |
| H-11 | US-17 define la diferencia como "más de 2 % del valor contado"; el BRD la deja como supuesto a validar. | US-17 vs BRD (Supuestos). | Sin impacto: conteo cíclico fuera del detalle de esta unidad. | Pendiente |
