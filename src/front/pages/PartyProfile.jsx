import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../services/api";

const KIND_ICON = { PERSON: "fa-user", ORGANIZATION: "fa-building", TRUST: "fa-scale-balanced" };

// The 360° view of one economic actor: every entity it is linked to across the
// whole book. Reached by clicking an actor's name anywhere in the app.
export const PartyProfile = () => {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.partyProfile(id).then(setP).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <div className="alert alert-danger">{error}</div>;
  if (!p) return <div className="empty">Loading actor…</div>;

  const owns = (p.appears_in || []).filter((l) => l.kind === "OWNS");
  const subjectOf = (p.appears_in || []).filter((l) => l.kind === "SUBJECT");
  const detail = [p.nationality, p.country_of_residence, p.country_of_incorporation]
    .filter(Boolean).join(" · ");

  const Row = ({ l }) => (
    <div className="work-row">
      <span className="dotsev INFO" />
      <div className="grow">
        <div className="title">
          {l.customer_id
            ? <Link to={`/customers/${l.customer_id}`}>{l.name}</Link>
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
        <Link to="/customers">← Customers</Link>
      </div>
      <div className="d-flex align-items-center gap-2" style={{ margin: ".3rem 0 1rem" }}>
        <span className="co-avatar" style={{ width: 40, height: 40 }}>
          <i className={`fa-solid ${KIND_ICON[p.kind] || "fa-user"}`} />
        </span>
        <div>
          <h3 style={{ margin: 0 }}>{p.name}</h3>
          <div className="muted">
            {p.kind === "ORGANIZATION" ? "Company" : p.kind === "TRUST" ? "Trust" : "Person"}
            {detail ? ` · ${detail}` : ""}
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
                <div className="meta">{o.relationship}{o.percentage ? ` · ${o.percentage}%` : ""}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
};
