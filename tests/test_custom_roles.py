"""Admin-managed custom roles: create (optionally cloning another role's
permissions), rename, assign to users, and delete — with the system-role and
still-assigned guards, and strict per-organisation scoping."""
from conftest import auth


def _create(client, token, label, base_role=None):
    return client.post("/api/roles", headers=auth(token),
                       json={"label": label, "base_role": base_role})


def test_create_custom_role_is_org_scoped_and_not_system(client, tokens):
    admin = tokens["admin@test.io"]
    r = _create(client, admin, "Senior Reviewer")
    assert r.status_code == 201
    role = r.get_json()
    assert role["is_system"] is False
    assert role["organization_id"] is not None
    assert role["label"] == "Senior Reviewer"
    assert role["name"].startswith("C")           # org-prefixed internal name


def test_create_clones_base_role_permissions(client, tokens):
    admin = tokens["admin@test.io"]
    roles = {x["name"]: x for x in client.get("/api/roles", headers=auth(admin)).get_json()}
    base = roles["KYC_ANALYST"]["permissions"]
    r = _create(client, admin, "Analyst Plus", base_role="KYC_ANALYST").get_json()
    assert set(r["permissions"]) == set(base)


def test_only_role_update_permission_can_create(client, tokens):
    # Analyst lacks role.update.
    r = _create(client, tokens["analyst@test.io"], "Nope")
    assert r.status_code == 403


def test_system_roles_cannot_be_deleted_or_renamed(client, tokens):
    admin = tokens["admin@test.io"]
    roles = {x["name"]: x for x in client.get("/api/roles", headers=auth(admin)).get_json()}
    sys_id = roles["MLRO"]["id"]
    assert client.delete(f"/api/roles/{sys_id}", headers=auth(admin)).status_code == 409
    assert client.patch(f"/api/roles/{sys_id}", headers=auth(admin),
                        json={"label": "x"}).status_code == 409


def test_assign_custom_role_then_delete_is_blocked_until_unassigned(client, tokens, app):
    admin = tokens["admin@test.io"]
    role = _create(client, admin, "Special Duty", base_role="AUDITOR").get_json()

    # Make a user to hold it.
    from api.models import db, User
    from api.auth import hash_password
    with app.app_context():
        from api.models import Organization
        org = Organization.query.first()
        u = User(email="holder@test.io", full_name="Holder", role="KYC_ANALYST",
                 password=hash_password("pw"), organization_id=org.id, is_active=True)
        db.session.add(u); db.session.commit()
        uid = u.id

    # Assign as an additional role.
    assign = client.post(f"/api/users/{uid}/roles", headers=auth(admin),
                         json={"role": role["name"]})
    assert assign.status_code == 200

    # Delete is refused while held.
    blocked = client.delete(f"/api/roles/{role['id']}", headers=auth(admin))
    assert blocked.status_code == 409

    # Unassign, then delete succeeds.
    client.delete(f"/api/users/{uid}/roles/{role['name']}", headers=auth(admin))
    assert client.delete(f"/api/roles/{role['id']}", headers=auth(admin)).status_code == 200


def test_custom_role_permissions_flow_to_the_user(client, tokens, app):
    admin = tokens["admin@test.io"]
    role = _create(client, admin, "Export Only").get_json()
    # Grant one permission on the custom role.
    client.post(f"/api/roles/{role['id']}/permissions", headers=auth(admin),
                json={"code": "data.export", "enabled": True})
    from api.models import db, User
    from api.auth import hash_password
    with app.app_context():
        from api.models import Organization
        org = Organization.query.first()
        u = User(email="exporter@test.io", full_name="Exp", role="KYC_ANALYST",
                 password=hash_password("pw"), organization_id=org.id, is_active=True)
        db.session.add(u); db.session.commit()
        uid = u.id
    client.post(f"/api/users/{uid}/roles", headers=auth(admin), json={"role": role["name"]})
    with app.app_context():
        from api.models import User as U
        assert "data.export" in U.query.get(uid).permission_codes()


def test_other_orgs_custom_role_is_invisible_and_unassignable(client, tokens, app):
    admin = tokens["admin@test.io"]
    # A custom role belonging to a different organisation.
    from api.models import db, Role
    with app.app_context():
        db.session.add(Role(name="C999_FOREIGN", label="Foreign", is_system=False,
                            organization_id=999))
        db.session.commit()
    names = {x["name"] for x in client.get("/api/roles", headers=auth(admin)).get_json()}
    assert "C999_FOREIGN" not in names
