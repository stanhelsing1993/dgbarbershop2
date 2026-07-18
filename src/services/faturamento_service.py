from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import STATUS_CONCLUIDO, Agendamento, Funcionario, Servico


def faturamento_total(session: Session) -> float:
    stmt = (
        select(func.coalesce(func.sum(Servico.preco), 0.0))
        .select_from(Agendamento)
        .join(Servico, Agendamento.servico_id == Servico.id)
        .where(Agendamento.status == STATUS_CONCLUIDO)
    )
    return session.scalar(stmt) or 0.0


def faturamento_por_funcionario(session: Session):
    stmt = (
        select(
            Funcionario.id.label("funcionario_id"),
            Funcionario.nome.label("funcionario"),
            func.coalesce(func.sum(Servico.preco), 0.0).label("faturamento"),
            func.count(Agendamento.id).label("atendimentos"),
        )
        .select_from(Agendamento)
        .join(Servico, Agendamento.servico_id == Servico.id)
        .join(Funcionario, Agendamento.funcionario_id == Funcionario.id)
        .where(Agendamento.status == STATUS_CONCLUIDO)
        .group_by(Funcionario.id)
        .order_by(func.sum(Servico.preco).desc())
    )
    return session.execute(stmt).all()


def faturamento_por_periodo(
    session: Session,
    data_inicio: date,
    data_fim: date,
    funcionario_nome: Optional[str] = None,
):
    stmt = (
        select(
            Funcionario.id.label("funcionario_id"),
            Funcionario.nome.label("funcionario"),
            Servico.nome.label("servico"),
            Servico.preco.label("preco_servico"),
            Agendamento.data,
        )
        .select_from(Agendamento)
        .join(Servico, Agendamento.servico_id == Servico.id)
        .join(Funcionario, Agendamento.funcionario_id == Funcionario.id)
        .where(Agendamento.data.between(data_inicio, data_fim))
        .where(Agendamento.status == STATUS_CONCLUIDO)
    )
    if funcionario_nome:
        stmt = stmt.where(Funcionario.nome == funcionario_nome)
    return session.execute(stmt).all()


def faturamento_por_mes(session: Session):
    mes_expr = func.strftime("%m-%Y", Agendamento.data).label("mes")
    stmt = (
        select(mes_expr, func.coalesce(func.sum(Servico.preco), 0.0).label("faturamento"))
        .select_from(Agendamento)
        .join(Servico, Agendamento.servico_id == Servico.id)
        .where(Agendamento.status == STATUS_CONCLUIDO)
        .group_by(mes_expr)
        .order_by(mes_expr.desc())
    )
    return session.execute(stmt).all()


def faturamento_por_ano(session: Session):
    ano_expr = func.strftime("%Y", Agendamento.data).label("ano")
    stmt = (
        select(ano_expr, func.coalesce(func.sum(Servico.preco), 0.0).label("faturamento"))
        .select_from(Agendamento)
        .join(Servico, Agendamento.servico_id == Servico.id)
        .where(Agendamento.status == STATUS_CONCLUIDO)
        .group_by(ano_expr)
        .order_by(ano_expr.desc())
    )
    return session.execute(stmt).all()


def calcular_repasse(rows, percentual: float = 0.5) -> list[dict]:
    """Recebe as linhas de faturamento_por_periodo e calcula o repasse funcionário/loja."""
    resultado = []
    for row in rows:
        preco = row.preco_servico
        resultado.append(
            {
                "funcionario_id": row.funcionario_id,
                "funcionario": row.funcionario,
                "servico": row.servico,
                "preco_servico": preco,
                "data": row.data,
                "repasse_funcionario": round(preco * percentual, 2),
                "repasse_loja": round(preco * (1 - percentual), 2),
            }
        )
    return resultado
