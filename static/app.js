const form = document.getElementById("prediction-form");
const fillExampleButton = document.getElementById("fill-example");
const datasetRowSelect = document.getElementById("dataset-row-select");
const recommendCropButton = document.getElementById("recommend-crop");
const resultBox = document.getElementById("result");
const historyBox = document.getElementById("history");
const validationBox = document.getElementById("validation-box");
const yieldChartContainer = document.getElementById("yield-chart-container");
const riskChartContainer = document.getElementById("risk-chart-container");
const trendChartContainer = document.getElementById("trend-chart-container");
const chartContextBanner = document.getElementById("chart-context-banner");
const userMenuToggle = document.getElementById("user-menu-toggle");
const userMenuDropdown = document.getElementById("user-menu-dropdown");
const assistantFab = document.getElementById("assistant-fab");
const assistantChatbot = document.getElementById("assistant-chatbot");
const assistantClose = document.getElementById("assistant-close");
const compareCurrent = document.getElementById("compare-current");
const compareImproved = document.getElementById("compare-improved");
const compareScenariosButton = document.getElementById("compare-scenarios");
const downloadReportButton = document.getElementById("download-report");
const saveChartImageButton = document.getElementById("save-chart-image");
const resetFormButton = document.getElementById("reset-form");
const applyAssistantButton = document.getElementById("apply-assistant");
const assistantRain = document.getElementById("assistant-rain");
const assistantPest = document.getElementById("assistant-pest");
const assistantSoil = document.getElementById("assistant-soil");
const assistantFertilizer = document.getElementById("assistant-fertilizer");
const languageSelect = document.getElementById("language-select");
const themeSelect = document.getElementById("theme-select");
const modeButtons = document.querySelectorAll(".mode-button");
const simpleModePanel = document.getElementById("simple-mode");
const advancedModePanel = document.getElementById("advanced-mode");
const simpleCountry = document.getElementById("simple-country");
const simpleDirection = document.getElementById("simple-direction");
const simpleCrop = document.getElementById("simple-crop");
const simpleRain = document.getElementById("simple-rain");
const simpleFertilizer = document.getElementById("simple-fertilizer");
const simplePest = document.getElementById("simple-pest");
const simplePreviewCard = document.getElementById("simple-preview-card");
let activeMode = "simple";
let currentLanguage = localStorage.getItem("cropAppLanguage") || "en";
let currentTheme = localStorage.getItem("cropAppTheme") || "light";
let lastPrediction = null;

const translations = {
  en: {
    eyebrow_ai_agri: "AI + Agriculture",
    title_main: "Crop Yield Prediction System",
    language: "Language",
    theme: "Theme",
    dark_mode: "Dark Mode",
    light_mode: "Light Mode",
    header_pill: "Working Flask backend + live prediction API",
    logout: "Logout",
    project_goal: "Project Goal",
    hero_heading: "Predict crop yield from environmental and soil conditions.",
    hero_text: "This application trains regression models on a dataset, compares model performance, predicts yield from user input, and classifies overall agricultural risk using a weighted scoring method.",
    try_predictor: "Try Live Predictor",
    dataset_rows: "Dataset Rows",
    crops_covered: "Crops Covered",
    average_yield: "Average Yield",
    best_model: "Best Model",
    model_evaluation: "Model Evaluation",
    trained_compared: "Trained and compared on the dataset",
    live_prediction: "Live Prediction",
    prediction_subtitle: "Use Simple Mode for quick prediction or Advanced Mode for expert analysis",
    risk_formula: "Risk Score = Sum(Weight * Factor Score)",
    simple_mode: "Simple Mode",
    advanced_mode: "Advanced Mode",
    farmer_friendly: "Farmer-friendly input",
    simple_intro: "Pick a country, direction, and broad field conditions. The system will auto-fill technical values from dataset-based regional averages plus location-aware climate adjustments.",
    country: "Country",
    direction: "Direction",
    north: "North",
    south: "South",
    east: "East",
    west: "West",
    crop: "Crop",
    rain_situation: "Rain Situation",
    normal: "Normal",
    low_rain: "Low Rain",
    heavy_rain: "Heavy Rain",
    fertilizer_level: "Fertilizer Level",
    balanced: "Balanced",
    low: "Low",
    medium: "Medium",
    high: "High",
    pest_situation: "Pest Situation",
    autofilled_profile: "Auto-filled Technical Profile",
    select_dataset_record: "Select Dataset Record",
    use_live_input: "Use only live input",
    advanced_help: "Advanced Mode keeps the detailed scientific parameters for research, lab values, and comparative testing.",
    crop_type: "Crop Type",
    region: "Region",
    soil_type: "Soil Type",
    rainfall_mm: "Rainfall (mm)",
    temperature_c: "Temperature (C)",
    humidity_pct: "Humidity (%)",
    soil_ph: "Soil pH",
    nitrogen: "Nitrogen (kg/ha)",
    phosphorus: "Phosphorus (kg/ha)",
    potassium: "Potassium (kg/ha)",
    pest_risk: "Pest Risk (0-10)",
    predict_yield: "Predict Yield",
    recommend_best_crop: "Recommend Best Crop",
    load_example: "Load Example",
    prediction_output: "Prediction Output",
    result_placeholder: "Submit the form to calculate yield potential and risk.",
    prediction_history: "Prediction History",
    recent_predictions: "Your recent prediction results",
    history_empty: "Your prediction history will appear here.",
    dataset_preview: "Dataset Preview",
    example_records: "Example records used for training",
    no_profile: "No matching dataset profile found.",
    simple_mode_note: "Simple Mode uses dataset-based defaults so non-technical users can predict yield without entering lab values.",
    loading_predict: "Predicting... please wait",
    loading_recommend: "Finding best crop...",
    error_prediction: "Error in prediction",
    error_recommend: "Could not recommend a crop",
    history_load_error: "Could not load prediction history.",
    history_crop_unknown: "Unknown crop",
    history_risk_unknown: "Unknown",
    dataset_yield: "Dataset Yield",
    difference: "Difference",
    not_selected: "Not selected",
    model: "Model",
    risk_level: "Risk Level",
    score: "Score",
    recommended_crop: "Recommended Crop",
    merged_yield: "Merged Yield",
    rainfall_deviation: "Rainfall Deviation",
    temperature_stress: "Temperature Stress",
    soil_condition: "Soil Condition",
    recommendations: "Recommendations",
    best_crop: "Best Crop",
    match_score: "Match Score",
    all_crop_predictions: "All Crop Predictions",
    dataset_row_loaded: "Dataset row loaded",
    original_yield: "Original Yield",
    dataset_loaded_note: "Now run prediction or crop recommendation using this row as context.",
    load_dataset_error: "Could not load dataset row.",
    preview_country: "Country",
    preview_direction: "Direction",
    preview_region: "Mapped Region",
    preview_soil: "Soil Type",
    preview_rainfall: "Rainfall",
    preview_temperature: "Temperature",
    preview_humidity: "Humidity",
    preview_soil_ph: "Soil pH",
    preview_pest: "Pest Risk",
    preview_location_note: "Location Note",
    preview_climate_logic: "Climate Logic",
    language_label: "हिंदी"
  },
  hi: {
    eyebrow_ai_agri: "एआई + कृषि",
    title_main: "फसल उपज पूर्वानुमान प्रणाली",
    language: "भाषा",
    theme: "थीम",
    dark_mode: "डार्क मोड",
    light_mode: "लाइट मोड",
    header_pill: "वर्किंग फ्लास्क बैकएंड + लाइव प्रेडिक्शन एपीआई",
    logout: "लॉगआउट",
    project_goal: "परियोजना उद्देश्य",
    hero_heading: "पर्यावरण और मिट्टी की स्थितियों से फसल उपज का अनुमान लगाएं।",
    hero_text: "यह एप्लिकेशन डेटासेट पर रिग्रेशन मॉडल ट्रेन करता है, उनके प्रदर्शन की तुलना करता है, उपयोगकर्ता इनपुट से उपज का अनुमान लगाता है और वेटेड स्कोरिंग विधि से कृषि जोखिम को वर्गीकृत करता है।",
    try_predictor: "लाइव प्रेडिक्टर आज़माएं",
    dataset_rows: "डेटासेट पंक्तियाँ",
    crops_covered: "कवर की गई फसलें",
    average_yield: "औसत उपज",
    best_model: "सर्वश्रेष्ठ मॉडल",
    model_evaluation: "मॉडल मूल्यांकन",
    trained_compared: "डेटासेट पर प्रशिक्षित और तुलना की गई",
    live_prediction: "लाइव पूर्वानुमान",
    prediction_subtitle: "त्वरित पूर्वानुमान के लिए सिंपल मोड या विशेषज्ञ विश्लेषण के लिए एडवांस्ड मोड का उपयोग करें",
    risk_formula: "जोखिम स्कोर = योग(वेट × फैक्टर स्कोर)",
    simple_mode: "सिंपल मोड",
    advanced_mode: "एडवांस्ड मोड",
    farmer_friendly: "किसान-अनुकूल इनपुट",
    simple_intro: "देश, दिशा और खेत की सामान्य स्थिति चुनें। सिस्टम डेटासेट आधारित क्षेत्रीय औसत और लोकेशन समायोजन से तकनीकी मान स्वतः भरेगा।",
    country: "देश",
    direction: "दिशा",
    north: "उत्तर",
    south: "दक्षिण",
    east: "पूर्व",
    west: "पश्चिम",
    crop: "फसल",
    rain_situation: "वर्षा स्थिति",
    normal: "सामान्य",
    low_rain: "कम वर्षा",
    heavy_rain: "अधिक वर्षा",
    fertilizer_level: "उर्वरक स्तर",
    balanced: "संतुलित",
    low: "कम",
    medium: "मध्यम",
    high: "उच्च",
    pest_situation: "कीट स्थिति",
    autofilled_profile: "स्वतः भरी तकनीकी प्रोफ़ाइल",
    select_dataset_record: "डेटासेट रिकॉर्ड चुनें",
    use_live_input: "केवल लाइव इनपुट उपयोग करें",
    advanced_help: "एडवांस्ड मोड रिसर्च, लैब वैल्यू और तुलना परीक्षण के लिए विस्तृत वैज्ञानिक पैरामीटर रखता है।",
    crop_type: "फसल प्रकार",
    region: "क्षेत्र",
    soil_type: "मिट्टी प्रकार",
    rainfall_mm: "वर्षा (मिमी)",
    temperature_c: "तापमान (C)",
    humidity_pct: "आर्द्रता (%)",
    soil_ph: "मिट्टी pH",
    nitrogen: "नाइट्रोजन (किग्रा/हेक्टेयर)",
    phosphorus: "फॉस्फोरस (किग्रा/हेक्टेयर)",
    potassium: "पोटैशियम (किग्रा/हेक्टेयर)",
    pest_risk: "कीट जोखिम (0-10)",
    predict_yield: "उपज का अनुमान लगाएं",
    recommend_best_crop: "सर्वश्रेष्ठ फसल सुझाएं",
    load_example: "उदाहरण लोड करें",
    prediction_output: "पूर्वानुमान परिणाम",
    result_placeholder: "उपज क्षमता और जोखिम निकालने के लिए फॉर्म सबमिट करें।",
    prediction_history: "पूर्वानुमान इतिहास",
    recent_predictions: "आपके हाल के पूर्वानुमान परिणाम",
    history_empty: "आपका पूर्वानुमान इतिहास यहां दिखाई देगा।",
    dataset_preview: "डेटासेट पूर्वावलोकन",
    example_records: "प्रशिक्षण के लिए उपयोग किए गए उदाहरण रिकॉर्ड",
    no_profile: "मिलती हुई डेटासेट प्रोफ़ाइल नहीं मिली।",
    simple_mode_note: "सिंपल मोड डेटासेट आधारित डिफ़ॉल्ट उपयोग करता है ताकि बिना लैब वैल्यू के भी पूर्वानुमान किया जा सके।",
    loading_predict: "पूर्वानुमान किया जा रहा है... कृपया प्रतीक्षा करें",
    loading_recommend: "सर्वश्रेष्ठ फसल खोजी जा रही है...",
    error_prediction: "पूर्वानुमान में त्रुटि",
    error_recommend: "फसल सुझाव नहीं मिल सका",
    history_load_error: "पूर्वानुमान इतिहास लोड नहीं हो सका।",
    history_crop_unknown: "अज्ञात फसल",
    history_risk_unknown: "अज्ञात",
    dataset_yield: "डेटासेट उपज",
    difference: "अंतर",
    not_selected: "चयनित नहीं",
    model: "मॉडल",
    risk_level: "जोखिम स्तर",
    score: "स्कोर",
    recommended_crop: "अनुशंसित फसल",
    merged_yield: "मर्ज उपज",
    rainfall_deviation: "वर्षा विचलन",
    temperature_stress: "तापमान तनाव",
    soil_condition: "मिट्टी की स्थिति",
    recommendations: "सुझाव",
    best_crop: "सर्वश्रेष्ठ फसल",
    match_score: "मैच स्कोर",
    all_crop_predictions: "सभी फसल परिणाम",
    dataset_row_loaded: "डेटासेट पंक्ति लोड हो गई",
    original_yield: "मूल उपज",
    dataset_loaded_note: "अब इस पंक्ति को संदर्भ बनाकर पूर्वानुमान या फसल सुझाव चलाएं।",
    load_dataset_error: "डेटासेट पंक्ति लोड नहीं हो सकी।",
    preview_country: "देश",
    preview_direction: "दिशा",
    preview_region: "मैप किया गया क्षेत्र",
    preview_soil: "मिट्टी प्रकार",
    preview_rainfall: "वर्षा",
    preview_temperature: "तापमान",
    preview_humidity: "आर्द्रता",
    preview_soil_ph: "मिट्टी pH",
    preview_pest: "कीट जोखिम",
    preview_location_note: "स्थान टिप्पणी",
    preview_climate_logic: "जलवायु तर्क",
    language_label: "English"
  }
};

function t(key) {
  return translations[currentLanguage]?.[key] || translations.en[key] || key;
}

function applyTheme(theme) {
  currentTheme = theme;
  document.body.classList.toggle("dark-mode", theme === "dark");
  localStorage.setItem("cropAppTheme", theme);
  if (themeSelect) {
    themeSelect.value = theme;
  }
}

function applyLanguage(language) {
  currentLanguage = language;
  localStorage.setItem("cropAppLanguage", language);

  document.documentElement.lang = language === "hi" ? "hi" : "en";
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    if (element.tagName === "OPTION") {
      element.textContent = t(key);
      return;
    }
    element.textContent = t(key);
  });

  if (languageSelect) {
    languageSelect.value = language;
  }
  if (themeSelect) {
    themeSelect.value = currentTheme;
  }

  renderSimplePreview();
}

function getFormData() {
  if (activeMode === "simple") {
    return getSimpleModePayload();
  }

  const formData = new FormData(form);
  const payload = {};
  formData.forEach((value, key) => {
    payload[key] = ["crop_type", "region", "soil_type"].includes(key) ? value : Number(value);
  });
  return payload;
}

function getProfile(crop, region) {
  const cropProfiles = window.simpleProfiles?.[crop];
  if (cropProfiles?.[region]) {
    return cropProfiles[region];
  }

  const fallbackRegion = cropProfiles ? Object.keys(cropProfiles)[0] : null;
  return fallbackRegion ? cropProfiles[fallbackRegion] : null;
}

function getLocationProfile(country, direction) {
  const countryProfile = window.locationProfiles?.[country];
  if (!countryProfile) {
    return null;
  }

  const selectedDirection = countryProfile.directions?.[direction];
  if (selectedDirection) {
    return {
      country,
      direction,
      description: countryProfile.description,
      adjustments: countryProfile.adjustments || {},
      ...selectedDirection,
    };
  }

  const fallbackDirection = Object.keys(countryProfile.directions || {})[0];
  if (!fallbackDirection) {
    return null;
  }

  return {
    country,
    direction: fallbackDirection,
    description: countryProfile.description,
    adjustments: countryProfile.adjustments || {},
    ...countryProfile.directions[fallbackDirection],
  };
}

function buildSimpleProfile() {
  const locationProfile = getLocationProfile(simpleCountry.value, simpleDirection.value);
  if (!locationProfile) {
    return null;
  }

  const profile = getProfile(simpleCrop.value, locationProfile.region);
  if (!profile) {
    return null;
  }

  const adjusted = { ...profile };
  adjusted.country = locationProfile.country;
  adjusted.direction = locationProfile.direction;
  adjusted.location_summary = locationProfile.summary;
  adjusted.location_description = locationProfile.description;
  adjusted.region = locationProfile.region;

  const countryAdjustments = locationProfile.adjustments || {};
  adjusted.rainfall_mm = Number(adjusted.rainfall_mm) + Number(countryAdjustments.rainfall_mm || 0);
  adjusted.temperature_c = Number(adjusted.temperature_c) + Number(countryAdjustments.temperature_c || 0);
  adjusted.humidity_pct = Number(adjusted.humidity_pct) + Number(countryAdjustments.humidity_pct || 0);
  adjusted.soil_ph = Number(adjusted.soil_ph) + Number(countryAdjustments.soil_ph || 0);
  adjusted.nitrogen_kg_ha = Number(adjusted.nitrogen_kg_ha) + Number(countryAdjustments.nitrogen_kg_ha || 0);
  adjusted.phosphorus_kg_ha = Number(adjusted.phosphorus_kg_ha) + Number(countryAdjustments.phosphorus_kg_ha || 0);
  adjusted.potassium_kg_ha = Number(adjusted.potassium_kg_ha) + Number(countryAdjustments.potassium_kg_ha || 0);

  const rainAdjustment = { low: -140, normal: 0, high: 140 };
  adjusted.rainfall_mm = Number(adjusted.rainfall_mm) + rainAdjustment[simpleRain.value];

  const fertilizerAdjustment = { low: -18, medium: 0, high: 18 };
  const nutrientShift = fertilizerAdjustment[simpleFertilizer.value];
  adjusted.nitrogen_kg_ha = Number(adjusted.nitrogen_kg_ha) + nutrientShift;
  adjusted.phosphorus_kg_ha = Number(adjusted.phosphorus_kg_ha) + nutrientShift * 0.6;
  adjusted.potassium_kg_ha = Number(adjusted.potassium_kg_ha) + nutrientShift * 0.7;

  const pestMap = { low: 2.5, medium: 5.0, high: 7.5 };
  adjusted.pest_risk = pestMap[simplePest.value];

  return adjusted;
}

function getSimpleModePayload() {
  const profile = buildSimpleProfile();
  if (!profile) {
    return {};
  }

  return {
    dataset_row_id: "",
    crop_type: profile.crop_type,
    region: profile.region,
    soil_type: profile.soil_type,
    country: profile.country,
    direction: profile.direction,
    rainfall_mm: Number(profile.rainfall_mm),
    temperature_c: Number(profile.temperature_c),
    humidity_pct: Number(profile.humidity_pct),
    soil_ph: Number(profile.soil_ph),
    nitrogen_kg_ha: Number(profile.nitrogen_kg_ha),
    phosphorus_kg_ha: Number(profile.phosphorus_kg_ha),
    potassium_kg_ha: Number(profile.potassium_kg_ha),
    pest_risk: Number(profile.pest_risk),
  };
}

function renderSimplePreview() {
  if (!simplePreviewCard) {
    return;
  }

  const profile = buildSimpleProfile();
  if (!profile) {
    simplePreviewCard.innerHTML = `<div>${t("no_profile")}</div>`;
    return;
  }

  simplePreviewCard.innerHTML = `
    <div><span>${t("preview_country")}</span><strong>${profile.country}</strong></div>
    <div><span>${t("preview_direction")}</span><strong>${profile.direction}</strong></div>
    <div><span>${t("preview_region")}</span><strong>${profile.region}</strong></div>
    <div><span>${t("preview_soil")}</span><strong>${profile.soil_type}</strong></div>
    <div><span>${t("preview_rainfall")}</span><strong>${Math.round(profile.rainfall_mm)} mm</strong></div>
    <div><span>${t("preview_temperature")}</span><strong>${Math.round(profile.temperature_c)} C</strong></div>
    <div><span>${t("preview_humidity")}</span><strong>${Math.round(profile.humidity_pct)} %</strong></div>
    <div><span>${t("preview_soil_ph")}</span><strong>${profile.soil_ph}</strong></div>
    <div><span>${t("preview_pest")}</span><strong>${profile.pest_risk}</strong></div>
    <div class="preview-wide"><span>${t("preview_location_note")}</span><strong>${profile.location_summary}</strong></div>
    <div class="preview-wide"><span>${t("preview_climate_logic")}</span><strong>${profile.location_description}</strong></div>
  `;
}

function setMode(mode) {
  activeMode = mode;
  modeButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.mode === mode);
  });

  simpleModePanel.classList.toggle("is-active", mode === "simple");
  advancedModePanel.classList.toggle("is-active", mode === "advanced");

  if (mode === "simple") {
    renderSimplePreview();
    resultBox.innerHTML = `<div class="result-placeholder">${t("simple_mode_note")}</div>`;
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

function showLoading(message) {
  resultBox.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p>${message}</p>
    </div>
  `;
}

function showError(message) {
  resultBox.innerHTML = `<div class="result-error">${message}</div>`;
}

function showValidationErrors(errors = []) {
  if (!validationBox) {
    return;
  }

  if (!errors.length) {
    validationBox.innerHTML = "";
    validationBox.classList.remove("is-visible");
    return;
  }

  validationBox.innerHTML = `<ul>${errors.map((item) => `<li>${item}</li>`).join("")}</ul>`;
  validationBox.classList.add("is-visible");
}

function updateChartContext(payload, predictionData = null) {
  if (!chartContextBanner) {
    return;
  }

  const crop = payload?.crop_type || "Unknown crop";
  const region = payload?.region || "Unknown region";
  const yieldText = predictionData?.predicted_yield ? ` Predicted yield: ${predictionData.predicted_yield} ton/hectare.` : "";
  chartContextBanner.textContent = `Last predicted for: ${crop} in ${region}.${yieldText} Charts are now aligned with the latest input.`;
}

function buildImprovedScenario(payload) {
  return {
    ...payload,
    pest_risk: Math.max(0, Number(payload.pest_risk) - 2),
    nitrogen_kg_ha: Number(payload.nitrogen_kg_ha) + 12,
    phosphorus_kg_ha: Number(payload.phosphorus_kg_ha) + 8,
    potassium_kg_ha: Number(payload.potassium_kg_ha) + 8,
    soil_ph: Math.min(7.0, Number(payload.soil_ph) + 0.2),
  };
}

function renderCompareCards(result) {
  if (!compareCurrent || !compareImproved) {
    return;
  }

  compareCurrent.innerHTML = `
    <h4>${result.current.crop_type}</h4>
    <p>${result.current.region}</p>
    <strong>${result.current.predicted_yield} ton/hectare</strong>
    <span class="compare-metric">Risk: ${result.current.risk.level}</span>
    <span class="compare-metric">Confidence: ${result.current.confidence.score}%</span>
  `;
  compareImproved.innerHTML = `
    <h4>${result.improved.crop_type}</h4>
    <p>${result.improved.region}</p>
    <strong>${result.improved.predicted_yield} ton/hectare</strong>
    <span class="compare-metric">Risk: ${result.improved.risk.level}</span>
    <span class="compare-metric">Confidence: ${result.improved.confidence.score}%</span>
    <span class="compare-highlight">Yield gain: ${result.yield_gain} | Risk reduction: ${result.risk_reduction}</span>
  `;
}

function renderPlotlyFigure(container, figure, chartKey) {
  if (!container || !figure || typeof Plotly === "undefined") {
    return;
  }

  let plotNode = container.querySelector(`[data-chart-key="${chartKey}"]`);
  if (!plotNode) {
    container.innerHTML = `<div class="dynamic-chart" data-chart-key="${chartKey}"></div>`;
    plotNode = container.querySelector(`[data-chart-key="${chartKey}"]`);
  }

  Plotly.react(plotNode, figure.data || [], figure.layout || {}, {
    responsive: true,
    displayModeBar: false,
  });
}

async function updateContextCharts(payload, predictionData = null) {
  if (!yieldChartContainer || !riskChartContainer || !trendChartContainer) {
    return;
  }

  const response = await fetch("/api/context-figures", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      current_input: payload,
      predicted_yield: predictionData?.predicted_yield ?? null,
      risk: predictionData?.risk ?? null,
    }),
  });

  if (!response.ok) {
    return;
  }

  const figures = await response.json();
  renderPlotlyFigure(yieldChartContainer, figures.yield_by_crop, "yield");
  renderPlotlyFigure(riskChartContainer, figures.risk_distribution, "risk");
  renderPlotlyFigure(trendChartContainer, figures.trend, "trend");
}

function renderPredictionResult(data) {
  const recommendationItems = data.recommendations.map((item) => `<li>${item}</li>`).join("");
  const insightItems = (data.insights || []).map((item) => `<li>${item}</li>`).join("");
  const actionCards = (data.action_cards || [])
    .map(
      (card) => `
        <article class="action-card ${card.tone}">
          <span class="action-icon">${card.icon}</span>
          <div>
            <h5>${card.title}</h5>
            <p>${card.detail}</p>
          </div>
        </article>
      `
    )
    .join("");
  const datasetInfo = data.dataset_context
    ? `<p><b>${t("dataset_yield")}:</b> ${data.dataset_context.actual_yield} ton/hectare</p>
       <p><b>${t("difference")}:</b> ${data.dataset_context.difference}</p>`
    : `<p><b>${t("dataset_yield")}:</b> ${t("not_selected")}</p>`;

  resultBox.innerHTML = `
    <div class="result-summary reveal-in">
      <div class="insight-banner">${data.insights?.[0] || "Prediction prepared successfully."}</div>
      <div class="result-headline">
        <div>
          <h2>${data.predicted_yield} ton/hectare</h2>
          <span class="risk-badge ${String(data.risk.level).toLowerCase()}">${data.risk.level}</span>
        </div>
        <div class="confidence-meter">
          <span>Confidence</span>
          <div class="confidence-track"><div class="confidence-fill" style="width:${data.confidence.score}%"></div></div>
          <strong>${data.confidence.score}%</strong>
        </div>
      </div>
      <p><b>${t("model")}:</b> ${data.best_model}</p>
      <p><b>${t("risk_level")}:</b> ${data.risk.level}</p>
      <p><b>${t("score")}:</b> ${data.risk.score}</p>
      <p><b>${t("recommended_crop")}:</b> ${data.recommended_crop}</p>
      <p><b>${t("merged_yield")}:</b> ${data.merged_yield} ton/hectare</p>
      ${datasetInfo}
      <p><b>${t("rainfall_deviation")}:</b> ${data.risk.factors.rainfall_deviation}</p>
      <p><b>${t("temperature_stress")}:</b> ${data.risk.factors.temperature_stress}</p>
      <p><b>${t("soil_condition")}:</b> ${data.risk.factors.soil_condition}</p>
      <p><b>${t("pest_risk")}:</b> ${data.risk.factors.pest_risk}</p>
      <div class="action-grid">${actionCards}</div>
      <div class="insight-list">
        <h4>Field Insights</h4>
        <ul>${insightItems}</ul>
      </div>
      <h4>${t("recommendations")}</h4>
      <ul>
        ${recommendationItems}
      </ul>
    </div>
  `;
}

function renderRecommendationResult(data) {
  const items = data.all_predictions
    .map(([crop, score]) => `<li>${crop}: ${t("match_score").toLowerCase()} ${score}</li>`)
    .join("");

  resultBox.innerHTML = `
    <div class="result-summary recommendation-mode">
      <h2>${t("best_crop")}: ${data.recommended_crop}</h2>
      <p><b>${t("match_score")}:</b> ${data.match_score}</p>
      <h4>${t("all_crop_predictions")}</h4>
      <ul>
        ${items}
      </ul>
    </div>
  `;
}

async function submitPrediction(event) {
  event.preventDefault();
  const payload = getFormData();
  const validationErrors = [];
  if (!payload.crop_type) validationErrors.push("Please choose a crop.");
  if (!payload.region) validationErrors.push("Please choose a region.");
  if (Number(payload.humidity_pct) < 0 || Number(payload.humidity_pct) > 100) validationErrors.push("Humidity should be between 0 and 100.");
  if (Number(payload.pest_risk) < 0 || Number(payload.pest_risk) > 10) validationErrors.push("Pest risk should be between 0 and 10.");
  showValidationErrors(validationErrors);
  if (validationErrors.length) {
    showError("Please fix the input issues before predicting.");
    return;
  }

  showLoading(t("loading_predict"));

  const response = await fetch("/api/predict", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    showValidationErrors(errorData.validation_errors || []);
    showError(t("error_prediction"));
    return;
  }

  const result = await response.json();
  lastPrediction = { payload, result };
  showValidationErrors([]);
  renderPredictionResult(result);
  updateContextCharts(payload, result);
  updateChartContext(payload, result);
  loadHistory();
}

async function recommendCrop() {
  const payload = getFormData();
  showLoading(t("loading_recommend"));

  const response = await fetch("/api/recommend-crop", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    showError(t("error_recommend"));
    return;
  }

  const result = await response.json();
  renderRecommendationResult(result);
  updateContextCharts(payload);
  updateChartContext(payload);
}

async function loadHistory() {
  const response = await fetch("/api/history");
  if (!response.ok) {
    historyBox.innerHTML = `<div class="history-empty">${t("history_load_error")}</div>`;
    return;
  }

  const data = await response.json();
  if (!data.length) {
    historyBox.innerHTML = `<div class="history-empty">${t("history_empty")}</div>`;
    return;
  }

  historyBox.innerHTML = data
    .map(
      (item) => `
        <div class="history-item">
          <strong>${item.crop || t("history_crop_unknown")}</strong>
          <span>${item.yield ?? "N/A"} ton/hectare</span>
          <span>${item.risk || t("history_risk_unknown")}</span>
        </div>
      `
    )
    .join("");
}

async function applyDatasetRow() {
  const rowId = datasetRowSelect.value;
  if (!rowId) {
    resultBox.innerHTML = `<div class="result-placeholder">${t("result_placeholder")}</div>`;
    return;
  }

  const response = await fetch(`/api/dataset-row/${rowId}`);
  const result = await response.json();
  if (!response.ok) {
    showError(result.error || t("load_dataset_error"));
    return;
  }

  populateForm(result);
  datasetRowSelect.value = rowId;
  resultBox.innerHTML = `
    <div class="result-summary">
      <h2>${t("dataset_row_loaded")}</h2>
      <p><b>${t("crop")}:</b> ${result.crop_type}</p>
      <p><b>${t("region")}:</b> ${result.region}</p>
      <p><b>${t("original_yield")}:</b> ${result.yield_ton_per_hectare} ton/hectare</p>
      <p>${t("dataset_loaded_note")}</p>
    </div>
  `;
  updateContextCharts(getFormData());
  updateChartContext(getFormData());
}

function applyAssistantSelections() {
  if (simpleRain) simpleRain.value = assistantRain.value;
  if (simplePest) simplePest.value = assistantPest.value;
  if (simpleFertilizer) simpleFertilizer.value = assistantFertilizer.value;
  if (assistantSoil?.value) {
    const soilField = form.elements.namedItem("soil_type");
    if (soilField) {
      soilField.value = assistantSoil.value;
    }
  }
  renderSimplePreview();
  resultBox.innerHTML = `<div class="result-placeholder reveal-in">Assistant applied your current field conditions. You can predict immediately now.</div>`;
  if (assistantChatbot) {
    assistantChatbot.classList.remove("is-open");
  }
}

function resetPredictionExperience() {
  showValidationErrors([]);
  populateForm(window.cropAppDefaults);
  if (datasetRowSelect) datasetRowSelect.value = "";
  if (simpleCountry) simpleCountry.selectedIndex = 0;
  if (simpleDirection) simpleDirection.value = "South";
  if (simpleCrop) simpleCrop.value = window.cropAppDefaults.crop_type;
  if (simpleRain) simpleRain.value = "normal";
  if (simpleFertilizer) simpleFertilizer.value = "medium";
  if (simplePest) simplePest.value = "low";
  renderSimplePreview();
  resultBox.innerHTML = `<div class="result-placeholder">${t("result_placeholder")}</div>`;
  if (compareCurrent) compareCurrent.innerHTML = "Run a prediction to capture the current scenario.";
  if (compareImproved) compareImproved.innerHTML = "Use the compare button after prediction to test a better scenario.";
  if (chartContextBanner) {
    chartContextBanner.textContent = "Last predicted for: no live prediction yet. The charts below will react to your latest input.";
  }
  lastPrediction = null;
}

async function compareScenarios() {
  if (!lastPrediction) {
    showError("Run one prediction first so the app can compare scenarios.");
    return;
  }

  const response = await fetch("/api/compare-scenarios", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      current_input: lastPrediction.payload,
      improved_input: buildImprovedScenario(lastPrediction.payload),
    }),
  });

  if (!response.ok) {
    showError("Scenario comparison could not be generated.");
    return;
  }

  const result = await response.json();
  renderCompareCards(result);
}

async function downloadReport() {
  if (!lastPrediction) {
    showError("Run a prediction first so a report can be created.");
    return;
  }

  const reportData = {
    crop_type: lastPrediction.payload.crop_type,
    region: lastPrediction.payload.region,
    predicted_yield: lastPrediction.result.predicted_yield,
    risk_level: lastPrediction.result.risk.level,
    confidence_score: lastPrediction.result.confidence.score,
    confidence_label: lastPrediction.result.confidence.label,
    recommended_crop: lastPrediction.result.recommended_crop,
    action_cards: lastPrediction.result.action_cards,
    insights: lastPrediction.result.insights,
    recommendations: lastPrediction.result.recommendations,
  };

  const response = await fetch("/api/export-report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report_data: reportData }),
  });

  if (!response.ok) {
    showError("Report export failed.");
    return;
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "crop_yield_report.html";
  link.click();
  URL.revokeObjectURL(url);
}

function saveTrendChartImage() {
  if (typeof Plotly === "undefined") {
    return;
  }
  const chart = trendChartContainer?.querySelector(".dynamic-chart, .plotly-graph-div");
  if (!chart) {
    showError("Generate the trend chart first before saving an image.");
    return;
  }
  Plotly.downloadImage(chart, { format: "png", filename: "rainfall_yield_trend" });
}

if (languageSelect) {
  languageSelect.addEventListener("change", (event) => {
    applyLanguage(event.target.value);
  });
}

if (themeSelect) {
  themeSelect.addEventListener("change", (event) => {
    applyTheme(event.target.value);
  });
}

if (applyAssistantButton) {
  applyAssistantButton.addEventListener("click", applyAssistantSelections);
}

if (assistantFab) {
  assistantFab.addEventListener("click", () => {
    assistantChatbot?.classList.toggle("is-open");
  });
}

if (assistantClose) {
  assistantClose.addEventListener("click", () => {
    assistantChatbot?.classList.remove("is-open");
  });
}

if (userMenuToggle) {
  userMenuToggle.addEventListener("click", () => {
    userMenuDropdown?.classList.toggle("is-open");
  });
}

document.addEventListener("click", (event) => {
  if (!userMenuDropdown || !userMenuToggle) {
    return;
  }

  if (!userMenuDropdown.contains(event.target) && !userMenuToggle.contains(event.target)) {
    userMenuDropdown.classList.remove("is-open");
  }
});

if (resetFormButton) {
  resetFormButton.addEventListener("click", resetPredictionExperience);
}

if (compareScenariosButton) {
  compareScenariosButton.addEventListener("click", compareScenarios);
}

if (downloadReportButton) {
  downloadReportButton.addEventListener("click", downloadReport);
}

if (saveChartImageButton) {
  saveChartImageButton.addEventListener("click", saveTrendChartImage);
}

if (form) {
  form.addEventListener("submit", submitPrediction);
}

if (fillExampleButton) {
  fillExampleButton.addEventListener("click", () => populateForm(window.cropAppDefaults));
}

if (recommendCropButton) {
  recommendCropButton.addEventListener("click", recommendCrop);
}

if (datasetRowSelect) {
  datasetRowSelect.addEventListener("change", applyDatasetRow);
}

modeButtons.forEach((button) => {
  button.addEventListener("click", () => setMode(button.dataset.mode));
});

[simpleCountry, simpleDirection, simpleCrop, simpleRain, simpleFertilizer, simplePest].forEach((field) => {
  if (field) {
    field.addEventListener("change", renderSimplePreview);
  }
});

applyTheme(currentTheme);
applyLanguage(currentLanguage);
loadHistory();
