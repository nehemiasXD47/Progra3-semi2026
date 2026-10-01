"""Error controlado: se muestra tal cual al usuario en la pantalla."""


class ApiError(Exception):
    def __init__(self, mensaje, codigo=400, extra=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
        self.extra = extra or {}
