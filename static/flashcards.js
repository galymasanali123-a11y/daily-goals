(function () {
  "use strict";

  const topicToggle = document.getElementById("topic-toggle");
  const emptyCards = document.getElementById("empty-cards");
  const allCaughtUp = document.getElementById("all-caught-up");
  const studyArea = document.getElementById("study-area");
  const studyProgress = document.getElementById("study-progress");
  const studyTopic = document.getElementById("study-topic");
  const studyTopicBack = document.getElementById("study-topic-back");
  const studyQuestion = document.getElementById("study-question");
  const studyAnswer = document.getElementById("study-answer");
  const studyExample = document.getElementById("study-example");
  const studyCard = document.getElementById("study-card");
  const revealBtn = document.getElementById("reveal-btn");
  const studyActions = document.getElementById("study-actions");
  const undoBtn = document.getElementById("undo-review");
  const toast = document.getElementById("toast");
  const countsBox = document.getElementById("anki-counts");
  const deckList = document.getElementById("deck-list");
  const deckTree = document.getElementById("deck-tree");
  const decksPane = document.getElementById("decks-pane");
  const studyPane = document.getElementById("study-pane");
  const catalogPane = document.getElementById("catalog-pane");
  const deckTabs = document.getElementById("deck-tabs");
  const studiedEl = document.getElementById("studied-today");
  const backBtn = document.getElementById("back-to-decks");
  if (!revealBtn || !studyActions) return;

  let pageAlive = true;
  function onPage() {
    return pageAlive && revealBtn.isConnected;
  }

  const params = new URLSearchParams(window.location.search);
  let allCards = [];
  let decks = [];
  let selectedPath = params.get("topic") || "";
  let selectedKey = "";
  let queue = [];
  let queueTotal = 0;
  let revealed = false;
  let lastReview = null;
  let busy = false;
  let studiedToday = 0;
  let collapsed = {};
  try {
    collapsed = JSON.parse(localStorage.getItem("deck-collapsed") || "{}") || {};
  } catch (error) {
    collapsed = {};
  }

  function showToast(message) {
    if (!onPage() || !toast || !message) return;
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => toast.classList.remove("show"), 2200);
  }

  async function api(path, options) {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (response.status === 401) {
      window.location.href = "/login";
      throw new Error(t("not_authenticated"));
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.error || t("something_wrong"));
    }
    return response.json();
  }

  function escapeHTML(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  const LANG_HEAD = {
    English: "deck_english",
    Deutsch: "deck_german",
    German: "deck_german",
    "한국어": "deck_korean",
    Korean: "deck_korean",
    "Английский": "deck_english",
    "Немецкий": "deck_german",
    "Корейский": "deck_korean",
  };
  const MED_HEAD = { Medicine: 1, "Медицина": 1 };

  function topicParts(topic) {
    const raw = String(topic || "").replace(/_/g, " ").trim() || "Cards";
    let bits;
    if (raw.includes(" / ")) bits = raw.split(" / ").map((part) => part.trim());
    else if (raw.includes(" · ")) bits = raw.split(" · ").map((part) => part.trim());
    else bits = [raw];
    const head = bits[0];
    if (LANG_HEAD[head]) {
      return [t("folder_languages"), t(LANG_HEAD[head]), bits[1] || t("topic_all")];
    }
    if (MED_HEAD[head]) {
      return [t("category_medicine"), bits[1] || t("topic_all")];
    }
    return [t("folder_other"), head];
  }

  function emptyCounts() {
    return { new: 0, learn: 0, due: 0, total: 0 };
  }

  function addCounts(target, extra) {
    target.new += extra.new;
    target.learn += extra.learn;
    target.due += extra.due;
    target.total += extra.total;
  }

  function cardCounts(card) {
    const queue = Number(card.queue || 0);
    const counts = emptyCounts();
    counts.total = 1;
    if (queue === 0) counts.new = 1;
    else if (queue === 1 || queue === 3) counts.learn = 1;
    else if (card.due_today) counts.due = 1;
    return counts;
  }

  function buildTree() {
    const root = { key: "", name: t("topic_all"), depth: 0, children: {}, cards: [], counts: emptyCounts() };
    allCards.forEach((card) => {
      const parts = topicParts(card.topic);
      let node = root;
      addCounts(node.counts, cardCounts(card));
      node.cards.push(card);
      parts.forEach((name, index) => {
        if (!node.children[name]) {
          const key = parts.slice(0, index + 1).join("\t");
          node.children[name] = { key, name, depth: index + 1, children: {}, cards: [], counts: emptyCounts() };
        }
        node = node.children[name];
        node.cards.push(card);
        addCounts(node.counts, cardCounts(card));
      });
    });
    return root;
  }

  function childList(node) {
    return Object.values(node.children).sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
  }

  function saveCollapsed() {
    try {
      localStorage.setItem("deck-collapsed", JSON.stringify(collapsed));
    } catch (error) {}
  }

  function isCollapsed(key) {
    if (key in collapsed) return !!collapsed[key];
    return false;
  }

  function renderTree() {
    if (!deckTree) return;
    const root = buildTree();
    const rows = [];

    function walk(node, hide) {
      const kids = childList(node);
      const hasKids = kids.length > 0;
      const folded = hasKids && isCollapsed(node.key);
      if (!hide) {
        const dueNow = node.cards.filter((card) => card.due_today).length;
        const active = node.key === selectedKey ? " is-active" : "";
        const chevron = hasKids
          ? `<button type="button" class="deck-chevron" data-toggle="${escapeHTML(node.key)}" aria-label="${folded ? "▸" : "▾"}">${folded ? "▸" : "▾"}</button>`
          : `<span class="deck-chevron-spacer"></span>`;
        rows.push(`<div class="deck-row${active}" data-key="${escapeHTML(node.key)}" data-study="${escapeHTML(node.key)}" data-due="${dueNow}" style="--depth:${node.depth}">
          ${chevron}
          <button type="button" class="deck-name" data-study="${escapeHTML(node.key)}">${escapeHTML(node.name)}</button>
          <span class="col-new">${node.counts.new || ""}</span>
          <span class="col-learn">${node.counts.learn || ""}</span>
          <span class="col-due">${node.counts.due || ""}</span>
        </div>`);
      }
      kids.forEach((child) => walk(child, hide || folded));
    }

    childList(root).forEach((child) => walk(child, false));
    if (!rows.length) {
      deckTree.innerHTML = `<p class="empty-state">${t("cards_empty")}</p>`;
    } else {
      deckTree.innerHTML = rows.join("");
    }
    if (studiedEl) studiedEl.textContent = t("studied_today", { n: studiedToday });
  }

  function showPane(name) {
    if (decksPane) decksPane.hidden = name !== "decks";
    if (studyPane) studyPane.hidden = name !== "study";
    if (catalogPane) catalogPane.hidden = name !== "catalog";
    if (deckTabs) {
      deckTabs.querySelectorAll("[data-pane]").forEach((chip) => {
        chip.classList.toggle("active", chip.dataset.pane === name);
      });
      deckTabs.hidden = name === "study";
    }
  }

  function cardsForKey(key) {
    if (!key) return allCards;
    const parts = key.split("\t");
    return allCards.filter((card) => {
      const path = topicParts(card.topic);
      return parts.every((part, index) => path[index] === part);
    });
  }

  function renderCounts(counts) {
    if (!onPage() || !countsBox || !counts) return;
    const nEl = document.getElementById("count-new");
    const lEl = document.getElementById("count-learn");
    const rEl = document.getElementById("count-review");
    if (!nEl || !lEl || !rEl) return;
    nEl.textContent = t("count_new", { n: counts.new || 0 });
    lEl.textContent = t("count_learn", { n: counts.learning || 0 });
    rEl.textContent = t("count_review", { n: counts.review || 0 });
    countsBox.hidden = false;
  }

  function applyPreviews(card) {
    const previews = (card && card.previews) || {};
    studyActions.querySelectorAll("[data-preview]").forEach((el) => {
      el.textContent = previews[el.dataset.preview] || "";
    });
  }

  function renderDecks() {
    if (!deckList) return;
    if (!decks.length) {
      deckList.innerHTML = "";
      return;
    }
    deckList.innerHTML = decks
      .map((deck) => {
        const action = deck.downloaded
          ? `<button type="button" class="ghost-link deck-remove" data-id="${escapeHTML(deck.id)}">${t("remove_deck")}</button>`
          : `<button type="button" class="primary deck-download" data-id="${escapeHTML(deck.id)}">${t("download_deck")}</button>`;
        const badge = deck.downloaded ? `<span class="book-meta">${t("downloaded")}</span>` : `<span class="book-meta">${t("cards_count", { n: deck.card_count })}</span>`;
        return `<div class="catalog-row" data-id="${escapeHTML(deck.id)}">
          <div>
            <strong>${escapeHTML(deck.title)}</strong>
            <p>${escapeHTML(deck.blurb)}</p>
            ${badge}
          </div>
          ${action}
        </div>`;
      })
      .join("");
  }

  function buildQueue() {
    const pool = cardsForKey(selectedKey);
    const dueCards = pool.filter((card) => card.due_today);
    queue = dueCards.slice();
    queueTotal = queue.length;
    showNextCard();
  }

  function showNextCard() {
    if (!onPage()) return;
    revealed = false;
    if (studyCard) studyCard.classList.remove("is-flipped");
    if (studyExample) studyExample.style.display = "none";
    revealBtn.style.display = "";
    studyActions.style.display = "none";
    if (undoBtn) undoBtn.hidden = !lastReview;

    if (allCards.length === 0) {
      if (emptyCards) emptyCards.style.display = "";
      studyArea.style.display = "none";
      if (allCaughtUp) allCaughtUp.style.display = "none";
      return;
    }
    if (emptyCards) emptyCards.style.display = "none";

    if (queue.length === 0) {
      studyArea.style.display = "none";
      if (allCaughtUp) {
        allCaughtUp.style.display = "";
        allCaughtUp.textContent = t("no_cards_in_deck");
      }
      return;
    }
    if (allCaughtUp) allCaughtUp.style.display = "none";
    studyArea.style.display = "";

    const card = queue[0];
    studyProgress.textContent = t("progress_of", { current: queueTotal - queue.length + 1, total: queueTotal });
    const topic = String(card.topic || "").replace(/_/g, " ");
    if (studyTopic) studyTopic.textContent = topic;
    if (studyTopicBack) studyTopicBack.textContent = topic;
    studyQuestion.textContent = card.question;
    studyAnswer.textContent = card.answer;
    if (studyExample) {
      studyExample.textContent = card.example || "";
      studyExample.style.display = "none";
    }
    applyPreviews(card);
  }

  function startStudy(key) {
    selectedKey = key;
    selectedPath = key;
    renderTree();
    showPane("study");
    buildQueue();
  }

  function reveal() {
    if (!onPage() || revealed || queue.length === 0) return;
    revealed = true;
    if (studyCard) studyCard.classList.add("is-flipped");
    if (queue[0] && queue[0].example && studyExample) studyExample.style.display = "";
    revealBtn.style.display = "none";
    studyActions.style.display = "grid";
  }

  revealBtn.addEventListener("click", reveal);
  if (studyCard) {
    studyCard.addEventListener("click", (event) => {
      if (event.target.closest("button") && event.target.closest(".study-actions")) return;
      if (!revealed) reveal();
    });
  }

  async function submitReview(confidence) {
    if (!onPage() || !revealed || queue.length === 0 || busy) return;
    const card = queue[0];
    lastReview = {
      card,
      snapshot: {
        due: card.due,
        interval: card.interval,
        ease: card.ease,
        reps: card.reps,
        lapses: card.lapses,
        queue: card.queue,
        due_at: card.due_at,
        learn_step: card.learn_step,
      },
    };
    queue.shift();
    card.due_today = false;
    studiedToday += 1;
    showNextCard();
    busy = true;
    try {
      await api(`/api/cards/${card.id}/review`, { method: "POST", body: JSON.stringify({ confidence }) });
    } catch (error) {
      queue.unshift(card);
      lastReview = null;
      studiedToday = Math.max(0, studiedToday - 1);
      if (onPage()) {
        showNextCard();
        showToast(error.message);
      }
    } finally {
      busy = false;
    }
  }

  studyActions.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-confidence]");
    if (!button) return;
    submitReview(parseInt(button.dataset.confidence, 10));
  });

  if (undoBtn) {
    undoBtn.addEventListener("click", async () => {
      if (!lastReview || busy) return;
      const { card, snapshot } = lastReview;
      lastReview = null;
      queue.unshift(card);
      card.due_today = true;
      queueTotal += 1;
      studiedToday = Math.max(0, studiedToday - 1);
      showNextCard();
      try {
        await api(`/api/cards/${card.id}/restore`, { method: "POST", body: JSON.stringify(snapshot) });
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  document.addEventListener("keydown", onKey);
  function onKey(event) {
    if (!onPage() || studyPane && studyPane.hidden) return;
    if (!revealed) {
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        reveal();
      }
      return;
    }
    const map = { 1: 1, 2: 2, 3: 3, 4: 4 };
    if (map[event.key]) submitReview(map[event.key]);
  }

  if (deckTabs) {
    deckTabs.addEventListener("click", (event) => {
      const chip = event.target.closest("[data-pane]");
      if (!chip) return;
      showPane(chip.dataset.pane);
    });
  }
  if (backBtn) {
    backBtn.addEventListener("click", () => {
      showPane("decks");
      renderTree();
    });
  }
  if (deckTree) {
    deckTree.addEventListener("click", (event) => {
      const toggle = event.target.closest("[data-toggle]");
      if (toggle) {
        const key = toggle.dataset.toggle;
        collapsed[key] = !isCollapsed(key);
        saveCollapsed();
        renderTree();
        return;
      }
      const study = event.target.closest("[data-study]");
      if (study) startStudy(study.dataset.study);
    });
  }

  if (deckList) {
    deckList.addEventListener("click", async (event) => {
      const download = event.target.closest(".deck-download");
      const remove = event.target.closest(".deck-remove");
      const id = (download || remove) && (download || remove).dataset.id;
      if (!id) return;
      try {
        if (download) {
          download.disabled = true;
          const result = await api(`/api/catalog/decks/${id}/download`, { method: "POST" });
          showToast(t("deck_added", { n: result.added, label: result.label }));
        } else {
          await api(`/api/catalog/decks/${id}`, { method: "DELETE" });
        }
        await load();
        showPane("decks");
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  function applyData(data) {
    if (!onPage() || !data) return;
    allCards = data.cards || [];
    decks = data.decks || decks;
    studiedToday = data.studied_today || 0;
    renderCounts(data.counts);
    renderDecks();
    renderTree();
    if (params.get("topic") && !selectedKey) {
      const want = params.get("topic");
      const match = allCards.find((card) => card.topic === want);
      if (match) selectedKey = topicParts(match.topic).join("\t");
      if (selectedKey) startStudy(selectedKey);
    }
  }

  async function load() {
    try {
      const data = await api("/api/cards");
      if (!onPage()) return;
      applyData(data);
    } catch (error) {
      if (onPage()) showToast(error.message);
    }
  }

  const bootstrapEl = document.getElementById("cards-bootstrap");
  let bootstrapped = false;
  if (bootstrapEl) {
    try {
      applyData(JSON.parse(bootstrapEl.textContent));
      bootstrapped = true;
    } catch (error) {}
  }
  if (!bootstrapped) load();
  if (!allCards.length) showPane("catalog");

  window._pageCleanup = function () {
    pageAlive = false;
    document.removeEventListener("keydown", onKey);
  };
})();
