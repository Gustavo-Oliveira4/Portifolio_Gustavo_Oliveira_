"""Testes de fumaça da interface: cada visão abre sem erros e o fluxo principal funciona."""
import os
from pathlib import Path

import pytest

os.environ.setdefault("MONGO_URI", "mongomock://")
os.environ.setdefault("DEMO", "1")

from streamlit.testing.v1 import AppTest  # noqa: E402

from core import config  # noqa: E402

config.MONGO_URI = "mongomock://"  # sempre em memória nos testes

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _app():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    return at


def _sem_erros(at):
    assert not at.exception, [e.value for e in at.exception]


def _entrar(at, matricula, senha):
    at.text_input[0].input(matricula)
    at.text_input[1].input(senha)
    at.button[0].click()
    at.run()


def test_tela_inicial():
    at = _app()
    _sem_erros(at)
    assert [t.label for t in at.text_input] == ["Matrícula", "Senha", "CPF"]


@pytest.mark.parametrize("matricula,senha", [("G01", "garcom123"), ("G25", "garcom123"), ("C01", "chef123")])
def test_visoes_de_funcionario(matricula, senha):
    at = _app()
    _entrar(at, matricula, senha)
    _sem_erros(at)
    assert any(b.label == "Sair" for b in at.button)


def test_visao_cliente_e_reserva():
    at = _app()
    at.text_input[2].input("111.444.777-35")
    at.button[1].click()
    at.run()
    _sem_erros(at)
    at.text_input[0].input("Cliente Teste")
    at.text_input[1].input("11999990000")
    next(b for b in at.button if b.label == "Confirmar reserva").click()
    at.run()
    _sem_erros(at)
    assert any("Mesa" in b.value for b in at.markdown)


def test_login_invalido():
    at = _app()
    _entrar(at, "G01", "errada")
    assert any("inválidas" in e.value for e in at.error)
