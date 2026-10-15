  /* ── Widget Avanzado de Accesibilidad ── */
  (function () {
    // Escala base del texto: el 100% del widget equivale al 85% del tamaño
    // nativo del navegador (16px * 0.85 = 13.6px). Debe coincidir con styles.css.
    var FONT_BASE_SCALE = 0.85;
    // Versión de la calibración de fuente (para migrar valores antiguos)
    var FONT_VERSION = 2;

    // Valores por defecto
    var D = {
      darkMode: false,
      bright: 100,
      font: 100,
      fv: FONT_VERSION,
      bigCursor: false,
      hlLinks: false,
      dyslexic: false,
      spacing: false,
      animations: true,
      focus: false,
    };
    var s = Object.assign({}, D);
    var _toast = null;
    var currentTab = "tamano";
    var lastClientY = window.innerHeight / 2;

    function save() {
      try {
        localStorage.setItem("a11y", JSON.stringify(s));
        
        // Guardar en sesión de Django mediante fetch
        var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
          fetch('/api/accesibilidad/save/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken.value
            },
            body: JSON.stringify(s)
          }).catch(function(e) { console.error("Error guardando accesibilidad", e); });
        }
      } catch (_) {}
    }

    function load() {
      try {
        var serverDataEl = document.getElementById("a11y-session-data");
        var serverData = null;
        if (serverDataEl && serverDataEl.textContent && serverDataEl.textContent !== "null") {
           serverData = JSON.parse(serverDataEl.textContent);
        }
        
        var localDataStr = localStorage.getItem("a11y");
        var localData = localDataStr ? JSON.parse(localDataStr) : null;
        
        // Priorizar datos del servidor (si la sesión sigue viva) o fallback local
        var activeData = serverData || localData;
        
        if (activeData) {
          s = Object.assign({}, D, activeData);
          // Eliminar configuraciones obsoletas de colores si existían en datos guardados
          delete s.theme;
          delete s.saturate;
          delete s.monochrome;
          delete s.invert;

          // Migración: los valores guardados con la escala anterior (sin "fv")
          // se reinician al nuevo 100%, que equivale al antiguo 85%.
          if (activeData.fv !== FONT_VERSION) {
            s.font = 100;
            s.fv = FONT_VERSION;
            save();
          }
        }
      } catch (_) {}
    }

    function applyDarkMode(on) {
      if (on) {
        document.documentElement.setAttribute("data-bs-theme", "dark");
      } else {
        document.documentElement.removeAttribute("data-bs-theme");
      }
    }

    // ═══ FUNCIONES DE TABS ═══
    function switchTab(tabName) {
      // Ocultar todos los tabs
      var panels = document.querySelectorAll(".a11y-tab-panel");
      panels.forEach(function (p) {
        p.style.display = "none";
        p.classList.remove("a11y-tab-panel-active");
      });

      // Desactivar todos los botones
      var btns = document.querySelectorAll(".a11y-tab-btn");
      btns.forEach(function (b) {
        b.classList.remove("a11y-tab-active");
        b.setAttribute("aria-selected", "false");
      });

      // Activar tab seleccionado
      var activePanel = document.getElementById("panel-" + tabName);
      var activeBtn = document.getElementById("tab-" + tabName);

      if (activePanel) {
        activePanel.style.display = "block";
        activePanel.classList.add("a11y-tab-panel-active");
      }
      if (activeBtn) {
        activeBtn.classList.add("a11y-tab-active");
        activeBtn.setAttribute("aria-selected", "true");
      }

      currentTab = tabName;
    }

    function applyBright(v) {
      var el = document.getElementById("a11y-bright-style");
      if (!el) {
        el = document.createElement("style");
        el.id = "a11y-bright-style";
        document.head.appendChild(el);
      }
      el.textContent =
        +v === 100 ? "" : "html{filter:brightness(" + v + "%)!important}";
    }

    function applyFont(v) {
      var baseSize = 16 * FONT_BASE_SCALE;
      document.documentElement.style.fontSize = (v / 100) * baseSize + "px";
    }

    function applyBigCursor(on) {
      if (on) {
        document.documentElement.setAttribute("data-a11y-cursor", "true");
      } else {
        document.documentElement.removeAttribute("data-a11y-cursor");
      }
    }

    function applyLinks(on) {
      if (on) {
        document.documentElement.setAttribute("data-a11y-links", "true");
      } else {
        document.documentElement.removeAttribute("data-a11y-links");
      }
    }

    function applyToggleAttr(attr, on) {
      if (on) {
        document.documentElement.setAttribute(attr, "true");
      } else {
        document.documentElement.removeAttribute(attr);
      }
    }

    // ═══ GUÍA DE LECTURA (PANTALLA COMPLETA) ═══
    function renderFocus(y) {
      var backdrop = document.getElementById("a11y-focus-backdrop");
      var guide = document.getElementById("a11y-reading-guide");
      if (backdrop && guide) {
        guide.style.top = y + "px";
        var winH = window.innerHeight || 800;
        var perc = (y / winH) * 100;
        backdrop.style.background = "linear-gradient(to bottom, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0.65) calc(" + perc + "% - 55px), transparent calc(" + perc + "% - 55px), transparent calc(" + perc + "% + 55px), rgba(0,0,0,0.65) calc(" + perc + "% + 55px), rgba(0,0,0,0.65) 100%)";
      }
    }

    function onFocusMouseMove(e) {
      if (e && typeof e.clientY === "number") {
        lastClientY = e.clientY;
      }
      renderFocus(lastClientY);
    }

    function onFocusScroll() {
      renderFocus(lastClientY);
    }

    function applyFocus(on) {
      var backdrop = document.getElementById("a11y-focus-backdrop");
      var guide = document.getElementById("a11y-reading-guide");
      if (backdrop && guide) {
        if (on) {
          backdrop.classList.remove("d-none");
          guide.classList.remove("d-none");
          renderFocus(lastClientY);
          document.addEventListener("mousemove", onFocusMouseMove, { passive: true });
          window.addEventListener("scroll", onFocusScroll, { passive: true });
          window.addEventListener("resize", onFocusScroll, { passive: true });
        } else {
          backdrop.classList.add("d-none");
          guide.classList.add("d-none");
          document.removeEventListener("mousemove", onFocusMouseMove);
          window.removeEventListener("scroll", onFocusScroll);
          window.removeEventListener("resize", onFocusScroll);
        }
      }
    }

    function cleanLegacyColorAttributes() {
      document.documentElement.removeAttribute("data-a11y-theme");
      document.documentElement.removeAttribute("data-a11y-monochrome");
      document.documentElement.removeAttribute("data-a11y-invert");
      var oldSaturate = document.getElementById("a11y-saturate-style");
      if (oldSaturate) oldSaturate.remove();
    }

    function syncUI() {
      var togDark = document.getElementById("tog-dark-mode");
      if (togDark) {
        togDark.checked = !!s.darkMode;
      }

      ["sl-bright", "sl-font"].forEach(function (id) {
        var el = document.getElementById(id);
        if (!el) return;
        var key = id.replace("sl-", "");
        el.value = s[key];
      });

      var vb = document.getElementById("val-bright");
      if (vb) vb.textContent = s.bright + "%";
      var vf = document.getElementById("val-font");
      if (vf) vf.textContent = s.font + "%";

      ["tog-cursor", "tog-links", "tog-dyslexic", "tog-spacing", "tog-focus"].forEach(function (id) {
        var el = document.getElementById(id);
        if (!el) return;
        var key = { 
          "tog-cursor": "bigCursor", 
          "tog-links": "hlLinks",
          "tog-dyslexic": "dyslexic",
          "tog-spacing": "spacing",
          "tog-focus": "focus"
        }[id];
        el.checked = s[key];
      });

      var togAnim = document.getElementById("tog-animations");
      if (togAnim) {
        // tog-animations es "Pausar animaciones", por lo que si s.animations es true, el checkbox está desmarcado
        togAnim.checked = !s.animations;
      }
    }

    function showToast(msg) {
      var el = document.getElementById("a11y-toast");
      var me = document.getElementById("a11y-toast-msg");
      if (!el || !me) return;
      me.textContent = msg;
      try {
        if (typeof bootstrap !== "undefined" && bootstrap.Toast) {
          if (!_toast) _toast = new bootstrap.Toast(el, { delay: 2000 });
          _toast.show();
        } else {
          el.classList.add("show");
          setTimeout(function () {
            el.classList.remove("show");
          }, 2000);
        }
      } catch (e) {
        el.classList.add("show");
        setTimeout(function () {
          el.classList.remove("show");
        }, 2000);
      }
    }

    function toggle() {
      var p = document.getElementById("a11y-panel");
      var b = document.getElementById("a11y-btn");
      if (!p || !b) return;
      var open = p.classList.contains("d-none");
      p.classList.toggle("d-none", !open);
      b.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) {
        setTimeout(function () {
          var f = p.querySelector("button,input,select");
          if (f) f.focus();
        }, 50);
      } else {
        b.focus();
      }
    }

    function reset() {
      s = Object.assign({}, D);
      try {
        localStorage.removeItem("a11y");
      } catch (_) {}
      applyDarkMode(false);
      applyBright(100);
      applyFont(100);
      applyBigCursor(false);
      applyLinks(false);
      applyToggleAttr("data-a11y-dyslexic", false);
      applyToggleAttr("data-a11y-spacing", false);
      applyToggleAttr("data-a11y-animations", true);
      applyFocus(false);
      cleanLegacyColorAttributes();
      syncUI();
      save();
      showToast("Opciones restablecidas ✓");
    }

    function init() {
      cleanLegacyColorAttributes();
      load();
      applyDarkMode(s.darkMode);
      applyBright(s.bright);
      applyFont(s.font);
      applyBigCursor(s.bigCursor);
      applyLinks(s.hlLinks);
      applyToggleAttr("data-a11y-dyslexic", s.dyslexic);
      applyToggleAttr("data-a11y-spacing", s.spacing);
      applyToggleAttr("data-a11y-animations", s.animations);
      applyFocus(s.focus);
      syncUI();

      // ═══ INICIALIZAR TABS ═══
      var tabBtns = document.querySelectorAll(".a11y-tab-btn");
      tabBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
          var tabName = this.id.replace("tab-", "");
          switchTab(tabName);
        });
        btn.addEventListener("keydown", function (e) {
          if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
            e.preventDefault();
            var allBtns = Array.from(
              document.querySelectorAll(".a11y-tab-btn"),
            );
            var currentIndex = allBtns.indexOf(this);
            var nextIndex =
              e.key === "ArrowRight"
                ? (currentIndex + 1) % allBtns.length
                : (currentIndex - 1 + allBtns.length) % allBtns.length;
            var nextBtn = allBtns[nextIndex];
            nextBtn.focus();
            nextBtn.click();
          }
        });
      });

      // Modo Oscuro
      var togDark = document.getElementById("tog-dark-mode");
      if (togDark) {
        togDark.addEventListener("change", function (e) {
          s.darkMode = e.target.checked;
          applyDarkMode(s.darkMode);
          save();
          showToast(
            s.darkMode ? "🌙 Modo oscuro activado" : "☀️ Modo claro activado",
          );
        });
      }

      // Brillo
      var slBright = document.getElementById("sl-bright");
      if (slBright) {
        slBright.addEventListener("input", function (e) {
          s.bright = +e.target.value;
          applyBright(s.bright);
          var v = document.getElementById("val-bright");
          if (v) v.textContent = s.bright + "%";
          save();
        });
      }

      // Tamaño de fuente
      var slFont = document.getElementById("sl-font");
      if (slFont) {
        slFont.addEventListener("input", function (e) {
          s.font = +e.target.value;
          applyFont(s.font);
          var v = document.getElementById("val-font");
          if (v) v.textContent = s.font + "%";
          save();
        });
      }

      // Cursor grande
      var togCursor = document.getElementById("tog-cursor");
      if (togCursor) {
        togCursor.addEventListener("change", function (e) {
          s.bigCursor = e.target.checked;
          applyBigCursor(s.bigCursor);
          save();
          showToast(
            s.bigCursor ? "🔍 Cursor grande activado" : "🔍 Cursor normal",
          );
        });
      }

      // Enlaces resaltados
      var togLinks = document.getElementById("tog-links");
      if (togLinks) {
        togLinks.addEventListener("change", function (e) {
          s.hlLinks = e.target.checked;
          applyLinks(s.hlLinks);
          save();
          showToast(s.hlLinks ? "🔗 Enlaces resaltados" : "🔗 Enlaces normales");
        });
      }

      // Función auxiliar para toggles con atributos HTML
      function bindToggleAttr(id, key, attr, icon, msgOn, msgOff) {
        var el = document.getElementById(id);
        if (el) {
          el.addEventListener("change", function (e) {
            s[key] = e.target.checked;
            applyToggleAttr(attr, s[key]);
            save();
            showToast(icon + " " + (s[key] ? msgOn : msgOff));
          });
        }
      }

      bindToggleAttr("tog-dyslexic", "dyslexic", "data-a11y-dyslexic", "🔤", "Fuente dislexia activada", "Fuente normal");
      bindToggleAttr("tog-spacing", "spacing", "data-a11y-spacing", "📏", "Espaciado aumentado", "Espaciado normal");

      // Guía de lectura (Focus / Reading Guide)
      var togFocus = document.getElementById("tog-focus");
      if (togFocus) {
        togFocus.addEventListener("change", function(e) {
          s.focus = e.target.checked;
          applyFocus(s.focus);
          save();
          showToast("🎯 Guía de lectura " + (s.focus ? "activada" : "desactivada"));
        });
      }

      // Pausar animaciones
      var togAnim = document.getElementById("tog-animations");
      if (togAnim) {
        togAnim.addEventListener("change", function(e) {
          s.animations = !e.target.checked; 
          applyToggleAttr("data-a11y-animations", s.animations);
          save();
          showToast("⏸️ Animaciones " + (e.target.checked ? "pausadas" : "reanudadas"));
        });
      }

      // Botón reset
      var btnReset = document.getElementById("btn-reset");
      if (btnReset) btnReset.addEventListener("click", reset);

      // Cerrar panel al hacer clic fuera
      document.addEventListener("click", function (e) {
        var p = document.getElementById("a11y-panel");
        var b = document.getElementById("a11y-btn");
        if (
          p &&
          b &&
          !p.classList.contains("d-none") &&
          !p.contains(e.target) &&
          !b.contains(e.target)
        ) {
          p.classList.add("d-none");
          b.setAttribute("aria-expanded", "false");
        }
      });

      // Atajos de teclado
      document.addEventListener("keydown", function (e) {
        if (e.altKey && e.key.toLowerCase() === "a") {
          e.preventDefault();
          toggle();
        }
        if (e.altKey && e.key.toLowerCase() === "r") {
          e.preventDefault();
          reset();
        }
      });

      // Atrapamiento de foco en el panel y tecla Escape para cerrar
      var panel = document.getElementById("a11y-panel");
      if (panel) {
        panel.addEventListener("keydown", function(e) {
          if (e.key === "Escape") {
            e.preventDefault();
            var p = document.getElementById("a11y-panel");
            if (p && !p.classList.contains("d-none")) {
              toggle();
            }
          }
          if (e.key === "Tab") {
            var focusable = panel.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (focusable.length === 0) return;
            var first = focusable[0];
            var last = focusable[focusable.length - 1];
            if (e.shiftKey) {
              if (document.activeElement === first) {
                e.preventDefault();
                last.focus();
              }
            } else {
              if (document.activeElement === last) {
                e.preventDefault();
                first.focus();
              }
            }
          }
        });
      }

      // Escuchar redimensionado para recalcular tamaño base
      window.addEventListener("resize", function () {
        applyFont(s.font);
      });
    }

    window.A11y = { toggle: toggle, reset: reset };

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  })();
