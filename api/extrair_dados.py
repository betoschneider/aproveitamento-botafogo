import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
from datetime import date
import sqlite3
from contextlib import contextmanager
import os

# Constantes
DB_PATH = os.getenv("DB_PATH", "/data/botafogo.db")

@contextmanager
def get_db_connection():
    """Context manager para conexão SQLite"""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Inicializa as tabelas do banco de dados"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Tabela de partidas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partidas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competicao TEXT,
                rodada TEXT,
                dia TEXT,
                data DATE,
                horario TEXT,
                local TEXT,
                ranking INTEGER,
                adversario TEXT,
                ranking_adversario INTEGER,
                sistema TEXT,
                publico INTEGER,
                gols INTEGER,
                gols_adversario INTEGER,
                resultado TEXT,
                dt_coleta DATE,
                UNIQUE(competicao, rodada, data)
            )
        """)
        
        # Tabela de técnicos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tecnicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                dt_nascimento DATE,
                dt_inicio DATE,
                dt_fim DATE,
                dt_coleta DATE,
                UNIQUE(nome, dt_inicio)
            )
        """)
        
        conn.commit()
        print("✅ Banco de dados inicializado")


def get_partidas():
    """Coleta partidas do Botafogo e salva no banco"""
    ano = datetime.datetime.now().year - 1
    # ano = 2023 # Definindo ano fixo para coleta
    
    url = f"https://www.transfermarkt.com.br/botafogo-rio-de-janeiro/spielplan/verein/537/saison_id/{ano}"

    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")

    tabelas = soup.find_all("div", class_="box")
    todos = []

    for box in tabelas:
        titulo = box.find("h2", class_="content-box-headline")
        if not titulo:
            continue

        competicao = titulo.get_text(strip=True)
        tabela = box.find("table")
        if not tabela:
            continue

        linhas = []
        for tr in tabela.find_all("tr")[1:]:
            cols = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cols) < 9:
                continue
            
            rodada, data, horario, local, ranking, _, adversario, sistema, publico, resultado = (cols + [None]*10)[:10]
            
            linhas.append({
                "competicao": competicao,
                "rodada": rodada,
                "dia": data.split(" ")[0] if " " in data else data,
                "data": data.split(" ")[-1] if " " in data else data,
                "horario": horario,
                "local": local,
                "ranking": ranking.replace(".", "").replace("(", "").replace(")", "") if ranking else None,
                "adversario": adversario.split("(")[0].strip() if adversario else None,
                "ranking_adversario": adversario.split("(")[-1].replace(".)", "").strip() if adversario and "(" in adversario else None,
                "sistema": sistema,
                "publico": publico,
                "gols": resultado.split(":")[0] if local == "C" else resultado.split(":")[-1] if resultado and ":" in resultado else None,
                "gols_adversario": resultado.split(":")[-1] if local == "C" else resultado.split(":")[0] if resultado and ":" in resultado else None,
                "resultado": resultado,
                "dt_coleta": datetime.date.today()
            })

        df_temp = pd.DataFrame(linhas)
        print(f"Competição: {competicao} | Linhas extraídas: {len(df_temp)}")
        todos.append(df_temp)

    if not todos:
        print("⚠️ Nenhuma tabela encontrada no HTML.")
        return

    df = pd.concat(todos, ignore_index=True)
    print(f"Total de partidas extraídas: {len(df)}")

    # Limpeza
    df = df[df["competicao"] != "Os últimos  jogos"]
    df = df[df["resultado"] != "-:-"]
    df = df[~df["data"].isnull()]

    # Conversão de tipos
    df["data"] = pd.to_datetime(df["data"], errors="coerce", dayfirst=True).dt.date
    df["publico"] = pd.to_numeric(df["publico"].str.replace(".", "", regex=False), errors="coerce")
    df["gols"] = pd.to_numeric(df["gols"], errors="coerce")
    df["gols_adversario"] = pd.to_numeric(df["gols_adversario"], errors="coerce")
    df["ranking"] = pd.to_numeric(df["ranking"], errors="coerce")
    df["ranking_adversario"] = pd.to_numeric(df["ranking_adversario"], errors="coerce")
    df["resultado"] = df.apply(
        lambda row: "V" if row["gols"] > row["gols_adversario"] 
                    else ("E" if row["gols"] == row["gols_adversario"] else "D") 
                    if pd.notnull(row["gols"]) and pd.notnull(row["gols_adversario"]) 
                    else None,
        axis=1
    )

    if df.empty:
        print("⚠️ Nenhum dado válido após limpeza.")
        return

    # Salvar no banco
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO partidas (
                    competicao, rodada, dia, data, horario, local, ranking,
                    adversario, ranking_adversario, sistema, publico,
                    gols, gols_adversario, resultado, dt_coleta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(competicao, rodada, data) DO UPDATE SET
                    horario = excluded.horario,
                    local = excluded.local,
                    ranking = excluded.ranking,
                    adversario = excluded.adversario,
                    ranking_adversario = excluded.ranking_adversario,
                    sistema = excluded.sistema,
                    publico = excluded.publico,
                    gols = excluded.gols,
                    gols_adversario = excluded.gols_adversario,
                    resultado = excluded.resultado,
                    dt_coleta = excluded.dt_coleta
            """, (
                row['competicao'], row['rodada'], row['dia'], row['data'],
                row['horario'], row['local'], row['ranking'], row['adversario'],
                row['ranking_adversario'], row['sistema'], row['publico'],
                row['gols'], row['gols_adversario'], row['resultado'], row['dt_coleta']
            ))
        
        conn.commit()
        print(f"✅ Banco atualizado com {len(df)} partidas")


def get_tecnicos():
    """Coleta técnicos do Botafogo e salva no banco"""
    url = "https://www.transfermarkt.com.br/botafogo-fr-rio-de-janeiro/mitarbeiterhistorie/verein/537"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/125.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="items")

    dados = []
    for row in table.find("tbody").find_all("tr", recursive=False):
        cols = row.find_all("td")
        if not cols or len(cols) < 7:
            continue

        nome = cols[2].get_text(strip=True)
        dt_nascimento = cols[3].get_text(strip=True)
        dt_inicio = cols[5].get_text(strip=True)
        dt_fim = cols[6].get_text(strip=True)

        dados.append({
            "nome": nome,
            "dt_nascimento": dt_nascimento,
            "dt_inicio": dt_inicio,
            "dt_fim": dt_fim,
        })

    df = pd.DataFrame(dados)

    # Conversão de datas
    for col in ["dt_inicio", "dt_fim", "dt_nascimento"]:
        df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True).dt.date

    # Filtros
    df = df[df["dt_inicio"] >= pd.to_datetime("2023-07-18").date()].reset_index(drop=True)
    df = df[df["nome"] != "Pedro Martins"]  # Remover Pedro Martins
    df["dt_coleta"] = date.today()  

    if df.empty:
        print("⚠️ Nenhum técnico encontrado após filtros.")
        return

    # Salvar no banco
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO tecnicos (nome, dt_nascimento, dt_inicio, dt_fim, dt_coleta)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(nome, dt_inicio) DO UPDATE SET
                    dt_nascimento = excluded.dt_nascimento,
                    dt_fim = excluded.dt_fim,
                    dt_coleta = excluded.dt_coleta
            """, (
                row['nome'],
                row['dt_nascimento'] if pd.notnull(row['dt_nascimento']) else None,
                row['dt_inicio'] if pd.notnull(row['dt_inicio']) else None,
                row['dt_fim'] if pd.notnull(row['dt_fim']) else None,
                row['dt_coleta'] if pd.notnull(row['dt_coleta']) else None,
            ))
        
        conn.commit()
        print(f"✅ Banco atualizado com {len(df)} técnicos")


if __name__ == "__main__":
    init_db()
    get_partidas()
    get_tecnicos()