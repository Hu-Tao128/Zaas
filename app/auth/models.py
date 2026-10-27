from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(100), nullable=False)
    apellido_paterno = db.Column(db.String(100), nullable=False)
    apellido_materno = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    tipo_usuario = db.Column(db.String(20), nullable=False)  # 'cliente', 'desarrollador', 'admin'

    # Relaciones — back_populates definidos en los modelos de cada blueprint
    perfil = db.relationship('Perfil', back_populates='usuario', uselist=False, cascade='all, delete-orphan')
    contratos_como_cliente = db.relationship('Contrato', foreign_keys='Contrato.id_cliente', back_populates='cliente')
    contratos_como_desarrollador = db.relationship('Contrato', foreign_keys='Contrato.id_desarrollador', back_populates='desarrollador')
    proyectos = db.relationship('Proyecto', back_populates='autor')
    ofertas = db.relationship('OfertaTrabajo', back_populates='cliente')
    calificaciones_dadas = db.relationship('Calificacion', foreign_keys='Calificacion.id_evaluador', back_populates='evaluador')
    calificaciones_recibidas = db.relationship('Calificacion', foreign_keys='Calificacion.id_evaluado', back_populates='evaluado')
    notificaciones = db.relationship('Notificacion', back_populates='usuario')
    incidencias = db.relationship('Incidencia', foreign_keys='Incidencia.id_usuario', back_populates='usuario')
    incidencias_resueltas = db.relationship('Incidencia', foreign_keys='Incidencia.id_admin', back_populates='admin')
    aceptaciones = db.relationship('Aceptacion', back_populates='usuario')
    liberaciones = db.relationship('Liberacion', back_populates='usuario')
    arbitrajes = db.relationship('Arbitraje', back_populates='arbitro')
    disputas_reportadas = db.relationship('Disputa', foreign_keys='Disputa.id_reportante', back_populates='reportante')
    disputas_resueltas = db.relationship('Disputa', foreign_keys='Disputa.id_admin', back_populates='admin')
    mensajes_enviados = db.relationship('Mensaje', foreign_keys='Mensaje.id_emisor', back_populates='emisor')
    mensajes_recibidos = db.relationship('Mensaje', foreign_keys='Mensaje.id_receptor', back_populates='receptor')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Usuario {self.email}>'


class Perfil(db.Model):
    __tablename__ = 'perfil'

    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    descripcion = db.Column(db.Text)
    habilidades = db.Column(db.Text)  # lista separada por comas
    empresa = db.Column(db.String(150))
    stack_tecnologico = db.Column(db.Text)
    enlaces = db.Column(db.Text)

    usuario = db.relationship('Usuario', back_populates='perfil')

    def __repr__(self):
        return f'<Perfil Usuario {self.id_usuario}>'
