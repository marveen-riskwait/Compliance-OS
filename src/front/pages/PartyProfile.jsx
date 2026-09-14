import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { api } from "../services/api";
import useGlobalReducer from "../hooks/useGlobalReducer";
import { can } from "../permissions/can";
import { edgeLabel } from "./Customer360";

const KIND_ICON = { PERSON: "fa-user", ORGANIZATION: "fa-building", TRUST: "fa-scale-balanced" };

// The 360° view of one economic actor: every entity it is linked to across the
// whole book. Reached by clicking an actor's name anywhere in the app.
export const PartyProfile = () => {
  const { id } = useParams();
  const { state } = useLocation();
  const { store } = useGlobalReducer();
  const [p, setP] = useState(null);
  const [error, setError] = useState(null);
  // "Link this actor to a customer file": the actor becomes an owner /
  // controller of another file's subject — the same shared record, so the
  // two files connect into one economic group.
  const [book, setBook] = useState([]);
  const [linkForm, setLinkForm] = useState({ customer_id: "", relationship_type: "SHAREHOLDER", percentage: "" });
  const [linking, setLinking] = useState(false);
  const [notice, setNotice] = useState(null);

  const load = () => api.partyProfile(id).then(setP).catch((e) => setError(e.message));
  useEffect(() => { load(); }, [id]);   // eslint-disable-line
  useEffect(() => {
    if (can(store.user, "kyb.edit")) api.customers().then(setBook).catch(() => setBook([]));
  }, [store.user]);   // eslint-disable-line

  const link = async (e) => {
    e.preventDefault();
    if (!linkForm.customer_id || linking) return;
    setLinking(true); setError(null); setNotice(null);
    try {
      await api.addOwnership(Number(linkForm.customer_id), {
        link_party_id: Number(id), owner_kind: p.kind,
        relationship_type: linkForm.relationship_type,
        percentage: Number(linkForm.percentage) || 0,
      });
      const target = book.find((c) => String(c.id) === String(linkForm.customer_id));
      setNotice(`Linked to ${target ? target.name : "the file"} — the two files now share this actor.`);
      setLinkForm({ customer_id: "", relationship_type: "SHAREHOLDER", percentage: "" });
      await load();
    } catch (err) { setError(err.message); }
    finally { setLinking(false); }
  };

  if (error) return <div className="alert alert-danger">{error}</div>;
  if (!p) return <div className="empty">Loading actor…</div>;

  const owns = (p.appears_in || []).filter((l) => l.kind === "OWNS");
  const subjectOf = (p.appears_in || []).filter((l) => l.kind === "SUBJECT");
  const detail = [p.nationality, p.country_of_residence, p.country_of_incorporation]
    .filter(Boolean).join(" · ");

  // Where "back" goes: the file the user came from (carried in router
  // state), else the first file this actor belongs to, else the book.
  const back = state?.back
    || (subjectOf[0]?.customer_id && { path: `/customers/${subjectOf[0].customer_id}?tab=relations`, label: `${subjectOf[0].name} · Relations` })
    || (owns[0]?.customer_id && { path: `/customers/${owns[0].customer_id}?tab=relations`, label: `${owns[0].name} · Relations` })
    || { path: "/customers", label: "Customers" };
  const alreadyIn = new Set((p.appears_in || []).map((l) => l.customer_id).filter(Boolean));

  const Row = ({ l }) => (
    <div className="work-row">
      <span className="dotsev INFO" />
      <div className="grow">
        <div className="title">
          {l.customer_id
            ? <Link to={`/customers/${l.customer_id}?tab=relations`}>{l.name}</Link>
            : l.name}
        </div>
        <div className="meta">
          {l.relationship}{l.percentage ? ` · ${l.percentage}%` : ""}
          {l.customer_id ? " · in our book" : ""}
        </div>
      </div>
      {l.percentage ? <span className="chip INFO">{l.percentage}%</span> : null}
    </div>
  );

  return (
    <>
      <div className="muted" style={{ fontSize: ".8rem" }}>
        <Link to={back.path}>← {back.label}</Link>
      </div>
      <div className="d-flex align-items-center gap-2" style={{ margin: ".3rem 0 1rem" }}>
        <span className="co-avatar" style={{ width: 40, height: 40 }}>
          <i className={`fa-solid ${KIND_ICON[p.kind] || "fa-user"}`} />
        </span>
        <div>
          <h3 style={{ margin: 0 }}>{p.name}</h3>
          <div className="muted">
            {p.kind === "ORGANIZATION" ? "Company" : p.kind === "TRUST" ? "Trust" : "Person"}
            {(p.nationalities_names || []).length > 0 ? ` · ${p.nationalities_names.join(" / ")}` : detail ? ` · ${detail}` : ""}
            {p.country_of_residence_name && p.kind === "PERSON" ? ` · resident in ${p.country_of_residence_name}` : ""}
            {p.date_of_birth ? ` · born ${p.date_of_birth.slice(0, 10)}` : ""}
            {p.gender ? ` · ${p.gender}` : ""}
            {p.registration_number ? ` · #${p.registration_number}` : ""}
          </div>
        </div>
        {p.is_pep && <span className="chip HIGH">PEP{p.pep_type ? ` · ${p.pep_type}` : ""}</span>}
      </div>

      {subjectOf.length > 0 && (
        <div className="co-card">
          <div className="section-title">Is our customer</div>
          {subjectOf.map((l) => <Row key={`s${l.customer_id}`} l={{ ...l, relationship: "subject of the file" }} />)}
        </div>
      )}

      <div className="co-card">
        <div className="section-title">Participations ({owns.length})</div>
        {owns.length === 0
          ? <div className="muted" style={{ fontSize: ".88rem" }}>No holdings recorded for this actor.</div>
          : owns.map((l, i) => <Row key={i} l={l} />)}
      </div>

      {error && <div className="alert alert-danger py-2">{error}</div>}
      {notice && <div className="alert alert-success py-2">{notice}</div>}
      {can(store.user, "kyb.edit") && (
        <div className="co-card">
          <div className="section-title">Link this actor to a customer file</div>
          <div className="muted" style={{ fontSize: ".85rem", marginBottom: ".5rem" }}>
            Makes this actor an owner or controller of another file’s subject — one shared record, so the
            files connect into a group and the group risk follows.
          </div>
          <form onSubmit={link} className="row g-1 align-items-end">
            <div className="col-12 col-md-5">
              <select className="form-select form-select-sm" value={linkForm.customer_id} required
                onChange={(e) => setLinkForm({ ...linkForm, customer_id: e.target.value })}>
                <option value="">— choose a customer file —</option>
                {book.filter((c) => !alreadyIn.has(c.id) && c.id !== p.customer_id).map((c) => (
                  <option key={c.id} value={c.id}>{c.name} ({c.customer_type.toLowerCase()})</option>
                ))}
              </select>
            </div>
            <div className="col-6 col-md-3">
              <select className="form-select form-select-sm" value={linkForm.relationship_type}
                onChange={(e) => setLinkForm({ ...linkForm, relationship_type: e.target.value })}>
                {["SHAREHOLDER", "DIRECTOR", "UBO", "CONTROL", "AUTHORIZED_REP", "SETTLOR", "TRUSTEE", "PROTECTOR", "BENEFICIARY"].map((t) => (
                  <option key={t} value={t}>{edgeLabel(t)}</option>
                ))}
              </select>
            </div>
            <div className="col-3 col-md-2">
              <input className="form-control form-control-sm" placeholder="%" type="number" min="0" max="100"
                value={linkForm.percentage} onChange={(e) => setLinkForm({ ...linkForm, percentage: e.target.value })} />
            </div>
            <div className="col-3 col-md-2">
              <button className="btn btn-sm btn-co w-100" disabled={linking || !linkForm.customer_id}>
                <i className="fa-solid fa-link" /> Link
              </button>
            </div>
          </form>
        </div>
      )}

      {(p.owned_by || []).length > 0 && (
        <div className="co-card">
          <div className="section-title">Owned / controlled by</div>
          {p.owned_by.map((o, i) => (
            <div className="work-row" key={i}>
              <span className="dotsev INFO" />
              <div className="grow">
                <div className="title">
                  <Link to={`/parties/${o.party_id}`}>{o.name}</Link>
                </div>
                <div className="meta">{edgeLabel(o.relationship)}{o.percentage ? ` · ${o.percentage}%` : ""}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
};
