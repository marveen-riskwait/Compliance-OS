"""Linked transactional flows: money moving BETWEEN members of the same economic
group. Per-customer monitoring sees each leg alone; only at the group level do
intra-group transfers and round-trips (a layering pattern) surface — the
counterparty of a leg is matched by name to a sister member."""
from conftest import auth


def _company(client, tok, name):
    return client.post("/api/customers", headers=auth(tok),
                       json={"name": name, "customer_type": "COMPANY",
                             "country": "Luxembourg"}).get_json()["id"]


def _group_of_two(client, tok, name_a, name_b):
    """Two companies made into one group by a shared UBO."""
    a = _company(client, tok, name_a)
    b = _company(client, tok, name_b)
    r = client.post(f"/api/customers/{a}/ownership", headers=auth(tok),
                    json={"owner_name": "Lena Ohlsson", "owner_kind": "PERSON",
                          "relationship_type": "UBO", "percentage": 60})
    pid = r.get_json()["owner"]["id"]
    client.post(f"/api/customers/{b}/ownership", headers=auth(tok),
                json={"link_party_id": pid, "relationship_type": "UBO",
                      "percentage": 40})
    return a, b


def _tx(client, tok, cid, direction, amount, counterparty):
    return client.post(f"/api/customers/{cid}/transactions", headers=auth(tok),
                       json={"direction": direction, "amount": amount,
                             "currency": "EUR", "method": "SEPA",
                             "counterparty_name": counterparty})


def test_intra_group_flow_direction_and_round_trip(client, tokens):
    tok = tokens["officer@test.io"]
    a, b = _group_of_two(client, tok, "Orion Holding SA", "Orion Trading SA")

    _tx(client, tok, a, "OUTBOUND", 5000, "Orion Trading SA")   # A -> B
    _tx(client, tok, b, "OUTBOUND", 3000, "Orion Holding SA")   # B -> A (return)

    g = client.get(f"/api/customers/{a}/group-flows", headers=auth(tok)).get_json()
    edges = {(e["source_id"], e["target_id"]): e for e in g["flows"]}

    assert (a, b) in edges and (b, a) in edges           # both directions booked
    assert edges[(a, b)]["amount_base"] == 5000
    assert edges[(a, b)]["round_trip"] is True
    assert g["round_trips"] == 1                         # the pair counted once
    assert g["total_base"] == 8000


def test_inbound_leg_is_attributed_to_the_payer(client, tokens):
    tok = tokens["officer@test.io"]
    a, b = _group_of_two(client, tok, "Vega Capital SA", "Vega Services SA")

    # A records money coming IN from B => the flow is B -> A.
    _tx(client, tok, a, "INBOUND", 4200, "Vega Services SA")

    g = client.get(f"/api/customers/{a}/group-flows", headers=auth(tok)).get_json()
    edges = {(e["source_id"], e["target_id"]): e for e in g["flows"]}
    assert (b, a) in edges and (a, b) not in edges
    assert edges[(b, a)]["round_trip"] is False


def test_external_counterparty_is_not_a_group_flow(client, tokens):
    tok = tokens["officer@test.io"]
    a, b = _group_of_two(client, tok, "Lyra Holding SA", "Lyra Trading SA")

    _tx(client, tok, a, "OUTBOUND", 6000, "Some Unrelated Vendor Ltd")

    g = client.get(f"/api/customers/{a}/group-flows", headers=auth(tok)).get_json()
    assert g["flows"] == []
    assert g["total_base"] == 0


def test_flagged_leg_is_counted_on_the_flow(client, tokens, app):
    tok = tokens["officer@test.io"]
    a, b = _group_of_two(client, tok, "Zenit Holding SA", "Zenit Trading SA")
    _tx(client, tok, a, "OUTBOUND", 7000, "Zenit Trading SA")

    with app.app_context():
        from api.models import db, Transaction, Customer
        ca = Customer.query.filter_by(name="Zenit Holding SA").first()
        t = Transaction.query.filter_by(customer_id=ca.id).first()
        t.flagged = True
        db.session.commit()

    g = client.get(f"/api/customers/{a}/group-flows", headers=auth(tok)).get_json()
    edge = next(e for e in g["flows"] if e["source_id"] == a and e["target_id"] == b)
    assert edge["flagged"] == 1
    assert g["flagged_flows"] == 1
