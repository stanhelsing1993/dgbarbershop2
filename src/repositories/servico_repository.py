from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Servico


def listar(session: Session) -> list[Servico]:
    return list(session.scalars(select(Servico).order_by(Servico.nome)))


def obter_por_id(session: Session, servico_id: int) -> Optional[Servico]:
    return session.get(Servico, servico_id)


def criar(session: Session, nome: str, preco: float, duracao: int) -> Servico:
    servico = Servico(nome=nome, preco=preco, duracao=duracao)
    session.add(servico)
    session.commit()
    return servico


def atualizar(session: Session, servico_id: int, nome: str, preco: float, duracao: int) -> None:
    servico = session.get(Servico, servico_id)
    if servico is None:
        return
    servico.nome = nome
    servico.preco = preco
    servico.duracao = duracao
    session.commit()


def excluir(session: Session, servico_id: int) -> None:
    servico = session.get(Servico, servico_id)
    if servico is not None:
        session.delete(servico)
        session.commit()
