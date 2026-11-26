(function () {
  const btn = document.getElementById("sidebar-toggle");
  const sb = document.getElementById("mainSidebar");
  const ov = document.getElementById("sidebar-overlay");
  const content = document.getElementById("mainContent");

  const ICON_OPEN = '<i class="bi bi-list fs-5"></i>';
  const ICON_CLOSE = '<i class="bi bi-x-lg fs-5"></i>';

  function toggleSidebar(forceClose = false) {
    const isOpen = document.body.classList.contains("sidebar-open");
    if (isOpen || forceClose) {
      document.body.classList.remove("sidebar-open");
      btn.innerHTML = ICON_OPEN;
      btn.setAttribute("aria-expanded", "false");
    } else {
      document.body.classList.add("sidebar-open");
      btn.innerHTML = ICON_CLOSE;
      btn.setAttribute("aria-expanded", "true");
    }
  }

  if (btn && ov) {
    btn.addEventListener("click", () => toggleSidebar());
    ov.addEventListener("click", () => toggleSidebar(true));
  }

  if (sb) {
    sb.querySelectorAll('a, button[data-bs-toggle="dropdown"]').forEach(
      (link) => {
        link.addEventListener("click", (e) => {
          if (
            window.innerWidth < 992 &&
            link.tagName === "A" &&
            !link.hasAttribute("data-bs-toggle")
          ) {
            toggleSidebar(true);
          }
        });
      },
    );
  }
})();

(function () {
  function initPopovers() {
    if (typeof bootstrap === "undefined") return;
    var popoverTriggerList = [].slice.call(
      document.querySelectorAll('[data-bs-toggle="popover"]')
    );
    popoverTriggerList.forEach(function (el) {
      try {
        if (!bootstrap.Popover.getInstance(el)) {
          new bootstrap.Popover(el, {
            boundary: document.body,
            trigger: el.getAttribute('data-bs-trigger') || 'focus',
            html: true
          });
        }
      } catch (e) {}
    });
  }

  // Delegación para soportar DataTables dinámicos (búsqueda, paginación, ordenamiento)
  document.addEventListener('click', function(e) {
    if (typeof bootstrap === "undefined") return;
    var btn = e.target.closest('[data-bs-toggle="popover"]');
    if (btn) {
      var instance = bootstrap.Popover.getInstance(btn);
      if (!instance) {
        instance = new bootstrap.Popover(btn, {
          boundary: document.body,
          trigger: btn.getAttribute('data-bs-trigger') || 'focus',
          html: true
        });
        instance.show();
      }
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function() {
      initPopovers();
    });
  } else {
    initPopovers();
  }
})();
