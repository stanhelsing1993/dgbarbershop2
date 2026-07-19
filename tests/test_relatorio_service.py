from datetime import date

import pytest

from src.repositories import agendamento_repository, cliente_repository, funcionario_repository, servico_repository
from src.services import relatorio_service

INICIO = date(2026, 8, 1)
FIM = date(2026, 8, 31)


@pytest.fixture()
def cenario(session):
    ana = cliente_repository.criar(session, "Ana", "11991", "a@a.com")
    beto = cliente_repository.criar(session, "Beto", "11992", "b@b.com")
    joao = funcionario_repository.criar(session, "João", "Barbeiro", 0.6)
    corte = servico_repository.criar(session, "Corte", 100.0, 30)
    barba = servico_repository.criar(session, "Barba", 50.0, 30)

    # Segunda 10/08: dois concluídos; Terça 11/08: um concluído, um cancelado, um no-show.
    agendamento_repository.criar(session, ana.id, joao.id, corte.id, date(2026, 8, 10), "09:00", status="concluido")
    agendamento_repository.criar(session, beto.id, joao.id, corte.id, date(2026, 8, 10), "10:00", status="concluido")
    agendamento_repository.criar(session, ana.id, joao.id, barba.id, date(2026, 8, 11), "09:00", status="concluido")
    agendamento_repository.criar(session, beto.id, joao.id, barba.id, date(2026, 8, 11), "10:00", status="cancelado")
    agendamento_repository.criar(session, ana.id, joao.id, barba.id, date(2026, 8, 11), "11:00", status="nao_compareceu")
    return {"joao_id": joao.id}


def test_kpis_do_periodo(session, cenario):
    indicadores = relatorio_service.kpis(session, INICIO, FIM)
    assert indicadores["total_agendamentos"] == 5
    assert indicadores["atendimentos_concluidos"] == 3
    assert indicadores["receita_bruta"] == 250.0
    assert indicadores["comissoes"] == 150.0  # 60% de 250
    assert indicadores["receita_loja"] == 100.0
    assert indicadores["ticket_medio"] == round(250.0 / 3, 2)
    assert indicadores["clientes_unicos"] == 2
    assert indicadores["taxa_cancelamento"] == 20.0
    assert indicadores["taxa_no_show"] == 20.0
    assert indicadores["taxa_ocupacao"] > 0


def test_kpis_periodo_vazio(session):
    indicadores = relatorio_service.kpis(session, INICIO, FIM)
    assert indicadores["receita_bruta"] == 0.0
    assert indicadores["ticket_medio"] == 0.0
    assert indicadores["taxa_cancelamento"] == 0.0


def test_comparativo_com_periodo_anterior(session, cenario):
    dados = relatorio_service.comparativo(session, INICIO, FIM)
    assert dados["atual"]["receita_bruta"] == 250.0
    assert dados["anterior"]["receita_bruta"] == 0.0
    inicio_anterior, fim_anterior = dados["periodo_anterior"]
    assert fim_anterior == date(2026, 7, 31)
    assert (FIM - INICIO) == (fim_anterior - inicio_anterior)


def test_receita_por_dia(session, cenario):
    serie = relatorio_service.receita_por_dia(session, INICIO, FIM)
    assert serie == [
        {"data": date(2026, 8, 10), "receita": 200.0},
        {"data": date(2026, 8, 11), "receita": 50.0},
    ]


def test_atendimentos_por_dia_semana(session, cenario):
    por_dia = relatorio_service.atendimentos_por_dia_semana(session, INICIO, FIM)
    contagem = {item["dia"]: item["atendimentos"] for item in por_dia}
    assert contagem["Segunda"] == 2
    assert contagem["Terça"] == 1
    assert contagem["Domingo"] == 0


def test_top_servicos_ordena_por_receita(session, cenario):
    servicos = relatorio_service.top_servicos(session, INICIO, FIM)
    assert servicos[0]["servico"] == "Corte"
    assert servicos[0]["receita"] == 200.0
    assert servicos[1]["servico"] == "Barba"


def test_desempenho_funcionarios(session, cenario):
    desempenho = relatorio_service.desempenho_funcionarios(session, INICIO, FIM)
    assert len(desempenho) == 1
    item = desempenho[0]
    assert item["funcionario"] == "João"
    assert item["atendimentos"] == 3
    assert item["receita"] == 250.0
    assert item["comissao"] == 150.0
    assert item["receita_loja"] == 100.0


def test_metas_padrao_e_salvar(session):
    metas = relatorio_service.obter_metas(session)
    assert metas == relatorio_service.METAS_PADRAO

    relatorio_service.salvar_meta(session, "receita_mensal", 20000.0)
    metas = relatorio_service.obter_metas(session)
    assert metas["receita_mensal"] == 20000.0


def test_salvar_meta_invalida(session):
    with pytest.raises(ValueError):
        relatorio_service.salvar_meta(session, "meta_inexistente", 10.0)
    with pytest.raises(ValueError):
        relatorio_service.salvar_meta(session, "receita_mensal", -5.0)


def test_progresso_metas(session, cenario):
    relatorio_service.salvar_meta(session, "receita_mensal", 500.0)
    indicadores = relatorio_service.kpis(session, INICIO, FIM)
    progresso = {m["chave"]: m for m in relatorio_service.progresso_metas(session, indicadores)}

    assert progresso["receita_mensal"]["progresso"] == 0.5  # 250 de 500
    assert not progresso["receita_mensal"]["atingida"]
    # No-show de 20% acima do teto de 10% => meta não atingida.
    assert not progresso["taxa_no_show_max"]["atingida"]
