'''import os
from typing import Optional, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import joblib
import pandas as pd
import numpy as np

import copilot'''
import os
import sys
from typing import Optional, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import joblib
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import copilot

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")


app = FastAPI(
    title="Residual Value & Risk Analytics API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


api_bundle = joblib.load(
    os.path.join(BASE_DIR, "residual_value_api_bundle.joblib")
)

model = api_bundle["model"]

depreciation_curve = np.poly1d(
    api_bundle["depreciation_coeffs"]
)

overall_avg_ratio = api_bundle["overall_avg_ratio"]

model_avg_ratio_map = api_bundle["model_avg_ratio_map"]


class PredictionInput(BaseModel):
    Cust_Age: float
    Cust_Cibil_Score: float
    Cust_Net_Salary: float
    Tenure: float
    Cust_Net_IRR: float

    Asset_Cost_At_Disbursal: float
    Loan_Amount: float
    LTV: float
    OS_Balance_At_Liquidation: float

    Asset_Age_Months_At_Seizure: float
    Months_Spent_In_Yard: float
    Traiffic_Challan_Amount: float

    Asset_Disc_Flag: str
    Asset_Alloy_Flag: str

    Cust_Gender: str
    Cust_Employment_Type: str
    Coborrower_Flag: str
    App_Score_Risk: str

    Cust_Region: str
    Pincode_Tier: str

    RC_Availability: str
    Registration_Flag: str

    Asset_Model: str
    Asset_Fuel_Type: str
    Asset_Accident_Flag: str

    Asset_Bodycondition: str
    Asset_Tyrecondition: str
    Asset_Generalcondition: str
    Asset_Enginecondition: str

    Seizure_Date_Year: int


def residual_risk_score(predicted_value, asset_cost):

    ratio = predicted_value / asset_cost

    score = 100 * (1 - ratio)

    return float(np.clip(score, 0, 100))


def get_risk_band(score):

    if score <= 25:
        return "LOW"

    elif score <= 50:
        return "MEDIUM"

    elif score <= 75:
        return "HIGH"

    else:
        return "CRITICAL"


def recommend_lending_terms(
    current_ltv,
    current_rate,
    current_tenure,
    risk_score
):

    risk_factor = risk_score / 100.0

    recommended_ltv = (
        current_ltv *
        (1 - 0.18 * risk_factor)
    )

    recommended_rate = (
        current_rate *
        (1 + 0.12 * risk_factor)
    )

    recommended_tenure = (
        current_tenure *
        (1 - 0.30 * risk_factor)
    )

    recommended_ltv = np.clip(
        recommended_ltv,
        0.40,
        0.95
    )

    recommended_tenure = np.clip(
        recommended_tenure,
        12,
        current_tenure
    )

    return (
        float(recommended_ltv),
        float(recommended_rate),
        float(recommended_tenure)
    )


def market_volatility_score(row):

    if row["Asset Fuel Type"] == "EV":
        base = 30
    else:
        base = 15

    recency_penalty = max(
        0,
        (row["Seizure Date Year"] - 2023) * 5
    )

    return min(
        100,
        base + recency_penalty
    )


def segment_risk_index(
    model_avg_ratio,
    overall_avg_ratio
):

    return round(
        100 *
        (
            1 -
            model_avg_ratio /
            overall_avg_ratio
        ),
        1
    )


def scenario_forecast(
    current_age_years,
    asset_cost,
    fuel_type,
    horizon_months,
    ev_adoption_stress=0.0,
    inflation_stress=0.0,
    fuel_price_stress=0.0
):

    future_age = (
        current_age_years +
        horizon_months / 12
    )

    base_ratio = depreciation_curve(
        future_age
    )

    if fuel_type == "Petrol":

        stressed_ratio = (
            base_ratio
            - ev_adoption_stress
            - fuel_price_stress
            + inflation_stress
        )

    else:

        stressed_ratio = (
            base_ratio
            + 0.5 * ev_adoption_stress
            + 0.5 * fuel_price_stress
            + inflation_stress
        )

    stressed_ratio = np.clip(
        stressed_ratio,
        0.02,
        1.3
    )

    return float(
        stressed_ratio *
        asset_cost
    )


def business_action(risk_band):

    if risk_band == "LOW":

        return {
            "overall_risk": "LOW",
            "recommended_action":
                "Proceed with standard lending terms."
        }

    elif risk_band == "MEDIUM":

        return {
            "overall_risk": "MEDIUM",
            "recommended_action":
                "Proceed with moderate adjustments and monitoring."
        }

    elif risk_band == "HIGH":

        return {
            "overall_risk": "HIGH",
            "recommended_action":
                "Reduce LTV, increase pricing and shorten tenure."
        }

    else:

        return {
            "overall_risk": "CRITICAL",
            "recommended_action":
                "High caution. Manual credit review recommended."
        }


@app.get("/api/health")
def home():

    return {
        "message":
            "Residual Value Analytics API is running",
        "model_loaded": True
    }


@app.post("/predict")
def predict(data: PredictionInput):

    cond_map = {
        "G": 3,
        "A": 2,
        "P": 1
    }


    body_score = cond_map.get(
        data.Asset_Bodycondition,
        2
    )

    tyre_score = cond_map.get(
        data.Asset_Tyrecondition,
        2
    )

    general_score = cond_map.get(
        data.Asset_Generalcondition,
        2
    )

    engine_score = cond_map.get(
        data.Asset_Enginecondition,
        2
    )


    asset_health_index = (
        body_score +
        tyre_score +
        general_score +
        engine_score
    ) / 4


    if data.Asset_Accident_Flag == "Yes":

        asset_health_index -= 0.5


    cibil_clean = (
        None
        if data.Cust_Cibil_Score == -1
        else data.Cust_Cibil_Score
    )


    cibil_missing_flag = (
        1
        if data.Cust_Cibil_Score == -1
        else 0
    )


    loan_to_cost = (
        data.Loan_Amount /
        data.Asset_Cost_At_Disbursal
    )


    os_to_cost = (
        data.OS_Balance_At_Liquidation /
        data.Asset_Cost_At_Disbursal
    )


    asset_age_years = (
        data.Asset_Age_Months_At_Seizure /
        12
    )


    yard_age_ratio = (
        data.Months_Spent_In_Yard /
        (
            data.Asset_Age_Months_At_Seizure +
            1
        )
    )


    input_data = {

        "Cust Age":
            data.Cust_Age,

        "CustCibilScoreClean":
            cibil_clean,

        "Cibil_Missing_Flag":
            cibil_missing_flag,

        "Cust Net Salary":
            data.Cust_Net_Salary,

        "Tenure":
            data.Tenure,

        "Cust Net IRR":
            data.Cust_Net_IRR,

        "Asset Cost At Disbursal":
            data.Asset_Cost_At_Disbursal,

        "Loan Amount":
            data.Loan_Amount,

        "LTV":
            data.LTV,

        "OS Balance At Liquidation":
            data.OS_Balance_At_Liquidation,

        "Asset Age Months At Seizure":
            data.Asset_Age_Months_At_Seizure,

        "Months Spent In Yard":
            data.Months_Spent_In_Yard,

        "Traiffic Challan Amount":
            data.Traiffic_Challan_Amount,

        "Asset_Health_Index":
            asset_health_index,

        "Loan_to_Cost":
            loan_to_cost,

        "OS_to_Cost":
            os_to_cost,

        "Yard_Age_Ratio":
            yard_age_ratio,

        "Asset Disc Flag":
            data.Asset_Disc_Flag,

        "Asset Alloy Flag":
            data.Asset_Alloy_Flag,

        "Cust Gender":
            data.Cust_Gender,

        "Cust Employment Type":
            data.Cust_Employment_Type,

        "Coborrower Flag":
            data.Coborrower_Flag,

        "App Score Risk":
            data.App_Score_Risk,

        "Cust Region":
            data.Cust_Region,

        "Pincode Tier":
            data.Pincode_Tier,

        "RC Availability":
            data.RC_Availability,

        "Registration Flag":
            data.Registration_Flag,

        "Asset Model":
            data.Asset_Model,

        "Asset Fuel Type":
            data.Asset_Fuel_Type,

        "Asset Accident Flag":
            data.Asset_Accident_Flag
    }


    prediction_df = pd.DataFrame(
        [input_data]
    )


    predicted_value = float(
        model.predict(prediction_df)[0]
    )


    risk_score = residual_risk_score(
        predicted_value,
        data.Asset_Cost_At_Disbursal
    )


    risk_band = get_risk_band(
        risk_score
    )


    market_volatility = market_volatility_score(
        {
            "Asset Fuel Type":
                data.Asset_Fuel_Type,

            "Seizure Date Year":
                data.Seizure_Date_Year
        }
    )


    model_avg_ratio = model_avg_ratio_map.get(
        data.Asset_Model,
        overall_avg_ratio
    )


    segment_risk = segment_risk_index(
        model_avg_ratio,
        overall_avg_ratio
    )


    recovery_efficiency = (
        100 *
        predicted_value /
        data.OS_Balance_At_Liquidation
    )


    profitability = (
        predicted_value -
        data.OS_Balance_At_Liquidation
    )


    recommended_ltv, recommended_rate, recommended_tenure = (
        recommend_lending_terms(
            data.LTV,
            data.Cust_Net_IRR,
            data.Tenure,
            risk_score
        )
    )


    forecast_12m = scenario_forecast(
        asset_age_years,
        data.Asset_Cost_At_Disbursal,
        data.Asset_Fuel_Type,
        12
    )


    forecast_24m = scenario_forecast(
        asset_age_years,
        data.Asset_Cost_At_Disbursal,
        data.Asset_Fuel_Type,
        24
    )


    forecast_36m = scenario_forecast(
        asset_age_years,
        data.Asset_Cost_At_Disbursal,
        data.Asset_Fuel_Type,
        36
    )


    decision = business_action(
        risk_band
    )


    return {

        "summary": {

            "predicted_sold_amount":
                round(predicted_value, 2),

            "residual_risk_score":
                round(risk_score, 2),

            "risk_band":
                risk_band
        },


        "asset_analytics": {

            "asset_health_index":
                round(
                    float(asset_health_index),
                    2
                ),

            "market_volatility_score":
                round(
                    float(market_volatility),
                    2
                ),

            "segment_risk_index":
                round(
                    float(segment_risk),
                    2
                ),

            "estimated_recovery_efficiency":
                round(
                    float(recovery_efficiency),
                    2
                ),

            "estimated_profitability":
                round(
                    float(profitability),
                    2
                )
        },


        "lending_recommendation": {

            "current_ltv":
                round(
                    data.LTV * 100,
                    2
                ),

            "recommended_ltv":
                round(
                    recommended_ltv * 100,
                    2
                ),

            "current_pricing":
                round(
                    data.Cust_Net_IRR,
                    2
                ),

            "recommended_pricing":
                round(
                    recommended_rate,
                    2
                ),

            "current_tenure":
                round(
                    data.Tenure,
                    2
                ),

            "recommended_tenure":
                round(
                    recommended_tenure,
                    2
                )
        },


        "forecast": {

            "current_predicted_value":
                round(
                    predicted_value,
                    2
                ),

            "forecast_12_month":
                round(
                    forecast_12m,
                    2
                ),

            "forecast_24_month":
                round(
                    forecast_24m,
                    2
                ),

            "forecast_36_month":
                round(
                    forecast_36m,
                    2
                )
        },


        "business_decision": {

            "overall_risk":
                decision["overall_risk"],

            "recommended_action":
                decision["recommended_action"]
        }
    }

class ScenarioSimRequest(BaseModel):
    Asset_Age_Months_At_Seizure: float
    Asset_Cost_At_Disbursal: float
    Asset_Fuel_Type: str

    # Custom stress dials, expressed as percentage points (0-100),
    # matching the sliders on the Scenario Simulator UI.
    ev_adoption_stress: Optional[float] = 6.0
    inflation_stress: Optional[float] = 5.0
    fuel_price_stress: Optional[float] = 7.0


@app.post("/scenario/simulate")
def scenario_simulate(data: ScenarioSimRequest):

    asset_age_years = (
        data.Asset_Age_Months_At_Seizure / 12
    )

    horizons = [12, 24, 36]

    # Preset scenarios mirror the illustrative stress levels used in the
    # modelling notebook's Macro Scenario Simulation Engine (Section 11):
    # a 6-point EV-adoption shock, a 5-point inflation shock, and a
    # 7-point fuel-price shock, plus a fully custom stress combination
    # driven by the sliders on the dashboard.
    preset_scenarios = {
        "Base Case": dict(
            ev_adoption_stress=0.0,
            inflation_stress=0.0,
            fuel_price_stress=0.0
        ),
        "High EV Adoption": dict(
            ev_adoption_stress=0.06,
            inflation_stress=0.0,
            fuel_price_stress=0.0
        ),
        "High Inflation": dict(
            ev_adoption_stress=0.0,
            inflation_stress=0.05,
            fuel_price_stress=0.0
        ),
        "Fuel Price Shock": dict(
            ev_adoption_stress=0.0,
            inflation_stress=0.0,
            fuel_price_stress=0.07
        ),
        "Custom Stress": dict(
            ev_adoption_stress=(data.ev_adoption_stress or 0.0) / 100.0,
            inflation_stress=(data.inflation_stress or 0.0) / 100.0,
            fuel_price_stress=(data.fuel_price_stress or 0.0) / 100.0
        ),
    }

    scenario_results = {}

    for name, stresses in preset_scenarios.items():

        values = []

        for h in horizons:

            v = scenario_forecast(
                asset_age_years,
                data.Asset_Cost_At_Disbursal,
                data.Asset_Fuel_Type,
                h,
                **stresses
            )

            values.append(round(v, 2))

        scenario_results[name] = values

    base_36m = scenario_results["Base Case"][-1]

    erosion_vs_base = {}

    for name, values in scenario_results.items():

        if base_36m:
            erosion_vs_base[name] = round(
                100 * (base_36m - values[-1]) / base_36m,
                2
            )
        else:
            erosion_vs_base[name] = 0.0

    return {
        "asset_fuel_type": data.Asset_Fuel_Type,
        "horizons": horizons,
        "scenarios": scenario_results,
        "erosion_vs_base_36m_pct": erosion_vs_base
    }


class CopilotRequest(BaseModel):
    question: str
    context: Optional[Dict[str, Any]] = None


@app.post("/copilot/ask")
def copilot_ask(payload: CopilotRequest):
    return copilot.answer_question(payload.question, payload.context)


# Serve the frontend (index.html, style.css, script.js) from the same app.
# Must be mounted LAST so it doesn't shadow the API routes above.
app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend"
)
