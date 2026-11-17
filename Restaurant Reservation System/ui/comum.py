"""Componentes compartilhados entre as telas."""
import streamlit as st

from core.services import RegraNegocioErro


def sair():
    for chave in list(st.session_state.keys()):
        del st.session_state[chave]
    st.rerun()


def botao_sair(chave: str = "sair"):
    if st.button("Sair", key=chave, icon=":material/logout:", width="stretch"):
        sair()


def executar(acao, sucesso: str | None = None, *args, **kwargs) -> bool:
    """Executa uma ação de serviço exibindo o erro de regra de negócio, se houver."""
    try:
        acao(*args, **kwargs)
    except RegraNegocioErro as erro:
        st.session_state["_flash"] = ("erro", str(erro))
        return False
    if sucesso:
        st.session_state["_flash"] = ("ok", sucesso)
    return True


def mostrar_flash():
    """Mensagens que sobrevivem ao st.rerun(), exibidas como aviso flutuante."""
    flash = st.session_state.pop("_flash", None)
    if flash:
        tipo, msg = flash
        # st.toast não altera o layout, então a aba aberta é preservada após a ação
        icone = "✅" if tipo == "ok" else "⚠️"
        try:
            st.toast(msg, icon=icone, duration="short" if tipo == "ok" else "long")
        except TypeError:  # versões do Streamlit sem o parâmetro duration
            st.toast(msg, icon=icone)
