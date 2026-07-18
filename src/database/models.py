from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


STATUS_AGENDADO = "agendado"
STATUS_CONCLUIDO = "concluido"
STATUS_CANCELADO = "cancelado"
STATUS_NAO_COMPARECEU = "nao_compareceu"

# Regra financeira: apenas atendimentos concluídos geram receita
# (faturamento, ticket médio e repasse). Agendado é expectativa, não caixa.


class Base(DeclarativeBase):
    pass


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    telefone: Mapped[Optional[str]] = mapped_column(String)
    email: Mapped[Optional[str]] = mapped_column(String)

    agendamentos: Mapped[list["Agendamento"]] = relationship(back_populates="cliente")


class Funcionario(Base):
    __tablename__ = "funcionarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    especialidade: Mapped[Optional[str]] = mapped_column(String)

    agendamentos: Mapped[list["Agendamento"]] = relationship(back_populates="funcionario")


class Servico(Base):
    __tablename__ = "servicos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    preco: Mapped[float] = mapped_column(nullable=False)
    duracao: Mapped[int] = mapped_column(nullable=False)

    agendamentos: Mapped[list["Agendamento"]] = relationship(back_populates="servico")


class Agendamento(Base):
    __tablename__ = "agendamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("funcionarios.id"), nullable=False)
    servico_id: Mapped[int] = mapped_column(ForeignKey("servicos.id"), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    hora: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="agendado")

    cliente: Mapped["Cliente"] = relationship(back_populates="agendamentos")
    funcionario: Mapped["Funcionario"] = relationship(back_populates="agendamentos")
    servico: Mapped["Servico"] = relationship(back_populates="agendamentos")


TIPO_ENTRADA = "entrada"
TIPO_SAIDA = "saida"


class Adiantamento(Base):
    """Vale concedido a um funcionário; sai do caixa do dia e é descontado do repasse."""

    __tablename__ = "adiantamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("funcionarios.id"), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[float] = mapped_column(nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(String)

    funcionario: Mapped["Funcionario"] = relationship()


class MovimentoCaixa(Base):
    """Entrada ou saída avulsa de caixa (compra de insumos, venda de produto etc.)."""

    __tablename__ = "movimentos_caixa"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    tipo: Mapped[str] = mapped_column(String, nullable=False)  # TIPO_ENTRADA | TIPO_SAIDA
    valor: Mapped[float] = mapped_column(nullable=False)
    descricao: Mapped[str] = mapped_column(String, nullable=False)


class FechamentoCaixa(Base):
    """Snapshot do dia no momento do fechamento; um por data."""

    __tablename__ = "fechamentos_caixa"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    receita_servicos: Mapped[float] = mapped_column(nullable=False)
    entradas: Mapped[float] = mapped_column(nullable=False)
    saidas: Mapped[float] = mapped_column(nullable=False)
    adiantamentos: Mapped[float] = mapped_column(nullable=False)
    saldo: Mapped[float] = mapped_column(nullable=False)
    observacao: Mapped[Optional[str]] = mapped_column(String)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome_usuario: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="funcionario")
