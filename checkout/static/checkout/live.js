(function initLiveCheckout() {
  if (window.smartCheckoutLiveInitialized) return;
  window.smartCheckoutLiveInitialized = true;

  const FRAME_WIDTH = 640;
  const FRAME_HEIGHT = 480;
  const SEND_INTERVAL_MS = 650;
  const JPEG_QUALITY = 0.78;

  const cameraSelect = document.getElementById("cameraSelect");
  const refreshCameras = document.getElementById("refreshCameras");
  const startCameraButton = document.getElementById("startCamera");
  const stopCameraButton = document.getElementById("stopCamera");
  const video = document.getElementById("cameraVideo");
  const frameCanvas = document.getElementById("frameCanvas");
  const overlayCanvas = document.getElementById("overlayCanvas");
  const liveStatus = document.getElementById("liveStatus");
  const fpsValue = document.getElementById("fpsValue");
  const latencyValue = document.getElementById("latencyValue");
  const detectionsCount = document.getElementById("detectionsCount");
  const detectionsList = document.getElementById("detectionsList");
  const autoAddMode = document.getElementById("autoAddMode");
  const addDetections = document.getElementById("addDetections");
  const clearCart = document.getElementById("clearCart");
  const cartList = document.getElementById("cartList");
  const cartTotal = document.getElementById("cartTotal");
  const paymentMethod = document.getElementById("paymentMethod");
  const confirmSale = document.getElementById("confirmSale");
  const saleStatus = document.getElementById("saleStatus");
  const salesHistory = document.getElementById("salesHistory");

  const frameCtx = frameCanvas.getContext("2d");
  const overlayCtx = overlayCanvas.getContext("2d");
  const addSound = new Audio("/static/checkout/sounds/cash-register.mp3");

  let stream = null;
  let sendTimer = null;
  let renderLoopId = null;
  let inferenceInFlight = false;
  let lastDetections = [];
  let lastFrameWidth = FRAME_WIDTH;
  let lastFrameHeight = FRAME_HEIGHT;
  let cart = [];
  let tracks = [];
  let nextTrackId = 1;
  let frames = 0;
  let fpsStartedAt = performance.now();

  function money(value, currency = "COP") {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency,
      maximumFractionDigits: currency === "COP" ? 0 : 2,
    }).format(Number(value || 0));
  }

  function setStatus(text) {
    liveStatus.textContent = text;
  }

  async function loadCameras() {
    if (!navigator.mediaDevices?.enumerateDevices) {
      setStatus("camara no soportada");
      return;
    }
    const devices = await navigator.mediaDevices.enumerateDevices();
    const cameras = devices.filter((device) => device.kind === "videoinput");
    cameraSelect.innerHTML = cameras.map((camera, index) => {
      return `<option value="${camera.deviceId}">${camera.label || `Camara ${index + 1}`}</option>`;
    }).join("");
  }

  async function startCamera() {
    stopCamera();
    const deviceId = cameraSelect.value;
    stream = await navigator.mediaDevices.getUserMedia({
      video: deviceId ? {
        deviceId: { exact: deviceId },
        width: { ideal: FRAME_WIDTH },
        height: { ideal: FRAME_HEIGHT },
      } : {
        width: { ideal: FRAME_WIDTH },
        height: { ideal: FRAME_HEIGHT },
      },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
    setStatus("camara activa");
    drawFrameLoop();
    scheduleInference(100);
    await loadCameras();
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = null;
    }
    video.srcObject = null;
    if (sendTimer) window.clearTimeout(sendTimer);
    if (renderLoopId) window.cancelAnimationFrame(renderLoopId);
    sendTimer = null;
    renderLoopId = null;
    inferenceInFlight = false;
    lastDetections = [];
    tracks = [];
    clearCanvas();
    renderDetections();
    setStatus("detenido");
  }

  function drawFrameLoop() {
    drawFrame();
    drawOverlay();
    renderLoopId = window.requestAnimationFrame(drawFrameLoop);
  }

  function drawFrame() {
    frameCtx.fillStyle = "#101820";
    frameCtx.fillRect(0, 0, FRAME_WIDTH, FRAME_HEIGHT);
    if (!video.videoWidth || !video.videoHeight) return;

    const scale = Math.min(FRAME_WIDTH / video.videoWidth, FRAME_HEIGHT / video.videoHeight);
    const drawWidth = video.videoWidth * scale;
    const drawHeight = video.videoHeight * scale;
    const drawX = (FRAME_WIDTH - drawWidth) / 2;
    const drawY = (FRAME_HEIGHT - drawHeight) / 2;
    frameCtx.drawImage(video, drawX, drawY, drawWidth, drawHeight);
  }

  function drawOverlay() {
    overlayCtx.clearRect(0, 0, FRAME_WIDTH, FRAME_HEIGHT);
    overlayCtx.lineWidth = 3;
    overlayCtx.font = "15px Arial";

    lastDetections.forEach((detection) => {
      const box = detection.bbox || [];
      if (box.length !== 4) return;
      const scaleX = FRAME_WIDTH / (lastFrameWidth || FRAME_WIDTH);
      const scaleY = FRAME_HEIGHT / (lastFrameHeight || FRAME_HEIGHT);
      const [x1, y1, x2, y2] = box;
      const sx1 = x1 * scaleX;
      const sy1 = y1 * scaleY;
      const sx2 = x2 * scaleX;
      const sy2 = y2 * scaleY;
      const label = detection.product?.name || detection.class_name || "Producto";
      overlayCtx.strokeStyle = "#20c997";
      overlayCtx.fillStyle = "#20c997";
      overlayCtx.strokeRect(sx1, sy1, sx2 - sx1, sy2 - sy1);
      const labelY = Math.max(20, sy1 - 8);
      const labelWidth = overlayCtx.measureText(label).width + 12;
      overlayCtx.fillRect(sx1, labelY - 17, labelWidth, 21);
      overlayCtx.fillStyle = "#071216";
      overlayCtx.fillText(label, sx1 + 6, labelY - 2);
    });
  }

  function clearCanvas() {
    frameCtx.fillStyle = "#101820";
    frameCtx.fillRect(0, 0, FRAME_WIDTH, FRAME_HEIGHT);
    overlayCtx.clearRect(0, 0, FRAME_WIDTH, FRAME_HEIGHT);
  }

  function scheduleInference(delay = SEND_INTERVAL_MS) {
    if (sendTimer) window.clearTimeout(sendTimer);
    sendTimer = window.setTimeout(sendFrame, delay);
  }

  async function sendFrame() {
    sendTimer = null;
    if (!stream || inferenceInFlight || !video.videoWidth) {
      scheduleInference();
      return;
    }
    inferenceInFlight = true;
    setStatus("analizando frame");

    const image = frameCanvas.toDataURL("image/jpeg", JPEG_QUALITY);
    try {
      const response = await fetch("/api/detect-frame/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify({ image }),
      });
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.error || "Error de inferencia");

      lastDetections = result.detections || [];
      lastFrameWidth = result.frame_width || FRAME_WIDTH;
      lastFrameHeight = result.frame_height || FRAME_HEIGHT;
      updateTrackedDetections(lastDetections);
      detectionsCount.textContent = String(lastDetections.length);
      latencyValue.textContent = `${Math.round(result.latency_ms || 0)} ms`;
      renderDetections();
      updateFps();
      setStatus(lastDetections.length ? "producto detectado" : "sin detecciones");
    } catch (error) {
      setStatus(error.message || "error");
    } finally {
      inferenceInFlight = false;
      scheduleInference();
    }
  }

  function updateFps() {
    frames += 1;
    const elapsed = (performance.now() - fpsStartedAt) / 1000;
    if (elapsed >= 1) {
      fpsValue.textContent = String(Math.round(frames / elapsed));
      frames = 0;
      fpsStartedAt = performance.now();
    }
  }

  function renderDetections() {
      if (!lastDetections.length) {
      detectionsList.innerHTML = `<div class="empty-box">Sin detecciones.</div>`;
      return;
    }
    detectionsList.innerHTML = lastDetections.map((detection) => {
      const product = detection.product;
      const price = product ? money(product.price, product.currency || "COP") : "Sin producto";
      const confirmation = product && detection.auto_add === false
        ? `<span class="warning-text">${detection.auto_add_reason || "Requiere confirmacion manual"}</span>`
        : "";
      return `
        <div class="live-item">
          <strong>${product ? product.name : detection.class_name}</strong>
          <span>Confianza: ${(Number(detection.confidence || 0) * 100).toFixed(1)}%</span>
          <span>${price}</span>
          ${confirmation}
        </div>
      `;
    }).join("");
  }

  function updateTrackedDetections(detections) {
    tracks.forEach((track) => {
      track.missing += 1;
    });

    detections.forEach((detection) => {
      if (!detection.product || !Array.isArray(detection.bbox)) return;

      let bestTrack = null;
      let bestScore = 0;
      tracks.forEach((track) => {
        if (track.productId !== detection.product.id) return;
        const score = iou(track.bbox, detection.bbox);
        if (score > bestScore) {
          bestScore = score;
          bestTrack = track;
        }
      });

      if (bestTrack && bestScore >= 0.18) {
        bestTrack.bbox = detection.bbox;
        bestTrack.confidence = detection.confidence || bestTrack.confidence;
        bestTrack.missing = 0;
        return;
      }

      const track = {
        id: nextTrackId++,
        productId: detection.product.id,
        bbox: detection.bbox,
        confidence: detection.confidence || 0,
        missing: 0,
      };
      tracks.push(track);
      if (isAutoAddEnabled() && detection.auto_add !== false) {
        addDetectionToCart(detection);
      }
    });

    tracks = tracks.filter((track) => track.missing < 10);
  }

  function iou(a, b) {
    if (!Array.isArray(a) || !Array.isArray(b) || a.length !== 4 || b.length !== 4) return 0;
    const x1 = Math.max(a[0], b[0]);
    const y1 = Math.max(a[1], b[1]);
    const x2 = Math.min(a[2], b[2]);
    const y2 = Math.min(a[3], b[3]);
    const interW = Math.max(0, x2 - x1);
    const interH = Math.max(0, y2 - y1);
    const inter = interW * interH;
    const areaA = Math.max(0, a[2] - a[0]) * Math.max(0, a[3] - a[1]);
    const areaB = Math.max(0, b[2] - b[0]) * Math.max(0, b[3] - b[1]);
    const union = areaA + areaB - inter;
    return union <= 0 ? 0 : inter / union;
  }

  function addDetectionToCart(detection) {
    const product = detection.product;
    if (!product) return;
    const existing = cart.find((item) => item.product_id === product.id);
    if (existing) {
      existing.quantity += 1;
      existing.total = existing.quantity * existing.unit_price;
      existing.confidence = Math.max(existing.confidence, detection.confidence || 0);
      existing.bbox = detection.bbox || [];
    } else {
      cart.push({
        product_id: product.id,
        product_name: product.name,
        quantity: 1,
        unit_price: Number(product.price || 0),
        currency: product.currency || "COP",
        total: Number(product.price || 0),
        confidence: Number(detection.confidence || 0),
        bbox: detection.bbox || [],
      });
    }
    renderCart();
    playAddSound();
    setStatus(`${product.name} agregado al carrito`);
  }

  function isAutoAddEnabled() {
    return !autoAddMode || autoAddMode.checked;
  }

  function addCurrentDetectionsToCart() {
    const productDetections = lastDetections.filter((detection) => detection.product);
    if (!productDetections.length) {
      setStatus("no hay productos para agregar");
      return;
    }
    productDetections.forEach((detection) => addDetectionToCart(detection));
    setStatus(`${productDetections.length} deteccion(es) agregada(s) manualmente`);
  }

  function playAddSound() {
    addSound.currentTime = 0;
    addSound.play().catch(() => {});
  }

  function renderCart() {
    if (!cart.length) {
      cartList.innerHTML = `<div class="empty-box">Carrito vacio.</div>`;
      cartTotal.textContent = money(0, "COP");
      return;
    }
    let total = 0;
    cartList.innerHTML = cart.map((item) => {
      total += item.total;
      return `
        <div class="live-item cart-line" data-product-id="${item.product_id}">
          <div class="cart-line-main">
            <div>
              <strong>${item.product_name}</strong>
              <span>${item.quantity} x ${money(item.unit_price, item.currency)}</span>
            </div>
            <strong>${money(item.total, item.currency)}</strong>
          </div>
          <div class="cart-controls">
            <button class="secondary-button" type="button" data-action="decrease">-</button>
            <strong>${item.quantity}</strong>
            <button class="secondary-button" type="button" data-action="increase">+</button>
            <button class="danger-button" type="button" data-action="remove">Eliminar</button>
          </div>
        </div>
      `;
    }).join("");
    cartTotal.textContent = money(total, cart[0]?.currency || "COP");
  }

  function changeCartQuantity(productId, action) {
    const item = cart.find((entry) => entry.product_id === productId);
    if (!item) return;

    if (action === "increase") {
      item.quantity += 1;
    } else if (action === "decrease") {
      item.quantity -= 1;
    } else if (action === "remove") {
      item.quantity = 0;
    }

    if (item.quantity <= 0) {
      cart = cart.filter((entry) => entry.product_id !== productId);
      setStatus(`${item.product_name} eliminado del carrito`);
    } else {
      item.total = item.quantity * item.unit_price;
      setStatus(`${item.product_name}: cantidad ${item.quantity}`);
    }

    renderCart();
  }

  async function submitSale() {
    if (!cart.length) {
      saleStatus.textContent = "No hay productos para confirmar.";
      return;
    }
    confirmSale.disabled = true;
    saleStatus.textContent = "Registrando venta...";
    try {
      const response = await fetch("/api/confirm-live-sale/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify({ items: cart, payment_method: paymentMethod.value }),
      });
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.error || "No se pudo registrar.");
      saleStatus.textContent = `Venta #${result.sale.id} registrada.`;
      cart = [];
      renderCart();
      await refreshSalesHistory();
    } catch (error) {
      saleStatus.textContent = error.message || "Error al confirmar.";
    } finally {
      confirmSale.disabled = false;
    }
  }

  async function refreshSalesHistory() {
    const response = await fetch("/api/sales-history/");
    const result = await response.json();
    if (!result.success) return;
    salesHistory.innerHTML = result.sales.length ? result.sales.map((sale) => {
      const items = (sale.items || []).map((item) => `${item.product_name} x${item.quantity}`).join(", ");
      return `
        <tr>
          <td>#${sale.id}</td>
          <td>${sale.payment_method}</td>
          <td>${money(sale.total, sale.currency || "COP")}</td>
          <td>${new Date(sale.created_at).toLocaleString("es-CO")}</td>
          <td>${items}</td>
        </tr>
      `;
    }).join("") : `<tr><td colspan="5">Sin ventas.</td></tr>`;
  }

  refreshCameras.addEventListener("click", loadCameras);
  startCameraButton.addEventListener("click", startCamera);
  stopCameraButton.addEventListener("click", stopCamera);
  if (addDetections) {
    addDetections.addEventListener("click", addCurrentDetectionsToCart);
  }
  if (autoAddMode) {
    autoAddMode.addEventListener("change", () => {
      setStatus(autoAddMode.checked ? "auto agregado activo" : "auto agregado pausado");
    });
  }
  cartList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const row = button.closest("[data-product-id]");
    if (!row) return;
    changeCartQuantity(Number(row.dataset.productId), button.dataset.action);
  });
  clearCart.addEventListener("click", () => {
    cart = [];
    tracks = [];
    renderCart();
  });
  confirmSale.addEventListener("click", submitSale);
  window.addEventListener("beforeunload", stopCamera);

  clearCanvas();
  renderDetections();
  renderCart();
  loadCameras();
  refreshSalesHistory();
})();
