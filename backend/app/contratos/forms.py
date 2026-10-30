from flask_wtf import FlaskForm
from wtforms import IntegerField, FloatField, TextAreaField, StringField
from wtforms.validators import DataRequired, NumberRange


class ContratoForm(FlaskForm):
    id_cliente = IntegerField('ID Cliente', validators=[DataRequired()])
    id_desarrollador = IntegerField('ID Desarrollador', validators=[DataRequired()])
    id_producto = IntegerField('ID Producto (opcional)')
    id_encargo = IntegerField('ID Encargo (opcional)')
    costo_acordado = FloatField('Costo Acordado', validators=[DataRequired(), NumberRange(min=0)])
    terminos_condiciones = TextAreaField('Términos y Condiciones')


class EntregableForm(FlaskForm):
    titulo = StringField('Título', validators=[DataRequired()])
    descripcion = TextAreaField('Descripción')
    url_archivo = StringField('URL del Archivo')
