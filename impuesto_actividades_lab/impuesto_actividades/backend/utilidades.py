"""Funciones pequeñas para decimales y fechas."""
import calendar
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from backend.errores import ApiError


def a_decimal(valor, campo="valor"):
    """Convierte texto a Decimal (nunca float, para no perder exactitud)."""
    try:
        numero = Decimal(str(valor).replace(",", "").strip())
    except Exception:
        raise ApiError(f"El campo {campo} no es un número válido.")
    if not numero.is_finite():
        raise ApiError(f"El campo {campo} no es un número válido.")
    return numero


def a_fecha(texto):
    """Convierte 'AAAA-MM-DD' a fecha."""
    try:
        return datetime.strptime(str(texto), "%Y-%m-%d").date()
    except ValueError:
        raise ApiError("Ingrese fechas válidas (AAAA-MM-DD).")


def redondear2(numero):
    return numero.quantize(Decimal("0.01"), ROUND_HALF_UP)


def redondear6(numero):
    return numero.quantize(Decimal("0.000001"), ROUND_HALF_UP)


def sumar_meses(fecha, cantidad):
    total = fecha.year * 12 + (fecha.month - 1) + cantidad
    anio, mes = divmod(total, 12)
    mes += 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def meses_entre(inicio, fin):
    """Meses del intervalo [inicio, fin). Si sobran días, se cuentan como fracción de mes."""
    meses = (fin.year - inicio.year) * 12 + (fin.month - inicio.month)
    if sumar_meses(inicio, meses) > fin:
        meses -= 1
    ancla = sumar_meses(inicio, meses)
    dias_sobrantes = (fin - ancla).days
    if dias_sobrantes == 0:
        return Decimal(meses)
    dias_del_mes = (sumar_meses(ancla, 1) - ancla).days
    return (Decimal(meses) + Decimal(dias_sobrantes) / Decimal(dias_del_mes)).quantize(Decimal("0.0001"))
