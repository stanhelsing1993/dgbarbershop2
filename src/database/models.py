from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


STATUS_AGENDADO = "agendado"
STATUS_CONCLUIDO = "concluido"
STATUS_CANCELADO = "cancelado"
STATUS_NAO_COMPARECEU = "nao_compareceu"

FORMAS_PAGAMENTO = {
    "dinheiro": "Dinheiro",
    "pix": "Pix",
    "cartao_debito": "Cartão de Débito",
    "cartao_credito": "Cartão de Crédito",
}
FORMA_NAO_INFORMADA = "Não informado"

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
    # Blacklist: ligada automaticamente ao acumular cancelamentos/faltas;
    # o gestor pode desligar na página de Clientes.
    bloqueado: Mapped[bool] = mapped_column(nullable=False, default=False)

    agendamentos: Mapped[list["Agendamento"]] = relationship(back_populates="cliente")


PERCENTUAL_COMISSAO_PADRAO = 0.5


class Funcionario(Base):
    __tablename__ = "funcionarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    especialidade: Mapped[Optional[str]] = mapped_column(String)
    # Fração do preço do serviço repassada ao funcionário (0.5 = 50%).
    percentual_comissao: Mapped[float] = mapped_column(
        nullable=False, default=PERCENTUAL_COMISSAO_PADRAO
    )

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
    # Preenchida quando o atendimento é concluído (chave de FORMAS_PAGAMENTO).
    forma_pagamento: Mapped[Optional[str]] = mapped_column(String)

    cliente: Mapped["Cliente"] = relationship(back_populates="agendamentos")
    funcionario: Mapped["Funcionario"] = relationship(back_populates="agendamentos")
    servico: Mapped["Servico"] = relationship(back_populates="agendamentos")


TIPO_ENTRADA = "entrada"
TIPO_SAIDA = "saida"


class Adiantamento(Base):
    """Vale concedido a um funcionário; sai do caixa do dia e é descontado do repasse.

    Fica pendente até ser abatido em um acerto: pagamento_id aponta para o
    pagamento em que o desconto aconteceu (NULL = ainda não descontado).
    """

    __tablename__ = "adiantamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("funcionarios.id"), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[float] = mapped_column(nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(String)
    pagamento_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pagamentos_funcionarios.id"), nullable=True
    )

    funcionario: Mapped["Funcionario"] = relationship()


class PagamentoFuncionario(Base):
    """Acerto realizado com um funcionário: comissão do período menos os vales abatidos."""

    __tablename__ = "pagamentos_funcionarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("funcionarios.id"), nullable=False)
    data_pagamento: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_fim: Mapped[date] = mapped_column(Date, nullable=False)
    comissao_base: Mapped[float] = mapped_column(nullable=False)
    descontos_abatidos: Mapped[float] = mapped_column(nullable=False)
    valor_pago: Mapped[float] = mapped_column(nullable=False)
    observacao: Mapped[Optional[str]] = mapped_column(String)

    funcionario: Mapped["Funcionario"] = relationship()


class Meta(Base):
    """Meta gerencial (OKR) configurável: chave -> valor alvo."""

    __tablename__ = "metas"

    id: Mapped[int] = mapped_column(primary_key=True)
    chave: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    valor: Mapped[float] = mapped_column(nullable=False)


class MovimentoCaixa(Base):
    """Entrada ou saída avulsa de caixa (compra de insumos, venda de produto etc.)."""

    __tablename__ = "movimentos_caixa"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    tipo: Mapped[str] = mapped_column(String, nullable=False)  # TIPO_ENTRADA | TIPO_SAIDA
    valor: Mapped[float] = mapped_column(nullable=False)
    descricao: Mapped[str] = mapped_column(String, nullable=False)


class AberturaCaixa(Base):
    """Abertura diária do caixa (troco inicial); uma por data."""

    __tablename__ = "aberturas_caixa"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    valor_inicial: Mapped[float] = mapped_column(nullable=False)
    hora: Mapped[str] = mapped_column(String, nullable=False)
    aberto_por: Mapped[Optional[str]] = mapped_column(String)


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


ROLE_ADMIN = "admin"
ROLE_FUNCIONARIO = "funcionario"
ROLES = {
    ROLE_ADMIN: "Administrador",
    ROLE_FUNCIONARIO: "Funcionário",
}


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome_usuario: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="funcionario")
