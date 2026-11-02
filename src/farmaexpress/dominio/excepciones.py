"""Errores del dominio expresados en lenguaje del negocio (glosario U2)."""


class ErrorDeDominio(Exception):
    codigo = "ERROR_DE_DOMINIO"

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class RecetaRequerida(ErrorDeDominio):
    codigo = "RECETA_REQUERIDA"


class RecetaIncompleta(ErrorDeDominio):
    codigo = "RECETA_INCOMPLETA"


class RecetaVencida(ErrorDeDominio):
    codigo = "RECETA_VENCIDA"


class LoteCaducado(ErrorDeDominio):
    codigo = "LOTE_CADUCADO"

    def __init__(self, mensaje: str, numero_lote=None):
        super().__init__(mensaje)
        self.numero_lote = numero_lote


class LoteRetirado(ErrorDeDominio):
    codigo = "LOTE_RETIRADO"

    def __init__(self, mensaje: str, numero_lote=None):
        super().__init__(mensaje)
        self.numero_lote = numero_lote


class ExistenciaInsuficiente(ErrorDeDominio):
    codigo = "SIN_EXISTENCIA"


class AutorizacionRequerida(ErrorDeDominio):
    codigo = "AUTORIZACION_REQUERIDA"


class RolSinPermiso(ErrorDeDominio):
    codigo = "ROL_SIN_PERMISO"


class VentaNoModificable(ErrorDeDominio):
    codigo = "VENTA_NO_MODIFICABLE"


class VentaSinProductos(ErrorDeDominio):
    codigo = "VENTA_SIN_PRODUCTOS"


class SustitutoNoEquivalente(ErrorDeDominio):
    codigo = "SUSTITUTO_NO_EQUIVALENTE"


class EntidadNoEncontrada(ErrorDeDominio):
    """Contrato común de todos los Repository cuando no existe el Aggregate
    (cualquier implementación, SQL o memoria, debe lanzar este mismo error: LSP)."""
    codigo = "NO_ENCONTRADO"
