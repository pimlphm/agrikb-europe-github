const API_BASE =
  window.KNOWLEDGE_RAG_API ||
  (location.protocol.startsWith("http") ? "" : "http://127.0.0.1:8020");

const TOULOUSE = {
  productionLocation: "Toulouse, Occitanie, France",
  marketLocation: "Toulouse MIN Occitanie wholesale market",
  weatherLocation: "Toulouse, Occitanie, France",
  productionLat: 43.6047,
  productionLon: 1.4442,
  marketLat: 43.5969,
  marketLon: 1.4394,
};

const PROMPTS = {
  today:
    "For a cooperative near Toulouse, prepare today's farm-service checklist: weather risk, harvest timing, market channel, CAP or regional support notes, and records that should be saved.",
  cap:
    "For a Toulouse / Occitanie farm or cooperative, explain which CAP, regional advisory or public-service checks should be reviewed before applying for agricultural support. Give a practical document checklist.",
  weather:
    "For farms around Toulouse today, assess weather-sensitive agriculture risks for vegetables, vineyards, sunflower and maize. Include harvest, irrigation, disease and transport actions.",
  market:
    "For a Toulouse producer selling through local cooperative or wholesale channels, compare direct sale, cooperative sale and wholesale market routes. Include price-check, logistics and traceability actions.",
  trace:
    "Design a traceability workflow for a Toulouse market-vegetable batch: field record, harvest record, cold-chain note, quality check, buyer record and public-service review log.",
};

const healthStatus = document.querySelector("#healthStatus");
const queryInput = document.querySelector("#queryInput");
const askButton = document.querySelector("#askButton");
const clearButton = document.querySelector("#clearButton");
const answerOutput = document.querySelector("#answerOutput");
const answerMeta = document.querySelector("#answerMeta");
const webSearchToggle = document.querySelector("#webSearchToggle");
const refreshLiveButton = document.querySelector("#refreshLiveButton");
const liveContextOutput = document.querySelector("#liveContextOutput");
const weatherLocationInput = document.querySelector("#weatherLocationInput");
const productionLocationInput = document.querySelector("#productionLocationInput");
const marketLocationInput = document.querySelector("#marketLocationInput");
const marketButton = document.querySelector("#marketButton");
const productSelect = document.querySelector("#productSelect");
const marketOutput = document.querySelector("#marketOutput");
const knowledgeOutput = document.querySelector("#knowledgeOutput");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function compact(value, fallback = "") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : fallback;
  return String(value);
}

function endpoint(path) {
  return `${API_BASE}${path}`;
}

async function fetchJson(path, options = {}) {
  const response = await fetch(endpoint(path), {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `${response.status} ${response.statusText}`);
  }
  return response.json();
}

function regionParams(extra = {}) {
  const params = new URLSearchParams({
    production_location: productionLocationInput.value || TOULOUSE.productionLocation,
    market_location: marketLocationInput.value || TOULOUSE.marketLocation,
    weather_location: weatherLocationInput.value || TOULOUSE.weatherLocation,
    production_lat: String(TOULOUSE.productionLat),
    production_lon: String(TOULOUSE.productionLon),
    market_lat: String(TOULOUSE.marketLat),
    market_lon: String(TOULOUSE.marketLon),
    weather_lat: String(TOULOUSE.productionLat),
    weather_lon: String(TOULOUSE.productionLon),
    ...extra,
  });
  return params.toString();
}

function setStatus(ok, text) {
  healthStatus.textContent = text;
  healthStatus.classList.toggle("ok", Boolean(ok));
  healthStatus.classList.toggle("bad", ok === false);
}

function firstDefined(...values) {
  return values.find((item) => item !== undefined && item !== null && item !== "");
}

function renderObjectSummary(data, keys) {
  const rows = keys
    .map(([label, getter]) => {
      const value = typeof getter === "function" ? getter(data) : data?.[getter];
      return value ? `<span class="pill">${escapeHtml(label)}: ${escapeHtml(compact(value))}</span>` : "";
    })
    .filter(Boolean)
    .join("");
  return rows ? `<div class="pill-row">${rows}</div>` : "";
}

function renderLiveContext(data) {
  const weather = firstDefined(data?.production_weather, data?.weather, data?.weather_summary, {});
  const route = data?.route || {};
  const market = firstDefined(data?.market_location, data?.market, {});
  const production = firstDefined(data?.production_location, data?.region, {});
  const news = data?.headlines || data?.news || data?.items || [];
  const newsRows = Array.isArray(news)
    ? news.slice(0, 5).map((item) => `<li>${escapeHtml(compact(item.title || item.name || item.snippet || item))}</li>`).join("")
    : "";

  liveContextOutput.innerHTML = `
    <h3>Toulouse live context</h3>
    ${renderObjectSummary({ weather, route, market, production }, [
      ["weather", (x) => x.weather?.summary || x.weather?.current_weather || x.weather?.short_summary],
      ["temperature", (x) => x.weather?.temperature || x.weather?.temperature_2m || x.weather?.current_temperature],
      ["distance", (x) => x.route?.distance_km ? `${x.route.distance_km} km` : ""],
      ["market", (x) => x.market?.short_name || x.market?.name || marketLocationInput.value],
      ["production", (x) => x.production?.short_name || x.production?.name || productionLocationInput.value],
    ])}
    ${newsRows ? `<ul>${newsRows}</ul>` : `<p class="muted">No live headlines returned yet. The backend may still be starting or web search may be unavailable.</p>`}
    <details><summary>Raw context</summary><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></details>
  `;
}

function renderMarket(data) {
  const rows = data?.rows || data?.prices || data?.items || data?.results || [];
  const decision = data?.decision || data?.summary || data?.insight || "";
  const tableRows = Array.isArray(rows)
    ? rows.slice(0, 8).map((row) => {
        const product = compact(row.product || row.name || row.item || productSelect.value);
        const market = compact(row.market || row.market_name || row.source || "market source");
        const price = compact(row.price || row.value || row.price_text || row.latest_price, "not returned");
        const date = compact(row.date || row.time || row.updated_at, "");
        return `<tr><td>${escapeHtml(product)}</td><td>${escapeHtml(market)}</td><td>${escapeHtml(price)}</td><td>${escapeHtml(date)}</td></tr>`;
      }).join("")
    : "";
  marketOutput.innerHTML = `
    <h3>${escapeHtml(productSelect.value)} market check</h3>
    ${decision ? `<p>${escapeHtml(decision)}</p>` : `<p class="muted">The backend returned the market payload below.</p>`}
    ${tableRows ? `<table><thead><tr><th>Product</th><th>Market</th><th>Price</th><th>Date</th></tr></thead><tbody>${tableRows}</tbody></table>` : ""}
    <details><summary>Raw market payload</summary><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></details>
  `;
}

function extractAnswer(data) {
  return (
    data?.answer ||
    data?.result ||
    data?.content ||
    data?.message ||
    data?.text ||
    "The backend returned a response without a plain answer field. See the raw payload below."
  );
}

function renderAnswer(data) {
  const answer = extractAnswer(data);
  const evidence = data?.evidence || data?.retrieved || data?.sources || data?.chunks || [];
  const evidenceRows = Array.isArray(evidence)
    ? evidence.slice(0, 5).map((item) => `<li>${escapeHtml(compact(item.title || item.source || item.name || item.text || item))}</li>`).join("")
    : "";
  const regional = data?.regional_intelligence
    ? `<details open><summary>Toulouse regional context</summary><pre>${escapeHtml(JSON.stringify(data.regional_intelligence, null, 2))}</pre></details>`
    : "";
  answerOutput.innerHTML = `
    <div>${escapeHtml(answer)}</div>
    ${evidenceRows ? `<h3>Evidence</h3><ul>${evidenceRows}</ul>` : ""}
    ${regional}
    <details><summary>Raw response</summary><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></details>
  `;
}

async function checkHealth() {
  try {
    const data = await fetchJson("/health");
    setStatus(true, `Backend ready: ${data.active_provider || data.backend || "AgriKB"}`);
  } catch (error) {
    setStatus(false, "Backend not ready");
  }
}

async function refreshLiveContext() {
  liveContextOutput.textContent = "Loading Toulouse context...";
  try {
    const query =
      "Toulouse Occitanie agriculture weather market CAP cooperative traceability vineyard sunflower vegetables";
    const data = await fetchJson(`/api/regional/live?${regionParams({ query })}`);
    renderLiveContext(data);
  } catch (error) {
    liveContextOutput.innerHTML = `<span class="error">Live context failed: ${escapeHtml(error.message)}</span>`;
  }
}

async function checkMarket() {
  marketOutput.textContent = "Checking market signal...";
  try {
    const params = new URLSearchParams({
      product: productSelect.value,
      category: "produce",
      production_location: productionLocationInput.value || TOULOUSE.productionLocation,
      market_location: marketLocationInput.value || TOULOUSE.marketLocation,
      include_ai: "false",
    });
    const data = await fetchJson(`/api/market/prices?${params.toString()}`);
    renderMarket(data);
  } catch (error) {
    marketOutput.innerHTML = `<span class="error">Market check failed: ${escapeHtml(error.message)}</span>`;
  }
}

async function loadKnowledgeStatus() {
  try {
    const data = await fetchJson("/api/knowledge/tree?limit=80");
    const docs = data?.document_count || data?.documents || data?.count || 0;
    const chunks = data?.chunk_count || data?.chunks || 0;
    knowledgeOutput.innerHTML = `
      <h3>Knowledge base loaded</h3>
      <p>${escapeHtml(compact(docs, "available"))} documents / ${escapeHtml(compact(chunks, "indexed"))} chunks.</p>
      <p class="muted">The Toulouse GUI uses the original AgriKB backend and knowledge store, with European/Toulouse prompts layered on top.</p>
    `;
  } catch (error) {
    knowledgeOutput.innerHTML = `<span class="error">Knowledge status failed: ${escapeHtml(error.message)}</span>`;
  }
}

async function askAgriKB() {
  const query = queryInput.value.trim();
  if (!query) return;
  askButton.disabled = true;
  answerMeta.textContent = "Running query...";
  answerOutput.textContent = "AgriKB is retrieving evidence and regional context...";
  try {
    const payload = {
      query,
      module_context: "AgriKB Europe Toulouse GUI: Occitanie regional smart-agriculture pilot.",
      top_k: 6,
      use_llm: true,
      web_search: webSearchToggle.checked,
      web_search_k: 5,
      regional_intelligence: true,
      production_location: productionLocationInput.value || TOULOUSE.productionLocation,
      market_location: marketLocationInput.value || TOULOUSE.marketLocation,
      production_lat: TOULOUSE.productionLat,
      production_lon: TOULOUSE.productionLon,
      market_lat: TOULOUSE.marketLat,
      market_lon: TOULOUSE.marketLon,
      answer_language: "en",
    };
    const data = await fetchJson("/api/query", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderAnswer(data);
    answerMeta.textContent = `Answered at ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    answerOutput.innerHTML = `<span class="error">Query failed: ${escapeHtml(error.message)}</span>`;
    answerMeta.textContent = "Query failed.";
  } finally {
    askButton.disabled = false;
  }
}

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = PROMPTS[button.dataset.prompt] || PROMPTS.today;
    askAgriKB();
  });
});

askButton.addEventListener("click", askAgriKB);
clearButton.addEventListener("click", () => {
  answerOutput.textContent = "Choose a quick module or ask your own Toulouse agriculture question.";
  answerMeta.textContent = "Waiting for a query.";
});
refreshLiveButton.addEventListener("click", refreshLiveContext);
marketButton.addEventListener("click", checkMarket);

checkHealth();
refreshLiveContext();
checkMarket();
loadKnowledgeStatus();
window.setInterval(checkHealth, 15000);
