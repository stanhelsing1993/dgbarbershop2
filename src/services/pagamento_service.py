from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import (
    STATUS_CONCLUIDO,
    TIPO_SAIDA,
    Agendamento,
    PagamentoFuncionario,
    Servico,
)
from src.repositories import (
    adiantamento_repository,
    caixa_repository,
    funcionario_repository,
    pagamento_repository,
)


class PagamentoError(Exception):
    pass


def comissao_do_periodo(session: Session, funcionario_id: int, inicio: date, fim: date) -> float:
    funcionario = funcionario_repository.obter_por_id(session, funcionario_id)
    if funcionario is None:
        return 0.0
    stmt = (
        select(func.coalesce(func.sum(Servico.preco), 0.0))
        .select_from(Agendamento)
        .join(Servico, Agendamento.servico_id == Servico.id)
        .where(
            Agendamento.funcionario_id == funcionario_id,
            Agendamento.status == STATUS_CONCLUIDO,
            Agendamento.data.between(inicio, fim),
        )
    )
    receita = session.scalar(stmt) or 0.0
    return round(receita * funcionario.percentual_comissao, 2)


def previa_acerto(
    session: Session, funcionario_id: int, periodo_inicio: date, periodo_fim: date
) -> dict:
    """Prévia do acerto: comissão do período e vales pendentes (de qualquer data) a abater."""
    comissao = comissao_do_periodo(session, funcionario_id, periodo_inicio, periodo_fim)
    vales = adiantamento_repository.listar_pendentes(session, funcionario_id, ate=periodo_fim)
    total_vales = round(sum(v.valor for v in vales), 2)
    return {
        "comissao": comissao,
        "vales_pendentes": vales,
        "total_vales": total_vales,
        "liquido": round(comissao - total_vales, 2),
    }


def registrar_pagamento(
    session: Session,
    funcionario_id: int,
    periodo_inicio: date,
    periodo_fim: date,
    data_pagamento: date,
    valor_pago: Optional[float] = None,
    observacao: Optional[str] = None,
    lancar_no_caixa: bool = False,
) -> PagamentoFuncionario:
    """Registra o acerto: grava o pagamento e marca os vales pendentes como abatidos.

    Se `lancar_no_caixa` for True, o valor pago também entra como saída no
    movimento de caixa do dia do pagamento.
    """
    if periodo_inicio > periodo_fim:
        raise PagamentoError("O início do período não pode ser depois do fim.")
    funcionario = funcionario_repository.obter_por_id(session, funcionario_id)
    if funcionario is None:
        raise PagamentoError("Funcionário não encontrado.")

    previa = previa_acerto(session, funcionario_id, periodo_inicio, periodo_fim)
    if previa["liquido"] < 0:
        raise PagamentoError(
            f"Os vales pendentes ({previa['total_vales']:.2f}) excedem a comissão do período "
            f"({previa['comissao']:.2f}). Amplie o período ou aguarde novas comissões."
        )
    if valor_pago is None:
        valor_pago = previa["liquido"]
    if valor_pago < 0:
        raise PagamentoError("O valor pago não pode ser negativo.")

    pagamento = pagamento_repository.criar(
        session,
        funcionario_id=funcionario_id,
        data_pagamento=data_pagamento,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        comissao_base=previa["comissao"],
        descontos_abatidos=previa["total_vales"],
        valor_pago=round(valor_pago, 2),
        observacao=observacao,
    )
    adiantamento_repository.marcar_abatidos(
        session, [v.id for v in previa["vales_pendentes"]], pagamento.id
    )
    if lancar_no_caixa and valor_pago > 0:
        caixa_repository.criar_movimento(
            session,
            data_pagamento,
            TIPO_SAIDA,
            round(valor_pago, 2),
            f"Pagamento (acerto) — {funcionario.nome}",
        )
    return pagamento
