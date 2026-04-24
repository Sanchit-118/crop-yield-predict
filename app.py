from __future__ import annotations

import json
import os
import sqlite3
import sys
from io import StringIO
from datetime import datetime
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = BASE_DIR / ".packages"
if PACKAGE_DIR.exists() and os.getenv("USE_LOCAL_PACKAGES") == "1":
    sys.path.append(str(PACKAGE_DIR))

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask import Response
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None
from werkzeug.security import check_password_hash, generate_password_hash
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from generate_dataset import ensure_dataset


def load_local_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_local_env_file()


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "crop-yield-demo-secret-key")

DATASET_PATH = BASE_DIR / "data" / "crop_yield_dataset.csv"
CUSTOM_DATASET_PATH = BASE_DIR / "data" / "custom_crop_yield_dataset.csv"
DATABASE_URL = os.getenv("DATABASE_URL")
LOCAL_DB_PATH = BASE_DIR / "data" / "local_app.db"
DB_MODE = os.getenv("APP_DB_MODE", "auto").strip().lower()
IS_RENDER = bool(os.getenv("RENDER")) or bool(os.getenv("RENDER_EXTERNAL_URL"))
DEFAULT_DB_BACKEND = (
    "postgres"
    if DATABASE_URL and psycopg2 is not None and (DB_MODE == "postgres" or (DB_MODE == "auto" and IS_RENDER))
    else "sqlite"
)
ACTIVE_DB_BACKEND = DEFAULT_DB_BACKEND
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

COUNTRY_LOCATION_PROFILES = {
    "India": {
        "description": "Monsoon-driven crop planning with strong north-south seasonal variation.",
        "adjustments": {
            "rainfall_mm": 80,
            "temperature_c": 0.8,
            "humidity_pct": 4,
            "soil_ph": 0.0,
            "nitrogen_kg_ha": 4,
            "phosphorus_kg_ha": 2,
            "potassium_kg_ha": 3,
        },
        "directions": {
            "North": {"region": "North", "summary": "Cooler plains with strong wheat and rice belts."},
            "South": {"region": "South", "summary": "Warmer, humid belts with rice and sugarcane strength."},
            "East": {"region": "East", "summary": "Higher humidity with strong rainfall support for cereals."},
            "West": {"region": "West", "summary": "Hotter and relatively drier production zones."},
        },
    },
    "United States": {
        "description": "Large-scale mechanized farming with diverse climate bands across regions.",
        "adjustments": {
            "rainfall_mm": -40,
            "temperature_c": -0.5,
            "humidity_pct": -3,
            "soil_ph": 0.1,
            "nitrogen_kg_ha": 7,
            "phosphorus_kg_ha": 3,
            "potassium_kg_ha": 4,
        },
        "directions": {
            "North": {"region": "North", "summary": "Cooler seasons with moderate rainfall and stable grain belts."},
            "South": {"region": "South", "summary": "Longer warm seasons suited for cotton, maize, and cane."},
            "East": {"region": "East", "summary": "Humid production regions with dependable seasonal moisture."},
            "West": {"region": "West", "summary": "Drier zones where irrigation planning matters more."},
        },
    },
    "Brazil": {
        "description": "Tropical and subtropical crop conditions with strong rainfall influence.",
        "adjustments": {
            "rainfall_mm": 130,
            "temperature_c": 1.1,
            "humidity_pct": 6,
            "soil_ph": -0.1,
            "nitrogen_kg_ha": 5,
            "phosphorus_kg_ha": 2,
            "potassium_kg_ha": 5,
        },
        "directions": {
            "North": {"region": "North", "summary": "Very humid tropical profile with strong rainfall pressure."},
            "South": {"region": "South", "summary": "More balanced temperatures with broad crop suitability."},
            "East": {"region": "East", "summary": "Coastal humidity supports high vegetation growth."},
            "West": {"region": "West", "summary": "Expanding interior agriculture with mixed rainfall conditions."},
        },
    },
    "Australia": {
        "description": "Dryland management focus with stronger dependence on rainfall timing.",
        "adjustments": {
            "rainfall_mm": -140,
            "temperature_c": 1.6,
            "humidity_pct": -8,
            "soil_ph": 0.2,
            "nitrogen_kg_ha": -3,
            "phosphorus_kg_ha": 0,
            "potassium_kg_ha": 1,
        },
        "directions": {
            "North": {"region": "North", "summary": "Hotter growing conditions with stronger weather stress."},
            "South": {"region": "South", "summary": "Relatively cooler conditions with better cereal stability."},
            "East": {"region": "East", "summary": "More dependable coastal moisture than inland zones."},
            "West": {"region": "West", "summary": "Dryer profile where irrigation and nutrient balance matter."},
        },
    },
    "Egypt": {
        "description": "Irrigation-dependent agriculture with hot and arid field conditions.",
        "adjustments": {
            "rainfall_mm": -220,
            "temperature_c": 2.0,
            "humidity_pct": -10,
            "soil_ph": 0.3,
            "nitrogen_kg_ha": 2,
            "phosphorus_kg_ha": 1,
            "potassium_kg_ha": 2,
        },
        "directions": {
            "North": {"region": "North", "summary": "Slightly milder coastal influence with moderate humidity."},
            "South": {"region": "South", "summary": "Hotter interior profile with strong irrigation dependency."},
            "East": {"region": "East", "summary": "Arid production zones where water stress is more likely."},
            "West": {"region": "West", "summary": "Desert-facing pressure with high temperature exposure."},
        },
    },
}


@dataclass
class ModelResult:
    name: str
    pipeline: Pipeline
    rmse: float
    mae: float
    r2: float


class SQLiteCursorWrapper:
    def __init__(self, cursor: sqlite3.Cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._cursor.close()
        return False

    def execute(self, query, params=()):
        self._cursor.execute(query, params)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid


class SQLiteConnectionWrapper:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def cursor(self):
        return SQLiteCursorWrapper(self._connection.cursor())

    def execute(self, *args, **kwargs):
        return self._connection.execute(*args, **kwargs)

    def commit(self):
        return self._connection.commit()

    def close(self):
        return self._connection.close()


def get_db_connection():
    global ACTIVE_DB_BACKEND

    if ACTIVE_DB_BACKEND == "postgres":
        try:
            return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        except psycopg2.OperationalError:
            if DB_MODE == "postgres":
                raise
            ACTIVE_DB_BACKEND = "sqlite"

    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(LOCAL_DB_PATH)
    connection.row_factory = sqlite3.Row
    return SQLiteConnectionWrapper(connection)


def run_query(cursor, query: str, params: tuple = ()):
    if ACTIVE_DB_BACKEND == "sqlite":
        query = query.replace("%s", "?")
    cursor.execute(query, params)


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def ensure_sqlite_column(connection, table_name: str, column_name: str, definition: str) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in existing_columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_auth_db() -> None:
    connection = get_db_connection()
    try:
        if ACTIVE_DB_BACKEND == "postgres":
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        full_name TEXT NOT NULL,
                        email TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS predictions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        crop TEXT,
                        yield_value DOUBLE PRECISION,
                        risk TEXT,
                        crop_type TEXT,
                        region TEXT,
                        predicted_yield DOUBLE PRECISION,
                        risk_level TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT fk_predictions_user
                            FOREIGN KEY(user_id)
                            REFERENCES users(id)
                            ON DELETE CASCADE
                    )
                    """
                )
                cursor.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS crop TEXT")
                cursor.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS yield_value DOUBLE PRECISION")
                cursor.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS risk TEXT")
                cursor.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS crop_type TEXT")
                cursor.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS region TEXT")
                cursor.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS predicted_yield DOUBLE PRECISION")
                cursor.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS risk_level TEXT")
        else:
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    crop TEXT,
                    yield_value REAL,
                    risk TEXT,
                    crop_type TEXT,
                    region TEXT,
                    predicted_yield REAL,
                    risk_level TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            ensure_sqlite_column(connection, "predictions", "crop", "TEXT")
            ensure_sqlite_column(connection, "predictions", "yield_value", "REAL")
            ensure_sqlite_column(connection, "predictions", "risk", "TEXT")
            ensure_sqlite_column(connection, "predictions", "crop_type", "TEXT")
            ensure_sqlite_column(connection, "predictions", "region", "TEXT")
            ensure_sqlite_column(connection, "predictions", "predicted_yield", "REAL")
            ensure_sqlite_column(connection, "predictions", "risk_level", "TEXT")
        connection.commit()
    finally:
        connection.close()


def get_current_user() -> dict[str, str] | None:
    user_id = session.get("user_id")
    if not user_id:
        return None

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            run_query(
                cursor,
                "SELECT id, full_name, email FROM users WHERE id = %s",
                (user_id,),
            )
            row = cursor.fetchone()
    finally:
        connection.close()

    return row_to_dict(row)


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


def build_action_cards(inputs: dict[str, float | str], risk: dict[str, object]) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    factors = risk["factors"]

    if factors["rainfall_deviation"] > 0.35:
        cards.append(
            {
                "title": "Irrigation Planning",
                "icon": "Water",
                "tone": "warning",
                "detail": "Rainfall is away from the crop benchmark. Adjust irrigation timing and monitor field moisture regularly.",
            }
        )
    if float(inputs["nitrogen_kg_ha"]) < 80 or float(inputs["phosphorus_kg_ha"]) < 40:
        cards.append(
            {
                "title": "Fertilizer Balance",
                "icon": "NPK",
                "tone": "accent",
                "detail": "Nutrient levels are on the lower side. Consider a balanced NPK schedule before the next growth stage.",
            }
        )
    if factors["pest_risk"] > 0.30:
        cards.append(
            {
                "title": "Pest Control",
                "icon": "Shield",
                "tone": "danger",
                "detail": "Pest pressure is elevated. Increase scouting frequency and prepare preventive treatment if symptoms rise.",
            }
        )
    if factors["soil_condition"] > 0.30:
        cards.append(
            {
                "title": "Soil Care",
                "icon": "Soil",
                "tone": "muted",
                "detail": "Soil pH is drifting from the ideal range. Review amendments and maintain soil health before the next cycle.",
            }
        )

    if not cards:
        cards.append(
            {
                "title": "Stable Conditions",
                "icon": "Leaf",
                "tone": "success",
                "detail": "Current field conditions are close to the crop profile. Continue routine irrigation, nutrient balance, and scouting.",
            }
        )

    return cards


def build_insights(inputs: dict[str, float | str], risk: dict[str, object], dataframe: pd.DataFrame) -> list[str]:
    crop = str(inputs["crop_type"])
    crop_rows = dataframe[dataframe["crop_type"] == crop]
    if crop_rows.empty:
        crop_rows = dataframe

    crop_avg_rainfall = float(crop_rows["rainfall_mm"].mean())
    rainfall_delta_pct = ((float(inputs["rainfall_mm"]) - crop_avg_rainfall) / max(crop_avg_rainfall, 1)) * 100
    dominant_factor = max(risk["factors"], key=risk["factors"].get)
    dominant_factor_label = dominant_factor.replace("_", " ").title()

    insights = [
        f"Your rainfall is {abs(rainfall_delta_pct):.1f}% {'above' if rainfall_delta_pct >= 0 else 'below'} the average for {crop}.",
        f"The strongest yield pressure right now is {dominant_factor_label.lower()}.",
    ]

    if float(inputs["temperature_c"]) > float(crop_rows["temperature_c"].mean()) + 2:
        insights.append("Temperature is running warmer than the crop average, so heat stress management can improve reliability.")
    elif float(inputs["pest_risk"]) >= 6:
        insights.append("Pest pressure is the fastest lever to improve output if addressed early.")
    else:
        insights.append("Your current profile is relatively close to training data conditions, which improves trust in the forecast.")

    return insights


def calculate_confidence(dataframe: pd.DataFrame, inputs: dict[str, float | str], best_model: ModelResult) -> dict[str, object]:
    crop_rows = dataframe[dataframe["crop_type"] == str(inputs["crop_type"])]
    if crop_rows.empty:
        crop_rows = dataframe

    distance_parts: list[float] = []
    for column in NUMERICAL_COLUMNS:
        series = crop_rows[column].astype(float)
        std = float(series.std()) if float(series.std()) > 0 else 1.0
        z_score = abs(float(inputs[column]) - float(series.mean())) / std
        distance_parts.append(z_score)

    avg_distance = float(np.mean(distance_parts)) if distance_parts else 0.0
    base_confidence = max(0.25, min(0.97, float(best_model.r2) * 0.75 + (1 / (1 + avg_distance)) * 0.25))
    score = round(base_confidence * 100, 1)

    if score >= 78:
        label = "High confidence"
    elif score >= 58:
        label = "Moderate confidence"
    else:
        label = "Low confidence"

    return {
        "score": score,
        "label": label,
        "explanation": "Confidence is based on model accuracy and how close the input is to known training patterns.",
    }


def validate_prediction_inputs(payload: dict[str, object]) -> list[str]:
    issues: list[str] = []
    for field in FEATURE_COLUMNS:
        if field not in payload or payload[field] in ("", None):
            issues.append(f"{field} is required.")

    if issues:
        return issues

    if float(payload["rainfall_mm"]) < 0:
        issues.append("Rainfall cannot be negative.")
    if not (0 <= float(payload["humidity_pct"]) <= 100):
        issues.append("Humidity should be between 0 and 100.")
    if not (0 <= float(payload["pest_risk"]) <= 10):
        issues.append("Pest risk should be between 0 and 10.")
    if not (3 <= float(payload["soil_ph"]) <= 10):
        issues.append("Soil pH should be between 3 and 10.")

    return issues


def build_report_html(report_data: dict[str, object]) -> str:
    action_cards = "".join(
        f"<li><strong>{card['title']}:</strong> {card['detail']}</li>"
        for card in report_data["action_cards"]
    )
    insights = "".join(f"<li>{item}</li>" for item in report_data["insights"])
    recommendations = "".join(f"<li>{item}</li>" for item in report_data["recommendations"])

    return f"""
    <html>
    <head>
      <title>Crop Yield Prediction Report</title>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2a1e; }}
        h1, h2 {{ color: #436850; }}
        .hero {{ padding: 18px; background: #f6f1e6; border-radius: 14px; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
        .card {{ border: 1px solid #d5dccd; border-radius: 14px; padding: 16px; margin-bottom: 14px; }}
      </style>
    </head>
    <body>
      <div class="hero">
        <h1>Crop Yield Prediction Report</h1>
        <p>Generated on {datetime.now().strftime('%d %B %Y, %I:%M %p')}</p>
        <p><strong>Crop:</strong> {report_data['crop_type']} | <strong>Region:</strong> {report_data['region']}</p>
      </div>
      <div class="grid">
        <div class="card">
          <h2>Prediction Summary</h2>
          <p><strong>Predicted Yield:</strong> {report_data['predicted_yield']} ton/hectare</p>
          <p><strong>Risk Level:</strong> {report_data['risk_level']}</p>
          <p><strong>Confidence:</strong> {report_data['confidence_label']} ({report_data['confidence_score']}%)</p>
          <p><strong>Recommended Crop:</strong> {report_data['recommended_crop']}</p>
        </div>
        <div class="card">
          <h2>Insights</h2>
          <ul>{insights}</ul>
        </div>
      </div>
      <div class="card">
        <h2>Action Cards</h2>
        <ul>{action_cards}</ul>
      </div>
      <div class="card">
        <h2>Recommendations</h2>
        <ul>{recommendations}</ul>
      </div>
    </body>
    </html>
    """


def recommend_crop_for_inputs(inputs: dict[str, float | str]) -> str:
    scores: dict[str, float] = {}

    for crop, ideal in IDEAL_GROWTH.items():
        score = 0.0
        score += abs(float(inputs["rainfall_mm"]) - ideal["rainfall_mm"]) / 1000
        score += abs(float(inputs["temperature_c"]) - ideal["temperature_c"]) / 20
        score += abs(float(inputs["soil_ph"]) - ideal["soil_ph"]) / 3
        scores[crop] = score

    return min(scores, key=scores.get)


def build_analytics_figures(
    dataframe: pd.DataFrame,
    model_results: list[ModelResult],
    current_input: dict[str, float | str] | None = None,
    predicted_yield: float | None = None,
    risk: dict[str, object] | None = None,
) -> dict[str, object]:
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
    highlighted_crop = str(current_input["crop_type"]) if current_input and current_input.get("crop_type") else None
    yield_by_crop["bar_color"] = yield_by_crop["crop_type"].apply(
        lambda crop: "#d97706" if crop == highlighted_crop else "#436850"
    )
    yield_chart = px.bar(
        yield_by_crop,
        x="crop_type",
        y="yield_ton_per_hectare",
        title=f"Average Yield by Crop{' with Current Crop Highlight' if highlighted_crop else ''}",
        color="bar_color",
        color_discrete_map="identity",
    )
    if highlighted_crop:
        crop_average = yield_by_crop.loc[
            yield_by_crop["crop_type"] == highlighted_crop, "yield_ton_per_hectare"
        ]
        if not crop_average.empty:
            yield_chart.add_annotation(
                x=highlighted_crop,
                y=float(crop_average.iloc[0]),
                text=f"Current crop: {highlighted_crop}",
                showarrow=True,
                arrowhead=2,
                ay=-45,
                bgcolor="rgba(255,248,234,0.9)",
            )
    if highlighted_crop and predicted_yield is not None:
        yield_chart.add_trace(
            go.Scatter(
                x=[highlighted_crop],
                y=[predicted_yield],
                mode="markers+text",
                marker=dict(size=16, color="#b91c1c", symbol="diamond"),
                text=["Live input yield"],
                textposition="top center",
                name="Live input",
            )
        )
    yield_chart.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=20),
        showlegend=False,
    )

    risk_bins = pd.cut(
        dataframe["risk_score"],
        bins=[-1, 35, 65, 100],
        labels=["Low", "Moderate", "High"],
    )
    risk_distribution = risk_bins.value_counts().rename_axis("Risk").reset_index(name="Count")
    risk_distribution["Risk"] = pd.Categorical(
        risk_distribution["Risk"],
        categories=["Low", "Moderate", "High"],
        ordered=True,
    )
    risk_distribution = risk_distribution.sort_values("Risk")
    risk_chart = px.bar(
        risk_distribution,
        x="Risk",
        y="Count",
        title="Training Data Risk Distribution",
        color="Risk",
        color_discrete_map={"Low": "#4d7c0f", "Moderate": "#ca8a04", "High": "#b91c1c"},
    )
    if risk:
        live_risk_level = risk["level"]
        live_count = risk_distribution.loc[risk_distribution["Risk"] == live_risk_level, "Count"]
        if not live_count.empty:
            risk_chart.add_trace(
                go.Scatter(
                    x=[live_risk_level],
                    y=[float(live_count.iloc[0])],
                    mode="markers+text",
                    marker=dict(size=16, color="#111827", symbol="diamond"),
                    text=[f"Current risk ({risk['score']})"],
                    textposition="top center",
                    name="Current input",
                )
            )
    risk_chart.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=20),
        showlegend=False,
    )

    trend_source = dataframe
    if current_input and current_input.get("crop_type"):
        trend_source = trend_source[trend_source["crop_type"] == str(current_input["crop_type"])]
    if current_input and current_input.get("region"):
        region_filtered = trend_source[trend_source["region"] == str(current_input["region"])]
        if not region_filtered.empty:
            trend_source = region_filtered
    trend_source = trend_source.sample(min(len(trend_source), 160), random_state=42)

    trend_chart = px.scatter(
        trend_source,
        x="rainfall_mm",
        y="yield_ton_per_hectare",
        color="crop_type",
        size="humidity_pct",
        hover_data=["region", "soil_type"],
        title=(
            f"Rainfall vs Yield Trend for {current_input['crop_type']} in {current_input['region']}"
            if current_input and current_input.get("crop_type") and current_input.get("region")
            else "Rainfall vs Yield Trend"
        ),
        color_discrete_sequence=["#436850", "#65a30d", "#0f766e", "#f59e0b", "#b45309"],
    )
    trend_chart.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    if current_input and predicted_yield is not None:
        trend_chart.add_trace(
            go.Scatter(
                x=[float(current_input["rainfall_mm"])],
                y=[predicted_yield],
                mode="markers+text",
                marker=dict(size=18, color="#d97706", symbol="star"),
                text=["Your current input"],
                textposition="top center",
                name="Current input",
            )
        )
        trend_chart.add_vline(
            x=float(current_input["rainfall_mm"]),
            line_dash="dash",
            line_color="#d97706",
            opacity=0.6,
        )

    return {
        "comparison": comparison_chart,
        "yield_by_crop": yield_chart,
        "risk_distribution": risk_chart,
        "trend": trend_chart,
    }


def create_figures(
    dataframe: pd.DataFrame,
    model_results: list[ModelResult],
    current_input: dict[str, float | str] | None = None,
    predicted_yield: float | None = None,
    risk: dict[str, object] | None = None,
) -> dict[str, str]:
    figures = build_analytics_figures(
        dataframe,
        model_results,
        current_input=current_input,
        predicted_yield=predicted_yield,
        risk=risk,
    )

    return {
        "comparison": figures["comparison"].to_html(full_html=False, include_plotlyjs="cdn"),
        "yield_by_crop": figures["yield_by_crop"].to_html(full_html=False, include_plotlyjs=False),
        "risk_distribution": figures["risk_distribution"].to_html(full_html=False, include_plotlyjs=False),
        "trend": figures["trend"].to_html(full_html=False, include_plotlyjs=False),
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


def build_simple_profiles(dataframe: pd.DataFrame) -> dict[str, dict[str, dict[str, float | str]]]:
    grouped = (
        dataframe.groupby(["crop_type", "region"], as_index=False)
        .agg(
            {
                "soil_type": lambda values: values.mode().iloc[0] if not values.mode().empty else values.iloc[0],
                "rainfall_mm": "mean",
                "temperature_c": "mean",
                "humidity_pct": "mean",
                "soil_ph": "mean",
                "nitrogen_kg_ha": "mean",
                "phosphorus_kg_ha": "mean",
                "potassium_kg_ha": "mean",
                "pest_risk": "mean",
            }
        )
    )

    profiles: dict[str, dict[str, dict[str, float | str]]] = {}
    for _, row in grouped.iterrows():
        crop = str(row["crop_type"])
        region = str(row["region"])
        profiles.setdefault(crop, {})[region] = {
            "crop_type": crop,
            "region": region,
            "soil_type": str(row["soil_type"]),
            "rainfall_mm": safe_float(row["rainfall_mm"]),
            "temperature_c": safe_float(row["temperature_c"]),
            "humidity_pct": safe_float(row["humidity_pct"]),
            "soil_ph": safe_float(row["soil_ph"]),
            "nitrogen_kg_ha": safe_float(row["nitrogen_kg_ha"]),
            "phosphorus_kg_ha": safe_float(row["phosphorus_kg_ha"]),
            "potassium_kg_ha": safe_float(row["potassium_kg_ha"]),
            "pest_risk": safe_float(row["pest_risk"]),
        }
    return profiles


def build_location_profiles(dataframe: pd.DataFrame) -> dict[str, object]:
    available_regions = set(dataframe["region"].astype(str).unique().tolist())
    fallback_region = "Central" if "Central" in available_regions else sorted(available_regions)[0]
    location_profiles: dict[str, object] = {}

    for country, details in COUNTRY_LOCATION_PROFILES.items():
        directions: dict[str, object] = {}
        for direction, direction_info in details["directions"].items():
            mapped_region = direction_info["region"]
            if mapped_region not in available_regions:
                mapped_region = fallback_region

            directions[direction] = {
                "region": mapped_region,
                "summary": direction_info["summary"],
            }

        location_profiles[country] = {
            "description": details["description"],
            "adjustments": details["adjustments"],
            "directions": directions,
        }

    return location_profiles


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
        "simple_profiles": build_simple_profiles(dataframe),
        "location_profiles": build_location_profiles(dataframe),
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
        simple_profiles=state["simple_profiles"],
        location_profiles=state["location_profiles"],
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
                with connection.cursor() as cursor:
                    run_query(
                        cursor,
                        "SELECT id FROM users WHERE email = %s",
                        (email,),
                    )
                    existing_user = cursor.fetchone()
                if existing_user:
                    error = "An account with this email already exists."
                else:
                    with connection.cursor() as cursor:
                        if ACTIVE_DB_BACKEND == "postgres":
                            run_query(
                                cursor,
                                "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
                                (full_name, email, generate_password_hash(password)),
                            )
                            created_user = row_to_dict(cursor.fetchone())
                        else:
                            run_query(
                                cursor,
                                "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
                                (full_name, email, generate_password_hash(password)),
                            )
                            created_user = {"id": cursor.lastrowid}
                    connection.commit()
                    session["user_id"] = created_user["id"]
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
            with connection.cursor() as cursor:
                run_query(
                    cursor,
                    "SELECT id, full_name, email, password_hash FROM users WHERE email = %s",
                    (email,),
                )
                user = row_to_dict(cursor.fetchone())
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
                with connection.cursor() as cursor:
                    run_query(
                        cursor,
                        "SELECT id FROM users WHERE email = %s",
                        (email,),
                    )
                    user = cursor.fetchone()
                if not user:
                    error = "No account found with this email address."
                else:
                    with connection.cursor() as cursor:
                        run_query(
                            cursor,
                            "UPDATE users SET password_hash = %s WHERE email = %s",
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
    validation_errors = validate_prediction_inputs(payload)
    if validation_errors:
        return jsonify({"error": "Please correct the highlighted inputs.", "validation_errors": validation_errors}), 400

    input_frame = pd.DataFrame([payload], columns=FEATURE_COLUMNS)
    predicted_yield = safe_float(best_model.pipeline.predict(input_frame)[0])
    risk = calculate_risk(payload)
    recommendations = build_recommendations(payload, risk)
    confidence = calculate_confidence(state["dataset"], payload, best_model)
    action_cards = build_action_cards(payload, risk)
    insights = build_insights(payload, risk, state["dataset"])
    recommended_crop = recommend_crop_for_inputs(payload)

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
        "confidence": confidence,
        "insights": insights,
        "action_cards": action_cards,
        "recommendations": recommendations,
        "recommended_crop": recommended_crop,
        "dataset_context": dataset_context,
        "input_summary": {
            "crop_type": payload["crop_type"],
            "region": payload["region"],
            "soil_type": payload["soil_type"],
        },
    }

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            run_query(
                cursor,
                """
                INSERT INTO predictions (
                    user_id,
                    crop,
                    yield_value,
                    risk,
                    crop_type,
                    region,
                    predicted_yield,
                    risk_level
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session["user_id"],
                    payload["crop_type"],
                    predicted_yield,
                    risk["level"],
                    payload["crop_type"],
                    payload.get("region"),
                    predicted_yield,
                    risk["level"],
                ),
            )
        connection.commit()
    finally:
        connection.close()

    return jsonify(response)


@app.post("/api/compare-scenarios")
def compare_scenarios():
    if not get_current_user():
        return jsonify({"error": "Unauthorized"}), 401

    state = load_project_state()
    best_model: ModelResult = state["best_model"]
    payload = request.get_json(force=True) or {}
    base_input = payload.get("current_input") or {}
    improved_input = payload.get("improved_input") or {}

    if not base_input or not improved_input:
        return jsonify({"error": "Two scenario payloads are required."}), 400

    def evaluate_scenario(inputs: dict[str, object]) -> dict[str, object]:
        validation_errors = validate_prediction_inputs(inputs)
        if validation_errors:
            return {"error": validation_errors}

        input_frame = pd.DataFrame([inputs], columns=FEATURE_COLUMNS)
        predicted = safe_float(best_model.pipeline.predict(input_frame)[0])
        risk = calculate_risk(inputs)
        confidence = calculate_confidence(state["dataset"], inputs, best_model)
        return {
            "predicted_yield": predicted,
            "risk": risk,
            "confidence": confidence,
            "crop_type": inputs["crop_type"],
            "region": inputs["region"],
        }

    current_result = evaluate_scenario(base_input)
    improved_result = evaluate_scenario(improved_input)
    if current_result.get("error") or improved_result.get("error"):
        return jsonify({"error": "Scenario inputs are invalid.", "details": [current_result, improved_result]}), 400

    improvement = safe_float(improved_result["predicted_yield"] - current_result["predicted_yield"])
    risk_change = safe_float(current_result["risk"]["score"] - improved_result["risk"]["score"])

    return jsonify(
        {
            "current": current_result,
            "improved": improved_result,
            "yield_gain": improvement,
            "risk_reduction": risk_change,
        }
    )


@app.post("/api/export-report")
def export_report():
    if not get_current_user():
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(force=True) or {}
    report_data = payload.get("report_data") or {}
    if not report_data:
        return jsonify({"error": "No report data was provided."}), 400

    html = build_report_html(report_data)
    return Response(
        html,
        mimetype="text/html",
        headers={"Content-Disposition": "attachment; filename=crop_yield_report.html"},
    )


@app.post("/api/context-figures")
def context_figures():
    if not get_current_user():
        return jsonify({"error": "Unauthorized"}), 401

    state = load_project_state()
    payload = request.get_json(force=True) or {}
    current_input = payload.get("current_input") or {}
    predicted_yield = payload.get("predicted_yield")
    risk = payload.get("risk")

    figures = build_analytics_figures(
        state["dataset"],
        state["results"],
        current_input=current_input if current_input else None,
        predicted_yield=float(predicted_yield) if predicted_yield is not None else None,
        risk=risk if isinstance(risk, dict) else None,
    )

    return jsonify(
        {
            "yield_by_crop": figures["yield_by_crop"].to_plotly_json(),
            "risk_distribution": figures["risk_distribution"].to_plotly_json(),
            "trend": figures["trend"].to_plotly_json(),
        }
    )


@app.post("/api/recommend-crop")
def recommend_crop():
    if not get_current_user():
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(force=True)
    results: list[tuple[str, float]] = []
    for crop, ideal in IDEAL_GROWTH.items():
        score = 0.0
        score += abs(float(payload["rainfall_mm"]) - ideal["rainfall_mm"]) / 1000
        score += abs(float(payload["temperature_c"]) - ideal["temperature_c"]) / 20
        score += abs(float(payload["soil_ph"]) - ideal["soil_ph"]) / 3
        results.append((crop, round(score, 3)))

    best_crop = min(results, key=lambda item: item[1])
    return jsonify(
        {
            "recommended_crop": best_crop[0],
            "match_score": best_crop[1],
            "all_predictions": results,
        }
    )


@app.get("/api/history")
def get_history():
    if not get_current_user():
        return jsonify({"error": "Unauthorized"}), 401

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            run_query(
                cursor,
                """
                SELECT
                    COALESCE(crop_type, crop) AS crop_name,
                    COALESCE(region, 'Not provided') AS region_name,
                    COALESCE(predicted_yield, yield_value) AS predicted_value,
                    COALESCE(risk_level, risk) AS risk_name,
                    created_at
                FROM predictions
                WHERE user_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 10
                """,
                (session["user_id"],),
            )
            rows = cursor.fetchall()
    finally:
        connection.close()

    history = [
        {
            "crop": row["crop_name"] or "Unknown crop",
            "region": row["region_name"] or "Not provided",
            "yield": row["predicted_value"],
            "risk": row["risk_name"] or "Unknown",
            "time": str(row["created_at"]),
        }
        for row in rows
    ]
    return jsonify(history)


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
