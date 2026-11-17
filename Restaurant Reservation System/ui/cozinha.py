"""Visão da Cozinha – totens (Seção 4.3)."""
import streamlit as st

from core import config
from core.services import EM_PREPARO, RECEBIDO, ROTULO_PEDIDO
from core.utils import agora, fmt_hora, fmt_minutos
from ui import comum, estilo
from ui.estilo import COR_PEDIDO, esc

COLUNAS = 3


def tela(svc, usuario: dict):
    c1, c2 = st.columns([6, 1])
    with c1:
        estilo.topo(f"Cozinha · {usuario['nome']}", "Fila de preparo em tempo real",
                    f"Totem {usuario['matricula']}")
    with c2:
        st.write("")
        comum.botao_sair()
    comum.mostrar_flash()
    _fila(svc, usuario)
    st.divider()
    _ajustes(svc, usuario)


@st.fragment(run_every=config.INTERVALO_ATUALIZACAO_S)
def _fila(svc, usuario: dict):
    svc.processar_rotinas()
    mat = usuario["matricula"]
    fila = svc.fila_cozinha()
    prontos = svc.pedidos_prontos()
    estilo.metricas([
        ("Na fila", sum(p["status"] == RECEBIDO for p in fila), "#757575"),
        ("Em preparo", sum(p["status"] == EM_PREPARO for p in fila), estilo.LARANJA),
        ("Atrasados", sum(p["atrasado"] for p in fila), estilo.VERMELHO),
        ("Aguardando retirada", len(prontos), "#2E7D32"),
    ])
    st.caption(f"Ordem: pedidos priorizados, agrupados por mesa e por ordem de chegada · "
               f"atualizado às {agora():%H:%M:%S}")
    if not fila:
        st.success("Nenhum pedido na fila. 👨‍🍳")
    for inicio in range(0, len(fila), COLUNAS):
        colunas = st.columns(COLUNAS)
        for k, (col, p) in enumerate(zip(colunas, fila[inicio:inicio + COLUNAS])):
            with col:
                _cartao(svc, p, mat, inicio + k + 1)

    if prontos:
        st.markdown("#### Aguardando retirada pelo garçom")
        for p in prontos:
            espera = (agora() - p["pronto_em"]).total_seconds() / 60
            urg = espera > config.TIMEOUT_RETIRADA_MIN
            st.markdown(f'<div class="notif {"urgente" if urg else ""}">🛎️ <b>Mesa {p["mesa"]}</b> · '
                        f'garçom {p["garcom"]} chamado há {fmt_minutos(espera)}'
                        f'{" · redirecionado a todos do pavimento" if urg else ""}</div>',
                        unsafe_allow_html=True)


def _cartao(svc, p: dict, mat: str, posicao: int):
    cor = COR_PEDIDO[p["status"]]
    itens = "".join(f"<li><b>{i['quantidade']}×</b> {esc(i['nome'])}"
                    + (f"<div class='obs'>⚠ {esc(i['observacao'])}</div>" if i["observacao"] else "")
                    + "</li>" for i in p["itens"])
    previsao = p.get("previsao_entrega")
    if p["atrasado"]:
        tempo = f'<span class="chip alerta">ATRASADO</span> previsto {fmt_hora(p["previsao_inicial"])}'
    else:
        tempo = f'Entrega prevista <b>{fmt_hora(previsao)}</b>'
    chefe = f" · {p['chefe']}" if p.get("chefe") else ""
    prioridade = ' <span class="chip" style="--cor:#F57C00">PRIORIDADE</span>' if p.get("prioridade") else ""
    st.markdown(
        f'<div class="totem {"atrasado" if p["atrasado"] else ""}" style="--cor:{cor}">'
        f'<div style="display:flex;justify-content:space-between;align-items:start">'
        f'<div><div class="rotulo">#{posicao} · {ROTULO_PEDIDO[p["status"]]}{esc(chefe)}</div>'
        f'<div class="mesa-n">Mesa {p["mesa"]}</div></div>'
        f'<div style="text-align:right"><div class="tempo">⏱ {fmt_minutos(p["decorrido_min"])}</div>'
        f'<small>lançado {fmt_hora(p["lancado_em"])}</small></div></div>{prioridade}'
        f'<ul>{itens}</ul><div>{tempo} · esperado {p.get("tempo_esperado_min", "—")} min</div></div>',
        unsafe_allow_html=True)
    if p["status"] == RECEBIDO:
        if st.button("Iniciar preparo", key=f"ini_{p['_id']}", width="stretch", type="primary"):
            comum.executar(svc.iniciar_preparo, None, p["_id"], mat)
            st.rerun()
    else:
        if st.button("Pronto · chamar garçom", key=f"pr_{p['_id']}", width="stretch", type="primary"):
            comum.executar(svc.marcar_pronto, f"Garçom chamado para a mesa {p['mesa']}.", p["_id"], mat)
            st.rerun()


def _ajustes(svc, usuario: dict):
    """RU-COZ-08 e RN-18 – fora da área de atualização automática para não perder a digitação."""
    mat = usuario["matricula"]
    fila = svc.fila_cozinha()
    if not fila:
        return
    rotulos = {str(p["_id"]): f"Mesa {p['mesa']} · {fmt_hora(p['lancado_em'])} · "
                              f"{ROTULO_PEDIDO[p['status']]} · {p['itens'][0]['nome']}"
                              f"{' +' if len(p['itens']) > 1 else ''}" for p in fila}
    c1, c2 = st.columns(2)
    with c1, st.form("ajuste"):
        st.markdown("##### ⏱ Ajustar tempo esperado")
        sel = st.selectbox("Pedido", list(rotulos), format_func=rotulos.get)
        minutos = st.number_input("Minutos (+ ou −)", -60, 120, 5, step=1)
        motivo = st.text_input("Motivo", placeholder="Ex.: forno sobrecarregado")
        if st.form_submit_button("Aplicar ajuste", type="primary"):
            comum.executar(svc.ajustar_tempo, "Tempo ajustado e cliente atualizado.", sel, minutos, motivo, mat)
            st.rerun()
    recebidos = {k: v for k, v in rotulos.items() if "Recebido" in v}
    with c2, st.form("priorizar"):
        st.markdown("##### ⬆ Priorizar pedido")
        if recebidos:
            sel_p = st.selectbox("Pedido aguardando preparo", list(recebidos), format_func=recebidos.get)
        else:
            sel_p = None
            st.caption("Nenhum pedido aguardando preparo.")
        just = st.text_input("Justificativa", placeholder="Ex.: cliente com horário restrito")
        if st.form_submit_button("Priorizar", type="primary", disabled=not recebidos):
            comum.executar(svc.priorizar, "Pedido priorizado na fila.", sel_p, just, mat)
            st.rerun()
