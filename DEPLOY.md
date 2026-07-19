# Deploy com dados persistentes

Por padrão o app usa SQLite (`barbearia.db`), que **não sobrevive a redeploys** em
hospedagens como o Streamlit Community Cloud. Há duas opções:

## Opção 1 (recomendada): Postgres gratuito

1. Crie uma conta gratuita no [Neon](https://neon.tech) ou [Supabase](https://supabase.com)
   (não pede cartão de crédito).
2. Crie um projeto/banco e copie a **connection string** Postgres.
   Ela tem o formato: `postgresql://usuario:senha@host/banco?sslmode=require`
3. No Streamlit Cloud, abra o app → **Settings → Secrets** e adicione:

   ```toml
   DATABASE_URL = "postgresql+psycopg2://usuario:senha@host/banco?sslmode=require"
   ADMIN_USERNAME = "seu_admin"
   ADMIN_PASSWORD = "uma_senha_forte"
   ```

   > Atenção ao prefixo: troque `postgresql://` por `postgresql+psycopg2://`.

4. Reinicie o app. As tabelas são criadas automaticamente no primeiro acesso e o
   admin é semeado com as credenciais dos secrets. Os dados passam a sobreviver a
   qualquer redeploy.

## Opção 2: continuar no SQLite com backups

Sem `DATABASE_URL`, o app segue no SQLite. Na página **Usuários** (admin) há a
seção **Backup do Banco de Dados**:

- **Baixar backup** antes de cada redeploy;
- **Restaurar backup** depois que o app voltar.

Funciona, mas depende de disciplina — qualquer redeploy sem backup recente perde
os dados desde o último download.

## Rodando localmente

Nada muda: sem `.env`/secrets o app usa `sqlite:///barbearia.db` na raiz do projeto.
