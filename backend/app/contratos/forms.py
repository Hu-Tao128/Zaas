from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FloatField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional


class ContratoForm(FlaskForm):
    """Datos para crear un contrato.

    El cliente siempre es el usuario autenticado; por eso no se pide su ID.
    El desarrollador, el producto y la oferta se eligen de listas, no a mano.
    """

    id_desarrollador = SelectField(
        'Desarrollador',
        coerce=int,
        validators=[DataRequired(message='Selecciona un desarrollador.')],
        validate_choice=False,
    )
    id_producto = SelectField(
        'Producto relacionado (opcional)',
        coerce=int,
        validators=[Optional()],
        validate_choice=False,
    )
    id_encargo = SelectField(
        'Oferta relacionada (opcional)',
        coerce=int,
        validators=[Optional()],
        validate_choice=False,
    )
    costo_acordado = FloatField(
        'Costo acordado (MXN)',
        validators=[
            InputRequired(message='Indica el costo acordado.'),
            NumberRange(min=0.01, message='El costo debe ser mayor a cero.'),
        ],
    )
    plantilla_id = SelectField(
        'Plantilla de contrato',
        coerce=int,
        validators=[DataRequired(message='Selecciona una plantilla.')],
        validate_choice=False,
    )
    notas = TextAreaField(
        'Notas adicionales (opcional)',
        validators=[Length(max=2000, message='Las notas no pueden superar los 2000 caracteres.')],
    )
    submit = SubmitField('Crear contrato')


class EntregableForm(FlaskForm):
    titulo = StringField(
        'Título',
        validators=[DataRequired(message='El título es obligatorio.'), Length(max=200)],
    )
    descripcion = TextAreaField('Descripción')
    url_archivo = StringField('URL del archivo', validators=[Length(max=500)])
    submit = SubmitField('Subir entregable')


class AceptacionForm(FlaskForm):
    acepto = BooleanField(
        'He leído y acepto los términos y condiciones de este contrato.',
        validators=[DataRequired(message='Debes confirmar que aceptas el contrato.')],
    )
    submit = SubmitField('Confirmar aceptación')


class RevisionEntregableForm(FlaskForm):
    comentario = TextAreaField('Comentario')
    aprobar = SubmitField('Aprobar')
    rechazar = SubmitField('Rechazar')


class ConfirmarForm(FlaskForm):
    confirmar = SubmitField('Confirmar')
