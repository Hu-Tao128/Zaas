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

    # Relaciones
    perfil = db.relationship('Perfil', backref='usuario', uselist=False, cascade='all, delete-orphan')
    contratos_cliente = db.relationship('Contrato', foreign_keys='Contrato.id_cliente', backref='cliente_contratos')
    contratos_desarrollador = db.relationship('Contrato', foreign_keys='Contrato.id_desarrollador', backref='desarrollador_contratos')

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

    def __repr__(self):
        return f'<Perfil Usuario {self.id_usuario}>'
