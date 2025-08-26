# Dockerfile

# Etapa 1: Usar uma imagem base oficial do Python
FROM python:3.9-slim

# Etapa 2: Definir o diretório de trabalho dentro do container
WORKDIR /app

# Etapa 3: Copiar o arquivo de dependências e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Etapa 4: Copiar o restante do código da aplicação
COPY . .

# Etapa 5: Expor a porta que a aplicação vai rodar
EXPOSE 5050

# Etapa 6: Comando para iniciar a aplicação usando Gunicorn (servidor de produção)
# As variáveis de ambiente (DB, S3, etc.) serão injetadas pelo ECS Task Definition
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:5050", "wsgi:app"]