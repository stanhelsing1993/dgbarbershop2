from datetime import date
from types import SimpleNamespace

from src.repositories import (
    adiantamento_repository,
    agendamento_repository,
    cliente_repository,
    funcionario_repository,
    servico_repository,
)
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


def test_calcular_repasse_usa_percentual_do_funcionario():
    rows = [
        SimpleNamespace(
            funcionario_id=1, funcionario="João", servico="Corte", preco_servico=100.0, data=date(2026, 8, 1)
        ),
        SimpleNamespace(
            funcionario_id=2, funcionario="Maria", servico="Corte", preco_servico=100.0, data=date(2026, 8, 1)
        ),
    ]
    resultado = faturamento_service.calcular_repasse(rows, percentuais={1: 0.6})
    assert resultado[0]["repasse_funcionario"] == 60.0
    assert resultado[0]["repasse_loja"] == 40.0
    # Quem não está no mapa cai no padrão 50%.
    assert resultado[1]["repasse_funcionario"] == 50.0


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


def test_relatorio_pagamentos_calcula_liquido_com_descontos(session):
    cliente = cliente_repository.criar(session, "Cliente", "119999", "c@c.com")
    joao = funcionario_repository.criar(session, "João", "Barbeiro", 0.6)
    maria = funcionario_repository.criar(session, "Maria", "Barbeira")
    servico = servico_repository.criar(session, "Corte", 100.0, 30)

    dia = date(2026, 8, 10)
    agendamento_repository.criar(session, cliente.id, joao.id, servico.id, dia, "09:00", status="concluido")
    agendamento_repository.criar(session, cliente.id, joao.id, servico.id, dia, "10:00", status="concluido")
    agendamento_repository.criar(session, cliente.id, maria.id, servico.id, dia, "09:00", status="concluido")
    adiantamento_repository.criar(session, joao.id, dia, 40.0, "vale")

    relatorio = faturamento_service.relatorio_pagamentos(session, dia, dia)
    por_nome = {item["funcionario"]: item for item in relatorio}

    assert por_nome["João"]["receita_bruta"] == 200.0
    assert por_nome["João"]["comissao"] == 120.0  # 60% de 200
    assert por_nome["João"]["descontos"] == 40.0
    assert por_nome["João"]["liquido"] == 80.0
    assert por_nome["Maria"]["comissao"] == 50.0  # padrão 50%
    assert por_nome["Maria"]["liquido"] == 50.0


def test_relatorio_pagamentos_inclui_funcionario_so_com_vale(session):
    funcionario = funcionario_repository.criar(session, "Zé", "Barbeiro")
    dia = date(2026, 8, 10)
    adiantamento_repository.criar(session, funcionario.id, dia, 30.0)

    relatorio = faturamento_service.relatorio_pagamentos(session, dia, dia)

    assert len(relatorio) == 1
    assert relatorio[0]["receita_bruta"] == 0.0
    assert relatorio[0]["liquido"] == -30.0


def test_resumo_financeiro_receita_loja(session):
    cliente = cliente_repository.criar(session, "Cliente", "119999", "c@c.com")
    joao = funcionario_repository.criar(session, "João", "Barbeiro", 0.4)
    servico = servico_repository.criar(session, "Corte", 100.0, 30)
    dia = date(2026, 8, 10)
    agendamento_repository.criar(session, cliente.id, joao.id, servico.id, dia, "09:00", status="concluido")
    adiantamento_repository.criar(session, joao.id, dia, 10.0)

    resumo = faturamento_service.resumo_financeiro(session, dia, dia)

    assert resumo["receita_bruta"] == 100.0
    assert resumo["pagamentos_funcionarios"] == 40.0
    assert resumo["descontos"] == 10.0
    assert resumo["liquido_a_pagar"] == 30.0
    assert resumo["receita_loja"] == 60.0


def test_receita_por_forma_pagamento(session):
    cliente = cliente_repository.criar(session, "Cliente", "119999", "c@c.com")
    funcionario = funcionario_repository.criar(session, "Func", "Barbeiro")
    servico = servico_repository.criar(session, "Corte", 50.0, 30)
    dia = date(2026, 8, 10)
    agendamento_repository.criar(
        session, cliente.id, funcionario.id, servico.id, dia, "09:00",
        status="concluido", forma_pagamento="pix",
    )
    agendamento_repository.criar(
        session, cliente.id, funcionario.id, servico.id, dia, "10:00",
        status="concluido", forma_pagamento="pix",
    )
    agendamento_repository.criar(
        session, cliente.id, funcionario.id, servico.id, dia, "11:00",
        status="concluido", forma_pagamento="dinheiro",
    )
    # Concluído sem forma informada (registro antigo) entra como 'Não informado'.
    agendamento_repository.criar(
        session, cliente.id, funcionario.id, servico.id, dia, "12:00", status="concluido"
    )

    resultado = faturamento_service.receita_por_forma_pagamento(session, dia, dia)
    por_forma = {item["forma"]: item for item in resultado}

    assert por_forma["Pix"]["receita"] == 100.0
    assert por_forma["Pix"]["atendimentos"] == 2
    assert por_forma["Dinheiro"]["receita"] == 50.0
    assert por_forma["Não informado"]["receita"] == 50.0
    assert resultado[0]["forma"] == "Pix"  # ordenado por receita


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
