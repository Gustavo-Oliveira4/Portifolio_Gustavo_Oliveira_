"""Identidade visual: vermelho, laranja, amarelo e branco."""
import html

import streamlit as st

VERMELHO = "#D32F2F"
VERMELHO_ESCURO = "#B71C1C"
LARANJA = "#F57C00"
AMARELO = "#FFC107"
AMARELO_CLARO = "#FFF8E1"
BRANCO = "#FFFFFF"

# Cores dos estados da mesa (Quadro 8 do documento de requisitos)
COR_MESA = {
    "livre": ("#2E7D32", "#E8F5E9"),
    "reservada": ("#1565C0", "#E3F2FD"),
    "ocupada_nao_atendida": ("#C62828", "#FFEBEE"),
    "ocupada_atendida": ("#E69500", "#FFF8DC"),
    "em_liberacao": ("#616161", "#F5F5F5"),
}
COR_PEDIDO = {
    "recebido": "#757575", "em_preparo": LARANJA, "pronto": "#2E7D32",
    "retirado": "#1565C0", "entregue": "#455A64", "cancelado": "#9E9E9E",
}

CSS = f"""
<style>
#MainMenu, footer {{visibility: hidden;}}
.block-container {{padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px;}}

/* ---------- Cabeçalho ---------- */
.topo {{
  background: linear-gradient(110deg, {VERMELHO_ESCURO} 0%, {VERMELHO} 45%, {LARANJA} 100%);
  border-radius: 18px; padding: 18px 26px; color: {BRANCO};
  display: flex; align-items: center; justify-content: space-between;
  box-shadow: 0 6px 18px rgba(183,28,28,.25); margin-bottom: 18px;
  border-bottom: 5px solid {AMARELO};
}}
.topo h1 {{color: {BRANCO}; font-size: 1.65rem; margin: 0; padding: 0; font-weight: 800; letter-spacing: .3px;}}
.topo p {{margin: 2px 0 0 0; opacity: .92; font-size: .95rem;}}
.topo .selo {{background: rgba(255,255,255,.18); border: 1px solid rgba(255,255,255,.35);
  padding: 6px 14px; border-radius: 999px; font-weight: 600; font-size: .9rem; white-space: nowrap;}}

/* ---------- Cartões ---------- */
.cartao {{background: {BRANCO}; border: 1px solid #F1E3C8; border-radius: 16px; padding: 18px 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,.05); margin-bottom: 14px;}}
.cartao h3 {{margin-top: 0; color: {VERMELHO_ESCURO};}}
.cartao-acesso {{border-top: 6px solid {VERMELHO};}}
.cartao-acesso.cliente {{border-top-color: {LARANJA};}}
.rotulo {{font-size: .78rem; text-transform: uppercase; letter-spacing: .6px; color: #8D6E63; font-weight: 700;}}

/* ---------- Métricas ---------- */
.metricas {{display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 14px;}}
.metrica {{background: {BRANCO}; border-radius: 14px; padding: 12px 16px; border: 1px solid #EEE;
  border-left: 6px solid var(--cor); box-shadow: 0 1px 6px rgba(0,0,0,.04);}}
.metrica .v {{font-size: 1.7rem; font-weight: 800; color: #333; line-height: 1.1;}}
.metrica .t {{font-size: .82rem; color: #6D6D6D;}}

/* ---------- Mapa de mesas ---------- */
.mapa {{display: grid; grid-template-columns: repeat(auto-fill, minmax(92px, 1fr)); gap: 10px;}}
.mesa {{border-radius: 14px; padding: 9px 8px 8px; text-align: center; border: 2px solid var(--cor);
  background: var(--fundo); position: relative; min-height: 86px;}}
.mesa .n {{font-size: 1.35rem; font-weight: 800; color: var(--cor);}}
.mesa .c {{font-size: .74rem; color: #555;}}
.mesa .s {{font-size: .70rem; font-weight: 700; color: var(--cor); margin-top: 2px;}}
.mesa.meu {{box-shadow: 0 0 0 3px {AMARELO};}}
.mesa.cota::after {{content: "S/R"; position: absolute; top: 4px; left: 6px; font-size: .58rem;
  color: #8D6E63; font-weight: 700;}}
.mesa .badge {{position: absolute; top: -8px; right: -6px; background: {LARANJA}; color: #fff;
  border-radius: 999px; font-size: .68rem; padding: 2px 7px; font-weight: 700;}}
.mesa.alerta {{animation: pulso 1.2s infinite;}}
@keyframes pulso {{0% {{box-shadow: 0 0 0 0 rgba(211,47,47,.55);}} 70% {{box-shadow: 0 0 0 10px rgba(211,47,47,0);}} 100% {{box-shadow: 0 0 0 0 rgba(211,47,47,0);}}}}
.legenda {{display: flex; flex-wrap: wrap; gap: 14px; font-size: .82rem; margin: 6px 0 12px;}}
.legenda span::before {{content: ""; display: inline-block; width: 12px; height: 12px; border-radius: 4px;
  background: var(--cor); margin-right: 6px; vertical-align: -1px;}}

/* ---------- Pedidos ---------- */
.pedido {{background: {BRANCO}; border-radius: 14px; border: 1px solid #EEE; border-left: 7px solid var(--cor);
  padding: 12px 16px; margin-bottom: 10px; box-shadow: 0 1px 6px rgba(0,0,0,.04);}}
.pedido.atrasado {{border-left-color: {VERMELHO}; background: #FFF5F5;}}
.chip {{display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: .75rem; font-weight: 700;
  color: #fff; background: var(--cor);}}
.chip.alerta {{background: {VERMELHO};}}
.etapas {{display: flex; gap: 4px; margin: 10px 0 4px;}}
.etapas div {{flex: 1; height: 8px; border-radius: 4px; background: #EEE;}}
.etapas div.ok {{background: linear-gradient(90deg, {AMARELO}, {LARANJA});}}
.etapas-rotulos {{display: flex; justify-content: space-between; font-size: .7rem; color: #888;}}

/* ---------- Totem da cozinha ---------- */
.totem {{background: {BRANCO}; border-radius: 18px; border: 2px solid #F3E0B5; padding: 14px 18px;
  border-top: 10px solid var(--cor); min-height: 230px; box-shadow: 0 3px 12px rgba(0,0,0,.06);}}
.totem.atrasado {{border-color: {VERMELHO}; background: #FFF3F3;}}
.totem .mesa-n {{font-size: 2.1rem; font-weight: 900; color: {VERMELHO_ESCURO}; line-height: 1;}}
.totem .tempo {{font-size: 1.05rem; font-weight: 700;}}
.totem ul {{padding-left: 18px; margin: 8px 0; font-size: 1.08rem;}}
.totem .obs {{color: {VERMELHO}; font-style: italic; font-size: .92rem;}}

/* ---------- Botões ---------- */
.stButton > button, .stFormSubmitButton > button {{border-radius: 10px; font-weight: 700;}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
  background: linear-gradient(90deg, {VERMELHO}, {LARANJA}); border: none;}}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
  filter: brightness(1.07); border: none;}}
.stButton > button:disabled, .stFormSubmitButton > button:disabled {{opacity: .45; filter: grayscale(.4);}}
.stTabs [data-baseweb="tab-list"] {{gap: 6px;}}
.stTabs [data-baseweb="tab"] {{background: {AMARELO_CLARO}; border-radius: 10px 10px 0 0; padding: 8px 16px; font-weight: 600;}}
.stTabs [aria-selected="true"] {{background: {VERMELHO}; color: {BRANCO} !important;}}
.stTabs [aria-selected="true"] p {{color: {BRANCO} !important;}}
.notif {{border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; background: {AMARELO_CLARO};
  border-left: 6px solid {LARANJA};}}
.notif.urgente {{background: #FFEBEE; border-left-color: {VERMELHO};}}
.rodape {{text-align: center; color: #A1887F; font-size: .78rem; margin-top: 26px;}}
</style>
"""


def aplicar():
    st.markdown(CSS, unsafe_allow_html=True)


def esc(texto) -> str:
    return html.escape(str(texto if texto is not None else ""))


def topo(titulo: str, subtitulo: str = "", selo: str = ""):
    selo_html = f'<div class="selo">{esc(selo)}</div>' if selo else ""
    st.markdown(f'<div class="topo"><div><h1>{esc(titulo)}</h1><p>{esc(subtitulo)}</p></div>{selo_html}</div>',
                unsafe_allow_html=True)


def metricas(itens: list[tuple[str, str | int, str]]):
    blocos = "".join(f'<div class="metrica" style="--cor:{c}"><div class="v">{esc(v)}</div>'
                     f'<div class="t">{esc(t)}</div></div>' for t, v, c in itens)
    st.markdown(f'<div class="metricas">{blocos}</div>', unsafe_allow_html=True)


def rodape():
    st.markdown('<div class="rodape">Sistema de Gestão de Reservas, Ocupação de Mesas e '
                'Acompanhamento de Pedidos · Projeto acadêmico – Engenharia de Computação</div>',
                unsafe_allow_html=True)
