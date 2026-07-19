from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Agendamento, Cliente, Funcionario, Servico


def listar_detalhado(session: Session, a_partir_de: Optional[date] = None, ate: Optional[date] = None):
    """Retorna linhas já com nomes de cliente/funcionário/serviço (sem expor objetos ORM presos à sessão)."""
    stmt = (
        select(
            Agendamento.id,
            Cliente.nome.label("cliente"),
            Funcionario.nome.label("funcionario"),
            Servico.nome.label("servico"),
            Servico.preco.label("preco"),
            Agendamento.data,
            Agendamento.hora,
            Agendamento.status,
            Agendamento.forma_pagamento,
        )
        .join(Cliente, Agendamento.cliente_id == Cliente.id)
        .join(Funcionario, Agendamento.funcionario_id == Funcionario.id)
        .join(Servico, Agendamento.servico_id == Servico.id)
        .order_by(Agendamento.data, Agendamento.hora)
    )
    if a_partir_de is not None:
        stmt = stmt.where(Agendamento.data >= a_partir_de)
    if ate is not None:
        stmt = stmt.where(Agendamento.data <= ate)
    return session.execute(stmt).all()


def listar_horarios_ocupados(
    session: Session, funcionario_id: int, dia: date, ignorar_id: Optional[int] = None
) -> set[str]:
    stmt = select(Agendamento.hora).where(
        Agendamento.funcionario_id == funcionario_id,
        Agendamento.data == dia,
        Agendamento.status != "cancelado",
    )
    if ignorar_id is not None:
        stmt = stmt.where(Agendamento.id != ignorar_id)
    return set(session.scalars(stmt))


def obter_por_id(session: Session, agendamento_id: int) -> Optional[Agendamento]:
    return session.get(Agendamento, agendamento_id)


def listar_ativos_do_cliente(session: Session, cliente_id: int, a_partir_de: date) -> list[Agendamento]:
    """Agendamentos futuros ainda com status 'agendado' do cliente."""
    stmt = (
        select(Agendamento)
        .where(
            Agendamento.cliente_id == cliente_id,
            Agendamento.status == "agendado",
            Agendamento.data >= a_partir_de,
        )
        .order_by(Agendamento.data, Agendamento.hora)
    )
    return list(session.scalars(stmt))


def contar_faltas_do_cliente(session: Session, cliente_id: int) -> int:
    """Total de cancelamentos + não comparecimentos do cliente (histórico completo)."""
    stmt = select(Agendamento).where(
        Agendamento.cliente_id == cliente_id,
        Agendamento.status.in_(["cancelado", "nao_compareceu"]),
    )
    return len(list(session.scalars(stmt)))


def criar(
    session: Session,
    cliente_id: int,
    funcionario_id: int,
    servico_id: int,
    dia: date,
    hora: str,
    status: str = "agendado",
    forma_pagamento: Optional[str] = None,
) -> Agendamento:
    agendamento = Agendamento(
        cliente_id=cliente_id,
        funcionario_id=funcionario_id,
        servico_id=servico_id,
        data=dia,
        hora=hora,
        status=status,
        forma_pagamento=forma_pagamento,
    )
    session.add(agendamento)
    session.commit()
    return agendamento


def atualizar(session: Session, agendamento_id: int, dia: date, hora: str, status: str) -> None:
    agendamento = session.get(Agendamento, agendamento_id)
    if agendamento is None:
        return
    agendamento.data = dia
    agendamento.hora = hora
    agendamento.status = status
    session.commit()


def atualizar_status(
    session: Session, agendamento_id: int, status: str, forma_pagamento: Optional[str] = None
) -> None:
    agendamento = session.get(Agendamento, agendamento_id)
    if agendamento is None:
        return
    agendamento.status = status
    if status == "concluido":
        agendamento.forma_pagamento = forma_pagamento
    elif status != "concluido" and agendamento.forma_pagamento is not None:
        # Reabrir/reclassificar desfaz a conclusão; a forma de pagamento deixa de valer.
        agendamento.forma_pagamento = None
    session.commit()


def excluir(session: Session, agendamento_id: int) -> None:
    agendamento = session.get(Agendamento, agendamento_id)
    if agendamento is not None:
        session.delete(agendamento)
        session.commit()
