(function () {
  "use strict";

  const toast = document.getElementById("toast");
  const uploadForm = document.getElementById("phone-upload-form");
  const fileInput = document.getElementById("phone-upload-file");
  const catalog = document.getElementById("book-catalog");
  const library = document.getElementById("library-list");
  if (!uploadForm && !catalog) return;

  let pageAlive = true;
  function onPage() {
    return pageAlive && document.body.contains(uploadForm || catalog);
  }

  function showToast(message) {
    if (!onPage() || !toast || !message) return;
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => toast.classList.remove("show"), 2200);
  }

  async function api(path, options) {
    const response = await fetch(path, options);
    if (response.status === 401) {
      window.location.href = "/login";
      throw new Error(t("not_authenticated"));
    }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || t("something_wrong"));
    return body;
  }

  if (uploadForm && fileInput) {
    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!fileInput.files || !fileInput.files[0]) return;
      const data = new FormData();
      data.append("file", fileInput.files[0]);
      try {
        const result = await api("/api/books/from-phone", { method: "POST", body: data });
        showToast(t("book_added", { title: result.title }));
        window.location.href = `/books/${result.id}`;
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  if (catalog) {
    catalog.addEventListener("click", async (event) => {
      const button = event.target.closest(".catalog-download");
      if (!button) return;
      button.disabled = true;
      try {
        const result = await api(`/api/catalog/books/${button.dataset.id}/download`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        });
        showToast(t("book_added", { title: result.title }));
        window.location.href = `/books/${result.id}`;
      } catch (error) {
        button.disabled = false;
        showToast(error.message);
      }
    });
  }

  if (library) {
    library.addEventListener("click", async (event) => {
      const button = event.target.closest(".delete-book");
      if (!button) return;
      event.preventDefault();
      if (!confirm(t("delete_book_confirm"))) return;
      try {
        await api(`/api/books/${button.dataset.id}`, { method: "DELETE" });
        const row = button.closest(".book-row");
        if (row) row.remove();
        if (!library.querySelector(".book-row")) {
          library.innerHTML = `<div class="empty-state">${t("books_empty")}</div>`;
        }
      } catch (error) {
        showToast(error.message);
      }
    });
  }

  window._pageCleanup = function () {
    pageAlive = false;
  };
})();
