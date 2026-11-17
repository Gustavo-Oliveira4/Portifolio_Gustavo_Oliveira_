"""
Interface Streamlit do Git Quality Validator - Verificacao Git.

Exibe somente a verificacao de documentacao dos projetos do
repositorio Git do time (README ou Word), usando o
`verificador_documentacao.py`.

O repositorio verificado e o mesmo definido no `config.py`
(`obter_pasta_git()`).

Uso:
    python -m streamlit run app.py
"""
import base64
import os

import pandas as pd
import streamlit as st

import verificador_documentacao as verificador

# ============================================================
# CONSTANTES VISUAIS (PADRAO ROXO)
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ASSETS = os.path.join(BASE_DIR, "assets")
LOGO_GITHUB = os.path.join(PASTA_ASSETS, "logo_github_branco.png")
ASSINATURA = (
    "Gustavo de Oliveira - Brasil"
)
ICONE = os.path.join(PASTA_ASSETS, "icon.ico")

COR_FUNDO = "#F7F5FB"
COR_PRIMARIA = "#6F42C1"      # Roxo principal
COR_SECUNDARIA = "#3D1A78"    # Roxo escuro
COR_DESTAQUE = "#9B6DFF"      # Roxo claro
COR_DESTAQUE_2 = "#D4BBFF"    # Lilas
COR_OK = "#00843D"            # Verde (status OK)
COR_FALHA = "#EF3340"         # Vermelho (status falha)
NOME_APP = "GIT QUALITY VALIDATOR"

# ============================================================
# CONFIGURACAO DA PAGINA
# ============================================================
st.set_page_config(
    page_title="Git Quality Validator",
    page_icon=ICONE if os.path.exists(ICONE) else "📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _imagem_para_base64(caminho_imagem):
    if not os.path.exists(caminho_imagem):
        return None
    with open(caminho_imagem, "rb") as arquivo_imagem:
        return base64.b64encode(arquivo_imagem.read()).decode("utf-8")


def exibir_banner_topo():
    """
    Faixa superior em degrade roxo com o logo do GitHub (branco)
    a esquerda e, a direita, o nome do aplicativo com a assinatura.
    """
    github_base64 = _imagem_para_base64(LOGO_GITHUB)

    logo_github_html = (
        f'<img src="data:image/png;base64,{github_base64}" '
        f'style="height: 82px; width: auto;">'
        if github_base64 else ""
    )

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(
                90deg, {COR_SECUNDARIA} 0%, {COR_PRIMARIA} 100%
            );
            border-radius: 16px;
            padding: 18px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
            margin-bottom: 1.5rem;
        ">
            <div style="display: flex; align-items: center; gap: 22px;">
                {logo_github_html}
            </div>
            <div style="text-align: right;">
                <div style="
                    color: #ffffff;
                    font-weight: 800;
                    font-size: 1.5rem;
                    letter-spacing: 1px;
                ">{NOME_APP}</div>
                <div style="
                    color: #ffffff;
                    opacity: 0.85;
                    font-size: 0.9rem;
                    margin-top: 4px;
                ">{ASSINATURA}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def carregar_css():
    """
    Aplica o visual roxo sobre a interface padrao do Streamlit.
    """
    css = """
    <style>
        [data-testid="stAppViewContainer"] {
            background-color: __COR_FUNDO__;
        }
        [data-testid="stHeader"] {
            background-color: rgba(0, 0, 0, 0);
        }
        [data-testid="stAppViewContainer"] .main .block-container {
            padding-top: 1.5rem;
        }
        /* Esconde a barra lateral e o menu padrao do Streamlit. */
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"],
        [data-testid="stToolbar"],
        #MainMenu,
        footer {
            display: none;
        }
        h1, h2, h3, h4 {
            color: __COR_SECUNDARIA__;
        }
        p, label, span, div {
            color: #1a1a1a;
        }

        /* Abas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #ffffff;
            border-radius: 10px 10px 0 0;
            padding: 10px 18px;
            border: 1px solid __COR_PRIMARIA__;
            border-bottom: none;
        }
        .stTabs [aria-selected="true"] {
            background-color: __COR_PRIMARIA__ !important;
        }
        .stTabs [aria-selected="true"] p {
            color: #ffffff !important;
            font-weight: 600;
        }

        /* Botao principal (Executar verificacao) */
        .stButton > button {
            border-radius: 10px;
            background-color: __COR_PRIMARIA__;
            border: 2px solid __COR_PRIMARIA__;
            font-weight: 600;
            min-height: 44px;
            transition: all 0.2s ease-in-out;
        }
        .stButton > button:hover {
            background-color: __COR_SECUNDARIA__;
            border-color: __COR_SECUNDARIA__;
        }
        .stButton > button,
        .stButton > button p,
        .stButton > button:hover p {
            color: #ffffff !important;
        }

        /* Botao de baixar CSV: letras sempre visiveis */
        .stDownloadButton > button {
            border-radius: 10px;
            background-color: __COR_OK__;
            border: 2px solid __COR_OK__;
            font-weight: 700;
            min-height: 44px;
            padding: 0.5rem 1.4rem;
            transition: all 0.2s ease-in-out;
        }
        .stDownloadButton > button:hover,
        .stDownloadButton > button:focus,
        .stDownloadButton > button:active {
            background-color: __COR_SECUNDARIA__;
            border-color: __COR_SECUNDARIA__;
        }
        .stDownloadButton > button,
        .stDownloadButton > button p,
        .stDownloadButton > button span,
        .stDownloadButton > button div,
        .stDownloadButton > button:hover p,
        .stDownloadButton > button:focus p {
            color: #ffffff !important;
        }

        .stAlert {
            border-radius: 10px;
        }
        .faixa-destaque {
            height: 6px;
            width: 100%;
            border-radius: 4px;
            background: linear-gradient(
                90deg,
                __COR_PRIMARIA__ 0%,
                __COR_DESTAQUE__ 50%,
                __COR_DESTAQUE_2__ 100%
            );
            margin: 1rem 0 1.5rem 0;
        }

        /* Cartoes de resumo */
        .cartao-doc {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 14px 18px;
            border: 1px solid __COR_PRIMARIA__;
            border-left: 8px solid __COR_PRIMARIA__;
        }
        .cartao-doc.ok {
            border-color: __COR_OK__;
        }
        .cartao-doc.falha {
            border-color: __COR_FALHA__;
        }
        .cartao-doc .numero {
            font-size: 2rem;
            font-weight: 800;
            color: __COR_SECUNDARIA__;
            line-height: 1.1;
        }
        .cartao-doc .rotulo {
            font-size: 0.85rem;
            font-weight: 600;
            color: __COR_PRIMARIA__;
            text-transform: uppercase;
        }
    </style>
    """
    css = (
        css.replace("__COR_FUNDO__", COR_FUNDO)
        .replace("__COR_PRIMARIA__", COR_PRIMARIA)
        .replace("__COR_SECUNDARIA__", COR_SECUNDARIA)
        .replace("__COR_DESTAQUE_2__", COR_DESTAQUE_2)
        .replace("__COR_DESTAQUE__", COR_DESTAQUE)
        .replace("__COR_OK__", COR_OK)
        .replace("__COR_FALHA__", COR_FALHA)
    )
    st.markdown(css, unsafe_allow_html=True)


# ============================================================
# FUNCOES DE APOIO
# ============================================================
def sem_acento(texto):
    return verificador.remover_acentos(texto)


def cartao_doc(numero, rotulo, classe=""):
    st.markdown(
        f"""
        <div class="cartao-doc {classe}">
            <div class="numero">{numero}</div>
            <div class="rotulo">{rotulo}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_visual(status):
    if status == verificador.STATUS_OK:
        return f"🟢 {status}"
    return f"🔴 {status}"


# ============================================================
# TELA
# ============================================================
carregar_css()
exibir_banner_topo()

st.subheader("Verificacao Git - Documentacao dos Projetos")
st.write(
    "Verifica quais projetos do repositorio Git do time possuem "
    "documentacao (arquivo README ou documento Word)."
)
st.caption(f"📁 Repositorio: {sem_acento(verificador.PASTA_GIT)}")

if st.button(
    "▶️ Executar verificacao",
    use_container_width=True,
    key="btn_docs",
):
    with st.spinner("Verificando projetos..."):
        try:
            st.session_state["resultado_docs"] = (
                verificador.executar_verificacao()
            )
        except FileNotFoundError as erro:
            st.session_state.pop("resultado_docs", None)
            st.error(f"❌ {sem_acento(erro)}")

resultado = st.session_state.get("resultado_docs")

if not resultado:
    st.info("Clique em **Executar verificacao** para gerar o relatorio.")
    st.stop()

if not resultado["git_disponivel"]:
    st.warning(
        "Git nao encontrado neste computador: o autor dos projetos "
        "aparecera como 'Nao informado'.\n\n"
        "**Como resolver:** instale o Git for Windows (Portal da "
        "Empresa / TI) e reabra o app. Se o Git ja estiver instalado "
        "em outra pasta, defina a variavel de ambiente `GIT_EXE` com "
        "o caminho completo do `git.exe`."
    )

if not resultado["projetos"]:
    st.warning("Nenhum projeto encontrado na estrutura Pais / Area / Projeto.")
    st.stop()

# ------------------------------------------------------------
# Resumo
# ------------------------------------------------------------
total = len(resultado["projetos"])
qtd_ok = len(resultado["projetos_ok"])
qtd_falha = len(resultado["projetos_falha"])
percentual = round(qtd_ok / total * 100) if total else 0

st.markdown('<div class="faixa-destaque"></div>', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
    cartao_doc(total, "Projetos verificados")
with col2:
    cartao_doc(qtd_ok, verificador.STATUS_OK, "ok")
with col3:
    cartao_doc(qtd_falha, verificador.STATUS_FALHA, "falha")
with col4:
    cartao_doc(f"{percentual}%", "Projetos documentados")

st.write("")

# ------------------------------------------------------------
# Tabelas
# ------------------------------------------------------------
aba_falha, aba_ok, aba_estrutura = st.tabs([
    f"Sem documentacao ({qtd_falha})",
    f"Com documentacao ({qtd_ok})",
    "Pastas de estrutura",
])


def nome_autor(autor):
    nome = autor["nome"]
    return "Nao informado" if nome == "Not informed" else sem_acento(nome)


with aba_falha:
    if resultado["projetos_falha"]:
        tabela_falha = pd.DataFrame([
            {
                "Status": status_visual(verificador.STATUS_FALHA),
                "Projeto": sem_acento(d["projeto"]),
                "Localizacao": sem_acento(d["localizacao"]),
                "Adicionado por": nome_autor(d["autor"]),
                "E-mail": d["autor"]["email"],
                "Data": d["autor"]["data"],
            }
            for d in resultado["projetos_falha"]
        ])
        st.dataframe(tabela_falha, use_container_width=True, hide_index=True)

        tabela_csv = tabela_falha.copy()
        tabela_csv["Status"] = verificador.STATUS_FALHA
        st.download_button(
            "⬇️ Baixar lista em CSV",
            tabela_csv.to_csv(index=False, sep=";").encode("utf-8-sig"),
            file_name="projetos_sem_documentacao.csv",
            mime="text/csv",
            key="btn_csv",
        )
    else:
        st.success("✅ Todos os projetos possuem documentacao.")

with aba_ok:
    if resultado["projetos_ok"]:
        tabela_ok = pd.DataFrame([
            {
                "Status": status_visual(verificador.STATUS_OK),
                "Projeto": sem_acento(d["projeto"]),
                "Localizacao": sem_acento(d["localizacao"]),
                "Tipo": d["tipo_doc"],
                "Documento": sem_acento(d["readme"]),
            }
            for d in resultado["projetos_ok"]
        ])
        st.dataframe(tabela_ok, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum projeto com documentacao.")

with aba_estrutura:
    st.markdown("**Pastas de estrutura (nao avaliadas)**")
    st.dataframe(
        pd.DataFrame({
            "Pasta": [sem_acento(p) for p in resultado["pastas_estrutura"]]
        }),
        use_container_width=True,
        hide_index=True,
    )
    if resultado["arquivos_soltos"]:
        st.markdown("**Arquivos soltos fora de projetos**")
        st.dataframe(
            pd.DataFrame({
                "Arquivo": [sem_acento(a) for a in resultado["arquivos_soltos"]]
            }),
            use_container_width=True,
            hide_index=True,
        )
