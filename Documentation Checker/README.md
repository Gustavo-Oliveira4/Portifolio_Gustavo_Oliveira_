<div align="center">

# 📄 Documentation Checker

### Verificação automática de documentação dos projetos de um repositório Git

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?logo=git&logoColor=white)
![Status](https://img.shields.io/badge/status-em%20uso-005EB8)

Ferramenta interna que percorre o repositório Git do time e identifica quais projetos
possuem documentação (README, Markdown ou Word) e quais ainda precisam ser documentados.

[Sobre](#-sobre-o-projeto) •
[Funcionalidades](#-funcionalidades) •
[Tecnologias](#-tecnologias) •
[Como executar](#-como-executar) •
[Configuração](#%EF%B8%8F-configuração) •
[Como funciona](#-como-funciona) •
[Autor](#-autor)

</div>

---

## 📌 Sobre o projeto

Em repositórios compartilhados por vários países e áreas, é comum que projetos sejam adicionados
sem nenhuma documentação. Com o tempo, fica difícil saber o que cada projeto faz, quem o criou e
como utilizá-lo.

O **Documentation Checker** resolve esse problema de forma automática:

| Etapa | O que acontece |
|---|---|
| 🔍 **Varredura** | Percorre a estrutura `País / Área / Projeto` do repositório |
| 🧭 **Classificação** | Separa pastas de organização (estrutura) das pastas que são projetos de fato |
| 📑 **Verificação** | Procura README, arquivos Markdown ou documentos Word em cada projeto |
| 👤 **Rastreabilidade** | Consulta o histórico do Git para identificar quem adicionou cada projeto sem documentação |
| 📊 **Relatório** | Exibe indicadores, tabelas e permite exportar a lista de pendências em CSV |

A verificação vale para **qualquer tipo de projeto**: Python, Power BI, SQL, Excel, automações etc.

---

## ✨ Funcionalidades

- **Interface web** simples, com identidade visual Danone, e também **execução pelo terminal**
- **Cartões de resumo:** projetos verificados, documentados, sem documentação e percentual de cobertura
- **Aba "Sem documentação":** projeto, localização, quem adicionou, e-mail e data do primeiro commit
- **Exportação em CSV** da lista de projetos sem documentação, pronta para abrir no Excel
- **Aba "Com documentação":** tipo e caminho do documento encontrado em cada projeto
- **Aba "Pastas de estrutura":** pastas de organização e arquivos soltos fora de projetos
- **Detecção automática** da pasta do repositório e do executável do Git
- **Saída sem acentos**, para evitar problemas de codificação no terminal e no CSV

### 🚦 Status por projeto

| Status | Significado |
|---|---|
| 🟢 **Qualidade de dados OK** | O projeto possui README, Markdown ou Word, ou é uma pasta de apoio |
| 🔴 **Qualidade de dados falha** | Nenhuma documentação encontrada no projeto |

---

## 🛠️ Tecnologias

| Tecnologia | Uso |
|---|---|
| **Python 3.10+** | Linguagem principal |
| **Streamlit** | Interface web |
| **Pandas** | Montagem das tabelas e exportação em CSV |
| **Git** | Consulta ao histórico para identificar o autor de cada projeto |
| **JSON** | Arquivo de configuração (`config.json`) |

---

## 🚀 Como executar

### Pré-requisitos
- [Python 3.10 ou superior](https://www.python.org/downloads/)
- [Git](https://git-scm.com/) instalado (opcional, mas necessário para exibir o autor dos projetos)
- Acesso ao repositório Git que será verificado

### 1. Clonar o repositório
```bash
git clone https://github.com/SEU-USUARIO/documentation-checker.git
cd documentation-checker
```

### 2. Criar e ativar o ambiente virtual
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Instalar as dependências
```bash
pip install streamlit pandas
```

### 4. Configurar a pasta do repositório
```bash
python config.py
```
Informe o caminho do repositório a ser verificado ou pressione **ENTER** para usar a detecção
automática (veja [Configuração](#%EF%B8%8F-configuração)).

### 5. Executar

**Interface web:**
```bash
python -m streamlit run app_verificador.py
```
Acesse **http://localhost:8501** e clique em **▶️ Executar verificação**.

**Terminal:**
```bash
python verificador_documentacao.py
```

---

## ⚙️ Configuração

A pasta do repositório é definida no arquivo `config.json`:

```json
{
  "pasta_git": "",
  "chroma_db": "./chroma_db"
}
```

| Chave | Descrição |
|---|---|
| `pasta_git` | Caminho do repositório a ser verificado. Se ficar vazio, o sistema procura automaticamente a pasta `.git` acima da pasta do projeto |
| `chroma_db` | Pasta do banco ChromaDB, usada por outros módulos do ecossistema (não é usada pelo verificador) |

> Se o arquivo `config.json` não existir, ele é criado automaticamente com os valores padrão.

### 🔧 Git fora do PATH

O verificador procura o Git automaticamente no PATH e nas pastas padrão do Windows (Git for Windows,
GitHub Desktop e Visual Studio). Se ele estiver instalado em outro local, defina a variável de ambiente:

```powershell
# Windows (PowerShell)
$env:GIT_EXE="C:\caminho\para\git.exe"
```

Sem o Git, a verificação funciona normalmente, mas o autor dos projetos aparece como **"Não informado"**.

### 🎛️ Parâmetros ajustáveis

As regras ficam no início do arquivo `verificador_documentacao.py`:

| Parâmetro | Função |
|---|---|
| `PAISES_VALIDOS` | Pastas de primeiro nível que serão verificadas |
| `NIVEL_MINIMO_PROJETO` | Nível a partir do qual uma pasta pode ser considerada projeto (padrão: 3) |
| `PASTAS_ESTRUTURA` | Nomes de pastas que sempre são estrutura |
| `PROJETOS_FORCADOS` | Nomes de pastas que sempre são projeto |
| `PASTAS_SEMPRE_OK` | Pastas de apoio que não exigem documentação (`support_files`, `classes`, `.vscode`) |
| `CONSIDERAR_WORD_COMO_DOCUMENTACAO` | Aceita documentos Word como documentação |
| `CONSIDERAR_MD_COMO_DOCUMENTACAO` | Aceita qualquer arquivo Markdown como documentação |
| `BUSCAR_README_EM_SUBPASTAS` | Procura a documentação também nas subpastas do projeto |
| `PASTAS_IGNORADAS` | Pastas técnicas ignoradas na varredura (`.git`, `.venv`, `node_modules`...) |

---

## 🧠 Como funciona

### Estrutura esperada do repositório
```
REPOSITÓRIO
└── País              (ex.: Brazil, Mexico, USA, Global...)
    └── Área
        └── (Subáreas / Categorias opcionais)
            └── Projeto
                └── arquivos de qualquer tipo
```

### 1. Identificação de projetos
Uma pasta é considerada **projeto** quando, a partir do 3º nível:
1. está listada em `PROJETOS_FORCADOS` ou `PASTAS_SEMPRE_OK`; **ou**
2. contém arquivos diretamente dentro dela; **ou**
3. contém subpastas típicas de projeto (`src`, `docs`, `sql`, `scripts`, `notebooks`, `tests`...).

Pastas que apenas organizam outras pastas são classificadas como **estrutura** e não são avaliadas.

### 2. Busca da documentação
A documentação é procurada nesta ordem de prioridade:

| Prioridade | Tipo | Exemplos |
|---|---|---|
| 1 | **README** | `README.md`, `README.txt`, `README_fleteros.md`, `README-projeto.md` |
| 2 | **Markdown** | Qualquer arquivo `.md` ou `.markdown` |
| 3 | **Word** | `.docx`, `.doc`, `.docm`, `.dotx`, `.dot`, `.rtf` |

Arquivos temporários do Word (iniciados por `~$`) são ignorados.

### 3. Identificação do autor
Para projetos sem documentação, o verificador consulta o histórico do Git
(`git log --diff-filter=A --reverse`) e retorna o **nome, e-mail e data** do primeiro commit
que adicionou a pasta ao repositório.

---

## 📁 Estrutura de pastas

```
documentation-checker/
├── app_verificador.py           # Interface web (Streamlit)
├── verificador_documentacao.py  # Lógica de verificação e execução pelo terminal
├── config.py                    # Leitura, gravação e detecção da configuração
├── config.json                  # Caminho do repositório a ser verificado
└── assets/                      # (opcional) logos e ícone da interface
    ├── logo_danone_branco.png
    ├── logo_di_branco.png
    └── icon.ico
```

> A pasta `assets` é opcional. Se os arquivos não existirem, a interface funciona normalmente, sem os logos.

---

## 🔮 Melhorias futuras

- [ ] Arquivo `requirements.txt` com as versões das dependências
- [ ] Tela de configuração na própria interface, sem precisar do terminal
- [ ] Validação do conteúdo mínimo do README (descrição, como executar, responsável)
- [ ] Histórico das verificações para acompanhar a evolução da cobertura
- [ ] Envio automático da lista de pendências aos responsáveis
- [ ] Execução agendada (por exemplo, semanal) com geração de relatório

---

## 👨‍💻 Autor

**Gustavo de Oliveira**
Estagiário · Digital Innovation · Brasil

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/SEU-PERFIL)
[![GitHub](https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=white)](https://github.com/SEU-USUARIO)

---

<div align="center">

Ferramenta desenvolvida para apoiar a governança e a qualidade da documentação dos projetos do time.

</div>
