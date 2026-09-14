import { useEffect, useState } from "react";
import { api } from "../services/api";
import { FilePreview } from "./FilePreview";

// The analyst's side of the document loop: read what the customer sent, then
// accept it or send it back. Whatever the customer uploaded — image, PDF,
// scan, anything — opens here rather than forcing a download first.
const STATE = {
  ACCEPTED: ["LOW", "Accepted"],
  RETURNED: ["HIGH", "Returned to customer"],
  RECEIVED: ["INFO", "Awaiting review"],
  EXPECTED: ["MEDIUM", "Not received"],
  EXPIRED: ["CRITICAL", "Expired"],
};

const stateOf = (doc) => {
  if (!doc.has_file) return "EXPECTED";
  if (doc.status === "EXPIRED" || doc.expired) return "EXPIRED";
  if (doc.rejection_reason) return "RETURNED";
  return doc.status === "VERIFIED" ? "ACCEPTED" : "RECEIVED";
};

const fileSize = (bytes) => {
  if (!bytes) return null;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const DocumentReview = ({ customerId, documents, canReview, canUpload, onChange }) => {
  const [preview, setPreview] = useState(null);
  // Upload straight from the file (K1): type from the proof checklist, an
  // optional expiry, or reuse a file already received (F9).
  const [proofs, setProofs] = useState([]);
  const [up, setUp] = useState({ doc_type: "", expiry_date: "", file: null, reuse_of: "" });
  const [uploading, setUploading] = useState(false);
  const [reusing, setReusing] = useState(null);      // doc whose file is being reused
  const [reuseType, setReuseType] = useState("");
  const [returning, setReturning] = useState(null);   // the document being sent back
  const [reasons, setReasons] = useState([]);
  const [reasonCode, setReasonCode] = useState("");
  const [freeText, setFreeText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (canReview) api.rejectionReasons().then(setReasons).catch(() => {});
  }, [canReview]);
  useEffect(() => {
    if (canUpload) api.kycForm(customerId).then((d) => setProofs(d.proofs || [])).catch(() => {});
  }, [canUpload, customerId]);

  const upload = async (e) => {
    e.preventDefault();
    if (!up.doc_type || uploading) return;
    setUploading(true); setError(null);
    try {
      if (up.reuse_of) {
        await api.reuseDocument(customerId, Number(up.reuse_of), { doc_type: up.doc_type });
      } else {
        if (!up.file) { setError("Choose a file, or pick a document already received to reuse."); return; }
        await api.uploadDocument(customerId, up.doc_type, up.file, null, { expiry_date: up.expiry_date });
      }
      setUp({ doc_type: "", expiry_date: "", file: null, reuse_of: "" });
      onChange();
    } catch (err) { setError(err.message); }
    finally { setUploading(false); }
  };
  const reuse = async (doc) => {
    if (!reuseType) return;
    setBusy(true); setError(null);
    try { await api.reuseDocument(customerId, doc.id, { doc_type: reuseType }); setReusing(null); setReuseType(""); onChange(); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const expiryText = (d) => {
    if (!d.expiry_date) return "";
    const day = new Date(d.expiry_date).toLocaleDateString();
    if (d.expired) return ` · expired ${day}`;
    return d.expires_in_days != null && d.expires_in_days <= 30 ? ` · expires ${day} (${d.expires_in_days} d)` : ` · valid until ${day}`;
  };

  const act = async (doc, payload) => {
    setBusy(true); setError(null);
    try {
      await api.reviewDocument(customerId, doc.id, payload);
      setReturning(null); setReasonCode(""); setFreeText("");
      onChange();
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const withFile = (documents || []).filter((d) => d.has_file);

  return (
    <div className="co-card">
      <div className="section-title">Documents ({withFile.length})</div>
      {error && <div className="alert alert-danger py-2">{error}</div>}
      {canUpload && (
        <form onSubmit={upload} className="row g-1 align-items-end" style={{ marginBottom: ".6rem" }}>
          <div className="col-12 col-md-4">
            <select className="form-select form-select-sm" value={up.doc_type} required
              onChange={(e) => setUp({ ...up, doc_type: e.target.value })}>
              <option value="">— document type —</option>
              {proofs.map((p) => <option key={p.doc_type} value={p.doc_type}>{p.label}</option>)}
            </select>
          </div>
          <div className="col-6 col-md-2">
            <input className="form-control form-control-sm" type="date" title="Expiry date (optional)"
              value={up.expiry_date} onChange={(e) => setUp({ ...up, expiry_date: e.target.value })} disabled={!!up.reuse_of} />
          </div>
          <div className="col-6 col-md-3">
            <select className="form-select form-select-sm" value={up.reuse_of} title="Reuse a file already received"
              onChange={(e) => setUp({ ...up, reuse_of: e.target.value, file: e.target.value ? null : up.file })}>
              <option value="">— new file —</option>
              {withFile.map((d) => <option key={d.id} value={d.id}>reuse: {d.file_name || d.doc_type}</option>)}
            </select>
          </div>
          <div className="col-8 col-md-2">
            {!up.reuse_of && (
              <input className="form-control form-control-sm" type="file"
                onChange={(e) => setUp({ ...up, file: e.target.files?.[0] || null })} />
            )}
          </div>
          <div className="col-4 col-md-1">
            <button className="btn btn-sm btn-co w-100" disabled={uploading || !up.doc_type || (!up.reuse_of && !up.file)}>
              {uploading ? "…" : "Add"}
            </button>
          </div>
        </form>
      )}
      {withFile.length === 0 && (
        <div className="empty">Nothing received yet.</div>
      )}

      <div className="co-rows">
      {withFile.map((d) => {
        const [chip, label] = STATE[stateOf(d)];
        return (
          <div key={d.id}>
            <div className="work-row">
              <span className={`dotsev ${chip}`} />
              <div className="grow">
                <div className="title">
                  <button type="button" className="kf-doc-link"
                    onClick={() => setPreview(d)}>
                    {d.file_name || d.doc_type}
                  </button>
                </div>
                <div className="meta">
                  {d.doc_type}{d.party_name ? ` · ${d.party_name}` : ""}
                  {fileSize(d.file_size) ? ` · ${fileSize(d.file_size)}` : ""}
                  {d.uploaded_at ? ` · ${new Date(d.uploaded_at).toLocaleDateString()}` : ""}
                  {expiryText(d)}
                </div>
                {/* What the customer said they were sending. */}
                {d.description && (
                  <div className="meta"><i className="fa-solid fa-quote-left" /> {d.description}</div>
                )}
                {d.rejection_reason && (
                  <div className="meta" style={{ color: "var(--sev-high)" }}>
                    Returned: {d.rejection_reason}
                  </div>
                )}
              </div>
              <span className={`chip ${chip}`}>{label}</span>
              {canReview && (
                <>
                  <button className="btn btn-sm btn-outline-secondary"
                    onClick={() => setPreview(d)}>Open</button>
                  {stateOf(d) !== "ACCEPTED" && (
                    <button className="btn btn-sm btn-co" disabled={busy}
                      onClick={() => act(d, { decision: "ACCEPT" })}>Accept</button>
                  )}
                  <button className="btn btn-sm btn-outline-danger" disabled={busy}
                    onClick={() => { setReturning(d); setReasonCode(""); setFreeText(""); }}>
                    Return
                  </button>
                </>
              )}
              {canUpload && (
                <button className="btn btn-sm btn-outline-secondary" title="Attach this same file to another requirement"
                  onClick={() => { setReusing(reusing?.id === d.id ? null : d); setReuseType(""); }}>
                  <i className="fa-solid fa-clone" />
                </button>
              )}
            </div>
            {reusing?.id === d.id && (
              <div className="dr-return d-flex gap-2 align-items-center">
                <span className="meta">Also use this file as:</span>
                <select className="form-select form-select-sm" style={{ maxWidth: 280 }} value={reuseType}
                  onChange={(e) => setReuseType(e.target.value)}>
                  <option value="">— document type —</option>
                  {proofs.filter((p) => p.doc_type !== d.doc_type).map((p) => <option key={p.doc_type} value={p.doc_type}>{p.label}</option>)}
                </select>
                <button className="btn btn-sm btn-co" disabled={busy || !reuseType} onClick={() => reuse(d)}>Attach</button>
              </div>
            )}

            {returning?.id === d.id && (
              <div className="dr-return">
                <div className="meta" style={{ marginBottom: ".4rem" }}>
                  The customer sees this wording. Describe the document — not
                  what your review found.
                </div>
                <select className="form-select form-select-sm" value={reasonCode}
                  onChange={(e) => setReasonCode(e.target.value)}>
                  <option value="">Choose a reason…</option>
                  {reasons.map((r) => (
                    <option key={r.code} value={r.code}>{r.message}</option>
                  ))}
                </select>
                <input className="form-control form-control-sm"
                  style={{ marginTop: ".4rem" }}
                  placeholder="…or write your own"
                  value={freeText} onChange={(e) => setFreeText(e.target.value)} />
                <div className="d-flex gap-2" style={{ marginTop: ".5rem" }}>
                  <button className="btn btn-sm btn-outline-secondary"
                    onClick={() => setReturning(null)}>Cancel</button>
                  <button className="btn btn-sm btn-danger"
                    disabled={busy || (!reasonCode && freeText.trim().length < 5)}
                    onClick={() => act(d, {
                      decision: "RETURN",
                      reason_code: freeText.trim() ? "" : reasonCode,
                      reason: freeText.trim(),
                    })}>
                    Send it back
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}
      </div>

      {preview && (
        <FilePreview url={preview.file_url} mediaType={preview.media_type}
          name={preview.file_name} onClose={() => setPreview(null)} />
      )}
    </div>
  );
};
