from flask import jsonify, url_for

class APIException(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)

def generate_sitemap(app):
    """The API root: a clean, branded status page. The full route listing is
    only exposed in debug (a dev convenience), never in production."""
    routes_html = ""
    if app.debug:
        links = []
        for rule in app.url_map.iter_rules():
            if "GET" in rule.methods and has_no_empty_params(rule):
                url = url_for(rule.endpoint, **(rule.defaults or {}))
                if "/admin/" not in url:
                    links.append(url)
        items = "".join("<li><a href='%s'>%s</a></li>" % (u, u) for u in sorted(links))
        routes_html = ("<details style='margin-top:1.5rem;text-align:left'>"
                       "<summary style='cursor:pointer;color:#6366f1'>Routes (debug)</summary>"
                       "<ul>" + items + "</ul></details>")
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Compliance OS API</title><link rel="icon" type="image/svg+xml" href="/logo.svg">
        <style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
        font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:#111a2e;color:#e7ecf5}
        .card{text-align:center;max-width:520px;padding:2rem}
        .badge{display:inline-flex;align-items:center;gap:.5rem;background:rgba(99,102,241,.15);
        color:#a5b4fc;border:1px solid rgba(99,102,241,.35);border-radius:999px;padding:.35rem .8rem;
        font-size:.8rem;font-weight:600}.dot{width:8px;height:8px;border-radius:50%;background:#22c55e}
        h1{margin:1rem 0 .3rem;font-size:1.6rem}p{color:#9fb0cc;font-size:.9rem;line-height:1.5}
        a{color:#a5b4fc}</style></head><body><div class="card">
        <span class="badge"><span class="dot"></span> API online</span>
        <h1>Compliance OS API</h1>
        <p>AML/KYC/KYB compliance platform. This is the API service &mdash;
        the application is served separately.</p>""" + routes_html + "</div></body></html>"
