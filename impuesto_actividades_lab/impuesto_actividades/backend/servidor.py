"""Servidor web con http.server (librería estándar): sirve la carpeta static/ y la API JSON."""
import json
import os
from datetime import date, datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pymysql

from backend.conexion import CONFIG, conectar
from backend.errores import ApiError
from backend.rutas import atender

HOST = "127.0.0.1"
PUERTO = 8000
CARPETA_STATIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

TIPOS = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8"}


def convertir(valor):
    """Decimal y fechas no son JSON: se envían como texto."""
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, datetime):
        return valor.isoformat(sep=" ")
    if isinstance(valor, date):
        return valor.isoformat()
    raise TypeError(f"No se puede convertir {type(valor)}")


class Manejador(BaseHTTPRequestHandler):

    def responder(self, codigo, contenido, tipo="application/json; charset=utf-8"):
        if not isinstance(contenido, bytes):
            contenido = json.dumps(contenido, default=convertir, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(contenido)))
        self.end_headers()
        self.wfile.write(contenido)

    def servir_archivo(self, ruta_url):
        nombre = "index.html" if ruta_url == "/" else ruta_url.lstrip("/")
        ruta = os.path.normpath(os.path.join(CARPETA_STATIC, nombre))
        if not ruta.startswith(CARPETA_STATIC) or not os.path.isfile(ruta):   # evita salir de static/
            return self.responder(404, {"error": "No encontrado"})
        with open(ruta, "rb") as f:
            tipo = TIPOS.get(os.path.splitext(ruta)[1], "application/octet-stream")
            self.responder(200, f.read(), tipo)

    def leer_datos(self, metodo, url):
        """Une los parámetros de la URL (?a=1) con el cuerpo JSON del POST."""
        datos = {clave: valores[0] for clave, valores in parse_qs(url.query).items()}
        if metodo == "POST":
            largo = int(self.headers.get("Content-Length") or 0)
            datos.update(json.loads(self.rfile.read(largo) or b"{}"))
        return datos

    def atender_api(self, metodo, url):
        conexion = None
        try:
            datos = self.leer_datos(metodo, url)
            conexion = conectar()
            with conexion.cursor() as cur:
                resultado = atender(metodo, url.path, datos, cur)
            conexion.commit()                      # todo se guarda junto (transacción)
            self.responder(200, resultado)
        except ApiError as error:
            if conexion:
                conexion.rollback()
            self.responder(error.codigo, {"error": error.mensaje, **error.extra})
        except pymysql.err.OperationalError as error:
            self.responder(500, {"error": f"No se pudo usar MariaDB (puerto {CONFIG['port']}): {error}. "
                                          "¿Está iniciado MySQL en XAMPP y creada la base?"})
        except Exception as error:
            if conexion:
                conexion.rollback()
            self.responder(500, {"error": f"Error interno: {error}"})
        finally:
            if conexion:
                conexion.close()

    def manejar(self, metodo):
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            self.atender_api(metodo, url)
        else:
            self.servir_archivo(url.path)

    def do_GET(self):
        self.manejar("GET")

    def do_POST(self):
        self.manejar("POST")

    def log_message(self, formato, *args):
        print(f"[{self.log_date_time_string()}] {formato % args}")


def iniciar():
    print(f"Abra http://{HOST}:{PUERTO}   (MariaDB {CONFIG['host']}:{CONFIG['port']}, base '{CONFIG['database']}')")
    ThreadingHTTPServer((HOST, PUERTO), Manejador).serve_forever()
