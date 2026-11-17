"""
Verificador de documentacao do DI Code Knowledge.

Percorre o mesmo repositorio Git usado pelo `indexador.py`:

    PASTA_GIT
    └── Pais
        └── Area
            └── (Subareas / Categorias opcionais...)
                └── Projeto
                    └── arquivos (qualquer tipo)

- Verifica TODO TIPO de projeto (Python, Power BI, SQL, Excel etc.).
- SEPARA as pastas de estrutura (Pais, Area, Subarea, Categoria) das
  pastas que sao projetos de fato. Uma pasta e projeto quando contem
  arquivos diretamente ou subpastas tipicas de projeto (src, docs,
  sql, scripts...). Pastas que so organizam outras pastas sao
  estrutura e nao sao avaliadas.
- Documentacao aceita: arquivo README (qualquer extensao, inclusive
  com sufixo, como README_fleteros.md), qualquer arquivo Markdown
  (.md) ou documento Word (.docx...).
- Pastas de apoio (support_files, classes, .vscode) sao sempre OK.

Resultado por projeto:
- Sem documentacao: "Qualidade de dados falha", com o nome do projeto
  e quem o adicionou ao repositorio (primeiro commit no Git).
- Com documentacao: "Qualidade de dados OK".

Toda a saida e exibida sem acentos.

Uso pelo terminal:
    python verificador_documentacao.py

Uso pela interface: app.py.
"""

import os
import shutil
import subprocess
import unicodedata

from config import obter_pasta_git

# ============================================================
# CONFIGURACOES
# ============================================================

PASTA_GIT = obter_pasta_git()

PAISES_VALIDOS = {
    "Argentina",
    "Brazil",
    "Global",
    "Mexico",
    "SOUTH CONE",
    "USA"
}

PASTAS_IGNORADAS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "chroma_db"
}

# Arquivos tecnicos que nao contam como conteudo do projeto.
ARQUIVOS_IGNORADOS = {
    ".gitkeep",
    ".gitignore",
    ".ds_store",
    "thumbs.db",
    "desktop.ini"
}

# ------------------------------------------------------------
# SEPARACAO ENTRE PASTAS DE ESTRUTURA E PROJETOS
# ------------------------------------------------------------
# Nivel minimo em que uma pasta pode ser projeto:
#   1 = Pais | 2 = Area | 3 = Projeto (ou Subarea)
NIVEL_MINIMO_PROJETO = 3

# Subpastas tipicas de DENTRO de um projeto. Se uma pasta contem
# alguma delas, ela e o projeto.
SUBPASTAS_INTERNAS_DE_PROJETO = {
    "src", "source", "code", "codigo", "scripts", "script",
    "docs", "doc", "documentation", "documentacao",
    "sql", "queries", "query", "notebooks", "notebook",
    "data", "dados", "input", "output", "files", "arquivos",
    "assets", "images", "imagens", "img",
    "config", "configs", "tests", "test",
    "lib", "libs", "utils", "modules", "templates",
    "flows", "fluxos", "macros"
}

# Nomes de pastas que SEMPRE sao estrutura (em minusculas).
# Ex.: {"planning", "power bi", "automations"}
PASTAS_ESTRUTURA = set()

# Nomes de pastas que SEMPRE sao projeto (em minusculas).
PROJETOS_FORCADOS = set()

# Pastas que SEMPRE recebem "Qualidade de dados OK", mesmo sem
# README ou Word (pastas de apoio/configuracao). Em minusculas.
PASTAS_SEMPRE_OK = {
    "support_files",
    "classes",
    ".vscode"
}

# ------------------------------------------------------------
# DOCUMENTACAO
# ------------------------------------------------------------
# Documentos Word tambem contam como documentacao.
CONSIDERAR_WORD_COMO_DOCUMENTACAO = True

EXTENSOES_WORD = {
    ".docx",
    ".doc",
    ".docm",
    ".dotx",
    ".dot",
    ".rtf"
}

# Qualquer arquivo Markdown (.md) tambem conta como documentacao.
# Use False para aceitar somente README e Word.
CONSIDERAR_MD_COMO_DOCUMENTACAO = True

EXTENSOES_MD = {
    ".md",
    ".markdown"
}

# Procura a documentacao tambem em subpastas do projeto.
BUSCAR_README_EM_SUBPASTAS = True

STATUS_OK = "Qualidade de dados OK"
STATUS_FALHA = "Qualidade de dados falha"
MARCADOR_RESULTADO = "RESULTADO DA VERIFICACAO"


# ============================================================
# SAIDA SEM ACENTOS
# ============================================================

def remover_acentos(texto):
    """
    Remove acentos e cedilha (ex.: "Documentação" -> "Documentacao").
    """
    texto_normalizado = unicodedata.normalize("NFKD", str(texto))
    return "".join(
        caractere
        for caractere in texto_normalizado
        if not unicodedata.combining(caractere)
    )


def imprimir(*valores, **kwargs):
    print(*(remover_acentos(valor) for valor in valores), **kwargs)


# ============================================================
# LOCALIZACAO DOS PROJETOS
# ============================================================

def nome_normalizado(nome):
    return nome.strip().lower()


def listar_subpastas(pasta):
    try:
        itens = sorted(os.listdir(pasta))
    except OSError:
        return []

    return [
        item
        for item in itens
        if item not in PASTAS_IGNORADAS
        and os.path.isdir(os.path.join(pasta, item))
    ]


def listar_arquivos_diretos(pasta):
    try:
        itens = sorted(os.listdir(pasta))
    except OSError:
        return []

    return [
        item
        for item in itens
        if item.lower() not in ARQUIVOS_IGNORADOS
        and os.path.isfile(os.path.join(pasta, item))
    ]


def percorrer_projeto(pasta_projeto):
    for raiz, pastas, arquivos in os.walk(pasta_projeto):
        pastas[:] = [
            pasta
            for pasta in pastas
            if pasta not in PASTAS_IGNORADAS
        ]
        yield raiz, arquivos


def possui_arquivos(pasta):
    for _, arquivos in percorrer_projeto(pasta):
        for arquivo in arquivos:
            if arquivo.lower() not in ARQUIVOS_IGNORADOS:
                return True
    return False


def eh_pasta_de_projeto(pasta, nivel):
    """
    Regras, em ordem:
    1. Abaixo do NIVEL_MINIMO_PROJETO nunca e projeto (Pais e Area).
    2. Nome em PASTAS_ESTRUTURA -> estrutura.
    3. Nome em PROJETOS_FORCADOS ou PASTAS_SEMPRE_OK -> projeto.
    4. Tem arquivos diretamente dentro -> projeto.
    5. Tem subpasta tipica de projeto (src, docs, sql...) -> projeto.
    6. Caso contrario -> estrutura.
    """
    nome = nome_normalizado(os.path.basename(pasta))

    if nivel < NIVEL_MINIMO_PROJETO:
        return False

    if nome in PASTAS_ESTRUTURA:
        return False

    if nome in PROJETOS_FORCADOS or nome in PASTAS_SEMPRE_OK:
        return True

    if listar_arquivos_diretos(pasta):
        return True

    subpastas = {
        nome_normalizado(subpasta)
        for subpasta in listar_subpastas(pasta)
    }

    return bool(subpastas & SUBPASTAS_INTERNAS_DE_PROJETO)


def listar_projetos():
    """
    Retorna (projetos, pastas_estrutura, arquivos_soltos).
    """
    projetos = []
    pastas_estrutura = []
    arquivos_soltos = []

    def visitar(pasta, caminho_estrutura, nivel):
        if not possui_arquivos(pasta):
            return

        if eh_pasta_de_projeto(pasta, nivel):
            projetos.append({
                "projeto": os.path.basename(pasta),
                "estrutura": caminho_estrutura,
                "pasta_projeto": pasta
            })
            return

        pastas_estrutura.append(
            " / ".join(caminho_estrutura + [os.path.basename(pasta)])
        )

        for arquivo in listar_arquivos_diretos(pasta):
            arquivos_soltos.append(
                os.path.relpath(os.path.join(pasta, arquivo), PASTA_GIT)
            )

        for subpasta in listar_subpastas(pasta):
            visitar(
                os.path.join(pasta, subpasta),
                caminho_estrutura + [os.path.basename(pasta)],
                nivel + 1
            )

    for pais in listar_subpastas(PASTA_GIT):
        if pais not in PAISES_VALIDOS:
            continue
        visitar(os.path.join(PASTA_GIT, pais), [], 1)

    return projetos, pastas_estrutura, arquivos_soltos


# ============================================================
# VERIFICACAO DA DOCUMENTACAO (README ou Word)
# ============================================================

def eh_readme(nome_arquivo):
    """
    Aceita README, README.md, README.txt etc. e tambem arquivos com
    sufixo apos "README", como README_fleteros.md, README-projeto.md
    ou README projeto.md.
    """
    nome = os.path.splitext(nome_arquivo)[0].lower()
    if nome == "readme":
        return True
    return nome.startswith(("readme_", "readme-", "readme ", "readme."))


def eh_word(nome_arquivo):
    if not CONSIDERAR_WORD_COMO_DOCUMENTACAO:
        return False
    if nome_arquivo.startswith("~$"):
        return False
    return os.path.splitext(nome_arquivo)[1].lower() in EXTENSOES_WORD


def eh_markdown(nome_arquivo):
    if not CONSIDERAR_MD_COMO_DOCUMENTACAO:
        return False
    return os.path.splitext(nome_arquivo)[1].lower() in EXTENSOES_MD


def listar_arquivos_para_documentacao(pasta_projeto):
    if not BUSCAR_README_EM_SUBPASTAS:
        for arquivo in sorted(os.listdir(pasta_projeto)):
            caminho = os.path.join(pasta_projeto, arquivo)
            if os.path.isfile(caminho):
                yield arquivo, caminho
        return

    for raiz, arquivos in percorrer_projeto(pasta_projeto):
        for arquivo in sorted(arquivos):
            yield arquivo, os.path.join(raiz, arquivo)


def encontrar_documentacao(pasta_projeto):
    """
    Prioridade: README > Markdown (.md) > Word.
    Retorna (tipo, caminho) ou (None, None).
    """
    primeiro_md = None
    primeiro_word = None

    for nome, caminho in listar_arquivos_para_documentacao(pasta_projeto):
        if eh_readme(nome):
            return "README", caminho
        if primeiro_md is None and eh_markdown(nome):
            primeiro_md = caminho
        if primeiro_word is None and eh_word(nome):
            primeiro_word = caminho

    if primeiro_md:
        return "Markdown", primeiro_md

    if primeiro_word:
        return "Word", primeiro_word

    return None, None


# ============================================================
# QUEM ADICIONOU O PROJETO (HISTORICO DO GIT)
# ============================================================

def localizar_git():
    """
    Encontra o executavel do Git mesmo quando ele nao esta no PATH.

    Ordem de busca:
    1. Variavel de ambiente GIT_EXE (caminho completo do git.exe).
    2. PATH do sistema.
    3. Locais padrao de instalacao no Windows (Git for Windows,
       instalacao por usuario, GitHub Desktop, Visual Studio).
    """
    caminho_env = os.environ.get("GIT_EXE", "").strip().strip('"')
    if caminho_env and os.path.isfile(caminho_env):
        return caminho_env

    caminho_path = shutil.which("git")
    if caminho_path:
        return caminho_path

    if os.name != "nt":
        return None

    candidatos = []
    for variavel in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        base = os.environ.get(variavel)
        if base:
            candidatos += [
                os.path.join(base, "Git", "cmd", "git.exe"),
                os.path.join(base, "Git", "bin", "git.exe"),
            ]

    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        candidatos += [
            os.path.join(local, "Programs", "Git", "cmd", "git.exe"),
            os.path.join(local, "Programs", "Git", "bin", "git.exe"),
        ]

        # Git embutido no GitHub Desktop (pasta muda a cada versao).
        pasta_desktop = os.path.join(local, "GitHubDesktop")
        if os.path.isdir(pasta_desktop):
            for versao in sorted(os.listdir(pasta_desktop), reverse=True):
                candidatos.append(os.path.join(
                    pasta_desktop, versao, "resources", "app",
                    "git", "cmd", "git.exe"
                ))

    # Git embutido no Visual Studio.
    for base in (
        os.environ.get("ProgramFiles", ""),
        os.environ.get("ProgramFiles(x86)", ""),
    ):
        pasta_vs = os.path.join(base, "Microsoft Visual Studio")
        if base and os.path.isdir(pasta_vs):
            for raiz, _, arquivos in os.walk(pasta_vs):
                if "git.exe" in arquivos and raiz.lower().endswith("cmd"):
                    candidatos.append(os.path.join(raiz, "git.exe"))
                    break

    for candidato in candidatos:
        if os.path.isfile(candidato):
            return candidato

    return None


GIT_EXE = localizar_git()
GIT_DISPONIVEL = GIT_EXE is not None


def obter_quem_adicionou(pasta_projeto):
    nao_informado = {"nome": "Not informed", "email": "", "data": ""}

    if not GIT_DISPONIVEL:
        return nao_informado

    caminho_relativo = os.path.relpath(
        pasta_projeto, PASTA_GIT
    ).replace(os.sep, "/")

    comando = [
        GIT_EXE, "-c", "core.quotepath=off",
        "log", "--diff-filter=A", "--reverse",
        "--format=%an|%ae|%ad", "--date=short",
        "--", caminho_relativo
    ]

    flags_criacao = 0
    if os.name == "nt":
        flags_criacao = subprocess.CREATE_NO_WINDOW

    try:
        resultado = subprocess.run(
            comando,
            cwd=PASTA_GIT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            creationflags=flags_criacao
        )
    except Exception:
        return nao_informado

    if resultado.returncode != 0:
        return nao_informado

    linhas = [l.strip() for l in resultado.stdout.splitlines() if l.strip()]
    if not linhas:
        return nao_informado

    nome, email, data = (linhas[0].split("|") + ["", "", ""])[:3]
    return {"nome": nome or "Not informed", "email": email, "data": data}


def formatar_autor(autor):
    texto = autor["nome"]
    if autor["email"]:
        texto += f" ({autor['email']})"
    if autor["data"]:
        texto += f" em {autor['data']}"
    return texto


# ============================================================
# EXECUCAO (usada pelo terminal e pelo app.py)
# ============================================================

def executar_verificacao():
    if not os.path.isdir(PASTA_GIT):
        raise FileNotFoundError(
            f"A pasta do Git nao foi encontrada: {PASTA_GIT}"
        )

    projetos, pastas_estrutura, arquivos_soltos = listar_projetos()
    projetos_ok = []
    projetos_falha = []

    for dados in projetos:
        dados["localizacao"] = " / ".join(dados["estrutura"])

        if nome_normalizado(dados["projeto"]) in PASTAS_SEMPRE_OK:
            dados["tipo_doc"] = "Sempre OK"
            dados["readme"] = "pasta de apoio (nao exige documentacao)"
            projetos_ok.append(dados)
            continue

        tipo_doc, caminho_doc = encontrar_documentacao(dados["pasta_projeto"])

        if caminho_doc:
            dados["tipo_doc"] = tipo_doc
            dados["readme"] = os.path.relpath(caminho_doc, dados["pasta_projeto"])
            projetos_ok.append(dados)
        else:
            dados["autor"] = obter_quem_adicionou(dados["pasta_projeto"])
            projetos_falha.append(dados)

    return {
        "pasta_git": PASTA_GIT,
        "git_disponivel": GIT_DISPONIVEL,
        "projetos": projetos,
        "projetos_ok": projetos_ok,
        "projetos_falha": projetos_falha,
        "pastas_estrutura": pastas_estrutura,
        "arquivos_soltos": arquivos_soltos
    }


def imprimir_relatorio(resultado):
    projetos_ok = resultado["projetos_ok"]
    projetos_falha = resultado["projetos_falha"]

    if not resultado["git_disponivel"]:
        imprimir(
            "WARNING: git nao foi encontrado no PATH. "
            "O autor dos projetos sera exibido como 'Not informed'."
        )

    if not resultado["projetos"]:
        imprimir("\nNenhum projeto encontrado na estrutura Pais/Area/Projeto.")
        return

    imprimir("\n" + "=" * 80)
    imprimir(MARCADOR_RESULTADO)
    imprimir("=" * 80)

    if projetos_falha:
        imprimir("\nPROJETOS SEM DOCUMENTACAO (sem README, sem .md e sem Word):\n")
        for d in projetos_falha:
            imprimir(STATUS_FALHA)
            imprimir(f"  Projeto: {d['projeto']}")
            imprimir(f"  Localizacao: {d['localizacao']}")
            imprimir(f"  Adicionado por: {formatar_autor(d['autor'])}")
            imprimir("-" * 80)

    if projetos_ok:
        imprimir("\nPROJETOS COM DOCUMENTACAO:\n")
        for d in projetos_ok:
            imprimir(
                f"{STATUS_OK} | {d['localizacao']} | "
                f"{d['projeto']} | {d['tipo_doc']}: {d['readme']}"
            )

    if resultado["pastas_estrutura"]:
        imprimir("\nPASTAS DE ESTRUTURA (nao sao projetos, nao foram avaliadas):\n")
        for caminho in resultado["pastas_estrutura"]:
            imprimir(f"- {caminho}")

    if resultado["arquivos_soltos"]:
        imprimir("\nATENCAO - ARQUIVOS SOLTOS EM PASTAS DE ESTRUTURA:\n")
        for caminho in resultado["arquivos_soltos"]:
            imprimir(f"- {caminho}")

    imprimir("\n" + "=" * 80)
    imprimir("RESUMO")
    imprimir("=" * 80)
    imprimir(f"Pastas de estrutura: {len(resultado['pastas_estrutura'])}")
    imprimir(f"Projetos verificados: {len(resultado['projetos'])}")
    imprimir(f"{STATUS_OK}: {len(projetos_ok)}")
    imprimir(f"{STATUS_FALHA}: {len(projetos_falha)}")
    imprimir(f"Arquivos soltos fora de projetos: {len(resultado['arquivos_soltos'])}")


if __name__ == "__main__":
    try:
        imprimir_relatorio(executar_verificacao())
    except FileNotFoundError as erro:
        imprimir(f"ERROR: {erro}")
        raise SystemExit(1)
