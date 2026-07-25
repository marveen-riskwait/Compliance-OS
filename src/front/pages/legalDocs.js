// Legal content for Compliance OS. Governing law: Luxembourg. Language: English.
// Entity-specific facts are [PLACEHOLDERS] to be completed by the operator.
//
// IMPORTANT: these are information-only drafts, NOT legal advice. They must be
// reviewed and adapted by qualified Luxembourg legal counsel before being relied
// on. The Legal page renders a visible banner to that effect on every document.
//
// Block grammar consumed by Legal.jsx:
//   "text"                      -> paragraph (supports **bold**)
//   { sub: "heading" }          -> sub-heading
//   { ul: [ "item", ... ] }     -> bullet list
//   { ol: [ "item", ... ] }     -> numbered list
//   { note: "text" }            -> callout box

export const LEGAL_UPDATED = "25 July 2026";
const COMPANY = "[COMPANY LEGAL NAME]";

export const LEGAL_INDEX = [
  { slug: "notice", title: "Legal Notice", blurb: "Publisher, host and editorial responsibility." },
  { slug: "terms", title: "Terms of Service", blurb: "The rules governing access to and use of the platform." },
  { slug: "acceptable-use", title: "Acceptable Use Policy", blurb: "Professional, lawful and justifiable use only." },
  { slug: "privacy", title: "Privacy Policy", blurb: "How personal data is processed under the GDPR." },
  { slug: "dpa", title: "Data Processing Agreement", blurb: "Article 28 GDPR terms — you are the controller, we are the processor." },
  { slug: "cookies", title: "Cookie Policy", blurb: "The strictly necessary cookies we use." },
];

export const LEGAL_DOCS = {
  // ---------------------------------------------------------------- Legal Notice
  notice: {
    title: "Legal Notice",
    summary:
      "Identification of the publisher and host of this website and of the Compliance OS application, as required by the Luxembourg Law of 14 August 2000 on electronic commerce, as amended.",
    sections: [
      { h: "Publisher", blocks: [
        "This website and the Compliance OS application (the **“Platform”**) are published by:",
        { ul: [
          "**Company:** " + COMPANY + " ([LEGAL FORM, e.g. S.à r.l.])",
          "**Registered office:** [REGISTERED ADDRESS], Grand Duchy of Luxembourg",
          "**Trade & Companies Register (RCS Luxembourg):** [RCS NUMBER]",
          "**VAT identification number:** [LU VAT NUMBER]",
          "**Share capital:** [AMOUNT] EUR",
          "**Email:** [CONTACT EMAIL]",
          "**Telephone:** [PHONE]",
          "**Director of publication:** [NAME, TITLE]",
        ] },
      ] },
      { h: "Host", blocks: [
        "The Platform is hosted by:",
        { ul: [
          "**Host:** [HOSTING PROVIDER NAME]",
          "**Address:** [HOSTING PROVIDER ADDRESS]",
          "**Contact:** [HOSTING PROVIDER CONTACT / URL]",
        ] },
        "The operator remains responsible for the content it publishes on the Platform.",
      ] },
      { h: "Intellectual property", blocks: [
        "The Platform, its software, source code, structure, databases, design, graphics, the “Compliance OS” name and logo, and all related content are the property of " + COMPANY + " or are used under licence, and are protected by intellectual-property law.",
        "No reproduction, representation, adaptation, extraction or reuse, in whole or in part, of any element of the Platform is permitted without the prior written authorisation of the publisher, save for the rights expressly granted under the Terms of Service.",
      ] },
      { h: "Editorial responsibility and disclaimer", blocks: [
        "The Platform is a professional software tool intended to assist regulated entities and compliance professionals. The information, screening results, risk scores, regulatory mappings and AI-generated outputs it produces are provided for professional information and operational assistance only.",
        { note: "Nothing on the Platform constitutes legal, regulatory, tax or compliance advice, nor a substitute for the judgement of the user’s own qualified compliance function. The publisher gives no warranty that the information is complete, accurate or up to date. Use of the Platform does not guarantee compliance with any legal or regulatory obligation." },
        "The publisher’s liability in connection with the Platform is governed and limited by the Terms of Service.",
      ] },
      { h: "Governing law", blocks: [
        "This Legal Notice is governed by Luxembourg law. Any dispute relating to the Platform falls within the jurisdiction of the courts of the city of Luxembourg, subject to any mandatory rule to the contrary.",
      ] },
    ],
  },

  // ---------------------------------------------------------------- Terms of Service
  terms: {
    title: "Terms of Service",
    summary:
      "These Terms govern access to and use of the Compliance OS platform. By creating an organisation, accessing or using the Platform, the Customer accepts these Terms.",
    sections: [
      { h: "1. Definitions", blocks: [
        { ul: [
          "**Platform / Services** – the Compliance OS application and all related features, made available online.",
          "**Customer / Subscriber** – the legal entity that subscribes to or uses the Platform.",
          "**Authorised User** – a member of the Customer’s staff or an agent authorised by the Customer to access the Platform.",
          "**Data Subject** – an individual whose personal data is processed through the Platform (e.g. a customer, director or beneficial owner of the Customer).",
          "**Obliged Entity** – a person subject to anti-money-laundering and counter-terrorist-financing obligations under applicable law.",
          "**Business Purpose** – the Customer’s legitimate, lawful use of the Platform for onboarding, KYC/KYB, screening, risk assessment, monitoring, case management and regulatory reporting within its own compliance obligations.",
        ] },
      ] },
      { h: "2. Acceptance and professional use only", blocks: [
        "By accessing or using the Platform, the Customer accepts these Terms on its own behalf and on behalf of its Authorised Users, and warrants that the person accepting has authority to bind the Customer.",
        { note: "The Platform is intended **exclusively for professional (business) use**. The Customer warrants that it is acting solely for professional purposes and not as a consumer, and that it is an Obliged Entity, a regulated professional, or a person otherwise pursuing a legitimate compliance purpose. The Platform is **not** intended for private, personal or consumer use." },
      ] },
      { h: "3. Eligibility and lawful basis", blocks: [
        "The Customer warrants and undertakes that, at all times, it has and maintains a valid legal basis and all necessary authority to process personal data through the Platform — in particular the legal obligation to which it is subject under applicable anti-money-laundering law (including the Luxembourg Law of 12 November 2004, as amended, and the EU anti-money-laundering framework) or another lawful basis under the GDPR.",
        "The Customer is solely responsible for determining that its use of the Platform is lawful in its jurisdiction and for obtaining any authorisation, licence or registration required to carry out its activity.",
      ] },
      { h: "4. Licence and access", blocks: [
        "Subject to these Terms, the publisher grants the Customer a non-exclusive, non-transferable, non-sublicensable and revocable right to access and use the Platform for the Business Purpose, for the duration of the subscription.",
        "The Customer is responsible for the confidentiality of its credentials, for the acts and omissions of its Authorised Users, and for configuring roles and permissions appropriately within its organisation. The Customer must notify the publisher without undue delay of any unauthorised access.",
      ] },
      { h: "5. Acceptable use", blocks: [
        "The Customer and its Authorised Users must use the Platform lawfully, in good faith and in accordance with the Acceptable Use Policy, which forms part of these Terms. Without limitation, the Customer must not use the Platform without a valid legal basis, for any unlawful, discriminatory or abusive purpose, to conduct surveillance or profiling of individuals outside a legitimate compliance purpose, or in any way that infringes the rights of any person.",
      ] },
      { h: "6. The Customer’s responsibility for its own compliance and decisions", blocks: [
        "The Platform is a decision-support tool. It does not make regulatory determinations and does not replace the judgement of the Customer’s compliance function.",
        { ul: [
          "The Customer’s compliance officers, MLRO and authorised personnel remain **solely responsible** for all compliance decisions, including onboarding, risk classification, escalation, the filing of suspicious activity/transaction reports with the competent authorities, and record-keeping.",
          "The Customer assumes sole responsibility for any conclusions drawn from, and any action taken or not taken on the basis of, the Services.",
          "The Customer is responsible for reviewing screening alerts and potential matches, which may include false positives and false negatives, and for verifying results before acting on them.",
          "The Customer remains responsible for its relationship with, and its legal obligations towards, its own customers and Data Subjects.",
        ] },
      ] },
      { h: "7. Third-party and screening data", blocks: [
        "The Platform may surface data from public sources and third-party providers (for example sanctions, PEP and adverse-media data, company registries or IP-reputation services). Such data is provided **“as is”**. The publisher does not control it and gives no warranty that it is accurate, complete, current, or that any match or absence of match is correct. The Customer must exercise its own judgement and, where required, corroborate results from primary sources.",
      ] },
      { h: "8. Intellectual property and Customer data", blocks: [
        "All intellectual-property rights in the Platform belong to the publisher or its licensors. No rights are granted other than those expressly set out in these Terms.",
        "Data uploaded or generated by the Customer through the Platform (**“Customer Data”**) remains the Customer’s property. The Customer grants the publisher the right to host and process Customer Data solely to provide the Services, as further described in the Privacy Policy and the Data Processing Agreement.",
        "If the Customer provides feedback or suggestions, the publisher may use them without restriction or obligation.",
      ] },
      { h: "9. Data protection", blocks: [
        "In respect of personal data that the Customer processes about its own Data Subjects through the Platform, the Customer acts as **controller** and the publisher acts as **processor**, on the terms of the Data Processing Agreement. In respect of the Customer’s account and Authorised-User data, the publisher acts as controller, as described in the Privacy Policy.",
      ] },
      { h: "10. Warranties and disclaimers", blocks: [
        "The Platform is provided on an **“as is” and “as available”** basis. To the fullest extent permitted by law, the publisher excludes all implied warranties, including of merchantability, fitness for a particular purpose, accuracy, and non-infringement.",
        "The publisher does not warrant that the Platform will be uninterrupted, error-free or secure against every threat, or that its use will ensure the Customer’s compliance with any legal or regulatory obligation.",
      ] },
      { h: "11. Limitation of liability", blocks: [
        "To the fullest extent permitted by law, the publisher shall not be liable for any indirect, incidental, special or consequential loss, nor for any loss of profit, revenue, data, goodwill, or for regulatory sanctions or fines incurred by the Customer.",
        "To the fullest extent permitted by law, the publisher’s total aggregate liability arising out of or in connection with the Platform shall not exceed the total fees paid by the Customer for the Services during the twelve (12) months preceding the event giving rise to the claim (or [CAP AMOUNT] EUR where no fees have been paid).",
        { note: "Nothing in these Terms excludes or limits liability that cannot lawfully be excluded or limited, including liability for fraud, wilful misconduct, gross negligence, or death or personal injury caused by negligence." },
      ] },
      { h: "12. Indemnification", blocks: [
        "The Customer shall indemnify, defend and hold harmless the publisher and its officers, employees and subcontractors from and against any claim, liability, loss, damage, cost or expense (including reasonable legal fees) arising out of or in connection with: (i) the Customer’s or its Authorised Users’ use of the Platform; (ii) any breach of these Terms or of the Acceptable Use Policy; (iii) any unlawful processing of personal data or infringement of the rights of a Data Subject or third party; or (iv) the absence of a valid legal basis for the Customer’s processing.",
      ] },
      { h: "13. Suspension and termination", blocks: [
        "The publisher may suspend or terminate access immediately in the event of a material breach, unlawful use, a risk to the security or integrity of the Platform, or non-payment. Either party may terminate the subscription in accordance with the applicable order or on reasonable notice.",
        "On termination, the Customer’s right to use the Platform ceases, and Customer Data is returned or deleted in accordance with the Data Processing Agreement, subject to any retention required by law.",
      ] },
      { h: "14. Changes to the Services and to these Terms", blocks: [
        "The publisher may evolve the Platform and may update these Terms to reflect legal, technical or commercial changes. Material changes will be notified through the Platform or by email. Continued use after the effective date constitutes acceptance.",
      ] },
      { h: "15. Confidentiality and force majeure", blocks: [
        "Each party shall keep confidential the non-public information of the other party disclosed in connection with the Services. Neither party is liable for a failure caused by an event beyond its reasonable control.",
      ] },
      { h: "16. Governing law and jurisdiction", blocks: [
        "These Terms are governed by the laws of the Grand Duchy of Luxembourg. Any dispute shall be submitted to the exclusive jurisdiction of the District Court of Luxembourg (Tribunal d’arrondissement de Luxembourg), without prejudice to any mandatory rule of law.",
        "If any provision is held invalid, the remainder continues in force. These Terms, together with the Acceptable Use Policy, Privacy Policy and Data Processing Agreement, constitute the entire agreement relating to the Platform.",
      ] },
    ],
  },

  // ---------------------------------------------------------------- Acceptable Use
  "acceptable-use": {
    title: "Acceptable Use Policy",
    summary:
      "The Platform may be used only for professional, lawful and justifiable compliance purposes. This Policy defines what is permitted and what is prohibited, and forms part of the Terms of Service.",
    sections: [
      { h: "1. Professional and justifiable use only", blocks: [
        "Access to and use of the Platform is reserved for professionals acting within a legitimate compliance purpose. The Platform must be used only:",
        { ul: [
          "by an Obliged Entity, a regulated professional, or a person otherwise subject to or supporting anti-money-laundering, counter-terrorist-financing, KYC/KYB, sanctions or compliance obligations;",
          "for a legitimate, specified and lawful business purpose connected to those obligations; and",
          "where the user has a valid legal basis under the GDPR (in particular a legal obligation) to process the personal data concerned.",
        ] },
        { note: "The Platform is not a tool for general-purpose investigation of individuals. Each Data Subject processed must have a genuine nexus to the user’s own compliance activity." },
      ] },
      { h: "2. Prohibited uses", blocks: [
        "The Customer and its Authorised Users must not:",
        { ul: [
          "use the Platform without a valid legal basis or lawful purpose, or to process personal data of individuals having no legitimate connection to a compliance purpose;",
          "use the Platform for private, personal, consumer, political, journalistic, or general surveillance purposes;",
          "use outputs of the Platform to unlawfully discriminate against any person on grounds protected by law;",
          "take a decision producing legal or similarly significant effects on a person based **solely** on automated processing, without meaningful human review (Article 22 GDPR);",
          "use the Platform for any unlawful, fraudulent, defamatory, harassing or abusive purpose, or to infringe the rights of any person;",
          "misrepresent identity or authority, or upload data the user is not lawfully entitled to process;",
          "attempt to reverse-engineer, copy, scrape, overload, disrupt or circumvent the security of the Platform, or access it other than through the interfaces provided;",
          "resell, sublicense or make the Platform available to any third party without prior written authorisation.",
        ] },
      ] },
      { h: "3. User warranties", blocks: [
        "By using the Platform, the Customer and each Authorised User warrant that they: (i) act in a professional capacity within a legitimate compliance purpose; (ii) have a valid legal basis and authority for the processing carried out; (iii) provide accurate information; (iv) apply meaningful human oversight to any decision affecting a person; and (v) comply with all applicable data-protection and anti-money-laundering law.",
      ] },
      { h: "4. Enforcement and reporting", blocks: [
        "Breach of this Policy may result in immediate suspension or termination and gives rise to the indemnity in the Terms of Service. Suspected misuse can be reported to [ABUSE / COMPLIANCE CONTACT EMAIL].",
      ] },
    ],
  },

  // ---------------------------------------------------------------- Privacy Policy
  privacy: {
    title: "Privacy Policy",
    summary:
      "How " + COMPANY + " processes personal data in connection with the Compliance OS platform, in accordance with the EU General Data Protection Regulation (GDPR) and Luxembourg data-protection law.",
    sections: [
      { h: "1. Who is responsible, and in what capacity", blocks: [
        "The Platform involves two distinct roles:",
        { ul: [
          "**Account and user data** — for personal data relating to the Customer’s organisation and its Authorised Users (names, professional emails, roles, security logs), " + COMPANY + " acts as **controller**. This Policy governs that processing.",
          "**Customer’s compliance data** — for personal data that the Customer processes about its own customers, directors and beneficial owners through the Platform, the **Customer is the controller** and " + COMPANY + " acts as **processor** on the Customer’s instructions, under the Data Processing Agreement. That processing is governed by the Customer’s own privacy notice.",
        ] },
      ] },
      { h: "2. Data we process as controller", blocks: [
        { ul: [
          "**Identification & account data:** name, professional email, organisation, role and permissions.",
          "**Authentication & security data:** hashed passwords, two-factor data, session and sign-in metadata, source IP and IP-reputation signals used to secure access.",
          "**Usage & log data:** audit and activity logs, technical logs necessary to operate and secure the Platform.",
          "**Support & communications data:** information you provide when you contact us.",
        ] },
      ] },
      { h: "3. Purposes and legal bases", blocks: [
        { ul: [
          "**To provide the Platform** (create and manage accounts, deliver the Services) — performance of a contract (Art. 6(1)(b) GDPR).",
          "**To secure the Platform** (authentication, fraud/abuse prevention, IP-reputation checks, audit logging) — legitimate interests (Art. 6(1)(f)) and, where applicable, legal obligation (Art. 6(1)(c)).",
          "**To comply with our own legal obligations** (accounting, responding to lawful requests) — legal obligation (Art. 6(1)(c)).",
          "**To improve and support the Platform** — legitimate interests, balanced against your rights.",
        ] },
        { note: "In the AML/KYC context, the legal basis for the Customer’s processing of its own Data Subjects’ personal data is the Customer’s **legal obligation** under anti-money-laundering law (Art. 6(1)(c) GDPR), not consent. As processor, we act only on the Customer’s documented instructions." },
      ] },
      { h: "4. Recipients and sub-processors", blocks: [
        "We share personal data only with: our authorised staff on a need-to-know basis; sub-processors that host and support the Platform, under contractual data-protection safeguards (see the Data Processing Agreement); and public authorities where required by law. We do not sell personal data.",
      ] },
      { h: "5. International transfers", blocks: [
        "Where personal data is transferred outside the European Economic Area, we rely on an adequacy decision or on appropriate safeguards such as the European Commission’s Standard Contractual Clauses, together with supplementary measures where required.",
      ] },
      { h: "6. Retention", blocks: [
        { ul: [
          "**Account and user data:** kept for the duration of the relationship and then deleted or anonymised, subject to legal retention periods (e.g. accounting).",
          "**Security and audit logs:** kept for a period proportionate to their security and accountability purpose.",
          "**AML/KYC records** processed by the Customer as controller are retained under the Customer’s instructions and applicable law — in Luxembourg, five (5) years after the end of the business relationship or the occasional transaction (Art. 3(6) of the Law of 12 November 2004 and Art. 25 of CSSF Regulation N° 12-02).",
        ] },
      ] },
      { h: "7. Your rights", blocks: [
        "Subject to the conditions set by law, you have the right to access, rectify, erase, restrict and object to the processing of your personal data, and to data portability. To exercise these rights, contact [DPO / PRIVACY CONTACT EMAIL].",
        { note: "Where personal data must be retained under anti-money-laundering law, the right to erasure may be restricted for the duration of the legal retention period. Requests concerning data processed by the Customer as controller should be addressed to that Customer." },
        "You also have the right to lodge a complaint with the Luxembourg supervisory authority, the **Commission nationale pour la protection des données (CNPD)**, or with the authority of your habitual residence.",
      ] },
      { h: "8. Security and cookies", blocks: [
        "We implement appropriate technical and organisational measures to protect personal data, including encryption in transit, access controls, role-based permissions, audit logging and two-factor authentication. See the Cookie Policy for the cookies we use.",
      ] },
      { h: "9. Contact and changes", blocks: [
        "For any privacy question, contact [DPO / PRIVACY CONTACT EMAIL] or write to " + COMPANY + ", [REGISTERED ADDRESS]. We may update this Policy; the current version is always available here with its date.",
      ] },
    ],
  },

  // ---------------------------------------------------------------- DPA
  dpa: {
    title: "Data Processing Agreement",
    summary:
      "This Data Processing Agreement (“DPA”) forms part of the Terms of Service and applies where " + COMPANY + " processes personal data on behalf of the Customer, in accordance with Article 28 of the GDPR. The Customer is the controller; " + COMPANY + " is the processor.",
    sections: [
      { h: "1. Roles and scope", blocks: [
        "The Customer (controller) determines the purposes and means of processing personal data about its own Data Subjects through the Platform. " + COMPANY + " (processor) processes that personal data only to provide the Services and only on the Customer’s documented instructions, including as set out in the Terms and this DPA.",
      ] },
      { h: "2. Subject-matter, duration, nature and purpose", blocks: [
        { ul: [
          "**Subject-matter:** provision of the Compliance OS platform for KYC/KYB, screening, risk assessment, monitoring, case management and regulatory reporting.",
          "**Duration:** for the term of the subscription and until deletion or return of the data.",
          "**Nature and purpose:** hosting, storage, structuring, screening against reference data, and related processing operations necessary to deliver the Services.",
        ] },
      ] },
      { h: "3. Categories of Data Subjects and personal data", blocks: [
        { ul: [
          "**Data Subjects:** the Customer’s prospects and customers, their directors, representatives and beneficial owners, and related persons screened for compliance purposes.",
          "**Personal data:** identification and contact data, corporate and ownership data, documents, screening and risk data, transaction data, and case information.",
          "**Special categories / criminal-offence data:** to the extent that sanctions, PEP or adverse-media results reveal such data, it is processed only as necessary for the Customer’s AML/CFT legal obligation and subject to appropriate safeguards.",
        ] },
      ] },
      { h: "4. Obligations of the processor", blocks: [
        { ul: [
          "process personal data only on the Customer’s documented instructions, including as to international transfers, unless required otherwise by law (in which case it will inform the Customer, unless prohibited);",
          "ensure that persons authorised to process the data are bound by confidentiality;",
          "implement appropriate technical and organisational security measures under Article 32 GDPR;",
          "engage sub-processors only with the Customer’s general authorisation, inform the Customer of intended changes, and impose equivalent data-protection obligations on them;",
          "assist the Customer, taking into account the nature of the processing, in responding to Data-Subject requests and in ensuring compliance with Articles 32–36 GDPR (security, breach notification, impact assessments and prior consultation);",
          "notify the Customer without undue delay after becoming aware of a personal-data breach;",
          "at the Customer’s choice, delete or return all personal data at the end of the Services and delete existing copies, unless retention is required by law;",
          "make available the information necessary to demonstrate compliance and allow for and contribute to audits, subject to reasonable confidentiality and security conditions.",
        ] },
      ] },
      { h: "5. Sub-processors", blocks: [
        "The Customer authorises the use of sub-processors for hosting and operating the Platform, including [HOSTING PROVIDER] and [OTHER SUB-PROCESSORS]. An up-to-date list is available on request. " + COMPANY + " remains liable for its sub-processors’ compliance with these obligations.",
      ] },
      { h: "6. International transfers and liability", blocks: [
        "Any transfer of personal data outside the EEA is made under an adequacy decision or appropriate safeguards (e.g. Standard Contractual Clauses). The liability provisions of the Terms of Service apply to this DPA. In case of conflict on data-protection matters, this DPA prevails.",
      ] },
    ],
  },

  // ---------------------------------------------------------------- Cookies
  cookies: {
    title: "Cookie Policy",
    summary:
      "How Compliance OS uses cookies and similar technologies.",
    sections: [
      { h: "1. Our approach", blocks: [
        "The Platform uses only **strictly necessary** cookies required to operate the service and keep it secure. We do not use advertising or third-party tracking cookies, and we do not build marketing profiles.",
      ] },
      { h: "2. Cookies we use", blocks: [
        { ul: [
          "**Session / authentication cookies** — secure, http-only cookies that keep you signed in and protect the session (including against cross-site request forgery). Duration: the session or a short period defined for security.",
          "**Preference cookies** — remember interface choices such as the collapsed navigation. Duration: persistent, until cleared.",
        ] },
      ] },
      { h: "3. Legal basis and management", blocks: [
        "Strictly necessary cookies do not require consent under the ePrivacy rules and Luxembourg law, because they are essential to provide a service you have requested. You can block or delete cookies through your browser settings; disabling strictly necessary cookies will prevent you from signing in and using the Platform.",
      ] },
      { h: "4. Changes", blocks: [
        "If we introduce any non-essential cookie in the future, we will update this Policy and request your consent beforehand where required.",
      ] },
    ],
  },
};
