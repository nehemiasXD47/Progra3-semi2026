"""Cobro: Cargo = Cantidad x Precio mensual x Meses aplicables."""
from backend import bitacora
from backend.errores import ApiError
from backend.utilidades import a_fecha, meses_entre, redondear2


def calcular(cur, datos):
    desde = a_fecha(datos.get("desde"))
    hasta = a_fecha(datos.get("hasta"))
    if desde >= hasta:
        raise ApiError("La fecha Hasta debe ser posterior a la fecha Desde.")

    # Solo los períodos que se superponen con el rango del cobro
    cur.execute(
        """SELECT * FROM periodos
           WHERE cliente_id = %s AND producto_codigo = %s AND desde < %s AND hasta > %s
           ORDER BY desde""",
        (datos.get("cliente_id"), datos.get("producto_codigo"), hasta, desde),
    )
    detalle = []
    total = 0
    meses_cubiertos = 0
    for p in cur.fetchall():
        inicio = max(p["desde"], desde)      # tramo del período que cae dentro del cobro
        fin = min(p["hasta"], hasta)
        meses = meses_entre(inicio, fin)
        importe = redondear2(p["cantidad"] * p["precio"] * meses)
        total += importe
        meses_cubiertos += meses
        detalle.append({"periodo_id": p["id"], "desde": inicio, "hasta": fin, "balance": p["balance"],
                        "cantidad": p["cantidad"], "precio": redondear2(p["precio"]),
                        "meses": meses, "importe": importe})

    avisos = []
    if not detalle:
        avisos.append("No hay períodos registrados que cubran el rango de cobro.")
    elif meses_cubiertos < meses_entre(desde, hasta):
        avisos.append("El rango de cobro no está cubierto totalmente por períodos registrados.")
    return {"detalle": detalle, "total": total, "avisos": avisos}


def crear_recibo(cur, datos):
    usuario = datos.get("usuario") or "sistema"
    cobro = calcular(cur, datos)
    if not cobro["detalle"]:
        raise ApiError(cobro["avisos"][0])

    cur.execute(
        "INSERT INTO recibos (cliente_id, producto_codigo, desde, hasta, total, creado_por) VALUES (%s,%s,%s,%s,%s,%s)",
        (datos["cliente_id"], datos["producto_codigo"], datos["desde"], datos["hasta"], cobro["total"], usuario),
    )
    recibo_id = cur.lastrowid

    for x in cobro["detalle"]:
        cur.execute(
            """INSERT INTO recibo_detalle (recibo_id, periodo_id, desde, hasta, meses, cantidad, precio, importe)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (recibo_id, x["periodo_id"], x["desde"], x["hasta"], x["meses"], x["cantidad"], x["precio"], x["importe"]),
        )
        cur.execute("UPDATE periodos SET facturado = 1 WHERE id = %s", (x["periodo_id"],))   # ya no se recalcula solo
        bitacora.registrar(cur, x["periodo_id"], usuario, "FACTURADO", {"recibo_id": recibo_id, "importe": x["importe"]})

    return {"id": recibo_id, "mensaje": f"Recibo {recibo_id} generado.", **cobro}


def listar_recibos(cur, datos):
    cur.execute("""SELECT r.*, c.nombre AS cliente FROM recibos r
                   JOIN clientes c ON c.id = r.cliente_id ORDER BY r.id DESC LIMIT 50""")
    return {"filas": cur.fetchall()}
