"""Visão do Garçom (Seção 4.2)."""
from datetime import datetime, time, timedelta

import pandas as pd
import streamlit as st

from core import config
from core.services import (ATENDIDA, EM_LIBERACAO, LIVRE, NAO_ATENDIDA, PRONTO,
                           RECEBIDO, RESERVADA, RETIRADO, ROTULO_MESA, ROTULO_PEDIDO,
                           ROTULO_RESERVA, R_ATIVA, STATUS_OCUPADA)
from core.utils import agora, fmt_hora, fmt_minutos, mascarar_cpf
from ui import comum, estilo
from ui.estilo import COR_MESA, COR_PEDIDO, esc

NOME_PAV = {"terreo": "Térreo", "mezanino": "Mezanino"}


def tela(svc, usuario: dict):
    mat = usuario["matricula"]
    c1, c2 = st.columns([6, 1])
    with c1:
        estilo.topo(f"Garçom · {usuario['nome']}", "Mapa de mesas, notificações e pedidos",
                    f"{mat} · {NOME_PAV[usuario['pavimento']]}")
    with c2:
        st.write("")
        comum.botao_sair()
    comum.mostrar_flash()

    abas = st.tabs(["🗺️ Mapa de mesas", "🔔 Notificações", "🍽️ Atender mesa",
                    "🛎️ Retiradas", "📅 Reservas"])
    with abas[0]:
        _painel_mapa(svc, usuario)
    with abas[1]:
        _painel_notificacoes(svc, usuario)
    with abas[2]:
        _painel_mesa(svc, usuario)
    with abas[3]:
        _painel_retiradas(svc, usuario)
    with abas[4]:
        _painel_reservas(svc, usuario)


# ================================================================ Mapa
@st.fragment(run_every=config.INTERVALO_ATUALIZACAO_S)
def _painel_mapa(svc, usuario: dict):
    svc.processar_rotinas()
    _avisar_novas(svc, usuario["matricula"])

    c1, c2 = st.columns([3, 2])
    filtro = c1.radio("Pavimento", ["Meu pavimento", "Térreo", "Mezanino", "Todos"],
                      horizontal=True, key="filtro_pav")
    so_setor = c2.toggle("Somente meu setor", key="so_setor")
    pav = {"Meu pavimento": usuario["pavimento"], "Térreo": "terreo",
           "Mezanino": "mezanino", "Todos": None}[filtro]

    mesas = svc.listar_mesas(pav)
    if so_setor:
        mesas = [m for m in mesas if m["garcom"] == usuario["matricula"]]
    cont = {k: sum(m["status_exibicao"] == k for m in mesas) for k in ROTULO_MESA}
    alertas = sum(m["alerta"] for m in mesas)
    estilo.metricas([
        ("Livres", cont[LIVRE], COR_MESA[LIVRE][0]),
        ("Reservadas", cont[RESERVADA], COR_MESA[RESERVADA][0]),
        ("Não atendidas", cont[NAO_ATENDIDA], COR_MESA[NAO_ATENDIDA][0]),
        ("Atendidas", cont[ATENDIDA], COR_MESA[ATENDIDA][0]),
        ("Em liberação", cont[EM_LIBERACAO], COR_MESA[EM_LIBERACAO][0]),
        (f"Esperando > {config.ALERTA_NAO_ATENDIDA_MIN} min", alertas, estilo.VERMELHO),
    ])
    st.markdown('<div class="legenda">' + "".join(
        f'<span style="--cor:{COR_MESA[k][0]}">{v}</span>' for k, v in ROTULO_MESA.items())
        + f'<span style="--cor:{estilo.AMARELO}">Contorno amarelo = meu setor</span>'
        + '<span style="--cor:#BCAAA4">S/R = reservada a clientes sem agendamento</span></div>',
        unsafe_allow_html=True)

    por_pav: dict = {}
    for m in mesas:
        por_pav.setdefault(m["pavimento"], []).append(m)
    for p, lista in por_pav.items():
        st.markdown(f"#### {NOME_PAV[p]}")
        st.markdown('<div class="mapa">' + "".join(_bloco_mesa(m, usuario["matricula"]) for m in lista)
                    + "</div>", unsafe_allow_html=True)
    if not mesas:
        st.info("Nenhuma mesa para o filtro selecionado.")
    st.caption(f"Atualizado às {agora():%H:%M:%S}")


def _bloco_mesa(m: dict, matricula: str) -> str:
    st_ex = m["status_exibicao"]
    cor, fundo = COR_MESA[st_ex]
    classes = ["mesa"]
    if m["garcom"] == matricula:
        classes.append("meu")
    if m["alerta"]:
        classes.append("alerta")
    if not m["reservavel"]:
        classes.append("cota")
    detalhe = ROTULO_MESA[st_ex].replace("Ocupada – ", "")
    if st_ex == NAO_ATENDIDA:
        detalhe = f"Aguarda {fmt_minutos(m['espera_min'])}"
    elif st_ex == RESERVADA:
        detalhe = f"Reserva {fmt_hora(m['reserva']['data_hora'])}"
    badge = (f'<div class="badge">{m["pedidos_prontos"]} pronto</div>' if m["pedidos_prontos"] else "")
    return (f'<div class="{" ".join(classes)}" style="--cor:{cor};--fundo:{fundo}" '
            f'title="Garçom {m["garcom"]}">{badge}<div class="n">{m["numero"]}</div>'
            f'<div class="c">👥 {m["capacidade"]} lugares</div><div class="s">{detalhe}</div></div>')


def _avisar_novas(svc, matricula: str):
    vistas = st.session_state.setdefault("notif_vistas", set())
    for n in svc.notificacoes(matricula):
        if n["_id"] not in vistas:
            vistas.add(n["_id"])
            st.toast(n["mensagem"], icon="🔔")


# ================================================================ Notificações
ICONE = {"entrada": "🚪", "saida": "🧹", "pronto": "🛎️", "chamado": "🙋", "reserva_expirada": "⌛"}


@st.fragment(run_every=config.INTERVALO_ATUALIZACAO_S)
def _painel_notificacoes(svc, usuario: dict):
    mat = usuario["matricula"]
    pendentes = svc.notificacoes(mat)
    st.markdown(f"#### Pendentes ({len(pendentes)})")
    if not pendentes:
        st.success("Tudo em dia! Nenhuma notificação pendente.")
    for n in pendentes:
        urgente = n["escalonada"] or n["tipo"] in ("pronto", "chamado")
        c1, c2 = st.columns([5, 1])
        c1.markdown(f'<div class="notif {"urgente" if urgente else ""}">{ICONE.get(n["tipo"], "🔔")} '
                    f'<b>{esc(n["mensagem"])}</b><br><small>{fmt_hora(n["criada_em"])} · há '
                    f'{fmt_minutos((agora() - n["criada_em"]).total_seconds() / 60)}</small></div>',
                    unsafe_allow_html=True)
        if c2.button("Ciente", key=f"ok_{n['_id']}", width="stretch"):
            comum.executar(svc.confirmar_notificacao, None, n["_id"], mat)
            st.rerun()
    with st.expander("Histórico recente"):
        hist = [n for n in svc.notificacoes(mat, pendentes=False, limite=30) if n["confirmada"]]
        for n in hist:
            st.caption(f"{fmt_hora(n['criada_em'])} · {n['mensagem']} — confirmada por "
                       f"{n['confirmada_por']} às {fmt_hora(n['confirmada_em'])}")
        if not hist:
            st.caption("Sem histórico.")


# ================================================================ Mesa
def _painel_mesa(svc, usuario: dict):
    mat = usuario["matricula"]
    mesas = svc.listar_mesas()
    c1, c2 = st.columns([1, 3])
    meu_setor = c1.toggle("Somente meu setor", value=True, key="mesa_meu_setor")
    opcoes = [m for m in mesas if m["garcom"] == mat] if meu_setor else mesas
    if not opcoes:
        st.info("Nenhuma mesa disponível.")
        return
    rotulo = {m["numero"]: f"Mesa {m['numero']} · {NOME_PAV[m['pavimento']]} · {m['capacidade']} lugares · "
                           f"{ROTULO_MESA[m['status_exibicao']]}" for m in opcoes}
    numero = c2.selectbox("Selecione a mesa", list(rotulo), format_func=rotulo.get, key="mesa_sel")
    if st.button("↻ Atualizar", key="atualizar_mesa"):
        st.rerun()
    m = next(x for x in mesas if x["numero"] == numero)
    cor, fundo = COR_MESA[m["status_exibicao"]]

    at = m["atendimento"]
    info = f"Responsável: <b>{m['garcom']}</b>"
    if at:
        info += (f" · Cliente: <b>{esc(at.get('nome') or 'Não informado')}</b>"
                 f" · CPF: {mascarar_cpf(at.get('cpf'))} · {at['pessoas']} pessoa(s)"
                 f" · Chegada: {fmt_hora(at['inicio'])}")
        if at.get("primeiro_atendimento_em"):
            espera = (at["primeiro_atendimento_em"] - at["inicio"]).total_seconds() / 60
            info += f" · Espera até o atendimento: {fmt_minutos(espera)}"
    st.markdown(f'<div class="pedido" style="--cor:{cor};background:{fundo}">'
                f'<span class="chip" style="--cor:{cor}">{ROTULO_MESA[m["status_exibicao"]]}</span> &nbsp;'
                f'{info}</div>', unsafe_allow_html=True)

    status = m["status"]
    if status == LIVRE:
        _acoes_mesa_livre(svc, m, mat)
    elif status == NAO_ATENDIDA:
        st.warning(f"Clientes aguardando o primeiro atendimento há {fmt_minutos(m['espera_min'])}.", icon="⏱️")
        if st.button("Registrar atendimento", type="primary", key="reg_at"):
            comum.executar(svc.registrar_atendimento, f"Atendimento da mesa {numero} registrado.", numero, mat)
            st.rerun()
    if status in STATUS_OCUPADA:
        _pedidos_da_mesa(svc, m, mat)
        _novo_pedido(svc, numero, mat)
        st.divider()
        if st.button("Encerrar atendimento e liberar mesa", key="liberar", icon=":material/logout:"):
            comum.executar(svc.liberar_mesa, f"Mesa {numero} liberada para higienização.", numero, mat)
            st.rerun()
    elif status == EM_LIBERACAO:
        st.info("A mesa aguarda higienização.")
        if st.button("Confirmar limpeza – mesa livre", type="primary", key="limpeza"):
            comum.executar(svc.confirmar_limpeza, f"Mesa {numero} disponível.", numero, mat)
            st.rerun()


def _acoes_mesa_livre(svc, m: dict, mat: str):
    numero = m["numero"]
    r = svc.proxima_reserva(numero)
    bloqueada = False
    if r:
        falta = (r["data_hora"] - agora()).total_seconds() / 60
        bloqueada = falta < config.DURACAO_PERMANENCIA_MIN
        st.info(f"Próxima reserva às **{fmt_hora(r['data_hora'])}** ({r['data_hora']:%d/%m}) para "
                f"**{r['nome']}** · {r['pessoas']} pessoa(s) · CPF {mascarar_cpf(r['cpf'])}.", icon="📅")
        if falta <= config.JANELA_EXIBIR_RESERVADA_MIN:
            if st.button("Registrar chegada (check-in)", type="primary", key="checkin_mesa"):
                comum.executar(svc.fazer_checkin, f"Check-in realizado na mesa {numero}.", r["_id"], mat)
                st.rerun()
    st.markdown("##### Cliente sem agendamento")
    if bloqueada:
        st.caption(f"Indisponível: a reserva começa em menos de {config.DURACAO_PERMANENCIA_MIN} minutos "
                   "(tempo médio de permanência). Escolha outra mesa.")
        return
    with st.form("ocupar"):
        c1, c2, c3 = st.columns([1, 2, 2])
        pessoas = c1.number_input("Pessoas", 1, m["capacidade"], min(2, m["capacidade"]))
        nome = c2.text_input("Nome (opcional)")
        cpf = c3.text_input("CPF (opcional)", help="Com o CPF o cliente acompanha o pedido pelo celular.")
        if st.form_submit_button("Acomodar clientes", type="primary"):
            comum.executar(svc.ocupar_sem_reserva, f"Mesa {numero} ocupada.", numero, pessoas, mat,
                           cpf=cpf, nome=nome)
            st.rerun()


def _pedidos_da_mesa(svc, m: dict, mat: str):
    pedidos = svc.pedidos_do_atendimento(m.get("atendimento_id"))
    st.markdown(f"##### Pedidos da mesa ({len(pedidos)})")
    if not pedidos:
        st.caption("Nenhum pedido lançado.")
    total = 0.0
    for p in pedidos:
        cor = COR_PEDIDO[p["status"]]
        itens = ", ".join(f"{i['quantidade']}× {esc(i['nome'])}" for i in p["itens"])
        if p["status"] != "cancelado":
            total += sum(i["quantidade"] * i["preco"] for i in p["itens"])
        prev = (f" · Previsão {fmt_hora(p.get('previsao_entrega'))}"
                if p["status"] in (RECEBIDO, "em_preparo") else "")
        c1, c2 = st.columns([5, 1.3])
        c1.markdown(f'<div class="pedido" style="--cor:{cor}"><span class="chip" style="--cor:{cor}">'
                    f'{ROTULO_PEDIDO[p["status"]]}</span> &nbsp;<b>{fmt_hora(p["lancado_em"])}</b> · '
                    f'{itens}{prev}</div>', unsafe_allow_html=True)
        with c2:
            if p["status"] == RECEBIDO and st.button("Cancelar", key=f"canc_{p['_id']}", width="stretch"):
                comum.executar(svc.cancelar_pedido, "Pedido cancelado.", p["_id"], mat)
                st.rerun()
            if p["status"] == PRONTO and st.button("Retirei", key=f"ret_{p['_id']}", type="primary",
                                                   width="stretch"):
                comum.executar(svc.confirmar_retirada, "Retirada confirmada.", p["_id"], mat)
                st.rerun()
            if p["status"] == RETIRADO and st.button("Entreguei", key=f"ent_{p['_id']}", type="primary",
                                                     width="stretch"):
                comum.executar(svc.confirmar_entrega, "Entrega confirmada.", p["_id"], mat)
                st.rerun()
    if total:
        st.caption(f"Consumo parcial: R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))


def _novo_pedido(svc, numero: int, mat: str):
    """Monta o pedido item a item (carrinho) e envia aos totens da cozinha."""
    carrinhos = st.session_state.setdefault("carrinhos", {})
    carrinho = carrinhos.setdefault(numero, [])
    with st.expander(f"➕ Lançar novo pedido{f' ({len(carrinho)} item(ns))' if carrinho else ''}",
                     expanded=bool(carrinho)):
        cardapio = {c["codigo"]: c for c in svc.cardapio()}
        with st.form(f"add_item_{numero}", clear_on_submit=True, border=False):
            c1, c2, c3, c4 = st.columns([3, 1, 2, 1.2])
            codigo = c1.selectbox(
                "Item do cardápio", list(cardapio),
                format_func=lambda k: f"{cardapio[k]['nome']} · {cardapio[k]['categoria']} · "
                                      f"{cardapio[k]['tempo_preparo_min']} min · R$ {cardapio[k]['preco']:.2f}")
            qtd = c2.number_input("Qtd", 1, 20, 1)
            obs = c3.text_input("Observação", placeholder="Ex.: sem cebola")
            c4.write("")
            if c4.form_submit_button("Adicionar", width="stretch"):
                carrinho.append({"codigo": codigo, "quantidade": int(qtd), "observacao": obs.strip()})
                st.rerun()

        for k, item in enumerate(carrinho):
            c1, c2 = st.columns([6, 1])
            nome = cardapio.get(item["codigo"], {}).get("nome", "?")
            c1.markdown(f"**{item['quantidade']}×** {esc(nome)}"
                        + (f" · _{esc(item['observacao'])}_" if item["observacao"] else ""))
            if c2.button("Remover", key=f"rm_{numero}_{k}", width="stretch"):
                carrinho.pop(k)
                st.rerun()

        if carrinho:
            b1, b2 = st.columns([1, 1])
            if b1.button("Enviar para a cozinha", type="primary", key=f"enviar_{numero}", width="stretch"):
                if comum.executar(svc.lancar_pedido, "Pedido enviado aos totens da cozinha.",
                                  numero, list(carrinho), mat):
                    carrinhos[numero] = []
                st.rerun()
            if b2.button("Limpar", key=f"limpar_{numero}", width="stretch"):
                carrinhos[numero] = []
                st.rerun()
        else:
            st.caption("Adicione os itens; eles serão enviados juntos à cozinha.")


# ================================================================ Retiradas
def _itens_txt(pedido: dict) -> str:
    return ", ".join(f"{i['quantidade']}× {esc(i['nome'])}" for i in pedido["itens"])


@st.fragment(run_every=config.INTERVALO_ATUALIZACAO_S)
def _painel_retiradas(svc, usuario: dict):
    mat, pav = usuario["matricula"], usuario["pavimento"]
    prontos = svc.pedidos_prontos(pav)
    st.markdown(f"#### Prontos para retirada · {NOME_PAV[pav]} ({len(prontos)})")
    if not prontos:
        st.success("Nenhum pedido aguardando retirada.")
    for p in prontos:
        meu = p["garcom"] == mat
        espera = (agora() - p["pronto_em"]).total_seconds() / 60
        c1, c2 = st.columns([5, 1])
        c1.markdown(f'<div class="notif {"urgente" if espera > config.TIMEOUT_RETIRADA_MIN else ""}">'
                    f'🛎️ <b>Mesa {p["mesa"]}</b> · {_itens_txt(p)}'
                    f'<br><small>Pronto há {fmt_minutos(espera)} · responsável {p["garcom"]}'
                    f'{" (você)" if meu else ""}</small></div>', unsafe_allow_html=True)
        if c2.button("Retirei", key=f"r_{p['_id']}", type="primary", width="stretch"):
            comum.executar(svc.confirmar_retirada, f"Retirada da mesa {p['mesa']} confirmada.", p["_id"], mat)
            st.rerun()

    meus = list(svc.db.pedidos.find({"status": RETIRADO, "retirado_por": mat}).sort("retirado_em", 1))
    if meus:
        st.markdown("#### A entregar")
        for p in meus:
            c1, c2 = st.columns([5, 1])
            c1.markdown(f'<div class="notif">🍽️ <b>Mesa {p["mesa"]}</b> · '
                        f'{_itens_txt(p)}</div>',
                        unsafe_allow_html=True)
            if c2.button("Entreguei", key=f"e_{p['_id']}", type="primary", width="stretch"):
                comum.executar(svc.confirmar_entrega, "Entrega confirmada.", p["_id"], mat)
                st.rerun()


# ================================================================ Reservas
def _painel_reservas(svc, usuario: dict):
    mat = usuario["matricula"]
    c1, c2 = st.columns([1, 1])
    dia = c1.date_input("Dia", value=agora().date(), format="DD/MM/YYYY", key="dia_res")
    pav_opc = {"Todos": None, "Térreo": "terreo", "Mezanino": "mezanino"}
    pav = c2.selectbox("Ambiente", list(pav_opc), key="pav_res")
    reservas = svc.reservas_do_dia(datetime.combine(dia, time()), pav_opc[pav])

    if reservas:
        st.dataframe(pd.DataFrame([{
            "Horário": fmt_hora(r["data_hora"]), "Mesa": r["mesa"], "Ambiente": NOME_PAV[r["ambiente"]],
            "Nome": r["nome"], "Pessoas": r["pessoas"], "CPF": mascarar_cpf(r["cpf"]),
            "Origem": "Garçom" if r["origem"] == "manual" else "Cliente",
            "Situação": ROTULO_RESERVA[r["status"]]} for r in reservas]),
            hide_index=True, width="stretch")
        ativas = {str(r["_id"]): r for r in reservas if r["status"] == R_ATIVA}
        if ativas:
            c1, c2 = st.columns([3, 1])
            sel = c1.selectbox("Registrar chegada de", list(ativas), key="sel_checkin",
                               format_func=lambda k: f"{fmt_hora(ativas[k]['data_hora'])} · Mesa "
                                                     f"{ativas[k]['mesa']} · {ativas[k]['nome']}")
            c2.write("")
            if c2.button("Check-in", type="primary", width="stretch", key="btn_checkin"):
                comum.executar(svc.fazer_checkin, "Check-in realizado.", sel, mat)
                st.rerun()
            with st.popover("Cancelar uma reserva"):
                canc = st.selectbox("Reserva", list(ativas), key="sel_canc",
                                    format_func=lambda k: f"{fmt_hora(ativas[k]['data_hora'])} · "
                                                          f"Mesa {ativas[k]['mesa']} · {ativas[k]['nome']}")
                if st.button("Confirmar cancelamento", key="btn_canc"):
                    comum.executar(svc.cancelar_reserva, "Reserva cancelada.", canc, usuario=mat)
                    st.rerun()
    else:
        st.info("Nenhuma reserva para este dia.")

    st.markdown("#### Nova reserva manual")
    st.caption("Para clientes que reservam por telefone ou no balcão. Pode usar qualquer mesa, "
               "inclusive as destinadas a clientes sem agendamento.")
    with st.form("reserva_manual"):
        c1, c2, c3 = st.columns(3)
        cpf = c1.text_input("CPF do cliente")
        nome = c2.text_input("Nome")
        tel = c3.text_input("Telefone com DDD")
        c4, c5, c6, c7, c8 = st.columns(5)
        data = c4.date_input("Data", value=agora().date(), min_value=agora().date(), format="DD/MM/YYYY")
        prox = agora() + timedelta(minutes=30)
        sugestao = time(prox.hour, prox.minute // 15 * 15)
        hora = c5.time_input("Horário", value=sugestao, step=timedelta(minutes=15))
        pessoas = c6.number_input("Pessoas", 1, svc.capacidade_maxima(), 2)
        amb = c7.selectbox("Ambiente", list(pav_opc))
        mesa = c8.number_input("Mesa (0 = automática)", 0, 100, 0)
        if st.form_submit_button("Reservar", type="primary"):
            try:
                r = svc.criar_reserva(cpf, nome, tel, datetime.combine(data, hora), pessoas, pav_opc[amb],
                                      origem="manual", usuario=mat, mesa_numero=mesa or None)
                st.session_state["_flash"] = ("ok", f"Reserva criada na mesa {r['mesa']} às "
                                                    f"{fmt_hora(r['data_hora'])}.")
            except Exception as erro:  # RegraNegocioErro
                st.session_state["_flash"] = ("erro", str(erro))
            st.rerun()
