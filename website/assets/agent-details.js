/* Agent details: published scores and separately sourced efficiency/trace data. */
(() => {
  "use strict";
  const element = id => document.getElementById(id);
  const escape = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const dialog = element("agent-dialog");
  const names = {rca: "Root Cause Analysis", path: "Path Restoration"};
  let paper, details, detailStatus = "loading", selected = 0, track = "rca", opener;

  function metricText(value, decimals = 1) {
    return Number.isFinite(value) ? value.toLocaleString("en-US", {maximumFractionDigits: decimals}) : "Not reported";
  }

  function renderScores(agent) {
    const count = paper.tasks[track];
    element("detail-score-context").textContent = `${names[track]} · ${count} tasks · Reported mean ± standard deviation (%)`;
    element("detail-score-source").href = paper.url;
    const metrics = [["accuracy", "Accuracy"], ["localization", "Localization IoU"],
      ["reasoning", track === "rca" ? "Identification IoU" : "Restoration IoU"], ["evidence", "Evidence F1"]];
    element("detail-score-cards").innerHTML = metrics.map(([key, label]) => {
      const metric = agent[track][key];
      const mean = Number.isFinite(metric?.mean) ? metric.mean.toFixed(2) : "—";
      const sd = Number.isFinite(metric?.sd) ? `± ${metric.sd.toFixed(1)}` : "";
      return `<article class="detail-score-card"><span>${label}</span><strong>${mean}<small>%</small></strong><div>${sd}</div></article>`;
    }).join("");
  }

  function renderEfficiency(entry) {
    const data = entry?.efficiency?.[track] || {};
    const source = details?.efficiencySource;
    element("detail-efficiency-label").textContent = source?.label || "Measurements pending";
    element("detail-efficiency-note").textContent = source?.note || (detailStatus === "loading"
      ? "Loading measurement availability…"
      : "Verified efficiency measurements are not available for this view. Paper capability scores remain available above.");
    const definitions = [];
    element("detail-efficiency-cards").innerHTML = [["rounds", "Interaction rounds"], ["latency", "Latency"], ["tokens", "Tokens"]].map(([key, label]) => {
      const metric = data[key];
      const displayLabel = metric?.label || label;
      const available = metric?.status === "available" && Number.isFinite(metric.value);
      const total = metric?.total ?? paper.tasks[track];
      const observed = metric?.observed ?? 0;
      const unit = metric?.unit || (key === "latency" ? "s / task" : key === "tokens" ? "tokens / task" : "rounds / task");
      const coverage = available ? `${observed} / ${total} tasks measured` : "Awaiting verified measurements";
      const explanation = metric?.definition || metric?.reason || "A verified, consistently defined measurement is required.";
      definitions.push(`<p><strong>${escape(displayLabel)}</strong>${escape(explanation)}${metric?.reason ? `<br>${escape(metric.reason)}` : ""}</p>`);
      return `<article class="efficiency-card ${available ? "" : "metric-unavailable"}"><span>${escape(displayLabel)}</span><strong>${available ? metricText(metric.value) : "—"}</strong><div>${available ? `Mean ${escape(unit)}` : "Not reported"}</div><small>${coverage}</small></article>`;
    }).join("");
    element("detail-efficiency-definitions").innerHTML = definitions.join("");
  }

  function renderExample(agent, entry) {
    const example = entry?.examples?.[track] || details?.examples?.[track];
    const content = element("detail-example-content");
    if (!example) {
      element("detail-example-kind").textContent = "Example pending";
      content.innerHTML = `<div class="detail-empty"><strong>${detailStatus === "loading" ? "Loading the walkthrough…" : "An approved example will appear here."}</strong><p>A public question and its observable tool trace can be added for this agent and task.</p></div>`;
      return;
    }
    const synthetic = example.kind === "synthetic";
    element("detail-example-kind").textContent = synthetic ? "Synthetic walkthrough" : "Recorded example";
    const notice = synthetic
      ? `This is a shared synthetic example of the task workflow, not a recorded run by ${agent.harness} + ${agent.model}. It contains no benchmark question or private trace.`
      : example.sourceNote;
    const stages = example.steps.map((step, index) => `<li><details class="trace-step" ${index === 0 ? "open" : ""}><summary><span class="trace-number">${String(index + 1).padStart(2, "0")}</span><span class="trace-step-title">${escape(step.title)}</span><span class="trace-chevron" aria-hidden="true">+</span></summary><div class="trace-step-body"><div class="trace-command"><span>TOOL / COMMAND</span><pre><code>${escape(step.command)}</code></pre></div><div class="trace-observation"><span>OBSERVATION</span><pre>${escape(step.observation)}</pre></div><p class="trace-action-summary"><strong>Action summary</strong>${escape(step.summary)}</p></div></details></li>`).join("");
    content.innerHTML = `<p class="example-provenance ${synthetic ? "synthetic-notice" : ""}">${escape(notice)}</p><div class="example-question"><span class="detail-kicker">${escape(example.id)} · QUESTION</span><h4>${escape(example.title)}</h4><p>${escape(example.question)}</p></div><div class="trace-toolbar"><span>${example.steps.length} diagnostic steps</span><div><button type="button" data-trace-expand="true">Expand all</button><button type="button" data-trace-expand="false">Collapse all</button></div></div><ol class="trace-list">${stages}</ol><div class="trace-answer"><span class="detail-kicker">FINAL ANSWER</span><p>${escape(example.finalAnswer)}</p></div>`;
  }

  function render() {
    if (!paper) return;
    const agent = paper.results[selected];
    if (!agent) return;
    element("agent-detail-title").textContent = agent.model;
    element("agent-detail-subtitle").textContent = `${agent.harness} · ${names[track]}`;
    element("agent-detail-select").value = String(selected);
    dialog.querySelectorAll("[data-detail-track]").forEach(button => {
      const active = button.dataset.detailTrack === track;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    const entry = details?.agents?.find(item => item.harness === agent.harness && item.model === agent.model);
    renderScores(agent);
    renderEfficiency(entry);
    renderExample(agent, entry);
  }

  function open(button) {
    const index = Number(button.dataset.agentIndex);
    if (!Number.isInteger(index) || !paper?.results[index]) return;
    selected = index;
    track = button.dataset.agentTrack === "path" ? "path" : "rca";
    opener = button;
    render();
    dialog.showModal();
    dialog.querySelector(".agent-dialog-body").scrollTop = 0;
    document.body.classList.add("agent-dialog-open");
    element("close-agent-detail").focus({preventScroll: true});
  }

  async function init(results) {
    paper = results;
    element("agent-detail-select").innerHTML = paper.results.map((agent, index) => `<option value="${index}">${escape(agent.harness)} + ${escape(agent.model)}</option>`).join("");
    element("leaderboard-body").addEventListener("click", event => {
      const button = event.target.closest("[data-agent-index]");
      if (button) open(button);
    });
    element("close-agent-detail").addEventListener("click", () => dialog.close());
    dialog.addEventListener("close", () => {
      document.body.classList.remove("agent-dialog-open");
      if (opener?.isConnected) opener.focus({preventScroll: true});
    });
    dialog.addEventListener("click", event => {
      if (event.target === dialog) {
        const bounds = dialog.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
      }
      const expand = event.target.closest("[data-trace-expand]");
      if (expand) dialog.querySelectorAll(".trace-step").forEach(step => { step.open = expand.dataset.traceExpand === "true"; });
    });
    element("agent-detail-select").addEventListener("change", event => { selected = Number(event.target.value); render(); });
    dialog.querySelectorAll("[data-detail-track]").forEach(button => button.addEventListener("click", () => {
      track = button.dataset.detailTrack;
      render();
    }));
    try {
      const response = await fetch("data/agent-details.json");
      if (!response.ok) throw new Error("Agent details unavailable");
      details = await response.json();
      detailStatus = "ready";
    } catch {
      detailStatus = "unavailable";
    }
    if (dialog.open) render();
  }
  window.CTBenchAgentDetails = {init};
})();
