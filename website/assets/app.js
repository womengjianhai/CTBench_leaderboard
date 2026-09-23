"use strict";
const state = { track: "rca", sort: "accuracy", direction: "desc", harness: "all", query: "", data: null };
const byId = id => document.getElementById(id);
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));

async function readJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Unable to load ${url} (${response.status}).`);
  return response.json();
}

function scoreCell(metric, primary = false) {
  if (!metric || !Number.isFinite(metric.mean)) return '<td aria-label="Not reported">—</td>';
  const uncertainty = Number.isFinite(metric.sd) ? `<span class="score-uncertainty"> ± ${metric.sd.toFixed(1)}</span>` : "";
  return `<td><span class="${primary ? "score-main" : ""}">${metric.mean.toFixed(2)}${uncertainty}</span>${primary ? `<div class="score-bar" aria-hidden="true"><i style="width:${Math.max(0, Math.min(100, metric.mean))}%"></i></div>` : ""}</td>`;
}

function renderLeaderboard() {
  if (!state.data) return;
  const source = state.data;
  const all = [...source.results].sort((a, b) => {
    const left = a[state.track][state.sort]?.mean ?? -Infinity;
    const right = b[state.track][state.sort]?.mean ?? -Infinity;
    return (state.direction === "desc" ? right - left : left - right) || a.model.localeCompare(b.model);
  });
  let previous = null, rank = 0;
  const ranked = all.map((item, index) => {
    const score = item[state.track][state.sort]?.mean;
    if (score !== previous || index === 0) rank = index + 1;
    previous = score;
    return { item, rank };
  });
  const visible = ranked.filter(({item}) => (state.harness === "all" || item.harness === state.harness) && `${item.model} ${item.harness}`.toLowerCase().includes(state.query));
  byId("leaderboard-body").innerHTML = visible.length ? visible.map(({item, rank}) => {
    const scores = item[state.track];
    return `<tr><td><span class="rank-chip ${rank === 1 ? "rank-first" : ""}">${rank.toString().padStart(2, "0")}</span></td><td><span class="model-name">${escapeHtml(item.model)}</span><span class="harness-name">${escapeHtml(item.harness)}</span></td>${scoreCell(scores.accuracy, true)}${scoreCell(scores.localization)}${scoreCell(scores.reasoning)}${scoreCell(scores.evidence)}</tr>`;
  }).join("") : '<tr><td colspan="6" class="empty-state">No matching agent–model combinations. Try another search or harness.</td></tr>';
  const count = state.track === "rca" ? source.tasks.rca : source.tasks.path;
  byId("result-count").textContent = `${visible.length} of ${source.results.length} combinations · ${count} tasks · Scores in %`;
  byId("reasoning-heading").textContent = state.track === "rca" ? "Identification" : "Restoration";
  byId("source-label").textContent = source.label;
  byId("source-note").textContent = source.note;
  byId("source-link").href = source.url;
  document.querySelectorAll("[data-sort-header]").forEach(header => {
    if (header.dataset.sortHeader === state.sort) header.setAttribute("aria-sort", state.direction === "desc" ? "descending" : "ascending");
    else header.removeAttribute("aria-sort");
    header.querySelector("button > span:last-child").textContent = header.dataset.sortHeader === state.sort ? (state.direction === "desc" ? "↓" : "↑") : "↕";
  });
}

document.querySelectorAll("[data-track]").forEach(button => button.addEventListener("click", () => {
  state.track = button.dataset.track;
  document.querySelectorAll("[data-track]").forEach(tab => { tab.classList.toggle("active", tab === button); tab.setAttribute("aria-pressed", String(tab === button)); });
  renderLeaderboard();
}));
document.querySelectorAll("[data-sort]").forEach(button => button.addEventListener("click", () => {
  state.direction = state.sort === button.dataset.sort && state.direction === "desc" ? "asc" : "desc";
  state.sort = button.dataset.sort;
  renderLeaderboard();
}));
byId("harness-filter").addEventListener("change", event => { state.harness = event.target.value; renderLeaderboard(); });
byId("model-search").addEventListener("input", event => { state.query = event.target.value.trim().toLowerCase(); renderLeaderboard(); });

const menuButton = document.querySelector(".menu-toggle");
const navigation = byId("navigation");
function closeMenu() { menuButton.setAttribute("aria-expanded", "false"); menuButton.setAttribute("aria-label", "Open navigation"); navigation.classList.remove("open"); }
menuButton.addEventListener("click", () => { const open = menuButton.getAttribute("aria-expanded") !== "true"; menuButton.setAttribute("aria-expanded", String(open)); menuButton.setAttribute("aria-label", open ? "Close navigation" : "Open navigation"); navigation.classList.toggle("open", open); });
navigation.querySelectorAll("a").forEach(link => link.addEventListener("click", closeMenu));
document.addEventListener("keydown", event => { if (event.key === "Escape") closeMenu(); });

byId("copy-citation").addEventListener("click", async () => {
  const text = byId("citation-text").textContent;
  if (!text.startsWith("@")) return;
  try {
    await navigator.clipboard.writeText(text);
    byId("copy-feedback").textContent = "Citation copied";
  } catch {
    const range = document.createRange(); range.selectNodeContents(byId("citation-text"));
    const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
    byId("copy-feedback").textContent = "Text selected — press Ctrl/Cmd+C";
  }
});

async function initialize() {
  const [results, config, citationResponse] = await Promise.allSettled([readJson("data/leaderboard.json"), readJson("site-config.json"), fetch("citation.bib")]);
  if (results.status === "fulfilled") {
    state.data = results.value;
    const harnesses = [...new Set(state.data.results.map(row => row.harness))].sort();
    byId("harness-filter").innerHTML = '<option value="all">All harnesses</option>' + harnesses.map(harness => `<option>${escapeHtml(harness)}</option>`).join("");
    renderLeaderboard();
  } else {
    byId("leaderboard-body").innerHTML = '<tr><td colspan="6" class="empty-state">Results could not be loaded. Reload the page or use Download CSV.</td></tr>';
    byId("result-count").textContent = "Results unavailable";
  }
  if (config.status === "fulfilled") {
    const settings = config.value;
    byId("authors").textContent = settings.authors.join(", ");
    if (settings.repositoryAvailable && /^https:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/.test(settings.repositoryUrl)) {
      byId("code-resource").href = settings.repositoryUrl;
      byId("footer-github").href = settings.repositoryUrl;
      byId("code-location").textContent = "GitHub · " + settings.repository;
      byId("code-resource").querySelector("h3").textContent = "Project on GitHub";
      byId("code-description").textContent = "Explore the CTBench repository, documentation and release updates.";
    }
  }
  if (citationResponse.status === "fulfilled" && citationResponse.value.ok) byId("citation-text").textContent = (await citationResponse.value.text()).trim();
  else { byId("citation-text").textContent = "Citation unavailable. Follow the paper link for bibliographic details."; byId("copy-citation").disabled = true; }
}
initialize();
