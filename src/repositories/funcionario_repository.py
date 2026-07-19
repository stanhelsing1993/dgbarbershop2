from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import PERCENTUAL_COMISSAO_PADRAO, Funcionario


def listar(session: Session) -> list[Funcionario]:
    return list(session.scalars(select(Funcionario).order_by(Funcionario.nome)))


def obter_por_id(session: Session, funcionario_id: int) -> Optional[Funcionario]:
    return session.get(Funcionario, funcionario_id)


def percentuais_por_funcionario(session: Session) -> dict[int, float]:
    stmt = select(Funcionario.id, Funcionario.percentual_comissao)
    return {funcionario_id: percentual for funcionario_id, percentual in session.execute(stmt)}


def criar(
    session: Session,
    nome: str,
    especialidade: str,
    percentual_comissao: float = PERCENTUAL_COMISSAO_PADRAO,
) -> Funcionario:
    funcionario = Funcionario(
        nome=nome, especialidade=especialidade, percentual_comissao=percentual_comissao
    )
    session.add(funcionario)
    session.commit()
    return funcionario


def atualizar(
    session: Session,
    funcionario_id: int,
    nome: str,
    especialidade: str,
    percentual_comissao: Optional[float] = None,
) -> None:
    funcionario = session.get(Funcionario, funcionario_id)
    if funcionario is None:
        return
    funcionario.nome = nome
    funcionario.especialidade = especialidade
    if percentual_comissao is not None:
        funcionario.percentual_comissao = percentual_comissao
    session.commit()


def excluir(session: Session, funcionario_id: int) -> None:
    funcionario = session.get(Funcionario, funcionario_id)
    if funcionario is not None:
        session.delete(funcionario)
        session.commit()
