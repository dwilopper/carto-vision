const state = {
  bootstrap: null,
  currentDataset: null,
  currentResult: null,
  map: null,
  geoLayer: null,
  labelLayer: null,
};

const elements = {
  sourceList: document.getElementById("source-list"),
  uploadForm: document.getElementById("upload-form"),
  uploadFile: document.getElementById("upload-file"),
  datasetName: document.getElementById("dataset-name"),
  datasetDescription: document.getElementById("dataset-description"),
  datasetSelect: document.getElementById("dataset-select"),
  datasetMeta: document.getElementById("dataset-meta"),
  datasetPreview: document.getElementById("dataset-preview"),
  regionIdColumn: document.getElementById("region-id-column"),
  regionNameColumn: document.getElementById("region-name-column"),
  valueColumn: document.getElementById("value-column"),
  filterColumn: document.getElementById("filter-column"),
  filterValue: document.getElementById("filter-value"),
  normalization: document.getElementById("normalization"),
  denominatorColumn: document.getElementById("denominator-column"),
  multiplier: document.getElementById("multiplier"),
  aggregation: document.getElementById("aggregation"),
  layerSelect: document.getElementById("layer-select"),
  classificationMethod: document.getElementById("classification-method"),
  classCount: document.getElementById("class-count"),
  paletteSelect: document.getElementById("palette-select"),
  sessionName: document.getElementById("session-name"),
  generateButton: document.getElementById("generate-button"),
  sessionList: document.getElementById("session-list"),
  mapTitle: document.getElementById("map-title"),
  mapSubtitle: document.getElementById("map-subtitle"),
  exportLinks: document.getElementById("export-links"),
  legendBox: document.getElementById("legend-box"),
  summaryMetric: document.getElementById("summary-metric"),
  summaryCoverage: document.getElementById("summary-coverage"),
  summaryRange: document.getElementById("summary-range"),
  summaryStats: document.getElementById("summary-stats"),
  analysisNotes: document.getElementById("analysis-notes"),
  rangeMin: document.getElementById("range-min"),
  rangeMax: document.getElementById("range-max"),
  applyRangeFilter: document.getElementById("apply-range-filter"),
  resetRangeFilter: document.getElementById("reset-range-filter"),
  sourceForm: document.getElementById("source-form"),
  sourceName: document.getElementById("source-name"),
  sourceDescription: document.getElementById("source-description"),
  sourceFormat: document.getElementById("source-format"),
  sourceUrl: document.getElementById("source-url"),
  layerForm: document.getElementById("layer-form"),
  layerName: document.getElementById("layer-name"),
  layerDescription: document.getElementById("layer-description"),
  layerFile: document.getElementById("layer-file"),
  mapPlaceholder: document.getElementById("map-placeholder"),
  mapStage: document.getElementById("map-stage"),
  historyToggle: document.getElementById("history-toggle"),
  historyClose: document.getElementById("history-close"),
  historyPopover: document.getElementById("history-popover"),
  historyBackdrop: document.getElementById("history-backdrop"),
  toastRoot: document.getElementById("toast-root"),
  controlColumn: document.querySelector(".control-column"),
  resultColumn: document.querySelector(".result-column"),
};

function removeToast(toast) {
  if (!toast || !toast.parentNode) {
    return;
  }
  toast.classList.remove("visible");
  window.setTimeout(() => {
    toast.remove();
  }, 180);
}

function notify(message, type = "info") {
  if (!elements.toastRoot) {
    window.alert(message);
    return;
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  const text = document.createElement("div");
  text.className = "toast-message";
  text.textContent = message;

  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "toast-close";
  closeButton.setAttribute("aria-label", "Закрыть уведомление");
  closeButton.textContent = "×";
  closeButton.addEventListener("click", () => removeToast(toast));

  toast.append(text, closeButton);
  elements.toastRoot.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("visible"));
  window.setTimeout(() => removeToast(toast), 3200);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    try {
      const payload = await response.json();
      throw new Error(payload.detail || "Запрос завершился ошибкой.");
    } catch (error) {
      if (error instanceof SyntaxError) {
        throw new Error("Запрос завершился ошибкой.");
      }
      throw error;
    }
  }

  return response.json();
}

function createOption(value, label) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  return option;
}

function setOptions(select, options, placeholder = "") {
  if (!select) {
    return;
  }
  select.innerHTML = "";
  if (placeholder) {
    select.appendChild(createOption("", placeholder));
  }
  options.forEach((option) => select.appendChild(createOption(option.value, option.label)));
}

function guessColumn(columns, candidates) {
  const lookup = candidates.map((item) => item.toLowerCase());
  return columns.find((column) => lookup.includes(column.name.toLowerCase()))?.name || "";
}

function guessMetricColumn(columns, numericColumns) {
  const ignoredColumns = [
    "year",
    "period",
    "date",
    "month",
    "quarter",
    "id",
    "code",
    "год",
    "период",
    "дата",
    "месяц",
    "квартал",
    "код территории",
    "код региона",
  ];
  const preferredKeywords = [
    "grdp",
    "gdp",
    "врп",
    "зарп",
    "salary",
    "income",
    "доход",
    "investment",
    "инвест",
    "innovation",
    "иннова",
    "digital",
    "цифров",
    "export",
    "экспорт",
    "import",
    "безработ",
    "unemployment",
    "population",
    "населен",
    "count",
    "value",
    "rate",
    "index",
    "индекс",
    "промыш",
    "производ",
  ];

  const numeric = (numericColumns || []).filter((columnName) => {
    const normalized = columnName.toLowerCase().trim();
    return !ignoredColumns.includes(normalized);
  });

  return (
    numeric.find((columnName) => {
      const normalized = columnName.toLowerCase();
      return preferredKeywords.some((keyword) => normalized.includes(keyword));
    }) ||
    numeric[0] ||
    (numericColumns || [])[0] ||
    ""
  );
}

function guessFilterValue(schema, filterColumnName) {
  if (!filterColumnName) {
    return "";
  }
  const column = (schema.columns || []).find((item) => item.name === filterColumnName);
  const sampleValues = column?.sampleValues || [];
  const numericValues = sampleValues
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));

  if (numericValues.length) {
    return String(Math.max(...numericValues));
  }

  return sampleValues[0] || "";
}

function formatTimestamp(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("ru-RU");
}

function mergeDatasetIntoBootstrap(dataset) {
  if (!state.bootstrap) {
    return;
  }

  const rest = (state.bootstrap.datasets || []).filter((item) => {
    return String(item.id) !== String(dataset.id) && item.name !== dataset.name;
  });
  state.bootstrap.datasets = [dataset, ...rest];
}

function setScrollFadeState(container) {
  if (!container) {
    return;
  }

  const maxScroll = Math.max(0, container.scrollHeight - container.clientHeight);
  if (maxScroll <= 2) {
    container.dataset.scrollFade = "none";
    return;
  }

  const scrollTop = container.scrollTop;
  const nearTop = scrollTop <= 4;
  const nearBottom = scrollTop >= maxScroll - 4;

  if (nearTop && !nearBottom) {
    container.dataset.scrollFade = "bottom";
    return;
  }
  if (!nearTop && nearBottom) {
    container.dataset.scrollFade = "top";
    return;
  }
  if (!nearTop && !nearBottom) {
    container.dataset.scrollFade = "both";
    return;
  }

  container.dataset.scrollFade = "none";
}

function refreshScrollFades() {
  setScrollFadeState(elements.controlColumn);
  setScrollFadeState(elements.resultColumn);
}

function openHistoryPopover() {
  if (!elements.historyPopover || !elements.historyBackdrop) {
    return;
  }
  elements.historyPopover.classList.remove("hidden");
  elements.historyBackdrop.classList.remove("hidden");
  elements.historyPopover.setAttribute("aria-hidden", "false");
}

function closeHistoryPopover() {
  if (!elements.historyPopover || !elements.historyBackdrop) {
    return;
  }
  elements.historyPopover.classList.add("hidden");
  elements.historyBackdrop.classList.add("hidden");
  elements.historyPopover.setAttribute("aria-hidden", "true");
}

function renderDataset(dataset) {
  state.currentDataset = dataset;

  const schema = dataset.schema || {};
  const columns = schema.columns || [];
  const allOptions = columns.map((column) => ({
    value: column.name,
    label: `${column.name} (${column.kind})`,
  }));
  const numericOptions = (schema.numericColumns || []).map((column) => ({
    value: column,
    label: column,
  }));
  const categoricalOptions = columns.map((column) => ({
    value: column.name,
    label: column.name,
  }));

  setOptions(elements.regionIdColumn, allOptions);
  setOptions(elements.regionNameColumn, allOptions);
  setOptions(elements.valueColumn, numericOptions);
  setOptions(elements.filterColumn, [{ value: "", label: "Без фильтра" }, ...categoricalOptions]);
  setOptions(elements.denominatorColumn, [{ value: "", label: "Без делителя" }, ...numericOptions]);

  elements.regionIdColumn.value = guessColumn(columns, [
    "territory_id",
    "region_id",
    "id",
    "code",
    "код территории",
    "код региона",
    "идентификатор территории",
  ]);
  elements.regionNameColumn.value = guessColumn(columns, [
    "territory_name",
    "region_name",
    "name",
    "territory",
    "территория",
    "название территории",
    "регион",
    "название региона",
  ]);
  elements.valueColumn.value = guessMetricColumn(columns, schema.numericColumns || []);
  elements.filterColumn.value = guessColumn(columns, ["year", "period", "date", "год", "период", "дата"]);
  elements.filterValue.value = guessFilterValue(schema, elements.filterColumn.value);
  elements.denominatorColumn.value = guessColumn(columns, [
    "population",
    "population_mln",
    "population_total",
    "население",
    "население (млн чел.)",
    "численность населения",
  ]);

  elements.datasetMeta.innerHTML = `
    <p><strong>${dataset.name}</strong></p>
    <p>${dataset.description || "Без описания."}</p>
    <p>Строк в наборе: ${schema.rowCount || 0}. Источник: ${dataset.sourceName || dataset.sourceType}</p>
  `;

  const header = columns.map((column) => `<th>${column.name}</th>`).join("");
  const rows = (schema.previewRows || [])
    .map((row) => {
      const cells = columns.map((column) => `<td>${row[column.name] ?? ""}</td>`).join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");

  elements.datasetPreview.innerHTML = columns.length
    ? `
      <table>
        <thead><tr>${header}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `
    : "<p>Предпросмотр данных недоступен.</p>";

  if (!elements.sessionName.value || elements.sessionName.value.startsWith(dataset.name)) {
    elements.sessionName.value = `${dataset.name} / ${elements.valueColumn.value || "показатель"}`;
  }

  requestAnimationFrame(refreshScrollFades);
}

function renderDatasets() {
  const datasets = state.bootstrap?.datasets || [];

  setOptions(
    elements.datasetSelect,
    datasets.map((dataset) => ({ value: dataset.id, label: dataset.name })),
    datasets.length ? "" : "Сначала загрузите датасет"
  );

  if (!datasets.length) {
    elements.datasetMeta.innerHTML = "<p>Датасет еще не загружен.</p>";
    elements.datasetPreview.innerHTML = "";
    setOptions(elements.regionIdColumn, [], "Нет данных");
    setOptions(elements.regionNameColumn, [], "Нет данных");
    setOptions(elements.valueColumn, [], "Нет данных");
    setOptions(elements.filterColumn, [], "Нет данных");
    setOptions(elements.denominatorColumn, [], "Нет данных");
    state.currentDataset = null;
    requestAnimationFrame(refreshScrollFades);
    return;
  }

  const preferredId = String(state.currentDataset?.id || elements.datasetSelect.value || datasets[0].id);
  const dataset =
    datasets.find((item) => String(item.id) === preferredId) ||
    datasets.find((item) => item.name === state.currentDataset?.name) ||
    datasets[0];

  elements.datasetSelect.value = String(dataset.id);
  renderDataset(dataset);
}

function renderSources() {
  if (!elements.sourceList) {
    return;
  }
  elements.sourceList.innerHTML = "";

  (state.bootstrap?.sources || []).forEach((source) => {
    const card = document.createElement("article");
    card.className = "source-item";
    card.innerHTML = `
      <h3>${source.name}</h3>
      <p>${source.description || "Без описания."}</p>
      <p><strong>Тип:</strong> ${source.kind} | <strong>Формат:</strong> ${source.format || "n/a"}</p>
      <div class="source-actions">
        <button type="button" class="ghost-button" data-source-id="${source.id}">Загрузить в рабочую область</button>
      </div>
    `;

    const button = card.querySelector("button");
    button.addEventListener("click", async () => {
      const originalLabel = button.textContent;
      try {
        button.disabled = true;
        button.textContent = "Загрузка...";
        const payload = await fetchJson(`/api/datasets/from-source/${source.id}`, { method: "POST" });
        mergeDatasetIntoBootstrap(payload.dataset);
        renderDatasets();
        elements.datasetSelect.value = String(payload.dataset.id);
        renderDataset(payload.dataset);
        notify(
          payload.alreadyLoaded ? "Датасет уже был загружен." : "Датасет успешно загружен.",
          payload.alreadyLoaded ? "info" : "success"
        );
      } catch (error) {
        notify(error.message, "error");
      } finally {
        button.disabled = false;
        button.textContent = originalLabel;
      }
    });

    elements.sourceList.appendChild(card);
  });
}

function renderLayers() {
  setOptions(
    elements.layerSelect,
    (state.bootstrap?.layers || []).map((layer) => ({
      value: layer.id,
      label: `${layer.name} (${layer.featureCount} объектов)`,
    }))
  );

  const preferredLayer =
    (state.bootstrap?.layers || []).find((layer) => layer.slug === state.bootstrap.defaultLayerSlug) ||
    (state.bootstrap?.layers || [])[0];

  if (preferredLayer) {
    elements.layerSelect.value = String(preferredLayer.id);
  }
}

function renderPalettes() {
  const options = Object.keys(state.bootstrap?.palettes || {}).map((paletteName) => ({
    value: paletteName,
    label: paletteName,
  }));
  setOptions(elements.paletteSelect, options);
  if (options.some((option) => option.value === "copper")) {
    elements.paletteSelect.value = "copper";
  }
}

function renderSessions() {
  if (!elements.sessionList) {
    return;
  }

  elements.sessionList.innerHTML = "";
  const sessions = state.bootstrap?.sessions || [];

  if (!sessions.length) {
    elements.sessionList.innerHTML = "<p>Сохраненные сессии появятся здесь после генерации картограммы.</p>";
    requestAnimationFrame(refreshScrollFades);
    return;
  }

  sessions.forEach((session) => {
    const card = document.createElement("article");
    card.className = "session-item";
    card.innerHTML = `
      <h3>${session.name}</h3>
      <p>Показатель: ${session.metricLabel || "-"}</p>
      <p>Метод классификации: ${session.classificationMethod || "-"}</p>
      <p>Обновлено: ${formatTimestamp(session.updatedAt)}</p>
      <div class="session-actions">
        <button type="button" class="ghost-button">Загрузить сессию</button>
      </div>
    `;

    const button = card.querySelector("button");
    button.addEventListener("click", async () => {
      try {
        const payload = await fetchJson(`/api/sessions/${session.id}`);
        const dataset =
          (state.bootstrap?.datasets || []).find((item) => item.id === payload.dataset.id) ||
          (state.bootstrap?.datasets || []).find((item) => item.name === payload.dataset.name);

        if (dataset) {
          mergeDatasetIntoBootstrap(dataset);
          renderDatasets();
          elements.datasetSelect.value = String(dataset.id);
          renderDataset(dataset);
        }

        applySettings(payload.settings);
        renderCartogram(payload, {
          geojson: payload.cartogram.geojson,
          legend: payload.cartogram.legend,
          summary: payload.cartogram.summary,
          exports: {
            geojson: `/api/exports/${session.id}/geojson`,
            csv: `/api/exports/${session.id}/csv`,
            png: `/api/exports/${session.id}/png`,
            pdf: `/api/exports/${session.id}/pdf`,
          },
          sessionId: session.id,
          sessionName: payload.session.name,
        });
        closeHistoryPopover();
      } catch (error) {
        notify(error.message, "error");
      }
    });

    elements.sessionList.appendChild(card);
  });

  requestAnimationFrame(refreshScrollFades);
}

function applySettings(settings) {
  elements.regionIdColumn.value = settings.regionIdColumn || "";
  elements.regionNameColumn.value = settings.regionNameColumn || "";
  elements.valueColumn.value = settings.valueColumn || "";
  elements.filterColumn.value = settings.filterColumn || "";
  elements.filterValue.value = settings.filterValue || "";
  elements.normalization.value = settings.normalization || "none";
  elements.denominatorColumn.value = settings.denominatorColumn || "";
  elements.multiplier.value = settings.multiplier || 1000;
  elements.aggregation.value = settings.aggregation || "sum";
  elements.layerSelect.value = settings.layerId || elements.layerSelect.value;
  elements.classificationMethod.value = settings.classificationMethod || "equal";
  elements.classCount.value = settings.classCount || 5;
  elements.paletteSelect.value = settings.palette || "copper";
  elements.sessionName.value = settings.sessionName || "";
}

function ensureMap() {
  if (state.map) {
    return;
  }

  state.map = L.map("map", {
    crs: L.CRS.Simple,
    minZoom: -2,
    maxZoom: 4,
    zoomSnap: 0.25,
    attributionControl: false,
  });
}

function clearMapLayers() {
  if (state.geoLayer) {
    state.geoLayer.remove();
    state.geoLayer = null;
  }
  if (state.labelLayer) {
    state.labelLayer.remove();
    state.labelLayer = null;
  }
}

function applyFeatureFilter() {
  if (!state.geoLayer) {
    return;
  }

  const minValue = parseFloat(elements.rangeMin.value);
  const maxValue = parseFloat(elements.rangeMax.value);
  const hasMin = Number.isFinite(minValue);
  const hasMax = Number.isFinite(maxValue);

  state.geoLayer.eachLayer((layer) => {
    const value = layer.feature.properties.display_value;
    const visible =
      (!hasMin && !hasMax) ||
      (value !== null &&
        (!hasMin || value >= minValue) &&
        (!hasMax || value <= maxValue));

    layer.setStyle({
      fillOpacity: visible ? 0.82 : 0.12,
      opacity: visible ? 1 : 0.25,
      weight: visible ? 1.3 : 0.8,
    });
  });
}

function renderLegend(legend) {
  if (!elements.legendBox) {
    return;
  }

  if (!legend || !legend.length) {
    elements.legendBox.classList.add("hidden");
    elements.legendBox.innerHTML = "";
    return;
  }

  elements.legendBox.classList.remove("hidden");
  elements.legendBox.innerHTML = `
    <p class="section-step">Легенда</p>
    <h3>Классы картограммы</h3>
    ${legend
      .map(
        (item) => `
      <div class="legend-row">
        <span class="legend-color" style="background:${item.color}"></span>
        <span>${item.label} (${item.count})</span>
      </div>
    `
      )
      .join("")}
  `;
}

function renderAnalysis(summary) {
  const missingItem =
    (summary.missingRegionNames || []).length > 0
      ? `<li>Без данных остались: ${summary.missingRegionNames.join(", ")}</li>`
      : "<li>Все территории получили классификационное значение.</li>";

  elements.analysisNotes.innerHTML = `
    <div class="status-banner">
      Картограмма сформирована. Экспорты доступны сразу после построения.
    </div>
    <ul>
      <li>Метод классификации: <strong>${summary.classificationMethod}</strong>.</li>
      <li>Показатель для отображения: <strong>${summary.metricLabel}</strong>.</li>
      <li>Покрытие территорий: <strong>${summary.matchedRegions}</strong> из ${summary.matchedRegions + summary.missingRegions}.</li>
      ${missingItem}
    </ul>
  `;
  requestAnimationFrame(refreshScrollFades);
}

function renderSummary(summary) {
  elements.summaryMetric.textContent = summary.metricLabel || "-";
  elements.summaryCoverage.textContent = `${summary.matchedRegions} / ${summary.matchedRegions + summary.missingRegions}`;
  elements.summaryRange.textContent = `${summary.min} ... ${summary.max}`;
  elements.summaryStats.textContent = `${summary.mean} / ${summary.median}`;
  elements.rangeMin.value = summary.min;
  elements.rangeMax.value = summary.max;
}

function renderExportLinks(exports, sessionName) {
  elements.exportLinks.innerHTML = `
    <a class="ghost-button" href="${exports.png}" target="_blank" rel="noreferrer">PNG</a>
    <a class="ghost-button" href="${exports.pdf}" target="_blank" rel="noreferrer">PDF</a>
    <a class="ghost-button" href="${exports.csv}" target="_blank" rel="noreferrer">CSV</a>
    <a class="ghost-button" href="${exports.geojson}" target="_blank" rel="noreferrer">GeoJSON</a>
  `;
  elements.mapTitle.textContent = sessionName;
}

function shouldRenderLabels(geojson) {
  const metadata = geojson?.metadata || {};
  if (metadata.labelMode === "none") {
    return false;
  }
  if (metadata.labelMode === "always") {
    return true;
  }
  return (geojson?.features || []).length <= 20;
}

function applyMapTheme(geojson) {
  const metadata = geojson?.metadata || {};
  const darkTheme = metadata.mapTheme === "dark";
  elements.mapStage?.classList.toggle("map-stage-dark", darkTheme);
  document.getElementById("map")?.classList.toggle("map-dark", darkTheme);
  elements.legendBox?.classList.toggle("legend-box-dark", darkTheme);
}

function buildLabelMarker(feature, fallbackCenter) {
  const props = feature.properties || {};
  const labelText = props.short_label || props.code || props.name_ru || props.name_en;
  if (!labelText) {
    return null;
  }

  const latLng =
    Number.isFinite(props.label_x) && Number.isFinite(props.label_y)
      ? [props.label_y, props.label_x]
      : [fallbackCenter.lat, fallbackCenter.lng];

  return L.marker(latLng, {
    interactive: false,
    keyboard: false,
    icon: L.divIcon({
      className: "district-label-icon",
      html: `<span class="district-label-chip">${labelText}</span>`,
      iconAnchor: [0, 0],
      iconSize: [0, 0],
    }),
  });
}

function renderLabels() {
  if (!state.geoLayer || !state.map) {
    return;
  }

  const markers = [];
  state.geoLayer.eachLayer((layer) => {
    const marker = buildLabelMarker(layer.feature, layer.getBounds().getCenter());
    if (marker) {
      markers.push(marker);
    }
  });
  state.labelLayer = L.layerGroup(markers).addTo(state.map);
}

function renderCartogram(statePayload, responsePayload) {
  ensureMap();
  clearMapLayers();

  state.currentResult = responsePayload;
  const geojson = responsePayload.geojson || statePayload.cartogram.geojson;
  applyMapTheme(geojson);

  state.geoLayer = L.geoJSON(geojson, {
    style: (feature) => ({
      color: feature.properties.stroke,
      weight: feature.properties.stroke_width,
      fillColor: feature.properties.fill,
      fillOpacity: feature.properties.has_data ? 0.82 : 0.24,
    }),
    onEachFeature: (feature, layer) => {
      layer.bindPopup(feature.properties.tooltip.replace(/\n/g, "<br>"));
      const regionName = feature.properties.name_ru || feature.properties.name_en || "Регион";
      layer.bindTooltip(regionName, {
        sticky: true,
        direction: "top",
        className: "cartogram-hover-tooltip",
      });
    },
  }).addTo(state.map);

  if (shouldRenderLabels(geojson)) {
    renderLabels();
  }

  state.map.fitBounds(state.geoLayer.getBounds(), { padding: [56, 56] });
  state.map.invalidateSize();

  if (elements.mapPlaceholder) {
    elements.mapPlaceholder.style.display = "none";
  }

  elements.mapSubtitle.textContent =
    `Классификация: ${responsePayload.summary.classificationMethod}. ` +
    `Оценка выполнена по показателю ${responsePayload.summary.metricLabel}.`;
  elements.sessionName.value = responsePayload.sessionName;

  renderLegend(responsePayload.legend);
  renderSummary(responsePayload.summary);
  renderAnalysis(responsePayload.summary);
  renderExportLinks(responsePayload.exports, responsePayload.sessionName);
  applyFeatureFilter();
}

async function handleGenerate() {
  if (!state.currentDataset) {
    notify("Сначала выберите или загрузите датасет.", "info");
    return;
  }

  const payload = {
    datasetId: Number(elements.datasetSelect.value),
    regionIdColumn: elements.regionIdColumn.value,
    regionNameColumn: elements.regionNameColumn.value,
    valueColumn: elements.valueColumn.value,
    filterColumn: elements.filterColumn.value,
    filterValue: elements.filterValue.value,
    normalization: elements.normalization.value,
    denominatorColumn: elements.denominatorColumn.value,
    multiplier: Number(elements.multiplier.value || 1),
    aggregation: elements.aggregation.value,
    layerId: Number(elements.layerSelect.value),
    classificationMethod: elements.classificationMethod.value,
    classCount: Number(elements.classCount.value),
    palette: elements.paletteSelect.value,
    sessionName: elements.sessionName.value,
  };

  try {
    elements.generateButton.disabled = true;
    elements.generateButton.textContent = "Формирование...";

    const response = await fetchJson("/api/cartograms/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    renderCartogram(
      {
        dataset: state.currentDataset,
        settings: payload,
        cartogram: response.cartogram,
      },
      {
        ...response.cartogram,
        exports: response.exports,
        sessionId: response.sessionId,
        sessionName: response.sessionName,
      }
    );

    state.bootstrap.sessions = [
      {
        id: response.sessionId,
        name: response.sessionName,
        datasetId: payload.datasetId,
        updatedAt: new Date().toISOString(),
        metricLabel: response.cartogram.summary.metricLabel,
        classificationMethod: response.cartogram.summary.classificationMethod,
      },
      ...(state.bootstrap.sessions || []).filter((session) => session.id !== response.sessionId),
    ];
    renderSessions();
    notify("Картограмма успешно сформирована.", "success");
  } catch (error) {
    notify(error.message, "error");
  } finally {
    elements.generateButton.disabled = false;
    elements.generateButton.textContent = "Сгенерировать картограмму";
  }
}

async function refreshBootstrap() {
  state.bootstrap = await fetchJson("/api/bootstrap", { method: "GET", headers: {} });
  renderSources();
  renderLayers();
  renderPalettes();
  renderDatasets();
  renderSessions();
  requestAnimationFrame(refreshScrollFades);
}

elements.datasetSelect?.addEventListener("change", () => {
  const dataset = (state.bootstrap?.datasets || []).find((item) => String(item.id) === elements.datasetSelect.value);
  if (dataset) {
    renderDataset(dataset);
  }
});

elements.valueColumn?.addEventListener("change", () => {
  if (!state.currentDataset) {
    return;
  }
  if (!elements.sessionName.value || elements.sessionName.value.startsWith(state.currentDataset.name)) {
    elements.sessionName.value = `${state.currentDataset.name} / ${elements.valueColumn.value || "показатель"}`;
  }
});

elements.filterColumn?.addEventListener("change", () => {
  if (!state.currentDataset) {
    return;
  }
  elements.filterValue.value = guessFilterValue(state.currentDataset.schema, elements.filterColumn.value);
});

elements.uploadForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!elements.uploadFile.files.length) {
    notify("Выберите файл для загрузки.", "info");
    return;
  }

  const formData = new FormData();
  formData.append("file", elements.uploadFile.files[0]);
  formData.append("dataset_name", elements.datasetName.value);
  formData.append("description", elements.datasetDescription.value);

  try {
    const response = await fetch("/api/datasets/upload", { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Не удалось загрузить датасет.");
    }

    mergeDatasetIntoBootstrap(payload.dataset);
    renderDatasets();
    elements.datasetSelect.value = String(payload.dataset.id);
    renderDataset(payload.dataset);
    elements.uploadForm.reset();
    notify("Датасет успешно загружен.", "success");
  } catch (error) {
    notify(error.message, "error");
  }
});

elements.generateButton?.addEventListener("click", handleGenerate);

elements.applyRangeFilter?.addEventListener("click", applyFeatureFilter);

elements.resetRangeFilter?.addEventListener("click", () => {
  if (!state.currentResult?.summary) {
    return;
  }
  elements.rangeMin.value = state.currentResult.summary.min;
  elements.rangeMax.value = state.currentResult.summary.max;
  applyFeatureFilter();
});

elements.sourceForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    name: elements.sourceName.value,
    description: elements.sourceDescription.value,
    kind: "url",
    format: elements.sourceFormat.value,
    url: elements.sourceUrl.value,
    filePath: "",
  };

  try {
    await fetchJson("/api/admin/sources", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await refreshBootstrap();
    elements.sourceForm.reset();
    notify("Источник добавлен.", "success");
  } catch (error) {
    notify(error.message, "error");
  }
});

elements.layerForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!elements.layerFile.files.length) {
    notify("Выберите GeoJSON-файл.", "info");
    return;
  }

  const formData = new FormData();
  formData.append("file", elements.layerFile.files[0]);
  formData.append("name", elements.layerName.value);
  formData.append("description", elements.layerDescription.value);

  try {
    const response = await fetch("/api/admin/layers", { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Не удалось загрузить слой.");
    }
    await refreshBootstrap();
    elements.layerForm.reset();
    notify("Слой успешно добавлен.", "success");
  } catch (error) {
    notify(error.message, "error");
  }
});

elements.historyToggle?.addEventListener("click", () => {
  if (elements.historyPopover?.classList.contains("hidden")) {
    openHistoryPopover();
  } else {
    closeHistoryPopover();
  }
});

elements.historyClose?.addEventListener("click", closeHistoryPopover);
elements.historyBackdrop?.addEventListener("click", closeHistoryPopover);
elements.controlColumn?.addEventListener("scroll", refreshScrollFades, { passive: true });
elements.resultColumn?.addEventListener("scroll", refreshScrollFades, { passive: true });
window.addEventListener("resize", refreshScrollFades);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeHistoryPopover();
  }
});

refreshBootstrap()
  .then(() => requestAnimationFrame(refreshScrollFades))
  .catch((error) => notify(error.message, "error"));
