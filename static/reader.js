(function () {
  "use strict";

  const cfg = window.READER || {};
  const list = document.getElementById("marker-list");
  const toast = document.getElementById("toast");
  const reader = document.getElementById("reader-text");
  const noteForm = document.getElementById("note-form");
  let color = "yellow";
  let highlights = Array.isArray(cfg.highlights) ? cfg.highlights.slice() : [];

  function showToast(message) {
    if (!toast) return;
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
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || "Something went wrong.");
    return body;
  }

  document.querySelectorAll(".swatch").forEach((btn) => {
    btn.addEventListener("click", () => {
      color = btn.dataset.color;
      document.querySelectorAll(".swatch").forEach((item) => item.classList.toggle("active", item.dataset.color === color));
    });
  });

  function escapeHTML(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderList() {
    if (!list) return;
    if (!highlights.length) {
      list.innerHTML = '<p class="empty-state">Пока нет маркеров.</p>';
      return;
    }
    list.innerHTML = highlights
      .map(
        (item) => `
        <div class="marker-item" data-id="${item.id}">
          <p class="snip">${escapeHTML(item.snippet || item.note || "")}</p>
          ${item.note ? `<p>${escapeHTML(item.note)}</p>` : ""}
          <button type="button" class="icon-btn delete-btn" data-id="${item.id}">✕</button>
        </div>`
      )
      .join("");
  }

  function renderText() {
    if (!reader || !cfg.isText) return;
    const source = reader.dataset.source || reader.textContent;
    reader.dataset.source = source;
    const ranges = highlights
      .filter((item) => item.end_offset > item.start_offset)
      .sort((a, b) => a.start_offset - b.start_offset);
    let html = "";
    let cursor = 0;
    ranges.forEach((item) => {
      const start = Math.max(cursor, item.start_offset);
      const end = Math.min(source.length, item.end_offset);
      if (end <= start) return;
      html += escapeHTML(source.slice(cursor, start));
      html += `<mark data-color="${escapeHTML(item.color)}" data-id="${item.id}">${escapeHTML(source.slice(start, end))}</mark>`;
      cursor = end;
    });
    html += escapeHTML(source.slice(cursor));
    reader.innerHTML = html;
  }

  function selectionOffsets() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || !reader) return null;
    const range = sel.getRangeAt(0);
    if (!reader.contains(range.commonAncestorContainer)) return null;
    const pre = range.cloneRange();
    pre.selectNodeContents(reader);
    pre.setEnd(range.startContainer, range.startOffset);
    const start = pre.toString().length;
    const end = start + range.toString().length;
    if (end <= start) return null;
    return { start, end, snippet: range.toString().slice(0, 400) };
  }

  if (reader && cfg.isText) {
    async function saveSelection() {
      const picked = selectionOffsets();
      if (!picked) return;
      try {
        const created = await api(`/api/books/${cfg.bookId}/highlights`, {
          method: "POST",
          body: JSON.stringify({
            color,
            start_offset: picked.start,
            end_offset: picked.end,
            snippet: picked.snippet,
          }),
        });
        highlights.push(created);
        renderList();
        renderText();
        window.getSelection().removeAllRanges();
      } catch (error) {
        showToast(error.message);
      }
    }
    reader.addEventListener("mouseup", saveSelection);
    reader.addEventListener("touchend", () => setTimeout(saveSelection, 50));
  }

  if (noteForm) {
    noteForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const snippet = document.getElementById("note-snippet").value.trim();
      const note = document.getElementById("note-text").value.trim();
      if (!snippet && !note) return;
      try {
        const created = await api(`/api/books/${cfg.bookId}/highlights`, {
          method: "POST",
          body: JSON.stringify({ color, snippet, note, start_offset: 0, end_offset: 0 }),
        });
        highlights.push(created);
        renderList();
        noteForm.reset();
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  if (list) {
    list.addEventListener("click", async (event) => {
      const button = event.target.closest(".delete-btn");
      if (!button) return;
      const id = button.dataset.id;
      try {
        await api(`/api/books/${cfg.bookId}/highlights/${id}`, { method: "DELETE" });
        highlights = highlights.filter((item) => String(item.id) !== String(id));
        renderList();
        renderText();
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  renderList();
  renderText();
})();
