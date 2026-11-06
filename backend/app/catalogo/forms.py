from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, BooleanField, DateField, DateTimeLocalField, SelectMultipleField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError


class ActionForm(FlaskForm):
    """Formulario vacío; solo aporta el token CSRF a acciones POST (p. ej. cerrar)."""


class ProyectoForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired(), Length(min=3, max=200)])
    descripcion = TextAreaField('Descripción', validators=[DataRequired(), Length(min=10)])
    precio = FloatField('Precio', validators=[
        DataRequired(message='Ingresa un precio válido.'),
        NumberRange(min=0.01, message='El precio debe ser mayor que 0.')])
    demo_habilitada = BooleanField('Habilitar demo')
    categorias_ids = SelectMultipleField('Categorías', coerce=int, validators=[Optional()])
    tecnologias_ids = SelectMultipleField('Tecnologías', coerce=int, validators=[Optional()])


class OfertaForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired(), Length(min=3, max=200)])
    descripcion = TextAreaField('Descripción de Requerimientos', validators=[DataRequired(), Length(min=10)])
    presupuesto = FloatField('Presupuesto', validators=[
        Optional(),
        NumberRange(min=0.01, message='El presupuesto debe ser mayor que 0.')])
    fecha_entrega = DateTimeLocalField('Fecha de Entrega', validators=[Optional()])

    def validate_fecha_entrega(self, field):
        if field.data and field.data < datetime.now():
            raise ValidationError('La fecha de entrega debe ser futura.')


class PostulacionForm(FlaskForm):
    detalles = TextAreaField('Detalles de la Postulación', validators=[DataRequired(), Length(min=10)])
    costo_propuesto = FloatField('Costo Propuesto', validators=[
        DataRequired(message='Ingresa un costo válido.'),
        NumberRange(min=0.01, message='El costo debe ser mayor que 0.')])


class DemoForm(FlaskForm):
    nombre_contacto = StringField('Nombre de Contacto', validators=[DataRequired(), Length(max=150)])
    correo_contacto = StringField('Correo de Contacto', validators=[DataRequired(), Length(max=150)])
