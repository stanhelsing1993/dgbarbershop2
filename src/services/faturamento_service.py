from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import (
    FORMA_NAO_INFORMADA,
    FORMAS_PAGAMENTO,
    PERCENTUAL_COMISSAO_PADRAO,
    STATUS_CONCLUIDO,
    Agendamento,
    Funcionario,
    Servico,
)
from src.repositories import adiantamento_repository, funcionario_repository, pagamento_repository


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


def receita_por_forma_pagamento(
    session: Session, data_inicio: Optional[date] = None, data_fim: Optional[date] = None
) -> list[dict]:
    """Receita e atendimentos concluídos agrupados por forma de pagamento."""
    stmt = (
        select(
            Agendamento.forma_pagamento,
            func.coalesce(func.sum(Servico.preco), 0.0).label("receita"),
            func.count(Agendamento.id).label("atendimentos"),
        )
        .select_from(Agendamento)
        .join(Servico, Agendamento.servico_id == Servico.id)
        .where(Agendamento.status == STATUS_CONCLUIDO)
        .group_by(Agendamento.forma_pagamento)
    )
    if data_inicio is not None and data_fim is not None:
        stmt = stmt.where(Agendamento.data.between(data_inicio, data_fim))
    linhas = session.execute(stmt).all()
    resultado = [
        {
            "forma": FORMAS_PAGAMENTO.get(forma, FORMA_NAO_INFORMADA),
            "receita": round(receita, 2),
            "atendimentos": atendimentos,
        }
        for forma, receita, atendimentos in linhas
    ]
    return sorted(resultado, key=lambda item: item["receita"], reverse=True)


def calcular_repasse(
    rows,
    percentuais: Optional[dict[int, float]] = None,
    percentual_padrao: float = PERCENTUAL_COMISSAO_PADRAO,
) -> list[dict]:
    """Recebe as linhas de faturamento_por_periodo e calcula o repasse funcionário/loja.

    `percentuais` mapeia funcionario_id -> fração da comissão; quem não estiver
    no mapa usa o percentual padrão.
    """
    percentuais = percentuais or {}
    resultado = []
    for row in rows:
        preco = row.preco_servico
        percentual = percentuais.get(row.funcionario_id, percentual_padrao)
        resultado.append(
            {
                "funcionario_id": row.funcionario_id,
                "funcionario": row.funcionario,
                "servico": row.servico,
                "preco_servico": preco,
                "data": row.data,
                "percentual": percentual,
                "repasse_funcionario": round(preco * percentual, 2),
                "repasse_loja": round(preco * (1 - percentual), 2),
            }
        )
    return resultado


def relatorio_pagamentos(session: Session, data_inicio: date, data_fim: date) -> list[dict]:
    """Relatório completo de pagamentos por funcionário no período.

    Receita bruta gerada, comissão pela % cadastrada, descontos (vales ainda
    pendentes de abatimento, de qualquer data até o fim do período), o que já
    foi pago em acertos no período e o líquido restante a pagar.
    """
    linhas = faturamento_por_periodo(session, data_inicio, data_fim)
    percentuais = funcionario_repository.percentuais_por_funcionario(session)
    nomes = {f.id: f.nome for f in funcionario_repository.listar(session)}
    vales_pendentes = adiantamento_repository.total_pendente_por_funcionario(session, ate=data_fim)
    pagos = pagamento_repository.total_pago_por_funcionario(session, data_inicio, data_fim)
    abatidos = pagamento_repository.total_abatido_por_funcionario(session, data_inicio, data_fim)

    receitas: dict[int, dict] = {}
    for row in linhas:
        item = receitas.setdefault(row.funcionario_id, {"atendimentos": 0, "receita_bruta": 0.0})
        item["atendimentos"] += 1
        item["receita_bruta"] += row.preco_servico

    resultado = []
    ids = sorted(set(receitas) | set(vales_pendentes) | set(pagos), key=lambda i: nomes.get(i, ""))
    for funcionario_id in ids:
        receita = receitas.get(funcionario_id, {}).get("receita_bruta", 0.0)
        percentual = percentuais.get(funcionario_id, PERCENTUAL_COMISSAO_PADRAO)
        comissao = round(receita * percentual, 2)
        descontos = round(vales_pendentes.get(funcionario_id, 0.0), 2)
        pago = round(pagos.get(funcionario_id, 0.0), 2)
        # O que já foi quitado em acertos = dinheiro pago + vales abatidos neles.
        quitado = round(pago + abatidos.get(funcionario_id, 0.0), 2)
        resultado.append(
            {
                "funcionario_id": funcionario_id,
                "funcionario": nomes.get(funcionario_id, f"Funcionário #{funcionario_id}"),
                "atendimentos": receitas.get(funcionario_id, {}).get("atendimentos", 0),
                "receita_bruta": round(receita, 2),
                "percentual": percentual,
                "comissao": comissao,
                "descontos": descontos,
                "pago": pago,
                "liquido": round(comissao - descontos - quitado, 2),
            }
        )
    return resultado


def resumo_financeiro(session: Session, data_inicio: date, data_fim: date) -> dict:
    """Visão da loja no período: bruto, custo com funcionários e o que sobra.

    Os adiantamentos não reduzem a receita da loja — são antecipação da comissão —
    mas reduzem o valor líquido a desembolsar no acerto.
    """
    pagamentos = relatorio_pagamentos(session, data_inicio, data_fim)
    receita_bruta = round(sum(p["receita_bruta"] for p in pagamentos), 2)
    comissoes = round(sum(p["comissao"] for p in pagamentos), 2)
    descontos = round(sum(p["descontos"] for p in pagamentos), 2)
    pagos = round(sum(p["pago"] for p in pagamentos), 2)
    return {
        "receita_bruta": receita_bruta,
        "pagamentos_funcionarios": comissoes,
        "descontos": descontos,
        "pagos": pagos,
        "liquido_a_pagar": round(sum(p["liquido"] for p in pagamentos), 2),
        "receita_loja": round(receita_bruta - comissoes, 2),
    }
