from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import Funcionario, PagamentoFuncionario


def criar(
    session: Session,
    funcionario_id: int,
    data_pagamento: date,
    periodo_inicio: date,
    periodo_fim: date,
    comissao_base: float,
    descontos_abatidos: float,
    valor_pago: float,
    observacao: Optional[str] = None,
) -> PagamentoFuncionario:
    pagamento = PagamentoFuncionario(
        funcionario_id=funcionario_id,
        data_pagamento=data_pagamento,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        comissao_base=comissao_base,
        descontos_abatidos=descontos_abatidos,
        valor_pago=valor_pago,
        observacao=observacao,
    )
    session.add(pagamento)
    session.commit()
    return pagamento


def listar_por_periodo(
    session: Session, inicio: date, fim: date, funcionario_id: Optional[int] = None
):
    """Pagamentos cuja data de pagamento cai no período, com nome do funcionário."""
    stmt = (
        select(
            PagamentoFuncionario.id,
            Funcionario.nome.label("funcionario"),
            PagamentoFuncionario.data_pagamento,
            PagamentoFuncionario.periodo_inicio,
            PagamentoFuncionario.periodo_fim,
            PagamentoFuncionario.comissao_base,
            PagamentoFuncionario.descontos_abatidos,
            PagamentoFuncionario.valor_pago,
            PagamentoFuncionario.observacao,
        )
        .join(Funcionario, PagamentoFuncionario.funcionario_id == Funcionario.id)
        .where(PagamentoFuncionario.data_pagamento.between(inicio, fim))
        .order_by(PagamentoFuncionario.data_pagamento.desc(), PagamentoFuncionario.id.desc())
    )
    if funcionario_id is not None:
        stmt = stmt.where(PagamentoFuncionario.funcionario_id == funcionario_id)
    return session.execute(stmt).all()


def total_pago_por_funcionario(session: Session, inicio: date, fim: date) -> dict[int, float]:
    stmt = (
        select(
            PagamentoFuncionario.funcionario_id,
            func.coalesce(func.sum(PagamentoFuncionario.valor_pago), 0.0),
        )
        .where(PagamentoFuncionario.data_pagamento.between(inicio, fim))
        .group_by(PagamentoFuncionario.funcionario_id)
    )
    return {funcionario_id: total for funcionario_id, total in session.execute(stmt).all()}


def total_abatido_por_funcionario(session: Session, inicio: date, fim: date) -> dict[int, float]:
    """Vales abatidos dentro de acertos do período (parte da comissão já quitada sem dinheiro novo)."""
    stmt = (
        select(
            PagamentoFuncionario.funcionario_id,
            func.coalesce(func.sum(PagamentoFuncionario.descontos_abatidos), 0.0),
        )
        .where(PagamentoFuncionario.data_pagamento.between(inicio, fim))
        .group_by(PagamentoFuncionario.funcionario_id)
    )
    return {funcionario_id: total for funcionario_id, total in session.execute(stmt).all()}


def obter_por_id(session: Session, pagamento_id: int) -> Optional[PagamentoFuncionario]:
    return session.get(PagamentoFuncionario, pagamento_id)
