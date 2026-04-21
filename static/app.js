const form = document.getElementById("prediction-form");
const fillExampleButton = document.getElementById("fill-example");
const datasetRowSelect = document.getElementById("dataset-row-select");

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function populateForm(values) {
  Object.entries(values).forEach(([key, value]) => {
    const field = form.elements.namedItem(key);
    if (field) {
      field.value = value;
    }
  });
}

async function submitPrediction(event) {
  event.preventDefault();

  const formData = new FormData(form);
  const payload = {};
  formData.forEach((value, key) => {
    payload[key] = ["crop_type", "region", "soil_type"].includes(key) ? value : Number(value);
  });

  setText("yield-value", "Calculating...");
  setText("yield-band", "Training result is being applied to your current input.");

  const response = await fetch("/api/predict", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const result = await response.json();
  setText("yield-value", `${result.predicted_yield} tons/hectare`);
  setText("yield-band", `${result.yield_band} using ${result.best_model}`);
  setText("merged-yield", `${result.merged_yield} tons/hectare`);
  setText("merged-note", result.merged_note);
  setText("risk-level", result.risk.level);
  setText("risk-score", `Risk score: ${result.risk.score} / 100`);
  setText("factor-rainfall", result.risk.factors.rainfall_deviation);
  setText("factor-temperature", result.risk.factors.temperature_stress);
  setText("factor-soil", result.risk.factors.soil_condition);
  setText("factor-pest", result.risk.factors.pest_risk);

  if (result.dataset_context) {
    setText(
      "dataset-context",
      `Dataset yield: ${result.dataset_context.actual_yield} tons/hectare | Difference from live prediction: ${result.dataset_context.difference}`
    );
  } else {
    setText("dataset-context", "No dataset record selected.");
  }

  const recommendationList = document.getElementById("recommendations");
  recommendationList.innerHTML = "";
  result.recommendations.forEach((item) => {
    const listItem = document.createElement("li");
    listItem.textContent = item;
    recommendationList.appendChild(listItem);
  });
}

async function applyDatasetRow() {
  const rowId = datasetRowSelect.value;
  if (!rowId) {
    return;
  }

  const response = await fetch(`/api/dataset-row/${rowId}`);
  const result = await response.json();
  if (!response.ok) {
    setText("dataset-context", result.error || "Could not load dataset row.");
    return;
  }

  populateForm(result);
  datasetRowSelect.value = rowId;
  setText(
    "dataset-context",
    `Loaded CSV row for ${result.crop_type} in ${result.region}. Original yield: ${result.yield_ton_per_hectare} tons/hectare.`
  );
}

if (form) {
  form.addEventListener("submit", submitPrediction);
}

if (fillExampleButton) {
  fillExampleButton.addEventListener("click", () => populateForm(window.cropAppDefaults));
}

if (datasetRowSelect) {
  datasetRowSelect.addEventListener("change", applyDatasetRow);
}
