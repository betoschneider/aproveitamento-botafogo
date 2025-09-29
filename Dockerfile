# Usar imagem Python oficial
FROM python:3.12

# Diretório de trabalho
WORKDIR /app

# Copiar arquivos
COPY . .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Porta padrão do Streamlit (alterada para 8505)
EXPOSE 8505

# Comando para iniciar o app
CMD ["streamlit", "run", "app.py", "--server.port=8505", "--server.address=0.0.0.0"]
