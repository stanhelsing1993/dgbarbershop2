import sqlite3


def connect_db():
    conn = sqlite3.connect('barbearia.db')
    return conn


def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        telefone TEXT,
        email TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS funcionarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        especialidade TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        preco REAL,
        duracao INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        funcionario_id INTEGER,
        servico_id INTEGER,
        data TEXT,
        hora TEXT,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id),
        FOREIGN KEY(funcionario_id) REFERENCES funcionarios(id),
        FOREIGN KEY(servico_id) REFERENCES servicos(id)
    )
    ''')


    cursor.execute('''CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY,
    nome_usuario TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL
    )''')

    conn.commit()
    conn.close()