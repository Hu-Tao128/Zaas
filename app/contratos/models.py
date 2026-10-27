from datetime import datetime
from app.extensions import db


class PlantillaContrato(db.Model):
    __tablename__ = 'plantilla_contrato'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    contenido_html = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PlantillaContrato {self.nombre}>'


class Contrato(db.Model):
    __tablename__ = 'contrato'

    id = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    id_desarrollador = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    id_producto = db.Column(db.Integer, db.ForeignKey('proyecto.id'))
    id_encargo = db.Column(db.Integer, db.ForeignKey('oferta_trabajo.id'))
    terminos_condiciones = db.Column(db.Text)
    costo_acordado = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(20), default='borrador')
    # estados: borrador, pendiente, aceptado, en_progreso, entregado, finalizado, cancelado
    firma_cliente = db.Column(db.String(64))  # hash de aceptación
    firma_desarrollador = db.Column(db.String(64))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship('Usuario', foreign_keys=[id_cliente], back_populates='contratos_como_cliente')
    desarrollador = db.relationship('Usuario', foreign_keys=[id_desarrollador], back_populates='contratos_como_desarrollador')
    producto = db.relationship('Proyecto', back_populates='contratos')
    encargo = db.relationship('OfertaTrabajo', back_populates='contratos')
    entregables = db.relationship('Entregable', back_populates='contrato', cascade='all, delete-orphan')
    aceptaciones = db.relationship('Aceptacion', back_populates='contrato', cascade='all, delete-orphan')
    conversaciones = db.relationship('Conversacion', back_populates='contrato', cascade='all, delete-orphan')
    disputas = db.relationship('Disputa', back_populates='contrato', cascade='all, delete-orphan')
    calificaciones = db.relationship('Calificacion', back_populates='contrato', cascade='all, delete-orphan')
    pagos = db.relationship('Pago', back_populates='contrato', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Contrato {self.id} - {self.estado}>'


class Entregable(db.Model):
    __tablename__ = 'entregable'

    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    url_archivo = db.Column(db.String(500))
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aprobado, rechazado
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_revision = db.Column(db.DateTime)
    comentario_revision = db.Column(db.Text)

    contrato = db.relationship('Contrato', back_populates='entregables')

    def __repr__(self):
        return f'<Entregable {self.titulo}>'


class Aceptacion(db.Model):
    """Registro de aceptación digital de un contrato."""
    __tablename__ = 'aceptacion'

    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)
    ip = db.Column(db.String(45))

    contrato = db.relationship('Contrato', back_populates='aceptaciones')
    usuario = db.relationship('Usuario', back_populates='aceptaciones')

    def __repr__(self):
        return f'<Aceptacion Contrato{self.id_contrato} Usuario{self.id_usuario}>'
