from datetime import datetime
from app.extensions import db


class Pago(db.Model):
    __tablename__ = 'pago'
    __table_args__ = (
        db.CheckConstraint(
            "estado_escrow IN ('retenido', 'liberado', 'reembolsado', 'dividido')",
            name='ck_pago_estado_escrow',
        ),
        db.CheckConstraint('monto >= 0', name='ck_pago_monto'),
    )

    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    estado_escrow = db.Column(db.String(20), default='retenido')
    # estados: retenido, liberado, reembolsado, dividido
    fecha_pago = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_liberacion = db.Column(db.DateTime)
    metodo_pago = db.Column(db.String(50))
    transaccion_id = db.Column(db.String(100), unique=True)

    contrato = db.relationship('Contrato', back_populates='pagos')
    liberaciones = db.relationship('Liberacion', back_populates='pago', cascade='all, delete-orphan')
    recibos = db.relationship('Recibo', back_populates='pago', cascade='all, delete-orphan')
    disputas = db.relationship('Disputa', back_populates='pago')

    def __repr__(self):
        return f'<Pago Contrato{self.id_contrato} ${self.monto} - {self.estado_escrow}>'


class Liberacion(db.Model):
    __tablename__ = 'liberacion'
    __table_args__ = (
        db.CheckConstraint('monto_liberado >= 0', name='ck_liberacion_monto'),
    )

    id = db.Column(db.Integer, primary_key=True)
    id_pago = db.Column(db.Integer, db.ForeignKey('pago.id'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    id_entregable = db.Column(db.Integer, db.ForeignKey('entregable.id'))
    monto_liberado = db.Column(db.Float, nullable=False)
    motivo = db.Column(db.Text)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)

    pago = db.relationship('Pago', back_populates='liberaciones')
    usuario = db.relationship('Usuario', back_populates='liberaciones')
    entregable = db.relationship('Entregable')

    def __repr__(self):
        return f'<Liberacion Pago{self.id_pago} ${self.monto_liberado}>'


class Recibo(db.Model):
    __tablename__ = 'recibo'
    __table_args__ = (
        db.CheckConstraint('total IS NULL OR total >= 0', name='ck_recibo_total'),
    )

    id = db.Column(db.Integer, primary_key=True)
    id_pago = db.Column(db.Integer, db.ForeignKey('pago.id'), nullable=False, unique=True)
    folio = db.Column(db.String(50), unique=True, nullable=False)
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float)
    contenido_html = db.Column(db.Text)

    pago = db.relationship('Pago', back_populates='recibos')

    def __repr__(self):
        return f'<Recibo {self.folio}>'


class Disputa(db.Model):
    __tablename__ = 'disputa'
    __table_args__ = (
        db.CheckConstraint(
            "estado IN ('abierta', 'en_revision', 'resuelta', 'cerrada')",
            name='ck_disputa_estado',
        ),
        db.CheckConstraint(
            '(id_pago IS NOT NULL) + (id_entregable IS NOT NULL) <= 1',
            name='ck_disputa_pago_o_entregable',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    id_admin = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    id_reportante = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    id_pago = db.Column(db.Integer, db.ForeignKey('pago.id'))
    id_entregable = db.Column(db.Integer, db.ForeignKey('entregable.id'))
    id_incidencia = db.Column(db.Integer, db.ForeignKey('incidencia.id'), unique=True)
    tipo = db.Column(db.String(50))
    descripcion = db.Column(db.Text)
    fecha_hora_publicacion = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='abierta')
    # estados: abierta, en_revision, resuelta, cerrada
    fecha_hora_resolucion = db.Column(db.DateTime)
    resolucion = db.Column(db.Text)

    contrato = db.relationship('Contrato', back_populates='disputas')
    admin = db.relationship('Usuario', foreign_keys=[id_admin], back_populates='disputas_resueltas')
    reportante = db.relationship('Usuario', foreign_keys=[id_reportante], back_populates='disputas_reportadas')
    pago = db.relationship('Pago', back_populates='disputas')
    entregable = db.relationship('Entregable')
    incidencia = db.relationship('Incidencia')
    arbitrajes = db.relationship('Arbitraje', back_populates='disputa', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Disputa Contrato{self.id_contrato} - {self.estado}>'


class Arbitraje(db.Model):
    __tablename__ = 'arbitraje'
    __table_args__ = (
        db.CheckConstraint(
            "decision IN ('liberar', 'reembolsar', 'dividir')",
            name='ck_arbitraje_decision',
        ),
        db.CheckConstraint(
            'porcentaje_desarrollador IS NULL OR '
            '(porcentaje_desarrollador >= 0 AND porcentaje_desarrollador <= 100)',
            name='ck_arbitraje_porcentaje',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    id_disputa = db.Column(
        db.Integer, db.ForeignKey('disputa.id'), nullable=False, unique=True
    )
    id_arbitro = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    decision = db.Column(db.String(20))  # liberar, reembolsar, dividir
    porcentaje_desarrollador = db.Column(db.Float)  # 0-100, solo si decision='dividir'
    notas = db.Column(db.Text)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)

    disputa = db.relationship('Disputa', back_populates='arbitrajes')
    arbitro = db.relationship('Usuario', back_populates='arbitrajes')

    def __repr__(self):
        return f'<Arbitraje Disputa{self.id_disputa} - {self.decision}>'
