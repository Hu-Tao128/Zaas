from flask_wtf import FlaskForm
from wtforms import TextAreaField, IntegerField, StringField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class MensajeForm(FlaskForm):
    contenido = TextAreaField('Mensaje', validators=[DataRequired()])


class CalificacionForm(FlaskForm):
    puntaje = IntegerField('Puntaje (1-5)', validators=[DataRequired(), NumberRange(min=1, max=5)])
    comentarios = TextAreaField('Comentarios')


class IncidenciaForm(FlaskForm):
    tipo = SelectField('Tipo', choices=[
        ('acoso', 'Acoso'),
        ('fraude', 'Fraude'),
        ('incumplimiento', 'Incumplimiento'),
        ('bug', 'Bug del sistema'),
        ('otro', 'Otro')
    ], validators=[DataRequired()])
    descripcion = TextAreaField('Descripción', validators=[DataRequired()])
    id_contrato = SelectField(
        'Contrato relacionado (opcional)',
        coerce=int,
        validators=[Optional()],
        validate_choice=False,
    )
