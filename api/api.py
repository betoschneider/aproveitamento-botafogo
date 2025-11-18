from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import sqlite3
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import date
import os

DB_PATH = os.getenv("DB_PATH", "/data/botafogo.db")

app = FastAPI(
    title="API Botafogo - Partidas e Técnicos",
    description="API para consultar partidas, técnicos e estatísticas do Botafogo de Futebol e Regatas.",
    version="1.0.0"
)

@contextmanager
def get_db_connection():
    """Context manager para conexão SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def dict_factory(cursor, row):
    """Converte resultado SQLite em dicionário"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

@app.get("/")
def root():
    """Endpoint raiz"""
    return {
        "message": "API Botafogo - Partidas e Técnicos",
        "endpoints": {
            "partidas": "/partidas",
            "partidas_por_ano": "/partidas/ano/{ano}",
            "partidas_por_tecnico": "partidas/tecnico/{tecnico_id}",
            "tecnicos": "/tecnicos",
            "estatisticas": "/estatisticas",
            "estatisticas_por_ano": "/estatisticas/ano/{ano}",
            "estatisticas_por_tecnico": "/estatisticas/tecnico/{tecnico_id}",
            "ultima_partida": "/ultima_partida",
        }
    }

@app.get("/partidas")
def get_partidas(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(10, ge=1, le=500, description="Registros por página"),
    ano: Optional[int] = Query(None, description="Filtrar por ano"),
    competicao: Optional[str] = Query(None, description="Filtrar por competição")
):
    """Retorna lista de partidas com filtros e paginação"""
    offset = (page - 1) * page_size

    with get_db_connection() as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()


        base_query = """
            FROM partidas p
            LEFT JOIN tecnicos t
                ON t.dt_inicio <= p.data
               AND (t.dt_fim IS NULL OR t.dt_fim >= p.data)
            WHERE 1=1
        """
        params = []

        if ano:
            base_query += " AND strftime(%Y, data) = ?"
            params.append(str(ano))

        if competicao:
            base_query += " AND competicao = ?"
            params.append(competicao)

        # Total de registros
        count_query = f"SELECT COUNT(*) AS total {base_query}"
        cursor.execute(count_query, params)
        total_registros = cursor.fetchone()["total"]

        # Dados paginados
        data_query = f"""
            SELECT 
                p.id,
                p.data,
                p.dia,
                p.competicao,
                p.rodada,
                p.adversario,
                p.local,
                p.gols,
                p.gols_adversario,
                p.resultado,
                p.publico,
                p.ranking,
                p.ranking_adversario,
                t.id AS tecnico_id,
                t.nome AS tecnico 
            {base_query}
            ORDER BY data DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(data_query, params + [page_size, offset])
        partidas = cursor.fetchall()

        total_paginas = (total_registros + page_size - 1) // page_size if total_registros else 0

    return {
        "total_registros": total_registros,
        "page": page,
        "page_size": page_size,
        "total_paginas": total_paginas,
        "has_next": page < total_paginas,
        "has_previous": page > 1,
        "filtros": {
            "ano": ano,
            "competicao": competicao
        },
        "partidas": partidas
    }

@app.get("/partidas/ano/{ano}")
def get_partidas_por_ano_com_tecnico(
    ano: int,
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(50, ge=1, le=500, description="Registros por página")
):
    """Retorna partidas de um ano específico com técnicos"""
    
    offset = (page - 1) * page_size
    
    with get_db_connection() as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        base_query = """
            FROM partidas p
            LEFT JOIN tecnicos t
                ON t.dt_inicio <= p.data
               AND (t.dt_fim IS NULL OR t.dt_fim >= p.data)
            WHERE strftime('%Y', p.data) = ?
        """
        
        # Total de registros
        count_query = f"SELECT COUNT(*) AS total {base_query}"
        cursor.execute(count_query, (str(ano),))
        total_registros = cursor.fetchone()["total"]
        
        if total_registros == 0:
            raise HTTPException(status_code=404, detail=f"Nenhuma partida encontrada para o ano {ano}")
        
        # Dados paginados
        data_query = f"""
            SELECT 
                p.id,
                p.data,
                p.dia,
                p.competicao,
                p.rodada,
                p.adversario,
                p.local,
                p.gols,
                p.gols_adversario,
                p.resultado,
                p.publico,
                p.ranking,
                p.ranking_adversario,
                t.id AS tecnico_id,
                t.nome AS tecnico
            {base_query}
            ORDER BY p.data DESC
            LIMIT ? OFFSET ?
        """
        
        cursor.execute(data_query, (str(ano), page_size, offset))
        partidas = cursor.fetchall()
        
        total_paginas = (total_registros + page_size - 1) // page_size
        
        return {
            "ano": ano,
            "total_registros": total_registros,
            "page": page,
            "page_size": page_size,
            "total_paginas": total_paginas,
            "has_next": page < total_paginas,
            "has_previous": page > 1,
            "partidas": partidas
        }

@app.get("/partidas/tecnico/{tecnico_id}")
def get_partidas_por_tecnico(
    tecnico_id: int,
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(50, ge=1, le=500, description="Registros por página")
):
    """
    Retorna todas as partidas de um técnico específico
    """
    offset = (page - 1) * page_size

    with get_db_connection() as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        # Verificar se técnico existe
        cursor.execute("SELECT * FROM tecnicos WHERE id = ?", (tecnico_id,))
        tecnico = cursor.fetchone()
        
        if not tecnico:
            raise HTTPException(status_code=404, detail=f"Técnico com ID {tecnico_id} não encontrado")
        
        # Total de registros
        count_query = """
            SELECT COUNT(*) AS total
            FROM partidas p
            INNER JOIN tecnicos t
                ON t.dt_inicio <= p.data
               AND (t.dt_fim IS NULL OR t.dt_fim >= p.data)
            WHERE t.id = ?
        """
        cursor.execute(count_query, (tecnico_id,))
        total_registros = cursor.fetchone()["total"]

        # Buscar partidas paginadas
        data_query = """
            SELECT 
                p.*,
                t.nome AS tecnico
            FROM partidas p
            INNER JOIN tecnicos t
                ON t.dt_inicio <= p.data
               AND (t.dt_fim IS NULL OR t.dt_fim >= p.data)
            WHERE t.id = ?
            ORDER BY p.data DESC
            LIMIT ? OFFSET ?
        """
        
        cursor.execute(data_query, (tecnico_id, page_size, offset))
        partidas = cursor.fetchall()

        total_paginas = (total_registros + page_size - 1) // page_size if total_registros else 0

        return {
            "tecnico": tecnico,
            "total_registros": total_registros,
            "page": page,
            "page_size": page_size,
            "total_paginas": total_paginas,
            "has_next": page < total_paginas,
            "has_prev": page > 1,
            "partidas": partidas
        }


@app.get("/tecnicos")
def get_tecnicos():
    """
    Retorna lista de todos os técnicos
    """
    with get_db_connection() as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tecnicos 
            ORDER BY dt_inicio DESC
        """)
        tecnicos = cursor.fetchall()
        
        return {
            "total": len(tecnicos),
            "tecnicos": tecnicos
        }


@app.get("/estatisticas")
def get_estatisticas():
    """
    Retorna estatísticas de todos os técnicos incluindo aproveitamento
    """
    with get_db_connection() as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        query = """
            SELECT 
                t.id AS tecnico_id,
                t.nome AS tecnico,
                t.dt_inicio,
                t.dt_fim,
                COUNT(*) AS jogos,
                SUM(CASE WHEN p.resultado = 'V' THEN 1 ELSE 0 END) AS vitorias,
                SUM(CASE WHEN p.resultado = 'E' THEN 1 ELSE 0 END) AS empates,
                SUM(CASE WHEN p.resultado = 'D' THEN 1 ELSE 0 END) AS derrotas,
                SUM(CASE WHEN p.resultado = 'V' THEN 3 
                         WHEN p.resultado = 'E' THEN 1 
                         ELSE 0 END) AS pontos_conquistados,
                COUNT(*) * 3 AS pontos_possiveis,
                ROUND(
                    (SUM(CASE WHEN p.resultado = 'V' THEN 3 
                              WHEN p.resultado = 'E' THEN 1 
                              ELSE 0 END) * 100.0) / (COUNT(*) * 3), 
                    2
                ) AS aproveitamento,
                SUM(p.gols) AS gols_marcados,
                SUM(p.gols_adversario) AS gols_sofridos,
                SUM(p.gols) - SUM(p.gols_adversario) AS saldo_gols
            FROM partidas p
            LEFT JOIN tecnicos t
                ON t.dt_inicio <= p.data
               AND (t.dt_fim IS NULL OR t.dt_fim >= p.data)
            WHERE p.resultado IS NOT NULL
            GROUP BY t.id, t.nome, t.dt_inicio, t.dt_fim
            ORDER BY aproveitamento DESC, jogos DESC
        """
        
        cursor.execute(query)
        estatisticas = cursor.fetchall()
        
        return {
            "total_tecnicos": len(estatisticas),
            "estatisticas": estatisticas
        }


@app.get("/estatisticas/tecnico/{tecnico_id}")
def get_estatisticas_tecnico(tecnico_id: int):
    """
    Retorna estatísticas detalhadas de um técnico específico
    """
    with get_db_connection() as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        # Verificar se técnico existe
        cursor.execute("SELECT * FROM tecnicos WHERE id = ?", (tecnico_id,))
        tecnico = cursor.fetchone()
        
        if not tecnico:
            raise HTTPException(status_code=404, detail=f"Técnico com ID {tecnico_id} não encontrado")
        
        # Estatísticas gerais
        query = """
            SELECT 
                COUNT(*) AS jogos,
                SUM(CASE WHEN p.resultado = 'V' THEN 1 ELSE 0 END) AS vitorias,
                SUM(CASE WHEN p.resultado = 'E' THEN 1 ELSE 0 END) AS empates,
                SUM(CASE WHEN p.resultado = 'D' THEN 1 ELSE 0 END) AS derrotas,
                SUM(CASE WHEN p.resultado = 'V' THEN 3 
                         WHEN p.resultado = 'E' THEN 1 
                         ELSE 0 END) AS pontos_conquistados,
                COUNT(*) * 3 AS pontos_possiveis,
                ROUND(
                    (SUM(CASE WHEN p.resultado = 'V' THEN 3 
                              WHEN p.resultado = 'E' THEN 1 
                              ELSE 0 END) * 100.0) / (COUNT(*) * 3), 
                    2
                ) AS aproveitamento,
                SUM(p.gols) AS gols_marcados,
                SUM(p.gols_adversario) AS gols_sofridos,
                SUM(p.gols) - SUM(p.gols_adversario) AS saldo_gols
            FROM partidas p
            INNER JOIN tecnicos t
                ON t.dt_inicio <= p.data
               AND (t.dt_fim IS NULL OR t.dt_fim >= p.data)
            WHERE t.id = ? AND p.resultado IS NOT NULL
        """
        
        cursor.execute(query, (tecnico_id,))
        stats = cursor.fetchone()
        
        # Estatísticas por competição
        query_competicao = """
            SELECT 
                p.competicao,
                COUNT(*) AS jogos,
                SUM(CASE WHEN p.resultado = 'V' THEN 1 ELSE 0 END) AS vitorias,
                SUM(CASE WHEN p.resultado = 'E' THEN 1 ELSE 0 END) AS empates,
                SUM(CASE WHEN p.resultado = 'D' THEN 1 ELSE 0 END) AS derrotas,
                SUM(CASE WHEN p.resultado = 'V' THEN 3 
                         WHEN p.resultado = 'E' THEN 1 
                         ELSE 0 END) AS pontos_conquistados,
                COUNT(*) * 3 AS pontos_possiveis,
                ROUND(
                    (SUM(CASE WHEN p.resultado = 'V' THEN 3 
                              WHEN p.resultado = 'E' THEN 1 
                              ELSE 0 END) * 100.0) / (COUNT(*) * 3), 
                    2
                ) AS aproveitamento,
                SUM(p.gols) AS gols_marcados,
                SUM(p.gols_adversario) AS gols_sofridos
            FROM partidas p
            INNER JOIN tecnicos t
                ON t.dt_inicio <= p.data
               AND (t.dt_fim IS NULL OR t.dt_fim >= p.data)
            WHERE t.id = ? AND p.resultado IS NOT NULL
            GROUP BY p.competicao
            ORDER BY jogos DESC
        """
        
        cursor.execute(query_competicao, (tecnico_id,))
        stats_competicao = cursor.fetchall()
        
        return {
            "tecnico": tecnico,
            "estatisticas_gerais": stats,
            "estatisticas_por_competicao": stats_competicao
        }

@app.get("/ultima_partida")
def get_ultima_partida():
    """
    Retorna a última partida registrada
    """
    with get_db_connection() as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        query = """
            SELECT 
                p.id,
                p.data,
                p.dia,
                p.competicao,
                p.rodada,
                p.adversario,
                p.local,
                p.gols,
                p.gols_adversario,
                p.resultado,
                p.publico,
                p.ranking,
                p.ranking_adversario,
                t.id AS tecnico_id,
                t.nome AS tecnico 
            FROM partidas p
            LEFT JOIN tecnicos t
                ON t.dt_inicio <= p.data
               AND (t.dt_fim IS NULL OR t.dt_fim >= p.data)
            ORDER BY p.data DESC
            LIMIT 1
        """
        
        cursor.execute(query)
        ultima_partida = cursor.fetchone()
        
        if not ultima_partida:
            raise HTTPException(status_code=404, detail="Nenhuma partida encontrada")
        
        return ultima_partida

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
