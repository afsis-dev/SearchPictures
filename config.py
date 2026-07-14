import os

# Valores padrão para pré-preencher o formulário de conexão na interface web.
# Nenhuma conexão é aberta ao importar este módulo (offline-first).
# Propositalmente genéricos: dados de bases reais não devem ficar no código —
# informe-os pela interface ou via variáveis de ambiente.
DEFAULT_DB = {
    "host": os.getenv("DB_HOST", ""),
    "port": os.getenv("DB_PORT", "1521"),
    "service": os.getenv("DB_SERVICE", ""),
    "user": os.getenv("DB_USER", ""),
}

# A senha nunca é gravada em disco; só é usada se vier do ambiente.
DEFAULT_DB_PASSWORD = os.getenv("DB_PASSWORD", "")
