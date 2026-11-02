"""Implementación SQL (SQLAlchemy 2.x) del Repository de lotes y de una Unit of Work.

Reemplaza a la versión en memoria sin tocar dominio ni aplicación (principio D de SOLID).
Alcance de la Unidad 5: solo el Aggregate Lote (caso de uso CU-04, retiro de lote).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from ..aplicacion.puertos import UnidadDeTrabajo
from ..dominio.excepciones import EntidadNoEncontrada
from ..dominio.lote import EstadoDeLote, Lote
from ..dominio.repositorios import RepositorioDeLotes
from ..dominio.valores import NumeroDeLote, Sku
from .memoria import BusDeEventosEnMemoria


class Base(DeclarativeBase):
    pass


class LoteRow(Base):
    __tablename__ = "lotes"

    sku: Mapped[str] = mapped_column(String, primary_key=True)
    numero: Mapped[str] = mapped_column(String, primary_key=True)
    fecha_caducidad: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String, nullable=False)


def crear_motor(url: str = "sqlite+pysqlite:///:memory:") -> Engine:
    """Crea el motor y las tablas. Por defecto usa SQLite EN MEMORIA (pruebas)."""
    motor = create_engine(url)
    Base.metadata.create_all(motor)
    return motor


class RepositorioDeLotesSql(RepositorioDeLotes):
    """Traduce entre filas SQL y el Aggregate Lote. El dominio no conoce SQLAlchemy."""

    def __init__(self, sesion: Session):
        self._sesion = sesion
        self._vistos: dict[tuple[str, str], Lote] = {}

    def _a_dominio(self, fila: LoteRow) -> Lote:
        clave = (fila.sku, fila.numero)
        if clave not in self._vistos:
            lote = Lote(Sku(fila.sku), NumeroDeLote(fila.numero), fila.fecha_caducidad)
            lote.estado = EstadoDeLote[fila.estado]
            self._vistos[clave] = lote
        return self._vistos[clave]

    def obtener(self, sku: Sku, numero: NumeroDeLote) -> Lote:
        fila = self._sesion.get(LoteRow, (sku.valor, numero.valor))
        if fila is None:  # mismo contrato que el repositorio en memoria (LSP)
            raise EntidadNoEncontrada(f"No existe el lote: {sku.valor}/{numero.valor}")
        return self._a_dominio(fila)

    def de_producto(self, sku: Sku) -> list[Lote]:
        filas = self._sesion.scalars(select(LoteRow).where(LoteRow.sku == sku.valor)).all()
        return [self._a_dominio(fila) for fila in filas]

    def agregar(self, lote: Lote) -> None:
        self._vistos[(lote.sku.valor, lote.numero.valor)] = lote
        self._sesion.add(LoteRow(
            sku=lote.sku.valor,
            numero=lote.numero.valor,
            fecha_caducidad=lote.fecha_caducidad,
            estado=lote.estado.name,
        ))

    def sincronizar(self) -> None:
        """Copia a las filas los cambios que el dominio hizo a los Aggregates cargados."""
        for (sku, numero), lote in self._vistos.items():
            fila = self._sesion.get(LoteRow, (sku, numero))
            if fila is not None:
                fila.estado = lote.estado.name
                fila.fecha_caducidad = lote.fecha_caducidad

    def agregados_vistos(self) -> list[Lote]:
        return list(self._vistos.values())


class UnidadDeTrabajoSql(UnidadDeTrabajo):
    """Una operación de negocio = una transacción SQL.

    BEGIN al entrar al bloque `with`; `confirmar()` hace COMMIT y solo después publica los
    Domain Events; si el bloque termina sin confirmar (o con excepción) se hace ROLLBACK.
    Solo expone `lotes`: los demás repositorios no tienen implementación SQL todavía.
    """

    def __init__(self, motor: Engine, bus: BusDeEventosEnMemoria):
        self._motor = motor
        self._bus = bus
        self._sesion: Session | None = None
        self._confirmada = False

    def __enter__(self) -> UnidadDeTrabajoSql:
        self._sesion = Session(self._motor)
        self._confirmada = False
        self.lotes = RepositorioDeLotesSql(self._sesion)
        return self

    def confirmar(self) -> None:
        self.lotes.sincronizar()
        eventos = []
        for lote in self.lotes.agregados_vistos():
            eventos.extend(lote.extraer_eventos())
        self._sesion.commit()                      # COMMIT
        self._confirmada = True
        for evento in eventos:                     # publicar DESPUÉS del commit
            self._bus.publicar(evento)

    def __exit__(self, *exc) -> None:
        if not self._confirmada:
            self._sesion.rollback()                # ROLLBACK
        self._sesion.close()
