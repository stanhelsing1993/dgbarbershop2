from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config import HORARIO_ABERTURA, HORARIO_FECHAMENTO
from src.database.models import STATUS_CONCLUIDO, Agendamento, FechamentoCaixa, Servico
from src.repositories import adiantamento_repository, caixa_repository

STATUS_NAO_ABERTO = "nao_aberto"
STATUS_ABERTO = "aberto"
STATUS_FECHADO = "fechado"

# Quantos dias para trás procurar caixas abertos sem fechamento.
JANELA_PENDENCIAS_DIAS = 7


class CaixaError(Exception):
    pass


def receita_servicos_do_dia(session: Session, dia: date) -> float:
    stmt = (
        select(func.coalesce(func.sum(Servico.preco), 0.0))
        .select_from(Agendamento)
        .join(Servico, Agendamento.servico_id == Servico.id)
        .where(Agendamento.data == dia, Agendamento.status == STATUS_CONCLUIDO)
    )
    return session.scalar(stmt) or 0.0


def status_do_dia(session: Session, dia: date) -> str:
    if caixa_repository.obter_fechamento(session, dia) is not None:
        return STATUS_FECHADO
    if caixa_repository.obter_abertura(session, dia) is not None:
        return STATUS_ABERTO
    return STATUS_NAO_ABERTO


def abrir_caixa(
    session: Session,
    dia: date,
    valor_inicial: float,
    aberto_por: Optional[str] = None,
    agora: Optional[datetime] = None,
):
    if valor_inicial < 0:
        raise CaixaError("O valor inicial do caixa não pode ser negativo.")
    status = status_do_dia(session, dia)
    if status == STATUS_FECHADO:
        raise CaixaError(f"O caixa de {dia.strftime('%d/%m/%Y')} já foi fechado.")
    if status == STATUS_ABERTO:
        raise CaixaError(f"O caixa de {dia.strftime('%d/%m/%Y')} já está aberto.")
    agora = agora or datetime.now()
    return caixa_repository.criar_abertura(
        session, dia, valor_inicial, agora.strftime("%H:%M"), aberto_por
    )


def resumo_do_dia(session: Session, dia: date) -> dict:
    abertura = caixa_repository.obter_abertura(session, dia)
    valor_inicial = abertura.valor_inicial if abertura is not None else 0.0
    receita = receita_servicos_do_dia(session, dia)
    entradas = caixa_repository.total_movimentos(session, dia, "entrada")
    saidas = caixa_repository.total_movimentos(session, dia, "saida")
    adiantamentos = adiantamento_repository.total_do_dia(session, dia)
    return {
        "valor_inicial": round(valor_inicial, 2),
        "receita_servicos": round(receita, 2),
        "entradas": round(entradas, 2),
        "saidas": round(saidas, 2),
        "adiantamentos": round(adiantamentos, 2),
        "saldo": round(valor_inicial + receita + entradas - saidas - adiantamentos, 2),
    }


def fechar_caixa(session: Session, dia: date, observacao: Optional[str] = None) -> FechamentoCaixa:
    status = status_do_dia(session, dia)
    if status == STATUS_FECHADO:
        raise CaixaError(f"O caixa de {dia.strftime('%d/%m/%Y')} já foi fechado.")
    if status == STATUS_NAO_ABERTO:
        raise CaixaError(
            f"O caixa de {dia.strftime('%d/%m/%Y')} ainda não foi aberto — abra antes de fechar."
        )
    resumo = resumo_do_dia(session, dia)
    return caixa_repository.criar_fechamento(
        session,
        dia,
        receita_servicos=resumo["receita_servicos"],
        entradas=resumo["entradas"],
        saidas=resumo["saidas"],
        adiantamentos=resumo["adiantamentos"],
        saldo=resumo["saldo"],
        observacao=observacao,
    )


def pendencias(session: Session, agora: Optional[datetime] = None) -> list[dict]:
    """Lembretes inteligentes do caixa, do mais urgente para o menos.

    - Dias anteriores abertos e nunca fechados (erro: o financeiro fica furado);
    - Hoje após o fim do expediente com caixa ainda aberto (hora de fechar);
    - Hoje dentro do expediente com caixa ainda não aberto (aviso).
    """
    agora = agora or datetime.now()
    hoje = agora.date()
    alertas = []

    inicio_janela = hoje - timedelta(days=JANELA_PENDENCIAS_DIAS)
    for abertura in caixa_repository.listar_aberturas(session, inicio_janela, hoje - timedelta(days=1)):
        if caixa_repository.obter_fechamento(session, abertura.data) is None:
            alertas.append(
                {
                    "nivel": "erro",
                    "mensagem": (
                        f"🔴 O caixa de {abertura.data.strftime('%d/%m/%Y')} ficou aberto e nunca "
                        "foi fechado. Feche-o para regularizar o financeiro."
                    ),
                }
            )

    status_hoje = status_do_dia(session, hoje)
    hora_atual = agora.strftime("%H:%M")
    if status_hoje == STATUS_ABERTO and hora_atual >= HORARIO_FECHAMENTO:
        alertas.append(
            {
                "nivel": "aviso",
                "mensagem": (
                    f"🔔 O expediente terminou ({HORARIO_FECHAMENTO}) e o caixa de hoje ainda "
                    "está aberto. Não esqueça de fazer o fechamento diário!"
                ),
            }
        )
    elif status_hoje == STATUS_NAO_ABERTO and HORARIO_ABERTURA <= hora_atual < HORARIO_FECHAMENTO:
        alertas.append(
            {
                "nivel": "info",
                "mensagem": "🟡 O caixa de hoje ainda não foi aberto. Abra o caixa para começar o dia.",
            }
        )
    return alertas
