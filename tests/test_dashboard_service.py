import pandas as pd

from src.services import dashboard_service

_COLUNAS = ["Funcionario", "Servico", "Preco", "Status"]


def test_calcular_metricas_rf012():
    df = pd.DataFrame(
        [
            {"Funcionario": "João", "Servico": "Corte", "Preco": 40.0, "Status": "concluido"},
            {"Funcionario": "João", "Servico": "Corte", "Preco": 40.0, "Status": "agendado"},
            {"Funcionario": "Pedro", "Servico": "Barba", "Preco": 30.0, "Status": "cancelado"},
            {"Funcionario": "Pedro", "Servico": "Barba", "Preco": 30.0, "Status": "nao_compareceu"},
        ]
    )
    m = dashboard_service.calcular_metricas(df)

    assert m["total_agendamentos"] == 4
    # Só o concluído vira receita: o agendado ainda é expectativa.
    assert m["receita"] == 40.0
    assert m["ticket_medio"] == 40.0
    assert m["taxa_cancelamento"] == 0.25
    assert m["taxa_no_show"] == 0.25
    assert m["servico_mais_vendido"] == "Corte"
    assert m["barbeiro_top"] == "João"


def test_calcular_metricas_sem_agendamentos():
    m = dashboard_service.calcular_metricas(pd.DataFrame(columns=_COLUNAS))

    assert m["total_agendamentos"] == 0
    assert m["receita"] == 0.0
    assert m["ticket_medio"] == 0.0
    assert m["taxa_cancelamento"] == 0.0
    assert m["taxa_no_show"] == 0.0
    assert m["servico_mais_vendido"] is None
    assert m["barbeiro_top"] is None


def test_calcular_metricas_so_cancelados_nao_divide_por_zero():
    df = pd.DataFrame(
        [{"Funcionario": "João", "Servico": "Corte", "Preco": 40.0, "Status": "cancelado"}]
    )
    m = dashboard_service.calcular_metricas(df)

    assert m["receita"] == 0.0
    assert m["ticket_medio"] == 0.0
    assert m["taxa_cancelamento"] == 1.0
    assert m["servico_mais_vendido"] is None
