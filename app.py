from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import sqlite3
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import date

DB_PATH = "botafogo.db"

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
            "estatisticas_por_tecnico": "/estatisticas/tecnico/{tecnico_id}"
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)