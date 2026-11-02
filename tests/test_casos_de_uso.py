from datetime import timedelta

from conftest import CLON, CLON_GEN, HOY, IBU, PARA, SUC1, SUC2, n

from farmaexpress.aplicacion.comandos import (
    AceptarSustituto,
    AgregarProductoALaVenta,
    ConfirmarCobro,
    GenerarOrdenDeCompra,
    IniciarVenta,
    OtorgarAutorizacionDeVenta,
    RegistrarRecetaEnVenta,
    RegistrarRetiroDeLote,
)
from farmaexpress.aplicacion.consultas import (
    ConsultarCaducidadesProximas,
    ConsultarDisponibilidadEnSucursales,
)
from farmaexpress.dominio.orden_de_compra import EstadoDeAlerta
from farmaexpress.dominio.valores import Rol, TipoDeAutorizacion
from farmaexpress.dominio.venta import EstadoDeVenta


def nueva_venta(app):
    return app.venta.iniciar_venta(IniciarVenta(SUC1, "cajero.ana")).datos["venta_id"]


def receta(vid, dias_de_antiguedad=3, medico="Dr. Pérez"):
    return RegistrarRecetaEnVenta(vid, "Juan López", medico, "CED-123",
                                  HOY - timedelta(days=dias_de_antiguedad))


# ---------------- CU-01 (US-01) flujo normal ----------------
def test_cu01_venta_sin_restricciones_descuenta_lote_y_genera_ticket(app):
    vid = nueva_venta(app)
    assert app.venta.agregar_producto(AgregarProductoALaVenta(vid, PARA, 2)).exitoso
    r = app.venta.confirmar_cobro(ConfirmarCobro(vid))
    assert r.exitoso and r.datos["total"] == "100"
    assert r.datos["folio"].startswith("T-SUC-01")
    assert app.almacen.inventarios[(SUC1, PARA)].cantidad_en(n("P-1")) == 18
    assert app.almacen.ventas[vid].estado is EstadoDeVenta.COBRADA


# ---------------- CU-02 (US-02, US-03, US-04) ----------------
def test_cu02_controlado_sin_receta_se_rechaza_y_no_toca_inventario(app):
    vid = nueva_venta(app)
    app.venta.agregar_producto(AgregarProductoALaVenta(vid, CLON, 1))
    r = app.venta.confirmar_cobro(ConfirmarCobro(vid))
    assert not r.exitoso and r.codigo == "RECETA_REQUERIDA"
    assert app.almacen.ventas[vid].estado is EstadoDeVenta.RECHAZADA     # fin por excepción BPMN
    assert app.almacen.inventarios[(SUC1, CLON)].total() == 25


def test_cu02_receta_vencida_se_rechaza(app):
    vid = nueva_venta(app)
    app.venta.agregar_producto(AgregarProductoALaVenta(vid, CLON, 1))
    app.venta.registrar_receta(receta(vid, dias_de_antiguedad=31))
    r = app.venta.confirmar_cobro(ConfirmarCobro(vid))
    assert not r.exitoso and r.codigo == "RECETA_VENCIDA"
    assert app.almacen.inventarios[(SUC1, CLON)].total() == 25


def test_cu02_receta_incompleta_indica_que_falta(app):
    vid = nueva_venta(app)
    app.venta.agregar_producto(AgregarProductoALaVenta(vid, CLON, 1))
    app.venta.registrar_receta(receta(vid, medico=""))
    r = app.venta.confirmar_cobro(ConfirmarCobro(vid))
    assert r.codigo == "RECETA_INCOMPLETA" and "médico" in r.mensaje


def test_cu02_controlado_con_receta_valida_se_cobra_y_usa_fefo(app):
    vid = nueva_venta(app)
    r = app.venta.agregar_producto(AgregarProductoALaVenta(vid, CLON, 2))
    assert r.datos["requiere_receta"] and r.datos["numero_lote"] == "C-2"   # caduca primero
    app.venta.registrar_receta(receta(vid))
    assert app.venta.confirmar_cobro(ConfirmarCobro(vid)).exitoso


def test_cu02_exceder_limite_retiene_y_solo_el_responsable_autoriza(app):
    vid = nueva_venta(app)
    app.venta.agregar_producto(AgregarProductoALaVenta(vid, CLON, 11))      # > 10 piezas
    app.venta.registrar_receta(receta(vid))
    r = app.venta.confirmar_cobro(ConfirmarCobro(vid))
    assert r.codigo == "AUTORIZACION_REQUERIDA"
    assert app.almacen.ventas[vid].estado is EstadoDeVenta.PENDIENTE_DE_AUTORIZACION

    cajero = app.autorizacion.otorgar(OtorgarAutorizacionDeVenta(
        vid, TipoDeAutorizacion.VENTA_CONTROLADA_EXCEDE_LIMITE, "cajero.ana", Rol.CAJERO))
    assert not cajero.exitoso and cajero.codigo == "ROL_SIN_PERMISO"        # BN-10

    ok = app.autorizacion.otorgar(OtorgarAutorizacionDeVenta(
        vid, TipoDeAutorizacion.VENTA_CONTROLADA_EXCEDE_LIMITE, "dra.ruiz",
        Rol.RESPONSABLE_DE_FARMACIA))
    assert ok.exitoso
    assert app.venta.confirmar_cobro(ConfirmarCobro(vid)).exitoso


# ---------------- CU-03 (US-05, US-06) ----------------
def test_cu03_sin_existencia_sugiere_sustitutos_y_acepta_equivalente(app):
    vid = nueva_venta(app)
    r = app.venta.agregar_producto(AgregarProductoALaVenta(vid, IBU, 1))    # sin existencia en SUC-01
    assert not r.exitoso and r.codigo == "SIN_EXISTENCIA"
    assert r.datos["sustitutos_sugeridos"] == []
    # Llega mercancía de ibuprofeno y el cliente de paracetamol acepta el equivalente
    app.almacen.inventarios[(SUC1, IBU)].recibir(n("I-1"), 5)
    r2 = app.venta.aceptar_sustituto(AceptarSustituto(vid, PARA, IBU, 1))
    assert r2.exitoso
    assert app.almacen.ventas[vid].lineas[0].sustituye_a == PARA


def test_cu03_sustituir_controlado_exige_autorizacion_del_responsable(app):
    app.almacen.inventarios[(SUC1, CLON_GEN)].recibir(n("G-1"), 5)
    vid = nueva_venta(app)
    sin = app.venta.aceptar_sustituto(AceptarSustituto(vid, CLON, CLON_GEN, 1))
    assert not sin.exitoso and sin.codigo == "AUTORIZACION_REQUERIDA"
    con = app.venta.aceptar_sustituto(AceptarSustituto(
        vid, CLON, CLON_GEN, 1, "dra.ruiz", Rol.RESPONSABLE_DE_FARMACIA))
    assert con.exitoso


# ---------------- CU-04 (US-07, US-08) ----------------
def test_cu04_retiro_bloquea_en_todas_las_sucursales_y_notifica_a_almacen(app):
    r = app.retiro.registrar_retiro(RegistrarRetiroDeLote(
        PARA, "P-1", "Aviso del proveedor", "dra.ruiz", Rol.RESPONSABLE_DE_FARMACIA))
    assert r.exitoso
    assert app.almacen_fisico.notificaciones[0][1] == n("P-1")              # evento -> Almacén
    for sucursal in (SUC1, SUC2):                                           # un solo Lote global
        from farmaexpress.aplicacion.comandos import IniciarVenta as IV
        vid = app.venta.iniciar_venta(IV(sucursal, "c")).datos["venta_id"]
        rr = app.venta.agregar_producto(AgregarProductoALaVenta(vid, PARA, 1))
        assert not rr.exitoso and rr.codigo == "LOTE_RETIRADO"


def test_cu04_solo_el_responsable_registra_retiros(app):
    r = app.retiro.registrar_retiro(RegistrarRetiroDeLote(
        PARA, "P-1", "x", "cajero.ana", Rol.CAJERO))
    assert not r.exitoso and r.codigo == "ROL_SIN_PERMISO"


def test_cu04_lote_retirado_despues_de_escanear_impide_el_cobro(app):
    vid = nueva_venta(app)
    app.venta.agregar_producto(AgregarProductoALaVenta(vid, PARA, 1))
    app.retiro.registrar_retiro(RegistrarRetiroDeLote(
        PARA, "P-1", "x", "dra.ruiz", Rol.RESPONSABLE_DE_FARMACIA))
    r = app.venta.confirmar_cobro(ConfirmarCobro(vid))
    assert r.codigo == "LOTE_RETIRADO"
    assert app.almacen.inventarios[(SUC1, PARA)].total() == 20


def test_cu04_producto_caducado_se_bloquea_y_el_lote_queda_no_disponible(app):
    from farmaexpress.dominio.lote import EstadoDeLote
    app.almacen.lotes[(PARA, n("P-1"))].fecha_caducidad = HOY - timedelta(days=1)
    vid = nueva_venta(app)
    r = app.venta.agregar_producto(AgregarProductoALaVenta(vid, PARA, 1))
    assert r.codigo == "LOTE_CADUCADO"
    assert app.almacen.lotes[(PARA, n("P-1"))].estado is EstadoDeLote.CADUCADO


# ---------------- CU-05 (US-12, US-13) ----------------
def test_cu05_bajar_del_minimo_genera_alerta_y_compras_genera_orden(app):
    vid = nueva_venta(app)
    app.venta.agregar_producto(AgregarProductoALaVenta(vid, PARA, 11))      # 20 -> 9 (< mínimo 10)
    assert app.venta.confirmar_cobro(ConfirmarCobro(vid)).exitoso
    alertas = list(app.almacen.alertas.values())
    assert len(alertas) == 1 and alertas[0].cantidad_sugerida == 41         # máximo 50 - 9

    cajero = app.resurtido.generar_orden_de_compra(GenerarOrdenDeCompra("PROV-A", "x", Rol.CAJERO))
    assert not cajero.exitoso
    r = app.resurtido.generar_orden_de_compra(GenerarOrdenDeCompra("PROV-A", "ana.compras", Rol.COMPRAS))
    assert r.exitoso and r.datos["lineas"] == 1
    assert app.almacen.alertas[1].estado is EstadoDeAlerta.ATENDIDA


def test_cu05_no_se_duplican_alertas_si_ya_estaba_bajo_el_minimo(app):
    for _ in range(2):
        vid = nueva_venta(app)
        app.venta.agregar_producto(AgregarProductoALaVenta(vid, PARA, 11 if _ == 0 else 1))
        app.venta.confirmar_cobro(ConfirmarCobro(vid))
    assert len(app.almacen.alertas) == 1


# ---------------- Transacción ----------------
def test_si_falla_el_descuento_se_revierte_la_venta(app):
    vid = nueva_venta(app)
    app.venta.agregar_producto(AgregarProductoALaVenta(vid, PARA, 2))
    app.almacen.inventarios[(SUC1, PARA)].existencias[n("P-1")] = 1         # otro cajero vendió antes
    r = app.venta.confirmar_cobro(ConfirmarCobro(vid))
    assert r.codigo == "SIN_EXISTENCIA"
    assert app.almacen.ventas[vid].estado is EstadoDeVenta.EN_CAPTURA       # rollback: no quedó cobrada


# ---------------- Queries (CQRS) ----------------
def test_query_disponibilidad_en_otras_sucursales(app):
    dto = app.disponibilidad.manejar(ConsultarDisponibilidadEnSucursales(SUC1, PARA))
    assert [(d.sucursal_id, d.cantidad_disponible) for d in dto] == [(SUC2, 15)]


def test_query_caducidades_proximas_con_severidad(app):
    dto = app.caducidades.manejar(ConsultarCaducidadesProximas(SUC1))
    assert [(d.numero_lote, d.severidad_dias) for d in dto] == [("C-2", 30), ("C-1", 90)]
