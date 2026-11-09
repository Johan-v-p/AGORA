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
python scripts/crear_db.py
```

Ejecutar:

```powershell
python app.py
```

La aplicación estará disponible en `http://localhost:5000`.

## Estructura del código

```text
.
├── app.py                  # Punto de entrada
├── backend/
│   ├── aplicacion.py       # Crea la aplicación y registra los módulos
│   ├── nucleo/             # Configuración, base de datos y utilidades
│   ├── rutas/              # Un Blueprint por dominio y decoradores de acceso
│   ├── servicios/          # Reglas de negocio
│   └── modelos/            # Entidades
├── frontend/
│   ├── templates/          # HTML, una carpeta por dominio
│   │   ├── compartidos/    # Base y barra lateral
│   │   ├── autenticacion/
│   │   ├── publicaciones/
│   │   ├── social/
│   │   ├── foros/
│   │   ├── portafolio/
│   │   ├── eventos/
│   │   ├── mensajes/
│   │   ├── moderacion/
│   │   └── ajustes/
│   └── static/             # CSS y recursos públicos
├── scripts/                # Tareas operativas
└── tests/                  # Pruebas automáticas
```

`app.py` se mantiene como punto de entrada compatible para despliegues y
pruebas existentes. No se deben añadir componentes de aplicación en la raíz.

Las rutas se trasladarán progresivamente desde `backend/aplicacion.py` a módulos
dentro de `backend/rutas/`, la lógica de negocio se ubicará en
`backend/servicios/` y las entidades en `backend/modelos/`.

Las rutas nuevas deben implementarse como Blueprints y registrarse desde
`backend/aplicacion.py`. El primer Blueprint migrado es
`backend.rutas.autenticacion`. Las plantillas de cada Blueprint van en la carpeta
de `frontend/templates/` que corresponde a su dominio.

El código operativo de inicialización de la base de datos se encuentra en
`scripts/crear_db.py`.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas usan bases SQLite temporales y no modifican la base de datos de
desarrollo.

## Flujo de contribución

Este fork (`mihzuk/AGORA-modularizado`) es el repositorio principal de trabajo
para la modularización. Los cambios deben trabajarse en ramas y proponerse
mediante Pull Request hacia el `main` de este fork. El repositorio original
[`divis-smith/AGORA`](https://github.com/divis-smith/AGORA) solo será el destino
de una Pull Request cuando la modularización esté terminada y revisada.

Nombres recomendados:

- `feat/<descripcion>` para funcionalidades;
- `fix/<descripcion>` para correcciones;
- `refactor/<descripcion>` para modularización;
- `chore/<descripcion>` para mantenimiento.

Flujo:

```text
git fetch origin
git switch -c tipo/descripcion origin/main
git push -u origin tipo/descripcion
```

Para el trabajo diario, abre un Pull Request desde
`mihzuk/AGORA-modularizado:tipo/descripcion` hacia
`mihzuk/AGORA-modularizado:main`.

Antes de fusionar al fork, el Pull Request debe tener pruebas exitosas y al
menos una revisión de otro integrante. Cuando el proyecto esté completamente
modularizado, se preparará una Pull Request final hacia
`divis-smith/AGORA:main`.
