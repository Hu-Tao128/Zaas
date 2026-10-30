from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, BooleanField, DateField, DateTimeLocalField
from wtforms.validators import DataRequired, Length, NumberRange


class ProyectoForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired(), Length(max=200)])
    descripcion = TextAreaField('Descripción')
    precio = FloatField('Precio', validators=[DataRequired(), NumberRange(min=0)])
    demo_habilitada = BooleanField('Habilitar demo')


class OfertaForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired(), Length(max=200)])
    descripcion = TextAreaField('Descripción de Requerimientos')
    presupuesto = FloatField('Presupuesto', validators=[NumberRange(min=0)])
    fecha_entrega = DateTimeLocalField('Fecha de Entrega')


class PostulacionForm(FlaskForm):
    detalles = TextAreaField('Detalles de la Postulación', validators=[DataRequired()])
    costo_propuesto = FloatField('Costo Propuesto', validators=[DataRequired(), NumberRange(min=0)])


class DemoForm(FlaskForm):
    nombre_contacto = StringField('Nombre de Contacto', validators=[DataRequired(), Length(max=150)])
    correo_contacto = StringField('Correo de Contacto', validators=[DataRequired(), Length(max=150)])
