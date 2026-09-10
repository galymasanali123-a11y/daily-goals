(function () {
  "use strict";
  if (window.__DG_NAV) return;
  window.__DG_NAV = true;

  var cache = new Map();
  var MAX = 24;
  var busy = false;
  var queued = null;
  var progress = null;
  var reduced =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function phoneShell() {
    return (
      document.documentElement.classList.contains("standalone") ||
      (window.matchMedia &&
        (window.matchMedia("(display-mode: standalone)").matches ||
          window.matchMedia("(max-width: 719px)").matches))
    );
  }

  function keyFromUrl(href) {
    var u = new URL(href, location.href);
    return u.pathname + u.search;
  }

  function remember(href, html) {
    var key = keyFromUrl(href);
    if (cache.has(key)) cache.delete(key);
    cache.set(key, { html: html, at: Date.now() });
    while (cache.size > MAX) cache.delete(cache.keys().next().value);
  }

  window.__DG_NAV_REMEMBER = function (href) {
    remember(href || location.href, document.documentElement.outerHTML);
  };

  function cached(href) {
    var row = cache.get(keyFromUrl(href));
    return row ? row.html : null;
  }

  function shouldCapture(anchor) {
    if (!anchor || anchor.target === "_blank" || anchor.hasAttribute("download")) return false;
    if (anchor.dataset.fullNav === "1") return false;
    var raw = anchor.getAttribute("href");
    if (!raw || raw.charAt(0) === "#" || raw.indexOf("mailto:") === 0 || raw.indexOf("javascript:") === 0) {
      return false;
    }
    var url;
    try {
      url = new URL(anchor.href, location.href);
    } catch (err) {
      return false;
    }
    if (url.origin !== location.origin) return false;
    if (url.pathname === "/logout" || url.pathname === "/login" || url.pathname === "/register") return false;
    if (/\/file$/.test(url.pathname)) return false;
    if (url.pathname === location.pathname && url.search === location.search && url.hash) return false;
    return true;
  }

  function markActive(pathname) {
    document.querySelectorAll(".bottom-nav a, .nav-tabs a.nav-tab").forEach(function (el) {
      if (el.target === "_blank") {
        el.classList.remove("active");
        return;
      }
      var path;
      try {
        path = new URL(el.href, location.href).pathname;
      } catch (err) {
        return;
      }
      var on = path === "/" ? pathname === "/" : pathname === path || pathname.indexOf(path + "/") === 0;
      el.classList.toggle("active", on);
    });
  }

  function ensureProgress() {
    if (progress) return progress;
    progress = document.getElementById("nav-progress") || document.createElement("div");
    progress.id = "nav-progress";
    progress.removeAttribute("hidden");
    if (!progress.parentNode) document.body.appendChild(progress);
    return progress;
  }

  function showProgress() {
    var bar = ensureProgress();
    bar.classList.remove("done");
    bar.classList.add("on");
  }

  function hideProgress() {
    if (!progress) return;
    progress.classList.add("done");
    setTimeout(function () {
      progress.classList.remove("on", "done");
    }, 220);
  }

  function runScripts(doc) {
    var src = doc.getElementById("page-scripts");
    var dest = document.getElementById("page-scripts");
    if (!dest) return;
    dest.innerHTML = "";
    if (!src) return;
    src.querySelectorAll("script").forEach(function (old) {
      var script = document.createElement("script");
      Array.from(old.attributes).forEach(function (attr) {
        script.setAttribute(attr.name, attr.value);
      });
      if (!old.getAttribute("src")) script.textContent = old.textContent;
      dest.appendChild(script);
    });
  }

  function applyDoc(doc) {
    if (typeof window._pageCleanup === "function") {
      try {
        window._pageCleanup();
      } catch (err) {}
      window._pageCleanup = null;
    }
    document.title = doc.title;
    var lang = doc.documentElement.getAttribute("lang");
    if (lang) document.documentElement.setAttribute("lang", lang);
    document.body.className = doc.body.className;

    var nextMain = doc.querySelector("main");
    var main = document.querySelector("main");
    if (nextMain && main) main.innerHTML = nextMain.innerHTML;

    var nextSub = doc.querySelector("header.top p");
    var sub = document.querySelector("header.top p");
    if (nextSub && sub) sub.innerHTML = nextSub.innerHTML;

    var nextBottom = doc.querySelector(".bottom-nav");
    var bottom = document.querySelector(".bottom-nav");
    if (nextBottom && !bottom) {
      var toast = document.getElementById("toast");
      document.body.insertBefore(nextBottom.cloneNode(true), toast);
    } else if (!nextBottom && bottom) {
      bottom.remove();
    }

    runScripts(doc);
    markActive(location.pathname);
    var liveToast = document.getElementById("toast");
    if (liveToast) liveToast.classList.remove("show");
  }

  function pull(href) {
    return fetch(href, {
      credentials: "same-origin",
      headers: { Accept: "text/html", "X-DG-Nav": "1" },
    }).then(function (response) {
      var finalUrl = response.url || href;
      var path = new URL(finalUrl, location.href).pathname;
      if (path === "/login" || path === "/register") {
        location.href = finalUrl;
        return Promise.reject(new Error("auth"));
      }
      if (!response.ok) throw new Error("nav");
      return response.text().then(function (html) {
        remember(finalUrl, html);
        return { html: html, url: finalUrl };
      });
    });
  }

  function paint(payload, opts) {
    opts = opts || {};
    var doc = new DOMParser().parseFromString(payload.html, "text/html");
    var run = function () {
      if (!opts.pop && !opts.silent) history.pushState({ dg: 1 }, "", payload.url);
      applyDoc(doc);
      if (!opts.silent) window.scrollTo(0, 0);
    };
    if (!reduced && !opts.silent && !phoneShell() && document.startViewTransition) {
      return document.startViewTransition(run).finished.catch(function () {});
    }
    run();
    var main = document.querySelector("main");
    if (!reduced && !opts.silent && main) {
      main.classList.remove("page-in");
      void main.offsetWidth;
      main.classList.add("page-in");
    }
    return Promise.resolve();
  }

  function go(href, opts) {
    opts = opts || {};
    var abs = new URL(href, location.href);
    var dest = abs.pathname + abs.search;
    var here = location.pathname + location.search;
    if (!opts.pop && dest === here) return Promise.resolve();
    if (busy) {
      queued = { href: href, opts: opts };
      return Promise.resolve();
    }
    busy = true;
    markActive(abs.pathname);
    showProgress();

    var html = cached(abs.href);
    var network = pull(abs.href);

    function finish() {
      hideProgress();
      busy = false;
      if (queued) {
        var next = queued;
        queued = null;
        go(next.href, next.opts);
      }
    }

    function fail(err) {
      finish();
      if (err && err.message === "auth") return;
      location.href = abs.href;
    }

    if (html) {
      return paint({ html: html, url: abs.href }, opts)
        .then(function () {
          finish();
          network
            .then(function (fresh) {
              if (phoneShell()) return;
              if (keyFromUrl(fresh.url) !== keyFromUrl(location.href)) return;
              if (fresh.html === html) return;
              var active = document.activeElement;
              if (active && /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName)) return;
              if (document.getElementById("study-card") || document.querySelector(".goal-edit-input")) return;
              return paint(fresh, { silent: true, pop: true });
            })
            .catch(function () {});
        })
        .catch(fail);
    }

    return network
      .then(function (fresh) {
        return paint(fresh, opts).then(finish);
      })
      .catch(fail);
  }

  function prefetch(href) {
    if (!href || cached(href)) return;
    pull(href).catch(function () {});
  }

  document.addEventListener(
    "click",
    function (event) {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      var anchor = event.target.closest("a");
      if (!shouldCapture(anchor)) return;
      event.preventDefault();
      go(anchor.href);
    },
    true
  );

  document.addEventListener(
    "pointerover",
    function (event) {
      var anchor = event.target.closest && event.target.closest("a");
      if (shouldCapture(anchor)) prefetch(anchor.href);
    },
    true
  );

  document.addEventListener(
    "pointerdown",
    function (event) {
      var anchor = event.target.closest && event.target.closest("a");
      if (shouldCapture(anchor)) prefetch(anchor.href);
    },
    true
  );

  window.addEventListener("popstate", function () {
    go(location.href, { pop: true });
  });

  try {
    history.scrollRestoration = "manual";
  } catch (err) {}
  remember(location.href, document.documentElement.outerHTML);

  function syncKeyboard() {
    var active = document.activeElement;
    var typing = active && /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName);
    document.body.classList.toggle("kb-open", Boolean(typing));
  }
  window.addEventListener("focusin", syncKeyboard);
  window.addEventListener("focusout", function () {
    setTimeout(syncKeyboard, 50);
  });

  if (!document.body.classList.contains("auth-page")) {
    var tabs = ["/", "/learn", "/flashcards", "/books"];
    var warm = function () {
      tabs.forEach(function (path) {
        if (path !== location.pathname) prefetch(path);
      });
    };
    if (window.requestIdleCallback) requestIdleCallback(warm, { timeout: 400 });
    else setTimeout(warm, 60);
  }
})();
