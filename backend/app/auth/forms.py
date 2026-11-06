from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegistroForm(FlaskForm):
    nombres = StringField('Nombres', validators=[DataRequired(), Length(max=100)])
    apellido_paterno = StringField('Apellido Paterno', validators=[DataRequired(), Length(max=100)])
    apellido_materno = StringField('Apellido Materno', validators=[Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    confirmar_password = PasswordField('Confirmar Contraseña', validators=[DataRequired(), EqualTo('password')])
    tipo_usuario = SelectField('Tipo de Cuenta', choices=[
        ('cliente', 'Cliente'),
        ('desarrollador', 'Desarrollador')
    ], validators=[DataRequired()])


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember = BooleanField('Recordarme')


class PerfilForm(FlaskForm):
    descripcion = TextAreaField('Descripción')
    habilidades = StringField('Habilidades (separadas por comas)')
    empresa = StringField('Empresa', validators=[Length(max=150)])
    stack_tecnologico = TextAreaField('Stack Tecnológico')
    enlaces = StringField('Enlaces (separados por comas)')
