"""Datos de demostración de ÁGORA: cuentas, publicaciones, foros, eventos y mensajes."""

from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash


def insertar_datos_demo(conn):
    """Inserta en la base de datos el contenido de ejemplo."""
    c = conn.cursor()

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
    print("  - Usuarios insertados.")

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
    print("  - Publicaciones, reacciones y comentarios insertados.")

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
    print("  - Foros, preguntas y respuestas insertados.")

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
    print("  - Proyectos y eventos insertados.")

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
    print("  - Mensajes, notificaciones y reportes insertados.")
