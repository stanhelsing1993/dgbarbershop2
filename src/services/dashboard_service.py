import pandas as pd
from sqlalchemy.orm import Session

from src.database.models import STATUS_CANCELADO, STATUS_CONCLUIDO, STATUS_NAO_COMPARECEU
from src.repositories import agendamento_repository


def listar_agendamentos_detalhado(session: Session):
    """Base de dados compartilhada entre Dashboard e Faturamento: um agendamento por linha, já com nomes."""
    return agendamento_repository.listar_detalhado(session)


def calcular_metricas(df: pd.DataFrame) -> dict:
    """Métricas do RF012 sobre o DataFrame de agendamentos.

    Espera as colunas Funcionario, Servico, Preco e Status (status crus do banco).
    Receita, ticket médio e rankings consideram apenas atendimentos concluídos;
    as taxas de cancelamento/no-show são sobre o total de agendamentos.
    """
    total = len(df)
    concluidos = df[df["Status"] == STATUS_CONCLUIDO]
    receita = float(concluidos["Preco"].sum())
    por_servico = concluidos["Servico"].value_counts()
    por_barbeiro = concluidos.groupby("Funcionario")["Preco"].sum()
    return {
        "total_agendamentos": total,
        "receita": receita,
        "ticket_medio": receita / len(concluidos) if len(concluidos) else 0.0,
        "taxa_cancelamento": float((df["Status"] == STATUS_CANCELADO).mean()) if total else 0.0,
        "taxa_no_show": float((df["Status"] == STATUS_NAO_COMPARECEU).mean()) if total else 0.0,
        "servico_mais_vendido": por_servico.idxmax() if not por_servico.empty else None,
        "barbeiro_top": por_barbeiro.idxmax() if not por_barbeiro.empty else None,
    }
