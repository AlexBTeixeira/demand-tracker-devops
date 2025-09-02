
FROM python:3.9-slim

# Instalar as dependências pra compilar o mysqlclient

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar o arquivo de dependências e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto da aplicação
COPY . .

# Expor a porta que a aplicação vai rodar
EXPOSE 5050

# iniciaa aplicação usando Gunicorn
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:5050", "wsgi:app"]