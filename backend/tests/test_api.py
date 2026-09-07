"""HTTP surface — the contract the PWA and the ministry dashboard both consume."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from setubiz.api import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def advisory_payload():
    return {
        "village_query": "Ormanji",
        "savings": 100000,
        "business_category": "dairy",
        "social_category": "sc",
        "annual_family_income": 280000,
        "radius_km": 10,
    }


def test_healthz(client):
    body = client.get("/healthz").json()
    assert body["status"] == "ok"
    assert body["version"]


def test_openapi_schema_is_served(client):
    schema = client.get("/openapi.json").json()
    assert "/api/v1/advisory" in schema["paths"]
    assert "/api/v1/finance/structure" in schema["paths"]


def test_village_search_returns_ranked_confirmable_matches(client):
    matches = client.get("/api/v1/villages/search", params={"q": "ormanji"}).json()
    assert matches
    assert matches[0]["name"] == "Ormanjhi"
    assert matches[0]["reason"]
    assert [m["score"] for m in matches] == sorted((m["score"] for m in matches), reverse=True)


def test_village_search_rejects_an_empty_query(client):
    assert client.get("/api/v1/villages/search", params={"q": ""}).status_code == 422


def test_finance_structure_reproduces_the_golden_vector(client):
    body = client.post(
        "/api/v1/finance/structure", json={"margin": 100000, "business_category": "dairy"}
    ).json()

    assert body["scheme"]["logic"] == "B"
    assert body["scheme"]["max_loan"] == "900000.00"
    schedule = body["schedules"]["max_loan"]
    assert schedule["instalment"] == "44729.31"
    assert len(schedule["rows"]) == 28
    assert schedule["rows"][-1]["closing"] == "0.00"

    sizing = body["right_sizing"]
    assert float(sizing["recommended_loan"]) < float(sizing["max_loan"])
    assert float(sizing["max_loan_min_dscr"]) < float(sizing["dscr_threshold"])
    assert sizing["binding"] in {"dscr", "stress", "scheme_cap", "capital_need"}


def test_finance_structure_out_of_scope_margin(client):
    body = client.post(
        "/api/v1/finance/structure", json={"margin": 600000, "business_category": "dairy"}
    ).json()
    assert body["scheme"]["logic"] == "OUT_OF_SCOPE"
    assert body["schedules"]["max_loan"] is None
    assert "pmegp" in body["scheme"]["referrals"]


def test_finance_structure_rejects_bad_input(client):
    assert client.post("/api/v1/finance/structure", json={"margin": 0}).status_code == 422
    assert (
        client.post(
            "/api/v1/finance/structure", json={"margin": 100000, "business_category": "nope"}
        ).status_code
        == 404
    )


def test_advisory_returns_facts_report_and_validation(client, advisory_payload):
    body = client.post("/api/v1/advisory", json=advisory_payload).json()

    assert body["facts"]["village"]["name"] == "Ormanjhi"
    assert body["facts"]["contains_synthetic_data"] is True
    assert body["validation"]["passed"] is True
    assert body["validation"]["checked"] > 20

    ids = [s["id"] for s in body["report"]["sections"]]
    assert ids[:4] == ["headline", "market_reach", "competition", "loan_structure"]
    assert {"swot", "threats", "repayment", "stress", "scheme", "data_note"} <= set(ids)
    assert all(s["body"].strip() for s in body["report"]["sections"])


def test_advisory_sections_carry_chart_data_for_the_ui(client, advisory_payload):
    body = client.post("/api/v1/advisory", json=advisory_payload).json()
    sections = {s["id"]: s for s in body["report"]["sections"]}

    assert sections["loan_structure"]["data"]["max_loan"]
    assert sections["stress"]["data"]["recommended"]
    assert sections["repayment"]["data"]["recommended"]
    assert sections["market_reach"]["data"]["villages"]
    assert sections["threats"]["data"]["seasonality"]["months"]
    assert sections["swot"]["data"]["quadrants"]


def test_advisory_provenance_covers_every_indexed_number(client, advisory_payload):
    body = client.post("/api/v1/advisory", json=advisory_payload).json()
    facts = body["facts"]
    assert set(facts["provenance"]) == set(facts["numeric_index"])
    known = {s["id"] for s in facts["sources"]}
    assert all(set(ids) <= known for ids in facts["provenance"].values())


def test_advisory_in_hindi(client, advisory_payload):
    body = client.post("/api/v1/advisory", json={**advisory_payload, "language": "hi"}).json()
    assert body["report"]["language"] == "hi"
    assert body["validation"]["passed"] is True
    assert "र" in body["report"]["sections"][0]["body"]  # Devanagari present


def test_advisory_unknown_village_is_a_404(client, advisory_payload):
    response = client.post("/api/v1/advisory", json={**advisory_payload, "village_query": "zzzz"})
    assert response.status_code == 404
    assert "no village matched" in response.json()["detail"]


def test_advisory_requires_a_village(client, advisory_payload):
    payload = {k: v for k, v in advisory_payload.items() if k != "village_query"}
    assert client.post("/api/v1/advisory", json=payload).status_code == 422


def test_cost_templates_expose_derived_totals(client):
    templates = client.get("/api/v1/cost-templates").json()
    assert len(templates) >= 5
    dairy = next(t for t in templates if t["id"] == "dairy_2_animal")
    assert dairy["required_capital"] == "410800.00"
    assert dairy["annual_noi"] == "93600.00"
    assert dairy["source"]


def test_schemes_catalogue(client):
    body = client.get("/api/v1/schemes").json()
    assert {c["id"] for c in body["corporations"]} == {"nsfdc", "nskfdc", "nbcfdc"}
    assert {s["id"] for s in body["comparison"]} >= {"pmmy", "pmegp", "cgtmse"}


def test_metrics_exposes_the_validator_catch_rate(client, advisory_payload):
    client.post("/api/v1/advisory", json=advisory_payload)
    body = client.get("/api/v1/metrics").json()
    assert body["validator"]["generations"] >= 1
    assert 0.0 <= body["validator"]["catch_rate"] <= 1.0
    assert body["narrator"] == "template"
    assert body["data_source"] == "sample"
