import { useLocation, Link } from "react-router-dom";
import ScrollToTop from "../components/ScrollToTop";
import { SiteFooter } from "../components/SiteFooter";
import { LEGAL_DOCS, LEGAL_INDEX, LEGAL_UPDATED } from "./legalDocs";

// Inline **bold** support for the legal text.
const rich = (text) =>
  String(text).split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**")
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : part);

const Block = ({ block }) => {
  if (typeof block === "string") return <p>{rich(block)}</p>;
  if (block.sub) return <h4 className="lg-sub">{block.sub}</h4>;
  if (block.note) return <div className="lg-note">{rich(block.note)}</div>;
  if (block.ul) return <ul className="lg-list">{block.ul.map((li, i) => <li key={i}>{rich(li)}</li>)}</ul>;
  if (block.ol) return <ol className="lg-list">{block.ol.map((li, i) => <li key={i}>{rich(li)}</li>)}</ol>;
  return null;
};

const slugify = (h) => h.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

const LegalShell = ({ children }) => (
  <ScrollToTop>
    <div className="lg-page">
      <header className="lg-topbar">
        <Link to="/" className="ld-brand" style={{ textDecoration: "none" }}>
          <span className="dot" /> Compliance OS
        </Link>
        <Link to="/" className="btn btn-sm btn-outline-light">
          <i className="fa-solid fa-arrow-left" /> Back to home
        </Link>
      </header>
      <main className="lg-main">{children}</main>
      <SiteFooter />
    </div>
  </ScrollToTop>
);

const Index = () => (
  <LegalShell>
    <h1 className="lg-title">Legal &amp; policies</h1>
    <p className="lg-summary">
      The documents that govern access to and use of Compliance OS, and how personal
      data is handled. Governing law: Grand Duchy of Luxembourg.
    </p>
    <DraftBanner />
    <div className="lg-index">
      {LEGAL_INDEX.map((d) => (
        <Link key={d.slug} to={`/legal/${d.slug}`} className="lg-index-card">
          <h3>{d.title}</h3>
          <p>{d.blurb}</p>
          <span className="lg-index-go">Read <i className="fa-solid fa-arrow-right" /></span>
        </Link>
      ))}
    </div>
  </LegalShell>
);

const DraftBanner = () => (
  <div className="lg-draft">
    <i className="fa-solid fa-triangle-exclamation" />
    <span>
      <strong>Template — not legal advice.</strong> These documents are provided for
      information and must be reviewed and adapted by qualified Luxembourg legal
      counsel, and completed with the operator’s details, before being relied upon.
    </span>
  </div>
);

const Document = ({ slug }) => {
  const doc = LEGAL_DOCS[slug];
  if (!doc) {
    return (
      <LegalShell>
        <h1 className="lg-title">Document not found</h1>
        <p className="lg-summary">This legal document does not exist. <Link to="/legal">See all documents</Link>.</p>
      </LegalShell>
    );
  }
  return (
    <LegalShell>
      <nav className="lg-breadcrumb">
        <Link to="/legal">Legal</Link> <span>/</span> {doc.title}
      </nav>
      <h1 className="lg-title">{doc.title}</h1>
      <div className="lg-meta">Last updated: {LEGAL_UPDATED} · Governing law: Luxembourg</div>
      {doc.summary && <p className="lg-summary">{doc.summary}</p>}
      <DraftBanner />

      {doc.sections.length > 1 && (
        <nav className="lg-toc" aria-label="Contents">
          <div className="lg-toc-title">On this page</div>
          <ol>
            {doc.sections.map((s) => (
              <li key={s.h}><a href={`#${slugify(s.h)}`}>{s.h}</a></li>
            ))}
          </ol>
        </nav>
      )}

      {doc.sections.map((s) => (
        <section key={s.h} id={slugify(s.h)} className="lg-section">
          <h2>{s.h}</h2>
          {s.blocks.map((b, i) => <Block key={i} block={b} />)}
        </section>
      ))}

      <div className="lg-other">
        <div className="lg-toc-title">Other documents</div>
        <div className="lg-other-links">
          {LEGAL_INDEX.filter((d) => d.slug !== slug).map((d) => (
            <Link key={d.slug} to={`/legal/${d.slug}`}>{d.title}</Link>
          ))}
        </div>
      </div>
    </LegalShell>
  );
};

// Rendered directly by Layout (before the auth gate) so legal pages are public.
export const Legal = () => {
  const { pathname } = useLocation();
  const slug = pathname.replace(/^\/legal\/?/, "").replace(/\/$/, "");
  return slug ? <Document slug={slug} /> : <Index />;
};
