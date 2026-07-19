from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from src.database.models import ROLE_ADMIN, ROLES, Usuario
from src.repositories import usuario_repository

SENHA_TAMANHO_MINIMO = 6


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
    nome_usuario = nome_usuario.strip()
    if not nome_usuario:
        raise ValueError("Informe o nome de usuário.")
    if role not in ROLES:
        raise ValueError(f"Tipo de usuário inválido: {role}")
    if len(senha) < SENHA_TAMANHO_MINIMO:
        raise ValueError(f"A senha deve ter pelo menos {SENHA_TAMANHO_MINIMO} caracteres.")
    if usuario_repository.obter_por_nome(session, nome_usuario) is not None:
        raise ValueError(f"Já existe um usuário chamado '{nome_usuario}'.")
    return usuario_repository.criar(session, nome_usuario, hash_senha(senha), role)


def alterar_role(session: Session, usuario_id: int, role: str) -> None:
    if role not in ROLES:
        raise ValueError(f"Tipo de usuário inválido: {role}")
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        return
    # Rebaixar o único admin deixaria o sistema sem ninguém para administrá-lo.
    if usuario.role == ROLE_ADMIN and role != ROLE_ADMIN:
        if usuario_repository.contar_admins(session) <= 1:
            raise ValueError("Não é possível rebaixar o único administrador do sistema.")
    usuario_repository.atualizar_role(session, usuario_id, role)


def redefinir_senha(session: Session, usuario_id: int, nova_senha: str) -> None:
    if len(nova_senha) < SENHA_TAMANHO_MINIMO:
        raise ValueError(f"A senha deve ter pelo menos {SENHA_TAMANHO_MINIMO} caracteres.")
    usuario_repository.atualizar_senha_hash(session, usuario_id, hash_senha(nova_senha))


def excluir_usuario(session: Session, usuario_id: int) -> None:
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        return
    if usuario.role == ROLE_ADMIN and usuario_repository.contar_admins(session) <= 1:
        raise ValueError("Não é possível excluir o único administrador do sistema.")
    usuario_repository.excluir(session, usuario_id)
