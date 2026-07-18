from datetime import date
from types import SimpleNamespace

from src.repositories import agendamento_repository, cliente_repository, funcionario_repository, servico_repository
from src.services import faturamento_service


def test_calcular_repasse_divide_50_50_por_padrao():
    rows = [
        SimpleNamespace(
            funcionario_id=1, funcionario="João", servico="Corte", preco_servico=100.0, data=date(2026, 8, 1)
        )
    ]
    resultado = faturamento_service.calcular_repasse(rows)
    assert resultado[0]["repasse_funcionario"] == 50.0
    assert resultado[0]["repasse_loja"] == 50.0


def test_calcular_repasse_percentual_customizado():
    rows = [
        SimpleNamespace(
            funcionario_id=1, funcionario="João", servico="Corte", preco_servico=100.0, data=date(2026, 8, 1)
        )
    ]
    resultado = faturamento_service.calcular_repasse(rows, percentual=0.6)
    assert resultado[0]["repasse_funcionario"] == 60.0
    assert resultado[0]["repasse_loja"] == 40.0


def test_faturamento_total_soma_apenas_concluidos(session):
    cliente = cliente_repository.criar(session, "Cliente", "119999", "c@c.com")
    funcionario = funcionario_repository.criar(session, "Func", "Barbeiro")
    servico = servico_repository.criar(session, "Corte", 40.0, 30)
    agendamento = agendamento_repository.criar(
        session, cliente.id, funcionario.id, servico.id, date(2026, 8, 1), "09:00"
    )

    # Agendado ainda não é receita.
    assert faturamento_service.faturamento_total(session) == 0.0

    agendamento_repository.atualizar_status(session, agendamento.id, "concluido")
    assert faturamento_service.faturamento_total(session) == 40.0


def test_faturamento_total_sem_agendamentos_retorna_zero(session):
    assert faturamento_service.faturamento_total(session) == 0.0


def test_faturamento_total_ignora_cancelados_e_no_show(session):
    cliente = cliente_repository.criar(session, "Cliente", "119999", "c@c.com")
    funcionario = funcionario_repository.criar(session, "Func", "Barbeiro")
    servico = servico_repository.criar(session, "Corte", 40.0, 30)
    valido = agendamento_repository.criar(session, cliente.id, funcionario.id, servico.id, date(2026, 8, 1), "09:00")
    cancelado = agendamento_repository.criar(session, cliente.id, funcionario.id, servico.id, date(2026, 8, 1), "10:00")
    falta = agendamento_repository.criar(session, cliente.id, funcionario.id, servico.id, date(2026, 8, 1), "11:00")
    agendamento_repository.atualizar_status(session, valido.id, "concluido")
    agendamento_repository.atualizar_status(session, cancelado.id, "cancelado")
    agendamento_repository.atualizar_status(session, falta.id, "nao_compareceu")

    assert faturamento_service.faturamento_total(session) == 40.0
