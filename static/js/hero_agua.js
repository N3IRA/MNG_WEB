/**
 * Inicialización de Ondas de Agua sobre el Carrusel del Hero (Monagua)
 * Optimizado para alto rendimiento (Lazy WebGL Init, Pausa de slides ocultos y GSAP).
 */

$(document).ready(function () {
  const $carousel = $('#carouselExampleFade');
  if (!$carousel.length) return;

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Helper para inicializar Ripples en un slide específico de forma perezosa
  function setupRipples($el) {
    if (!$el || !$el.length || $el.data('ripples-ready')) return;
    try {
      $el.ripples({
        resolution: 512,       // Alta resolución para nitidez cristalina
        dropRadius: 16,        // Radio de gota
        perturbance: 0.02,     // Refracción equilibrada
        interactive: true      // Interacción táctil y mouse
      });
      $el.data('ripples-ready', true);
    } catch (err) {
      console.warn('[Ripples] Error inicializando WebGL:', err);
    }
  }

  // 1. Inicializar de inmediato ÚNICAMENTE la primera diapositiva (carga ultrarrápida, cero lag)
  const $initialActive = $carousel.find('.carousel-item.active');
  setupRipples($initialActive);

  function triggerDrop(relX, relY, radius, strength) {
    try {
      const $active = $carousel.find('.carousel-item.active');
      const width = $active.innerWidth();
      const height = $active.innerHeight();
      if (!width || !height) return;
      $active.ripples('drop', width * relX, height * relY, radius, strength);
    } catch (e) {}
  }

  // 2. Animación de entrada cinematográfica con GSAP
  if (window.gsap && !prefersReducedMotion) {
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    tl.fromTo($carousel[0],
      { opacity: 0, scale: 0.96, y: 30 },
      { opacity: 1, scale: 1, y: 0, duration: 1.1, clearProps: 'transform' }
    )
    .add(function () {
      triggerDrop(0.5, 0.46, 20, 0.024);
    }, '-=0.4')
    .fromTo('.hero-anim-item',
      { opacity: 0, y: 22 },
      { opacity: 1, y: 0, duration: 0.8, stagger: 0.08, clearProps: 'transform' },
      '-=0.8'
    );
  }

  // 3. Gotas periódicas suaves cada 2.5s exclusivamente sobre el slide activo
  if (!prefersReducedMotion) {
    setInterval(function () {
      if (!$carousel.is(':visible')) return;

      const $active = $carousel.find('.carousel-item.active');
      if (!$active.length) return;

      const width = $active.innerWidth();
      const height = $active.innerHeight();
      if (!width || !height) return;

      const x = Math.random() * width;
      const y = Math.random() * height;
      const dropRadius = 14 + Math.random() * 8;
      const strength = 0.014 + Math.random() * 0.012;

      $active.ripples('drop', x, y, dropRadius, strength);
    }, 2500);
  }

  // 4. Lazy-loading de WebGL al cambiar de diapositiva (slide.bs.carousel)
  $carousel.on('slide.bs.carousel', function (e) {
    const $next = $(e.relatedTarget);

    // Inicializar WebGL en la diapositiva entrante solo cuando va a mostrarse
    setupRipples($next);
    if ($next.data('ripples-ready')) {
      $next.ripples('play');
    }

    // Onda acuática expansiva al comenzar el desvanecimiento hacia la nueva imagen
    setTimeout(function () {
      try {
        const w = $next.innerWidth();
        const h = $next.innerHeight();
        if (w && h) {
          $next.ripples('drop', w * 0.5, h * 0.48, 22, 0.022);
        }
      } catch (err) {}
    }, 200);
  });

  // 5. Al terminar la transición (slid.bs.carousel), pausar las diapositivas ocultas para ahorrar 100% GPU
  $carousel.on('slid.bs.carousel', function () {
    $carousel.find('.carousel-item:not(.active)').each(function () {
      const $inactive = $(this);
      if ($inactive.data('ripples-ready')) {
        $inactive.ripples('pause');
      }
    });
  });

  // 6. Pre-calentar el siguiente slide en segundo plano (idle time) para que esté listo antes del giro
  setTimeout(function () {
    const $second = $carousel.find('.carousel-item').eq(1);
    if ($second.length && !$second.data('ripples-ready')) {
      // Breve cálculo invisible para compilar shader sin tirones
      $second.css({ display: 'block', visibility: 'hidden', position: 'absolute' });
      setupRipples($second);
      $second.ripples('pause');
      $second.css({ display: '', visibility: '', position: '' });
    }
  }, 2000);

  // 7. Pausar cuando el carrusel salga del viewport (ahorro de batería y recursos)
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        const $active = $carousel.find('.carousel-item.active');
        if (entry.isIntersecting) {
          if ($active.data('ripples-ready')) $active.ripples('play');
        } else {
          if ($active.data('ripples-ready')) $active.ripples('pause');
        }
      });
    }, { threshold: 0.05 });

    observer.observe($carousel[0]);
  }
});
