class IncidenciaError(Exception):
    codigo = "incidencia_error"
    mensaje = "No se pudo procesar la incidencia."

    def __init__(self, mensaje=None, codigo=None):
        super().__init__(mensaje or self.mensaje)
        self.mensaje = mensaje or self.mensaje
        self.codigo = codigo or self.codigo


class IncidenciaTipoInvalidoError(IncidenciaError):
    codigo = "incidencia_tipo_invalido"
    mensaje = "El tipo de incidencia no es válido."


class IncidenciaContratoRequeridoError(IncidenciaError):
    codigo = "incidencia_contrato_requerido"
    mensaje = "Debes seleccionar un contrato para este tipo de incidencia."


class IncidenciaContratoAjenoError(IncidenciaError):
    codigo = "incidencia_contrato_ajeno"
    mensaje = "No tienes acceso al contrato seleccionado."


class IncidenciaDetalleRequeridoError(IncidenciaError):
    codigo = "incidencia_detalle_requerido"
    mensaje = "Debes indicar el tipo de incidencia cuando seleccionas \"Otro\"."


class IncidenciaDescripcionInvalidaError(IncidenciaError):
    codigo = "incidencia_descripcion_invalida"
    mensaje = "La descripción debe tener entre 10 y 1000 caracteres."
