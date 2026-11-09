# AGORA

Aplicación web comunitaria construida con Flask, Flask-SocketIO y SQLite.

## Desarrollo local

Requisitos:

- Python 3.13 o superior
- Git

Crear un entorno virtual e instalar dependencias:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Configurar variables locales:

```powershell
Copy-Item .env.example .env
```

El archivo `.env` es únicamente una referencia de configuración; la aplicación lee
las variables que estén definidas en el entorno del proceso. Antes de ejecutar,
configura al menos `SECRET_KEY` y, opcionalmente, `DATABASE_PATH` y `FLASK_DEBUG`.

Inicializar la base de datos si es necesario:

```powershell
python crearr_db.py
```

Ejecutar:

```powershell
python app.py
```

La aplicación estará disponible en `http://localhost:5000`.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas usan bases SQLite temporales y no modifican la base de datos de
desarrollo.

## Flujo de contribución

Este repositorio es un fork de
[`divis-smith/AGORA`](https://github.com/divis-smith/AGORA). Los cambios deben
trabajarse en una rama y proponerse mediante Pull Request al repositorio
original, usando `main` como rama base.

Nombres recomendados:

- `feat/<descripcion>` para funcionalidades;
- `fix/<descripcion>` para correcciones;
- `refactor/<descripcion>` para modularización;
- `chore/<descripcion>` para mantenimiento.

Flujo:

```text
git fetch upstream
git switch -c tipo/descripcion upstream/main
git push -u origin tipo/descripcion
```

Después, abre un Pull Request desde
`mihzuk/AGORA-modularizado:tipo/descripcion` hacia
`divis-smith/AGORA:main`.

Antes de fusionar, el Pull Request debe tener pruebas exitosas y al menos una
revisión de otro integrante.
