"""Tabla de rutas: cada dirección de la API apunta a una función."""
from backend import bitacora, cobro, periodos, tarifas
from backend.errores import ApiError


def catalogos(cur, datos):
    """Listas para llenar los selectores de la pantalla."""
    resultado = {}
    cur.execute("SELECT * FROM clientes ORDER BY nombre")
    resultado["clientes"] = cur.fetchall()
    cur.execute("SELECT * FROM productos ORDER BY codigo")
    resultado["productos"] = cur.fetchall()
    cur.execute("SELECT * FROM usuarios ORDER BY nombre")
    resultado["usuarios"] = cur.fetchall()
    return resultado


RUTAS = {
    ("GET",  "/api/init"):                 catalogos,
    ("GET",  "/api/periodos"):             periodos.listar,
    ("GET",  "/api/tarifas"):              tarifas.listar,
    ("GET",  "/api/bitacora"):             bitacora.listar,
    ("GET",  "/api/recibos"):              cobro.listar_recibos,
    ("POST", "/api/calcular"):             periodos.calcular_vista_previa,
    ("POST", "/api/periodos"):             periodos.crear,
    ("POST", "/api/periodos/recalcular"):  periodos.recalcular,
    ("POST", "/api/cobro"):                cobro.calcular,
    ("POST", "/api/recibos"):              cobro.crear_recibo,
    ("POST", "/api/tarifas"):              tarifas.crear,
}


def atender(metodo, ruta, datos, cur):
    funcion = RUTAS.get((metodo, ruta))
    if funcion is None:
        raise ApiError("Ruta no encontrada.", 404)
    return funcion(cur, datos)
