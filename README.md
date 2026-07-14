# AFSIS Search Pictures

Aplicação web local para buscar e baixar imagens de produtos a partir do código de barras (GTIN/EAN). As imagens são obtidas de APIs públicas e salvas em disco com o nome do código do produto, prontas para uso em catálogos, e-commerce ou ERP.

A aplicação sobe **offline**: nenhuma conexão com banco de dados é aberta na inicialização — o usuário escolhe a fonte de busca pela interface web.

## Funcionalidades

- **Busca via WinThor (Oracle)**: consulta a tabela `PCPRODUT` e baixa as imagens de todos os produtos ativos com código de barras. A query padrão pode ser editada na interface, desde que continue retornando as colunas `CODPROD`, `DESCRICAO` e `CODAUXILIAR`.
- **Busca via arquivo Excel**: envie um arquivo `.xls` ou `.xlsx` com a coluna `CODBARRA` (se ausente, a primeira coluna é usada) e as imagens são baixadas para cada código.
- **Múltiplas fontes de imagem**: as URLs são tentadas em ordem até encontrar a imagem. Fontes padrão:
  - `http://www.eanpictures.com.br:9000/api/gtin/{gtin}`
  - `https://cdn-cosmos.bluesoft.com.br/products/{gtin}`
- **Processamento em background** com acompanhamento em tempo real (progresso, encontradas/não encontradas, log) e possibilidade de cancelamento.
- **Rate limiting**: pausa de 10 segundos a cada 10 requisições para não sobrecarregar os servidores de imagens.
- **Download em ZIP** das imagens baixadas na última busca.
- **Configurações persistentes** (`settings.json`): URLs de API, pasta de destino, query e dados de conexão. A senha do banco **nunca é gravada em disco**.

## Requisitos

- Python 3.9+
- Acesso a um banco Oracle (apenas para a busca via WinThor)

Dependências (ver `requirements.txt`): Flask, requests, oracledb, pandas, openpyxl, xlrd.

## Instalação e execução (desenvolvimento)

```bash
git clone <url-do-repositorio>
cd SearchPictures

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

A aplicação fica disponível em `http://127.0.0.1:7000`. A porta pode ser alterada pela variável de ambiente `APP_PORT`.

## Gerando o executável Windows (.exe)

No Windows, execute:

```bat
setup\build.bat
```

O script instala as dependências, roda o PyInstaller com o spec `setup/AFSISSearchPictures.spec` e gera `dist\AFSISSearchPictures.exe` (onefile). Ao abrir o executável, o navegador é aberto automaticamente. Os arquivos graváveis (`settings.json`, log e imagens) ficam ao lado do `.exe`.

## Configuração

As configurações são editadas pela interface e persistidas em `settings.json` (na raiz do projeto em desenvolvimento; ao lado do executável quando congelado):

| Chave | Descrição |
|---|---|
| `api_urls` | Lista de URLs de busca de imagem; `{gtin}` é substituído pelo código de barras |
| `output_dir` | Pasta onde as imagens são salvas (padrão: `DOWNLOAD_API/`) |
| `product_query` | Query SQL da busca WinThor |
| `db` | Host, porta, service name e usuário do Oracle (sem senha) |

Os campos de conexão também podem ser pré-preenchidos por variáveis de ambiente: `DB_HOST`, `DB_PORT`, `DB_SERVICE`, `DB_USER` e `DB_PASSWORD` (a senha só é usada se vier do ambiente; nunca é salva).

## API

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Interface web |
| `GET/POST` | `/api/settings` | Lê/salva as configurações |
| `POST` | `/api/db/test` | Testa a conexão com o Oracle |
| `POST` | `/api/search/winthor` | Inicia a busca via banco WinThor |
| `POST` | `/api/search/file` | Inicia a busca via arquivo Excel (multipart, campo `file`) |
| `GET` | `/api/job/status` | Status/progresso do job em andamento |
| `POST` | `/api/job/cancel` | Solicita o cancelamento do job |
| `GET` | `/api/download/zip` | Baixa um ZIP com as imagens da última busca |

Apenas um job roda por vez; iniciar uma nova busca com outra em andamento retorna `409`.

## Estrutura do projeto

```
SearchPictures/
├── app.py                  # Ponto de entrada (Flask)
├── config.py               # Defaults de conexão via variáveis de ambiente
├── settings.json           # Configurações persistidas (gerado/editado pela interface)
├── requirements.txt
├── source/
│   ├── models/database.py  # Conexão Oracle (oracledb)
│   ├── routes/api.py       # Rotas da API e da interface
│   ├── services/images.py  # Download e gravação das imagens
│   ├── services/jobs.py    # Gerenciador de jobs em background
│   └── utils/paths.py      # Caminhos (dev vs. executável PyInstaller)
├── static/                 # CSS, JS e logo
├── templates/index.html    # Interface web
└── setup/                  # Build do executável Windows (PyInstaller)
```

## Logs

As mensagens de processamento são exibidas na interface e gravadas em `load_images.log` (na raiz do projeto ou ao lado do executável).

## Licença

Distribuído sob a licença [MIT](LICENSE).
