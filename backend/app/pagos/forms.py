from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FloatField
from wtforms.validators import DataRequired, NumberRange


class PagoForm(FlaskForm):
    """Formulario simulado de pago (sin integración real con pasarela)."""
    pass  # El pago usa directamente el costo del contrato


class DisputaForm(FlaskForm):
    tipo = StringField('Tipo de Disputa', validators=[DataRequired()])
    descripcion = TextAreaField('Descripción', validators=[DataRequired()])


class ArbitrajeForm(FlaskForm):
    decision = SelectField('Decisión', choices=[
        ('liberar', 'Liberar fondos al desarrollador'),
        ('reembolsar', 'Reembolsar al cliente'),
        ('dividir', 'Dividir fondos')
    ], validators=[DataRequired()])
    porcentaje_desarrollador = FloatField('% para el desarrollador (si divide)', validators=[NumberRange(min=0, max=100)])
    notas = TextAreaField('Notas de Resolución')
