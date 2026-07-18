from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Funcionario


def listar(session: Session) -> list[Funcionario]:
    return list(session.scalars(select(Funcionario).order_by(Funcionario.nome)))


def obter_por_id(session: Session, funcionario_id: int) -> Optional[Funcionario]:
    return session.get(Funcionario, funcionario_id)


def criar(session: Session, nome: str, especialidade: str) -> Funcionario:
    funcionario = Funcionario(nome=nome, especialidade=especialidade)
    session.add(funcionario)
    session.commit()
    return funcionario


def atualizar(session: Session, funcionario_id: int, nome: str, especialidade: str) -> None:
    funcionario = session.get(Funcionario, funcionario_id)
    if funcionario is None:
        return
    funcionario.nome = nome
    funcionario.especialidade = especialidade
    session.commit()


def excluir(session: Session, funcionario_id: int) -> None:
    funcionario = session.get(Funcionario, funcionario_id)
    if funcionario is not None:
        session.delete(funcionario)
        session.commit()
