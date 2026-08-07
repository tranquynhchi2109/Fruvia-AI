/**
 * Fruvia AI — Fruit Classification UI Logic
 */
document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const dropzonePrompt = document.getElementById("dropzone-prompt");
  const previewContainer = document.getElementById("preview-container");
  const previewImg = document.getElementById("preview-img");
  const btnChangeImage = document.getElementById("btn-change-image");
  const btnRemoveImage = document.getElementById("btn-remove-image");

  const topKSlider = document.getElementById("top-k-slider");
  const topKDisplay = document.getElementById("top-k-display");

  const btnClassify = document.getElementById("btn-classify");
  const classifyText = document.getElementById("classify-text");
  const classifySpinner = document.getElementById("classify-spinner");

  const backendStatusBadge = document.getElementById("backend-status");
  const statusText = document.getElementById("status-text");

  const errorBannerContainer = document.getElementById("error-banner-container");
  const initialEmptyState = document.getElementById("initial-empty-state");
  const predictionCardContainer = document.getElementById("prediction-card-container");
  const predictionsListContainer = document.getElementById("predictions-list-container");
  const predictionsList = document.getElementById("predictions-list");
  const resultQueryImg = document.getElementById("result-query-img");

  const topClassName = document.getElementById("top-class-name");
  const topConfidenceValue = document.getElementById("top-confidence-value");
  const topConfidenceFill = document.getElementById("top-confidence-fill");
  const acceptedBadge = document.getElementById("accepted-badge");
  const resultStatusMsg = document.getElementById("result-status-msg");
  const metaTimingInfo = document.getElementById("meta-timing-info");

  // State Variables
  let selectedFile = null;
  let queryDataUrl = null;
  let isClassifying = false;

  // ---------- Health Check Polling ----------
  async function checkBackendHealth() {
    try {
      const health = await ApiClient.getHealth();
      if (health.status === "ok") {
        backendStatusBadge.setAttribute("data-status", "online");
        statusText.textContent = "Backend Trực tuyến (Trained Model)";
      } else if (health.status === "degraded") {
        backendStatusBadge.setAttribute("data-status", "degraded");
        const method = health.classification ? health.classification.inference_method : "kNN Fallback";
        statusText.textContent = `Backend Giảm chất lượng (${method})`;
      } else {
        backendStatusBadge.setAttribute("data-status", "offline");
        statusText.textContent = "Backend Ngoại tuyến";
      }
    } catch (err) {
      backendStatusBadge.setAttribute("data-status", "offline");
      statusText.textContent = "Backend Ngoại tuyến";
    }
  }

  checkBackendHealth();
  setInterval(checkBackendHealth, CONFIG.HEALTH_CHECK_INTERVAL_MS);

  // ---------- File Selection & Drag-and-Drop & Paste ----------
  function handleFileSelected(file) {
    if (!file) return;

    if (file.size > CONFIG.MAX_UPLOAD_BYTES) {
      showErrorBanner(
        "File quá lớn",
        `Hình ảnh đã chọn (${(file.size / (1024 * 1024)).toFixed(1)} MB) vượt quá giới hạn 10 MB.`
      );
      return;
    }

    const ext = file.name && file.name.includes(".") ? "." + file.name.split(".").pop().toLowerCase() : "";
    const isValidExt = CONFIG.ALLOWED_EXTENSIONS.includes(ext);
    const isValidMime = CONFIG.ALLOWED_MIME_TYPES.includes(file.type);

    if (!isValidExt && !isValidMime) {
      showErrorBanner(
        "Định dạng không hỗ trợ",
        `Định dạng file không được hỗ trợ. Vui lòng chọn hoặc dán ảnh JPG, PNG, hoặc WEBP.`
      );
      return;
    }

    clearBanners();
    selectedFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
      queryDataUrl = e.target.result;
      previewImg.src = queryDataUrl;
      dropzonePrompt.style.display = "none";
      previewContainer.style.display = "flex";
      btnClassify.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  function clearSelectedFile() {
    selectedFile = null;
    queryDataUrl = null;
    fileInput.value = "";
    previewImg.src = "";
    previewContainer.style.display = "none";
    dropzonePrompt.style.display = "block";
    btnClassify.disabled = true;
    predictionCardContainer.style.display = "none";
    predictionsListContainer.style.display = "none";
    clearBanners();
  }

  dropzone.addEventListener("click", (e) => {
    if (e.target !== btnChangeImage && e.target !== btnRemoveImage && !previewContainer.contains(e.target)) {
      fileInput.click();
    }
  });

  dropzone.addEventListener("keydown", (e) => {
    if ((e.key === "Enter" || e.key === " ") && e.target === dropzone) {
      e.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  });

  btnChangeImage.addEventListener("click", (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  btnRemoveImage.addEventListener("click", (e) => {
    e.stopPropagation();
    clearSelectedFile();
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files[0]) {
      handleFileSelected(dt.files[0]);
    }
  });

  document.addEventListener("paste", (e) => {
    const clipboardData = e.clipboardData;
    if (!clipboardData) return;

    if (clipboardData.files && clipboardData.files.length > 0) {
      for (let i = 0; i < clipboardData.files.length; i++) {
        const file = clipboardData.files[i];
        if (file.type.startsWith("image/")) {
          handleFileSelected(file);
          e.preventDefault();
          return;
        }
      }
    }

    const items = clipboardData.items;
    if (items && items.length > 0) {
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) {
            let finalFile = file;
            if (!file.name || !file.name.match(/\.(jpg|jpeg|png|webp)$/i)) {
              const extMap = { "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp" };
              const ext = extMap[file.type] || ".png";
              const name = `pasted_image_${Date.now()}${ext}`;
              finalFile = new File([file], name, { type: file.type || "image/png" });
            }
            handleFileSelected(finalFile);
            e.preventDefault();
            return;
          }
        }
      }
    }
  });

  topKSlider.addEventListener("input", (e) => {
    topKDisplay.textContent = e.target.value;
  });

  function showErrorBanner(title, message) {
    errorBannerContainer.innerHTML = "";
    const banner = document.createElement("div");
    banner.className = "alert-banner alert-banner-error";
    banner.setAttribute("role", "alert");

    const icon = document.createElement("span");
    icon.className = "alert-icon";
    icon.textContent = "⚠️";

    const content = document.createElement("div");
    content.className = "alert-content";

    const h4 = document.createElement("h4");
    h4.textContent = title;

    const p = document.createElement("p");
    p.textContent = message;

    content.appendChild(h4);
    content.appendChild(p);
    banner.appendChild(icon);
    banner.appendChild(content);
    errorBannerContainer.appendChild(banner);
    errorBannerContainer.style.display = "block";
  }

  function clearBanners() {
    errorBannerContainer.innerHTML = "";
    errorBannerContainer.style.display = "none";
  }

  // ---------- Classification Action ----------
  btnClassify.addEventListener("click", async () => {
    if (!selectedFile || isClassifying) return;

    isClassifying = true;
    btnClassify.disabled = true;
    classifySpinner.style.display = "inline-block";
    classifyText.textContent = "Đang phân loại...";
    clearBanners();

    const topK = parseInt(topKSlider.value, 10);

    try {
      const response = await ApiClient.classifyImage(selectedFile, topK);
      renderResults(response);
    } catch (err) {
      const friendly = Utils.getFriendlyErrorMessage(err);
      showErrorBanner(friendly.title, friendly.message);
    } finally {
      isClassifying = false;
      btnClassify.disabled = !selectedFile;
      classifySpinner.style.display = "none";
      classifyText.textContent = "Classify Fruit Image";
    }
  });

  // ---------- Render Results ----------
  function renderResults(response) {
    if (initialEmptyState) {
      initialEmptyState.style.display = "none";
    }

    const top = response.prediction || { class_name: "unknown", confidence: 0 };
    const predictions = response.top_predictions || [];
    const isAccepted = response.accepted;
    const isFallback = response.is_fallback;
    const scoreType = response.score_type || "softmax_probability";
    const method = response.inference_method || "convnext_tiny";

    if (queryDataUrl) {
      resultQueryImg.src = queryDataUrl;
    }

    topClassName.textContent = top.class_name;
    const scoreVal = top.confidence;
    const topPct = (scoreVal * 100).toFixed(1);

    if (scoreType === "knn_vote") {
      topConfidenceValue.textContent = `Score: ${scoreVal.toFixed(2)}`;
      topConfidenceFill.style.width = `${Math.min(scoreVal * 100, 100)}%`;
    } else {
      topConfidenceValue.textContent = `${topPct}%`;
      topConfidenceFill.style.width = `${topPct}%`;
    }

    if (isAccepted) {
      acceptedBadge.textContent = isFallback ? "Accepted (kNN Match)" : "Accepted";
      acceptedBadge.style.backgroundColor = "#f0fdf4";
      acceptedBadge.style.color = "#16a34a";
      acceptedBadge.style.borderColor = "#bbf7d0";
    } else {
      acceptedBadge.textContent = isFallback ? "Low kNN Confidence" : "Low Confidence";
      acceptedBadge.style.backgroundColor = "#fef2f2";
      acceptedBadge.style.color = "#dc2626";
      acceptedBadge.style.borderColor = "#fecaca";
    }

    resultStatusMsg.textContent = response.message;
    predictionCardContainer.style.display = "block";

    // Render list
    predictionsList.innerHTML = "";
    predictions.forEach((item, index) => {
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.gap = "1rem";
      row.style.padding = "0.5rem 0.75rem";
      row.style.borderRadius = "var(--radius-md)";
      row.style.backgroundColor = index === 0 ? "var(--color-primary-light)" : "var(--color-bg-subtle)";

      const rank = document.createElement("span");
      rank.style.fontWeight = "700";
      rank.style.fontSize = "0.875rem";
      rank.style.color = "var(--color-text-subtle)";
      rank.style.width = "24px";
      rank.textContent = `#${index + 1}`;

      const name = document.createElement("span");
      name.style.flex = "1";
      name.style.fontWeight = "600";
      name.style.textTransform = "capitalize";
      name.textContent = item.class_name;

      const score = document.createElement("span");
      score.style.fontWeight = "700";
      score.style.fontFamily = "var(--font-mono)";
      score.style.fontSize = "0.875rem";
      score.textContent = scoreType === "knn_vote" ? item.confidence.toFixed(2) : `${(item.confidence * 100).toFixed(1)}%`;

      row.appendChild(rank);
      row.appendChild(name);
      row.appendChild(score);
      predictionsList.appendChild(row);
    });

    let extraInfo = `Engine: ${method}`;
    if (isFallback) {
      if (response.neighbor_agreement) {
        extraInfo += ` | Agreement: ${response.neighbor_agreement}`;
      }
      if (response.top_similarity) {
        extraInfo += ` | Top Sim: ${response.top_similarity.toFixed(2)}`;
      }
    }
    metaTimingInfo.textContent = `Inference: ${response.processing_time_ms} ms | ${extraInfo}`;
    predictionsListContainer.style.display = "block";
  }
});
