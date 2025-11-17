import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
import requests

API_BASE_URL = "http://localhost:8000"  # ajuste se rodar em outro host/porta

def fetch_partidas_from_api(page_size: int = 500):
    """
    Busca partidas da API e retorna um DataFrame no formato esperado pelo app.
    """
    try:
        # pega muitas partidas de uma vez; ajuste se precisar de paginação real
        params = {"page": 1, "page_size": page_size}
        response = requests.get(f"{API_BASE_URL}/partidas", params=params)
        response.raise_for_status()
        data = response.json()

        partidas = data.get("partidas", [])
        if not partidas:
            st.warning("API retornou zero partidas.")
            return None

        df = pd.DataFrame(partidas)

        # Renomear colunas da API para o que o frontend espera
        # (ajuste se o CSV original usava outros nomes)
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

        # Se quiser simular exatamente o CSV, pode criar colunas extras aqui
        # df["xxx"] = None
        # df["Placar_"] = df["Gol Botafogo"].astype(str) + "x" + df["Gol Adversário"].astype(str)

        return df

    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao buscar dados da API: {e}")
        return None
    except ValueError as e:
        st.error(f"Erro ao processar dados da API: {e}")
        return None


def main():
    st.set_page_config(
        page_title="Botafogo | Aproveitamento dos treinadores",
        page_icon="⚽",
        # layout="wide",
    )

    # df = pd.read_csv('data.csv')
    df = fetch_partidas_from_api()

    if df is None or df.empty:
        st.error("Não foi possível carregar os dados da API.")
        return

    # Se ainda existir no df por algum motivo, removemos
    df = df.drop(columns=['xxx', 'Placar_'], errors='ignore')

    # Ajuste de Local:
    # sua API guarda provavelmente "Casa"/"Fora".
    # O código original esperava "(C)" e "(F)" e mapeava pra "Casa"/"Fora".
    # Agora podemos pular o mapeamento ou adaptar:
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

    # título e filtros
    dt_atualizacao = df["Data"].max()
    temporada = dt_atualizacao.year
    st.title(f"Botafogo | Aproveitamento dos treinadores {temporada}")

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
    ).round(2)
    df["Gols marcados"] = df.groupby(["Treinador"])["Gol Botafogo"].cumsum()
    df["Gols sofridos"] = df.groupby(["Treinador"])["Gol Adversário"].cumsum()
    df["Média de gols marcados"] = (df["Gols marcados"] / df["Partida"]).round(2)
    df["Média de gols sofridos"] = (df["Gols sofridos"] / df["Partida"]).round(2)

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
    colunas = [
        "Treinador",
        "Partida",
        "Aproveitamento",
        "Média de gols marcados",
        "Média de gols sofridos",
    ]

    st.subheader("Resumo por treinador")

    st.dataframe(
        df_resumo[colunas]
        .sort_values(by="Aproveitamento", ascending=False)
        .reset_index(drop=True),
        hide_index=True,
    )


if __name__ == "__main__":
    main()