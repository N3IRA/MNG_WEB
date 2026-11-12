/**
 * Inicialización de Ondas de Agua sobre la Imagen del Hero (Monagua)
 * Utiliza la librería jQuery Ripples (WebGL) configurada para ondas
 * rítmicas cada 1.5s con presencia clara pero elegante.
 */

$(document).ready(function () {
  const $hero = $('#hero-agua');
  if (!$hero.length) return;

  // Respetar preferencias de accesibilidad (reducción de movimiento)
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion) return;

  try {
    // Inicializar jQuery Ripples con mayor visibilidad y definición
    $hero.ripples({
      resolution: 512,       // Alta resolución para ondas nítidas y cristalinas
      dropRadius: 16,        // Tamaño de onda bien definido y visible (antes 12)
      perturbance: 0.02,     // Refracción un poco más notoria sin deformar en exceso (antes 0.012)
      interactive: true      // Ondas dinámicas al interactuar con el cursor o toque
    });

    // Ondas periódicas cada 1.5 segundos para mantener el agua viva y notoria
    let dropTimer = setInterval(function () {
      if (!$hero.is(':visible')) return;

      const width = $hero.innerWidth();
      const height = $hero.innerHeight();
      if (!width || !height) return;

      // Coordenadas aleatorias para cada gota de agua
      const x = Math.random() * width;
      const y = Math.random() * height;
      const dropRadius = 14 + Math.random() * 8;       // Radio notable (14px a 22px)
      const strength = 0.014 + Math.random() * 0.012;  // Fuerza más notoria (0.014 a 0.026)

      $hero.ripples('drop', x, y, dropRadius, strength);
    }, 1500);

    // Pausar y reanudar la animación según visibilidad en pantalla (ahorro de recursos)
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
  } catch (err) {
    console.warn('[Ripples] No fue posible inicializar WebGL Ripples:', err);
  }
});
