"""Registro de auditoría: quién hizo qué y cuándo."""
import json


def registrar(cur, periodo_id, usuario, accion, detalle):
    cur.execute(
        "INSERT INTO bitacora (periodo_id, usuario, accion, detalle) VALUES (%s, %s, %s, %s)",
        (periodo_id, usuario, accion, json.dumps(detalle, default=str, ensure_ascii=False)),
    )


def listar(cur, datos):
    cur.execute("SELECT * FROM bitacora ORDER BY id DESC LIMIT 100")
    return {"filas": cur.fetchall()}
