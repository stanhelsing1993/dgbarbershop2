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
