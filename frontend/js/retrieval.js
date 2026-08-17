/**
 * Fruvia AI — Image Retrieval UI Logic
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

  const btnSearch = document.getElementById("btn-search");
  const searchText = document.getElementById("search-text");
  const searchSpinner = document.getElementById("search-spinner");

  const comparisonContainer = document.getElementById("comparison-container");
  const queryComparisonImg = document.getElementById("query-comparison-img");
  const topMatchMedia = document.getElementById("top-match-media");

  const errorBannerContainer = document.getElementById("error-banner-container");
  const warningBannerContainer = document.getElementById("warning-banner-container");
  const resultsHeader = document.getElementById("results-header");
  const resCount = document.getElementById("res-count");
  const resTime = document.getElementById("res-time");
  const resultsGrid = document.getElementById("results-grid");
  const initialEmptyState = document.getElementById("initial-empty-state");

  // Modal Elements
  const imageModal = document.getElementById("image-modal");
  const modalClose = document.getElementById("modal-close");
  const modalMediaWrapper = document.getElementById("modal-media-wrapper");
  const modalTitle = document.getElementById("modal-title");
  const modalOriginalClass = document.getElementById("modal-original-class");
  const modalSimilarityBox = document.getElementById("modal-similarity-box");
  const modalFilename = document.getElementById("modal-filename");
  const modalSplit = document.getElementById("modal-split");
  const modalPath = document.getElementById("modal-path");

  // State Variables
  let selectedFile = null;
  let queryDataUrl = null;
  let isSearching = false;

  // SVG Helper
  function createSvgIcon(pathD, width = 24, height = 24) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "svg-icon");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("width", String(width));
    svg.setAttribute("height", String(height));
    svg.setAttribute("fill", "currentColor");

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", pathD);
    svg.appendChild(path);
    return svg;
  }

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
      btnSearch.disabled = false;
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
    btnSearch.disabled = true;
    comparisonContainer.style.display = "none";
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

  // Global Clipboard Paste Handler (Ctrl+V / Cmd+V)
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

  // ---------- Banner Renderers ----------
  function showErrorBanner(title, message) {
    errorBannerContainer.innerHTML = "";
    const banner = document.createElement("div");
    banner.className = "alert-banner alert-banner-error";
    banner.setAttribute("role", "alert");

    const icon = document.createElement("span");
    icon.className = "alert-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.appendChild(createSvgIcon("M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z", 20, 20));

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

  function showWarningBanner(title, message) {
    warningBannerContainer.innerHTML = "";
    const banner = document.createElement("div");
    banner.className = "alert-banner alert-banner-warning";
    banner.setAttribute("role", "alert");

    const icon = document.createElement("span");
    icon.className = "alert-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.appendChild(createSvgIcon("M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z", 20, 20));

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
    warningBannerContainer.appendChild(banner);
    warningBannerContainer.style.display = "block";
  }

  function clearBanners() {
    errorBannerContainer.innerHTML = "";
    errorBannerContainer.style.display = "none";
    warningBannerContainer.innerHTML = "";
    warningBannerContainer.style.display = "none";
  }

  // ---------- Search Submission ----------
  btnSearch.addEventListener("click", async () => {
    if (!selectedFile || isSearching) return;

    isSearching = true;
    btnSearch.disabled = true;
    searchSpinner.style.display = "inline-block";
    searchText.textContent = "Đang tìm kiếm vector...";
    clearBanners();

    const topK = parseInt(topKSlider.value, 10);

    try {
      const response = await ApiClient.retrieveImage(selectedFile, topK);
      renderResults(response);
    } catch (err) {
      const friendly = Utils.getFriendlyErrorMessage(err);
      showErrorBanner(friendly.title, friendly.message);
    } finally {
      isSearching = false;
      btnSearch.disabled = !selectedFile;
      searchSpinner.style.display = "none";
      searchText.textContent = "Tìm Ảnh Tương đồng";
    }
  });

  // ---------- Render Results Cards (DOM API) ----------
  function renderResults(response) {
    if (initialEmptyState) {
      initialEmptyState.style.display = "none";
    }

    const results = response.results || [];
    resCount.textContent = String(response.result_count || results.length);
    resTime.textContent = String(response.processing_time_ms || 0);
    resultsHeader.style.display = "flex";

    if (queryDataUrl) {
      queryComparisonImg.src = queryDataUrl;
      comparisonContainer.style.display = "flex";
    }

    resultsGrid.innerHTML = "";
    topMatchMedia.innerHTML = "";

    if (results.length === 0) {
      const emptyDiv = document.createElement("div");
      emptyDiv.className = "empty-state";
      emptyDiv.style.gridColumn = "1 / -1";

      const icon = document.createElement("div");
      icon.className = "empty-state-icon";
      icon.appendChild(createSvgIcon("M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z", 48, 48));

      const h3 = document.createElement("h3");
      h3.textContent = "Không tìm thấy Ảnh Tương đồng";

      const p = document.createElement("p");
      p.textContent = "Tìm kiếm vector không trả về kết quả nào cho ảnh truy vấn của bạn.";

      emptyDiv.appendChild(icon);
      emptyDiv.appendChild(h3);
      emptyDiv.appendChild(p);
      resultsGrid.appendChild(emptyDiv);
      return;
    }

    const topResult = results[0];
    const topSim = topResult && typeof topResult.similarity === "number" ? topResult.similarity : 0;

    if (topSim < CONFIG.LOW_SIMILARITY_THRESHOLD) {
      showWarningBanner(
        "Không tìm thấy kết quả tương đồng cao trong bộ dữ liệu hiện tại.",
        "Các kết quả trả về có độ tương đồng thấp, có thể không chính xác."
      );
    }

    if (topResult) {
      const displayName = topResult.display_name || topResult.canonical_class || "Unknown";
      if (Utils.isSafeImageUrl(topResult.image_url)) {
        const topImg = document.createElement("img");
        topImg.src = topResult.image_url;
        topImg.alt = `Top match: ${displayName}`;
        topMatchMedia.appendChild(topImg);
      } else {
        const topPlaceholder = document.createElement("div");
        topPlaceholder.className = "card-placeholder";
        const pIcon = document.createElement("span");
        pIcon.className = "fruit-icon";
        pIcon.appendChild(createSvgIcon("M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z", 32, 32));
        const pText = document.createElement("span");
        pText.className = "placeholder-class";
        pText.textContent = displayName;
        topPlaceholder.appendChild(pIcon);
        topPlaceholder.appendChild(pText);
        topMatchMedia.appendChild(topPlaceholder);
      }
    }

    results.forEach((item, index) => {
      const rank = index + 1;
      const originalClass = item.original_class || "unknown";
      const canonicalClass = item.canonical_class || "unknown";
      const displayName = item.display_name || canonicalClass;
      const filename = item.filename || "unknown";
      const originalSplit = item.original_split || "unknown";
      const relativePath = item.relative_path || "";
      const similarityObj = Utils.formatSimilarity(item.similarity);

      const card = document.createElement("article");
      card.className = "result-card";

      const mediaDiv = document.createElement("div");
      mediaDiv.className = "card-media";

      const rankBadge = document.createElement("span");
      rankBadge.className = "rank-badge";
      rankBadge.textContent = `#${rank}`;
      mediaDiv.appendChild(rankBadge);

      const hasSafeUrl = Utils.isSafeImageUrl(item.image_url);

      if (hasSafeUrl) {
        const skeleton = document.createElement("div");
        skeleton.className = "card-skeleton";
        mediaDiv.appendChild(skeleton);

        const img = document.createElement("img");
        img.setAttribute("loading", "lazy");
        img.setAttribute("decoding", "async");
        img.alt = `Similar fruit match: ${displayName}`;

        img.addEventListener("load", () => {
          skeleton.remove();
          img.classList.add("loaded");
        });

        img.addEventListener("error", () => {
          skeleton.remove();
          img.remove();
          mediaDiv.appendChild(createPlaceholderElement(displayName, "Lỗi tải ảnh"));
        });

        img.src = item.image_url;
        mediaDiv.appendChild(img);
      } else {
        mediaDiv.appendChild(createPlaceholderElement(displayName, "Không có xem trước"));
      }

      mediaDiv.addEventListener("click", () => {
        openModal(item, queryDataUrl);
      });

      const bodyDiv = document.createElement("div");
      bodyDiv.className = "card-body";

      const titleHeader = document.createElement("div");
      const titleH3 = document.createElement("h3");
      titleH3.className = "card-class-title";
      titleH3.textContent = displayName;

      const rawLabelP = document.createElement("p");
      rawLabelP.className = "card-class-original";
      rawLabelP.textContent = `Nhãn gốc: ${originalClass}`;

      titleHeader.appendChild(titleH3);
      titleHeader.appendChild(rawLabelP);
      bodyDiv.appendChild(titleHeader);

      const simBox = document.createElement("div");
      simBox.className = `similarity-box ${similarityObj.levelClass}`;

      const simHeader = document.createElement("div");
      simHeader.className = "similarity-header";

      const simLabel = document.createElement("span");
      simLabel.className = "similarity-label";
      simLabel.textContent = "Độ tương đồng";

      const simValue = document.createElement("span");
      simValue.className = "similarity-value";
      simValue.textContent = similarityObj.percentageText;

      simHeader.appendChild(simLabel);
      simHeader.appendChild(simValue);

      const simTrack = document.createElement("div");
      simTrack.className = "similarity-track";
      simTrack.setAttribute("role", "progressbar");
      simTrack.setAttribute("aria-valuenow", (item.similarity * 100).toFixed(1));
      simTrack.setAttribute("aria-valuemin", "-100");
      simTrack.setAttribute("aria-valuemax", "100");

      const simFill = document.createElement("div");
      simFill.className = "similarity-fill";
      simFill.style.width = similarityObj.visualWidth;

      simTrack.appendChild(simFill);
      simBox.appendChild(simHeader);
      simBox.appendChild(simTrack);
      bodyDiv.appendChild(simBox);

      const summaryDiv = document.createElement("div");
      summaryDiv.className = "card-details";

      const fileLine = document.createElement("div");
      const fileStrong = document.createElement("strong");
      fileStrong.textContent = "Tên file: ";
      fileLine.appendChild(fileStrong);
      fileLine.appendChild(document.createTextNode(filename));

      const splitLine = document.createElement("div");
      const splitStrong = document.createElement("strong");
      splitStrong.textContent = "Tập dữ liệu: ";
      splitLine.appendChild(splitStrong);
      splitLine.appendChild(document.createTextNode(originalSplit));

      summaryDiv.appendChild(fileLine);
      summaryDiv.appendChild(splitLine);

      const detailsToggleBtn = document.createElement("button");
      detailsToggleBtn.type = "button";
      detailsToggleBtn.className = "card-details-toggle";
      detailsToggleBtn.textContent = "Chi tiết kỹ thuật";

      const hiddenDetailsDiv = document.createElement("div");
      hiddenDetailsDiv.style.display = "none";
      hiddenDetailsDiv.className = "card-details";
      hiddenDetailsDiv.style.marginTop = "0.25rem";

      const pathLine = document.createElement("div");
      const pathStrong = document.createElement("strong");
      pathStrong.textContent = "Đường dẫn: ";
      pathLine.appendChild(pathStrong);
      pathLine.appendChild(document.createTextNode(relativePath));

      const rawSimLine = document.createElement("div");
      const rawSimStrong = document.createElement("strong");
      rawSimStrong.textContent = "Similarity gốc: ";
      rawSimLine.appendChild(rawSimStrong);
      rawSimLine.appendChild(document.createTextNode(String(item.similarity)));

      hiddenDetailsDiv.appendChild(pathLine);
      hiddenDetailsDiv.appendChild(rawSimLine);

      detailsToggleBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const isHidden = hiddenDetailsDiv.style.display === "none";
        hiddenDetailsDiv.style.display = isHidden ? "block" : "none";
      });

      bodyDiv.appendChild(summaryDiv);
      bodyDiv.appendChild(detailsToggleBtn);
      bodyDiv.appendChild(hiddenDetailsDiv);

      card.appendChild(mediaDiv);
      card.appendChild(bodyDiv);
      resultsGrid.appendChild(card);
    });
  }

  function createPlaceholderElement(displayName, noteText) {
    const placeholder = document.createElement("div");
    placeholder.className = "card-placeholder";

    const fruitIcon = document.createElement("span");
    fruitIcon.className = "fruit-icon";
    fruitIcon.setAttribute("aria-hidden", "true");
    fruitIcon.appendChild(createSvgIcon("M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z", 32, 32));

    const nameSpan = document.createElement("span");
    nameSpan.className = "placeholder-class";
    nameSpan.textContent = displayName;

    const noteSpan = document.createElement("span");
    noteSpan.className = "placeholder-note";
    noteSpan.textContent = noteText;

    placeholder.appendChild(fruitIcon);
    placeholder.appendChild(nameSpan);
    placeholder.appendChild(noteSpan);
    return placeholder;
  }

  // ---------- Modal / Lightbox Logic ----------
  function openModal(item, queryImgUrl) {
    const displayName = item.display_name || item.canonical_class || "Unknown";
    const originalClass = item.original_class || "unknown";
    const filename = item.filename || "unknown";
    const originalSplit = item.original_split || "unknown";
    const relativePath = item.relative_path || "";
    const similarityObj = Utils.formatSimilarity(item.similarity);

    modalTitle.textContent = displayName;
    modalOriginalClass.textContent = `Nhãn gốc: ${originalClass}`;
    modalFilename.textContent = filename;
    modalSplit.textContent = originalSplit;
    modalPath.textContent = relativePath;

    modalMediaWrapper.innerHTML = "";
    if (Utils.isSafeImageUrl(item.image_url)) {
      const modalImg = document.createElement("img");
      modalImg.src = item.image_url;
      modalImg.alt = displayName;
      modalMediaWrapper.appendChild(modalImg);
    } else {
      modalMediaWrapper.appendChild(createPlaceholderElement(displayName, "Không có xem trước"));
    }

    modalSimilarityBox.className = `similarity-box ${similarityObj.levelClass}`;
    modalSimilarityBox.innerHTML = `
      <div class="similarity-header">
        <span class="similarity-label">Độ tương đồng</span>
        <span class="similarity-value">${similarityObj.percentageText}</span>
      </div>
      <div class="similarity-track">
        <div class="similarity-fill" style="width: ${similarityObj.visualWidth};"></div>
      </div>
    `;

    imageModal.style.display = "flex";
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    imageModal.style.display = "none";
    document.body.style.overflow = "";
  }

  modalClose.addEventListener("click", closeModal);
  imageModal.addEventListener("click", (e) => {
    if (e.target === imageModal) {
      closeModal();
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && imageModal.style.display === "flex") {
      closeModal();
    }
  });
});
