import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def is_frozen():
    """True quando rodando como executável PyInstaller."""
    return getattr(sys, "frozen", False)


def resource_dir():
    """Assets somente leitura (templates/static). No .exe onefile do
    PyInstaller aponta para a pasta temporária _MEIPASS."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return PROJECT_ROOT


def data_dir():
    """Arquivos graváveis (settings.json, log, imagens): ao lado do
    executável quando congelado; raiz do projeto em desenvolvimento."""
    if is_frozen():
        return Path(sys.executable).parent
    return PROJECT_ROOT
