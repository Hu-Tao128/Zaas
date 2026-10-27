from datetime import datetime
from app.extensions import db


class Proyecto(db.Model):
    """Un proyecto/producto publicado por un desarrollador."""
    __tablename__ = 'proyecto'

    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    demo_habilitada = db.Column(db.Boolean, default=False)
    fecha_publicacion = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default='activo')  # activo, cerrado

    # Relaciones
    categorias = db.relationship('CategoriaProyecto', back_populates='proyecto', cascade='all, delete-orphan')
    tecnologias = db.relationship('TecnologiaProyecto', back_populates='proyecto', cascade='all, delete-orphan')
    solicitudes_demo = db.relationship('SolicitudDemo', back_populates='producto', cascade='all, delete-orphan')

    autor = db.relationship('Usuario', backref='proyectos')

    def __repr__(self):
        return f'<Proyecto {self.titulo}>'


class Categoria(db.Model):
    __tablename__ = 'categoria'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)


class CategoriaProyecto(db.Model):
    """Tabla intermedia proyecto <-> categoría."""
    __tablename__ = 'categoria_proyecto'

    id = db.Column(db.Integer, primary_key=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)
    id_categoria = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)

    proyecto = db.relationship('Proyecto', back_populates='categorias')
    categoria = db.relationship('Categoria')


class Tecnologia(db.Model):
    __tablename__ = 'tecnologia'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)


class TecnologiaProyecto(db.Model):
    """Tabla intermedia proyecto <-> tecnología."""
    __tablename__ = 'tecnologia_proyecto'

    id = db.Column(db.Integer, primary_key=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)
    id_tecnologia = db.Column(db.Integer, db.ForeignKey('tecnologia.id'), nullable=False)

    proyecto = db.relationship('Proyecto', back_populates='tecnologias')
    tecnologia = db.relationship('Tecnologia')


class OfertaTrabajo(db.Model):
    """Un encargo/solicitud de desarrollo publicado por un cliente."""
    __tablename__ = 'oferta_trabajo'

    id = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion_requerimientos = db.Column(db.Text)
    presupuesto = db.Column(db.Float)
    estado = db.Column(db.String(20), default='abierto')  # abierto, en_progreso, cerrado
    fecha_publicacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_entrega = db.Column(db.DateTime)

    cliente = db.relationship('Usuario', backref='ofertas')
    postulaciones = db.relationship('Postulacion', back_populates='oferta', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<OfertaTrabajo {self.titulo}>'


class Postulacion(db.Model):
    """Una postulación de un desarrollador a una oferta de trabajo."""
    __tablename__ = 'postulacion'

    id = db.Column(db.Integer, primary_key=True)
    id_desarrollador = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    id_oferta = db.Column(db.Integer, db.ForeignKey('oferta_trabajo.id'), nullable=False)
    detalles = db.Column(db.Text)
    costo_propuesto = db.Column(db.Float)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aceptada, rechazada
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)

    desarrollador = db.relationship('Usuario', backref='postulaciones')
    oferta = db.relationship('OfertaTrabajo', back_populates='postulaciones')

    def __repr__(self):
        return f'<Postulacion Dev{self.id_desarrollador} -> Oferta{self.id_oferta}>'


class SolicitudDemo(db.Model):
    __tablename__ = 'solicitud_demo'

    id = db.Column(db.Integer, primary_key=True)
    id_producto = db.Column(db.Integer, db.ForeignKey('proyecto.id'), nullable=False)
    id_cliente = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    nombre_contacto = db.Column(db.String(150))
    correo_contacto = db.Column(db.String(150))
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)

    producto = db.relationship('Proyecto', back_populates='solicitudes_demo')
    cliente = db.relationship('Usuario', backref='solicitudes_demo')

    def __repr__(self):
        return f'<SolicitudDemo Producto{self.id_producto}>'
