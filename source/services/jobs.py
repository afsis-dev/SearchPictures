import threading
import time

from source.services.images import log_message, process_product

PAUSE_AFTER_REQUESTS = 10  # pausa após este número de requisições
PAUSE_SECONDS = 10         # duração da pausa em segundos


class JobManager:
    """Executa uma busca de imagens por vez, em thread de background.

    O estado é consultado pela interface web via polling (/api/job/status).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._thread = None
        self._cancel = threading.Event()
        self._reset()

    def _reset(self):
        self.source = None
        self.running = False
        self.finished = False
        self.cancelled = False
        self.total = 0
        self.done = 0
        self.found = 0
        self.not_found = 0
        self.messages = []
        self.saved_files = []

    def is_running(self):
        with self._lock:
            return self.running

    def start(self, source, items_provider, urls, output_dir):
        """Inicia um job. items_provider é chamado dentro da thread e deve
        retornar a lista de itens ({codprod, descricao, gtin}); pode demorar
        (ex.: consulta ao Oracle) e pode lançar exceção, que vai para o log."""
        with self._lock:
            if self.running:
                return False
            self._reset()
            self.source = source
            self.running = True
            self._cancel.clear()
            self._thread = threading.Thread(
                target=self._run, args=(items_provider, urls, output_dir), daemon=True
            )
            self._thread.start()
            return True

    def cancel(self):
        self._cancel.set()

    def log(self, message):
        with self._lock:
            self.messages.append(message)
        log_message(message)

    def status(self, after=0):
        with self._lock:
            return {
                "source": self.source,
                "running": self.running,
                "finished": self.finished,
                "cancelled": self.cancelled,
                "total": self.total,
                "done": self.done,
                "found": self.found,
                "not_found": self.not_found,
                "messages": self.messages[after:],
                "next_after": len(self.messages),
                "has_files": bool(self.saved_files),
            }

    def saved_files_snapshot(self):
        with self._lock:
            return list(self.saved_files)

    def _run(self, items_provider, urls, output_dir):
        try:
            items = items_provider()
            if not items:
                self.log("Nenhum registro encontrado para processar.")
                return

            with self._lock:
                self.total = len(items)
            self.log(f"{len(items)} registros encontrados. Iniciando processamento...")

            for index, item in enumerate(items, start=1):
                if self._cancel.is_set():
                    with self._lock:
                        self.cancelled = True
                    self.log("Processamento cancelado pelo usuário.")
                    return

                ok, file_path = process_product(
                    item["codprod"], item["descricao"], item["gtin"],
                    urls=urls, output_dir=output_dir, log=self.log,
                )
                with self._lock:
                    self.done = index
                    if ok:
                        self.found += 1
                        self.saved_files.append(file_path)
                    else:
                        self.not_found += 1

                # Pausa para não sobrecarregar os servidores de imagens
                if index % PAUSE_AFTER_REQUESTS == 0 and index < len(items):
                    self.log(f"Pausa de {PAUSE_SECONDS}s após {index} requisições...")
                    for _ in range(PAUSE_SECONDS):
                        if self._cancel.is_set():
                            break
                        time.sleep(1)

            self.log(
                f"Processamento concluído: {self.found} imagens salvas, "
                f"{self.not_found} não encontradas."
            )
        except Exception as e:
            self.log(f"Erro durante o processamento: {e}")
        finally:
            with self._lock:
                self.running = False
                self.finished = True


job_manager = JobManager()
