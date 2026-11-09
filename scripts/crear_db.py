"""
crear_db.py — Crea TODA la base de datos de ÁGORA desde cero.
Ejecutar UNA sola vez: python crear_db.py

Tablas:
  usuarios, seguidores, publicaciones, reacciones_publicacion,
  comentarios, reacciones_comentario, foros, preguntas_foro,
  respuestas_foro, votos_respuesta, proyectos, tecnologias_proyecto,
  aplausos_proyecto, comentarios_proyecto, eventos, inscripciones_evento,
  mensajes, conversaciones, participantes_conversacion,
  notificaciones, reportes, guardados
"""

import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

DB = 'agora.db'

conn = sqlite3.connect(DB)
c    = conn.cursor()

# Activar claves foráneas
c.execute("PRAGMA foreign_keys = ON")

# ══════════════════════════════════════════════════════════
# 1. USUARIOS
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT    NOT NULL,
    correo       TEXT    NOT NULL UNIQUE,
    password     TEXT    NOT NULL,
    carrera      TEXT,
    universidad  TEXT,
    semestre     INTEGER,
    bio          TEXT,
    avatar_url   TEXT,
    rol          TEXT    NOT NULL DEFAULT 'estudiante',
                         -- 'estudiante' | 'moderador' | 'admin'
    verificado   INTEGER NOT NULL DEFAULT 0,   -- 1 = verificado
    activo       INTEGER NOT NULL DEFAULT 1,   -- 0 = suspendido/baneado
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# ══════════════════════════════════════════════════════════
# 2. SEGUIDORES  (quién sigue a quién)
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS seguidores (
    seguidor_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    seguido_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (seguidor_id, seguido_id)
)
""")

# ══════════════════════════════════════════════════════════
# 3. PUBLICACIONES (feed)
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS publicaciones (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    autor_id     INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo       TEXT    NOT NULL,
    contenido    TEXT    NOT NULL,
    categoria    TEXT    NOT NULL DEFAULT 'general',
                         -- 'academico' | 'meme' | 'foro' | 'portafolio' | 'general'
    hashtags     TEXT,   -- guardados como JSON: ["#ia","#python"]
    imagen_url   TEXT,
    visibilidad  TEXT    NOT NULL DEFAULT 'todos',
                         -- 'todos' | 'seguidores' | 'carrera'
    estado       TEXT    NOT NULL DEFAULT 'publicado',
                         -- 'publicado' | 'borrador' | 'eliminado' | 'pendiente'
    es_anonimo   INTEGER NOT NULL DEFAULT 0,
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP,
    editado_en   DATETIME
)
""")

# ══════════════════════════════════════════════════════════
# 4. REACCIONES A PUBLICACIONES
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS reacciones_publicacion (
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    publicacion_id  INTEGER NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    tipo            TEXT    NOT NULL DEFAULT 'aplauso',
                            -- 'aplauso' | 'craneo' | 'manos' | 'estrella'
    creado_en       DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, publicacion_id)
)
""")

# ══════════════════════════════════════════════════════════
# 5. COMENTARIOS DE PUBLICACIONES
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS comentarios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    publicacion_id  INTEGER NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    autor_id        INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    contenido       TEXT    NOT NULL,
    padre_id        INTEGER REFERENCES comentarios(id) ON DELETE CASCADE,
                    -- NULL = comentario raíz; valor = respuesta a otro comentario
    creado_en       DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# ══════════════════════════════════════════════════════════
# 6. REACCIONES A COMENTARIOS (like)
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS reacciones_comentario (
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    comentario_id INTEGER NOT NULL REFERENCES comentarios(id) ON DELETE CASCADE,
    creado_en     DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, comentario_id)
)
""")

# ══════════════════════════════════════════════════════════
# 7. FOROS
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS foros (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT    NOT NULL UNIQUE,
    descripcion  TEXT,
    categoria    TEXT,   -- 'matematicas' | 'sistemas' | 'campus' | etc.
    creado_por   INTEGER REFERENCES usuarios(id),
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# ══════════════════════════════════════════════════════════
# 8. PREGUNTAS DE FORO
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS preguntas_foro (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    foro_id      INTEGER NOT NULL REFERENCES foros(id) ON DELETE CASCADE,
    autor_id     INTEGER REFERENCES usuarios(id),  -- NULL = anónimo
    tipo         TEXT    NOT NULL DEFAULT 'pregunta',
                         -- 'pregunta' | 'apuntes' | 'duda' | 'recurso' | 'debate'
    titulo       TEXT    NOT NULL,
    contenido    TEXT,
    es_anonimo   INTEGER NOT NULL DEFAULT 0,
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# ══════════════════════════════════════════════════════════
# 9. RESPUESTAS DE FORO
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS respuestas_foro (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta_id  INTEGER NOT NULL REFERENCES preguntas_foro(id) ON DELETE CASCADE,
    autor_id     INTEGER REFERENCES usuarios(id),
    contenido    TEXT    NOT NULL,
    es_anonimo   INTEGER NOT NULL DEFAULT 0,
    aceptada     INTEGER NOT NULL DEFAULT 0,  -- 1 = respuesta marcada como correcta
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# ══════════════════════════════════════════════════════════
# 10. VOTOS A RESPUESTAS DE FORO
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS votos_respuesta (
    usuario_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    respuesta_id INTEGER NOT NULL REFERENCES respuestas_foro(id) ON DELETE CASCADE,
    valor        INTEGER NOT NULL DEFAULT 1,   -- 1 = upvote, -1 = downvote
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, respuesta_id)
)
""")

# ══════════════════════════════════════════════════════════
# 11. PROYECTOS (portafolio)
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS proyectos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    autor_id     INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo       TEXT    NOT NULL,
    descripcion  TEXT,
    tecnologias  TEXT,   -- JSON: ["Python","Flask","MySQL"]
    materia      TEXT,   -- Ej: "Bases de Datos I · 2025"
    estado       TEXT    NOT NULL DEFAULT 'en_desarrollo',
                         -- 'en_desarrollo' | 'completado' | 'pausado'
    fecha_inicio DATE,
    fecha_fin    DATE,
    imagen_url   TEXT,
    repo_url     TEXT,
    demo_url     TEXT,
    destacado    INTEGER NOT NULL DEFAULT 0,   -- 1 = destacado en perfil
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# ══════════════════════════════════════════════════════════
# 12. APLAUSOS A PROYECTOS
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS aplausos_proyecto (
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    proyecto_id INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    creado_en   DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, proyecto_id)
)
""")

# ══════════════════════════════════════════════════════════
# 13. COMENTARIOS DE PROYECTOS
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS comentarios_proyecto (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    proyecto_id INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    autor_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    contenido   TEXT    NOT NULL,
    creado_en   DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# ══════════════════════════════════════════════════════════
# 14. EVENTOS
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS eventos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    creador_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo       TEXT    NOT NULL,
    descripcion  TEXT,
    categoria    TEXT    NOT NULL DEFAULT 'academico',
                         -- 'academico' | 'cultural' | 'deportivo' | 'bienestar'
    fecha        DATE    NOT NULL,
    hora_inicio  TIME,
    hora_fin     TIME,
    lugar        TEXT,
    cupos        INTEGER,   -- NULL = sin límite
    organizador  TEXT,      -- Nombre del semillero/grupo organizador
    agenda       TEXT,      -- JSON: [{"hora":"09:00","item":"Apertura"}]
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# ══════════════════════════════════════════════════════════
# 15. INSCRIPCIONES A EVENTOS
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS inscripciones_evento (
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    evento_id   INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    creado_en   DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, evento_id)
)
""")

# ══════════════════════════════════════════════════════════
# 16. CONVERSACIONES DE MENSAJERÍA
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS conversaciones (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP,
    ultimo_msg   DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS participantes_conversacion (
    conversacion_id  INTEGER NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
    usuario_id       INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    archivada        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (conversacion_id, usuario_id)
)
""")

# ══════════════════════════════════════════════════════════
# 17. MENSAJES
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS mensajes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    conversacion_id  INTEGER NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
    autor_id         INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    contenido        TEXT    NOT NULL,
    leido            INTEGER NOT NULL DEFAULT 0,
    creado_en        DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# ══════════════════════════════════════════════════════════
# 18. NOTIFICACIONES
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS notificaciones (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo         TEXT    NOT NULL,
                         -- 'like' | 'comentario' | 'seguidor' | 'mencion'
                         -- 'foro' | 'proyecto' | 'evento' | 'reporte'
    mensaje      TEXT    NOT NULL,
    leida        INTEGER NOT NULL DEFAULT 0,
    url          TEXT,   -- ruta a la que lleva la notificación
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# ══════════════════════════════════════════════════════════
# 19. REPORTES
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS reportes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reportado_por   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo            TEXT    NOT NULL,
                            -- 'publicacion' | 'comentario' | 'usuario'
    referencia_id   INTEGER NOT NULL,   -- id de la publicación/comentario/usuario
    motivo          TEXT    NOT NULL,
    descripcion     TEXT,
    estado          TEXT    NOT NULL DEFAULT 'enviado',
                            -- 'enviado' | 'en_revision' | 'resuelto' | 'descartado'
    revisado_por    INTEGER REFERENCES usuarios(id),
    resolucion      TEXT,
    creado_en       DATETIME DEFAULT CURRENT_TIMESTAMP,
    resuelto_en     DATETIME
)
""")

# ══════════════════════════════════════════════════════════
# 20. GUARDADOS (bookmarks)
# ══════════════════════════════════════════════════════════
c.execute("""
CREATE TABLE IF NOT EXISTS guardados (
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    publicacion_id  INTEGER NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    creado_en       DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, publicacion_id)
)
""")

conn.commit()
print("✅ Tablas creadas correctamente.")

# ══════════════════════════════════════════════════════════
# DATOS DE EJEMPLO
# ══════════════════════════════════════════════════════════

now = datetime.now()

# ── Usuarios ───────────────────────────────────────────────
usuarios_seed = [
    ('Admin',          'admin@agora.edu',       'admin123',    'Administración',        'Universidad del Valle', 8,  'Administrador de Ágora.',        'admin',       1),
    ('Valentina M.',   'vale@correounivalle.edu','vale123',     'Ing. de Sistemas',      'Universidad del Valle', 6,  'Backend · café · memes 💻',      'estudiante',  1),
    ('Divis Smith R.', 'divis@correounivalle.edu','divis123',   'Ing. de Sistemas',      'Universidad del Valle', 7,  'Fullstack y jugador de ajedrez.', 'estudiante',  0),
    ('Cristian F. A.', 'cris@correounivalle.edu', 'cris123',   'Ing. de Sistemas',      'Universidad del Valle', 7,  'Python & Data Science.',         'estudiante',  0),
    ('María G.',       'maria@correounivalle.edu','maria123',   'Ing. de Sistemas',      'Universidad del Valle', 5,  'Frontend · diseño UX.',          'estudiante',  0),
    ('Carlos Mendoza', 'carlos@correounivalle.edu','carlos123', 'Administración',         'Universidad del Valle', 4,  'Gestor y emprendedor.',          'estudiante',  0),
    ('Laura Quintero', 'laura@correounivalle.edu','laura123',   'Psicología',            'Universidad del Valle', 3,  'Bienestar estudiantil.',         'estudiante',  0),
    ('Andrés Castaño', 'andres@correounivalle.edu','andres123', 'Ing. Electrónica',      'Universidad del Valle', 6,  'Robótica y maker.',              'estudiante',  0),
    ('Sofía Ramírez',  'sofia@correounivalle.edu', 'sofia123',  'Comunicación Social',   'Universidad del Valle', 2,  'Periodismo y redes.',            'estudiante',  0),
    ('Moderador',      'mod@agora.edu',          'mod123',     'Administración',         'Universidad del Valle', None, 'Mantiene el orden en Ágora.',  'moderador',   0),
]

user_ids = {}
for (nombre, correo, pwd, carrera, uni, sem, bio, rol, verif) in usuarios_seed:
    c.execute("""
        INSERT OR IGNORE INTO usuarios (nombre, correo, password, carrera, universidad, semestre, bio, rol, verificado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (nombre, correo, generate_password_hash(pwd), carrera, uni, sem, bio, rol, verif))
    c.execute("SELECT id FROM usuarios WHERE correo = ?", (correo,))
    user_ids[correo] = c.fetchone()[0]

conn.commit()
print("  → Usuarios insertados.")

# Atajos
U_ADMIN  = user_ids['admin@agora.edu']
U_VALE   = user_ids['vale@correounivalle.edu']
U_DIVIS  = user_ids['divis@correounivalle.edu']
U_CRIS   = user_ids['cris@correounivalle.edu']
U_MARIA  = user_ids['maria@correounivalle.edu']
U_CARLOS = user_ids['carlos@correounivalle.edu']
U_LAURA  = user_ids['laura@correounivalle.edu']
U_ANDRES = user_ids['andres@correounivalle.edu']
U_SOFIA  = user_ids['sofia@correounivalle.edu']
U_MOD    = user_ids['mod@agora.edu']

# ── Seguidores ──────────────────────────────────────────────
follows = [
    (U_VALE, U_DIVIS), (U_VALE, U_CRIS), (U_VALE, U_MARIA),
    (U_DIVIS, U_VALE), (U_DIVIS, U_CRIS),
    (U_CRIS, U_VALE),  (U_CRIS, U_MARIA),
    (U_MARIA, U_VALE), (U_CARLOS, U_VALE), (U_LAURA, U_VALE),
    (U_ANDRES, U_VALE),(U_SOFIA, U_VALE),
]
for (a, b) in follows:
    c.execute("INSERT OR IGNORE INTO seguidores (seguidor_id, seguido_id) VALUES (?,?)", (a, b))

# ── Publicaciones ───────────────────────────────────────────
pubs = [
    (U_VALE,  'Sistema de gestión hospitalaria con microservicios Flask',
              'Desarrollamos una arquitectura basada en microservicios con Flask y Docker. Cada módulo (pacientes, citas, facturación) corre de forma independiente. ¿Preguntas?',
              'academico', None, now - timedelta(hours=2)),
    (U_DIVIS, 'el profe: esto NO entra al parcial — el parcial:',
              'Y ahí estaba. Todo el capítulo 4 completo 💀',
              'meme',      None, now - timedelta(minutes=45)),
    (None,    '¿Alguien tiene apuntes del martes con Ramírez?',
              'Me perdí la clase del martes de Cálculo III con el profesor Ramírez. ¿Alguien los tiene escaneados o en PDF? 🙏',
              'foro',      None, now - timedelta(hours=1)),
    (U_MARIA, 'API REST para sistema de matrículas universitarias',
              'Mi proyecto de Bases de Datos I ya está en GitHub. Construido con Node.js + Express + PostgreSQL. Abierto a feedback.',
              'portafolio',None, now - timedelta(hours=3)),
    (U_CRIS,  '¿Vale la pena aprender Rust en 2026?',
              'Llevo un mes con Rust y la verdad es que el borrow checker me tiene loco. Pero la performance es increíble. ¿Alguien más lo está aprendiendo?',
              'academico', None, now - timedelta(hours=5)),
    (U_ANDRES,'Sensor de temperatura con Arduino y Flask',
              'Mini proyecto: un sensor DHT22 conectado a un Arduino que envía datos a una API Flask y los grafica en tiempo real. Tutorial completo próximamente.',
              'portafolio',None, now - timedelta(days=1)),
    (U_LAURA, 'Charla de bienestar mental mañana a las 11am 📅',
              'El departamento de bienestar universitario organiza una charla sobre manejo del estrés en época de parciales. ¡Anímate!',
              'general',   None, now - timedelta(hours=8)),
    (U_SOFIA, 'Tips para hacer buenas presentaciones orales',
              'Aquí van mis 5 tips para no morir en las sustentaciones: 1) Practica en voz alta 2) Conoce tu intro de memoria 3) Mira a los ojos 4) Habla despacio 5) Respira.',
              'academico', None, now - timedelta(days=2)),
]

pub_ids = []
for (autor, titulo, contenido, cat, img, fecha) in pubs:
    anonimo = 1 if autor is None else 0
    autor_real = U_VALE if autor is None else autor
    c.execute("""
        INSERT INTO publicaciones (autor_id, titulo, contenido, categoria, imagen_url, es_anonimo, creado_en)
        VALUES (?,?,?,?,?,?,?)
    """, (autor_real, titulo, contenido, cat, img, anonimo, fecha.strftime('%Y-%m-%d %H:%M:%S')))
    pub_ids.append(c.lastrowid)

# ── Reacciones a publicaciones ──────────────────────────────
reacciones_data = [
    (U_DIVIS,  pub_ids[0], 'aplauso'), (U_CRIS,   pub_ids[0], 'aplauso'),
    (U_MARIA,  pub_ids[0], 'aplauso'), (U_CARLOS, pub_ids[0], 'aplauso'),
    (U_VALE,   pub_ids[1], 'craneo'),  (U_CRIS,   pub_ids[1], 'craneo'),
    (U_MARIA,  pub_ids[1], 'craneo'),  (U_ANDRES, pub_ids[1], 'craneo'),
    (U_VALE,   pub_ids[2], 'manos'),   (U_CRIS,   pub_ids[3], 'estrella'),
    (U_VALE,   pub_ids[3], 'estrella'),(U_DIVIS,  pub_ids[3], 'estrella'),
]
for (uid, pid, tipo) in reacciones_data:
    c.execute("INSERT OR IGNORE INTO reacciones_publicacion (usuario_id, publicacion_id, tipo) VALUES (?,?,?)", (uid, pid, tipo))

# ── Comentarios ─────────────────────────────────────────────
comentarios_data = [
    (pub_ids[0], U_DIVIS,  '¿Usaron JWT para la autenticación? Me parece genial la arquitectura 🔥'),
    (pub_ids[0], U_CRIS,   'Buenísimo. ¿Comparten el repo?'),
    (pub_ids[0], U_MARIA,  '¿Dónde puedo ver el código?'),
    (pub_ids[1], U_VALE,   'Clásico 💀 eso nunca falla'),
    (pub_ids[1], U_CRIS,   'Igual nos pasó en Cálculo III'),
    (pub_ids[3], U_VALE,   '¡Excelente proyecto! ¿Está desplegado en algún lado?'),
    (pub_ids[3], U_DIVIS,  'Muy limpio el código, buen trabajo 👏'),
]
com_ids = []
for (pid, uid, texto) in comentarios_data:
    c.execute("INSERT INTO comentarios (publicacion_id, autor_id, contenido) VALUES (?,?,?)", (pid, uid, texto))
    com_ids.append(c.lastrowid)

conn.commit()
print("  → Publicaciones, reacciones y comentarios insertados.")

# ── Foros ────────────────────────────────────────────────────
foros_data = [
    ('Memes de Sistemas',    'El humor de los ingenieros de sistemas de Univalle.',        'campus'),
    ('Cálculo III',          'Preguntas, dudas y recursos de Cálculo Diferencial III.',    'matematicas'),
    ('Estructura de Datos',  'Algoritmos, árboles, grafos y todo lo demás.',               'sistemas'),
    ('Vida Universitaria',   'Tips, experiencias y todo lo que pasa en el campus.',        'campus'),
    ('Parciales',            'Banco de parciales, apuntes y recursos de estudio.',         'academico'),
]
foro_ids = []
for (nombre, desc, cat) in foros_data:
    c.execute("INSERT OR IGNORE INTO foros (nombre, descripcion, categoria, creado_por) VALUES (?,?,?,?)",
              (nombre, desc, cat, U_ADMIN))
    c.execute("SELECT id FROM foros WHERE nombre = ?", (nombre,))
    foro_ids.append(c.fetchone()[0])

# ── Preguntas de foro ────────────────────────────────────────
preguntas_data = [
    (foro_ids[1], None,    'pregunta', '¿Alguien tiene apuntes del martes con Ramírez?', 1),
    (foro_ids[1], U_MARIA, 'apuntes',  'Notas completas del segundo corte – Cálculo III', 0),
    (foro_ids[1], U_CRIS,  'duda',     'No entiendo la demostración del teorema de Green', 0),
    (foro_ids[1], U_VALE,  'recurso',  'Playlist YT que me salvó el semestre', 0),
    (foro_ids[1], None,    'debate',   '¿Vale la pena estudiar con grupo o solo?', 1),
    (foro_ids[2], U_DIVIS, 'pregunta', '¿Cuál es la diferencia real entre un árbol AVL y un árbol rojo-negro?', 0),
    (foro_ids[3], U_SOFIA, 'recurso',  'Guía de becas y financiación para estudiantes 2026', 0),
]
preg_ids = []
for (fid, uid, tipo, titulo, anon) in preguntas_data:
    autor = U_VALE if uid is None else uid
    c.execute("INSERT INTO preguntas_foro (foro_id, autor_id, tipo, titulo, es_anonimo) VALUES (?,?,?,?,?)",
              (fid, autor, tipo, titulo, anon))
    preg_ids.append(c.lastrowid)

# ── Respuestas de foro ───────────────────────────────────────
for (pid, uid, texto) in [
    (preg_ids[0], U_VALE,  'Yo tengo los apuntes escaneados, te los mando por chat.'),
    (preg_ids[0], U_CRIS,  'Yo también los tengo, son bastante completos.'),
    (preg_ids[2], U_DIVIS, 'El teorema de Green relaciona una integral de línea con una integral doble. La clave está en orientar correctamente la curva.'),
]:
    c.execute("INSERT INTO respuestas_foro (pregunta_id, autor_id, contenido) VALUES (?,?,?)", (pid, uid, texto))

conn.commit()
print("  → Foros, preguntas y respuestas insertados.")

# ── Proyectos ────────────────────────────────────────────────
proyectos_data = [
    (U_VALE,  'Ágora — Red Social Universitaria',            '["Flask","MySQL","Python","Jinja2"]', 'Proyecto universitario · 2026', 'en_desarrollo', 1),
    (U_VALE,  'Analizador de sentimientos académicos',        '["Python","NLP","scikit-learn"]',    'Curso ML · 2025',              'completado',    0),
    (U_VALE,  'Sistema de matrícula universitaria',           '["Java","BD","Swing"]',              'Bases de datos I · 2025',      'completado',    0),
    (U_VALE,  'Dashboard de métricas estudiantiles',          '["React","Node.js","Chart.js"]',     'Desarrollo Web · 2024',        'completado',    0),
    (U_ANDRES,'Sensor temperatura laboratorio',               '["C++","Arduino","Flask"]',          'Electrónica · 2024',           'completado',    0),
    (U_MARIA, 'API REST gestión de horarios',                 '["Django","REST","PostgreSQL"]',     'Proyecto integrador · 2024',   'completado',    0),
]
proy_ids = []
for (uid, titulo, tech, materia, estado, dest) in proyectos_data:
    c.execute("""
        INSERT INTO proyectos (autor_id, titulo, tecnologias, materia, estado, destacado)
        VALUES (?,?,?,?,?,?)
    """, (uid, titulo, tech, materia, estado, dest))
    proy_ids.append(c.lastrowid)

# ── Aplausos a proyectos ─────────────────────────────────────
for (uid, pid) in [(U_DIVIS, proy_ids[0]), (U_CRIS, proy_ids[0]),
                   (U_MARIA, proy_ids[0]), (U_CARLOS, proy_ids[0]),
                   (U_VALE,  proy_ids[4]), (U_CRIS,  proy_ids[5])]:
    c.execute("INSERT OR IGNORE INTO aplausos_proyecto (usuario_id, proyecto_id) VALUES (?,?)", (uid, pid))

# ── Eventos ──────────────────────────────────────────────────
eventos_data = [
    (U_VALE,  'Hackathon Univalle 2026 — retos de IA',  'academico',  '2026-06-15', '09:00', '18:00', 'Auditorio Paraninfo', 200, 'Semillero SIRIUS',
     '[{"hora":"09:00","item":"Apertura y registro"},{"hora":"10:00","item":"Inicio del hackathon"},{"hora":"13:00","item":"Almuerzo y networking"},{"hora":"17:00","item":"Presentación de proyectos"},{"hora":"18:00","item":"Premiación y cierre"}]'),
    (U_DIVIS, 'Feria de Semilleros — exposición de proyectos', 'cultural', '2026-06-20', '14:00', '18:00', 'Sala Múltiple B', 150, 'Vicerrectoría Académica', None),
    (U_ANDRES,'Torneo Intercambio de Robótica',          'deportivo',  '2026-06-25', '08:00', '17:00', 'Lab. Mecatrónica',   80,  'Club de Robótica', None),
    (U_LAURA, 'Charla: salud mental en la universidad',  'bienestar',  '2026-06-28', '11:00', '13:00', 'Auditorio Sur',      120, 'Bienestar Universitario', None),
]
ev_ids = []
for (cid, titulo, cat, fecha, hi, hf, lugar, cupos, org, agenda) in eventos_data:
    c.execute("""
        INSERT INTO eventos (creador_id, titulo, categoria, fecha, hora_inicio, hora_fin, lugar, cupos, organizador, agenda)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (cid, titulo, cat, fecha, hi, hf, lugar, cupos, org, agenda))
    ev_ids.append(c.lastrowid)

# ── Inscripciones ────────────────────────────────────────────
for (uid, eid) in [(U_DIVIS, ev_ids[0]), (U_CRIS, ev_ids[0]), (U_MARIA, ev_ids[0]),
                   (U_CARLOS, ev_ids[1]), (U_VALE, ev_ids[1]),
                   (U_ANDRES, ev_ids[2]),
                   (U_LAURA, ev_ids[3]),  (U_SOFIA, ev_ids[3])]:
    c.execute("INSERT OR IGNORE INTO inscripciones_evento (usuario_id, evento_id) VALUES (?,?)", (uid, eid))

conn.commit()
print("  → Proyectos y eventos insertados.")

# ── Conversaciones y mensajes ────────────────────────────────
c.execute("INSERT INTO conversaciones DEFAULT VALUES")
conv1 = c.lastrowid
c.execute("INSERT INTO participantes_conversacion VALUES (?,?,0)", (conv1, U_VALE))
c.execute("INSERT INTO participantes_conversacion VALUES (?,?,0)", (conv1, U_CARLOS))
msgs = [
    (conv1, U_CARLOS, 'Hola Valentina! ¿Pudiste ver mi portafolio?'),
    (conv1, U_VALE,   'Sí! Está muy bien estructurado. 👏'),
    (conv1, U_CARLOS, '¿Puedes revisar mi portafolio antes del lunes?'),
    (conv1, U_VALE,   'Claro, te doy retroalimentación hoy en la tarde.'),
    (conv1, U_CARLOS, '¡Genial! Muchas gracias Valentina 😊'),
]
for (cid, uid, txt) in msgs:
    c.execute("INSERT INTO mensajes (conversacion_id, autor_id, contenido) VALUES (?,?,?)", (cid, uid, txt))

# ── Notificaciones ────────────────────────────────────────────
nots = [
    (U_VALE, 'seguidor',   'Carlos A. comenzó a seguirte',                             '/perfil'),
    (U_VALE, 'like',       'María G. le dio ⭐ a tu post "API REST para matrículas"',  f'/post/{pub_ids[3]}'),
    (U_VALE, 'comentario', 'Divis S. comentó en tu publicación: ¡Excelente implementación!', f'/post/{pub_ids[0]}'),
    (U_VALE, 'foro',       'Felipe A. respondió tu pregunta en el foro Cálculo III',   f'/foro/{foro_ids[1]}'),
]
for (uid, tipo, msg, url) in nots:
    c.execute("INSERT INTO notificaciones (usuario_id, tipo, mensaje, url) VALUES (?,?,?,?)", (uid, tipo, msg, url))

# ── Reportes ──────────────────────────────────────────────────
c.execute("""INSERT INTO reportes (reportado_por, tipo, referencia_id, motivo, estado)
             VALUES (?,?,?,?,?)""", (U_VALE, 'publicacion', pub_ids[1], 'Posible plagio', 'enviado'))
c.execute("""INSERT INTO reportes (reportado_por, tipo, referencia_id, motivo, estado)
             VALUES (?,?,?,?,?)""", (U_VALE, 'comentario', com_ids[0], 'Contenido ofensivo', 'en_revision'))

conn.commit()
conn.close()

print("  → Mensajes, notificaciones y reportes insertados.")
print()
print("✅  Base de datos 'agora.db' creada con éxito.")
print()
print("   Cuentas de prueba:")
print("   ┌─────────────────────────────────────────────────────┐")
print("   │  admin@agora.edu          /  admin123   (admin)     │")
print("   │  vale@correounivalle.edu  /  vale123    (estudiante)│")
print("   │  divis@correounivalle.edu /  divis123   (estudiante)│")
print("   │  cris@correounivalle.edu  /  cris123    (estudiante)│")
print("   │  mod@agora.edu            /  mod123     (moderador) │")
print("   └─────────────────────────────────────────────────────┘")
