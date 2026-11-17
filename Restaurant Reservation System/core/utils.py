"""Funções utilitárias: CPF, senhas e formatação."""
import hashlib
import hmac
import os
import re
from datetime import datetime


# ------------------------------------------------------------------ CPF (RN-01)
def limpar_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", cpf or "")


def validar_cpf(cpf: str) -> bool:
    """Valida tamanho e dígitos verificadores do CPF."""
    cpf = limpar_cpf(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[tamanho]):
            return False
    return True


def mascarar_cpf(cpf: str | None) -> str:
    """RN-25: o CPF aparece mascarado nas telas internas."""
    cpf = limpar_cpf(cpf or "")
    if len(cpf) != 11:
        return "—"
    return f"•••.{cpf[3:6]}.•••-••"


def formatar_cpf(cpf: str) -> str:
    cpf = limpar_cpf(cpf)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf


# ------------------------------------------------------------------ Senhas (RN-22)
def gerar_hash_senha(senha: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, 120_000)
    return f"{salt.hex()}${dk.hex()}"


def verificar_senha(senha: str, armazenado: str) -> bool:
    try:
        salt_hex, hash_hex = armazenado.split("$")
    except (ValueError, AttributeError):
        return False
    calculado = gerar_hash_senha(senha, bytes.fromhex(salt_hex)).split("$")[1]
    return hmac.compare_digest(calculado, hash_hex)


# ------------------------------------------------------------------ Tempo
def agora() -> datetime:
    """Horário local sem fuso; todo o sistema usa a mesma referência."""
    return datetime.now().replace(microsecond=0)


def minutos_entre(inicio: datetime | None, fim: datetime | None = None) -> float:
    if not inicio:
        return 0.0
    return ((fim or agora()) - inicio).total_seconds() / 60


def fmt_hora(dt: datetime | None) -> str:
    return dt.strftime("%H:%M") if dt else "—"


def fmt_data_hora(dt: datetime | None) -> str:
    return dt.strftime("%d/%m/%Y %H:%M") if dt else "—"


def fmt_minutos(minutos: float) -> str:
    minutos = max(0, int(round(minutos)))
    if minutos < 60:
        return f"{minutos} min"
    return f"{minutos // 60}h{minutos % 60:02d}"
