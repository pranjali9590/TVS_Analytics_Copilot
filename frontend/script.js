let forecastChart = null;
let scenarioChart = null;
let riskGaugeChart = null;
let portfolioDistributionChart = null;


async function predictValue() {

    const button = document.querySelector(".predict-button");

    const originalButtonHTML = button.innerHTML;

    button.innerHTML = `
        <span>Running Model...</span>
        <span class="button-arrow">⟳</span>
    `;

    button.disabled = true;


    const data = {

        Cust_Age:
            Number(document.getElementById("Cust_Age").value),

        Cust_Cibil_Score:
            Number(document.getElementById("Cust_Cibil_Score").value),

        Cust_Net_Salary:
            Number(document.getElementById("Cust_Net_Salary").value),

        Tenure:
            Number(document.getElementById("Tenure").value),

        Cust_Net_IRR:
            Number(document.getElementById("Cust_Net_IRR").value),

        Asset_Cost_At_Disbursal:
            Number(document.getElementById("Asset_Cost_At_Disbursal").value),

        Loan_Amount:
            Number(document.getElementById("Loan_Amount").value),

        LTV:
            Number(document.getElementById("LTV").value),

        OS_Balance_At_Liquidation:
            Number(
                document.getElementById(
                    "OS_Balance_At_Liquidation"
                ).value
            ),

        Asset_Age_Months_At_Seizure:
            Number(
                document.getElementById(
                    "Asset_Age_Months_At_Seizure"
                ).value
            ),

        Months_Spent_In_Yard:
            Number(
                document.getElementById(
                    "Months_Spent_In_Yard"
                ).value
            ),

        Traiffic_Challan_Amount:
            Number(
                document.getElementById(
                    "Traiffic_Challan_Amount"
                ).value
            ),

        Asset_Disc_Flag:
            document.getElementById(
                "Asset_Disc_Flag"
            ).value,

        Asset_Alloy_Flag:
            document.getElementById(
                "Asset_Alloy_Flag"
            ).value,

        Cust_Gender:
            document.getElementById(
                "Cust_Gender"
            ).value,

        Cust_Employment_Type:
            document.getElementById(
                "Cust_Employment_Type"
            ).value,

        Coborrower_Flag:
            document.getElementById(
                "Coborrower_Flag"
            ).value,

        App_Score_Risk:
            document.getElementById(
                "App_Score_Risk"
            ).value,

        Cust_Region:
            document.getElementById(
                "Cust_Region"
            ).value,

        Pincode_Tier:
            document.getElementById(
                "Pincode_Tier"
            ).value,

        RC_Availability:
            document.getElementById(
                "RC_Availability"
            ).value,

        Registration_Flag:
            document.getElementById(
                "Registration_Flag"
            ).value,

        Asset_Model:
            document.getElementById(
                "Asset_Model"
            ).value,

        Asset_Fuel_Type:
            document.getElementById(
                "Asset_Fuel_Type"
            ).value,

        Asset_Accident_Flag:
            document.getElementById(
                "Asset_Accident_Flag"
            ).value,

        Asset_Bodycondition:
            document.getElementById(
                "Asset_Bodycondition"
            ).value,

        Asset_Tyrecondition:
            document.getElementById(
                "Asset_Tyrecondition"
            ).value,

        Asset_Generalcondition:
            document.getElementById(
                "Asset_Generalcondition"
            ).value,

        Asset_Enginecondition:
            document.getElementById(
                "Asset_Enginecondition"
            ).value,

        Seizure_Date_Year:
            Number(
                document.getElementById(
                    "Seizure_Date_Year"
                ).value
            )
    };


    try {

        const response = await fetch(
            "/predict",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(data)
            }
        );


        if (!response.ok) {

            let errorData = {};

            try {
                errorData = await response.json();
            }

            catch (e) {
                errorData = {
                    detail: "Unknown API error"
                };
            }

            console.error(
                "API Error:",
                errorData
            );

            alert(
                "Prediction failed.\n\n" +
                JSON.stringify(
                    errorData,
                    null,
                    2
                )
            );

            return;
        }


        const result =
            await response.json();


        console.log(
            "API Response:",
            result
        );


        /* Hand this prediction to the AI Lending Copilot so its
           answers stay grounded in what's actually on screen. */
        window.__lastPredictionContext = result;
        if (typeof onNewPredictionForCopilot === "function") {
            onNewPredictionForCopilot(result);
        }


        /* ================= SUMMARY ================= */

        animateNumberText(
            document.getElementById("predicted_sold_amount"),
            Number(result.summary.predicted_sold_amount) || 0,
            900,
            formatCurrency
        );


        const riskScore =
            Number(
                result.summary.residual_risk_score
            );


        animateNumberText(
            document.getElementById("residual_risk_score"),
            riskScore,
            900,
            (v) => v.toFixed(2)
        );


        document.getElementById(
            "risk_band"
        ).innerText =
            result.summary.risk_band;


        /* ================= RISK METER ================= */

        document.getElementById(
            "risk_meter_fill"
        ).style.width =
            Math.min(
                Math.max(
                    riskScore,
                    0
                ),
                100
            ) + "%";


        const bandCard =
            document.getElementById(
                "risk_band_card"
            );


        bandCard.style.border =
            "2px solid " +
            getRiskColor(
                result.summary.risk_band
            );


        /* ================= RISK GAUGE (pictorial) ================= */

        updateRiskGauge(
            riskScore,
            getRiskColor(result.summary.risk_band)
        );


        document.getElementById(
            "risk_band"
        ).style.color =
            getRiskColor(
                result.summary.risk_band
            );


        /* ================= ASSET ANALYTICS ================= */

        document.getElementById(
            "asset_health_index"
        ).innerText =
            result.asset_analytics
                .asset_health_index;


        document.getElementById(
            "market_volatility_score"
        ).innerText =
            result.asset_analytics
                .market_volatility_score;


        document.getElementById(
            "segment_risk_index"
        ).innerText =
            result.asset_analytics
                .segment_risk_index;


        document.getElementById(
            "recovery_efficiency"
        ).innerText =
            Number(
                result.asset_analytics
                    .estimated_recovery_efficiency
            ).toFixed(2)
            + "%";


        document.getElementById(
            "profitability"
        ).innerText =
            formatCurrency(
                result.asset_analytics
                    .estimated_profitability
            );


        /* ================= LENDING ================= */

        const lending =
            result.lending_recommendation;


        document.getElementById(
            "current_ltv"
        ).innerText =
            Number(
                lending.current_ltv
            ).toFixed(2) + "%";


        document.getElementById(
            "recommended_ltv"
        ).innerText =
            Number(
                lending.recommended_ltv
            ).toFixed(2) + "%";


        document.getElementById(
            "current_pricing"
        ).innerText =
            Number(
                lending.current_pricing
            ).toFixed(2) + "%";


        document.getElementById(
            "recommended_pricing"
        ).innerText =
            Number(
                lending.recommended_pricing
            ).toFixed(2) + "%";


        document.getElementById(
            "current_tenure"
        ).innerText =
            Number(
                lending.current_tenure
            ).toFixed(2)
            + " months";


        document.getElementById(
            "recommended_tenure"
        ).innerText =
            Number(
                lending.recommended_tenure
            ).toFixed(2)
            + " months";


        /* ================= CHANGES ================= */

        document.getElementById(
            "ltv_change"
        ).innerText =
            formatDifference(
                lending.current_ltv,
                lending.recommended_ltv,
                "pp"
            );


        document.getElementById(
            "pricing_change"
        ).innerText =
            formatDifference(
                lending.current_pricing,
                lending.recommended_pricing,
                "pp"
            );


        document.getElementById(
            "tenure_change"
        ).innerText =
            formatDifference(
                lending.current_tenure,
                lending.recommended_tenure,
                "months"
            );


        /* ================= FORECAST ================= */

        const forecast =
            result.forecast;


        document.getElementById(
            "current_predicted_value"
        ).innerText =
            formatCurrency(
                forecast.current_predicted_value
            );


        document.getElementById(
            "forecast_12_month"
        ).innerText =
            formatCurrency(
                forecast.forecast_12_month
            );


        document.getElementById(
            "forecast_24_month"
        ).innerText =
            formatCurrency(
                forecast.forecast_24_month
            );


        document.getElementById(
            "forecast_36_month"
        ).innerText =
            formatCurrency(
                forecast.forecast_36_month
            );


        createForecastChart(
            forecast
        );


        /* ================= BUSINESS DECISION ================= */

        document.getElementById(
            "overall_risk"
        ).innerText =
            "Overall Risk: " +
            result.business_decision
                .overall_risk;


        document.getElementById(
            "recommended_action"
        ).innerText =
            result.business_decision
                .recommended_action;


        /* ================= SCENARIO SIMULATOR READY STATE ================= */

        window.__hasPrediction = true;

        const scenarioHint =
            document.getElementById("scenario_hint");

        if (scenarioHint) {
            scenarioHint.innerText =
                "Adjust the stress dials and click \"Run Scenario Simulation\" " +
                "to stress-test this asset's 12/24/36-month residual value.";
        }


        /* ================= SHOW RESULTS ================= */

        document
            .getElementById("results")
            .scrollIntoView({
                behavior: "smooth"
            });


    }

    catch (error) {

        console.error(
            "Connection Error:",
            error
        );

        alert(
            "Could not connect to the prediction server.\n\n" +
            "Make sure the backend is running and reachable."
        );

    }

    finally {

        button.innerHTML =
            originalButtonHTML;

        button.disabled = false;

    }

}


/* ================= CURRENCY ================= */

function formatCurrency(value) {

    const number =
        Number(value);


    if (Number.isNaN(number)) {

        return "₹0";

    }


    return (
        "₹" +
        number.toLocaleString(
            "en-IN",
            {
                maximumFractionDigits: 2,
                minimumFractionDigits: 2
            }
        )
    );

}


/* ================= RISK COLOR ================= */

function getRiskColor(band) {

    switch (
        String(band)
            .toUpperCase()
    ) {

        case "LOW":
            return "#00a651";

        case "MEDIUM":
            return "#f79009";

        case "HIGH":
            return "#e67e22";

        case "CRITICAL":
            return "#d92d20";

        default:
            return "#00a651";

    }

}


/* ================= DIFFERENCE ================= */

function formatDifference(
    current,
    recommended,
    suffix
) {

    const difference =
        Number(recommended) -
        Number(current);


    const sign =
        difference > 0
            ? "+"
            : "";


    return (
        sign +
        difference.toFixed(2) +
        " " +
        suffix
    );

}


/* ================= FORECAST CHART ================= */

function createForecastChart(
    forecast
) {

    const canvas =
        document.getElementById(
            "forecastChart"
        );


    if (
        forecastChart !== null
    ) {

        forecastChart.destroy();

    }


    forecastChart =
        new Chart(
            canvas,
            {

                type: "line",

                data: {

                    labels: [
                        "Current",
                        "12 Months",
                        "24 Months",
                        "36 Months"
                    ],

                    datasets: [

                        {

                            label:
                                "Predicted Residual Value",

                            data: [

                                forecast.current_predicted_value,

                                forecast.forecast_12_month,

                                forecast.forecast_24_month,

                                forecast.forecast_36_month

                            ],

                            borderColor:
                                "#00a651",

                            backgroundColor:
                                "rgba(0,166,81,0.10)",

                            borderWidth: 4,

                            pointRadius: 6,

                            pointHoverRadius: 8,

                            tension: 0.35,

                            fill: true

                        }

                    ]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {

                            display: true,

                            labels: {

                                font: {
                                    family: "Inter"
                                }

                            }

                        }

                    },

                    scales: {

                        y: {

                            beginAtZero: false,

                            ticks: {

                                callback:
                                    function(value) {

                                        return "₹" +
                                            Number(value)
                                                .toLocaleString(
                                                    "en-IN"
                                                );

                                    }

                            }

                        },

                        x: {

                            grid: {
                                display: false
                            }

                        }

                    }

                }

            }

        );

}


/* ================= NUMBER COUNT-UP ANIMATION ================= */

function animateNumberText(el, targetValue, duration, formatFn) {

    if (!el) {
        return;
    }

    const startValue = 0;
    const startTime = performance.now();

    function step(now) {

        const progress = Math.min((now - startTime) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = startValue + (targetValue - startValue) * eased;

        el.innerText = formatFn(current);

        if (progress < 1) {
            requestAnimationFrame(step);
        } else {
            el.innerText = formatFn(targetValue);
        }
    }

    requestAnimationFrame(step);
}


/* ================= RISK GAUGE (semi-circle doughnut) ================= */

function updateRiskGauge(score, color) {

    const canvas = document.getElementById("riskGaugeChart");
    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    const clamped = Math.min(Math.max(Number(score) || 0, 0), 100);

    const gaugeLabel = document.getElementById("gauge_score_label");
    if (gaugeLabel) {
        gaugeLabel.innerText = clamped.toFixed(0);
        gaugeLabel.style.color = color || "#00a651";
    }

    if (riskGaugeChart !== null) {
        riskGaugeChart.destroy();
    }

    riskGaugeChart = new Chart(canvas, {
        type: "doughnut",
        data: {
            labels: ["Risk", "Remaining"],
            datasets: [{
                data: [clamped, 100 - clamped],
                backgroundColor: [color || "#00a651", "#e6efec"],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            circumference: 180,
            rotation: 270,
            cutout: "72%",
            animation: {
                animateRotate: true,
                duration: 900
            },
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            }
        }
    });
}


/* ================= PORTFOLIO RISK DISTRIBUTION (static benchmark) ================= */

function createPortfolioDistributionChart() {

    const canvas = document.getElementById("portfolioDistributionChart");
    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    /* Illustrative distribution across the 15,000-agreement liquidated
       training portfolio, as reported in the case study data dictionary
       (Table 4 / notebook Section 8 risk-band breakdown). */
    portfolioDistributionChart = new Chart(canvas, {
        type: "doughnut",
        data: {
            labels: ["Low", "Medium", "High", "Critical"],
            datasets: [{
                data: [0.4, 51.1, 48.2, 0.3],
                backgroundColor: ["#2ecc71", "#f39c12", "#e67e22", "#e74c3c"],
                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 900 },
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        boxWidth: 10,
                        font: { size: 10, family: "Inter" }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            return ctx.label + ": " + ctx.parsed + "%";
                        }
                    }
                }
            }
        }
    });
}


/* ================= SCENARIO SIMULATOR ================= */

function readScenarioAssetInputs() {

    return {
        Asset_Age_Months_At_Seizure:
            Number(document.getElementById("Asset_Age_Months_At_Seizure").value) || 0,

        Asset_Cost_At_Disbursal:
            Number(document.getElementById("Asset_Cost_At_Disbursal").value) || 0,

        Asset_Fuel_Type:
            document.getElementById("Asset_Fuel_Type").value || "Petrol"
    };
}

async function runScenarioSimulation() {

    const button = document.querySelector(".scenario-run-button");
    const originalHTML = button.innerHTML;

    button.innerHTML = "<span>Simulating...</span><span class=\"button-arrow\">⟳</span>";
    button.disabled = true;

    const assetInputs = readScenarioAssetInputs();

    if (!assetInputs.Asset_Cost_At_Disbursal || !assetInputs.Asset_Age_Months_At_Seizure) {
        alert(
            "Enter at least Asset Cost At Disbursal and Asset Age At Seizure " +
            "in the Asset Profile section above before running the scenario simulation."
        );
        button.innerHTML = originalHTML;
        button.disabled = false;
        return;
    }

    const payload = {
        Asset_Age_Months_At_Seizure: assetInputs.Asset_Age_Months_At_Seizure,
        Asset_Cost_At_Disbursal: assetInputs.Asset_Cost_At_Disbursal,
        Asset_Fuel_Type: assetInputs.Asset_Fuel_Type,
        ev_adoption_stress: Number(document.getElementById("ev_stress_slider").value),
        inflation_stress: Number(document.getElementById("inflation_stress_slider").value),
        fuel_price_stress: Number(document.getElementById("fuel_stress_slider").value)
    };

    try {

        const response = await fetch("/scenario/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            alert("Scenario simulation failed.\n\n" + JSON.stringify(errorData, null, 2));
            return;
        }

        const result = await response.json();

        createScenarioChart(result);

        const erosion = result.erosion_vs_base_36m_pct || {};

        setErosionCard("scenario_base_erosion", erosion["Base Case"]);
        setErosionCard("scenario_ev_erosion", erosion["High EV Adoption"]);
        setErosionCard("scenario_inflation_erosion", erosion["High Inflation"]);
        setErosionCard("scenario_fuel_erosion", erosion["Fuel Price Shock"]);
        setErosionCard("scenario_custom_erosion", erosion["Custom Stress"]);

        document
            .getElementById("scenarioChart")
            .closest(".output-section")
            .scrollIntoView({ behavior: "smooth", block: "center" });

    } catch (error) {
        console.error("Scenario simulation error:", error);
        alert("Could not reach the scenario simulation service. Please try again.");
    } finally {
        button.innerHTML = originalHTML;
        button.disabled = false;
    }
}

function setErosionCard(elementId, value) {
    const el = document.getElementById(elementId);
    if (!el) {
        return;
    }
    const v = Number(value);
    el.innerText = (Number.isNaN(v) ? 0 : v).toFixed(1) + "%";
}

function createScenarioChart(result) {

    const canvas = document.getElementById("scenarioChart");
    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    if (scenarioChart !== null) {
        scenarioChart.destroy();
    }

    const horizons = (result.horizons || [12, 24, 36]).map(h => h + "M");
    const scenarios = result.scenarios || {};

    const seriesStyle = {
        "Base Case":         { color: "#45a4e5" },
        "High EV Adoption":  { color: "#00a651" },
        "High Inflation":    { color: "#f79009" },
        "Fuel Price Shock":  { color: "#d92d20" },
        "Custom Stress":     { color: "#7a4ee0" }
    };

    const datasets = Object.keys(scenarios).map(function (name) {
        const style = seriesStyle[name] || { color: "#718087" };
        return {
            label: name,
            data: scenarios[name],
            borderColor: style.color,
            backgroundColor: style.color + "22",
            borderWidth: name === "Custom Stress" ? 4 : 2.5,
            borderDash: name === "Custom Stress" ? [] : [],
            pointRadius: 5,
            pointHoverRadius: 7,
            tension: 0.35,
            fill: false
        };
    });

    scenarioChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: horizons,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 900 },
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { font: { family: "Inter", size: 11 } }
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: function (value) {
                            return "₹" + Number(value).toLocaleString("en-IN");
                        }
                    }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}


/* ================= SCROLL-REVEAL ANIMATION ================= */

function initScrollReveal() {

    const targets = document.querySelectorAll(".reveal");

    if (!("IntersectionObserver" in window)) {
        targets.forEach(el => el.classList.add("visible"));
        return;
    }

    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12 });

    targets.forEach(el => observer.observe(el));
}


/* ================= SCENARIO SLIDER LIVE LABELS ================= */

function initScenarioSliders() {

    const bindings = [
        { slider: "ev_stress_slider", label: "ev_stress_value" },
        { slider: "inflation_stress_slider", label: "inflation_stress_value" },
        { slider: "fuel_stress_slider", label: "fuel_stress_value" }
    ];

    bindings.forEach(function (b) {
        const slider = document.getElementById(b.slider);
        const label = document.getElementById(b.label);
        if (!slider || !label) {
            return;
        }
        label.innerText = slider.value + "%";
        slider.addEventListener("input", function () {
            label.innerText = slider.value + "%";
        });
    });
}


/* ================= INITIAL STATE ================= */

document.addEventListener(
    "DOMContentLoaded",
    function() {

        document
            .getElementById(
                "results"
            )
            .style.display = "block";

        initScrollReveal();
        initScenarioSliders();
        createPortfolioDistributionChart();

    }
);

/* ================================================================
   AI LENDING COPILOT — chat widget logic
   Talks to POST /copilot/ask, always sending the latest prediction
   result (if any) as context so answers stay grounded in the
   numbers actually shown on this dashboard.
================================================================ */

window.__lastPredictionContext = window.__lastPredictionContext || null;
let __copilotOpened = false;
let __copilotBusy = false;

function toggleCopilot() {
    const panel = document.getElementById("copilot-panel");
    const isHidden = panel.classList.contains("copilot-hidden");

    if (isHidden) {
        panel.classList.remove("copilot-hidden");
        if (!__copilotOpened) {
            __copilotOpened = true;
            copilotAddMessage(
                "bot",
                "Hi! I'm the AI Lending Copilot for this dashboard. " +
                "Run a prediction, then ask me why it scored the way it did " +
                "— or ask about the model, LTV, pricing, tenure, or the scenario forecasts."
            );
            copilotRenderChips([
                "Why is this agreement risky?",
                "What does Asset Health Index mean?",
                "How is the recommended LTV calculated?",
                "Which model powers these predictions?"
            ]);
        }
        const input = document.getElementById("copilot-input");
        if (input) {
            input.focus();
        }
    } else {
        panel.classList.add("copilot-hidden");
    }
}

function onNewPredictionForCopilot(result) {
    if (!__copilotOpened) {
        return;
    }
    const band = result && result.summary ? result.summary.risk_band : null;
    if (band) {
        copilotAddMessage(
            "bot",
            "New prediction analyzed — risk band: " + band + ". Ask me why, or how to improve it."
        );
        copilotRenderChips([
            "Why is this agreement risky?",
            "How can I reduce the risk?",
            "Explain the recommended lending terms",
            "What will this asset be worth in 24 months?"
        ]);
    }
}

function copilotAddMessage(role, text) {
    const container = document.getElementById("copilot-messages");
    if (!container) {
        return;
    }
    const bubble = document.createElement("div");
    bubble.className = "copilot-msg " + (role === "user" ? "copilot-msg-user" : "copilot-msg-bot");
    bubble.textContent = text;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
    return bubble;
}

function copilotRenderChips(suggestions) {
    const chipsContainer = document.getElementById("copilot-chips");
    if (!chipsContainer) {
        return;
    }
    chipsContainer.innerHTML = "";
    (suggestions || []).forEach(function (text) {
        const chip = document.createElement("div");
        chip.className = "copilot-chip";
        chip.textContent = text;
        chip.onclick = function () {
            sendCopilotMessage(text);
        };
        chipsContainer.appendChild(chip);
    });
}

function handleCopilotSubmit(event) {
    event.preventDefault();
    const input = document.getElementById("copilot-input");
    const text = (input.value || "").trim();
    if (!text) {
        return false;
    }
    input.value = "";
    sendCopilotMessage(text);
    return false;
}

async function sendCopilotMessage(question) {
    if (__copilotBusy) {
        return;
    }
    __copilotBusy = true;

    copilotAddMessage("user", question);
    document.getElementById("copilot-chips").innerHTML = "";

    const typingBubble = document.createElement("div");
    typingBubble.className = "copilot-msg copilot-msg-typing";
    typingBubble.textContent = "Thinking...";
    const container = document.getElementById("copilot-messages");
    container.appendChild(typingBubble);
    container.scrollTop = container.scrollHeight;

    try {
        const response = await fetch("/copilot/ask", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question,
                context: window.__lastPredictionContext || null
            })
        });

        const data = await response.json();

        typingBubble.remove();
        copilotAddMessage("bot", data.answer || "Sorry, I couldn't process that.");
        copilotRenderChips(data.suggestions || []);
    } catch (error) {
        console.error("Copilot error:", error);
        typingBubble.remove();
        copilotAddMessage(
            "bot",
            "I couldn't reach the copilot service just now. Please try again in a moment."
        );
    } finally {
        __copilotBusy = false;
    }
}
