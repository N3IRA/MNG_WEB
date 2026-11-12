/**
 * Inicialización de Ondas de Agua sobre la Imagen del Hero (Monagua)
 * Con animación de entrada cinematográfica premium (GSAP) y WebGL Ripples.
 */

$(document).ready(function () {
  const $hero = $('#hero-agua');
  if (!$hero.length) return;

  // Respetar preferencias de accesibilidad (reducción de movimiento)
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // 1. Inicializar WebGL Ripples sobre la imagen
  try {
    $hero.ripples({
      resolution: 512,       // Alta resolución para ondas nítidas y cristalinas
      dropRadius: 16,        // Tamaño de onda bien definido y visible
      perturbance: 0.02,     // Refracción acuática equilibrada y notoria
      interactive: true      // Ondas dinámicas al interactuar con el cursor o toque
    });
  } catch (err) {
    console.warn('[Ripples] No fue posible inicializar WebGL Ripples:', err);
  }

  function triggerDrop(relX, relY, radius, strength) {
    try {
      const width = $hero.innerWidth();
      const height = $hero.innerHeight();
      if (!width || !height) return;
      $hero.ripples('drop', width * relX, height * relY, radius, strength);
    } catch (e) {}
  }

  // 2. Transición de Entrada Cinematográfica Premium con GSAP
  if (window.gsap && !prefersReducedMotion) {
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    // La imagen entra con escala sutil y elevación flotante de 0 a 1
    tl.fromTo('#hero-agua',
      { opacity: 0, scale: 0.95, y: 35 },
      { opacity: 1, scale: 1, y: 0, duration: 1.25, clearProps: 'transform' }
    )
    // En el clímax del asentamiento (a los ~0.8s), cae una gota de bienvenida en el centro del lago
    .add(function () {
      triggerDrop(0.5, 0.46, 20, 0.024);
    }, '-=0.45')
    // Cascada rítmica y suave de textos, botones y badges
    .fromTo('.hero-anim-item',
      { opacity: 0, y: 24 },
      { opacity: 1, y: 0, duration: 0.85, stagger: 0.09, clearProps: 'transform' },
      '-=0.9'
    );
  }

  // 3. Gotas periódicas cada 1.5s para mantener el agua viva en reposo
  if (!prefersReducedMotion) {
    setInterval(function () {
      if (!$hero.is(':visible')) return;

      const width = $hero.innerWidth();
      const height = $hero.innerHeight();
      if (!width || !height) return;

      const x = Math.random() * width;
      const y = Math.random() * height;
      const dropRadius = 14 + Math.random() * 8;       // Radio notable (14px a 22px)
      const strength = 0.014 + Math.random() * 0.012;  // Fuerza notable (0.014 a 0.026)

      $hero.ripples('drop', x, y, dropRadius, strength);
    }, 1500);
  }

  // 4. Pausar y reanudar la animación según visibilidad en pantalla (ahorro de GPU)
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          $hero.ripples('play');
        } else {
          $hero.ripples('pause');
        }
      });
    }, { threshold: 0.05 });

    observer.observe($hero[0]);
  }
});
