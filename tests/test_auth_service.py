import pytest

from src.services import auth_service


def test_hash_e_verificar_senha_correta():
    hashed = auth_service.hash_senha("minhasenha123")
    assert auth_service.verificar_senha("minhasenha123", hashed)


def test_verificar_senha_incorreta():
    hashed = auth_service.hash_senha("minhasenha123")
    assert not auth_service.verificar_senha("outrasenha", hashed)


def test_autenticar_usuario_valido(session):
    auth_service.criar_usuario(session, "joao", "senha123", role="funcionario")
    usuario = auth_service.autenticar(session, "joao", "senha123")
    assert usuario is not None
    assert usuario.role == "funcionario"


def test_autenticar_senha_incorreta(session):
    auth_service.criar_usuario(session, "joao", "senha123")
    assert auth_service.autenticar(session, "joao", "errada") is None


def test_autenticar_usuario_inexistente(session):
    assert auth_service.autenticar(session, "ninguem", "senha") is None


def test_criar_usuario_admin(session):
    usuario = auth_service.criar_usuario(session, "chefe", "senha123", role="admin")
    assert usuario.role == "admin"


def test_criar_usuario_duplicado_levanta_erro(session):
    auth_service.criar_usuario(session, "joao", "senha123")
    with pytest.raises(ValueError):
        auth_service.criar_usuario(session, "joao", "outrasenha")


def test_criar_usuario_role_invalida_levanta_erro(session):
    with pytest.raises(ValueError):
        auth_service.criar_usuario(session, "joao", "senha123", role="super")


def test_criar_usuario_senha_curta_levanta_erro(session):
    with pytest.raises(ValueError):
        auth_service.criar_usuario(session, "joao", "123")


def test_alterar_role_promove_funcionario(session):
    auth_service.criar_usuario(session, "chefe", "senha123", role="admin")
    usuario = auth_service.criar_usuario(session, "joao", "senha123")
    auth_service.alterar_role(session, usuario.id, "admin")
    assert usuario.role == "admin"


def test_nao_rebaixa_unico_admin(session):
    admin = auth_service.criar_usuario(session, "chefe", "senha123", role="admin")
    with pytest.raises(ValueError):
        auth_service.alterar_role(session, admin.id, "funcionario")


def test_nao_exclui_unico_admin(session):
    admin = auth_service.criar_usuario(session, "chefe", "senha123", role="admin")
    with pytest.raises(ValueError):
        auth_service.excluir_usuario(session, admin.id)


def test_excluir_admin_quando_ha_outro(session):
    auth_service.criar_usuario(session, "chefe", "senha123", role="admin")
    segundo = auth_service.criar_usuario(session, "vice", "senha123", role="admin")
    auth_service.excluir_usuario(session, segundo.id)
    assert auth_service.autenticar(session, "vice", "senha123") is None


def test_redefinir_senha(session):
    usuario = auth_service.criar_usuario(session, "joao", "senha123")
    auth_service.redefinir_senha(session, usuario.id, "novasenha")
    assert auth_service.autenticar(session, "joao", "novasenha") is not None
    assert auth_service.autenticar(session, "joao", "senha123") is None
