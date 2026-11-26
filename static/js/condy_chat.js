document.addEventListener("DOMContentLoaded", function () {
  const btnOpen = document.getElementById("condor-img"); // Usar la imagen de la mascota
  const btnClose = document.getElementById("condy-chat-close");
  const btnClear = document.getElementById("condy-chat-clear");
  const window = document.getElementById("condy-chat-window");
  const messagesContainer = document.getElementById("condy-chat-messages");
  const input = document.getElementById("condy-chat-input-text");
  const btnSend = document.getElementById("condy-chat-send");
  const optionsContainer = document.getElementById("condy-chat-options");
  const bubble = document.getElementById('condor-speech-bubble');
  const statusBadge = document.getElementById('condy-status-badge');
  const statusDesc = document.getElementById('condy-status-desc');
  
  let isFirstOpen = true;
  let forzarModoOffline = false; // Modo de presentación / simulación sin internet

  // Gestión de Resiliencia y Estado de Conexión a Internet
  function actualizarEstadoConexion(isOnline) {
    if (!statusBadge) return;
    if (isOnline && !forzarModoOffline) {
      statusBadge.style.backgroundColor = '#28a745';
      statusBadge.style.color = '#fff';
      statusBadge.innerHTML = '● En línea';
      if (statusDesc) statusDesc.textContent = 'Mongua, Boyacá • Siempre disponible';
    } else {
      statusBadge.style.backgroundColor = '#ffc107';
      statusBadge.style.color = '#000';
      statusBadge.innerHTML = '⚠ Sin internet (Modo Local)';
      if (statusDesc) statusDesc.textContent = 'Respuestas offline activadas para montaña';
    }
  }

  // Permitir alternar Modo Offline haciendo clic en la insignia (Ideal para Presentaciones / Demos)
  if (statusBadge) {
    statusBadge.style.cursor = 'pointer';
    statusBadge.title = 'Haz clic para simular/alternar Modo Offline (para presentaciones sin internet)';
    statusBadge.addEventListener('click', () => {
      forzarModoOffline = !forzarModoOffline;
      if (forzarModoOffline) {
        actualizarEstadoConexion(false);
        addMessage("🟡 **Modo Fuera de Línea Activado (Simulación para Presentación / Demostración)**\n\nPuedes probar cualquier consulta sin necesidad de internet. Cóndy responderá de forma 100% autónoma desde la memoria del navegador.", "bot");
        showOptions([
          "¿Cómo funciona la página?",
          "Regulaciones ambientales",
          "Contactos de emergencia",
          "Primeros auxilios / Altura"
        ]);
      } else {
        actualizarEstadoConexion(navigator.onLine);
        addMessage("🟢 **Modo En Línea Restaurado.** Cóndy vuelve a consultar el servidor de Monagua en tiempo real.", "bot");
        showOptions(initialOptions);
      }
    });
  }

  // Inicializar estado según navegador
  actualizarEstadoConexion(navigator.onLine);

  window.addEventListener('online', () => {
    if (!forzarModoOffline) {
      actualizarEstadoConexion(true);
      addMessage("🟢 **Conexión a internet restablecida.** Cóndy vuelve a estar conectado en tiempo real con el servidor de Monagua.", "bot");
    }
  });

  window.addEventListener('offline', () => {
    actualizarEstadoConexion(false);
    addMessage("📶 **Has perdido la conexión a internet.** Se ha activado el **Modo Sin Conexión (Offline)**. Cóndy cuenta con base de conocimiento completa para responderte sobre tours, cómo funciona la página, reservas, pagos, emergencias y regulaciones del páramo.", "bot");
    showOptions([
      "¿Cómo funciona la página?",
      "Regulaciones ambientales",
      "Contactos de emergencia",
      "Primeros auxilios / Altura"
    ]);
  });

  // Opciones iniciales frecuentes (CA2)
  const initialOptions = [
    "¿Cómo funciona la página?",
    "Regulaciones ambientales",
    "¿Qué tours ofrecen?",
    "¿Cómo realizar un pago?",
    "¿Cómo radicar una PQRS?"
  ];

  // Restaurar historial del sessionStorage
  let chatHistory = JSON.parse(sessionStorage.getItem('condy_chat_history') || '[]');
  
  if (chatHistory.length > 0) {
      isFirstOpen = false;
      // Recrear mensajes
      chatHistory.forEach(msg => {
          if (msg.type === 'message') {
              addMessage(msg.text, msg.sender, false);
          } else if (msg.type === 'options') {
              showOptions(msg.options, false);
          } else if (msg.type === 'custom_link') {
              showCustomLink(msg.url, msg.text, false);
          } else if (msg.type === 'fallback') {
              showFallbackOption(false);
          }
      });
  }

  // Alternar ventana de chat
  if (btnOpen) {
      btnOpen.addEventListener("click", (e) => {
          e.stopPropagation();
          toggleChat();
      });
  }
  
  if (btnClose) {
      btnClose.addEventListener("click", (e) => {
          e.stopPropagation();
          toggleChat(false);
      });
  }

  if (btnClear) {
      btnClear.addEventListener("click", (e) => {
          e.stopPropagation();
          reiniciarChat();
      });
  }

  document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !window.classList.contains("d-none")) {
          toggleChat(false);
      }
  });

  function reiniciarChat() {
      sessionStorage.removeItem('condy_chat_history');
      chatHistory = [];
      messagesContainer.innerHTML = '';
      hideOptions();
      const greeting = "¡Hola! He reiniciado nuestra conversación. Soy Cóndy, tu cóndor guardián y asistente en Monagua Turismo. ¿En qué te puedo orientar hoy?";
      addMessage(greeting, "bot");
      showOptions(initialOptions);
  }

  function toggleChat(forceState = null) {
    const isHidden = window.classList.contains("d-none");
    const willShow = forceState !== null ? forceState : isHidden;
    
    if (willShow) {
      window.classList.remove("d-none");
      
      if (isFirstOpen) {
        const greeting = "¡Hola! Soy Cóndy, tu asistente virtual y cóndor guardián en Monagua Turismo. ¿En qué te puedo orientar hoy? Puedes consultarme sobre tours, cómo funciona la página, regulaciones ambientales o pagos.";
        addMessage(greeting, "bot");
        showOptions(initialOptions);
        isFirstOpen = false;
      }
      setTimeout(() => input.focus(), 300);
    } else {
      window.classList.add("d-none");
    }
  }

  // Manejar input de texto
  input.addEventListener("input", function() {
    btnSend.disabled = this.value.trim().length === 0;
  });

  input.addEventListener("keypress", function(e) {
    if (e.key === "Enter" && !btnSend.disabled) {
      handleSend();
    }
  });

  btnSend.addEventListener("click", handleSend);

  function saveToHistory(item) {
      chatHistory.push(item);
      sessionStorage.setItem('condy_chat_history', JSON.stringify(chatHistory));
  }

  // ════════════════════════════════════════════════════════════════════════════
  // BASE DE CONOCIMIENTO LOCAL OFFLINE MULTIPLE (CERO FALLAS EN PRESENTACIÓN)
  // ════════════════════════════════════════════════════════════════════════════
  const OFFLINE_FAQS = [
    // 1. Saludo
    {
      id: "saludo",
      keywords: ["hola", "buen dia", "buenos dias", "buenas tardes", "buenas noches", "hey", "saludos", "que tal", "como estas", "buenas", "hi", "hello"],
      answer: "¡Hola! Soy Cóndy, tu asistente virtual y cóndor guardián en Monagua Turismo. Me encuentro funcionando en **Modo Local (Autónomo)**. ¿En qué te puedo colaborar hoy? Puedes consultarme sobre tours, cómo funciona la página, reservas, pagos o regulaciones del páramo.",
      options: ["¿Cómo funciona la página?", "Regulaciones ambientales", "¿Qué tours ofrecen?", "¿Cómo realizar un pago?"]
    },
    // 2. Identidad
    {
      id: "identidad",
      keywords: ["quien eres", "que eres", "como te llamas", "tu nombre", "eres un bot", "eres una ia", "que es condy", "quien es condy", "presentate", "que haces", "cual es tu funcion"],
      answer: "Soy Cóndy, la mascota oficial y asistente virtual de Monagua Turismo. Represento al cóndor andino que sobrevuela las cumbres del Páramo de Ocetá. Mi función es guiarte en tu viaje, explicarte las normas de protección ambiental y orientarte en tus reservas y pagos, tanto con internet como en modo fuera de línea.",
      options: ["¿Cómo funciona la página?", "Regulaciones ambientales", "Destinos de Mongua"]
    },
    // 3. Despedida y agradecimiento
    {
      id: "despedida",
      keywords: ["gracias", "muchas gracias", "mil gracias", "te agradezco", "chao", "adios", "hasta luego", "nos vemos", "que estes bien", "excelente", "perfecto", "muy amable"],
      answer: "¡Con el mayor de los gustos! En Monagua amamos proteger la magia de Boyacá y cuidar de nuestros visitantes. Si requieres algo más durante tu viaje por Mongua, aquí estaré siempre disponible.",
      options: ["Ver destinos", "¿Cómo reservar?", "Regulaciones ambientales"]
    },
    // 4. Cómo funciona la página
    {
      id: "como_funciona",
      keywords: ["como funciona la pagina", "como funciona la web", "como funciona monagua", "como funciona la plataforma", "guia de la pagina", "pasos para usar la pagina", "que puedo hacer en la pagina", "instructivo", "de que trata la pagina", "que es monagua web", "como funciona"],
      answer: "💻 **¿Cómo funciona Monagua Turismo? Paso a paso:**\n\n1. **Explora**: Conoce nuestros tours en 'Destinos' (Páramo de Ocetá, Laguna Negra, Ciudad de Piedra).\n2. **Regístrate**: Crea tu cuenta con validación instantánea y código OTP al correo.\n3. **Reserva**: Escoge fecha, cupos de adultos y menores, y añade al carrito.\n4. **Paga y Comprueba**: Transfiere por Nequi, Daviplata o Bancolombia y sube la captura en 'Enviar Comprobante'.\n5. **Confirmación y Factura**: Una vez validado por el administrador, descargas tu factura con código QR y asistes a tu tour con guía certificado y seguro médico.",
      options: ["¿Qué roles hay en la página?", "¿Qué tours ofrecen?", "¿Cómo realizar un pago?"]
    },
    // 5. Roles de Usuario
    {
      id: "roles_usuario",
      keywords: ["roles", "roles de usuario", "tipos de usuario", "que roles hay", "rol de usuario", "turista", "cliente", "guia", "guia turistico", "admin", "administrador", "quien administra"],
      answer: "👥 **Roles del Sistema en Monagua Turismo:**\n\n• **Turista / Cliente**: Explora tours, reserva cupos, sube comprobantes de pago, gestiona cancelaciones, solicita reembolsos, descarga facturas legales y califica el servicio.\n• **Guía Turístico**: Guía local certificado (SENA/RNT) con formación en primeros auxilios y rescate, asignado a liderar las expediciones en campo.\n• **Administrador / Staff**: Revisa y aprueba pagos, administra el catálogo y tarifas por temporada, autoriza reembolsos y supervisa la operación general.",
      options: ["¿Cómo funciona la página?", "¿Cómo registrarse?", "¿Qué tours ofrecen?"]
    },
    // 6. Emergencias y teléfonos
    {
      id: "emergencia",
      keywords: ["emergencia", "auxilio", "ayuda", "socorro", "accidente", "policia", "bomberos", "hospital", "centro de salud", "ambulancia", "urgencias", "herido", "perdido", "desorientado", "contacto", "telefono", "whatsapp", "llamar", "celular"],
      answer: "🚨 **CONTACTOS Y EMERGENCIAS EN MONGUA (DISPONIBLE OFFLINE):**\n\n• **Línea Oficial Monagua / Guías:** +57 322 3465191\n• **Policía Nacional (Mongua):** 112 / 123 (Estación en el Parque Principal)\n• **Centro de Salud de Mongua:** Atención médica de urgencias en el casco urbano\n• **Bomberos y Rescate Sogamoso:** 119\n• **Defensa Civil:** 144\n\n*Consejo de seguridad en montaña:* Permanece en el sendero demarcado, abrígate de inmediato y no intentes descensos por riscos.",
      options: ["Primeros auxilios / Altura", "¿Qué ropa llevar?", "Punto de encuentro"]
    },
    // 7. Altura y Mal de Altura (Soroche)
    {
      id: "altura_soroche",
      keywords: ["soroche", "mal de altura", "altura", "mareo", "dolor de cabeza", "falta de aire", "oxigeno", "nauseas", "frio extremo", "hipotermia", "primeros auxilios", "cansancio", "dificil", "dificultad"],
      answer: "⛰️ **GUÍA DE PRIMEROS AUXILIOS Y MAL DE ALTURA (SOROCHE):**\n\nMongua y el Páramo de Ocetá están entre 3.000 y 3.800 msnm. Ante mareo, fatiga o falta de aire:\n1. **Detente y descansa**: Camina dando pasos cortos y a ritmo pausado; nunca corras en la subida.\n2. **Respira profundo**: Inhala por la nariz inflando el abdomen y exhala con tranquilidad.\n3. **Glucosa e Hidratación**: Toma sorbos de agua de panela tibia o consume un dulce, chocolatina o bocadillo.\n4. **Abrigo rápido**: Colócate el forro polar y cortavientos para no perder calor corporal.\n5. **Avisa a tu guía**: Nunca continúes sintiéndote mal en solitario.",
      options: ["Contactos de emergencia", "¿Qué ropa llevar?", "Regulaciones ambientales"]
    },
    // 8. Regulaciones Ambientales y Ley de Páramos
    {
      id: "regulaciones",
      keywords: ["regulaciones", "normas", "reglas", "paramo", "frailejon", "frailejones", "basura", "residuos", "fogata", "fumar", "prohibido", "que esta prohibido", "ley 1930", "cuidar", "sanciones", "multas", "drones", "no deje rastro", "regulaciones del paramo", "normas del paramo", "reglas del paramo", "prohibiciones del paramo", "ley de paramos"],
      answer: "🌲 **REGULACIONES AMBIENTALES OFICIALES (LEY 1930 DE 2018):**\n\n1. **Protección a Frailejones**: Terminantemente prohibido pisar, arrancar o cortar frailejones y musgos. Crecen apenas 1 cm al año y destruirlos es delito ambiental.\n2. **Cero Basuras ('No Deje Rastro')**: Todo residuo o plástico debe regresar en tu mochila al pueblo.\n3. **Cero Fuego**: Prohibido hacer fogatas, hornillas o fumar en toda el área de reserva.\n4. **Patrimonio Muisca**: Prohibido rayar o tocar los petroglifos y pictogramas sagrados.\n5. **Drones**: Prohibidos sin autorización ambiental previa de Corpoboyacá.\n6. **Mascotas**: No permitidas en la zona de páramo por protección de fauna silvestre.",
      options: ["Primeros auxilios / Altura", "Contactos de emergencia", "Destinos de Mongua"]
    },
    // 9. Ropa y Equipo
    {
      id: "ropa_equipo",
      keywords: ["ropa", "que ropa llevar", "calzado", "botas", "frio", "chaqueta", "impermeable", "que llevar", "como vestir", "equipaje", "zapatos", "guantes", "gorro", "vestimenta", "capas"],
      answer: "🧥 **EQUIPO Y VESTIMENTA RECOMENDADA (CLIMA FRÍO 7°C A 16°C):**\n\n• **Sistema de 3 capas**:\n  1. Prenda térmica transpirable (pegada a la piel).\n  2. Forro polar o saco abrigado (abrigo térmico).\n  3. Chaqueta impermeable o cortavientos (protección contra viento y lluvia).\n• **Calzado**: Botas de trekking con suela antideslizante con buen agarre.\n• **Accesorios**: Gorro, guantes térmicos, protector solar ecológico y botella de agua reutilizable.",
      options: ["Regulaciones ambientales", "Primeros auxilios / Altura", "Punto de encuentro"]
    },
    // 10. Tours y Destinos
    {
      id: "tours_destinos",
      keywords: ["tours", "paquetes", "destinos", "que visitar", "oceta", "paramo de oceta", "laguna negra", "ciudad de piedra", "morro san pedro", "peña de oti", "atractivos", "caminatas", "senderismo", "ecoturismo", "que conocer", "lugares"],
      answer: "🗺️ **DESTINOS PRINCIPALES DE MONGUA:**\n\n• **Páramo de Ocetá**: Ciudad de Piedra, jardines de frailejones gigantes y cascadas cristalinas.\n• **Laguna Negra**: Espejo de agua místico de origen glaciar a más de 3.500 msnm.\n• **Morro de San Pedro y Peña de Otí**: Miradores panorámicos de alta montaña con arte rupestre Muisca.\n• **Senderos Arqueológicos**: Petroglifos ancestrales y caminos reales de la cultura Chibcha.",
      options: ["¿Cómo funciona la página?", "¿Qué precios tienen?", "Regulaciones ambientales"]
    },
    // 11. Precios y Tarifas
    {
      id: "precios_tarifas",
      keywords: ["precio", "precios", "costo", "costos", "cuanto vale", "cuanto cuesta", "tarifas", "valores", "cotizar", "cuanto cobran"],
      answer: "💰 **Tarifas y Precios de los Tours:**\n\nLas tarifas varían según el paquete turístico, la duración (días/noches), la temporada (alta o baja) y el número de personas (adultos y menores).\nTodos los paquetes incluyen **acompañamiento de guía certificado** y **póliza de seguro médico**. Puedes cotizar en tiempo real en la sección 'Destinos' (/tours/).",
      options: ["Temporadas alta vs baja", "¿Cómo reservar?", "¿Qué métodos de pago aceptan?"]
    },
    // 12. Temporadas
    {
      id: "temporadas",
      keywords: ["temporada", "temporadas", "temporada alta", "temporada baja", "festivos", "puentes", "vacaciones", "diferencia de temporada"],
      answer: "📅 **Manejo de Temporadas en Monagua:**\n\n• **Temporada Alta**: Fines de semana con puente festivo, Semana Santa, vacaciones de mitad de año y receso decembrino.\n• **Temporada Baja**: Resto del año, ideal para disfrutar de senderos despejados con tarifas preferenciales y descuentos especiales.\n\nEl sistema aplica la tarifa automáticamente según la fecha que elijas al reservar.",
      options: ["Ver promociones vigentes", "¿Cómo reservar?", "¿Qué métodos de pago aceptan?"]
    },
    // 13. Promociones y Descuentos
    {
      id: "promociones",
      keywords: ["promocion", "promociones", "descuento", "descuentos", "oferta", "ofertas", "cupon", "cupones", "codigo promocional"],
      answer: "🏷️ **Promociones y Descuentos:**\n\nMonagua ofrece descuentos en temporada baja y promociones por grupos. Si cuentas con un código de cupón, puedes ingresarlo al momento de confirmar tu reserva en el carrito de compras para obtener una rebaja directa sobre el valor total.",
      options: ["¿Cómo reservar?", "¿Qué tours ofrecen?", "¿Cómo realizar un pago?"]
    },
    // 14. Cómo Reservar
    {
      id: "como_reservar",
      keywords: ["como reservar", "reservar", "reserva", "reservas", "agendar", "apartar", "separar", "cupos", "booking", "pasos para reservar"],
      answer: "📝 **Pasos para Reservar tu Tour:**\n\n1. Ingresa a **Destinos** (/tours/) y selecciona el paquete deseado.\n2. Escoge la fecha y define la cantidad de adultos y menores (mínimo 1 adulto).\n3. Añade al carrito y confirma los detalles.\n4. Realiza la transferencia bancaria y carga el comprobante en **Enviar Comprobante** para confirmar tus cupos.",
      options: ["¿Cómo realizar el pago?", "Políticas de cancelación", "¿Qué ropa llevar?"]
    },
    // 15. Métodos de Pago y Comprobantes
    {
      id: "pagos",
      keywords: ["pago", "pagos", "como pagar", "como puedo pagar", "metodos de pago", "transferencia", "nequi", "daviplata", "bancolombia", "comprobante", "subir comprobante", "consignacion", "tarjeta", "pse"],
      answer: "💳 **Métodos de Pago y Comprobantes:**\n\nAceptamos transferencias bancarias (Bancolombia, Davivienda, etc.) y billeteras digitales (Nequi y Daviplata).\n\n**Procedimiento:**\n1. Realiza la transferencia por el monto de tu reserva.\n2. Ve a **Enviar Comprobante** (/pagos/enviar-comprobante/), selecciona tu reserva, digita el número de referencia y adjunta la captura.\n3. La administración valida el pago y tu reserva queda confirmada.",
      options: ["¿Cómo descargar mi factura?", "Políticas de cancelación", "¿Cómo funciona la página?"]
    },
    // 16. Facturas Electrónicas y QR
    {
      id: "facturas",
      keywords: ["factura", "facturas", "recibo", "descargar factura", "codigo qr", "qr", "comprobante de reserva", "pdf reserva", "factura legal"],
      answer: "📄 **Facturas Legales y Comprobantes con Código QR:**\n\nAl ser aprobado tu pago, el sistema genera de forma automática:\n• Tu **Factura Legal** con desglose de pasajeros, paquete y fecha.\n• Tu **Comprobante Oficial en PDF con Código QR** para verificación en campo por el guía.\nPuedes descargarlo desde **Mis Reservas** o **Mis Facturas**.",
      options: ["¿Cómo realizar el pago?", "¿Cómo reservar?", "Políticas de cancelación"]
    },
    // 17. Políticas de Cancelación y Reembolsos
    {
      id: "cancelacion_reembolsos",
      keywords: ["cancelar", "cancelacion", "politicas de cancelacion", "reembolso", "devolucion", "retracto", "anular reserva", "penalidad", "penalidades", "devolver dinero"],
      answer: "🔄 **Políticas de Cancelación y Reembolsos:**\n\nPuedes solicitar la cancelación desde tu cuenta en **Mis Reservas**:\n• **Más de 48 horas de anticipación**: Condiciones favorables de reprogramación o reembolso con penalidad mínima.\n• **Menos de 24 horas**: Aplican penalidades por logística y pólizas ya expedidas.\n• **Desembolso**: Tras aprobación, la administración realiza la transferencia bancaria (Nequi, Daviplata o banco) y adjunta el comprobante bancario visible en 'Mis Reembolsos'.",
      options: ["¿Qué es una nota de crédito?", "¿Cómo funciona la página?", "Contactos de emergencia"]
    },
    // 18. Notas de Crédito y Saldo a Favor
    {
      id: "notas_credito_saldo",
      keywords: ["nota de credito", "notas de credito", "saldo a favor", "mi saldo", "monedero", "saldo disponible", "credito en cuenta"],
      answer: "💵 **Notas de Crédito y Saldo a Favor:**\n\nCuando reduces cupos o cancelas una reserva dentro de los plazos establecidos, el sistema emite una **Nota de Crédito** contable. Ese importe se acredita como **Saldo a Favor** en tu perfil para adquirir nuevos tours sin volver a transferir dinero o para tramitar tu reembolso.",
      options: ["Políticas de cancelación", "¿Cómo reservar?", "Ver mi perfil"]
    },
    // 19. Modificar Personas en Reserva
    {
      id: "modificar_personas",
      keywords: ["modificar reserva", "cambiar personas", "reducir personas", "menos personas", "agregar personas", "cambiar fecha", "bajar cupos"],
      answer: "✏️ **Modificación de Cupos de Reserva:**\n\nEn **Mis Reservas** puedes gestionar cambios. Si necesitas reducir personas en una reserva pagada, el sistema liquida la diferencia y emite una Nota de Crédito para que conserves el saldo a favor o solicites devolución bancaria.",
      options: ["Notas de crédito y saldo", "Políticas de cancelación", "Enviar comprobante"]
    },
    // 20. Registro y Validación OTP
    {
      id: "registro_cuenta_otp",
      keywords: ["como registrarme", "registrarse", "registro", "crear cuenta", "codigo otp", "otp", "iniciar sesion", "login", "recuperar clave", "olvide contraseña", "cambiar clave"],
      answer: "🔐 **Registro Seguro y Validación con Código OTP:**\n\n• **Registro**: Ingresa tus datos personales (validación en tiempo real). Para garantizar la autenticidad, te enviamos un código OTP (de un solo uso) a tu correo para activar la cuenta.\n• **Recuperación**: Si olvidas tu clave o usuario, puedes restablecerla desde la pantalla de login con tu correo registrado.",
      options: ["¿Cómo funciona la página?", "Ver destinos", "Radicar PQRS"]
    },
    // 21. Guías Turísticos
    {
      id: "guias",
      keywords: ["guia", "guias", "guia turistico", "guia certificado", "sena", "quien nos guia", "por que se exige guia", "acompañante"],
      answer: "🧗 **Guías Turísticos Certificados:**\n\nTodos los recorridos son guiados por profesionales locales acreditados por el **SENA** e inscritos en el **Registro Nacional de Turismo (RNT)**. Cuentan con formación en rescate, primeros auxilios, conocimiento de flora y respeto por el patrimonio Muisca. Por regulación ambiental y seguridad en niebla, no se permite subir al páramo sin guía.",
      options: ["Regulaciones ambientales", "Póliza médica", "Destinos de Mongua"]
    },
    // 22. Seguro y Póliza Médica
    {
      id: "seguro_poliza",
      keywords: ["seguro", "seguros", "poliza", "polizas", "asistencia medica", "seguro de viaje", "accidente", "cobertura", "aseguradora", "rescate"],
      answer: "🛡️ **Póliza de Asistencia Médica Incluida:**\n\nCada paquete confirmado en Monagua incluye una póliza de asistencia médica y seguro de viaje emitida con aseguradoras autorizadas. Cubre gastos médicos de urgencia, rescate en montaña y accidentes personales durante toda la duración de la expedición.",
      options: ["Primeros auxilios / Altura", "¿Qué ropa llevar?", "¿Cómo reservar?"]
    },
    // 23. Ubicación y Cómo Llegar
    {
      id: "ubicacion_transporte",
      keywords: ["donde estan", "ubicacion", "donde queda mongua", "como llegar", "transporte", "bus", "flota", "terminal", "sogamoso", "bogota", "tunja", "punto de encuentro", "parque"],
      answer: "📍 **Ubicación y Cómo Llegar a Mongua:**\n\n• **Ubicación**: Mongua, Boyacá (a 35-40 min de Sogamoso por vía pavimentada).\n• **Punto de Encuentro**: Parque Principal de Mongua frente al templo parroquial.\n• **Desde Bogotá**: Tomas autobús en la Terminal del Salitre/Norte hasta la Terminal de Sogamoso (~3h30). Desde allí salen busetas continuas hacia Mongua cada 20 minutos.",
      options: ["Horarios de salida", "Destinos de Mongua", "¿Qué ropa llevar?"]
    },
    // 24. Mascotas
    {
      id: "mascotas",
      keywords: ["mascota", "mascotas", "perro", "perros", "gato", "gatos", "animales", "puedo llevar mi perro"],
      answer: "🐾 **Regulación sobre Mascotas:**\n\nLas mascotas son bienvenidas en las rutas culturales urbanas y senderos campestres bajos de Mongua. Sin embargo, en la **zona de reserva estricta del Páramo de Ocetá está prohibido el ingreso de mascotas** por regulación ambiental para proteger a los frailejones y evitar alterar la fauna silvestre nativa.",
      options: ["Regulaciones ambientales", "Destinos de Mongua", "¿Cómo reservar?"]
    },
    // 25. Gastronomía
    {
      id: "comida",
      keywords: ["comida", "comidas", "restaurante", "donde comer", "platos tipicos", "arepas", "arepas monguanas", "almuerzo", "trucha", "gastronomia", "que comer"],
      answer: "🍲 **Gastronomía Tradicional en Mongua:**\n\nPodrás deleitarte con las famosas **arepas monguanas de maíz pelado** horneadas en tiesto de barro, caldo campesino de papa, trucha fresca y agua de panela con queso campesino. Para la caminata recomendamos portar bocadillos veleños, frutos secos y chocolatinas.",
      options: ["Punto de encuentro", "¿Qué ropa llevar?", "Destinos de Mongua"]
    },
    // 26. Artesanías
    {
      id: "artesanias",
      keywords: ["artesanias", "recuerdos", "souvenirs", "lana", "ruanas", "fique", "artesanos", "compras"],
      answer: "🧶 **Artesanías Tradicionales de Mongua:**\n\nMongua es célebre por sus tejedores de lana virgen de oveja, ruanas boyacenses auténticas, cobijas campesinas y canastos en fibra de fique. En el casco urbano encontrarás talleres artesanales donde apoyar directamente la economía local campesina.",
      options: ["Punto de encuentro", "Ubicación y transporte", "¿Cómo funciona la página?"]
    },
    // 27. Radicación de PQRS
    {
      id: "pqrs",
      keywords: ["pqrs", "pqr", "queja", "quejas", "reclamo", "reclamos", "peticion", "sugerencia", "radicar pqrs", "poner queja", "inconformidad", "ticket"],
      answer: "📬 **Radicación de PQRS (Peticiones, Quejas y Reclamos):**\n\nMonagua cuenta con un módulo formal de PQRS (/pqrs/). Al radicar tu solicitud, se genera un número de radicado oficial con el cual podrás hacer seguimiento y recibir respuesta institucional de la administración.",
      options: ["¿Cómo funciona la página?", "Políticas de cancelación", "Contactos de emergencia"]
    },
    // 28. Horarios
    {
      id: "horarios",
      keywords: ["horario", "horarios", "a que hora", "cuando abren", "atencion", "salidas", "hora de salida"],
      answer: "⏰ **Horarios de Salida y Atención:**\n\n• **Atención Web y Soporte**: Lunes a Domingo de 8:00 AM a 6:00 PM.\n• **Salidas de Expedición en Campo**: Entre 6:00 AM y 7:00 AM desde el Parque Principal de Mongua para aprovechar la mayor estabilidad climática del páramo.",
      options: ["Punto de encuentro", "¿Qué ropa llevar?", "Contactos de emergencia"]
    }
  ];

  function normalizarTextoLocal(str) {
    if (!str) return '';
    return str
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function responderOffline(userText) {
    const textoNorm = normalizarTextoLocal(userText);
    let mejorMatch = null;
    let mejorPuntaje = 0;

    for (const faq of OFFLINE_FAQS) {
      let puntaje = 0;
      for (const kw of faq.keywords) {
        const kwNorm = normalizarTextoLocal(kw);
        if (!kwNorm) continue;
        
        if (kwNorm.includes(' ')) {
          if (textoNorm.includes(kwNorm)) {
            puntaje += 6; // Frase exacta multi-palabra prioritaria
          }
        } else {
          const regex = new RegExp('\\b' + kwNorm + '\\b', 'i');
          if (regex.test(textoNorm)) {
            puntaje += 2;
          }
        }
      }
      if (puntaje > mejorPuntaje) {
        mejorPuntaje = puntaje;
        mejorMatch = faq;
      }
    }

    if (mejorMatch && mejorPuntaje >= 2) {
      addMessage("📶 *[Modo Fuera de Línea / Offline]*\n\n" + mejorMatch.answer, "bot");
      if (mejorMatch.options && mejorMatch.options.length > 0) {
        showOptions(mejorMatch.options);
      }
    } else {
      addMessage(
        "📶 **[Cóndy en Modo Local Autónomo - Sin Internet]**\n\nNo fue posible consultar el servidor web (sin conexión a internet detectada o simulación activa), pero tengo cargada en tu navegador la base completa de conocimientos de Monagua Turismo.\n\nPuedes consultarme sobre:\n• 🌲 **Regulaciones del Páramo (Ley 1930)**\n• 💻 **¿Cómo funciona la página? y Roles**\n• ⛰️ **Primeros auxilios / Mal de altura (Soroche)**\n• 🧥 **Ropa y clima frío de montaña**\n• 🗺️ **Tours, atractivos y precios**\n• 💳 **Proceso de pago y reservas**\n• 🚨 **Teléfonos de emergencia y rescate**",
        "bot"
      );
      showOptions([
        "¿Cómo funciona la página?",
        "Regulaciones ambientales",
        "Primeros auxilios / Altura",
        "¿Qué tours ofrecen?"
      ]);
    }
  }

  function handleSend() {
    const text = input.value.trim();
    if (!text) return;
    
    input.value = "";
    btnSend.disabled = true;
    hideOptions();
    
    addMessage(text, "user");
    showTypingIndicator();

    // Verificación proactiva de conexión: Si el navegador no tiene internet o si está activada la simulación offline para presentaciones
    if (!navigator.onLine || forzarModoOffline) {
      setTimeout(() => {
        removeTypingIndicator();
        responderOffline(text);
      }, 250);
      return;
    }
    
    // Llamada al backend
    fetch('/api/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken') // Obtener token CSRF
      },
      body: JSON.stringify({ message: text })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error('Servidor no disponible (HTTP ' + response.status + ')');
      }
      return response.json();
    })
    .then(data => {
      removeTypingIndicator();
      actualizarEstadoConexion(true);
      if (data.response) {
        addMessage(data.response, "bot");
      }
      if (data.link_url && data.link_text) {
        showCustomLink(data.link_url, data.link_text);
      }
      if (data.options && data.options.length > 0) {
        showOptions(data.options);
      }
      if (data.fallback_action === 'ticket' || data.fallback_action === 'pqrs' || data.action === 'pqrs') {
        showFallbackOption();
      }
    })
    .catch(error => {
      removeTypingIndicator();
      console.warn('Falla de red detectada. Activando motor local offline de emergencia:', error);
      actualizarEstadoConexion(false);
      responderOffline(text);
    });
  }

  function formatText(text) {
    if (!text) return '';
    let formatted = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Negritas **texto**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Cursiva *texto*
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Código en línea `codigo`
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="bg-light px-1 rounded text-dark">$1</code>');
    // Saltos de línea
    formatted = formatted.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');

    return formatted;
  }

  function addMessage(text, sender, save = true) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${sender}`;
    bubble.innerHTML = formatText(text);
    messagesContainer.appendChild(bubble);
    scrollToBottom();
    
    if (save) {
        saveToHistory({ type: 'message', text: text, sender: sender });
    }
  }

  function showOptions(options, save = true) {
    optionsContainer.innerHTML = '';
    options.forEach(opt => {
      const btn = document.createElement('button');
      btn.className = 'chat-option-btn';
      btn.innerText = opt;
      btn.addEventListener('click', () => {
        input.value = opt;
        btnSend.disabled = false;
        handleSend();
      });
      optionsContainer.appendChild(btn);
    });
    optionsContainer.classList.remove('d-none');
    optionsContainer.classList.add('d-flex');
    scrollToBottom();
    
    if (save) {
        saveToHistory({ type: 'options', options: options });
    }
  }

  function hideOptions() {
    optionsContainer.classList.add('d-none');
    optionsContainer.classList.remove('d-flex');
  }

  function showTypingIndicator() {
    const typing = document.createElement('div');
    typing.id = 'condy-typing';
    typing.className = 'condy-typing-indicator';
    typing.innerHTML = '<div class="condy-typing-dot"></div><div class="condy-typing-dot"></div><div class="condy-typing-dot"></div>';
    messagesContainer.appendChild(typing);
    scrollToBottom();
  }

  function removeTypingIndicator() {
    const typing = document.getElementById('condy-typing');
    if (typing) {
      typing.remove();
    }
  }

  function showCustomLink(url, text, save = true) {
    const div = document.createElement('div');
    div.className = 'mt-2 mb-2 d-flex flex-wrap gap-2 justify-content-start';
    div.innerHTML = `
      <a href="${url}" class="btn btn-sm btn-success rounded-pill px-3 shadow-sm d-inline-flex align-items-center gap-1" style="background-color: #2c6e3c; color: #fff; font-weight: 600; text-decoration: none;">
        <i class="bi bi-box-arrow-up-right"></i> ${text}
      </a>
    `;
    messagesContainer.appendChild(div);
    scrollToBottom();
    if (save) {
      saveToHistory({ type: 'custom_link', url: url, text: text });
    }
  }

  function showFallbackOption(save = true) {
    const div = document.createElement('div');
    div.className = 'mt-2 mb-2 d-flex flex-wrap gap-2 justify-content-start';
    div.innerHTML = `
      <a href="/pqrs/" class="btn btn-sm btn-success rounded-pill px-3 shadow-sm d-inline-flex align-items-center gap-1" style="background-color: #2c6e3c; color: #fff; font-weight: 600; text-decoration: none;">
        <i class="bi bi-pencil-square"></i> Radicar PQRS
      </a>
      <a href="/mis_pqrs/" class="btn btn-sm btn-outline-success rounded-pill px-3 shadow-sm d-inline-flex align-items-center gap-1" style="border-color: #2c6e3c; color: #2c6e3c; font-weight: 600; text-decoration: none;">
        <i class="bi bi-inbox"></i> Mis Solicitudes
      </a>
    `;
    messagesContainer.appendChild(div);
    scrollToBottom();
    
    if (save) {
        saveToHistory({ type: 'fallback' });
    }
  }

  function scrollToBottom() {
    setTimeout(() => {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 50);
  }

  // Función auxiliar para CSRF Token en Django
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
});
