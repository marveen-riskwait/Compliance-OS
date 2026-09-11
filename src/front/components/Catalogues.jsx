import { useEffect, useState } from "react";
import { api } from "../services/api";

// Reference lists (ISO countries, closed business-activity catalogue) come
// from the backend once per page load and are shared by every form. Codes are
// what gets stored; names are what people see.
let cache = null;
let inflight = null;
const EMPTY = { countries: [], activities: [] };

export const loadCatalogues = () => {
  if (cache) return Promise.resolve(cache);
  if (!inflight) {
    inflight = api.catalogues()
      .then((c) => { cache = c; return c; })
      .catch(() => { inflight = null; return EMPTY; });
  }
  return inflight;
};

export const useCatalogues = () => {
  const [cat, setCat] = useState(cache);
  useEffect(() => { if (!cat) loadCatalogues().then(setCat); }, []); // eslint-disable-line
  return cat || EMPTY;
};

export const countryLabel = (code, cat) => {
  if (!code) return "";
  const found = (cat || cache || EMPTY).countries.find((c) => c.code === code);
  return found ? found.name : code;
};

export const activityLabel = (code, cat) => {
  if (!code) return "";
  const found = (cat || cache || EMPTY).activities.find((a) => a.code === code);
  return found ? found.label : code;
};

// NACE Rev. 2 code -> catalogue code (longest matching prefix wins).
export const activityFromNace = (nace, cat) => {
  const digits = String(nace || "").replace(/[^0-9]/g, "");
  if (!digits) return null;
  let best = null, bestLen = 0;
  for (const a of (cat || cache || EMPTY).activities) {
    for (const p of a.nace || []) {
      const pd = p.replace(".", "");
      if (digits.startsWith(pd) && pd.length > bestLen) { best = a.code; bestLen = pd.length; }
    }
  }
  return best;
};

export const CountrySelect = ({ value, onChange, required, id, size, placeholder = "— select a country —", style }) => {
  const { countries } = useCatalogues();
  const v = value || "";
  const known = countries.some((c) => c.code === v);
  return (
    <select id={id} className={"form-select" + (size === "sm" ? " form-select-sm" : "")}
      value={v} required={required} style={style}
      onChange={(e) => onChange(e.target.value)}>
      <option value="">{placeholder}</option>
      {v && !known && <option value={v}>{v}</option>}
      {countries.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
    </select>
  );
};

export const ActivitySelect = ({ value, onChange, required, id, size, placeholder = "— select an activity —", style }) => {
  const { activities } = useCatalogues();
  const v = value || "";
  const known = activities.some((a) => a.code === v);
  return (
    <select id={id} className={"form-select" + (size === "sm" ? " form-select-sm" : "")}
      value={v} required={required} style={style}
      onChange={(e) => onChange(e.target.value)}>
      <option value="">{placeholder}</option>
      {v && !known && <option value={v}>{v}</option>}
      {activities.map((a) => (
        <option key={a.code} value={a.code}>
          {a.label}{a.high_risk ? " — high risk" : ""}
        </option>
      ))}
    </select>
  );
};
