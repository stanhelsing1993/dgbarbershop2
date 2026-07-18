from datetime import date, datetime

import pytest

from src.repositories import agendamento_repository, cliente_repository, funcionario_repository, servico_repository
from src.services import agendamento_service
from src.services.agendamento_service import ConflitoDeHorarioError


@pytest.fixture()
def cadastro_basico(session):
    cliente = cliente_repository.criar(session, "Cliente Teste", "11999999999", "cliente@teste.com")
    funcionario_a = funcionario_repository.criar(session, "Funcionário A", "Barbeiro")
    funcionario_b = funcionario_repository.criar(session, "Funcionário B", "Barbeiro")
    servico = servico_repository.criar(session, "Corte", 50.0, 30)
    return {
        "cliente_id": cliente.id,
        "funcionario_a_id": funcionario_a.id,
        "funcionario_b_id": funcionario_b.id,
        "servico_id": servico.id,
    }


def test_criar_agendamento_sucesso(session, cadastro_basico):
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    assert agendamento.id is not None
    assert agendamento.status == "agendado"


def test_conflito_mesmo_funcionario_mesmo_horario(session, cadastro_basico):
    agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    with pytest.raises(ConflitoDeHorarioError):
        agendamento_service.criar_agendamento(
            session,
            cadastro_basico["cliente_id"],
            cadastro_basico["funcionario_a_id"],
            cadastro_basico["servico_id"],
            date(2026, 8, 10),
            "10:00",
        )


def test_mesmo_horario_funcionarios_diferentes_nao_conflita(session, cadastro_basico):
    agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_b_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    assert agendamento.id is not None


def test_horarios_disponiveis_exclui_horario_ocupado(session, cadastro_basico):
    agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    horarios = agendamento_service.horarios_disponiveis(
        session, cadastro_basico["funcionario_a_id"], date(2026, 8, 10)
    )
    assert "10:00" not in horarios
    assert "10:30" in horarios


def test_grade_nao_inclui_horario_de_fechamento(session, cadastro_basico):
    horarios = agendamento_service.horarios_disponiveis(
        session, cadastro_basico["funcionario_a_id"], date(2026, 8, 10)
    )
    assert "08:00" in horarios
    assert "18:30" in horarios
    assert "19:00" not in horarios


def test_horarios_de_hoje_excluem_horas_ja_passadas(session, cadastro_basico):
    agora = datetime(2026, 8, 10, 12, 10)
    horarios = agendamento_service.horarios_disponiveis(
        session, cadastro_basico["funcionario_a_id"], date(2026, 8, 10), agora=agora
    )
    assert "12:00" not in horarios
    assert "12:30" in horarios


def test_horarios_de_data_passada_retorna_vazio(session, cadastro_basico):
    agora = datetime(2026, 8, 11, 9, 0)
    horarios = agendamento_service.horarios_disponiveis(
        session, cadastro_basico["funcionario_a_id"], date(2026, 8, 10), agora=agora
    )
    assert horarios == []


def test_criar_agendamento_em_data_passada_levanta_erro(session, cadastro_basico):
    with pytest.raises(ValueError):
        agendamento_service.criar_agendamento(
            session,
            cadastro_basico["cliente_id"],
            cadastro_basico["funcionario_a_id"],
            cadastro_basico["servico_id"],
            date(2020, 1, 1),
            "10:00",
        )


def test_reativar_falha_se_horario_foi_tomado(session, cadastro_basico):
    original = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    agendamento_service.alterar_status(session, original.id, "cancelado")
    agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    with pytest.raises(ConflitoDeHorarioError):
        agendamento_service.alterar_status(session, original.id, "agendado")


def test_reativar_proprio_agendamento_concluido_nao_conflita_consigo(session, cadastro_basico):
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    agendamento_service.alterar_status(session, agendamento.id, "concluido")
    agendamento_service.alterar_status(session, agendamento.id, "agendado")
    assert agendamento.status == "agendado"


def test_alterar_status_em_lote(session, cadastro_basico):
    ids = []
    for hora in ("10:00", "10:30", "11:00"):
        agendamento = agendamento_service.criar_agendamento(
            session,
            cadastro_basico["cliente_id"],
            cadastro_basico["funcionario_a_id"],
            cadastro_basico["servico_id"],
            date(2026, 8, 10),
            hora,
        )
        ids.append(agendamento.id)

    alterados = agendamento_service.alterar_status_em_lote(session, ids, "concluido")

    assert alterados == 3
    linhas = agendamento_repository.listar_detalhado(session)
    assert all(r.status == "concluido" for r in linhas)


def test_lancar_atendimento_avulso_entra_como_concluido(session, cadastro_basico):
    agora = datetime(2026, 8, 10, 14, 30)
    agendamento = agendamento_service.lancar_atendimento_avulso(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        agora=agora,
    )
    assert agendamento.status == "concluido"
    assert agendamento.data == date(2026, 8, 10)
    assert agendamento.hora == "14:30"


def test_lancar_atendimento_avulso_nao_aceita_data_futura(session, cadastro_basico):
    agora = datetime(2026, 8, 10, 14, 30)
    with pytest.raises(ValueError):
        agendamento_service.lancar_atendimento_avulso(
            session,
            cadastro_basico["cliente_id"],
            cadastro_basico["funcionario_a_id"],
            cadastro_basico["servico_id"],
            dia=date(2026, 8, 11),
            agora=agora,
        )


def test_lancar_atendimento_avulso_ignora_conflito_de_grade(session, cadastro_basico):
    agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    agora = datetime(2026, 8, 10, 10, 0)
    avulso = agendamento_service.lancar_atendimento_avulso(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        dia=date(2026, 8, 10),
        hora="10:00",
        agora=agora,
    )
    assert avulso.id is not None


def test_alterar_status_valido(session, cadastro_basico):
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    agendamento_service.alterar_status(session, agendamento.id, "cancelado")
    assert agendamento.status == "cancelado"


def test_alterar_status_invalido_levanta_erro(session, cadastro_basico):
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    with pytest.raises(ValueError):
        agendamento_service.alterar_status(session, agendamento.id, "inexistente")


def test_horario_cancelado_volta_a_ficar_disponivel(session, cadastro_basico):
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    agendamento_service.alterar_status(session, agendamento.id, "cancelado")
    horarios = agendamento_service.horarios_disponiveis(
        session, cadastro_basico["funcionario_a_id"], date(2026, 8, 10)
    )
    assert "10:00" in horarios


def test_horarios_disponiveis_nao_afeta_outro_funcionario(session, cadastro_basico):
    agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    horarios_b = agendamento_service.horarios_disponiveis(
        session, cadastro_basico["funcionario_b_id"], date(2026, 8, 10)
    )
    assert "10:00" in horarios_b
