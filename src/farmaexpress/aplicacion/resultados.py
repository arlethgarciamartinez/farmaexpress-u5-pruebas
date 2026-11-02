from __future__ import annotations

from dataclasses import dataclass, field

from ..dominio.excepciones import ErrorDeDominio


@dataclass(frozen=True)
class Resultado:
    """Respuesta de un caso de uso: éxito o rechazo explicado en términos del negocio."""

    exitoso: bool
    codigo: str
    mensaje: str
    datos: dict = field(default_factory=dict)

    @staticmethod
    def ok(codigo: str = "OK", mensaje: str = "", **datos) -> "Resultado":
        return Resultado(True, codigo, mensaje, datos)

    @staticmethod
    def rechazo(error: ErrorDeDominio, **datos) -> "Resultado":
        return Resultado(False, error.codigo, error.mensaje, datos)
