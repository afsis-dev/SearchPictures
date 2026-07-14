const $ = (id) => document.getElementById(id);

const DEFAULT_URLS = [
  "http://www.eanpictures.com.br:9000/api/gtin/{gtin}",
  "https://cdn-cosmos.bluesoft.com.br/products/{gtin}",
];

let pollTimer = null;
let logAfter = 0;
let defaultQuery = "";

// ---------- Tema claro/escuro ----------
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  $("btn-theme").textContent = theme === "light" ? "☀" : "☾";
  localStorage.setItem("theme", theme);
}

$("btn-theme").addEventListener("click", () => {
  const current = document.documentElement.dataset.theme === "light" ? "light" : "dark";
  applyTheme(current === "light" ? "dark" : "light");
});

applyTheme(localStorage.getItem("theme") === "light" ? "light" : "dark");

// ---------- Abas ----------
function activateTab(tabId) {
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tabId));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === tabId));
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
});

// ---------- Helpers ----------
async function api(path, options = {}) {
  const response = await fetch(path, options);
  let data = {};
  try { data = await response.json(); } catch (_) {}
  if (!response.ok) throw new Error(data.error || `Erro HTTP ${response.status}`);
  return data;
}

function appendLog(lines) {
  if (!lines.length) return;
  const log = $("log");
  log.textContent += lines.map((l) => l + "\n").join("");
  log.scrollTop = log.scrollHeight;
}

function toast(message, type = "info") {
  const container = $("toasts");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);
  requestAnimationFrame(() => el.classList.add("show"));
  setTimeout(() => {
    el.classList.remove("show");
    setTimeout(() => el.remove(), 400);
  }, 4000);
}

// Alerta toast + registro no log + leva o usuário à aba de log
function notify(message, type = "info", goToLog = true) {
  toast(message, type);
  appendLog([message]);
  if (goToLog) activateTab("tab-log");
}

function setBusy(busy) {
  ["btn-test", "btn-winthor", "btn-file", "btn-save", "btn-restore"].forEach((id) => {
    $(id).disabled = busy;
  });
  $("btn-cancel").disabled = !busy;
  const pill = $("status-pill");
  if (busy) {
    pill.textContent = "Executando";
    pill.className = "pill running";
  }
}

function dbPayload() {
  return {
    host: $("db-host").value.trim(),
    port: $("db-port").value.trim(),
    service: $("db-service").value.trim(),
    user: $("db-user").value.trim(),
    password: $("db-password").value,
  };
}

// ---------- Configurações ----------
async function loadSettings() {
  const settings = await api("/api/settings");
  $("api-urls").value = settings.api_urls.join("\n");
  $("output-dir").value = settings.output_dir;
  $("db-host").value = settings.db.host || "";
  $("db-port").value = settings.db.port || "";
  $("db-service").value = settings.db.service || "";
  $("db-user").value = settings.db.user || "";
  $("db-query").value = settings.product_query || "";
  defaultQuery = settings.default_product_query || "";
}

$("btn-save").addEventListener("click", async () => {
  try {
    const urls = $("api-urls").value.split("\n").map((u) => u.trim()).filter(Boolean);
    await api("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_urls: urls, output_dir: $("output-dir").value.trim() }),
    });
    notify("Configurações salvas.", "success");
  } catch (e) {
    notify(`Erro: ${e.message}`, "error");
  }
});

$("btn-restore").addEventListener("click", () => {
  $("api-urls").value = DEFAULT_URLS.join("\n");
  notify("URLs padrão restauradas. Clique em 'Salvar configurações' para aplicar.");
});

// ---------- Conexão e buscas ----------
$("btn-test").addEventListener("click", async () => {
  notify("Testando conexão com o WinThor...");
  try {
    const result = await api("/api/db/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dbPayload()),
    });
    notify(result.message, "success");
  } catch (e) {
    notify(`Erro: ${e.message}`, "error");
  }
});

$("btn-query-restore").addEventListener("click", () => {
  $("db-query").value = defaultQuery;
  notify("Query padrão restaurada.");
});

$("btn-winthor").addEventListener("click", async () => {
  try {
    const result = await api("/api/search/winthor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...dbPayload(), query: $("db-query").value }),
    });
    notify(result.message, "success");
    startPolling();
  } catch (e) {
    notify(`Erro: ${e.message}`, "error");
  }
});

$("btn-file").addEventListener("click", async () => {
  const input = $("file-input");
  if (!input.files.length) {
    notify("Selecione um arquivo XLS ou XLSX antes de processar.", "error");
    return;
  }
  const formData = new FormData();
  formData.append("file", input.files[0]);
  try {
    const result = await api("/api/search/file", { method: "POST", body: formData });
    notify(result.message, "success");
    startPolling();
  } catch (e) {
    notify(`Erro: ${e.message}`, "error");
  }
});

$("btn-cancel").addEventListener("click", async () => {
  try {
    await api("/api/job/cancel", { method: "POST" });
    notify("Cancelamento solicitado.");
  } catch (e) {
    notify(`Erro: ${e.message}`, "error");
  }
});

$("btn-zip").addEventListener("click", () => {
  notify("Download do .zip iniciado.", "success");
  window.location.href = "/api/download/zip";
});

// ---------- Progresso ----------
function renderStatus(status) {
  const percent = status.total ? Math.round((status.done / status.total) * 100) : 0;
  $("progress-bar").style.width = `${percent}%`;
  if (status.total) {
    $("progress-info").textContent =
      `${status.done}/${status.total} processados — ` +
      `${status.found} imagens salvas, ${status.not_found} não encontradas (${percent}%)`;
  }
  appendLog(status.messages);
  logAfter = status.next_after;
  $("btn-zip").disabled = !status.has_files;

  const pill = $("status-pill");
  if (!status.running && status.finished) {
    pill.textContent = status.cancelled ? "Cancelado" : "Concluído";
    pill.className = "pill done";
  }
}

function startPolling() {
  setBusy(true);
  activateTab("tab-log");
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const status = await api(`/api/job/status?after=${logAfter}`);
      renderStatus(status);
      if (!status.running) {
        clearInterval(pollTimer);
        pollTimer = null;
        setBusy(false);
        renderStatus(await api(`/api/job/status?after=${logAfter}`));
      }
    } catch (e) {
      appendLog([`Erro ao consultar status: ${e.message}`]);
      clearInterval(pollTimer);
      pollTimer = null;
      setBusy(false);
    }
  }, 1000);
}

// ---------- Inicialização ----------
(async function init() {
  try {
    await loadSettings();
    appendLog(["Interface iniciada em modo offline. Configure a conexão ou envie um arquivo."]);
    const status = await api("/api/job/status");
    if (status.running) {
      logAfter = 0;
      startPolling();
    }
  } catch (e) {
    appendLog([`Erro ao carregar configurações: ${e.message}`]);
  }
})();
