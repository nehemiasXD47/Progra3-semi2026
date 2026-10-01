"""Períodos anuales: validar, calcular, guardar, cerrar y recalcular."""
from backend import bitacora, tarifas
from backend.errores import ApiError
from backend.utilidades import a_decimal, a_fecha, redondear2

MSG_FACTURADO = "El período ya fue utilizado en recibos y no puede recalcularse automáticamente."
MSG_SUPERPUESTO = "El período indicado se superpone con un período existente."


# ---------- Validación ----------
def validar_datos(cur, datos):
    """Revisa los datos del formulario en el orden del documento. Devuelve los valores ya convertidos."""
    cur.execute("SELECT * FROM clientes WHERE id = %s", (datos.get("cliente_id"),))
    cliente = cur.fetchone()
    if not cliente:
        raise ApiError("Seleccione un cliente.")
    if cliente["tipo"] != "empresa":
        raise ApiError("El Impuesto a las Actividades Económicas requiere un cliente de tipo empresa.")

    cur.execute("SELECT * FROM productos WHERE codigo = %s", (datos.get("producto_codigo") or 0,))
    producto = cur.fetchone()
    if not producto:
        raise ApiError("Confirme si la actividad corresponde a comercio o industria.")

    texto_balance = str(datos.get("balance", "")).strip()
    if texto_balance == "" or a_decimal(texto_balance, "balance") <= 0:
        raise ApiError("Ingrese un balance mayor que cero.")
    balance = a_decimal(texto_balance, "balance")

    desde = a_fecha(datos.get("desde"))
    hasta = a_fecha(datos.get("hasta"))
    if desde >= hasta:
        raise ApiError("La fecha Hasta debe ser posterior a la fecha Desde.")

    cantidad = a_decimal(datos.get("cantidad") or 1, "cantidad")
    if cantidad <= 0:
        raise ApiError("La cantidad debe ser mayor que cero.")

    return {"cliente": cliente, "producto": producto, "balance": balance,
            "desde": desde, "hasta": hasta, "cantidad": cantidad}


def buscar_superpuestos(cur, e):
    """Períodos del mismo cliente y producto que se cruzan con [desde, hasta)."""
    cur.execute(
        """SELECT * FROM periodos
           WHERE cliente_id = %s AND producto_codigo = %s AND desde < %s AND hasta > %s
           ORDER BY desde""",
        (e["cliente"]["id"], e["producto"]["codigo"], e["hasta"], e["desde"]),
    )
    return cur.fetchall()


def buscar_huecos(cur, e):
    """Avisos si queda un espacio sin cobertura antes o después del período nuevo."""
    avisos = []
    cliente, producto = e["cliente"]["id"], e["producto"]["codigo"]

    cur.execute("SELECT MAX(hasta) AS f FROM periodos WHERE cliente_id=%s AND producto_codigo=%s AND hasta <= %s",
                (cliente, producto, e["desde"]))
    anterior = cur.fetchone()["f"]
    if anterior and anterior < e["desde"]:
        avisos.append(f"Existe un espacio sin cobertura entre {anterior} y {e['desde']}.")

    cur.execute("SELECT MIN(desde) AS f FROM periodos WHERE cliente_id=%s AND producto_codigo=%s AND desde >= %s",
                (cliente, producto, e["hasta"]))
    siguiente = cur.fetchone()["f"]
    if siguiente and siguiente > e["hasta"]:
        avisos.append(f"Existe un espacio sin cobertura entre {e['hasta']} y {siguiente}.")
    return avisos


# ---------- Vista previa (sin guardar) ----------
def calcular_vista_previa(cur, datos):
    e = validar_datos(cur, datos)
    tarifa = tarifas.buscar_tarifa(cur, e["producto"]["codigo"], e["balance"], e["desde"])
    calculo = tarifas.calcular_impuesto(tarifa, e["balance"])
    calculo["subtotal"] = redondear2(e["cantidad"] * calculo["precio"])
    superpuestos = buscar_superpuestos(cur, e)
    return {
        "calculo": calculo,
        "avisos": buscar_huecos(cur, e),
        "conflicto": MSG_SUPERPUESTO if superpuestos else None,
        "conflictos": superpuestos,
    }


# ---------- Guardar ----------
def cerrar_periodo_vigente(cur, existente, nueva_fecha, usuario):
    """Si el balance cambió, el período vigente termina donde empieza el nuevo."""
    if existente["facturado"]:
        raise ApiError(MSG_FACTURADO)
    cur.execute("UPDATE periodos SET hasta = %s, modificado_por = %s, modificado_en = NOW() WHERE id = %s",
                (nueva_fecha, usuario, existente["id"]))
    bitacora.registrar(cur, existente["id"], usuario, "CIERRE",
                       {"hasta_anterior": existente["hasta"], "hasta_nuevo": nueva_fecha})


def crear(cur, datos):
    usuario = datos.get("usuario") or "sistema"
    e = validar_datos(cur, datos)
    tarifa = tarifas.buscar_tarifa(cur, e["producto"]["codigo"], e["balance"], e["desde"])
    calculo = tarifas.calcular_impuesto(tarifa, e["balance"])
    subtotal = redondear2(e["cantidad"] * calculo["precio"])

    superpuestos = buscar_superpuestos(cur, e)
    if superpuestos:
        existente = superpuestos[0]
        # Solo se puede cerrar si hay UN período y el nuevo empieza dentro de él
        puede_cerrar = (datos.get("cerrar_vigente") and len(superpuestos) == 1
                        and existente["desde"] < e["desde"] < existente["hasta"])
        if not puede_cerrar:
            raise ApiError(MSG_SUPERPUESTO, extra={"conflictos": superpuestos})
        cerrar_periodo_vigente(cur, existente, e["desde"], usuario)

    cur.execute(
        """INSERT INTO periodos
           (cliente_id, producto_codigo, desde, hasta, balance, cantidad, precio, subtotal,
            tarifa_id, tarifa_version, tarifa_desde, tarifa_hasta, precio_base, adicional, porcentaje,
            formula, fecha_calculo, creado_por)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s)""",
        (e["cliente"]["id"], e["producto"]["codigo"], e["desde"], e["hasta"], e["balance"], e["cantidad"],
         calculo["precio"], subtotal, calculo["tarifa_id"], calculo["tarifa_version"],
         calculo["rango_desde"], calculo["rango_hasta"], calculo["precio_base"], calculo["adicional"],
         calculo["porcentaje"], calculo["formula"], usuario),
    )
    periodo_id = cur.lastrowid
    bitacora.registrar(cur, periodo_id, usuario, "CREACION",
                       {"balance": e["balance"], "precio": calculo["precio"], "formula": calculo["formula"],
                        "desde": e["desde"], "hasta": e["hasta"]})
    return {"id": periodo_id, "mensaje": "Período guardado.", "avisos": buscar_huecos(cur, e), "calculo": calculo}


# ---------- Recalcular ----------
def exigir_autorizacion(cur, usuario, motivo):
    """Corregir un período facturado requiere rol 'autorizador' y un motivo."""
    cur.execute("SELECT rol FROM usuarios WHERE nombre = %s", (usuario,))
    fila = cur.fetchone()
    if not fila or fila["rol"] != "autorizador":
        raise ApiError(MSG_FACTURADO + " Requiere un usuario autorizador y un motivo.", 403)
    if not motivo:
        raise ApiError("Indique el motivo de la corrección retroactiva.")


def recalcular(cur, datos):
    usuario = datos.get("usuario") or "sistema"
    motivo = (datos.get("motivo") or "").strip()

    cur.execute("SELECT * FROM periodos WHERE id = %s", (datos.get("periodo_id"),))
    periodo = cur.fetchone()
    if not periodo:
        raise ApiError("Período no encontrado.", 404)
    if periodo["facturado"]:
        exigir_autorizacion(cur, usuario, motivo)

    tarifa = tarifas.buscar_tarifa(cur, periodo["producto_codigo"], periodo["balance"], periodo["desde"])
    nuevo = tarifas.calcular_impuesto(tarifa, periodo["balance"])
    subtotal = redondear2(periodo["cantidad"] * nuevo["precio"])

    cur.execute(
        """UPDATE periodos SET precio=%s, subtotal=%s, tarifa_id=%s, tarifa_version=%s, tarifa_desde=%s,
           tarifa_hasta=%s, precio_base=%s, adicional=%s, porcentaje=%s, formula=%s, fecha_calculo=NOW(),
           modificado_por=%s, modificado_en=NOW() WHERE id=%s""",
        (nuevo["precio"], subtotal, nuevo["tarifa_id"], nuevo["tarifa_version"], nuevo["rango_desde"],
         nuevo["rango_hasta"], nuevo["precio_base"], nuevo["adicional"], nuevo["porcentaje"],
         nuevo["formula"], usuario, periodo["id"]),
    )
    accion = "RECALCULO_FACTURADO" if periodo["facturado"] else "RECALCULO"
    bitacora.registrar(cur, periodo["id"], usuario, accion,
                       {"precio_anterior": periodo["precio"], "precio_nuevo": nuevo["precio"],
                        "formula_anterior": periodo["formula"], "formula_nueva": nuevo["formula"],
                        "motivo": motivo})
    return {"mensaje": "Período recalculado.", "calculo": nuevo}


# ---------- Listado ----------
def listar(cur, datos):
    """Períodos de un cliente, con el impuesto vigente y el total referencial (solo administrativo)."""
    producto = datos.get("producto_codigo") or None
    cur.execute(
        """SELECT p.*, pr.nombre AS producto,
                  CASE WHEN CURDATE() >= p.desde AND CURDATE() < p.hasta THEN 'Vigente'
                       WHEN p.hasta <= CURDATE() THEN 'Histórico'
                       ELSE 'Futuro' END AS estado
           FROM periodos p JOIN productos pr ON pr.codigo = p.producto_codigo
           WHERE p.cliente_id = %s AND (%s IS NULL OR p.producto_codigo = %s)
           ORDER BY p.producto_codigo, p.desde""",
        (datos.get("cliente_id"), producto, producto),
    )
    filas = cur.fetchall()
    vigentes = [{"producto": f["producto"], "precio": redondear2(f["precio"])} for f in filas if f["estado"] == "Vigente"]
    return {"periodos": filas,
            "total_referencial": sum((f["precio"] for f in filas), 0),
            "impuesto_mensual_vigente": vigentes}
