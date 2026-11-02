"""Soporte común de los Aggregates: acumulan Domain Events hasta que la
Unit of Work los publica (después del commit)."""


class RaizDeAgregado:
    def __init__(self):
        self._eventos = []

    def registrar_evento(self, evento) -> None:
        self._eventos.append(evento)

    def extraer_eventos(self) -> list:
        eventos, self._eventos = self._eventos, []
        return eventos
