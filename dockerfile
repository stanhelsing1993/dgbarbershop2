# Usa a imagem oficial do Python
FROM python:3.9

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos de dependências
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia todos os arquivos do projeto
COPY . .

# Expõe a porta padrão do Streamlit
EXPOSE 8501

# Comando para rodar o app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]