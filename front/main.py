import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
import requests
from datetime import date

API_BASE_URL = "http://api:8000"  

def fetch_ultima_partida_date():
    """
    Busca a data da última partida registrada na API.
    """
    try:
        response = requests.get(f"{API_BASE_URL}/partidas/ultima")
        response.raise_for_status()
        data = response.json()
        ultima_data_str = data.get("data")
        if ultima_data_str:
            return pd.to_datetime(ultima_data_str, format="%Y-%m-%d")
        else:
            st.warning("API não retornou a data da última partida.")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao buscar dados da API: {e}")
        return None
    except ValueError as e:
        st.error(f"Erro ao processar dados da API: {e}")
        return None

def fetch_partidas_from_api(ano, page_size: int = 500):
    """
    Busca partidas da API e retorna um DataFrame no formato esperado pelo app.
    """
    try:
        params = {"page": 1, "page_size": page_size}
        response = requests.get(f"{API_BASE_URL}/partidas/ano/{ano}", params=params)
        response.raise_for_status()
        data = response.json()

        partidas = data.get("partidas", [])
        if not partidas:
            st.warning("API retornou zero partidas.")
            return None

        df = pd.DataFrame(partidas)

        # Renomear colunas da API para o que o frontend espera
        df.rename(
            columns={
                "data": "Data",
                "competicao": "Campeonato",
                "tecnico": "Treinador",
                "gols": "Gol Botafogo",
                "gols_adversario": "Gol Adversário",
                "local": "Local",
                "resultado": "Resultado",
            },
            inplace=True,
        )

        return df

    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao buscar dados da API: {e}")
        return None
    except ValueError as e:
        st.error(f"Erro ao processar dados da API: {e}")
        return None


def main():
    st.set_page_config(
        page_title="Treinadores Botafogo",
        page_icon="⚽",
    )

    # Verificar a data da última partida na API
    ultima_data = fetch_ultima_partida_date()
    if ultima_data is None:
        ultima_data = date.today()
    
    ano_para_busca = ultima_data.year

    st.title(f"Botafogo - Análise dos treinadores")
    st.write(f"Data da última partida registrada: {ultima_data.strftime('%d/%m/%Y')}")

    option = st.selectbox(
        "Selecione a temporada para análise:",
        options=list(range(ano_para_busca, 2024 - 1, -1)),
        index=0,
    )

    df = fetch_partidas_from_api(option)

    if df is None or df.empty:
        st.error("Não foi possível carregar os dados da API.")
        return

    # Se ainda existir no df por algum motivo, removemos
    df = df.drop(columns=['xxx', 'Placar_'], errors='ignore')

    # Substituir NaN por 0
    df.fillna(0, inplace=True)

    # Definir Resultado com base nos gols
    df["Resultado"] = df.apply(
        lambda row: "V"
        if row["Gol Botafogo"] > row["Gol Adversário"]
        else ("E" if row["Gol Botafogo"] == row["Gol Adversário"] else "D"),
        axis=1,
    )

    # Ajuste de Local:
    mapa_local = {
        "(C)": "Casa",
        "(F)": "Fora",
        "Casa": "Casa",
        "Fora": "Fora",
    }
    df["Local"] = df["Local"].map(mapa_local).fillna(df["Local"])

    # Pontos conforme resultado
    df["Pontos"] = df["Resultado"].map({"V": 3, "E": 1, "D": 0})

    # Data: API retorna "YYYY-MM-DD"
    df["Data"] = pd.to_datetime(df["Data"], format="%Y-%m-%d")
    df.sort_values(by=["Data"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    df["Campeonato"] = df["Campeonato"].apply(
        lambda x: x.replace("Campeonato ", "").replace(" - Taça Rio", "").strip()
    )
    # Filtros
    campeonatos = np.sort(df["Campeonato"].unique())
    camp_selecionado = st.pills(
        "Selecione um campeonato:", campeonatos, selection_mode="multi"
    )
    if camp_selecionado:
        df = df[df["Campeonato"].isin(camp_selecionado)]

    # Garantir que ainda temos algo após o filtro
    if df.empty:
        st.warning("Nenhuma partida encontrada com os filtros selecionados.")
        return

    df["Partida"] = df.groupby(["Treinador"]).cumcount() + 1
    df["Pontos acumulados"] = df.groupby(["Treinador"])["Pontos"].cumsum()
    df["Aproveitamento"] = (
        df["Pontos acumulados"] / (df["Partida"] * 3) * 100
    ).round(1)
    df["Gols marcados"] = df.groupby(["Treinador"])["Gol Botafogo"].cumsum()
    df["Gols sofridos"] = df.groupby(["Treinador"])["Gol Adversário"].cumsum()
    df["Média de gols marcados"] = (df["Gols marcados"] / df["Partida"]).round(1)
    df["Média de gols sofridos"] = (df["Gols sofridos"] / df["Partida"]).round(1)

    min_partidas = df["Partida"].min()
    max_partidas = df["Partida"].max()

    tab1, tab2, tab3 = st.tabs(
        ["Aproveitamento", "Gols marcados", "Gols sofridos"]
    )

    with tab1:
        st.subheader("Aproveitamento ao longo do tempo")

        chart = (
            alt.Chart(df)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "Partida:Q",
                    scale=alt.Scale(domain=[min_partidas, max_partidas]),
                    title="Partida",
                ),
                y=alt.Y("Aproveitamento:Q", title="Aproveitamento (%)"),
                color="Treinador:N",
            )
            .properties(height=700)
        )
        st.altair_chart(chart, use_container_width=True)

    with tab2:
        st.subheader("Média de gols marcados ao longo do tempo")

        chart = (
            alt.Chart(df)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "Partida:Q",
                    scale=alt.Scale(domain=[min_partidas, max_partidas]),
                    title="Partida",
                ),
                y=alt.Y("Média de gols marcados:Q", title="Gols marcados"),
                color="Treinador:N",
            )
            .properties(height=700)
        )
        st.altair_chart(chart, use_container_width=True)

    with tab3:
        st.subheader("Média de gols sofridos ao longo do tempo")

        chart = (
            alt.Chart(df)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "Partida:Q",
                    scale=alt.Scale(domain=[min_partidas, max_partidas]),
                    title="Partida",
                ),
                y=alt.Y("Média de gols sofridos:Q", title="Gols sofridos"),
                color="Treinador:N",
            )
            .properties(height=700)
        )
        st.altair_chart(chart, use_container_width=True)

    st.markdown("---")

    # Tabela resumo por treinador
    df_resumo = df.loc[df.groupby("Treinador")["Partida"].idxmax()]
    
    # Calcular vitórias, empates e derrotas por treinador
    resultados_por_treinador = df.groupby("Treinador")["Resultado"].value_counts().unstack(fill_value=0)
    resultados_por_treinador = resultados_por_treinador.rename(columns={"V": "Vitórias", "E": "Empates", "D": "Derrotas"})
    
    # Garantir que todas as colunas existam (caso algum treinador não tenha V, E ou D)
    for col in ["Vitórias", "Empates", "Derrotas"]:
        if col not in resultados_por_treinador.columns:
            resultados_por_treinador[col] = 0
    
    # Merge com o resumo
    df_resumo = df_resumo.merge(resultados_por_treinador, on="Treinador", how="left")
    
    df_resumo = df_resumo[
        [
            "Treinador",
            "Partida",
            "Vitórias",
            "Empates",
            "Derrotas",
            "Aproveitamento",
            "Média de gols marcados",
            "Média de gols sofridos",
        ]
    ].rename(
        columns={
            "Partida": "Partidas",
            "Média de gols marcados": "Gols marcados/jogo",
            "Média de gols sofridos": "Gols sofridos/jogo",
        }
    )

    df_resumo["Resultados"] = (
        df_resumo["Vitórias"].astype(str) + "V, " +
        df_resumo["Empates"].astype(str) + "E, " +
        df_resumo["Derrotas"].astype(str) + "D"
    )

    df_resumo.sort_values(by="Aproveitamento", ascending=False, inplace=True)

    df_resumo["Aproveitamento"] = df_resumo["Aproveitamento"].round(1).astype(str) + " %"
    df_resumo["Gols marcados/jogo"] = df_resumo["Gols marcados/jogo"].astype(str)
    df_resumo["Gols sofridos/jogo"] = df_resumo["Gols sofridos/jogo"].astype(str)
    df_resumo["Partidas"] = df_resumo["Partidas"].astype(int).astype(str)

    colunas_resumo = [
        "Treinador",
        "Partidas",
        "Resultados",
        "Aproveitamento",
        "Gols marcados/jogo",
        "Gols sofridos/jogo",
    ]

    st.subheader("Resumo por treinador")

    st.dataframe(
        df_resumo[colunas_resumo]
        .reset_index(drop=True),
        hide_index=True,
    )

    st.markdown("---")

    # Tabela de partidas
    df_partidas = df[
        [
            "Treinador",
            "Data",
            "Campeonato",
            "rodada",
            "Local",
            "adversario",
            "Gol Botafogo",
            "Gol Adversário",
            "Resultado",
            "publico",
        ]
    ].rename(
        columns={
            "Gol Botafogo": "Gols marcados",
            "Gol Adversário": "Gols sofridos",
            "rodada": "Rodada",
            "adversario": "Adversário",
            "publico": "Público",
        }
    ).sort_values(by="Data", ascending=False).reset_index(drop=True)

    # Formatações
    df_partidas["Data"] = df_partidas["Data"].dt.strftime("%d/%m/%Y")

    def format_publico(x):
        try:
            if pd.notnull(x):
                return f"{int(float(x)):,}".replace(",", ".")
            return "N/A"
        except (ValueError, TypeError):
            return "N/A"

    df_partidas["Público"] = df_partidas["Público"].apply(format_publico)
    df_partidas["Rodada"] = df_partidas["Rodada"].replace(0, "N/A")
    df_partidas["Placar"] = df_partidas["Gols marcados"].astype(int).astype(str) + " x " + df_partidas["Gols sofridos"].astype(int).astype(str)
    df_partidas["Resultado"] = df_partidas["Resultado"].map({"V": "🟢 Vitória", "E": "⚪ Empate", "D": "🔴 Derrota"})
    df_partidas = df_partidas[
        [
            "Treinador",
            "Data",
            "Campeonato",
            "Rodada",
            "Local",
            "Adversário",
            "Placar",
            "Resultado",
        ]
    ]

    st.subheader("Partidas")    
    st.dataframe(
        df_partidas,
        hide_index=True,
    )


if __name__ == "__main__":
    main()