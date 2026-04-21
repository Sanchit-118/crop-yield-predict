from __future__ import annotations

import json
import os
import sqlite3
import sys
from io import StringIO
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = BASE_DIR / ".packages"
if PACKAGE_DIR.exists():
    sys.path.insert(0, str(PACKAGE_DIR))

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
import numpy as np
import pandas as pd
import plotly.express as px
from werkzeug.security import check_password_hash, generate_password_hash
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from generate_dataset import ensure_dataset


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "crop-yield-demo-secret-key")

DATASET_PATH = BASE_DIR / "data" / "crop_yield_dataset.csv"
CUSTOM_DATASET_PATH = BASE_DIR / "data" / "custom_crop_yield_dataset.csv"
DB_PATH = BASE_DIR / "data" / "users.db"
FEATURE_COLUMNS = [
    "crop_type",
    "region",
    "soil_type",
    "rainfall_mm",
    "temperature_c",
    "humidity_pct",
    "soil_ph",
    "nitrogen_kg_ha",
    "phosphorus_kg_ha",
    "potassium_kg_ha",
    "pest_risk",
]
CATEGORICAL_COLUMNS = ["crop_type", "region", "soil_type"]
NUMERICAL_COLUMNS = [column for column in FEATURE_COLUMNS if column not in CATEGORICAL_COLUMNS]

RISK_WEIGHTS = {
    "rainfall_deviation": 0.30,
    "temperature_stress": 0.25,
    "soil_condition": 0.25,
    "pest_risk": 0.20,
}

IDEAL_GROWTH = {
    "Rice": {"rainfall_mm": 1120, "temperature_c": 28, "soil_ph": 6.1},
    "Wheat": {"rainfall_mm": 620, "temperature_c": 21, "soil_ph": 6.7},
    "Maize": {"rainfall_mm": 760, "temperature_c": 25, "soil_ph": 6.3},
    "Cotton": {"rainfall_mm": 680, "temperature_c": 29, "soil_ph": 6.8},
    "Sugarcane": {"rainfall_mm": 1240, "temperature_c": 30, "soil_ph": 6.6},
}


@dataclass
class ModelResult:
    name: str
    pipeline: Pipeline
    rmse: float
    mae: float
    r2: float


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_auth_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = get_db_connection()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def get_current_user() -> dict[str, str] | None:
    user_id = session.get("user_id")
    if not user_id:
        return None

    connection = get_db_connection()
    try:
        row = connection.execute(
            "SELECT id, full_name, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        connection.close()

    return dict(row) if row else None


def safe_float(value: float) -> float:
    return float(round(value, 3))


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS),
            ("numerical", StandardScaler(), NUMERICAL_COLUMNS),
        ]
    )


def evaluate_models(dataframe: pd.DataFrame) -> dict[str, object]:
    x = dataframe[FEATURE_COLUMNS]
    y = dataframe["yield_ton_per_hectare"]

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42
    )

    candidates = [
        ("Linear Regression", LinearRegression()),
        ("Random Forest", RandomForestRegressor(n_estimators=220, random_state=42, max_depth=12)),
    ]

    results: list[ModelResult] = []
    for name, estimator in candidates:
        pipeline = Pipeline(
            steps=[
                ("preprocessor", build_preprocessor()),
                ("model", estimator),
            ]
        )
        pipeline.fit(x_train, y_train)
        predictions = pipeline.predict(x_test)
        results.append(
            ModelResult(
                name=name,
                pipeline=pipeline,
                rmse=safe_float(np.sqrt(mean_squared_error(y_test, predictions))),
                mae=safe_float(mean_absolute_error(y_test, predictions)),
                r2=safe_float(r2_score(y_test, predictions)),
            )
        )

    best_model = max(results, key=lambda result: result.r2)
    return {
        "results": results,
        "best_model": best_model,
        "x_test": x_test,
        "y_test": y_test,
    }


def get_active_dataset_path() -> Path:
    return CUSTOM_DATASET_PATH if CUSTOM_DATASET_PATH.exists() else DATASET_PATH


def validate_dataset(dataframe: pd.DataFrame) -> tuple[bool, str | None]:
    expected_columns = FEATURE_COLUMNS + ["yield_ton_per_hectare"]
    missing_columns = [column for column in expected_columns if column not in dataframe.columns]
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"

    if len(dataframe) < 30:
        return False, "Dataset must contain at least 30 rows for training."

    try:
        numeric_columns = [
            "rainfall_mm",
            "temperature_c",
            "humidity_pct",
            "soil_ph",
            "nitrogen_kg_ha",
            "phosphorus_kg_ha",
            "potassium_kg_ha",
            "pest_risk",
            "yield_ton_per_hectare",
        ]
        dataframe[numeric_columns] = dataframe[numeric_columns].apply(pd.to_numeric)
    except Exception:
        return False, "Numeric columns contain invalid values."

    supported_crops = set(IDEAL_GROWTH.keys())
    found_crops = set(dataframe["crop_type"].astype(str).unique())
    unsupported_crops = sorted(found_crops - supported_crops)
    if unsupported_crops:
        return False, (
            "Unsupported crop_type values found: "
            + ", ".join(unsupported_crops)
            + ". Supported crops are: "
            + ", ".join(sorted(supported_crops))
        )

    return True, None


def calculate_risk(inputs: dict[str, float | str]) -> dict[str, object]:
    profile = IDEAL_GROWTH[str(inputs["crop_type"])]

    rainfall_deviation = min(abs(float(inputs["rainfall_mm"]) - profile["rainfall_mm"]) / 600, 1.0)
    temperature_stress = min(abs(float(inputs["temperature_c"]) - profile["temperature_c"]) / 15, 1.0)
    soil_condition = min(abs(float(inputs["soil_ph"]) - profile["soil_ph"]) / 2.5, 1.0)
    pest_risk = min(float(inputs["pest_risk"]) / 10, 1.0)

    factor_scores = {
        "rainfall_deviation": rainfall_deviation,
        "temperature_stress": temperature_stress,
        "soil_condition": soil_condition,
        "pest_risk": pest_risk,
    }
    weighted_score = sum(factor_scores[key] * RISK_WEIGHTS[key] for key in factor_scores)
    score_out_of_100 = round(weighted_score * 100, 1)

    if score_out_of_100 < 35:
      level = "Low"
    elif score_out_of_100 < 65:
      level = "Moderate"
    else:
      level = "High"

    return {
        "score": score_out_of_100,
        "level": level,
        "factors": {key: safe_float(value) for key, value in factor_scores.items()},
    }


def build_recommendations(inputs: dict[str, float | str], risk: dict[str, object]) -> list[str]:
    recommendations: list[str] = []
    factors = risk["factors"]

    if factors["rainfall_deviation"] > 0.45:
        recommendations.append("Adjust irrigation planning because rainfall is far from the crop's ideal range.")
    if factors["temperature_stress"] > 0.45:
        recommendations.append("Prepare for temperature stress with mulch, shade planning, or heat-tolerant crop management.")
    if factors["soil_condition"] > 0.40:
        recommendations.append("Improve soil balance by monitoring pH and reviewing nutrient amendments before the next cycle.")
    if factors["pest_risk"] > 0.35:
        recommendations.append("Increase pest surveillance and preventive treatment because pest risk is elevated.")
    if not recommendations:
        recommendations.append("Current conditions are relatively stable. Continue routine monitoring and balanced nutrient management.")

    return recommendations


def create_figures(dataframe: pd.DataFrame, model_results: list[ModelResult]) -> dict[str, str]:
    model_metrics_df = pd.DataFrame(
        [
            {"Model": item.name, "Metric": "RMSE", "Value": item.rmse}
            for item in model_results
        ]
        + [
            {"Model": item.name, "Metric": "MAE", "Value": item.mae}
            for item in model_results
        ]
        + [
            {"Model": item.name, "Metric": "R2", "Value": item.r2}
            for item in model_results
        ]
    )

    comparison_chart = px.bar(
        model_metrics_df,
        x="Metric",
        y="Value",
        color="Model",
        barmode="group",
        title="Model Performance Comparison",
        color_discrete_sequence=["#436850", "#d97706"],
    )
    comparison_chart.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=20),
    )

    yield_by_crop = (
        dataframe.groupby("crop_type", as_index=False)["yield_ton_per_hectare"]
        .mean()
        .sort_values("yield_ton_per_hectare", ascending=False)
    )
    yield_chart = px.bar(
        yield_by_crop,
        x="crop_type",
        y="yield_ton_per_hectare",
        title="Average Yield by Crop",
        color="yield_ton_per_hectare",
        color_continuous_scale="YlGn",
    )
    yield_chart.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=20),
        coloraxis_showscale=False,
    )

    risk_bins = pd.cut(
        dataframe["risk_score"],
        bins=[-1, 35, 65, 100],
        labels=["Low", "Moderate", "High"],
    )
    risk_distribution = risk_bins.value_counts().rename_axis("Risk").reset_index(name="Count")
    risk_chart = px.pie(
        risk_distribution,
        names="Risk",
        values="Count",
        title="Training Data Risk Distribution",
        color="Risk",
        color_discrete_map={"Low": "#4d7c0f", "Moderate": "#ca8a04", "High": "#b91c1c"},
    )
    risk_chart.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=20),
    )

    trend_chart = px.scatter(
        dataframe.sample(min(len(dataframe), 250), random_state=42),
        x="rainfall_mm",
        y="yield_ton_per_hectare",
        color="crop_type",
        size="humidity_pct",
        hover_data=["region", "soil_type"],
        title="Rainfall vs Yield Trend",
        color_discrete_sequence=["#436850", "#65a30d", "#0f766e", "#f59e0b", "#b45309"],
    )
    trend_chart.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=20),
    )

    return {
        "comparison": comparison_chart.to_html(full_html=False, include_plotlyjs="cdn"),
        "yield_by_crop": yield_chart.to_html(full_html=False, include_plotlyjs=False),
        "risk_distribution": risk_chart.to_html(full_html=False, include_plotlyjs=False),
        "trend": trend_chart.to_html(full_html=False, include_plotlyjs=False),
    }


def build_dataset_records(dataframe: pd.DataFrame) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    preview_rows = dataframe.head(80).reset_index(drop=True)
    for index, row in preview_rows.iterrows():
        records.append(
            {
                "row_id": int(index),
                "label": (
                    f"{row['crop_type']} | {row['region']} | "
                    f"Rainfall {safe_float(row['rainfall_mm'])} | "
                    f"Yield {safe_float(row['yield_ton_per_hectare'])}"
                ),
            }
        )
    return records


@lru_cache(maxsize=1)
def load_project_state() -> dict[str, object]:
    init_auth_db()
    ensure_dataset(DATASET_PATH)
    active_dataset_path = get_active_dataset_path()
    dataframe = pd.read_csv(active_dataset_path)
    evaluation = evaluate_models(dataframe)
    best_model: ModelResult = evaluation["best_model"]

    dataframe = dataframe.copy()
    dataframe["risk_score"] = dataframe.apply(
        lambda row: calculate_risk(row.to_dict())["score"], axis=1
    )

    return {
        "dataset": dataframe,
        "results": evaluation["results"],
        "best_model": best_model,
        "figures": create_figures(dataframe, evaluation["results"]),
        "active_dataset_name": active_dataset_path.name,
        "active_dataset_source": "Custom uploaded dataset" if active_dataset_path == CUSTOM_DATASET_PATH else "Built-in demo dataset",
        "dataset_records": build_dataset_records(dataframe),
    }


def get_form_options(dataframe: pd.DataFrame) -> dict[str, list[str]]:
    return {
        "crop_types": sorted(dataframe["crop_type"].unique().tolist()),
        "regions": sorted(dataframe["region"].unique().tolist()),
        "soil_types": sorted(dataframe["soil_type"].unique().tolist()),
    }


@app.route("/")
def index():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login"))

    state = load_project_state()
    dataset = state["dataset"]
    best_model: ModelResult = state["best_model"]
    results: list[ModelResult] = state["results"]

    latest_rows = (
        dataset.sort_values(["crop_type", "yield_ton_per_hectare"], ascending=[True, False])
        .head(8)
        .to_dict(orient="records")
    )

    summary = {
        "dataset_rows": int(len(dataset)),
        "crop_count": int(dataset["crop_type"].nunique()),
        "avg_yield": safe_float(dataset["yield_ton_per_hectare"].mean()),
        "best_model": best_model.name,
        "best_r2": best_model.r2,
        "dataset_name": state["active_dataset_name"],
        "dataset_source": state["active_dataset_source"],
    }

    return render_template(
        "index.html",
        summary=summary,
        model_results=results,
        figures=state["figures"],
        options=get_form_options(dataset),
        latest_rows=latest_rows,
        current_user=current_user,
        dataset_records=state["dataset_records"],
    )


@app.route("/signup", methods=["GET", "POST"])
def signup():
    init_auth_db()
    if get_current_user():
        return redirect(url_for("index"))

    error = None

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not full_name or not email or not password:
            error = "Please fill in all required fields."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters long."
        else:
            connection = get_db_connection()
            try:
                existing_user = connection.execute(
                    "SELECT id FROM users WHERE email = ?",
                    (email,),
                ).fetchone()
                if existing_user:
                    error = "An account with this email already exists."
                else:
                    cursor = connection.execute(
                        "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                        (full_name, email, generate_password_hash(password)),
                    )
                    connection.commit()
                    session["user_id"] = cursor.lastrowid
                    return redirect(url_for("index"))
            finally:
                connection.close()

    return render_template("signup.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    init_auth_db()
    if get_current_user():
        return redirect(url_for("index"))

    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db_connection()
        try:
            user = connection.execute(
                "SELECT id, full_name, email, password_hash FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        finally:
            connection.close()

        if not user or not check_password_hash(user["password_hash"], password):
            error = "Invalid email or password."
        else:
            session["user_id"] = user["id"]
            return redirect(url_for("index"))

    return render_template("login.html", error=error)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    init_auth_db()
    if get_current_user():
        return redirect(url_for("index"))

    error = None
    success = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not new_password or not confirm_password:
            error = "Please fill in all required fields."
        elif new_password != confirm_password:
            error = "Passwords do not match."
        elif len(new_password) < 6:
            error = "Password must be at least 6 characters long."
        else:
            connection = get_db_connection()
            try:
                user = connection.execute(
                    "SELECT id FROM users WHERE email = ?",
                    (email,),
                ).fetchone()
                if not user:
                    error = "No account found with this email address."
                else:
                    connection.execute(
                        "UPDATE users SET password_hash = ? WHERE email = ?",
                        (generate_password_hash(new_password), email),
                    )
                    connection.commit()
                    success = "Password updated successfully. You can now log in with the new password."
            finally:
                connection.close()

    return render_template("forgot_password.html", error=error, success=success)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.post("/api/upload-dataset")
def upload_dataset():
    if not get_current_user():
        return jsonify({"error": "Unauthorized"}), 401

    uploaded_file = request.files.get("dataset_file")
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"error": "Please choose a CSV file to upload."}), 400

    if not uploaded_file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only CSV files are supported."}), 400

    try:
        file_text = uploaded_file.read().decode("utf-8")
        dataframe = pd.read_csv(StringIO(file_text))
    except Exception:
        return jsonify({"error": "The uploaded file could not be read as a valid CSV."}), 400

    is_valid, error_message = validate_dataset(dataframe)
    if not is_valid:
        return jsonify({"error": error_message}), 400

    CUSTOM_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(CUSTOM_DATASET_PATH, index=False)
    load_project_state.cache_clear()
    state = load_project_state()

    return jsonify(
        {
            "message": "Dataset uploaded successfully. Models retrained using the new backend dataset.",
            "dataset_name": state["active_dataset_name"],
            "dataset_source": state["active_dataset_source"],
            "dataset_rows": len(state["dataset"]),
            "best_model": state["best_model"].name,
        }
    )


@app.post("/api/reset-dataset")
def reset_dataset():
    if not get_current_user():
        return jsonify({"error": "Unauthorized"}), 401

    if CUSTOM_DATASET_PATH.exists():
        CUSTOM_DATASET_PATH.unlink()
    load_project_state.cache_clear()
    state = load_project_state()
    return jsonify(
        {
            "message": "Dataset reset to the built-in demo dataset.",
            "dataset_name": state["active_dataset_name"],
            "dataset_source": state["active_dataset_source"],
            "dataset_rows": len(state["dataset"]),
            "best_model": state["best_model"].name,
        }
    )


@app.post("/api/predict")
def predict():
    if not get_current_user():
        return jsonify({"error": "Unauthorized"}), 401

    state = load_project_state()
    best_model: ModelResult = state["best_model"]

    payload = request.get_json(force=True)
    input_frame = pd.DataFrame([payload], columns=FEATURE_COLUMNS)
    predicted_yield = safe_float(best_model.pipeline.predict(input_frame)[0])
    risk = calculate_risk(payload)
    recommendations = build_recommendations(payload, risk)

    dataset_context = None
    merged_yield = predicted_yield
    merged_note = "Live output is using the trained model only."
    selected_row_id = payload.get("dataset_row_id")
    if selected_row_id not in (None, "", "null"):
        try:
            row_index = int(selected_row_id)
            dataset = state["dataset"].reset_index(drop=True)
            if 0 <= row_index < len(dataset):
                dataset_row = dataset.iloc[row_index]
                actual_yield = safe_float(dataset_row["yield_ton_per_hectare"])
                merged_yield = safe_float(predicted_yield * 0.7 + actual_yield * 0.3)
                difference = safe_float(predicted_yield - actual_yield)
                dataset_context = {
                    "row_id": row_index,
                    "crop_type": str(dataset_row["crop_type"]),
                    "region": str(dataset_row["region"]),
                    "soil_type": str(dataset_row["soil_type"]),
                    "actual_yield": actual_yield,
                    "difference": difference,
                }
                merged_note = (
                    "Merged output combines 70% live model prediction with 30% selected "
                    "dataset yield to keep the result grounded in your CSV record."
                )
        except (ValueError, TypeError):
            dataset_context = None

    response = {
        "predicted_yield": predicted_yield,
        "merged_yield": merged_yield,
        "merged_note": merged_note,
        "yield_band": (
            "High Potential"
            if predicted_yield >= 6.5
            else "Stable Potential"
            if predicted_yield >= 4.5
            else "Needs Attention"
        ),
        "best_model": best_model.name,
        "risk": risk,
        "recommendations": recommendations,
        "dataset_context": dataset_context,
    }
    return jsonify(response)


@app.route("/api/dataset-preview")
def dataset_preview():
    if not get_current_user():
        return jsonify({"error": "Unauthorized"}), 401

    dataset = load_project_state()["dataset"]
    preview = dataset.head(20).to_dict(orient="records")
    return app.response_class(
        response=json.dumps(preview, indent=2),
        status=200,
        mimetype="application/json",
    )


@app.get("/api/dataset-row/<int:row_id>")
def dataset_row(row_id: int):
    if not get_current_user():
        return jsonify({"error": "Unauthorized"}), 401

    dataset = load_project_state()["dataset"].reset_index(drop=True)
    if row_id < 0 or row_id >= len(dataset):
        return jsonify({"error": "Dataset row not found."}), 404

    row = dataset.iloc[row_id].to_dict()
    row["row_id"] = row_id
    return jsonify(row)


if __name__ == "__main__":
    app.run(
        debug=False,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
    )
