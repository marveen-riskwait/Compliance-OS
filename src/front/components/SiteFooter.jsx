import { Link } from "react-router-dom";
import { LEGAL_INDEX } from "../pages/legalDocs";

// The public site footer: brand, the professional-use notice, and the full set
// of legal pages. Used on the landing and on every legal page.
export const SiteFooter = () => (
  <footer className="site-foot">
    <div className="site-foot-top">
      <div className="site-foot-brand">
        <span className="ld-brand"><span className="dot" /> Compliance OS</span>
        <p className="muted">
          A modular AML / KYC / KYB compliance platform — onboarding, screening,
          risk, monitoring, case management and regulatory reporting.
        </p>
        <p className="site-foot-pro">
          <i className="fa-solid fa-triangle-exclamation" /> Demonstration project —
          not a live service. Do not enter real personal data.
        </p>
      </div>
      <nav className="site-foot-links" aria-label="Legal">
        <div className="site-foot-col-title">Legal</div>
        {LEGAL_INDEX.map((d) => (
          <Link key={d.slug} to={`/legal/${d.slug}`}>{d.title}</Link>
        ))}
      </nav>
      <nav className="site-foot-links" aria-label="Product">
        <div className="site-foot-col-title">Platform</div>
        <Link to="/">Home</Link>
        <Link to="/login">Sign in</Link>
        <Link to="/legal">All legal documents</Link>
      </nav>
    </div>
    <div className="site-foot-bottom">
      <span>© {new Date().getFullYear()} Marveen Riskwait — Demo compliance.OS. Demonstration project.</span>
      <span className="muted">Marveen Riskwait disclaims all liability. This is a demonstration version.</span>
    </div>
  </footer>
);
