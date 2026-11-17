"""
Configuração compartilhada do Busca Códigos.

Centraliza em um único arquivo (config.json) os caminhos que hoje estavam
fixos no código (pasta do repositório Git e pasta do banco ChromaDB), para
que cada usuário possa apontar para a sua própria estrutura de pastas.

Este módulo também serve de base para a futura interface única que irá
reunir configuração, indexação e consulta em um só lugar: hoje ele expõe
`configurar_interativo()` como um utilitário de linha de comando simples,
mas a ideia é que uma UI futura chame diretamente `carregar_config()` /
`salvar_config()`.
"""

import json
import os

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "config.json"
)

CONFIG_PADRAO = {
    "pasta_git": "",
    "chroma_db": "./chroma_db"
}


def carregar_config():
    """
    Carrega o config.json da pasta do projeto.

    Se o arquivo não existir, cria um novo com os valores padrão
    (sem pasta_git definida) para o usuário preencher.
    """

    if not os.path.exists(CONFIG_PATH):
        salvar_config(CONFIG_PADRAO)
        return dict(CONFIG_PADRAO)

    with open(CONFIG_PATH, "r", encoding="utf-8") as arquivo:
        config = json.load(arquivo)

    # Garante que chaves novas (adicionadas em versões futuras) existam
    config_completo = dict(CONFIG_PADRAO)
    config_completo.update(config)

    return config_completo


def salvar_config(config):
    """
    Salva o dicionário de configuração no config.json.
    """

    with open(CONFIG_PATH, "w", encoding="utf-8") as arquivo:
        json.dump(config, arquivo, indent=2, ensure_ascii=False)


def detectar_pasta_git():
    """
    Tenta localizar automaticamente a raiz do repositório Git.

    Sobe a árvore de pastas a partir da localização deste arquivo até
    encontrar uma pasta ".git". Isso permite que cada desenvolvedor use
    o repositório sem precisar configurar manualmente o caminho, desde
    que a estrutura de pastas dentro do repositório seja a mesma em
    todos os clones (o que é o caso: este arquivo sempre fica dentro de
    "Tools/CodeKnowledge", relativo à raiz do repositório).

    Retorna None caso nenhuma pasta ".git" seja encontrada.
    """

    pasta_atual = os.path.dirname(os.path.abspath(__file__))

    while True:
        if os.path.isdir(os.path.join(pasta_atual, ".git")):
            return pasta_atual

        pasta_pai = os.path.dirname(pasta_atual)
        if pasta_pai == pasta_atual:
            return None

        pasta_atual = pasta_pai


def obter_pasta_git():
    """
    Retorna o caminho da pasta do repositório Git.

    Se "pasta_git" estiver preenchido no config.json, esse valor tem
    prioridade (útil para apontar para um repositório fora do padrão).
    Caso contrário, tenta detectar automaticamente a raiz do
    repositório. Interrompe a execução com uma mensagem clara caso não
    seja possível determinar a pasta de nenhuma das duas formas.
    """

    config = carregar_config()
    pasta_git = (config.get("pasta_git") or "").strip()

    if pasta_git:
        return pasta_git

    pasta_detectada = detectar_pasta_git()

    if pasta_detectada:
        return pasta_detectada

    raise SystemExit(
        "Não foi possível localizar automaticamente a pasta do "
        "repositório (nenhuma pasta '.git' foi encontrada acima deste "
        f"arquivo).\nEdite o arquivo '{CONFIG_PATH}' e informe o "
        "caminho em 'pasta_git', ou rode:\n"
        "    python config.py"
    )


def obter_pasta_chroma_db():
    """
    Retorna o caminho configurado para a pasta do banco ChromaDB.

    Caminhos relativos (ex.: "./chroma_db") são resolvidos em relação à
    pasta deste projeto (onde fica o config.json), e não em relação ao
    diretório de onde o script foi chamado. Isso evita que o banco seja
    criado em um lugar inesperado quando os scripts forem executados a
    partir de outra pasta (ex.: um atalho, ou o futuro app Streamlit).
    """

    config = carregar_config()
    pasta_chroma_db = config.get("chroma_db") or CONFIG_PADRAO["chroma_db"]

    if os.path.isabs(pasta_chroma_db):
        return pasta_chroma_db

    pasta_projeto = os.path.dirname(CONFIG_PATH)
    return os.path.normpath(os.path.join(pasta_projeto, pasta_chroma_db))


def configurar_interativo():
    """
    Utilitário de linha de comando para configurar a pasta do repositório.

    Pode ser rodado diretamente com `python config.py`.
    """

    config = carregar_config()

    print("=== Configuração do Busca Códigos ===\n")

    pasta_configurada = (config.get("pasta_git") or "").strip()

    if pasta_configurada:
        pasta_atual = pasta_configurada
    else:
        pasta_detectada = detectar_pasta_git()
        if pasta_detectada:
            pasta_atual = f"{pasta_detectada}  (detectada automaticamente)"
        else:
            pasta_atual = "(não definida e não detectada automaticamente)"

    print(f"Pasta do repositório atual: {pasta_atual}")

    nova_pasta = input(
        "Informe o novo caminho da pasta do repositório, somente se "
        "quiser sobrepor a detecção automática "
        "(ENTER para manter o atual): "
    ).strip()

    if nova_pasta:
        if not os.path.isdir(nova_pasta):
            print(
                f"\nAviso: a pasta '{nova_pasta}' não foi encontrada no "
                "disco. A configuração será salva mesmo assim."
            )

        config["pasta_git"] = nova_pasta
        salvar_config(config)
        print(f"\nConfiguração salva em: {CONFIG_PATH}")
    else:
        print("\nNenhuma alteração feita.")


if __name__ == "__main__":
    configurar_interativo()
