from datetime import datetime
from flask_login import UserMixin
from app.extensions import db


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    __table_args__ = (
        db.CheckConstraint(
            "tipo_usuario IN ('cliente', 'desarrollador', 'admin')",
            name='ck_usuario_tipo_usuario',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True, index=True)
    nombres = db.Column(db.String(100), nullable=False)
    apellido_paterno = db.Column(db.String(100), nullable=False)
    apellido_materno = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True, nullable=False)
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

    @property
    def nombre_completo(self):
        partes = [self.nombres, self.apellido_paterno, self.apellido_materno]
        return ' '.join(parte.strip() for parte in partes if parte and parte.strip())

    def __repr__(self):
        return f'<Usuario {self.email}>'


class Perfil(db.Model):
    __tablename__ = 'perfil'

    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(
        db.Integer, db.ForeignKey('usuario.id'), nullable=False, unique=True
    )
    descripcion = db.Column(db.Text)
    empresa = db.Column(db.String(150))
    enlaces = db.Column(db.Text)

    usuario = db.relationship('Usuario', back_populates='perfil')
    habilidades = db.relationship(
        'PerfilHabilidad', back_populates='perfil', cascade='all, delete-orphan'
    )
    tecnologias = db.relationship(
        'PerfilTecnologia', back_populates='perfil', cascade='all, delete-orphan'
    )

    @property
    def nombres_habilidades(self):
        return [item.habilidad.nombre for item in self.habilidades if item.habilidad]

    @property
    def nombres_tecnologias(self):
        return [item.tecnologia.nombre for item in self.tecnologias if item.tecnologia]

    def __repr__(self):
        return f'<Perfil Usuario {self.id_usuario}>'


class Habilidad(db.Model):
    __tablename__ = 'habilidad'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

    perfiles = db.relationship(
        'PerfilHabilidad', back_populates='habilidad', cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Habilidad {self.nombre}>'


class PerfilHabilidad(db.Model):
    __tablename__ = 'perfil_habilidad'
    __table_args__ = (
        db.UniqueConstraint('id_perfil', 'id_habilidad', name='uq_perfil_habilidad'),
    )

    id = db.Column(db.Integer, primary_key=True)
    id_perfil = db.Column(db.Integer, db.ForeignKey('perfil.id'), nullable=False)
    id_habilidad = db.Column(db.Integer, db.ForeignKey('habilidad.id'), nullable=False)

    perfil = db.relationship('Perfil', back_populates='habilidades')
    habilidad = db.relationship('Habilidad', back_populates='perfiles')

    def __repr__(self):
        return f'<PerfilHabilidad perfil={self.id_perfil} habilidad={self.id_habilidad}>'


class PerfilTecnologia(db.Model):
    __tablename__ = 'perfil_tecnologia'
    __table_args__ = (
        db.UniqueConstraint('id_perfil', 'id_tecnologia', name='uq_perfil_tecnologia'),
    )

    id = db.Column(db.Integer, primary_key=True)
    id_perfil = db.Column(db.Integer, db.ForeignKey('perfil.id'), nullable=False)
    id_tecnologia = db.Column(db.Integer, db.ForeignKey('tecnologia.id'), nullable=False)

    perfil = db.relationship('Perfil', back_populates='tecnologias')
    tecnologia = db.relationship('Tecnologia')

    def __repr__(self):
        return f'<PerfilTecnologia perfil={self.id_perfil} tecnologia={self.id_tecnologia}>'
