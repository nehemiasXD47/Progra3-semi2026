"""Conexión a MariaDB (XAMPP, puerto 3306).
Si cambia la contraseña de root o el nombre de la base, edítelo AQUÍ."""
import pymysql
import pymysql.cursors

CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",                      # XAMPP trae root sin contraseña
    "database": "impuesto_actividades",
    "charset": "utf8mb4",
}


def conectar():
    """Abre una conexión nueva. Los resultados se devuelven como diccionarios."""
    return pymysql.connect(**CONFIG, cursorclass=pymysql.cursors.DictCursor, autocommit=False)
