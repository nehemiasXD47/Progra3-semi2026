"""Tabla tarifaria: buscar la tarifa, calcular el impuesto y administrar tarifas."""
from decimal import Decimal, ROUND_CEILING

from backend.errores import ApiError
from backend.utilidades import a_decimal, a_fecha, redondear2, redondear6

FORMULA_ACTUAL = "BLOQUES_CEIL_V2"   # fórmula de los períodos nuevos


def buscar_tarifa(cur, producto, balance, fecha):
    """Devuelve LA tarifa que contiene el balance (Desde <= Balance <= Hasta) para esa fecha."""
    cur.execute(
        """SELECT * FROM tarifas
           WHERE producto_codigo = %s AND activa = 1
             AND vigente_desde <= %s AND (vigente_hasta IS NULL OR vigente_hasta > %s)
             AND desde <= %s AND %s <= hasta""",
        (producto, fecha, fecha, balance, balance),
    )
    encontradas = cur.fetchall()

    if len(encontradas) == 0:   # nunca se usa el precio general del producto
        raise ApiError("No existe una tarifa configurada para el balance indicado.")
    if len(encontradas) > 1:
        raise ApiError("Existe más de una tarifa aplicable. Corrija la tabla tarifaria.")
    return encontradas[0]


def calcular_impuesto(tarifa, balance):
    """Aplica la fórmula del documento y devuelve todo el detalle del cálculo."""
    excedente = None
    bloques = None

    if tarifa["porcentaje"] > 0:
        # Tarifa porcentual: Balance x Porcentaje / 100
        precio = balance * tarifa["porcentaje"] / 100
    else:
        # Tarifa por bloques: Precio base + (Bloques x Adicional)
        excedente = balance - tarifa["desde"]
        bloques = (excedente / Decimal(1000)).to_integral_value(rounding=ROUND_CEILING)
        precio = tarifa["precio_base"] + bloques * tarifa["adicional"]

    return {
        "balance": balance,
        "tarifa_id": tarifa["id"],
        "tarifa_version": tarifa["version"],
        "rango_desde": tarifa["desde"],
        "rango_hasta": tarifa["hasta"],
        "precio_base": tarifa["precio_base"],
        "adicional": tarifa["adicional"],
        "porcentaje": tarifa["porcentaje"],
        "excedente": excedente,
        "bloques": bloques,
        "precio": redondear6(precio),            # 6 decimales internos
        "precio_mostrado": redondear2(precio),   # 2 decimales al mostrar/cobrar
        "formula": FORMULA_ACTUAL,
    }


def listar(cur, datos):
    """Tarifas de un producto + rangos de balance que no tienen tarifa (huecos)."""
    cur.execute(
        "SELECT * FROM tarifas WHERE producto_codigo = %s AND activa = 1 ORDER BY vigente_desde, desde",
        (datos.get("producto_codigo"),),
    )
    tarifas = cur.fetchall()

    huecos = []
    for actual, siguiente in zip(tarifas, tarifas[1:]):
        misma_version = actual["vigente_desde"] == siguiente["vigente_desde"]
        if misma_version and siguiente["desde"] - actual["hasta"] > Decimal("0.01"):
            huecos.append({"desde": actual["hasta"] + Decimal("0.01"),
                           "hasta": siguiente["desde"] - Decimal("0.01")})
    return {"tarifas": tarifas, "huecos": huecos}


def crear(cur, datos):
    """Agrega una tarifa. Si reemplaza el mismo rango, cierra la versión anterior."""
    producto = datos.get("producto_codigo")
    desde = a_decimal(datos.get("desde"), "desde")
    hasta = a_decimal(datos.get("hasta"), "hasta")
    precio_base = a_decimal(datos.get("precio_base") or 0, "precio base")
    adicional = a_decimal(datos.get("adicional") or 0, "adicional")
    porcentaje = a_decimal(datos.get("porcentaje") or 0, "porcentaje")
    vigente_desde = a_fecha(datos.get("vigente_desde"))

    if desde <= 0 or desde > hasta:
        raise ApiError("El rango de la tarifa no es válido.")

    # Tarifas vigentes que se cruzan con el rango nuevo
    cur.execute(
        """SELECT * FROM tarifas
           WHERE producto_codigo = %s AND activa = 1 AND desde <= %s AND hasta >= %s
             AND COALESCE(vigente_hasta, '9999-12-31') > %s""",
        (producto, hasta, desde, vigente_desde),
    )
    cruzadas = cur.fetchall()

    for t in cruzadas:
        es_nueva_version = t["desde"] == desde and t["hasta"] == hasta and t["vigente_desde"] < vigente_desde
        if not es_nueva_version:
            raise ApiError("El rango se superpone con una tarifa vigente del mismo producto.")

    for t in cruzadas:   # cerrar la versión anterior (los períodos viejos conservan su copia)
        cur.execute("UPDATE tarifas SET vigente_hasta = %s WHERE id = %s", (vigente_desde, t["id"]))

    cur.execute("SELECT COALESCE(MAX(version), 0) + 1 AS v FROM tarifas WHERE producto_codigo = %s", (producto,))
    version = cur.fetchone()["v"]

    cur.execute(
        """INSERT INTO tarifas (producto_codigo, version, desde, hasta, precio_base, adicional, porcentaje, vigente_desde)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (producto, version, desde, hasta, precio_base, adicional, porcentaje, vigente_desde),
    )
    return {"mensaje": "Tarifa agregada. Los períodos y recibos existentes no se modifican."}
