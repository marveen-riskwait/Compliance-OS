import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import useGlobalReducer from "../hooks/useGlobalReducer";
import { can } from "../permissions/can";
import { DeleteCustomerModal } from "../components/DeleteCustomerModal";
import { RowMenu } from "../components/RowMenu";
import { CountrySelect, ActivitySelect } from "../components/Catalogues";
import { NameSuggest, onboardingChip } from "../components/NameSuggest";

const EMPTY_FORM = {
  name: "", customer_type: "INDIVIDUAL", legal_form: "", country: "",
  business_activity: "", business_activity_detail: "", complex_ownership: false,
  date_of_birth: "",
};

// Company legal forms — the sub-type drives the KYC document checklist.
const LEGAL_FORM_OPTIONS = [
  ["PRIVATELY_HELD", "Privately held company"],
  ["PARTNERSHIP", "Partnership"],
  ["LISTED", "Listed company (simplified DD)"],
];

export const Customers = () => {
  const { store } = useGlobalReducer();
  const canCreate = can(store.user, "customer.create");
  // Removing is archiving by default, so it follows customer.update; erasing
  // the rows underneath is what customer.delete gates, inside the modal.
  const canRemove = can(store.user, "customer.update");
  const [deleting, setDeleting] = useState(null);
  const [archived, setArchived] = useState(false);
  const [customers, setCustomers] = useState([]);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  // An existing file that matches what is being typed / was refused as a
  // duplicate by the server: shown with a link, never silently overwritten.
  const [existing, setExisting] = useState(null);

  const load = () => api.customers(archived).then(setCustomers).catch((e) => setError(e.message));
  useEffect(() => { load(); }, [archived]);

  const restore = async (cu) => {
    try { await api.restoreCustomer(cu.id, "Restored from archive"); load(); }
    catch (e) { setError(e.message); }
  };

  const create = async (e) => {
    e.preventDefault();
    if (creating) return;                    // no double submit on a slow POST
    setCreating(true); setError(null);
    try {
      const created = await api.createCustomer(
        existing?.confirmed ? { ...form, allow_duplicate: true } : form);
      // Show the new file straight away from the POST response, then reconcile
      // with the server (risk scoring runs on create, so the row is refreshed).
      setCustomers((prev) => [created, ...prev.filter((c) => c.id !== created.id)]);
      setForm(EMPTY_FORM);
      setExisting(null);
      setShowForm(false);
      setNotice(`Customer registered — ${created.name}.`);
      load();
    } catch (err) {
      if (err.status === 409 && err.data?.existing?.length) {
        // The server found the same name and type in the active book.
        setExisting({ files: err.data.existing, confirmed: false, fromServer: true });
      } else setError(err.message);
    }
    finally { setCreating(false); }
  };

  // Let the confirmation fade instead of lingering over the list.
  useEffect(() => {
    if (!notice) return undefined;
    const t = setTimeout(() => setNotice(null), 5000);
    return () => clearTimeout(t);
  }, [notice]);

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h3 style={{ margin: 0 }}>{archived ? "Archived customers" : "Customers"}</h3>
        <div style={{ display: "flex", gap: ".5rem" }}>
          <button className="btn btn-outline-secondary"
            onClick={() => setArchived((a) => !a)}
            title="Archived files are kept but taken out of the active book">
            <i className="fa-solid fa-box-archive" />{" "}
            {archived ? "Back to active" : "Archived"}
          </button>
          {canCreate && !archived && (
            <button className="btn btn-co" onClick={() => setShowForm((s) => !s)}>
              <i className="fa-solid fa-plus" /> New customer
            </button>
          )}
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {notice && (
        <div className="alert alert-success py-2">
          <i className="fa-solid fa-circle-check" /> {notice}
        </div>
      )}

      {showForm && (
        <form className="co-card" onSubmit={create} style={{ marginBottom: "1rem" }}>
          <div className="row g-2">
            <div className="col-md-6">
              <label className="form-label">Name</label>
              <NameSuggest value={form.name} customerType={form.customer_type}
                placeholder="Start typing — existing files and watchlists appear"
                onChange={(name) => { setForm({ ...form, name }); if (existing && !existing.confirmed) setExisting(null); }}
                onPickExisting={(c) => setExisting({ files: [c], confirmed: false, fromServer: false })} />
            </div>
            {form.customer_type === "INDIVIDUAL" && (
              <div className="col-md-3">
                <label className="form-label">Date of birth</label>
                <input className="form-control" type="date" value={form.date_of_birth}
                  onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })} />
                <div className="form-text">Tells homonyms apart — and lets a genuine namesake through.</div>
              </div>
            )}
            <div className="col-md-3">
              <label className="form-label">Type</label>
              <select className="form-select" value={form.customer_type}
                onChange={(e) => setForm({ ...form, customer_type: e.target.value,
                  legal_form: e.target.value === "COMPANY" ? form.legal_form : "" })}>
                <option value="INDIVIDUAL">Individual</option>
                <option value="COMPANY">Company</option>
                <option value="TRUST">Trust / legal arrangement</option>
              </select>
            </div>
            {form.customer_type === "COMPANY" && (
              <div className="col-md-3">
                <label className="form-label">Legal form</label>
                <select className="form-select" value={form.legal_form}
                  onChange={(e) => setForm({ ...form, legal_form: e.target.value })}>
                  <option value="">— not classified —</option>
                  {LEGAL_FORM_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
            )}
            <div className="col-md-3">
              <label className="form-label">Country <span className="text-danger">*</span></label>
              <CountrySelect value={form.country} required
                onChange={(code) => setForm({ ...form, country: code })} />
            </div>
            <div className="col-md-6">
              <label className="form-label">
                Business activity{form.customer_type === "COMPANY" && <span className="text-danger"> *</span>}
              </label>
              <ActivitySelect value={form.business_activity} required={form.customer_type === "COMPANY"}
                onChange={(code) => setForm({ ...form, business_activity: code })} />
              <input className="form-control form-control-sm mt-1" value={form.business_activity_detail}
                placeholder="Describe the activity in a few words (optional)"
                onChange={(e) => setForm({ ...form, business_activity_detail: e.target.value })} />
            </div>
            <div className="col-md-6 d-flex align-items-end">
              <div className="form-check">
                <input className="form-check-input" type="checkbox" checked={form.complex_ownership}
                  onChange={(e) => setForm({ ...form, complex_ownership: e.target.checked })} id="cx" />
                <label className="form-check-label" htmlFor="cx">Complex ownership structure</label>
              </div>
            </div>
          </div>
          {existing && (
            <div className={`alert ${existing.confirmed ? "alert-secondary" : "alert-warning"} mt-3 mb-0 py-2`}>
              <div>
                <i className="fa-solid fa-triangle-exclamation" />{" "}
                {existing.fromServer ? "This file already exists" : "You picked an existing file"}
                {existing.files.length > 1 ? ` (${existing.files.length} matches)` : ""}:
              </div>
              {existing.files.map((c) => (
                <div key={c.id} className="d-flex align-items-center flex-wrap gap-2 mt-1">
                  <b>{c.name}</b>
                  <span className="muted">{c.customer_type} · {c.country_name || c.country || "—"}{c.date_of_birth ? ` · born ${c.date_of_birth}` : ""}</span>
                  {onboardingChip(c)}
                  <Link to={`/customers/${c.id}`} className="btn btn-sm btn-co">Open the existing file</Link>
                </div>
              ))}
              {!existing.confirmed && (
                <button type="button" className="btn btn-sm btn-outline-secondary mt-2"
                  onClick={() => setExisting({ ...existing, confirmed: true })}>
                  This is a different {form.customer_type.toLowerCase()} — create a new file anyway
                </button>
              )}
            </div>
          )}
          <button className="btn btn-co mt-3" disabled={creating || (existing && !existing.confirmed)}>
            {creating ? "Creating…" : existing?.confirmed ? "Create a separate file" : "Create"}
          </button>
        </form>
      )}

      <div className="co-card">
        {customers.length === 0 && (
          <div className="empty">
            {archived ? "No archived customers." : "No customers yet."}
          </div>
        )}
        {customers.map((cu) => (
          <div className="work-row" key={cu.id}>
            <span className={`dotsev ${cu.risk_level}`} />
            <div className="grow">
              <div className="title"><Link to={`/customers/${cu.id}`}>{cu.name}</Link></div>
              <div className="meta">
                {cu.customer_type} · {cu.country_name || cu.country || "—"}
                {cu.business_activity ? ` · ${cu.business_activity_label || cu.business_activity}` : ""}
                {cu.is_pep ? " · PEP" : ""}
                {cu.has_sanctions_match ? " · SANCTIONS" : ""}
              </div>
            </div>
            {onboardingChip(cu)}
            <span className={`chip ${cu.risk_level}`}>{cu.risk_level} · {cu.risk_score}</span>
            <Link to={`/customers/${cu.id}`} className="btn btn-sm btn-outline-secondary">Open</Link>
            <RowMenu items={[
              archived && canRemove && {
                label: "Restore to active", icon: "fa-solid fa-rotate-left",
                onClick: () => restore(cu),
              },
              canRemove && {
                label: archived ? "Delete record…" : "Remove customer…",
                icon: "fa-solid fa-trash", danger: true,
                onClick: () => setDeleting(cu),
              },
            ]} />
          </div>
        ))}
      </div>

      {deleting && (
        <DeleteCustomerModal
          customer={deleting}
          onClose={() => setDeleting(null)}
          onDeleted={() => { setDeleting(null); load(); }}
          onArchived={() => { setDeleting(null); load(); }}
        />
      )}
    </>
  );
};
