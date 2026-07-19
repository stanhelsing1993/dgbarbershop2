from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import Cliente


def listar(session: Session) -> list[Cliente]:
    return list(session.scalars(select(Cliente).order_by(Cliente.nome)))


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Cliente)) or 0


def obter_por_id(session: Session, cliente_id: int) -> Optional[Cliente]:
    return session.get(Cliente, cliente_id)


def criar(session: Session, nome: str, telefone: str, email: str) -> Cliente:
    cliente = Cliente(nome=nome, telefone=telefone, email=email)
    session.add(cliente)
    session.commit()
    return cliente


def atualizar(session: Session, cliente_id: int, nome: str, telefone: str, email: str) -> None:
    cliente = session.get(Cliente, cliente_id)
    if cliente is None:
        return
    cliente.nome = nome
    cliente.telefone = telefone
    cliente.email = email
    session.commit()


def definir_bloqueio(session: Session, cliente_id: int, bloqueado: bool) -> None:
    cliente = session.get(Cliente, cliente_id)
    if cliente is None:
        return
    cliente.bloqueado = bloqueado
    session.commit()


def excluir(session: Session, cliente_id: int) -> None:
    cliente = session.get(Cliente, cliente_id)
    if cliente is not None:
        session.delete(cliente)
        session.commit()
