"""Smoke test manual: exercita init_db, migração legada e os serviços contra um banco temporário.

Uso: DATABASE_URL=sqlite:///<tmp> python tests/smoke_manual.py
Não é coletado pelo pytest (não segue o padrão test_*.py) — é um script de verificação end-to-end.
"""
import os
import sqlite3
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

tmp_dir = tempfile.mkdtemp()
db_path = os.path.join(tmp_dir, "smoke.db")

# Monta um banco no formato LEGADO (schema antigo do sqlite3 cru) para validar a migração.
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("CREATE TABLE clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, telefone TEXT, email TEXT)")
cur.execute("CREATE TABLE funcionarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, especialidade TEXT)")
cur.execute("CREATE TABLE servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, preco REAL, duracao INTEGER)")
cur.execute(
    "CREATE TABLE agendamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, funcionario_id INTEGER, "
    "servico_id INTEGER, data TEXT, hora TEXT)"
)
cur.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome_usuario TEXT NOT NULL UNIQUE, senha TEXT NOT NULL)")
cur.execute("INSERT INTO usuarios (nome_usuario, senha) VALUES ('dono', 'senha-antiga')")
cur.execute("INSERT INTO clientes (nome, telefone, email) VALUES ('Cliente Legado', '11999', 'x@y.com')")
cur.execute("INSERT INTO funcionarios (nome, especialidade) VALUES ('Barbeiro Legado', 'Cortes')")
cur.execute("INSERT INTO servicos (nome, preco, duracao) VALUES ('Corte Legado', 45.0, 30)")
cur.execute("INSERT INTO agendamentos (cliente_id, funcionario_id, servico_id, data, hora) VALUES (1, 1, 1, '2026-07-20', '10:00:00')")
conn.commit()
conn.close()

os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from src.database.connection import get_session, init_db  # noqa: E402
from src.repositories import agendamento_repository, cliente_repository  # noqa: E402
from src.services import agendamento_service, auth_service, faturamento_service  # noqa: E402

init_db()

with get_session() as session:
    # 1. Migração: usuário legado deve logar com a senha antiga (agora com hash)
    usuario = auth_service.autenticar(session, "dono", "senha-antiga")
    assert usuario is not None, "login do usuário legado falhou"
    assert usuario.role == "admin", f"role esperada admin, veio {usuario.role}"

    # 2. Migração: hora 'HH:MM:SS' deve ter sido normalizada para 'HH:MM'
    linhas = agendamento_repository.listar_detalhado(session)
    assert linhas[0].hora == "10:00", f"hora não normalizada: {linhas[0].hora}"
    assert linhas[0].status == "agendado", f"status default ausente: {linhas[0].status}"

    # 3. Disponibilidade: 10:00 ocupado para o funcionário 1 em 2026-07-20
    horarios = agendamento_service.horarios_disponiveis(session, 1, date(2026, 7, 20))
    assert "10:00" not in horarios, "horário ocupado apareceu como disponível"
    assert "10:30" in horarios, "grade de horários incompleta"

    # 4. Conflito bloqueado / criação normal funciona
    try:
        agendamento_service.criar_agendamento(session, 1, 1, 1, date(2026, 7, 20), "10:00")
        raise AssertionError("conflito não foi bloqueado")
    except agendamento_service.ConflitoDeHorarioError:
        pass
    agendamento_service.criar_agendamento(session, 1, 1, 1, date(2026, 7, 20), "11:00")

    # 5. CRUD básico
    cliente = cliente_repository.criar(session, "Novo Cliente", "1188", "n@c.com")
    assert cliente.id is not None

    # 6. Faturamento
    total = faturamento_service.faturamento_total(session)
    assert total == 90.0, f"faturamento esperado 90.0 (2 x 45), veio {total}"

    # 7. Repasse
    rows = faturamento_service.faturamento_por_periodo(session, date(2026, 7, 1), date(2026, 7, 31))
    repasse = faturamento_service.calcular_repasse(rows)
    assert sum(r["repasse_funcionario"] for r in repasse) == 45.0

print("SMOKE TEST OK: migração legada, auth, agenda, CRUD e faturamento funcionando.")
sys.exit(0)
