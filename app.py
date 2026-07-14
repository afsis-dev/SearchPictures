import os
import threading
import webbrowser

from flask import Flask

from source.routes.api import api_blueprint
from source.utils.paths import is_frozen, resource_dir

app = Flask(
    __name__,
    template_folder=str(resource_dir() / "templates"),
    static_folder=str(resource_dir() / "static"),
)
app.register_blueprint(api_blueprint)

PORT = int(os.getenv("APP_PORT", "7000")) #Altere a porta aqui se necessário. A porta padrão é 7000.


def main():
    """Inicia o servidor web. Nenhuma conexão com banco é aberta aqui:
    a aplicação sobe offline e o usuário escolhe a fonte de busca na interface."""
    url = f"http://127.0.0.1:{PORT}"
    print(f"AFSIS Search Pictures disponível em {url}")
    if is_frozen():
        # No .exe, abre o navegador automaticamente para o usuário final
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(debug=False, port=PORT)


if __name__ == "__main__":
    main()
