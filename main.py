import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
# from datetime import datetime

def main():
    df = pd.read_csv('data.csv')
    df = df.drop(columns=['xxx', 'Placar_'])

    df['Local'] = df['Local'].map({'(C)': 'Casa', '(F)': 'Fora'})
    df['Pontos'] = df['Resultado'].map({'V': 3, 'E': 1, 'D': 0})
    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
    df.sort_values(by=['Data'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Configurações da página
    st.set_page_config(
        page_title="Botafogo | Aproveitamento dos treinadores",
        page_icon="⚽",
        # layout="wide",
    )

    # título e filtros
    dt_atualizacao = df['Data'].max()
    temporada = dt_atualizacao.year
    st.title(f"Botafogo | Aproveitamento dos treinadores {temporada}")

    campeonatos = np.sort(df['Campeonato'].unique())
    # camp_selecionado = st.multiselect("Selecione um campeonato:", campeonatos, placeholder="Todos", max_selections=1)
    camp_selecionado = st.pills("Selecione um campeonato:", campeonatos, selection_mode="multi")
    if camp_selecionado:
        df = df[df['Campeonato'].isin(camp_selecionado)]

    
    df['Partida'] = (
        df.groupby(['Treinador']).cumcount() + 1
    )
    df['Pontos acumulados'] = (
        df.groupby(['Treinador'])['Pontos'].cumsum()
    )
    df['Aproveitamento'] = (
        df['Pontos acumulados'] / (df['Partida'] * 3) * 100
    ).round(2)
    df['Gols marcados'] = (
        df.groupby(['Treinador'])['Gol Botafogo'].cumsum()
    )
    df['Gols sofridos'] = (
        df.groupby(['Treinador'])['Gol Adversário'].cumsum()
    )
    df['Média de gols marcados'] = (df['Gols marcados'] / df['Partida']).round(2)
    df['Média de gols sofridos'] = (df['Gols sofridos'] / df['Partida']).round(2)

    min_partidas = df['Partida'].min()
    max_partidas = df['Partida'].max()

    # Aproveitamento ao longo do tempo
    st.subheader("Aproveitamento ao longo do tempo")

    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X("Partida:Q", scale=alt.Scale(domain=[min_partidas, max_partidas]), title="Partida"),
            y=alt.Y("Aproveitamento:Q", title="Aproveitamento (%)"),
            color="Treinador:N",
        )
        .properties(height=700)
    )
    st.altair_chart(chart, use_container_width=True)
    st.markdown("---")

    # Média de gols marcados ao longo do tempo
    st.subheader("Média de gols marcados ao longo do tempo")

    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X("Partida:Q", scale=alt.Scale(domain=[min_partidas, max_partidas]), title="Partida"),
            y=alt.Y("Média de gols marcados:Q", title="Gols marcados"),
            color="Treinador:N",
        )
        .properties(height=700)
    )
    st.altair_chart(chart, use_container_width=True)
    st.markdown("---")

    # Média de gols sofridos ao longo do tempo
    st.subheader("Média de gols sofridos ao longo do tempo")

    chart = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X("Partida:Q", scale=alt.Scale(domain=[min_partidas, max_partidas]), title="Partida"),
            y=alt.Y("Média de gols sofridos:Q", title="Gols sofridos"),
            color="Treinador:N",
        )
        .properties(height=700)
    )
    st.altair_chart(chart, use_container_width=True)
    st.markdown("---")
    
    # Tabela resumo por treinador
    df = df.loc[df.groupby("Treinador")["Partida"].idxmax()]
    colunas = [ "Treinador", "Partida", "Aproveitamento", "Média de gols marcados", "Média de gols sofridos"]

    st.subheader("Resumo por treinador")

    st.dataframe(df[colunas].sort_values(by="Aproveitamento", ascending=False).reset_index(drop=True), hide_index=True)

    

if __name__ == "__main__":
    main()