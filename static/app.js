(function () {
  "use strict";

  const goalsList = document.getElementById("goals-list");
  const syncedList = document.getElementById("synced-list");
  const statDone = document.getElementById("stat-done");
  const statStreak = document.getElementById("stat-streak");
  const addForm = document.getElementById("add-goal-form");
  const addInput = document.getElementById("add-goal-input");
  const historyStrip = document.getElementById("history-strip");
  const digestCard = document.getElementById("digest-card");
  const digestBody = document.getElementById("digest-body");
  const toast = document.getElementById("toast");
  const reorderToggle = document.getElementById("reorder-toggle");
  const allDone = document.getElementById("all-done-today");
  if (!goalsList || !addForm) return;

  let pageAlive = true;
  function onPage() {
    return pageAlive && goalsList.isConnected;
  }

  let editingId = null;
  let reorderMode = false;
  let pendingDelete = null;
  let state = { goals: [], synced_tasks: [], done_count: 0, total_count: 0, streak: 0 };
  const bootstrap = document.getElementById("goals-bootstrap");
  if (bootstrap) {
    try {
      state = Object.assign(state, JSON.parse(bootstrap.textContent));
    } catch (error) {}
  }

  function showToast(message, actionLabel, onAction) {
    if (!onPage() || !toast || !message) return;
    toast.innerHTML = "";
    const text = document.createElement("span");
    text.textContent = message;
    toast.appendChild(text);
    if (actionLabel && onAction) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "toast-action";
      btn.textContent = actionLabel;
      btn.addEventListener("click", () => {
        toast.classList.remove("show");
        onAction();
      });
      toast.appendChild(btn);
    }
    toast.classList.add("show");
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => toast.classList.remove("show"), 3200);
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

  function goalRowHTML(goal, index, total) {
    const doneClass = goal.done ? "done" : "";
    const check = goal.done ? "✓" : "";
    return `
      <div class="goal-row" data-id="${goal.id}">
        <div class="reorder-col">
          <button class="reorder-btn" data-dir="up" title="${t("move_up")}" ${index === 0 ? "disabled" : ""}>▲</button>
          <button class="reorder-btn" data-dir="down" title="${t("move_down")}" ${index === total - 1 ? "disabled" : ""}>▼</button>
        </div>
        <button class="goal-toggle ${doneClass}">
          <span class="checkbox">${check}</span>
          <span class="goal-text">${escapeHTML(goal.text)}</span>
        </button>
        <button class="icon-btn edit-btn" title="${t("edit")}">✎</button>
        <button class="icon-btn delete-btn" title="${t("delete")}">✕</button>
      </div>`;
  }

  function syncedRowHTML(task) {
    const doneClass = task.done ? "done" : "";
    const check = task.done ? "✓" : "";
    const prefix = task.time ? `${task.time} ` : "";
    return `
      <div class="goal-row synced-row" data-id="${task.id}">
        <button class="goal-toggle synced-toggle ${doneClass}">
          <span class="checkbox">${check}</span>
          <span class="goal-text">${escapeHTML(prefix + task.text)}</span>
        </button>
      </div>`;
  }

  function paintLocal() {
    if (!onPage()) return;
    if (statDone) statDone.textContent = `${state.done_count}/${state.total_count}`;
    if (statStreak) statStreak.textContent = `🔥 ${state.streak}`;
    const goals = state.goals || [];
    if (goals.length === 0) {
      goalsList.innerHTML = `<div class="empty-state">${t("no_goals")}</div>`;
    } else {
      goalsList.innerHTML = goals.map((goal, index) => goalRowHTML(goal, index, goals.length)).join("");
    }
    goalsList.classList.toggle("is-reordering", reorderMode);
    if (syncedList && state.synced_tasks) {
      syncedList.innerHTML = state.synced_tasks.map(syncedRowHTML).join("");
    }
    if (allDone) {
      const open = goals.filter((goal) => !goal.done).length + (state.synced_tasks || []).filter((task) => !task.done).length;
      allDone.hidden = !(goals.length && open === 0);
    }
  }

  function renderState(next) {
    if (!onPage() || !next) return;
    state = next;
    paintLocal();
    if (state.history) renderHistory(state.history);
    if (state.digest) renderDigest(state.digest);
    if (typeof window.__DG_NAV_REMEMBER === "function") window.__DG_NAV_REMEMBER();
  }

  function renderHistory(data) {
    if (!historyStrip || !data || !data.days) return;
    const maxCount = Math.max(data.total_goals || 1, 1, ...data.days.map((day) => day.count || 0));
    historyStrip.innerHTML = data.days
      .map((day) => {
        const heightPct = day.height || Math.max(6, Math.round((day.count / maxCount) * 100));
        return `
          <div class="history-day">
            <div class="history-bar ${day.count ? "has-activity" : ""} ${day.date === state.today ? "is-today" : ""}" style="height:${heightPct}%"></div>
            <div class="history-label">${escapeHTML(day.label || "")}</div>
          </div>`;
      })
      .join("");
  }

  function renderDigest(digest) {
    if (!digestCard || !digestBody) return;
    const nothingYet = digest.streak === 0 && digest.goals_completed === 0 && digest.reviews_completed === 0 && !digest.weakest_topic;
    if (nothingYet) {
      digestCard.hidden = true;
      return;
    }
    let html = `
      <div class="digest-row"><span>${t("day_streak")}</span><span class="digest-value">🔥 ${digest.streak}</span></div>
      <div class="digest-row"><span>${t("goals_completed")}</span><span class="digest-value">${digest.goals_completed}</span></div>
      <div class="digest-row"><span>${t("flashcards_reviewed")}</span><span class="digest-value">${digest.reviews_completed}</span></div>
    `;
    if (digest.weakest_topic) {
      html += `<div class="digest-weak-topic">${t("weakest_topic", { topic: escapeHTML(digest.weakest_topic.topic), ease: digest.weakest_topic.avg_ease })}</div>`;
    }
    digestBody.innerHTML = html;
    digestCard.hidden = false;
  }

  function recount() {
    const doneGoals = (state.goals || []).filter((goal) => goal.done).length;
    const doneTasks = (state.synced_tasks || []).filter((task) => task.done).length;
    state.done_count = doneGoals + doneTasks;
    state.total_count = (state.goals || []).length + (state.synced_tasks || []).length;
  }

  if (reorderToggle) {
    reorderToggle.addEventListener("click", () => {
      reorderMode = !reorderMode;
      reorderToggle.textContent = reorderMode ? t("done_reorder") : t("reorder");
      goalsList.classList.toggle("is-reordering", reorderMode);
    });
  }

  if (syncedList) {
    syncedList.addEventListener("click", async (event) => {
      const row = event.target.closest(".synced-row");
      if (!row || !event.target.closest(".synced-toggle")) return;
      const task = (state.synced_tasks || []).find((item) => String(item.id) === row.dataset.id);
      if (task) {
        task.done = !task.done;
        recount();
        paintLocal();
      }
      try {
        renderState(await api(`/api/synced-tasks/${row.dataset.id}/toggle`, { method: "POST" }));
      } catch (error) {
        if (task) task.done = !task.done;
        recount();
        paintLocal();
        showToast(error.message);
      }
    });
  }

  goalsList.addEventListener("click", async (event) => {
    const row = event.target.closest(".goal-row");
    if (!row) return;
    const goalId = row.dataset.id;

    if (event.target.closest(".goal-toggle")) {
      if (editingId === goalId) return;
      const goal = (state.goals || []).find((item) => String(item.id) === goalId);
      if (goal) {
        goal.done = !goal.done;
        recount();
        paintLocal();
      }
      try {
        renderState(await api(`/api/toggle/${goalId}`, { method: "POST" }));
      } catch (error) {
        if (goal) goal.done = !goal.done;
        recount();
        paintLocal();
        showToast(error.message);
      }
      return;
    }

    if (event.target.closest(".delete-btn")) {
      const goal = (state.goals || []).find((item) => String(item.id) === goalId);
      if (!goal) return;
      pendingDelete = goal;
      state.goals = state.goals.filter((item) => String(item.id) !== goalId);
      recount();
      paintLocal();
      showToast(t("goal_deleted"), t("undo"), async () => {
        pendingDelete = null;
        try {
          renderState(await api("/api/goals", { method: "POST", body: JSON.stringify({ text: goal.text }) }));
        } catch (error) {
          showToast(error.message);
        }
      });
      try {
        await api(`/api/goals/${goalId}/delete`, { method: "POST" });
        pendingDelete = null;
      } catch (error) {
        state.goals.push(goal);
        recount();
        paintLocal();
        showToast(error.message);
      }
      return;
    }

    if (event.target.closest(".reorder-btn")) {
      const button = event.target.closest(".reorder-btn");
      if (button.disabled) return;
      try {
        renderState(await api(`/api/goals/${goalId}/move`, {
          method: "POST",
          body: JSON.stringify({ direction: button.dataset.dir }),
        }));
      } catch (error) {
        showToast(error.message);
      }
      return;
    }

    if (event.target.closest(".edit-btn")) {
      startEdit(row, goalId);
    }
  });

  function startEdit(row, goalId) {
    editingId = goalId;
    const textEl = row.querySelector(".goal-text");
    const currentText = textEl.textContent;
    const toggleBtn = row.querySelector(".goal-toggle");
    const editBtn = row.querySelector(".edit-btn");
    const deleteBtn = row.querySelector(".delete-btn");
    toggleBtn.style.display = "none";
    editBtn.style.display = "none";
    deleteBtn.style.display = "none";
    const wrapper = document.createElement("div");
    wrapper.style.cssText = "flex:1; display:flex; gap:6px;";
    wrapper.innerHTML = `
      <input type="text" class="goal-edit-input" value="${currentText.replace(/"/g, "&quot;")}">
      <button class="icon-btn save-edit-btn" title="${t("save")}">✓</button>
      <button class="icon-btn cancel-edit-btn" title="${t("cancel")}">✕</button>
    `;
    row.insertBefore(wrapper, editBtn);
    const input = wrapper.querySelector("input");
    input.focus();
    input.select();

    async function save() {
      const newText = input.value.trim();
      if (!newText) {
        showToast(t("goal_empty_error"));
        return;
      }
      try {
        renderState(await api(`/api/goals/${goalId}/edit`, {
          method: "POST",
          body: JSON.stringify({ text: newText }),
        }));
      } catch (error) {
        showToast(error.message);
      } finally {
        editingId = null;
      }
    }

    function cancel() {
      editingId = null;
      wrapper.remove();
      toggleBtn.style.display = "";
      editBtn.style.display = "";
      deleteBtn.style.display = "";
    }

    wrapper.querySelector(".save-edit-btn").addEventListener("click", save);
    wrapper.querySelector(".cancel-edit-btn").addEventListener("click", cancel);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") save();
      if (event.key === "Escape") cancel();
    });
  }

  addForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = addInput.value.trim();
    if (!text) return;
    try {
      renderState(await api("/api/goals", { method: "POST", body: JSON.stringify({ text }) }));
      addInput.value = "";
    } catch (error) {
      showToast(error.message);
    }
  });

  paintLocal();

  window._pageCleanup = function () {
    pageAlive = false;
  };
})();
