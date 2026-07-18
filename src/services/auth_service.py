from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from src.database.models import Usuario
from src.repositories import usuario_repository


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode(), senha_hash.encode())


def autenticar(session: Session, nome_usuario: str, senha: str) -> Optional[Usuario]:
    usuario = usuario_repository.obter_por_nome(session, nome_usuario)
    if usuario is None or not verificar_senha(senha, usuario.senha_hash):
        return None
    return usuario


def criar_usuario(session: Session, nome_usuario: str, senha: str, role: str = "funcionario") -> Usuario:
    return usuario_repository.criar(session, nome_usuario, hash_senha(senha), role)
