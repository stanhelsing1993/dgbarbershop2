from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import (
    PERCENTUAL_COMISSAO_PADRAO,
    STATUS_AGENDADO,
    STATUS_CANCELADO,
    STATUS_CONCLUIDO,
    STATUS_NAO_COMPARECEU,
    Meta,
)
from src.repositories import agendamento_repository, funcionario_repository
from src.services.agendamento_service import _gerar_grade_horarios

# Metas gerenciais (OKR) com valores iniciais; o gestor ajusta na página de relatórios.
METAS_PADRAO = {
    "receita_mensal": 10000.0,
    "atendimentos_mensais": 100.0,
    "ticket_medio": 50.0,
    "taxa_no_show_max": 10.0,  # em %
}

METAS_LABELS = {
    "receita_mensal": "Receita do período (R$)",
    "atendimentos_mensais": "Atendimentos concluídos",
    "ticket_medio": "Ticket médio (R$)",
    "taxa_no_show_max": "Taxa máxima de no-show (%)",
}


def kpis(session: Session, inicio: date, fim: date) -> dict:
    """Indicadores do período para o painel gerencial."""
    linhas = agendamento_repository.listar_detalhado(session, a_partir_de=inicio, ate=fim)
    percentuais = funcionario_repository.percentuais_por_funcionario(session)

    total = len(linhas)
    concluidas = [r for r in linhas if r.status == STATUS_CONCLUIDO]
    cancelados = sum(1 for r in linhas if r.status == STATUS_CANCELADO)
    no_show = sum(1 for r in linhas if r.status == STATUS_NAO_COMPARECEU)

    receita = sum(r.preco for r in concluidas)
    comissoes = _comissoes_do_periodo(session, inicio, fim)

    dias = (fim - inicio).days + 1
    slots_por_dia = len(_gerar_grade_horarios())
    n_funcionarios = len(percentuais) or 1
    capacidade = dias * slots_por_dia * n_funcionarios
    ocupados = sum(1 for r in linhas if r.status in (STATUS_CONCLUIDO, STATUS_AGENDADO))

    return {
        "total_agendamentos": total,
        "atendimentos_concluidos": len(concluidas),
        "receita_bruta": round(receita, 2),
        "comissoes": round(comissoes, 2),
        "receita_loja": round(receita - comissoes, 2),
        "ticket_medio": round(receita / len(concluidas), 2) if concluidas else 0.0,
        "clientes_unicos": len({r.cliente for r in concluidas}),
        "taxa_cancelamento": round(cancelados / total * 100, 1) if total else 0.0,
        "taxa_no_show": round(no_show / total * 100, 1) if total else 0.0,
        "taxa_ocupacao": round(ocupados / capacidade * 100, 1) if capacidade else 0.0,
    }


def _comissoes_do_periodo(session: Session, inicio: date, fim: date) -> float:
    from src.services import faturamento_service

    linhas = faturamento_service.faturamento_por_periodo(session, inicio, fim)
    percentuais = funcionario_repository.percentuais_por_funcionario(session)
    return sum(
        r.preco_servico * percentuais.get(r.funcionario_id, PERCENTUAL_COMISSAO_PADRAO)
        for r in linhas
    )


def comparativo(session: Session, inicio: date, fim: date) -> dict:
    """KPIs do período e do período imediatamente anterior de mesma duração."""
    dias = (fim - inicio).days + 1
    inicio_anterior = inicio - timedelta(days=dias)
    fim_anterior = inicio - timedelta(days=1)
    return {
        "atual": kpis(session, inicio, fim),
        "anterior": kpis(session, inicio_anterior, fim_anterior),
        "periodo_anterior": (inicio_anterior, fim_anterior),
    }


def receita_por_dia(session: Session, inicio: date, fim: date) -> list[dict]:
    linhas = agendamento_repository.listar_detalhado(session, a_partir_de=inicio, ate=fim)
    por_dia: dict[date, float] = {}
    for r in linhas:
        if r.status == STATUS_CONCLUIDO:
            por_dia[r.data] = por_dia.get(r.data, 0.0) + r.preco
    return [{"data": dia, "receita": round(valor, 2)} for dia, valor in sorted(por_dia.items())]


DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def atendimentos_por_dia_semana(session: Session, inicio: date, fim: date) -> list[dict]:
    linhas = agendamento_repository.listar_detalhado(session, a_partir_de=inicio, ate=fim)
    contagem = [0] * 7
    for r in linhas:
        if r.status == STATUS_CONCLUIDO:
            contagem[r.data.weekday()] += 1
    return [{"dia": DIAS_SEMANA[i], "atendimentos": contagem[i]} for i in range(7)]


def atendimentos_por_horario(session: Session, inicio: date, fim: date) -> list[dict]:
    linhas = agendamento_repository.listar_detalhado(session, a_partir_de=inicio, ate=fim)
    contagem: dict[str, int] = {}
    for r in linhas:
        if r.status == STATUS_CONCLUIDO:
            contagem[r.hora] = contagem.get(r.hora, 0) + 1
    return [{"hora": hora, "atendimentos": qtd} for hora, qtd in sorted(contagem.items())]


def top_servicos(session: Session, inicio: date, fim: date, limite: int = 8) -> list[dict]:
    linhas = agendamento_repository.listar_detalhado(session, a_partir_de=inicio, ate=fim)
    por_servico: dict[str, dict] = {}
    for r in linhas:
        if r.status == STATUS_CONCLUIDO:
            item = por_servico.setdefault(r.servico, {"quantidade": 0, "receita": 0.0})
            item["quantidade"] += 1
            item["receita"] += r.preco
    ordenado = sorted(por_servico.items(), key=lambda kv: kv[1]["receita"], reverse=True)
    return [
        {"servico": nome, "quantidade": v["quantidade"], "receita": round(v["receita"], 2)}
        for nome, v in ordenado[:limite]
    ]


def desempenho_funcionarios(session: Session, inicio: date, fim: date) -> list[dict]:
    from src.services import faturamento_service

    linhas = faturamento_service.faturamento_por_periodo(session, inicio, fim)
    percentuais = funcionario_repository.percentuais_por_funcionario(session)
    por_funcionario: dict[int, dict] = {}
    for r in linhas:
        item = por_funcionario.setdefault(
            r.funcionario_id, {"funcionario": r.funcionario, "atendimentos": 0, "receita": 0.0}
        )
        item["atendimentos"] += 1
        item["receita"] += r.preco_servico
    resultado = []
    for funcionario_id, item in por_funcionario.items():
        percentual = percentuais.get(funcionario_id, PERCENTUAL_COMISSAO_PADRAO)
        comissao = round(item["receita"] * percentual, 2)
        resultado.append(
            {
                "funcionario": item["funcionario"],
                "atendimentos": item["atendimentos"],
                "receita": round(item["receita"], 2),
                "comissao": comissao,
                "receita_loja": round(item["receita"] - comissao, 2),
                "ticket_medio": round(item["receita"] / item["atendimentos"], 2),
            }
        )
    return sorted(resultado, key=lambda item: item["receita"], reverse=True)


# --- Metas (OKR) ---


def obter_metas(session: Session) -> dict[str, float]:
    metas = dict(METAS_PADRAO)
    for meta in session.scalars(select(Meta)):
        if meta.chave in metas:
            metas[meta.chave] = meta.valor
    return metas


def salvar_meta(session: Session, chave: str, valor: float) -> None:
    if chave not in METAS_PADRAO:
        raise ValueError(f"Meta desconhecida: {chave}")
    if valor < 0:
        raise ValueError("A meta não pode ser negativa.")
    meta = session.scalar(select(Meta).where(Meta.chave == chave))
    if meta is None:
        session.add(Meta(chave=chave, valor=valor))
    else:
        meta.valor = valor
    session.commit()


def progresso_metas(session: Session, indicadores: dict) -> list[dict]:
    """Progresso de cada meta em relação aos KPIs do período (0.0 a 1.0, limitado a 1)."""
    metas = obter_metas(session)
    itens = [
        ("receita_mensal", indicadores["receita_bruta"], False),
        ("atendimentos_mensais", float(indicadores["atendimentos_concluidos"]), False),
        ("ticket_medio", indicadores["ticket_medio"], False),
        ("taxa_no_show_max", indicadores["taxa_no_show"], True),
    ]
    resultado = []
    for chave, valor_atual, menor_melhor in itens:
        alvo = metas[chave]
        if menor_melhor:
            # Meta de teto: 100% quando o indicador está em zero; 0% quando dobra o teto.
            progresso = 1.0 if alvo == 0 and valor_atual == 0 else max(0.0, 1 - valor_atual / (alvo * 2)) if alvo else 0.0
            atingida = valor_atual <= alvo
        else:
            progresso = min(valor_atual / alvo, 1.0) if alvo else 0.0
            atingida = valor_atual >= alvo
        resultado.append(
            {
                "chave": chave,
                "label": METAS_LABELS[chave],
                "alvo": alvo,
                "atual": valor_atual,
                "progresso": round(progresso, 3),
                "atingida": atingida,
                "menor_melhor": menor_melhor,
            }
        )
    return resultado
