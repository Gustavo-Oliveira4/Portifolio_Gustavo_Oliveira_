"""Visão do Cliente: reserva por CPF e acompanhamento dos pedidos (Seção 4.1)."""
from datetime import datetime, time, timedelta

import streamlit as st

from core import config
from core.services import (PEDIDO_NA_COZINHA, R_ATIVA, ROTULO_PEDIDO, ROTULO_RESERVA,
                           SEQUENCIA_PEDIDO, CANCELADO)
from core.utils import agora, fmt_data_hora, fmt_hora, fmt_minutos, formatar_cpf
from ui import comum, estilo
from ui.estilo import COR_PEDIDO, esc

AMBIENTES = {"Sem preferência": None, "Térreo": "terreo", "Mezanino": "mezanino"}
NOME_AMBIENTE = {"terreo": "Térreo", "mezanino": "Mezanino"}


def tela(svc, cpf: str):
    c1, c2 = st.columns([6, 1])
    with c1:
        estilo.topo("Olá! Bem-vindo(a) 👋", "Reserve sua mesa e acompanhe seu pedido em tempo real",
                    f"CPF {formatar_cpf(cpf)}")
    with c2:
        st.write("")
        comum.botao_sair()
    comum.mostrar_flash()

    aba_acomp, aba_nova, aba_minhas = st.tabs(["🍲 Meu pedido", "📅 Nova reserva", "🗂️ Minhas reservas"])
    with aba_acomp:
        _acompanhamento(svc, cpf)
    with aba_nova:
        _nova_reserva(svc, cpf)
    with aba_minhas:
        _minhas_reservas(svc, cpf)


# ---------------------------------------------------------------- Acompanhamento
@st.fragment(run_every=config.INTERVALO_ATUALIZACAO_S)
def _acompanhamento(svc, cpf: str):
    svc.processar_rotinas()
    dados = svc.acompanhamento_cliente(cpf)
    if not dados:
        st.markdown('<div class="cartao"><h3>Você ainda não está à mesa</h3>'
                    'Assim que o garçom registrar sua chegada, seus pedidos aparecerão aqui '
                    'com o tempo estimado de preparo.</div>', unsafe_allow_html=True)
        return

    mesa, pedidos = dados["mesa"], dados["pedidos"]
    na_cozinha = [p for p in pedidos if p["status"] in PEDIDO_NA_COZINHA]
    prox = min((p["previsao_entrega"] for p in na_cozinha if p.get("previsao_entrega")), default=None)
    estilo.metricas([
        ("Sua mesa", mesa["numero"], estilo.VERMELHO),
        ("Ambiente", NOME_AMBIENTE[mesa["pavimento"]], estilo.LARANJA),
        ("Pedidos em preparo", len(na_cozinha), estilo.AMARELO),
        ("Próxima entrega prevista", fmt_hora(prox) if prox else "—", "#2E7D32"),
    ])

    col_a, col_b = st.columns([3, 1])
    with col_b:
        if dados["chamado_pendente"]:
            st.info("🔔 Garçom chamado. Ele já foi avisado!")
        elif st.button("🔔 Chamar garçom", type="primary", width="stretch"):
            comum.executar(svc.chamar_garcom, "Garçom chamado! Ele já foi avisado.", cpf)
            st.rerun()
    with col_a:
        st.caption(f"Atualização automática a cada {config.INTERVALO_ATUALIZACAO_S} segundos · "
                   f"{agora():%H:%M:%S}")

    if not pedidos:
        st.info("Nenhum pedido lançado ainda. Chame o garçom quando quiser fazer o seu pedido.")
    for i, p in enumerate(reversed(pedidos), 1):
        _cartao_pedido(p, len(pedidos) - i + 1)


def _cartao_pedido(p: dict, numero: int):
    status = p["status"]
    cor = COR_PEDIDO[status]
    itens = "".join(f"<li>{i['quantidade']}× {esc(i['nome'])}"
                    + (f" <i style='color:#888'>({esc(i['observacao'])})</i>" if i["observacao"] else "")
                    + "</li>" for i in p["itens"])
    if status in PEDIDO_NA_COZINHA:
        if p.get("atrasado"):
            prazo = (f'<span class="chip alerta">Atrasado</span> &nbsp;Novo prazo: '
                     f'<b>{fmt_hora(p["previsao_entrega"])}</b> (≈ {fmt_minutos(p["restante_min"])})')
        else:
            prazo = (f'Previsão: <b>{fmt_hora(p["previsao_entrega"])}</b> · '
                     f'faltam aproximadamente <b>{fmt_minutos(p["restante_min"])}</b>')
    elif status == CANCELADO:
        prazo = "Pedido cancelado."
    else:
        prazo = f"Atualizado às {fmt_hora(p.get(f'{status}_em'))}"

    etapas = ""
    if status != CANCELADO:
        idx = SEQUENCIA_PEDIDO.index(status)
        etapas = ('<div class="etapas">' + "".join(
            f'<div class="{"ok" if k <= idx else ""}"></div>' for k in range(len(SEQUENCIA_PEDIDO)))
            + '</div><div class="etapas-rotulos">'
            + "".join(f"<span>{ROTULO_PEDIDO[s]}</span>" for s in SEQUENCIA_PEDIDO) + "</div>")

    classe = "pedido atrasado" if p.get("atrasado") else "pedido"
    st.markdown(
        f'<div class="{classe}" style="--cor:{cor}">'
        f'<div style="display:flex;justify-content:space-between;align-items:center">'
        f'<b>Pedido {numero} · lançado às {fmt_hora(p["lancado_em"])}</b>'
        f'<span class="chip" style="--cor:{cor}">{ROTULO_PEDIDO[status]}</span></div>'
        f'<ul style="margin:6px 0 4px">{itens}</ul><div>{prazo}</div>{etapas}</div>',
        unsafe_allow_html=True)


# ---------------------------------------------------------------- Reservas
def _horarios() -> list[time]:
    return [time(h, m) for h in range(config.HORARIO_ABERTURA, config.HORARIO_FECHAMENTO)
            for m in (0, 15, 30, 45)]


def _sugestao():
    """Primeiro horário que respeita a antecedência mínima (RN-05)."""
    minimo = agora() + timedelta(minutes=config.ANTECEDENCIA_MIN_RESERVA)
    for dia in (minimo.date(), minimo.date() + timedelta(days=1)):
        for h in _horarios():
            if datetime.combine(dia, h) >= minimo:
                return dia, h
    return minimo.date() + timedelta(days=1), _horarios()[0]


def _dados_anteriores(svc, cpf):
    ultima = next(iter(svc.reservas_do_cliente(cpf)), None)
    return (ultima or {}).get("nome", ""), (ultima or {}).get("telefone", "")


def _nova_reserva(svc, cpf: str):
    nome_ant, tel_ant = _dados_anteriores(svc, cpf)
    st.markdown(f'<div class="cartao"><h3>Reservar uma mesa</h3>Reservas com no mínimo '
                f'{config.ANTECEDENCIA_MIN_RESERVA} minutos de antecedência. Tolerância de '
                f'{config.TOLERANCIA_ATRASO_MIN} minutos após o horário marcado.</div>',
                unsafe_allow_html=True)
    with st.form("nova_reserva", clear_on_submit=False):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome", value=nome_ant)
        telefone = c2.text_input("Telefone com DDD", value=tel_ant, placeholder="(11) 90000-0000")
        c3, c4, c5, c6 = st.columns(4)
        hoje = agora().date()
        dia_sug, hora_sug = _sugestao()
        data = c3.date_input("Data", value=dia_sug, min_value=hoje,
                             max_value=hoje + timedelta(days=60), format="DD/MM/YYYY")
        hora = c4.selectbox("Horário", _horarios(), index=_horarios().index(hora_sug),
                            format_func=lambda t: t.strftime("%H:%M"))
        pessoas = c5.number_input("Pessoas", 1, svc.capacidade_maxima(), 2)
        ambiente = c6.selectbox("Ambiente", list(AMBIENTES))
        if st.form_submit_button("Confirmar reserva", type="primary", width="stretch"):
            try:
                r = svc.criar_reserva(cpf, nome, telefone, datetime.combine(data, hora),
                                      pessoas, AMBIENTES[ambiente])
                st.session_state["_flash"] = (
                    "ok", f"Reserva confirmada! Mesa {r['mesa']} ({NOME_AMBIENTE[r['ambiente']]}) "
                          f"em {fmt_data_hora(r['data_hora'])}.")
                st.balloons()
            except Exception as erro:  # RegraNegocioErro
                st.session_state["_flash"] = ("erro", str(erro))
            st.rerun()


def _minhas_reservas(svc, cpf: str):
    reservas = svc.reservas_do_cliente(cpf)
    if not reservas:
        st.info("Você ainda não possui reservas.")
        return
    for r in reservas:
        ativa = r["status"] == R_ATIVA
        cor = estilo.LARANJA if ativa else "#9E9E9E"
        st.markdown(
            f'<div class="pedido" style="--cor:{cor}"><div style="display:flex;justify-content:space-between">'
            f'<b>{fmt_data_hora(r["data_hora"])} · Mesa {r["mesa"]} ({NOME_AMBIENTE[r["ambiente"]]})</b>'
            f'<span class="chip" style="--cor:{cor}">{ROTULO_RESERVA[r["status"]]}</span></div>'
            f'{r["pessoas"]} pessoa(s) · em nome de {esc(r["nome"])}</div>', unsafe_allow_html=True)
        if ativa:
            with st.expander("Alterar ou cancelar esta reserva"):
                with st.form(f"alt_{r['_id']}"):
                    c1, c2, c3 = st.columns(3)
                    data = c1.date_input("Nova data", value=r["data_hora"].date(),
                                         min_value=agora().date(), format="DD/MM/YYYY")
                    hs = _horarios()
                    atual = r["data_hora"].time()
                    hora = c2.selectbox("Novo horário", hs, index=hs.index(atual) if atual in hs else 0,
                                        format_func=lambda t: t.strftime("%H:%M"))
                    pessoas = c3.number_input("Pessoas", 1, svc.capacidade_maxima(), r["pessoas"])
                    b1, b2 = st.columns(2)
                    alterar = b1.form_submit_button("Salvar alteração", type="primary", width="stretch")
                    cancelar = b2.form_submit_button("Cancelar reserva", width="stretch")
                if alterar:
                    comum.executar(svc.alterar_reserva, "Reserva alterada com sucesso.",
                                   r["_id"], cpf, datetime.combine(data, hora), pessoas)
                    st.rerun()
                if cancelar:
                    comum.executar(svc.cancelar_reserva, "Reserva cancelada.", r["_id"], cpf=cpf)
                    st.rerun()
