/* Grid Color War - browser client.
 *
 * Draws what the server says and sends clicks back. All the rules live on the
 * server (core/). The one thing computed here is the hover preview (which cells
 * the card would paint), purely cosmetic.
 *
 * The settings form of the home page is built from GET /api/settings, so a new
 * parameter, rule or rule option appears here without any change in this file.
 */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "gridColorWar.gameId";

  // ---------------------------------------------------------------- API
  async function request(method, url, body) {
    const response = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      let detail = response.statusText;
      try { detail = (await response.json()).detail || detail; } catch (_) { /* no json body */ }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return response.status === 204 ? null : response.json();
  }
  const api = {
    settings: () => request("GET", "/api/settings"),
    createGame: (config) => request("POST", "/api/games", { config }),
    getGame: (id) => request("GET", `/api/games/${id}`),
    play: (id, row, col) => request("POST", `/api/games/${id}/moves`, { row, col }),
    deleteGame: (id) => request("DELETE", `/api/games/${id}`),
  };

  // ---------------------------------------------------------------- state
  let state = null;       // last game state sent by the server
  let schema = null;      // settings schema (parameters, rules, defaults)
  let lastConfig = null;  // settings of the current game: Replay reuses them
  let hovered = null;     // [row, col] under the mouse
  let busy = false;       // a request is in flight

  const remember = (id) => {
    try { id ? sessionStorage.setItem(STORAGE_KEY, id) : sessionStorage.removeItem(STORAGE_KEY); }
    catch (_) { /* storage not available: a reload just returns to the home page */ }
  };
  const remembered = () => { try { return sessionStorage.getItem(STORAGE_KEY); } catch (_) { return null; } };

  const colorOf = (name) => (state.players.find((p) => p.name === name) || {}).color || "#888";
  const rgba = (hex, alpha) => {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
  };
  const el = (tag, props = {}, ...children) => {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...children);
    return node;
  };

  // ---------------------------------------------------------------- screens
  function showScreen(name) {
    $("home").classList.toggle("hidden", name !== "home");
    $("match").classList.toggle("hidden", name !== "match");
    if (name === "home") $("play-btn").focus({ preventScroll: true });  // do not scroll past the title
  }

  let errorTimer = null;
  function showError(message) {
    const box = $("error");
    box.textContent = message;
    box.classList.remove("hidden");
    clearTimeout(errorTimer);
    errorTimer = setTimeout(() => box.classList.add("hidden"), 3500);
  }

  // ---------------------------------------------------------------- settings form (home page)
  function numberInput(id, min, max, step, value) {
    return el("input", { id, type: "number", min, max, step, value });
  }

  function buildSettingsForm() {
    const params = $("params");
    params.replaceChildren(...schema.parameters.map((p) => {
      const id = `param-${p.key}`;
      const input = p.kind === "bool"
        ? el("input", { id, type: "checkbox" })
        : numberInput(id, p.min, p.max, p.step, "");
      input.dataset.param = p.key;
      return el("div", { className: "row" }, el("label", { htmlFor: id, textContent: p.label }), input);
    }));

    $("rules-list").replaceChildren(...schema.rules.map((rule) => {
      const box = el("input", { id: `rule-${rule.name}`, type: "checkbox" });
      box.dataset.rule = rule.name;
      const options = el("div", { className: "options" }, ...rule.option_specs.map((spec) => {
        const id = `option-${rule.name}-${spec.key}`;
        const input = spec.kind === "choice"
          ? el("select", { id }, ...spec.choices.map((c) => el("option", { value: c, textContent: c })))
          : numberInput(id, spec.min ?? "", spec.max ?? "", 1, "");
        input.dataset.rule = rule.name;
        input.dataset.option = spec.key;
        return el("div", { className: "row" }, el("label", { htmlFor: id, textContent: spec.label }), input);
      }));
      box.addEventListener("change", () => updateRuleLook(rule.name));
      return el("div", { className: "rule", id: `rulebox-${rule.name}` },
        el("div", { className: "row" },
          el("label", { htmlFor: box.id, className: "name", textContent: rule.name }), box),
        el("div", { className: "desc", textContent: rule.description }),
        rule.option_specs.length ? options : "");
    }));
    applyConfigToForm(schema.defaults);
  }

  function updateRuleLook(name) {
    $(`rulebox-${name}`).classList.toggle("off", !$(`rule-${name}`).checked);
  }

  function applyConfigToForm(config) {
    for (const input of document.querySelectorAll("[data-param]")) {
      const value = config[input.dataset.param];
      if (input.type === "checkbox") input.checked = !!value; else input.value = value;
    }
    const enabled = new Set(config.rules.enabled);
    for (const rule of schema.rules) {
      $(`rule-${rule.name}`).checked = enabled.has(rule.name);
      updateRuleLook(rule.name);
    }
    for (const input of document.querySelectorAll("[data-option]")) {
      const values = config.rules.options[input.dataset.rule] || {};
      if (input.dataset.option in values) input.value = values[input.dataset.option];
    }
  }

  function collectConfig() {
    const config = { rules: { enabled: [], options: {} } };
    for (const input of document.querySelectorAll("[data-param]")) {
      config[input.dataset.param] = input.type === "checkbox" ? input.checked : Number(input.value);
    }
    for (const input of document.querySelectorAll("input[data-rule][type=checkbox]")) {
      if (input.checked) config.rules.enabled.push(input.dataset.rule);
    }
    for (const input of document.querySelectorAll("[data-option]")) {
      const rule = input.dataset.rule;
      (config.rules.options[rule] = config.rules.options[rule] || {})[input.dataset.option] =
        input.tagName === "SELECT" ? input.value : Number(input.value);
    }
    return config;
  }

  function showConfigError(message) {
    const box = $("config-error");
    box.textContent = message || "";
    box.classList.toggle("hidden", !message);
  }

  // ---------------------------------------------------------------- flow
  async function startMatch(config) {
    showConfigError("");
    try {
      state = await api.createGame(config);
    } catch (error) {
      if (!$("home").classList.contains("hidden")) showConfigError(error.message);
      else showError(`Could not start a game: ${error.message}`);
      return;
    }
    lastConfig = config;
    remember(state.id);
    hovered = null;
    showScreen("match");
    render();
  }

  function goHome() {
    if (state) api.deleteGame(state.id).catch(() => {});  // best effort
    state = null;
    remember(null);
    showScreen("home");
  }

  async function playCell(row, col) {
    if (!state || state.is_over || busy) return;
    busy = true;
    try {
      state = await api.play(state.id, row, col);
    } catch (error) {
      showError(error.message);
    } finally {
      busy = false;
    }
    render();
  }

  // ---------------------------------------------------------------- rendering
  function render() {
    if (!state) return;
    renderScores();
    renderBoard();
    renderMessage();
    renderCards();
    renderGameOver();
    $("rules").textContent = "Rules: " + (state.rules.length ? state.rules.join(", ") : "none (plain game)");
    updatePreview();
  }

  function renderScores() {
    $("turns").textContent = `${state.turns_left} / ${state.total_turns}`;
    $("scores").replaceChildren(...state.players.map((player) => {
      const box = el("div", { className: "score", id: `score-${player.name}` },
        el("span", { className: "name", textContent: player.name }),
        el("span", { className: "value", textContent: state.scores[player.name] }),
        el("span", { className: "unit", textContent: "cells" }));
      box.style.setProperty("--c", player.color);
      box.classList.toggle("active", !state.is_over && state.current_player === player.name);
      return box;
    }));
  }

  function renderBoard() {
    const board = $("board");
    board.style.setProperty("--size", state.size);
    board.style.setProperty("--pc", rgba(colorOf(state.current_player), 0.65));
    board.classList.toggle("over", state.is_over);
    board.replaceChildren();
    state.grid.forEach((cells, row) => {
      cells.forEach((owner, col) => {
        const cell = el("button", { type: "button", className: "cell" });
        cell.dataset.row = row;
        cell.dataset.col = col;
        if (owner) { cell.style.background = colorOf(owner); cell.dataset.owner = owner; }
        cell.setAttribute("aria-label", `Row ${row + 1}, column ${col + 1}, ${owner ? owner.toLowerCase() : "empty"}`);
        board.appendChild(cell);
      });
    });
  }

  function renderMessage() {
    $("message").replaceChildren(...state.message.map((line) => el("p", { textContent: line })));
  }

  function cardElement(card, color, sizeClass) {
    const element = el("div", { className: `card ${sizeClass}${color ? "" : " neutral"}` });
    element.style.gridTemplateColumns = `repeat(${card.size}, 1fr)`;
    const radius = Math.floor(card.size / 2);
    const colored = new Set(card.offsets.map(([r, c]) => `${r},${c}`));
    for (let r = -radius; r <= radius; r++) {
      for (let c = -radius; c <= radius; c++) {
        const cell = el("div", { className: "cell-c" });
        if (colored.has(`${r},${c}`)) { cell.classList.add("on"); if (color) cell.style.background = color; }
        if (r === 0 && c === 0) cell.classList.add("center");
        element.appendChild(cell);
      }
    }
    return element;
  }

  function renderCards() {
    const playing = !state.is_over;
    $("cards-block").classList.toggle("hidden", !playing);
    $("actions").classList.toggle("hidden", playing);
    if (!playing) return;

    const player = state.current_player;
    const title = $("current-title");
    title.textContent = `${player}'s card`;
    title.style.color = colorOf(player);
    $("current-card").replaceWith(Object.assign(
      cardElement(state.current_card, colorOf(player), "big"), { id: "current-card" }));
    $("card-note").textContent = state.current_card.note || "";

    $("next-block").classList.toggle("hidden", state.upcoming_cards.length === 0);
    $("next-cards").replaceChildren(...state.upcoming_cards.map((card) => cardElement(card, null, "small")));

    const streak = $("streak");
    const limit = state.line_streak_limit;
    if (limit === null) {
      streak.textContent = "";
      streak.classList.remove("danger");
    } else {
      const danger = state.line_streak > 0 && state.line_streak >= limit - 1;
      streak.classList.toggle("danger", danger);
      streak.replaceChildren(
        el("div", { textContent: `Line streak: ${state.line_streak} / ${limit}` }),
        ...(danger ? [el("div", { textContent: "One more line and you lose all your cells!" })] : []));
    }
  }

  function renderGameOver() {
    $("hint").classList.toggle("hidden", state.is_over);
    $("gameover").classList.toggle("hidden", !state.is_over);
    if (!state.is_over) return;
    $("final-scores").replaceChildren(...state.players.map((player) =>
      el("span", { className: "final-score", textContent: state.scores[player.name], style: `color: ${player.color}` })));
    const outcome = $("outcome");
    outcome.textContent = state.outcome;
    outcome.style.color = state.winner ? colorOf(state.winner) : "";
  }

  // ---------------------------------------------------------------- hover preview
  function paintedCells(row, col) {
    return state.current_card.offsets
      .map(([dr, dc]) => [row + dr, col + dc])
      .filter(([r, c]) => r >= 0 && r < state.size && c >= 0 && c < state.size);
  }

  function updatePreview() {
    const cells = $("board").children;
    for (const cell of cells) cell.classList.remove("preview", "preview-center");
    if (!state || state.is_over || !hovered) return;
    for (const [r, c] of paintedCells(hovered[0], hovered[1])) {
      cells[r * state.size + c].classList.add("preview");
    }
    cells[hovered[0] * state.size + hovered[1]].classList.add("preview-center");
  }

  // ---------------------------------------------------------------- events
  function cellOf(event) {
    const cell = event.target.closest(".cell");
    return cell ? [Number(cell.dataset.row), Number(cell.dataset.col)] : null;
  }

  $("board").addEventListener("mouseover", (event) => { hovered = cellOf(event); updatePreview(); });
  $("board").addEventListener("mouseleave", () => { hovered = null; updatePreview(); });
  $("board").addEventListener("click", (event) => {
    const position = cellOf(event);
    if (position) playCell(position[0], position[1]);
  });

  $("play-btn").addEventListener("click", () => startMatch(collectConfig()));
  $("defaults-btn").addEventListener("click", () => { applyConfigToForm(schema.defaults); showConfigError(""); });
  $("replay-btn").addEventListener("click", () => {
    if (state) api.deleteGame(state.id).catch(() => {});
    startMatch(lastConfig || collectConfig());
  });
  $("home-btn").addEventListener("click", goHome);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state) goHome();
  });

  // ---------------------------------------------------------------- start
  async function init() {
    try {
      schema = await api.settings();
      buildSettingsForm();
    } catch (error) {
      showConfigError(`Could not load the settings: ${error.message}`);
    }
    const id = remembered();
    if (id) {
      try {
        state = await api.getGame(id);
        lastConfig = state.config;
        if (schema) applyConfigToForm(state.config);
        showScreen("match");
        render();
        return;
      } catch (_) { remember(null); state = null; }
    }
    showScreen("home");
  }
  init();
})();
