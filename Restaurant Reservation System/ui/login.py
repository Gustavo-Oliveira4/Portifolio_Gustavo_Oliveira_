"""Tela inicial: campos Funcionário e Cliente lado a lado (Seção 3.1)."""
import streamlit as st

from core.utils import limpar_cpf, validar_cpf
from ui import estilo


def tela(svc):
    estilo.topo("🍽️ MesaFácil", "Reservas, ocupação de mesas e acompanhamento de pedidos",
                "100 mesas · Térreo e Mezanino")

    col_func, col_cli = st.columns(2, gap="large")

    with col_func:
        st.markdown('<div class="cartao cartao-acesso"><span class="rotulo">Equipe</span>'
                    '<h3>Funcionário</h3>Garçons e cozinha acessam com matrícula e senha.</div>',
                    unsafe_allow_html=True)
        with st.form("login_funcionario", border=False):
            matricula = st.text_input("Matrícula", placeholder="Ex.: G01 ou C01")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", type="primary", width="stretch"):
                usuario = svc.autenticar(matricula, senha)
                if usuario:
                    st.session_state["funcionario"] = usuario
                    st.rerun()
                st.error("Matrícula ou senha inválidas.")

    with col_cli:
        st.markdown('<div class="cartao cartao-acesso cliente"><span class="rotulo">Clientes</span>'
                    '<h3>Cliente</h3>Faça sua reserva e acompanhe seus pedidos usando apenas o CPF.</div>',
                    unsafe_allow_html=True)
        with st.form("login_cliente", border=False):
            cpf = st.text_input("CPF", placeholder="000.000.000-00", max_chars=14)
            st.caption("Não é necessário criar conta nem senha.")
            if st.form_submit_button("Acessar", type="primary", width="stretch"):
                if validar_cpf(cpf):
                    st.session_state["cliente_cpf"] = limpar_cpf(cpf)
                    st.rerun()
                st.error("CPF inválido. Confira os 11 dígitos.")

    with st.expander("Acessos de demonstração"):
        st.markdown(
            "- **Garçons:** `G01` a `G30` (G01–G21 no térreo, G22–G30 no mezanino) · senha `garcom123`\n"
            "- **Cozinha (totens):** `C01` a `C05` · senha `chef123`\n"
            "- **Cliente:** qualquer CPF válido, por exemplo `529.982.247-25`")
