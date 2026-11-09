"""Transformaciones de datos compartidas por las rutas."""

import json
from datetime import datetime


_MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
             'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def tiempo_relativo(fecha_str):
    """Convierte una fecha ISO a texto relativo legible."""
    try:
        fecha = datetime.strptime(str(fecha_str), '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return ''
    delta = datetime.now() - fecha
    segundos = int(delta.total_seconds())
    if segundos < 60:
        return 'ahora mismo'
    if segundos < 3600:
        return f'hace {segundos // 60}min'
    if segundos < 86400:
        return f'hace {segundos // 3600}h'
    return f'hace {delta.days} días'


def parsear_tecnologias(texto):
    """Convierte JSON o CSV de tecnologías en una lista."""
    if not texto:
        return []
    texto = texto.strip()
    if texto.startswith('['):
        try:
            return json.loads(texto)
        except (json.JSONDecodeError, TypeError):
            pass
    return [tecnologia.strip() for tecnologia in texto.split(',')
            if tecnologia.strip()]


def procesar_evento(row):
    """Añade campos calculados a un evento."""
    evento = dict(row)
    try:
        fecha = datetime.strptime(str(evento['fecha']), '%Y-%m-%d')
        evento['fecha_dia'] = fecha.day
        evento['fecha_mes'] = _MESES_ES[fecha.month - 1].upper()
    except (KeyError, TypeError, ValueError):
        evento['fecha_dia'] = '--'
        evento['fecha_mes'] = '---'
    evento['inscrito'] = bool(evento.get('inscrito'))
    evento['cupos_libres'] = evento.get('cupos_libres') or '∞'
    return evento


def con_tiempo_relativo(filas):
    """Convierte filas en diccionarios con el campo tiempo_relativo calculado."""
    resultado = []
    for fila in filas:
        item = dict(fila)
        item['tiempo_relativo'] = tiempo_relativo(item['creado_en'])
        resultado.append(item)
    return resultado
