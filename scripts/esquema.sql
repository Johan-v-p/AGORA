-- Esquema de la base de datos de ÁGORA.

-- 1. USUARIOS
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
);

-- 2. SEGUIDORES  (quién sigue a quién)
CREATE TABLE IF NOT EXISTS seguidores (
    seguidor_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    seguido_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (seguidor_id, seguido_id)
);

-- 3. PUBLICACIONES (feed)
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
);

-- 4. REACCIONES A PUBLICACIONES
CREATE TABLE IF NOT EXISTS reacciones_publicacion (
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    publicacion_id  INTEGER NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    tipo            TEXT    NOT NULL DEFAULT 'aplauso',
                            -- 'aplauso' | 'craneo' | 'manos' | 'estrella'
    creado_en       DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, publicacion_id)
);

-- 5. COMENTARIOS DE PUBLICACIONES
CREATE TABLE IF NOT EXISTS comentarios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    publicacion_id  INTEGER NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    autor_id        INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    contenido       TEXT    NOT NULL,
    padre_id        INTEGER REFERENCES comentarios(id) ON DELETE CASCADE,
                    -- NULL = comentario raíz; valor = respuesta a otro comentario
    creado_en       DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6. REACCIONES A COMENTARIOS (like)
CREATE TABLE IF NOT EXISTS reacciones_comentario (
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    comentario_id INTEGER NOT NULL REFERENCES comentarios(id) ON DELETE CASCADE,
    creado_en     DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, comentario_id)
);

-- 7. FOROS
CREATE TABLE IF NOT EXISTS foros (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT    NOT NULL UNIQUE,
    descripcion  TEXT,
    categoria    TEXT,   -- 'matematicas' | 'sistemas' | 'campus' | etc.
    creado_por   INTEGER REFERENCES usuarios(id),
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 8. PREGUNTAS DE FORO
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
);

-- 9. RESPUESTAS DE FORO
CREATE TABLE IF NOT EXISTS respuestas_foro (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta_id  INTEGER NOT NULL REFERENCES preguntas_foro(id) ON DELETE CASCADE,
    autor_id     INTEGER REFERENCES usuarios(id),
    contenido    TEXT    NOT NULL,
    es_anonimo   INTEGER NOT NULL DEFAULT 0,
    aceptada     INTEGER NOT NULL DEFAULT 0,  -- 1 = respuesta marcada como correcta
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 10. VOTOS A RESPUESTAS DE FORO
CREATE TABLE IF NOT EXISTS votos_respuesta (
    usuario_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    respuesta_id INTEGER NOT NULL REFERENCES respuestas_foro(id) ON DELETE CASCADE,
    valor        INTEGER NOT NULL DEFAULT 1,   -- 1 = upvote, -1 = downvote
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, respuesta_id)
);

-- 11. PROYECTOS (portafolio)
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
);

-- 12. APLAUSOS A PROYECTOS
CREATE TABLE IF NOT EXISTS aplausos_proyecto (
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    proyecto_id INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    creado_en   DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, proyecto_id)
);

-- 13. COMENTARIOS DE PROYECTOS
CREATE TABLE IF NOT EXISTS comentarios_proyecto (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    proyecto_id INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    autor_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    contenido   TEXT    NOT NULL,
    creado_en   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 14. EVENTOS
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
);

-- 15. INSCRIPCIONES A EVENTOS
CREATE TABLE IF NOT EXISTS inscripciones_evento (
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    evento_id   INTEGER NOT NULL REFERENCES eventos(id) ON DELETE CASCADE,
    creado_en   DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, evento_id)
);

-- 16. CONVERSACIONES DE MENSAJERÍA
CREATE TABLE IF NOT EXISTS conversaciones (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    creado_en    DATETIME DEFAULT CURRENT_TIMESTAMP,
    ultimo_msg   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS participantes_conversacion (
    conversacion_id  INTEGER NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
    usuario_id       INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    archivada        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (conversacion_id, usuario_id)
);

-- 17. MENSAJES
CREATE TABLE IF NOT EXISTS mensajes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    conversacion_id  INTEGER NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
    autor_id         INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    contenido        TEXT    NOT NULL,
    leido            INTEGER NOT NULL DEFAULT 0,
    creado_en        DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 18. NOTIFICACIONES
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
);

-- 19. REPORTES
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
);

-- 20. GUARDADOS (bookmarks)
CREATE TABLE IF NOT EXISTS guardados (
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    publicacion_id  INTEGER NOT NULL REFERENCES publicaciones(id) ON DELETE CASCADE,
    creado_en       DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, publicacion_id)
);
