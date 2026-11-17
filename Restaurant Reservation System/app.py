"""Ponto de entrada da aplicação.

Execute com:  streamlit run app.py
"""
import os

import streamlit as st

from core import config
from core.database import obter_db
from core.seed import popular
from core.services import Servico

st.set_page_config(page_title="MesaFácil · Restaurante", page_icon="🍽️", layout="wide")

from ui import cliente, cozinha, estilo, garcom, login  # noqa: E402


@st.cache_resource(show_spinner="Conectando ao banco de dados…")
def obter_servico() -> Servico:
    db = obter_db()
    popular(db)  # garante a carga inicial (100 mesas, 35 funcionários, cardápio)
    svc = Servico(db)
    demo = os.getenv("DEMO", "1" if config.MONGO_URI.startswith("mongomock://") else "0")
    if demo == "1":
        from core.demo import gerar_cenario
        gerar_cenario(svc)  # salão já movimentado para demonstração
    return svc


def main():
    estilo.aplicar()
    try:
        svc = obter_servico()
    except Exception as erro:  # noqa: BLE001
        estilo.topo("MesaFácil", "Não foi possível conectar ao MongoDB")
        st.error(f"Falha ao conectar em **{config.MONGO_URI}**.\n\n`{erro}`")
        st.info("Verifique se o MongoDB está em execução (veja o README) ou rode em modo "
                "demonstração, com os dados em memória:\n\n"
                "`MONGO_URI=mongomock:// streamlit run app.py`")
        st.stop()

    sessao = st.session_state
    if sessao.get("funcionario"):
        perfil = sessao["funcionario"]["perfil"]
        (garcom.tela if perfil == "garcom" else cozinha.tela)(svc, sessao["funcionario"])
    elif sessao.get("cliente_cpf"):
        cliente.tela(svc, sessao["cliente_cpf"])
    else:
        login.tela(svc)
    estilo.rodape()


main()
