"""Utilidades compartidas para las conexiones SQLite."""

import sqlite3


def abrir_conexion(ruta: str) -> sqlite3.Connection:
    """Abre una conexión SQLite con filas accesibles por nombre de columna."""
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    return conexion
