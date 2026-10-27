from datetime import datetime
from app.extensions import db


class Pago(db.Model):
    __tablename__ = 'pago'

    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    estado_escrow = db.Column(db.String(20), default='retenido')
    # estados: retenido, liberado, reembolsado, dividido
    fecha_pago = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_liberacion = db.Column(db.DateTime)

    contrato = db.relationship('Contrato', backref='pagos')
    liberaciones = db.relationship('Liberacion', back_populates='pago', cascade='all, delete-orphan')
    recibos = db.relationship('Recibo', back_populates='pago', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Pago Contrato{self.id_contrato} ${self.monto} - {self.estado_escrow}>'


class Liberacion(db.Model):
    __tablename__ = 'liberacion'

    id = db.Column(db.Integer, primary_key=True)
    id_pago = db.Column(db.Integer, db.ForeignKey('pago.id'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    monto_liberado = db.Column(db.Float, nullable=False)
    motivo = db.Column(db.Text)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)

    pago = db.relationship('Pago', back_populates='liberaciones')
    usuario = db.relationship('Usuario', backref='liberaciones')

    def __repr__(self):
        return f'<Liberacion Pago{self.id_pago} ${self.monto_liberado}>'


class Recibo(db.Model):
    __tablename__ = 'recibo'

    id = db.Column(db.Integer, primary_key=True)
    id_pago = db.Column(db.Integer, db.ForeignKey('pago.id'), nullable=False)
    folio = db.Column(db.String(50), unique=True, nullable=False)
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow)
    contenido_html = db.Column(db.Text)

    pago = db.relationship('Pago', back_populates='recibos')

    def __repr__(self):
        return f'<Recibo {self.folio}>'


class Disputa(db.Model):
    __tablename__ = 'disputa'

    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    id_admin = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    id_reportante = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tipo = db.Column(db.String(50))
    descripcion = db.Column(db.Text)
    fecha_hora_publicacion = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='abierta')
    # estados: abierta, en_revision, resuelta, cerrada
    fecha_hora_resolucion = db.Column(db.DateTime)
    resolucion = db.Column(db.Text)

    contrato = db.relationship('Contrato', backref='disputas')
    admin = db.relationship('Usuario', foreign_keys=[id_admin], backref='disputas_resueltas')
    reportante = db.relationship('Usuario', foreign_keys=[id_reportante], backref='disputas_reportadas')

    def __repr__(self):
        return f'<Disputa Contrato{self.id_contrato} - {self.estado}>'


class Arbitraje(db.Model):
    __tablename__ = 'arbitraje'

    id = db.Column(db.Integer, primary_key=True)
    id_disputa = db.Column(db.Integer, db.ForeignKey('disputa.id'), nullable=False)
    id_arbitro = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    decision = db.Column(db.String(20))  # liberar, reembolsar, dividir
    porcentaje_desarrollador = db.Column(db.Float)  # 0-100, solo si decision='dividir'
    notas = db.Column(db.Text)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)

    disputa = db.relationship('Disputa', backref='arbitrajes')
    arbitro = db.relationship('Usuario', backref='arbitrajes')

    def __repr__(self):
        return f'<Arbitraje Disputa{self.id_disputa} - {self.decision}>'
