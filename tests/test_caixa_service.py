from datetime import date, datetime

import pytest

from src.repositories import (
    adiantamento_repository,
    agendamento_repository,
    caixa_repository,
    cliente_repository,
    funcionario_repository,
    servico_repository,
)
from src.services import caixa_service
from src.services.caixa_service import CaixaError

DIA = date(2026, 8, 10)


@pytest.fixture()
def atendimento_concluido(session):
    cliente = cliente_repository.criar(session, "Cliente", "119999", "c@c.com")
    funcionario = funcionario_repository.criar(session, "Func", "Barbeiro")
    servico = servico_repository.criar(session, "Corte", 50.0, 30)
    agendamento = agendamento_repository.criar(
        session, cliente.id, funcionario.id, servico.id, DIA, "09:00", status="concluido"
    )
    return {"funcionario_id": funcionario.id, "agendamento_id": agendamento.id}


def test_abrir_caixa_muda_status(session):
    assert caixa_service.status_do_dia(session, DIA) == caixa_service.STATUS_NAO_ABERTO
    caixa_service.abrir_caixa(session, DIA, 100.0, "admin", agora=datetime(2026, 8, 10, 8, 0))
    assert caixa_service.status_do_dia(session, DIA) == caixa_service.STATUS_ABERTO


def test_abrir_caixa_duas_vezes_levanta_erro(session):
    caixa_service.abrir_caixa(session, DIA, 100.0)
    with pytest.raises(CaixaError):
        caixa_service.abrir_caixa(session, DIA, 50.0)


def test_abrir_caixa_valor_negativo_levanta_erro(session):
    with pytest.raises(CaixaError):
        caixa_service.abrir_caixa(session, DIA, -10.0)


def test_fechar_sem_abrir_levanta_erro(session):
    with pytest.raises(CaixaError):
        caixa_service.fechar_caixa(session, DIA)


def test_fechar_duas_vezes_levanta_erro(session):
    caixa_service.abrir_caixa(session, DIA, 0.0)
    caixa_service.fechar_caixa(session, DIA)
    with pytest.raises(CaixaError):
        caixa_service.fechar_caixa(session, DIA)


def test_resumo_do_dia_soma_tudo(session, atendimento_concluido):
    caixa_service.abrir_caixa(session, DIA, 100.0)
    caixa_repository.criar_movimento(session, DIA, "entrada", 30.0, "Venda de pomada")
    caixa_repository.criar_movimento(session, DIA, "saida", 20.0, "Compra de lâminas")
    adiantamento_repository.criar(session, atendimento_concluido["funcionario_id"], DIA, 25.0)

    resumo = caixa_service.resumo_do_dia(session, DIA)

    assert resumo["valor_inicial"] == 100.0
    assert resumo["receita_servicos"] == 50.0
    assert resumo["entradas"] == 30.0
    assert resumo["saidas"] == 20.0
    assert resumo["adiantamentos"] == 25.0
    assert resumo["saldo"] == 100.0 + 50.0 + 30.0 - 20.0 - 25.0


def test_fechar_caixa_grava_snapshot(session, atendimento_concluido):
    caixa_service.abrir_caixa(session, DIA, 100.0)
    fechamento = caixa_service.fechar_caixa(session, DIA, "tudo certo")
    assert fechamento.receita_servicos == 50.0
    assert fechamento.saldo == 150.0
    assert fechamento.observacao == "tudo certo"
    assert caixa_service.status_do_dia(session, DIA) == caixa_service.STATUS_FECHADO


def test_pendencia_dia_anterior_sem_fechamento(session):
    caixa_service.abrir_caixa(session, date(2026, 8, 9), 50.0)
    alertas = caixa_service.pendencias(session, agora=datetime(2026, 8, 10, 10, 0))
    assert any("09/08/2026" in a["mensagem"] for a in alertas)
    assert alertas[0]["nivel"] == "erro"


def test_pendencia_caixa_nao_aberto_durante_expediente(session):
    alertas = caixa_service.pendencias(session, agora=datetime(2026, 8, 10, 10, 0))
    assert any(a["nivel"] == "info" for a in alertas)


def test_pendencia_fechar_caixa_apos_expediente(session):
    caixa_service.abrir_caixa(session, DIA, 0.0)
    alertas = caixa_service.pendencias(session, agora=datetime(2026, 8, 10, 19, 30))
    assert any(a["nivel"] == "aviso" for a in alertas)


def test_sem_pendencias_com_caixa_fechado(session):
    caixa_service.abrir_caixa(session, DIA, 0.0)
    caixa_service.fechar_caixa(session, DIA)
    alertas = caixa_service.pendencias(session, agora=datetime(2026, 8, 10, 20, 0))
    assert alertas == []


def test_sem_pendencia_antes_do_expediente(session):
    alertas = caixa_service.pendencias(session, agora=datetime(2026, 8, 10, 7, 0))
    assert alertas == []
