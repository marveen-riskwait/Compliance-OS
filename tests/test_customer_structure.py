"""Modularity brick B: a company's legal form (privately-held / partnership /
listed) selects its KYC document checklist. A listed company on a regulated
market gets the simplified-due-diligence list — the UBO-heavy documents do not
apply to it, by design."""
from conftest import auth


def _company(client, tok, name, legal_form=None):
    return client.post("/api/customers", headers=auth(tok),
                       json={"name": name, "customer_type": "COMPANY",
                             "country": "Luxembourg",
                             "legal_form": legal_form}).get_json()


def _codes(app, cid):
    with app.app_context():
        from api.engine import requirement_engine
        from api.models import Customer
        c = Customer.query.get(cid)
        return {ri.code for ri in requirement_engine.evaluate(c)}


def test_privately_held_gets_the_ubo_checklist(client, tokens, app):
    tok = tokens["officer@test.io"]
    c = _company(client, tok, "Meridian Privé SA", "PRIVATELY_HELD")
    assert c["legal_form"] == "PRIVATELY_HELD"
    assert c["sdd"] is False
    codes = _codes(app, c["id"])
    # Customer-level documents (the per-party UBO passports appear once a UBO is
    # on the file — see test_per_party_documents).
    assert {"COMMERCIAL_REGISTER", "STRUCTURE_CHART", "SIGNATORY_LIST",
            "BENEFICIAL_OWNER_EXTRACT"} <= codes
    assert "PROOF_OF_LISTING" not in codes      # not a listed company
    assert "LPA" not in codes                   # not a partnership


def test_listed_company_is_simplified_due_diligence(client, tokens, app):
    tok = tokens["officer@test.io"]
    c = _company(client, tok, "Bourse Cotée SA", "LISTED")
    assert c["sdd"] is True
    codes = _codes(app, c["id"])
    assert "PROOF_OF_LISTING" in codes
    # The UBO-heavy diligence a listed issuer is exempt from:
    for absent in ("COMMERCIAL_REGISTER", "STRUCTURE_CHART",
                   "BENEFICIAL_OWNER_EXTRACT", "SHAREHOLDER_REGISTER", "LPA"):
        assert absent not in codes, absent
    # But basic incorporation identity still applies:
    assert "CERTIFICATE_OF_INCORPORATION" in codes


def test_partnership_needs_lpa_and_aml_letter(client, tokens, app):
    tok = tokens["officer@test.io"]
    c = _company(client, tok, "Alpha Fund LP", "PARTNERSHIP")
    codes = _codes(app, c["id"])
    assert {"LPA", "AML_LETTER", "COMMERCIAL_REGISTER", "STRUCTURE_CHART"} <= codes
    assert "PROOF_OF_LISTING" not in codes


def test_reclassifying_recomputes_the_checklist(client, tokens, app):
    tok = tokens["officer@test.io"]
    c = _company(client, tok, "Unclassified Co")     # no legal form yet
    before = _codes(app, c["id"])
    assert "PROOF_OF_LISTING" not in before

    r = client.patch(f"/api/customers/{c['id']}/legal-form", headers=auth(tok),
                     json={"legal_form": "LISTED"})
    assert r.status_code == 200 and r.get_json()["sdd"] is True

    after = _codes(app, c["id"])
    assert "PROOF_OF_LISTING" in after
    assert "STRUCTURE_CHART" not in after            # dropped to the SDD list


def test_legal_form_is_company_only(client, tokens):
    tok = tokens["officer@test.io"]
    # Ignored on a non-company at creation.
    ind = client.post("/api/customers", headers=auth(tok),
                      json={"name": "Jane Doe", "customer_type": "INDIVIDUAL",
                            "legal_form": "LISTED"}).get_json()
    assert ind["legal_form"] is None and ind["sdd"] is False
    # And rejected on the classify endpoint.
    r = client.patch(f"/api/customers/{ind['id']}/legal-form", headers=auth(tok),
                     json={"legal_form": "LISTED"})
    assert r.status_code == 400
