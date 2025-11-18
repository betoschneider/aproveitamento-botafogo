# Usar imagem Python oficial
FROM python:3.12-slim

# Diretório de trabalho
WORKDIR /app

# Copiar arquivos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expor a porta 8505
EXPOSE 8505

# Comando para iniciar o Streamlit
CMD ["streamlit", "run", "main.py", "--server.port=8505", "--server.address=0.0.0.0"]