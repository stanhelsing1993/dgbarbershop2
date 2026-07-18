"""Smoke test de UI: executa app.py e cada página via streamlit.testing.AppTest contra um banco temporário.

Uso: python tests/smoke_ui.py
"""
import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

tmp_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(tmp_dir, 'ui_smoke.db')}"

from streamlit.testing.v1 import AppTest  # noqa: E402

from src.database.connection import get_session, init_db  # noqa: E402
from src.repositories import cliente_repository, funcionario_repository, servico_repository  # noqa: E402
from src.services import agendamento_service  # noqa: E402

init_db()
with get_session() as session:
    cliente = cliente_repository.criar(session, "Cliente UI", "1199", "ui@teste.com")
    funcionario = funcionario_repository.criar(session, "Barbeiro UI", "Cortes")
    servico = servico_repository.criar(session, "Corte UI", 50.0, 30)
    agendamento_service.criar_agendamento(session, cliente.id, funcionario.id, servico.id, date.today(), "10:00")

falhas = []


def rodar(alvo, logado=True, admin=True):
    at = AppTest.from_file(alvo, default_timeout=30)
    if logado:
        at.session_state["usuario_logado"] = "admin"
        at.session_state["role"] = "admin" if admin else "funcionario"
    at.run()
    if at.exception:
        falhas.append((alvo, [str(e.value) for e in at.exception]))
        print(f"FALHOU  {alvo}: {[str(e.value) for e in at.exception]}")
    else:
        print(f"OK      {alvo}")


rodar("app.py", logado=False)          # visitante: só Agenda
rodar("app.py")                        # admin logado
rodar("pages/1_Dashboard.py")
rodar("pages/2_Clientes.py")
rodar("pages/3_Agenda.py", logado=False)
rodar("pages/4_Servicos.py")
rodar("pages/5_Funcionarios.py")
rodar("pages/6_Faturamento.py")
rodar("pages/6_Faturamento.py", admin=False)  # não-admin deve ser barrado sem exceção

sys.exit(1 if falhas else 0)
