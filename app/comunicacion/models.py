from datetime import datetime
from app.extensions import db


class Conversacion(db.Model):
    __tablename__ = 'conversacion'

    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contrato.id'))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    contrato = db.relationship('Contrato', backref='conversaciones')
    mensajes = db.relationship('Mensaje', back_populates='conversacion', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Conversacion {self.id}>'


class Mensaje(db.Model):
    __tablename__ = 'mensaje'

    id = db.Column(db.Integer, primary_key=True)
    id_conversacion = db.Column(db.Integer, db.ForeignKey('conversacion.id'), nullable=False)
    id_emisor = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    id_receptor = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)
    leido = db.Column(db.Boolean, default=False)

    conversacion = db.relationship('Conversacion', back_populates='mensajes')
    emisor = db.relationship('Usuario', foreign_keys=[id_emisor], backref='mensajes_enviados')
    receptor = db.relationship('Usuario', foreign_keys=[id_receptor], backref='mensajes_recibidos')

    def __repr__(self):
        return f'<Mensaje {self.id} de {self.id_emisor} a {self.id_receptor}>'


class Notificacion(db.Model):
    __tablename__ = 'notificacion'

    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    asunto = db.Column(db.String(200), nullable=False)
    mensaje = db.Column(db.Text)
    leido = db.Column(db.Boolean, default=False)
    fecha_hora_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    link = db.Column(db.String(500))

    usuario = db.relationship('Usuario', backref='notificaciones')

    def __repr__(self):
        return f'<Notificacion Usuario{self.id_usuario} - {self.asunto}>'


class Calificacion(db.Model):
    __tablename__ = 'calificacion'

    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contrato.id'), nullable=False)
    id_evaluador = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    id_evaluado = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    puntaje = db.Column(db.Integer, nullable=False)  # 1-5
    comentarios = db.Column(db.Text)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)

    contrato = db.relationship('Contrato', backref='calificaciones')
    evaluador = db.relationship('Usuario', foreign_keys=[id_evaluador], backref='calificaciones_dadas')
    evaluado = db.relationship('Usuario', foreign_keys=[id_evaluado], backref='calificaciones_recibidas')

    def __repr__(self):
        return f'<Calificacion {self.puntaje}/5 a Usuario{self.id_evaluado}>'


class Incidencia(db.Model):
    __tablename__ = 'incidencia'

    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    id_admin = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    tipo = db.Column(db.String(50))
    descripcion = db.Column(db.Text)
    estado = db.Column(db.String(20), default='abierta')  # abierta, en_proceso, resuelta, cerrada
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)
    resolucion = db.Column(db.Text)
    fecha_resolucion = db.Column(db.DateTime)

    usuario = db.relationship('Usuario', foreign_keys=[id_usuario], backref='incidencias')
    admin = db.relationship('Usuario', foreign_keys=[id_admin], backref='incidencias_resueltas')

    def __repr__(self):
        return f'<Incidencia Usuario{self.id_usuario} - {self.estado}>'
