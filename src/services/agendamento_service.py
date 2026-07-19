from datetime import date, datetime, timedelta
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from src.config import DURACAO_SLOT_MINUTOS, HORARIO_ABERTURA, HORARIO_FECHAMENTO
from src.database.models import (
    FORMAS_PAGAMENTO,
    STATUS_AGENDADO,
    STATUS_CANCELADO,
    STATUS_CONCLUIDO,
    STATUS_NAO_COMPARECEU,
    Agendamento,
)
from src.repositories import agendamento_repository, cliente_repository

STATUS_LABELS = {
    STATUS_AGENDADO: "Agendado",
    STATUS_CONCLUIDO: "Concluído",
    STATUS_CANCELADO: "Cancelado",
    STATUS_NAO_COMPARECEU: "Não compareceu",
}


class ConflitoDeHorarioError(Exception):
    pass


class ClienteBloqueadoError(Exception):
    pass


class AgendamentoDuplicadoError(Exception):
    pass


# Clientes agendam com no mínimo 1 dia de antecedência; o mesmo dia é atendido
# apenas via encaixe (lancar_atendimento_avulso), que é restrito à equipe.
ANTECEDENCIA_MINIMA_DIAS = 1

# Cancelamentos + faltas a partir dos quais o cliente entra na blacklist.
LIMITE_FALTAS_BLACKLIST = 3

MENSAGEM_COMPROMISSO = (
    "🕒 **Compromisso com o seu horário:** chegue com **10 minutos de antecedência**. "
    "O horário é reservado só para você — se não puder comparecer, **cancele com antecedência** "
    "para liberar a vaga a outro cliente. Cancelamentos e faltas repetidas (3x) bloqueiam novos agendamentos."
)


def _validar_forma_pagamento(forma_pagamento: Optional[str]) -> None:
    if forma_pagamento is not None and forma_pagamento not in FORMAS_PAGAMENTO:
        raise ValueError(f"Forma de pagamento inválida: {forma_pagamento}")


def _gerar_grade_horarios() -> list[str]:
    inicio = datetime.strptime(HORARIO_ABERTURA, "%H:%M")
    fim = datetime.strptime(HORARIO_FECHAMENTO, "%H:%M")
    horarios = []
    atual = inicio
    # O último slot começa antes do fechamento: um atendimento às 19:00
    # terminaria com a barbearia fechada.
    while atual < fim:
        horarios.append(atual.strftime("%H:%M"))
        atual += timedelta(minutes=DURACAO_SLOT_MINUTOS)
    return horarios


def data_minima_agendamento(hoje: Optional[date] = None) -> date:
    hoje = hoje or date.today()
    return hoje + timedelta(days=ANTECEDENCIA_MINIMA_DIAS)


def horarios_disponiveis(
    session: Session, funcionario_id: int, dia: date, agora: Optional[datetime] = None
) -> list[str]:
    agora = agora or datetime.now()
    if dia < data_minima_agendamento(agora.date()):
        return []
    ocupados = agendamento_repository.listar_horarios_ocupados(session, funcionario_id, dia)
    return [h for h in _gerar_grade_horarios() if h not in ocupados]


def criar_agendamento(
    session: Session,
    cliente_id: int,
    funcionario_id: int,
    servico_id: int,
    dia: date,
    hora: str,
    hoje: Optional[date] = None,
) -> Agendamento:
    if dia < data_minima_agendamento(hoje):
        raise ValueError(
            f"Agendamentos devem ser feitos com pelo menos {ANTECEDENCIA_MINIMA_DIAS} dia de antecedência."
        )
    cliente = cliente_repository.obter_por_id(session, cliente_id)
    if cliente is not None and cliente.bloqueado:
        raise ClienteBloqueadoError(
            "Este cliente está bloqueado para novos agendamentos por excesso de "
            "cancelamentos/faltas. Procure a equipe da barbearia para regularizar."
        )
    ativos = agendamento_repository.listar_ativos_do_cliente(
        session, cliente_id, a_partir_de=hoje or date.today()
    )
    if ativos:
        existente = ativos[0]
        raise AgendamentoDuplicadoError(
            f"Este cliente já tem um agendamento ativo em "
            f"{existente.data.strftime('%d/%m/%Y')} às {existente.hora}. "
            "Conclua ou cancele o agendamento atual antes de marcar outro."
        )
    ocupados = agendamento_repository.listar_horarios_ocupados(session, funcionario_id, dia)
    if hora in ocupados:
        raise ConflitoDeHorarioError(
            f"O horário {hora} já está ocupado para este funcionário nesta data."
        )
    return agendamento_repository.criar(session, cliente_id, funcionario_id, servico_id, dia, hora)


def lancar_atendimento_avulso(
    session: Session,
    cliente_id: int,
    funcionario_id: int,
    servico_id: int,
    dia: Optional[date] = None,
    hora: Optional[str] = None,
    agora: Optional[datetime] = None,
    forma_pagamento: Optional[str] = None,
) -> Agendamento:
    """Registra um atendimento de encaixe (sem agendamento prévio).

    O serviço já aconteceu, então entra direto como concluído — sem checagem
    de grade ou conflito — e passa a contar em receita, repasse e métricas.
    """
    _validar_forma_pagamento(forma_pagamento)
    agora = agora or datetime.now()
    dia = dia or agora.date()
    hora = hora or agora.strftime("%H:%M")
    if dia > agora.date():
        raise ValueError("Um atendimento avulso não pode ser lançado em data futura.")
    return agendamento_repository.criar(
        session,
        cliente_id,
        funcionario_id,
        servico_id,
        dia,
        hora,
        status=STATUS_CONCLUIDO,
        forma_pagamento=forma_pagamento,
    )


class ConclusaoAntecipadaError(Exception):
    pass


def _avaliar_blacklist(session: Session, agendamento_id: int) -> None:
    """Liga a flag de bloqueio quando o cliente acumula faltas/cancelamentos demais."""
    agendamento = agendamento_repository.obter_por_id(session, agendamento_id)
    if agendamento is None:
        return
    faltas = agendamento_repository.contar_faltas_do_cliente(session, agendamento.cliente_id)
    if faltas >= LIMITE_FALTAS_BLACKLIST:
        cliente_repository.definir_bloqueio(session, agendamento.cliente_id, True)


def alterar_status(
    session: Session,
    agendamento_id: int,
    status: str,
    agora: Optional[datetime] = None,
    forma_pagamento: Optional[str] = None,
) -> None:
    if status not in STATUS_LABELS:
        raise ValueError(f"Status inválido: {status}")
    _validar_forma_pagamento(forma_pagamento)
    if status == STATUS_CONCLUIDO:
        # Concluir gera receita; só pode acontecer depois do horário marcado,
        # senão o financeiro registra dinheiro de um serviço que ainda não houve.
        agendamento = agendamento_repository.obter_por_id(session, agendamento_id)
        if agendamento is not None:
            agora = agora or datetime.now()
            inicio = datetime.combine(
                agendamento.data, datetime.strptime(agendamento.hora, "%H:%M").time()
            )
            if inicio > agora:
                raise ConclusaoAntecipadaError(
                    f"Não é possível concluir antes do horário agendado "
                    f"({agendamento.data.strftime('%d/%m/%Y')} às {agendamento.hora})."
                )
    if status == STATUS_AGENDADO:
        # Reativar um agendamento exige que o horário ainda esteja livre —
        # após um cancelamento, outro cliente pode ter tomado o slot.
        agendamento = agendamento_repository.obter_por_id(session, agendamento_id)
        if agendamento is not None:
            ocupados = agendamento_repository.listar_horarios_ocupados(
                session, agendamento.funcionario_id, agendamento.data, ignorar_id=agendamento.id
            )
            if agendamento.hora in ocupados:
                raise ConflitoDeHorarioError(
                    f"Não é possível reativar: o horário {agendamento.hora} já foi ocupado por outro agendamento."
                )
    agendamento_repository.atualizar_status(session, agendamento_id, status, forma_pagamento)
    if status in (STATUS_CANCELADO, STATUS_NAO_COMPARECEU):
        _avaliar_blacklist(session, agendamento_id)


def alterar_status_em_lote(
    session: Session,
    agendamento_ids: Iterable[int],
    status: str,
    agora: Optional[datetime] = None,
    forma_pagamento: Optional[str] = None,
) -> int:
    """Aplica o mesmo status a vários agendamentos. Retorna quantos foram alterados."""
    alterados = 0
    for agendamento_id in agendamento_ids:
        alterar_status(session, agendamento_id, status, agora=agora, forma_pagamento=forma_pagamento)
        alterados += 1
    return alterados
