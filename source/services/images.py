import os
from datetime import datetime

import requests

from source.utils.paths import data_dir

LOG_FILE = str(data_dir() / "load_images.log")

# URLs padrão para busca de imagens; {gtin} é substituído pelo código de barras.
DEFAULT_IMAGE_URLS = [
    "http://www.eanpictures.com.br:9000/api/gtin/{gtin}",
    "https://cdn-cosmos.bluesoft.com.br/products/{gtin}",
]


def log_message(message):
    """Registra mensagens de log em arquivo."""
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(f"{datetime.now()}: {message}\n")


def download_image(gtin, urls):
    """Tenta baixar a imagem usando a lista de URLs informadas, na ordem."""
    for template in urls:
        image_url = template.format(gtin=gtin)
        try:
            response = requests.get(image_url, timeout=10)
        except requests.RequestException:
            continue
        if response.status_code == 200 and response.content:
            return response.content, image_url
    return None, None


def save_image(codprod, image_data, output_dir):
    """Salva a imagem no diretório especificado e retorna o caminho do arquivo."""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(str(output_dir), f"{codprod}.jpg")
    with open(file_path, "wb") as file:
        file.write(image_data)
    return file_path


def process_product(codprod, descricao, gtin, urls, output_dir, log=log_message):
    """Processa um produto individual, baixando sua imagem.

    Retorna (encontrado, caminho_do_arquivo_ou_None).
    """
    gtin = str(gtin or "").strip()
    if not gtin:
        log(f"GTIN vazio para {descricao} ({codprod}); pulando registro.")
        return False, None

    try:
        image_data, source_url = download_image(gtin, urls)
        if image_data:
            file_path = save_image(codprod, image_data, output_dir)
            log(f"Imagem encontrada e salva para {descricao} ({codprod}) via {source_url}")
            return True, file_path

        log(f"Imagem não encontrada para {descricao} ({codprod}) em todas as fontes.")
        return False, None
    except Exception as e:
        log(f"Erro ao processar {descricao} ({codprod}): {e}")
        return False, None
