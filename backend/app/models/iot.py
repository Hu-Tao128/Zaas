from datetime import datetime, timezone

from app.extensions import db


def _bigint_autoincrementable():
    """BIGINT en PostgreSQL y INTEGER en SQLite (necesario para autoincremento local)."""
    return db.BigInteger().with_variant(db.Integer, 'sqlite')


class DispositivoIoT(db.Model):
    __tablename__ = 'dispositivo_iot'

    id_dispositivo = db.Column(_bigint_autoincrementable(), primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    modelo_hardware = db.Column(db.String(50), nullable=False, default='ESP32-S3')
    api_key_hash = db.Column(db.String(256), unique=True, nullable=False, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    ultimo_ping = db.Column(db.DateTime(timezone=True), nullable=True)
    fecha_registro = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    telemetrias = db.relationship(
        'TelemetriaECBD',
        back_populates='dispositivo',
        lazy=True,
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<DispositivoIoT {self.nombre}>'


class TelemetriaECBD(db.Model):
    __tablename__ = 'telemetria_ecbd'

    id_registro = db.Column(_bigint_autoincrementable(), primary_key=True)
    id_dispositivo = db.Column(
        _bigint_autoincrementable(),
        db.ForeignKey('dispositivo_iot.id_dispositivo'),
        nullable=False,
        index=True,
    )
    tipo_evento = db.Column(db.String(50), nullable=False)
    modulo_evaluado = db.Column(db.String(50), nullable=True, index=True)
    latencia_ms = db.Column(db.Float, nullable=True)
    memoria_libre_kb = db.Column(db.Integer, nullable=True)
    anomalia_detectada = db.Column(db.Boolean, nullable=False, default=False)
    payload_crudo = db.Column(db.JSON, nullable=False)
    resumen_agente = db.Column(db.Text, nullable=True)
    procesado_etl = db.Column(db.Boolean, nullable=False, default=False, index=True)
    fecha_captura = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    dispositivo = db.relationship('DispositivoIoT', back_populates='telemetrias')

    def __repr__(self):
        return f'<TelemetriaECBD {self.id_registro} {self.tipo_evento}>'
