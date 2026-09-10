(function () {
  "use strict";

  const topicToggle = document.getElementById("topic-toggle");
  const topicFilter = document.getElementById("topic-filter");
  const emptyCards = document.getElementById("empty-cards");
  const allCaughtUp = document.getElementById("all-caught-up");
  const studyArea = document.getElementById("study-area");
  const studyProgress = document.getElementById("study-progress");
  const studyTopic = document.getElementById("study-topic");
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
  if (!revealBtn || !studyActions) return;

  let pageAlive = true;
  function onPage() {
    return pageAlive && revealBtn.isConnected;
  }

  const params = new URLSearchParams(window.location.search);
  let allCards = [];
  let decks = [];
  let selectedTopic = params.get("topic") || "All";
  let queue = [];
  let queueTotal = 0;
  let revealed = false;
  let topicFilterExpanded = false;
  let lastReview = null;
  let busy = false;

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

  function topicLabel(topic) {
    return topic === "All" ? t("topic_all") : String(topic).replace(/_/g, " ");
  }

  function renderTopicFilter(topics) {
    if (!onPage() || !topicFilter) return;
    const chips = ["All", ...topics];
    if (selectedTopic !== "All" && !topics.includes(selectedTopic)) chips.push(selectedTopic);
    topicFilter.innerHTML = chips
      .map((topic) => `<span class="topic-chip ${topic === selectedTopic ? "active" : ""}" data-topic="${escapeHTML(topic)}">${escapeHTML(topicLabel(topic))}</span>`)
      .join("");
    updateTopicToggleLabel();
  }

  function updateTopicToggleLabel() {
    if (!topicToggle) return;
    const arrow = topicFilterExpanded ? "▴" : "▾";
    topicToggle.textContent = `📂 ${t("topic_toggle", { topic: topicLabel(selectedTopic) })} ${arrow}`;
  }

  function setTopicFilterExpanded(expanded) {
    topicFilterExpanded = expanded;
    if (topicFilter) topicFilter.style.display = expanded ? "" : "none";
    updateTopicToggleLabel();
  }

  if (topicToggle) {
    topicToggle.addEventListener("click", () => setTopicFilterExpanded(!topicFilterExpanded));
  }
  if (topicFilter) {
    topicFilter.addEventListener("click", (event) => {
      const chip = event.target.closest(".topic-chip");
      if (!chip) return;
      selectedTopic = chip.dataset.topic;
      renderTopicFilter([...new Set(allCards.map((card) => card.topic))].sort());
      buildQueue();
      setTopicFilterExpanded(false);
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
    const dueCards = allCards.filter((card) => card.due_today);
    queue = selectedTopic === "All" ? dueCards.slice() : dueCards.filter((card) => card.topic === selectedTopic);
    queueTotal = queue.length;
    showNextCard();
  }

  function showNextCard() {
    if (!onPage()) return;
    revealed = false;
    studyAnswer.style.display = "none";
    studyExample.style.display = "none";
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
      if (allCaughtUp) allCaughtUp.style.display = "";
      return;
    }
    if (allCaughtUp) allCaughtUp.style.display = "none";
    studyArea.style.display = "";

    const card = queue[0];
    studyProgress.textContent = t("progress_of", { current: queueTotal - queue.length + 1, total: queueTotal });
    studyTopic.textContent = topicLabel(card.topic);
    studyQuestion.textContent = card.question;
    studyAnswer.textContent = card.answer;
    studyExample.textContent = card.example || "";
    applyPreviews(card);
  }

  function reveal() {
    if (!onPage() || revealed || queue.length === 0) return;
    revealed = true;
    studyAnswer.style.display = "";
    if (queue[0] && queue[0].example) studyExample.style.display = "";
    revealBtn.style.display = "none";
    studyActions.style.display = "grid";
  }

  revealBtn.addEventListener("click", reveal);
  if (studyCard) {
    studyCard.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
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
    showNextCard();
    busy = true;
    try {
      await api(`/api/cards/${card.id}/review`, { method: "POST", body: JSON.stringify({ confidence }) });
    } catch (error) {
      queue.unshift(card);
      lastReview = null;
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
    if (!onPage() || !document.getElementById("study-area")) return;
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
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  function applyData(data) {
    if (!onPage() || !data) return;
    allCards = data.cards || [];
    decks = data.decks || decks;
    renderCounts(data.counts);
    renderTopicFilter(data.topics || []);
    renderDecks();
    buildQueue();
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

  window._pageCleanup = function () {
    pageAlive = false;
    document.removeEventListener("keydown", onKey);
  };
})();
