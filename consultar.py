import sqlite3
import pandas as pd

DB_PATH = "botafogo.db"

def consultar_partidas(limite=10, ano=None, competicao=None):
    """Consulta partidas com filtros opcionais"""
    conn = sqlite3.connect(DB_PATH)
    
    query = "SELECT * FROM partidas WHERE 1=1"
    params = []
    
    if ano:
        query += " AND strftime('%Y', data) = ?"
        params.append(str(ano))
    
    if competicao:
        query += " AND competicao LIKE ?"
        params.append(f"%{competicao}%")
    
    query += " ORDER BY data DESC LIMIT ?"
    params.append(limite)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    return df


def consultar_tecnicos():
    """Consulta todos os técnicos"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT * FROM tecnicos 
        ORDER BY dt_inicio DESC
    """, conn)
    conn.close()
    
    return df


def partidas_com_tecnico(ano=None, limite=50):
    """Consulta partidas com o técnico correspondente"""
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT 
            p.data,
            p.competicao,
            p.rodada,
            p.adversario,
            p.local,
            p.gols,
            p.gols_adversario,
            p.resultado,
            t.nome AS tecnico
        FROM partidas p
        LEFT JOIN tecnicos t
            ON t.dt_inicio <= p.data
           AND (t.dt_fim IS NULL OR t.dt_fim >= p.data)
        WHERE 1=1
    """
    
    params = []
    if ano:
        query += " AND strftime('%Y', p.data) = ?"
        params.append(str(ano))
    
    query += " ORDER BY p.data DESC LIMIT ?"
    params.append(limite)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    return df


def estatisticas_por_tecnico():
    """Estatísticas de cada técnico"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT 
            t.nome AS tecnico,
            COUNT(*) AS jogos,
            SUM(CASE WHEN p.resultado = 'V' THEN 1 ELSE 0 END) AS vitorias,
            SUM(CASE WHEN p.resultado = 'E' THEN 1 ELSE 0 END) AS empates,
            SUM(CASE WHEN p.resultado = 'D' THEN 1 ELSE 0 END) AS derrotas,
            ROUND(AVG(CASE WHEN p.resultado = 'V' THEN 3 
                           WHEN p.resultado = 'E' THEN 1 
                           ELSE 0 END), 2) AS media_pontos,
            SUM(p.gols) AS gols_marcados,
            SUM(p.gols_adversario) AS gols_sofridos
        FROM partidas p
        LEFT JOIN tecnicos t
            ON t.dt_inicio <= p.data
           AND (t.dt_fim IS NULL OR t.dt_fim >= p.data)
        WHERE p.resultado IS NOT NULL
        GROUP BY t.nome
        ORDER BY jogos DESC
    """, conn)
    conn.close()
    
    return df


if __name__ == "__main__":
    print("\n=== 📊 TÉCNICOS ===")
    print(consultar_tecnicos())
    
    print("\n=== ⚽ ÚLTIMAS 10 PARTIDAS ===")
    print(consultar_partidas(limite=10))
    
    print("\n=== 🏆 PARTIDAS DE 2024 COM TÉCNICO ===")
    print(partidas_com_tecnico(ano=2024, limite=15))
    
    print("\n=== 📈 ESTATÍSTICAS POR TÉCNICO ===")
    print(estatisticas_por_tecnico())