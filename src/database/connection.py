from contextlib import contextmanager

import bcrypt
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from src.config import ADMIN_PASSWORD, ADMIN_USERNAME, DATABASE_URL
from src.database.models import Base

# check_same_thread só existe (e só é preciso) no SQLite; em Postgres/MySQL não se aplica.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def _add_column_if_missing(conn, table, column, ddl):
    existing = {col["name"] for col in inspect(conn).get_columns(table)}
    if column not in existing:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def _rebuild_usuarios_legado(conn):
    """A tabela antiga tem 'senha' (texto plano, NOT NULL). Reconstrói com o schema novo,
    fazendo hash das senhas existentes. Usuários legados viram admin (eram o dono da loja)."""
    rows = conn.execute(text("SELECT * FROM usuarios")).mappings().all()
    conn.execute(text("ALTER TABLE usuarios RENAME TO usuarios_legado"))
    conn.execute(
        text(
            """
            CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY,
                nome_usuario TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'funcionario'
            )
            """
        )
    )
    for row in rows:
        senha_hash = row.get("senha_hash")
        if not senha_hash:
            senha_hash = bcrypt.hashpw(row["senha"].encode(), bcrypt.gensalt()).decode()
        conn.execute(
            text("INSERT INTO usuarios (id, nome_usuario, senha_hash, role) VALUES (:id, :u, :h, :r)"),
            {"id": row["id"], "u": row["nome_usuario"], "h": senha_hash, "r": row.get("role") or "admin"},
        )
    conn.execute(text("DROP TABLE usuarios_legado"))


def _migrate_legacy_schema(conn):
    """Traz bancos criados pela versão antiga (sqlite3 cru) para o schema atual. Idempotente."""
    tables = inspect(conn).get_table_names()

    if "funcionarios" in tables:
        _add_column_if_missing(
            conn,
            "funcionarios",
            "percentual_comissao",
            "percentual_comissao FLOAT NOT NULL DEFAULT 0.5",
        )

    if "adiantamentos" in tables:
        _add_column_if_missing(
            conn, "adiantamentos", "pagamento_id", "pagamento_id INTEGER REFERENCES pagamentos_funcionarios(id)"
        )

    if "clientes" in tables:
        _add_column_if_missing(conn, "clientes", "bloqueado", "bloqueado BOOLEAN NOT NULL DEFAULT 0")

    if "agendamentos" in tables:
        _add_column_if_missing(conn, "agendamentos", "status", "status TEXT NOT NULL DEFAULT 'agendado'")
        _add_column_if_missing(conn, "agendamentos", "forma_pagamento", "forma_pagamento TEXT")
        # A versão antiga gravava hora ora como 'HH:MM', ora como 'HH:MM:SS'.
        conn.execute(text("UPDATE agendamentos SET hora = substr(hora, 1, 5) WHERE length(hora) > 5"))

    if "usuarios" in tables:
        columns = {col["name"] for col in inspect(conn).get_columns("usuarios")}
        if "senha" in columns:
            _rebuild_usuarios_legado(conn)


def _seed_admin(conn):
    count = conn.execute(text("SELECT COUNT(*) FROM usuarios")).scalar()
    if count == 0:
        hashed = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
        conn.execute(
            text("INSERT INTO usuarios (nome_usuario, senha_hash, role) VALUES (:u, :h, 'admin')"),
            {"u": ADMIN_USERNAME, "h": hashed},
        )


def init_db():
    with engine.begin() as conn:
        _migrate_legacy_schema(conn)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        _seed_admin(conn)


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
