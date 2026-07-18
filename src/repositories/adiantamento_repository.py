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
        )
        .join(Funcionario, Adiantamento.funcionario_id == Funcionario.id)
        .where(Adiantamento.data.between(inicio, fim))
        .order_by(Adiantamento.data, Adiantamento.id)
    )
    if funcionario_id is not None:
        stmt = stmt.where(Adiantamento.funcionario_id == funcionario_id)
    return session.execute(stmt).all()


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
