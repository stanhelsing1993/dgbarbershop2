from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import AberturaCaixa, FechamentoCaixa, MovimentoCaixa


def obter_abertura(session: Session, dia: date) -> Optional[AberturaCaixa]:
    stmt = select(AberturaCaixa).where(AberturaCaixa.data == dia)
    return session.scalars(stmt).first()


def criar_abertura(
    session: Session, dia: date, valor_inicial: float, hora: str, aberto_por: Optional[str] = None
) -> AberturaCaixa:
    abertura = AberturaCaixa(data=dia, valor_inicial=valor_inicial, hora=hora, aberto_por=aberto_por)
    session.add(abertura)
    session.commit()
    return abertura


def listar_aberturas(session: Session, inicio: date, fim: date) -> list[AberturaCaixa]:
    stmt = (
        select(AberturaCaixa)
        .where(AberturaCaixa.data.between(inicio, fim))
        .order_by(AberturaCaixa.data)
    )
    return list(session.scalars(stmt))


def criar_movimento(session: Session, dia: date, tipo: str, valor: float, descricao: str) -> MovimentoCaixa:
    movimento = MovimentoCaixa(data=dia, tipo=tipo, valor=valor, descricao=descricao)
    session.add(movimento)
    session.commit()
    return movimento


def listar_movimentos(session: Session, dia: date) -> list[MovimentoCaixa]:
    stmt = select(MovimentoCaixa).where(MovimentoCaixa.data == dia).order_by(MovimentoCaixa.id)
    return list(session.scalars(stmt))


def total_movimentos(session: Session, dia: date, tipo: str) -> float:
    stmt = select(func.coalesce(func.sum(MovimentoCaixa.valor), 0.0)).where(
        MovimentoCaixa.data == dia, MovimentoCaixa.tipo == tipo
    )
    return session.scalar(stmt) or 0.0


def excluir_movimento(session: Session, movimento_id: int) -> None:
    movimento = session.get(MovimentoCaixa, movimento_id)
    if movimento is not None:
        session.delete(movimento)
        session.commit()


def obter_fechamento(session: Session, dia: date) -> Optional[FechamentoCaixa]:
    stmt = select(FechamentoCaixa).where(FechamentoCaixa.data == dia)
    return session.scalars(stmt).first()


def criar_fechamento(
    session: Session,
    dia: date,
    receita_servicos: float,
    entradas: float,
    saidas: float,
    adiantamentos: float,
    saldo: float,
    observacao: Optional[str] = None,
) -> FechamentoCaixa:
    fechamento = FechamentoCaixa(
        data=dia,
        receita_servicos=receita_servicos,
        entradas=entradas,
        saidas=saidas,
        adiantamentos=adiantamentos,
        saldo=saldo,
        observacao=observacao,
    )
    session.add(fechamento)
    session.commit()
    return fechamento


def listar_fechamentos(session: Session, inicio: date, fim: date) -> list[FechamentoCaixa]:
    stmt = (
        select(FechamentoCaixa)
        .where(FechamentoCaixa.data.between(inicio, fim))
        .order_by(FechamentoCaixa.data)
    )
    return list(session.scalars(stmt))
