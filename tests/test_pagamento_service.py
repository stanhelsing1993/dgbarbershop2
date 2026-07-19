from datetime import date

import pytest

from src.repositories import (
    adiantamento_repository,
    agendamento_repository,
    caixa_repository,
    cliente_repository,
    funcionario_repository,
    pagamento_repository,
    servico_repository,
)
from src.services import faturamento_service, pagamento_service
from src.services.pagamento_service import PagamentoError

INICIO = date(2026, 8, 1)
FIM = date(2026, 8, 31)


@pytest.fixture()
def base(session):
    cliente = cliente_repository.criar(session, "Cliente", "119999", "c@c.com")
    joao = funcionario_repository.criar(session, "João", "Barbeiro", 0.6)
    servico = servico_repository.criar(session, "Corte", 100.0, 30)
    # Dois atendimentos concluídos no período: comissão = 60% de 200 = 120.
    agendamento_repository.criar(
        session, cliente.id, joao.id, servico.id, date(2026, 8, 10), "09:00", status="concluido"
    )
    agendamento_repository.criar(
        session, cliente.id, joao.id, servico.id, date(2026, 8, 12), "10:00", status="concluido"
    )
    return {"funcionario_id": joao.id, "cliente_id": cliente.id, "servico_id": servico.id}


def test_previa_acerto_soma_comissao_e_vales(session, base):
    adiantamento_repository.criar(session, base["funcionario_id"], date(2026, 8, 11), 40.0)
    previa = pagamento_service.previa_acerto(session, base["funcionario_id"], INICIO, FIM)
    assert previa["comissao"] == 120.0
    assert previa["total_vales"] == 40.0
    assert previa["liquido"] == 80.0


def test_previa_inclui_vale_antigo_pendente(session, base):
    # Vale de antes do período segue pendente e entra no abatimento.
    adiantamento_repository.criar(session, base["funcionario_id"], date(2026, 7, 20), 30.0)
    previa = pagamento_service.previa_acerto(session, base["funcionario_id"], INICIO, FIM)
    assert previa["total_vales"] == 30.0
    assert previa["liquido"] == 90.0


def test_registrar_pagamento_abate_vales(session, base):
    vale = adiantamento_repository.criar(session, base["funcionario_id"], date(2026, 8, 11), 40.0)
    pagamento = pagamento_service.registrar_pagamento(
        session, base["funcionario_id"], INICIO, FIM, data_pagamento=date(2026, 8, 31)
    )
    assert pagamento.comissao_base == 120.0
    assert pagamento.descontos_abatidos == 40.0
    assert pagamento.valor_pago == 80.0
    assert vale.pagamento_id == pagamento.id
    # Depois do acerto não sobra vale pendente.
    pendentes = adiantamento_repository.listar_pendentes(session, base["funcionario_id"], ate=FIM)
    assert pendentes == []


def test_registrar_pagamento_lanca_saida_no_caixa(session, base):
    pagamento_service.registrar_pagamento(
        session,
        base["funcionario_id"],
        INICIO,
        FIM,
        data_pagamento=date(2026, 8, 31),
        lancar_no_caixa=True,
    )
    saidas = caixa_repository.total_movimentos(session, date(2026, 8, 31), "saida")
    assert saidas == 120.0


def test_registrar_pagamento_vales_maiores_que_comissao_bloqueia(session, base):
    adiantamento_repository.criar(session, base["funcionario_id"], date(2026, 8, 11), 500.0)
    with pytest.raises(PagamentoError):
        pagamento_service.registrar_pagamento(
            session, base["funcionario_id"], INICIO, FIM, data_pagamento=date(2026, 8, 31)
        )


def test_registrar_pagamento_periodo_invertido_bloqueia(session, base):
    with pytest.raises(PagamentoError):
        pagamento_service.registrar_pagamento(
            session, base["funcionario_id"], FIM, INICIO, data_pagamento=date(2026, 8, 31)
        )


def test_relatorio_pagamentos_reflete_acerto(session, base):
    adiantamento_repository.criar(session, base["funcionario_id"], date(2026, 8, 11), 40.0)
    antes = faturamento_service.relatorio_pagamentos(session, INICIO, FIM)[0]
    assert antes["descontos"] == 40.0
    assert antes["liquido"] == 80.0

    pagamento_service.registrar_pagamento(
        session, base["funcionario_id"], INICIO, FIM, data_pagamento=date(2026, 8, 31)
    )

    depois = faturamento_service.relatorio_pagamentos(session, INICIO, FIM)[0]
    assert depois["descontos"] == 0.0  # vale abatido não é mais pendente
    assert depois["pago"] == 80.0
    # Comissão 120 = 80 pagos em dinheiro + 40 de vale abatido: nada mais a pagar.
    assert depois["liquido"] == 0.0


def test_historico_de_pagamentos(session, base):
    pagamento_service.registrar_pagamento(
        session, base["funcionario_id"], INICIO, FIM, data_pagamento=date(2026, 8, 31)
    )
    historico = pagamento_repository.listar_por_periodo(session, INICIO, FIM)
    assert len(historico) == 1
    assert historico[0].funcionario == "João"
    assert historico[0].valor_pago == 120.0
