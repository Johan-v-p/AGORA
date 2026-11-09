"""
crear_db.py — Crea la base de datos de ÁGORA con datos de demostración.
Ejecutar desde la raíz del proyecto: python scripts/crear_db.py
La base se crea en data/agora.db, o en la ruta indicada por DATABASE_PATH.

La estructura está en esquema.sql y el contenido de ejemplo en datos_demo.py.
"""

import os
import sqlite3
from pathlib import Path

from datos_demo import insertar_datos_demo

CARPETA_SCRIPTS = Path(__file__).resolve().parent
RUTA_POR_DEFECTO = CARPETA_SCRIPTS.parent / 'data' / 'agora.db'
DB = Path(os.environ.get('DATABASE_PATH', RUTA_POR_DEFECTO))
DB.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB)
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript((CARPETA_SCRIPTS / 'esquema.sql').read_text(encoding='utf-8'))
conn.commit()
print("✅ Tablas creadas correctamente.")

insertar_datos_demo(conn)
conn.close()

print()
print(f"✅  Base de datos '{DB}' creada con éxito.")
print()
print("   Cuentas de prueba:")
print("   ┌─────────────────────────────────────────────────────┐")
print("   │  admin@agora.edu          /  admin123   (admin)     │")
print("   │  vale@correounivalle.edu  /  vale123    (estudiante)│")
print("   │  divis@correounivalle.edu /  divis123   (estudiante)│")
print("   │  cris@correounivalle.edu  /  cris123    (estudiante)│")
print("   │  mod@agora.edu            /  mod123     (moderador) │")
print("   └─────────────────────────────────────────────────────┘")
