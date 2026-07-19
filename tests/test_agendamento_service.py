from datetime import date, datetime

import pytest

from src.repositories import agendamento_repository, cliente_repository, funcionario_repository, servico_repository
from src.services import agendamento_service
from src.services.agendamento_service import ConflitoDeHorarioError


@pytest.fixture()
def cadastro_basico(session):
    cliente = cliente_repository.criar(session, "Cliente Teste", "11999999999", "cliente@teste.com")
    cliente_b = cliente_repository.criar(session, "Cliente B", "11888888888", "b@teste.com")
    funcionario_a = funcionario_repository.criar(session, "Funcionário A", "Barbeiro")
    funcionario_b = funcionario_repository.criar(session, "Funcionário B", "Barbeiro")
    servico = servico_repository.criar(session, "Corte", 50.0, 30)
    return {
        "cliente_id": cliente.id,
        "cliente_b_id": cliente_b.id,
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
            cadastro_basico["cliente_b_id"],
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
        cadastro_basico["cliente_b_id"],
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


def test_horarios_de_hoje_ficam_indisponiveis_pela_antecedencia(session, cadastro_basico):
    agora = datetime(2026, 8, 10, 12, 10)
    horarios = agendamento_service.horarios_disponiveis(
        session, cadastro_basico["funcionario_a_id"], date(2026, 8, 10), agora=agora
    )
    assert horarios == []


def test_horarios_de_amanha_disponiveis(session, cadastro_basico):
    agora = datetime(2026, 8, 10, 12, 10)
    horarios = agendamento_service.horarios_disponiveis(
        session, cadastro_basico["funcionario_a_id"], date(2026, 8, 11), agora=agora
    )
    assert "08:00" in horarios


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


def test_criar_agendamento_para_hoje_exige_antecedencia(session, cadastro_basico):
    with pytest.raises(ValueError):
        agendamento_service.criar_agendamento(
            session,
            cadastro_basico["cliente_id"],
            cadastro_basico["funcionario_a_id"],
            cadastro_basico["servico_id"],
            date(2026, 8, 10),
            "10:00",
            hoje=date(2026, 8, 10),
        )


def test_criar_agendamento_para_amanha_respeita_antecedencia(session, cadastro_basico):
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 11),
        "10:00",
        hoje=date(2026, 8, 10),
    )
    assert agendamento.id is not None


def test_concluir_antes_do_horario_levanta_erro(session, cadastro_basico):
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "15:00",
    )
    with pytest.raises(agendamento_service.ConclusaoAntecipadaError):
        agendamento_service.alterar_status(
            session, agendamento.id, "concluido", agora=datetime(2026, 8, 10, 14, 0)
        )


def test_concluir_apos_o_horario_funciona(session, cadastro_basico):
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "15:00",
    )
    agendamento_service.alterar_status(
        session, agendamento.id, "concluido", agora=datetime(2026, 8, 10, 15, 40)
    )
    assert agendamento.status == "concluido"


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
    agendamento_service.alterar_status(
        session, agendamento.id, "concluido", agora=datetime(2026, 8, 10, 10, 30)
    )
    agendamento_service.alterar_status(session, agendamento.id, "agendado")
    assert agendamento.status == "agendado"


def test_alterar_status_em_lote(session, cadastro_basico):
    ids = []
    for i, hora in enumerate(("10:00", "10:30", "11:00")):
        cliente = cliente_repository.criar(session, f"Cliente Lote {i}", "1190000", "l@l.com")
        agendamento = agendamento_service.criar_agendamento(
            session,
            cliente.id,
            cadastro_basico["funcionario_a_id"],
            cadastro_basico["servico_id"],
            date(2026, 8, 10),
            hora,
        )
        ids.append(agendamento.id)

    alterados = agendamento_service.alterar_status_em_lote(
        session, ids, "concluido", agora=datetime(2026, 8, 10, 12, 0)
    )

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


def test_concluir_grava_forma_pagamento(session, cadastro_basico):
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    agendamento_service.alterar_status(
        session, agendamento.id, "concluido",
        agora=datetime(2026, 8, 10, 11, 0), forma_pagamento="pix",
    )
    assert agendamento.forma_pagamento == "pix"


def test_forma_pagamento_invalida_levanta_erro(session, cadastro_basico):
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    with pytest.raises(ValueError):
        agendamento_service.alterar_status(
            session, agendamento.id, "concluido",
            agora=datetime(2026, 8, 10, 11, 0), forma_pagamento="cheque",
        )


def test_reabrir_limpa_forma_pagamento(session, cadastro_basico):
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
    )
    agendamento_service.alterar_status(
        session, agendamento.id, "concluido",
        agora=datetime(2026, 8, 10, 11, 0), forma_pagamento="dinheiro",
    )
    agendamento_service.alterar_status(session, agendamento.id, "agendado")
    assert agendamento.forma_pagamento is None


def test_avulso_grava_forma_pagamento(session, cadastro_basico):
    agendamento = agendamento_service.lancar_atendimento_avulso(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        agora=datetime(2026, 8, 10, 14, 30),
        forma_pagamento="cartao_credito",
    )
    assert agendamento.forma_pagamento == "cartao_credito"


def test_agendamento_duplicado_bloqueia(session, cadastro_basico):
    agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
        hoje=date(2026, 8, 1),
    )
    with pytest.raises(agendamento_service.AgendamentoDuplicadoError):
        agendamento_service.criar_agendamento(
            session,
            cadastro_basico["cliente_id"],
            cadastro_basico["funcionario_a_id"],
            cadastro_basico["servico_id"],
            date(2026, 8, 12),
            "11:00",
            hoje=date(2026, 8, 1),
        )


def test_apos_cancelar_pode_agendar_de_novo(session, cadastro_basico):
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 10),
        "10:00",
        hoje=date(2026, 8, 1),
    )
    agendamento_service.alterar_status(session, agendamento.id, "cancelado")
    novo = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 12),
        "11:00",
        hoje=date(2026, 8, 1),
    )
    assert novo.id is not None


def _cancelar_n_vezes(session, cadastro, n):
    for i in range(n):
        agendamento = agendamento_service.criar_agendamento(
            session,
            cadastro["cliente_id"],
            cadastro["funcionario_a_id"],
            cadastro["servico_id"],
            date(2026, 8, 10 + i),
            "10:00",
            hoje=date(2026, 8, 1),
        )
        agendamento_service.alterar_status(session, agendamento.id, "cancelado")


def test_blacklist_apos_3_cancelamentos(session, cadastro_basico):
    _cancelar_n_vezes(session, cadastro_basico, 2)
    cliente = cliente_repository.obter_por_id(session, cadastro_basico["cliente_id"])
    assert not cliente.bloqueado  # 2 ainda não bloqueia

    _cancelar_n_vezes(session, cadastro_basico, 1)
    assert cliente.bloqueado  # 3ª falta liga a flag

    with pytest.raises(agendamento_service.ClienteBloqueadoError):
        agendamento_service.criar_agendamento(
            session,
            cadastro_basico["cliente_id"],
            cadastro_basico["funcionario_a_id"],
            cadastro_basico["servico_id"],
            date(2026, 8, 20),
            "10:00",
            hoje=date(2026, 8, 1),
        )


def test_blacklist_com_nao_compareceu(session, cadastro_basico):
    for i in range(3):
        agendamento = agendamento_service.criar_agendamento(
            session,
            cadastro_basico["cliente_id"],
            cadastro_basico["funcionario_a_id"],
            cadastro_basico["servico_id"],
            date(2026, 8, 10 + i),
            "10:00",
            hoje=date(2026, 8, 1),
        )
        agendamento_service.alterar_status(session, agendamento.id, "nao_compareceu")
    cliente = cliente_repository.obter_por_id(session, cadastro_basico["cliente_id"])
    assert cliente.bloqueado


def test_desbloquear_cliente_permite_agendar(session, cadastro_basico):
    _cancelar_n_vezes(session, cadastro_basico, 3)
    cliente_repository.definir_bloqueio(session, cadastro_basico["cliente_id"], False)
    agendamento = agendamento_service.criar_agendamento(
        session,
        cadastro_basico["cliente_id"],
        cadastro_basico["funcionario_a_id"],
        cadastro_basico["servico_id"],
        date(2026, 8, 20),
        "10:00",
        hoje=date(2026, 8, 1),
    )
    assert agendamento.id is not None


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
