import io
import json
import os
import zipfile
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, send_file

from config import DEFAULT_DB, DEFAULT_DB_PASSWORD
from source.models.database import Database
from source.services.images import DEFAULT_IMAGE_URLS
from source.services.jobs import job_manager

from source.utils.paths import data_dir

api_blueprint = Blueprint("api", __name__)

SETTINGS_PATH = data_dir() / "settings.json"
DEFAULT_OUTPUT_DIR = data_dir() / "DOWNLOAD_API"

# Coluna esperada no arquivo XLS/XLSX de busca manual
FILE_KEY_COLUMN = "CODBARRA"

# Query padrão da busca WinThor; o usuário pode editá-la na interface,
# desde que continue retornando as colunas CODPROD, DESCRICAO e CODAUXILIAR.
DEFAULT_PRODUCT_QUERY = (
    "SELECT CODPROD, DESCRICAO, CODAUXILIAR\n"
    "  FROM PCPRODUT\n"
    " WHERE DTEXCLUSAO IS NULL\n"
    "   AND CODAUXILIAR IS NOT NULL"
)


def validate_product_query(query):
    """Validação básica da query editada pelo usuário."""
    query = str(query or "").strip().rstrip(";").strip()
    if not query:
        return DEFAULT_PRODUCT_QUERY
    if not query.lower().startswith("select"):
        raise ValueError("A query deve ser uma instrução SELECT.")
    if ";" in query:
        raise ValueError("Informe apenas uma instrução SELECT (sem ';').")
    return query


def load_settings():
    data = {}
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
    db = {**DEFAULT_DB, **(data.get("db") or {})}
    db.pop("password", None)  # senha nunca vem de/para o disco
    return {
        "api_urls": data.get("api_urls") or DEFAULT_IMAGE_URLS.copy(),
        "output_dir": data.get("output_dir") or str(DEFAULT_OUTPUT_DIR),
        "product_query": data.get("product_query") or DEFAULT_PRODUCT_QUERY,
        "db": db,
    }


def persist_settings(settings):
    settings = dict(settings)
    if "db" in settings:
        settings["db"] = {k: v for k, v in settings["db"].items() if k != "password"}
    SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def db_params_from_request(payload):
    saved = load_settings()["db"]
    params = {
        "host": (payload.get("host") or saved.get("host") or "").strip(),
        "port": str(payload.get("port") or saved.get("port") or "").strip(),
        "service": (payload.get("service") or saved.get("service") or "").strip(),
        "user": (payload.get("user") or saved.get("user") or "").strip(),
        "password": payload.get("password") or DEFAULT_DB_PASSWORD,
    }
    missing = [k for k, v in params.items() if not v]
    if missing:
        raise ValueError(f"Informe os campos de conexão: {', '.join(missing)}.")
    return params


def remember_db(params):
    settings = load_settings()
    settings["db"] = {k: params[k] for k in ("host", "port", "service", "user")}
    persist_settings(settings)


@api_blueprint.route("/")
def index():
    return render_template("index.html")


@api_blueprint.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify({**load_settings(), "default_product_query": DEFAULT_PRODUCT_QUERY})


@api_blueprint.route("/api/settings", methods=["POST"])
def save_settings():
    payload = request.get_json(silent=True) or {}
    settings = load_settings()

    urls = [u.strip() for u in payload.get("api_urls", []) if str(u).strip()]
    if not urls:
        return jsonify({"error": "Informe ao menos uma URL de API válida."}), 400

    output_dir = str(payload.get("output_dir") or "").strip()
    if not output_dir:
        return jsonify({"error": "Informe a pasta onde as imagens serão salvas."}), 400
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return jsonify({"error": f"Não foi possível criar a pasta: {e}"}), 400

    settings["api_urls"] = urls
    settings["output_dir"] = output_dir
    persist_settings(settings)
    return jsonify(load_settings())


@api_blueprint.route("/api/db/test", methods=["POST"])
def test_connection():
    payload = request.get_json(silent=True) or {}
    try:
        params = db_params_from_request(payload)
        database = Database(**params)
        database.query("SELECT 1 FROM DUAL")
        database.close()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Falha na conexão: {e}"}), 502

    remember_db(params)
    return jsonify({"message": "Conexão estabelecida com sucesso."})


@api_blueprint.route("/api/search/winthor", methods=["POST"])
def search_winthor():
    if job_manager.is_running():
        return jsonify({"error": "Já há uma operação em andamento."}), 409

    payload = request.get_json(silent=True) or {}
    try:
        params = db_params_from_request(payload)
        product_query = validate_product_query(payload.get("query"))
        # Valida credenciais antes de iniciar o job em background
        database = Database(**params)
        database.close()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Falha na conexão: {e}"}), 502

    remember_db(params)
    settings = load_settings()
    settings["product_query"] = product_query
    persist_settings(settings)

    def fetch_items():
        job_manager.log("Consultando produtos no WinThor...")
        database = Database(**params)
        try:
            rows = database.query(product_query)
        finally:
            database.close()
        rows = rows or []
        if rows and len(rows[0]) < 3:
            raise ValueError(
                "A query deve retornar as colunas CODPROD, DESCRICAO e CODAUXILIAR."
            )
        return [
            {
                "codprod": row[0],
                "descricao": row[1],
                "gtin": str(row[2] or "").strip(),
            }
            for row in rows
        ]

    job_manager.start("winthor", fetch_items, settings["api_urls"], settings["output_dir"])
    return jsonify({"message": "Busca no WinThor iniciada."})


@api_blueprint.route("/api/search/file", methods=["POST"])
def search_file():
    if job_manager.is_running():
        return jsonify({"error": "Já há uma operação em andamento."}), 409

    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"error": "Selecione um arquivo XLS ou XLSX."}), 400

    filename = upload.filename.lower()
    if filename.endswith(".xls"):
        engine = "xlrd"
    elif filename.endswith(".xlsx"):
        engine = "openpyxl"
    else:
        return jsonify({"error": "Formato não suportado. Use .xls ou .xlsx."}), 400

    try:
        import pandas as pd

        df = pd.read_excel(upload, dtype=str, engine=engine)
    except Exception as e:
        return jsonify({"error": f"Erro ao ler o arquivo Excel: {e}"}), 400

    if df.empty:
        return jsonify({"error": "O arquivo Excel está vazio."}), 400

    # Por padrão o arquivo deve ter a coluna CODBARRA; caso não exista,
    # a primeira coluna é usada como fallback.
    warning = None
    lower_columns = {str(col).strip().lower(): col for col in df.columns}
    key_column = lower_columns.get(FILE_KEY_COLUMN.lower())
    if key_column is None:
        key_column = df.columns[0]
        warning = (
            f"Coluna {FILE_KEY_COLUMN} não encontrada; usando a primeira coluna "
            f"do arquivo ('{key_column}') como código de barras."
        )

    items = []
    seen = set()
    for value in df[key_column]:
        codbarra = str(value or "").strip()
        if not codbarra or codbarra.lower() == "nan" or codbarra in seen:
            continue
        seen.add(codbarra)
        items.append({"codprod": codbarra, "descricao": "Arquivo", "gtin": codbarra})

    if not items:
        return jsonify({"error": "Nenhum código de barras válido encontrado no arquivo."}), 400

    settings = load_settings()
    job_manager.start("arquivo", lambda: items, settings["api_urls"], settings["output_dir"])
    job_manager.log(f"Arquivo '{upload.filename}' carregado.")
    if warning:
        job_manager.log(warning)
    return jsonify({"message": f"Busca por arquivo iniciada ({len(items)} códigos)."})


@api_blueprint.route("/api/job/status", methods=["GET"])
def job_status():
    after = request.args.get("after", default=0, type=int)
    return jsonify(job_manager.status(after=after))


@api_blueprint.route("/api/job/cancel", methods=["POST"])
def job_cancel():
    job_manager.cancel()
    return jsonify({"message": "Cancelamento solicitado."})


@api_blueprint.route("/api/download/zip", methods=["GET"])
def download_zip():
    files = job_manager.saved_files_snapshot()
    if not files:
        return jsonify({"error": "Nenhuma imagem baixada na última busca."}), 404

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in files:
            if os.path.exists(path):
                zip_file.write(path, arcname=os.path.basename(path))
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="imagens.zip",
    )
