from datetime import date, datetime, timedelta
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from src.config import DURACAO_SLOT_MINUTOS, HORARIO_ABERTURA, HORARIO_FECHAMENTO
from src.database.models import (
    STATUS_AGENDADO,
    STATUS_CANCELADO,
    STATUS_CONCLUIDO,
    STATUS_NAO_COMPARECEU,
    Agendamento,
)
from src.repositories import agendamento_repository

STATUS_LABELS = {
    STATUS_AGENDADO: "Agendado",
    STATUS_CONCLUIDO: "Concluído",
    STATUS_CANCELADO: "Cancelado",
    STATUS_NAO_COMPARECEU: "Não compareceu",
}


class ConflitoDeHorarioError(Exception):
    pass


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


def horarios_disponiveis(
    session: Session, funcionario_id: int, dia: date, agora: Optional[datetime] = None
) -> list[str]:
    agora = agora or datetime.now()
    if dia < agora.date():
        return []
    ocupados = agendamento_repository.listar_horarios_ocupados(session, funcionario_id, dia)
    grade = [h for h in _gerar_grade_horarios() if h not in ocupados]
    if dia == agora.date():
        limite = agora.strftime("%H:%M")
        grade = [h for h in grade if h > limite]
    return grade


def criar_agendamento(
    session: Session,
    cliente_id: int,
    funcionario_id: int,
    servico_id: int,
    dia: date,
    hora: str,
) -> Agendamento:
    if dia < date.today():
        raise ValueError("Não é possível agendar em uma data passada.")
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
) -> Agendamento:
    """Registra um atendimento de encaixe (sem agendamento prévio).

    O serviço já aconteceu, então entra direto como concluído — sem checagem
    de grade ou conflito — e passa a contar em receita, repasse e métricas.
    """
    agora = agora or datetime.now()
    dia = dia or agora.date()
    hora = hora or agora.strftime("%H:%M")
    if dia > agora.date():
        raise ValueError("Um atendimento avulso não pode ser lançado em data futura.")
    return agendamento_repository.criar(
        session, cliente_id, funcionario_id, servico_id, dia, hora, status=STATUS_CONCLUIDO
    )


def alterar_status(session: Session, agendamento_id: int, status: str) -> None:
    if status not in STATUS_LABELS:
        raise ValueError(f"Status inválido: {status}")
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
    agendamento_repository.atualizar_status(session, agendamento_id, status)


def alterar_status_em_lote(session: Session, agendamento_ids: Iterable[int], status: str) -> int:
    """Aplica o mesmo status a vários agendamentos. Retorna quantos foram alterados."""
    alterados = 0
    for agendamento_id in agendamento_ids:
        alterar_status(session, agendamento_id, status)
        alterados += 1
    return alterados
