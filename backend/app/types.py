"""Tipos personalizados de SQLAlchemy compartidos por los modelos."""

from datetime import timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Fecha/hora almacenada como UTC y expuesta como ``datetime`` naive.

    Supabase/Postgres usa columnas ``timestamptz`` mientras el resto de la
    aplicación trabaja con ``datetime.utcnow()`` (naive). Este tipo normaliza
    ambos lados: al escribir envía UTC con zona horaria y al leer devuelve un
    datetime naive en UTC. En SQLite (solo pruebas) se guarda naive.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        if dialect.name == 'postgresql':
            return value
        # SQLite no maneja bien datetimes con zona horaria: guardar naive UTC.
        return value.replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
