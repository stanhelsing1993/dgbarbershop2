from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import Adiantamento, Funcionario


def criar(
    session: Session, funcionario_id: int, dia: date, valor: float, descricao: Optional[str] = None
) -> Adiantamento:
    adiantamento = Adiantamento(funcionario_id=funcionario_id, data=dia, valor=valor, descricao=descricao)
    session.add(adiantamento)
    session.commit()
    return adiantamento


def listar_por_periodo(session: Session, inicio: date, fim: date, funcionario_id: Optional[int] = None):
    stmt = (
        select(
            Adiantamento.id,
            Funcionario.nome.label("funcionario"),
            Adiantamento.data,
            Adiantamento.valor,
            Adiantamento.descricao,
            Adiantamento.pagamento_id,
        )
        .join(Funcionario, Adiantamento.funcionario_id == Funcionario.id)
        .where(Adiantamento.data.between(inicio, fim))
        .order_by(Adiantamento.data, Adiantamento.id)
    )
    if funcionario_id is not None:
        stmt = stmt.where(Adiantamento.funcionario_id == funcionario_id)
    return session.execute(stmt).all()


def listar_pendentes(session: Session, funcionario_id: int, ate: date) -> list[Adiantamento]:
    """Vales ainda não abatidos em nenhum acerto, até a data informada."""
    stmt = (
        select(Adiantamento)
        .where(
            Adiantamento.funcionario_id == funcionario_id,
            Adiantamento.pagamento_id.is_(None),
            Adiantamento.data <= ate,
        )
        .order_by(Adiantamento.data, Adiantamento.id)
    )
    return list(session.scalars(stmt))


def total_pendente_por_funcionario(session: Session, ate: date) -> dict[int, float]:
    stmt = (
        select(Adiantamento.funcionario_id, func.coalesce(func.sum(Adiantamento.valor), 0.0))
        .where(Adiantamento.pagamento_id.is_(None), Adiantamento.data <= ate)
        .group_by(Adiantamento.funcionario_id)
    )
    return {funcionario_id: total for funcionario_id, total in session.execute(stmt).all()}


def marcar_abatidos(session: Session, adiantamento_ids: list[int], pagamento_id: int) -> None:
    for adiantamento_id in adiantamento_ids:
        adiantamento = session.get(Adiantamento, adiantamento_id)
        if adiantamento is not None:
            adiantamento.pagamento_id = pagamento_id
    session.commit()


def total_do_dia(session: Session, dia: date) -> float:
    stmt = select(func.coalesce(func.sum(Adiantamento.valor), 0.0)).where(Adiantamento.data == dia)
    return session.scalar(stmt) or 0.0


def total_por_funcionario_no_periodo(session: Session, inicio: date, fim: date) -> dict[int, float]:
    stmt = (
        select(Adiantamento.funcionario_id, func.coalesce(func.sum(Adiantamento.valor), 0.0))
        .where(Adiantamento.data.between(inicio, fim))
        .group_by(Adiantamento.funcionario_id)
    )
    return {funcionario_id: total for funcionario_id, total in session.execute(stmt).all()}


def excluir(session: Session, adiantamento_id: int) -> None:
    adiantamento = session.get(Adiantamento, adiantamento_id)
    if adiantamento is not None:
        session.delete(adiantamento)
        session.commit()
