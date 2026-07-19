from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Usuario


def obter_por_nome(session: Session, nome_usuario: str) -> Optional[Usuario]:
    return session.scalar(select(Usuario).where(Usuario.nome_usuario == nome_usuario))


def listar(session: Session) -> list[Usuario]:
    return list(session.scalars(select(Usuario).order_by(Usuario.nome_usuario)))


def criar(session: Session, nome_usuario: str, senha_hash: str, role: str = "funcionario") -> Usuario:
    usuario = Usuario(nome_usuario=nome_usuario, senha_hash=senha_hash, role=role)
    session.add(usuario)
    session.commit()
    return usuario


def contar_admins(session: Session) -> int:
    return len(list(session.scalars(select(Usuario).where(Usuario.role == "admin"))))


def atualizar_role(session: Session, usuario_id: int, role: str) -> None:
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        return
    usuario.role = role
    session.commit()


def atualizar_senha_hash(session: Session, usuario_id: int, senha_hash: str) -> None:
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        return
    usuario.senha_hash = senha_hash
    session.commit()


def excluir(session: Session, usuario_id: int) -> None:
    usuario = session.get(Usuario, usuario_id)
    if usuario is not None:
        session.delete(usuario)
        session.commit()
