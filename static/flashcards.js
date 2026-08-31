(function () {
  "use strict";

  const topicFilter = document.getElementById("topic-filter");
  const emptyCards = document.getElementById("empty-cards");
  const importDeckCard = document.getElementById("import-deck-card");
  const importDeckForm = document.getElementById("import-deck-form");
  const importDeckCode = document.getElementById("import-deck-code");
  const allCaughtUp = document.getElementById("all-caught-up");
  const studyArea = document.getElementById("study-area");
  const studyProgress = document.getElementById("study-progress");
  const studyTopic = document.getElementById("study-topic");
  const studyQuestion = document.getElementById("study-question");
  const studyAnswer = document.getElementById("study-answer");
  const studyExample = document.getElementById("study-example");
  const revealBtn = document.getElementById("reveal-btn");
  const studyActions = document.getElementById("study-actions");
  const toast = document.getElementById("toast");

  let allCards = [];
  let today = "";
  let selectedTopic = "All";
  let queue = [];
  let queueTotal = 0;
  let revealed = false;

  function showToast(message) {
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
      throw new Error("not authenticated");
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.error || "Something went wrong.");
    }
    return response.json();
  }

  function escapeHTML(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function renderTopicFilter(topics) {
    const chips = ["All", ...topics];
    topicFilter.innerHTML = chips
      .map((topic) => `<span class="topic-chip ${topic === selectedTopic ? "active" : ""}" data-topic="${escapeHTML(topic)}">${escapeHTML(topic)}</span>`)
      .join("");
  }

  topicFilter.addEventListener("click", (event) => {
    const chip = event.target.closest(".topic-chip");
    if (!chip) return;
    selectedTopic = chip.dataset.topic;
    renderTopicFilter([...new Set(allCards.map((card) => card.topic))].sort());
    buildQueue();
  });

  function buildQueue() {
    // due_today is server-computed: review-due cards are always included, but never-reviewed
    // cards are capped per day (see select_study_cards in app.py) so a freshly-synced 900-card
    // deck doesn't dump every card on you the moment it lands on your phone.
    const dueCards = allCards.filter((card) => card.due_today);
    queue = selectedTopic === "All" ? dueCards : dueCards.filter((card) => card.topic === selectedTopic);
    queueTotal = queue.length;
    showNextCard();
  }

  function showNextCard() {
    revealed = false;
    studyAnswer.style.display = "none";
    studyExample.style.display = "none";
    revealBtn.style.display = "";
    studyActions.style.display = "none";

    if (allCards.length === 0) {
      emptyCards.style.display = "";
      importDeckCard.style.display = "";
      studyArea.style.display = "none";
      allCaughtUp.style.display = "none";
      return;
    }
    emptyCards.style.display = "none";
    importDeckCard.style.display = "none";

    if (queue.length === 0) {
      studyArea.style.display = "none";
      allCaughtUp.style.display = "";
      return;
    }
    allCaughtUp.style.display = "none";
    studyArea.style.display = "";

    const card = queue[0];
    studyProgress.textContent = `${queueTotal - queue.length + 1} of ${queueTotal} due`;
    studyTopic.textContent = card.topic;
    studyQuestion.textContent = card.question;
    studyAnswer.textContent = card.answer;
    if (card.example) {
      studyExample.textContent = card.example;
    }
  }

  revealBtn.addEventListener("click", () => {
    revealed = true;
    studyAnswer.style.display = "";
    if (queue[0] && queue[0].example) studyExample.style.display = "";
    revealBtn.style.display = "none";
    studyActions.style.display = "grid";
  });

  async function submitReview(confidence) {
    if (!revealed || queue.length === 0) return;
    const card = queue[0];
    try {
      await api(`/api/cards/${card.id}/review`, { method: "POST", body: JSON.stringify({ confidence }) });
    } catch (error) {
      showToast(error.message);
      return;
    }
    queue.shift();
    showNextCard();
  }

  studyActions.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-confidence]");
    if (!button) return;
    submitReview(parseInt(button.dataset.confidence, 10));
  });

  importDeckForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const code = importDeckCode.value.trim();
    if (!code) return;
    try {
      const result = await api("/api/import-shared-deck", { method: "POST", body: JSON.stringify({ code }) });
      showToast(`Added ${result.card_count} cards from ${result.label}.`);
      importDeckCode.value = "";
      await load();
    } catch (error) {
      showToast(error.message);
    }
  });

  async function load() {
    try {
      const data = await api("/api/cards");
      allCards = data.cards;
      today = data.today;
      renderTopicFilter(data.topics);
      buildQueue();
    } catch (error) {
      showToast(error.message);
    }
  }

  load();
})();
