# Dockerfile (versão corrigida com dependências de build)

# Etapa 1: Usar uma imagem base oficial do Python
FROM python:3.9-slim

# Etapa 2: Instalar as dependências de sistema necessárias para compilar o mysqlclient
# - build-essential: Contém compiladores como gcc
# - default-libmysqlclient-dev (Debian/Ubuntu): Pacote de desenvolvimento do cliente MySQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Etapa 3: Definir o diretório de trabalho dentro do container
WORKDIR /app

# Etapa 4: Copiar o arquivo de dependências e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Etapa 5: Copiar o restante do código da aplicação
COPY . .

# Etapa 6: Expor a porta que a aplicação vai rodar
EXPOSE 5050

# Etapa 7: Comando para iniciar a aplicação usando Gunicorn
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:5050", "wsgi:app"]