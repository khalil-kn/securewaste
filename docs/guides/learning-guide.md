# SecureWaste learning guide

**Every concept used in the Milestone 0 package, explained from zero.**

You do not need any prior knowledge to read this guide. Each section starts with the idea in plain words, then shows where it appears in SecureWaste, and ends with **Check yourself** questions (answers are folded underneath — try first, then open them).

| Section | You will understand |
|---|---|
| [1. Requirements](#1-requirements-engineering) | Why we write down *what* to build before *how*, and how to read `docs/01-requirements.md` |
| [2. How the stack works](#2-how-the-stack-works) | What happens between clicking "Scan" and seeing findings |
| [3. Reading UML diagrams](#3-reading-uml-diagrams) | Every diagram type in `docs/diagrams/` |
| [4. Data modelling](#4-data-modelling) | Tables, keys, relationships and why we never store raw values |
| [5. Security and threat modelling](#5-security-and-threat-modelling) | Assets, trust boundaries, STRIDE, residual risk |
| [6. Architecture Decision Records](#6-architecture-decision-records-adrs) | How and why we record decisions |
| [7. The risk score, step by step](#7-the-risk-score-step-by-step) | How a document gets "critical" |
| [8. Glossary](#8-glossary) | Short definitions to come back to |

---

## 1. Requirements engineering

### 1.1 The idea

Software projects rarely fail because people cannot code. They fail because people build the wrong thing, or each team member builds a different idea of it. **Requirements** are the written agreement on *what* the product must do, *for whom*, and *how we will know it works* — before anyone argues about *how* to code it.

### 1.2 The building blocks (in the order they appear in `01-requirements.md`)

| Block | Question it answers | SecureWaste example |
|---|---|---|
| **Problem statement** | What pain exists today? | Employees share documents containing card numbers or API keys by accident. |
| **Goals** | What must be true when we succeed? | G-3: the tool never becomes a leak itself. |
| **Non-goals** | What are we deliberately *not* doing? | No OCR, no user accounts in the MVP. Non-goals protect the schedule. |
| **Personas** | Who exactly uses it? | Sana (IT admin), Youssef (analyst), Leila (compliance). Fictional but realistic. |
| **User stories** | What does a persona want and why? | US-13: *As Youssef, I want to mark a finding as false positive so that the record reflects human judgement.* |
| **MoSCoW priority** | How important is it? | **M**ust, **S**hould, **C**ould, **W**on't (this time). |
| **Functional requirement (FR)** | What must the system *do*? Testable. | FR-02: reject files above 10 MB with HTTP 413. |
| **Non-functional requirement (NFR)** | How *well* must it do it? Quality attributes. | NFR-06: scan a 10-page PDF in under 3 s. |
| **Acceptance criteria** | How do we prove it is done? | "Redacting the card produces a file in which text extraction finds no card number." |

### 1.3 Why IDs matter: traceability

Every item has an ID (US-01, FR-02, NFR-06, T-04, ST-08). The same ID appears in GitHub issues, pull requests, test names and the threat model. If someone asks *"why does this code exist?"* you can follow the ID back to a user need. If a requirement changes, you can find every place affected.

### 1.4 A good requirement is…

- **Testable** — "fast" is not testable; "under 3 seconds for a 10-page PDF" is.
- **Unambiguous** — one interpretation only.
- **Necessary** — traced to a user story or a goal.
- **Feasible** — doable by a five-student team in the time available (that is the scope rule: stretch ideas go to *Future direction*).

### Check yourself

1. Is "the dashboard should look professional" a good requirement? How would you rewrite it?
2. What is the difference between FR-03 and NFR-03?
3. Why does the requirements document list *non-goals*?
4. Write a user story for Leila about downloading a report.

<details><summary>Answers</summary>

1. No — not testable. Better: "The dashboard meets WCAG 2.1 AA contrast, works from 390 px wide, and shows severity with an icon and text, not only colour" (that is NFR-10).
2. FR-03 says *what* the system does (detect the real file type from content). NFR-03 says a *quality* constraint (security headers on every response).
3. To prevent scope creep: everyone knows what will *not* be built, so effort goes to the MVP.
4. *As Leila, I want to download a printable report of a scan so that I can attach evidence of review to a compliance file.* (US-19)
</details>

---

## 2. How the stack works

### 2.1 The big picture

When Sana clicks **Scan**, this happens (see the [upload sequence diagram](../diagrams/svg/seq-upload-scan.svg)):

```
Browser ──HTTP POST /documents──▶ Flask route ──▶ ScanService ──▶ core modules ──▶ SQLite + files
Browser ◀──303 redirect + HTML page────────────────────────────────────────────────┘
```

### 2.2 HTTP in five minutes

The browser and the server talk with **HTTP**: the browser sends a **request** (a *method* such as `GET` to read or `POST` to change something, a *path* like `/documents/42`, *headers*, and sometimes a *body*), and the server returns a **response** (a *status code*, headers, a body).

| Status | Meaning | SecureWaste example |
|---|---|---|
| 200 | OK | Details page shown |
| 303 | See Other — go to this other URL | After upload, go to `/documents/{id}` |
| 400 | Bad request | Missing CSRF token |
| 404 | Not found | Unknown document ID |
| 409 | Conflict | Invalid review transition |
| 413 | Payload too large | File above 10 MB |
| 415 | Unsupported media type | A renamed `.exe` |
| 422 | Unprocessable | Encrypted PDF |

**Post/Redirect/Get:** after a successful `POST`, the server answers `303` and the browser does a `GET`. Refreshing the page then repeats the harmless `GET`, not the upload.

### 2.3 Python, virtual environments and pip

- **Python** runs our code. **pip** installs libraries from PyPI.
- A **virtual environment** (`.venv/`) is a private folder of libraries for one project, so SecureWaste's Flask version never clashes with another project's. You *activate* it in each new terminal: `source .venv/Scripts/activate` in Git Bash on Windows.
- `requirements.txt` lists exact versions ("pinned"), so all five teammates and CI install the same thing.

### 2.4 Flask

Flask maps URLs to Python functions:

```python
@bp.get("/documents/<document_id>")
def document_detail(document_id: str):
    doc = documents_repo.get(document_id)  # db layer
    if doc is None:
        abort(404)
    return render_template("document-detail.html", doc=doc)
```

- A **route** is the URL pattern + function.
- **Jinja2 templates** are HTML with placeholders `{{ doc.display_name }}`. Jinja2 **auto-escapes**: if a filename contains `<script>`, it is shown as text, not run. That is a key XSS defence.
- An **application factory** (`create_app()`) builds the app with its configuration, so tests can create a fresh app with a temporary database.
- **Thin routes:** routes only translate HTTP ↔ Python. The logic lives in `services/` and `core/` (NFR-08), so it can be tested without a browser.

### 2.5 CSRF and why forms carry a hidden token

**Cross-Site Request Forgery**: you are using SecureWaste in one tab; a malicious page in another tab contains a hidden form that POSTs to `http://127.0.0.1:5000/documents/42/delete`. Your browser would happily send it. Defence: every form includes a secret random **CSRF token** that the evil page cannot read; the server rejects requests without the right token. Flask-WTF does this for us.

### 2.6 PyMuPDF: reading and redacting PDFs

A PDF is not a text file: it is a set of drawing instructions ("draw these glyphs at these coordinates"). PyMuPDF (`import pymupdf`) can:

- open and validate a PDF, count pages, detect encryption;
- extract the text of each page (`page.get_text()`);
- find where a string is drawn (`page.search_for("…")` returns rectangles);
- **redact**: `page.add_redact_annot(rect)` marks an area, then `page.apply_redactions()` *deletes* the text and image content under it. Drawing a black rectangle would only *hide* it — copy/paste would still reveal it.

### 2.7 Regular expressions and validators

A **regular expression** (regex) is a pattern for text. `[\w.+-]+@[\w-]+\.[\w.]+` roughly matches e-mail addresses. Regexes find *candidates*; they cannot tell if a number is a real card. That is why we add **validators**.

**Luhn checksum** (cards). Starting from the rightmost digit, double every second digit; if doubling gives more than 9, subtract 9; add everything; valid if the total is divisible by 10. Test card `4242 4242 4242 4242`: the doubled 4s become 8, so each pair contributes 8 + 2 = 10; eight pairs → 80 → divisible by 10 → **valid**. Change one digit and it fails. A random 16-digit number passes only 1 time in 10, so Luhn removes ~90 % of false card matches.

**IBAN mod-97.** Move the first four characters (country + check digits) to the end, replace letters with numbers (A = 10 … Z = 35), and compute the remainder when dividing by 97; a valid IBAN gives **1**. The standard documentation example `GB82 WEST 1234 5698 7654 32` passes.

**Context words.** An 8-digit number is everywhere (dates, invoice numbers). A Tunisian CIN rule only reports it when a word such as "CIN" or "carte d'identité" is close by. That trades a few missed IDs for far fewer false alarms.

**ReDoS.** Badly written regexes (nested `(a+)+`) can take exponential time on crafted text. We keep quantifiers bounded and test with adversarial strings (threat T-18).

### 2.8 SQLite and SQL

**SQLite** is a whole relational database in one file (`instance/securewaste.db`), accessed with Python's built-in `sqlite3`. **SQL** is the language: `CREATE TABLE`, `INSERT`, `SELECT … WHERE …`, `UPDATE`, `DELETE`.

Always use **parameters**, never string formatting:

```python
conn.execute("SELECT * FROM findings WHERE scan_id = ?", (scan_id,))  # safe
conn.execute(f"SELECT * FROM findings WHERE scan_id = '{scan_id}'")  # SQL injection!
```

### 2.9 pytest and CI

**pytest** runs functions named `test_*` and reports failures. A unit test checks one small piece (e.g. `luhn_valid("4242424242424242") is True`). **Continuous Integration (CI)** — GitHub Actions — runs all tests automatically on every pull request, so broken code cannot be merged quietly. `pip-audit` checks dependencies for known vulnerabilities.

### Check yourself

1. Why does the upload answer `303` instead of `200` with the page?
2. A filename is `<img src=x onerror=alert(1)>.pdf`. Which mechanism stops it from running in the browser?
3. Is `4242 4242 4242 4241` Luhn-valid? Why?
4. Why can't SecureWaste simply draw black boxes over sensitive text?
5. What is wrong with `f"... WHERE id = '{doc_id}'"`?

<details><summary>Answers</summary>

1. Post/Redirect/Get: refreshing the result page must not re-upload the file.
2. Jinja2 auto-escaping (plus the Content-Security-Policy as a second layer).
3. No. The last digit changed from 2 to 1, so the total is 79, not divisible by 10.
4. The text stays in the PDF and can be copied or extracted; only `apply_redactions()` removes it.
5. SQL injection: a crafted ID can change the query. Use `?` parameters.
</details>

---

## 3. Reading UML diagrams

**UML** (Unified Modeling Language) is a set of standard drawing conventions so that any developer can read any team's diagrams. Each diagram type answers one question. All SecureWaste diagrams are in [`docs/diagrams/`](../diagrams/README.md).

| Diagram | Question it answers | Static or dynamic |
|---|---|---|
| Use case | *Who* uses the system for *what*? | — |
| Class | What *types* of objects exist and how are they related? | Static |
| Data model (ER) | What *tables* store the data? | Static |
| State machine | What *states* can one object be in? | Dynamic (per object) |
| Sequence | Who calls whom, *in what order*, for one scenario? | Dynamic |
| Activity | What is the *workflow*, and who does each step? | Dynamic |
| Component | What *parts* is the software made of? | Static |
| Deployment | *Where* does each part run? | Static |
| Data-flow / trust boundaries | Where does data *cross* between trust zones? | Security view |

### 3.1 Use case diagram — [view](../diagrams/svg/use-case.svg)

| Symbol | Meaning |
|---|---|
| Stick figure | **Actor** — a role outside the system (a person or another system) |
| Ellipse | **Use case** — a goal the actor achieves |
| Rectangle | **System boundary** |
| Plain line | The actor takes part in the use case |
| Dashed arrow «include» | The base use case *always* performs the included one (Upload → Scan) |
| Dashed arrow «extend» | Optional extra behaviour in some conditions |

Tip: a use case is a **goal** ("Redact PDF"), not a button click.

### 3.2 Class diagram — [view](../diagrams/svg/class-domain.svg)

A box has three compartments: **name**, **attributes** (`confidence : float`), **operations** (`+ assess(findings) : RiskAssessment`). `+` means public. *Italic* name = abstract class (cannot be created directly).

| Line | Meaning | Example |
|---|---|---|
| Hollow triangle ▷ | **Inheritance** ("is a") | `PaymentCardRule` is a `RegexRule` |
| Filled diamond ◆ | **Composition** — the part dies with the whole | Deleting a `Document` deletes its `ScanJob`s |
| Hollow diamond ◇ | **Aggregation** — has, but parts live independently | `DetectionEngine` uses a set of rules |
| Plain arrow | **Association** — knows about | `Redaction` redacts `Finding`s |
| Dashed arrow | **Dependency** — uses or creates | `RiskEngine` «creates» `RiskAssessment` |

**Multiplicity**: `1` exactly one, `0..1` optional, `0..*` zero or many, `1..*` at least one.

### 3.3 Data model (entity–relationship) — [view](../diagrams/svg/data-model.svg)

Each box is a **table**; each row inside is a **column** with its type. `PK` = primary key, `FK` = foreign key. The ends of lines use **crow's-foot notation**:

| End symbol | Reads as |
|---|---|
| `||` two bars | exactly one |
| `o|` circle + bar | zero or one |
| `|<` bar + crow's foot | one or many |
| `o<` circle + crow's foot | zero or many |

Read `documents ||──o< scans` as "one document has zero or many scans; each scan belongs to exactly one document".

### 3.4 State machine — [view](../diagrams/svg/state-machines.svg)

| Symbol | Meaning |
|---|---|
| Filled dot | Initial state |
| Rounded box | State |
| Arrow `event [guard] / action` | Transition: when *event* happens and *guard* is true, do *action* and move |
| Ringed dot | Final state |

The finding machine encodes business rules: a *resolved* finding can only be reopened. Code enforces exactly these arrows (FR-22) and tests try the forbidden ones.

### 3.5 Sequence diagram — [view](../diagrams/svg/seq-upload-scan.svg)

| Symbol | Meaning |
|---|---|
| Box on top + dashed vertical line | **Participant** and its **lifeline** (time goes down) |
| Solid arrow, filled head | Call / message |
| Dashed arrow, open head | Return |
| Arrow back to the same lifeline | Internal step (self-call) |
| Thin rectangle on a lifeline | Activation — the participant is busy |
| `alt` frame | If / else — sections separated by a dashed line, each with a `[guard]` |
| `loop` frame | Repeat while the guard holds |

Read it top to bottom, following the numbers.

### 3.6 Activity diagram with swimlanes — [view](../diagrams/svg/activity-scan-review-redact.svg)

Like a flowchart with responsibilities. Each vertical **swimlane** is an actor or layer. Rounded boxes are **actions**, diamonds are **decisions** (exits labelled `[yes]`/`[no]`) or **merges** (several arrows joining), the filled dot starts, the ringed dot ends. Moving between lanes = handing work to someone else.

### 3.7 Component diagram — [view](../diagrams/svg/component.svg)

Boxes with the small "plug" icon are **components** (replaceable parts with a clear job). Folder shapes are **packages** (Python packages here). An arrow A → B means *A depends on B*. Look for the direction: arrows only go web → services → core/db, never backwards — that is the layered architecture.

### 3.8 Deployment diagram — [view](../diagrams/svg/deployment.svg)

3-D boxes are **nodes** (a laptop, a container, a CI runner). Dog-eared boxes are **artifacts** (files that are deployed: the Python package, the database file). Lines are communication paths labelled with protocols (`HTTP 127.0.0.1:5000`, `git push (HTTPS)`).

### 3.9 Data-flow diagram with trust boundaries — [view](../diagrams/svg/trust-boundaries.svg)

Not strictly UML, but standard in security. Dashed red zones are **trust boundaries**; numbered arrows (DF1…DF7) are **data flows**. Every arrow that crosses a boundary is a place where we must validate, authenticate or sanitise.

### Check yourself

1. In the class diagram, why is Document → ScanJob a filled diamond and not a plain line?
2. In the data model, what does `findings ||──o< redaction_items` mean in words?
3. In the upload sequence, which frame shows what happens to a rejected file?
4. In the review state machine, can a *false_positive* go directly to *resolved*?
5. Which diagram would you open to explain to a teacher where the database file lives?

<details><summary>Answers</summary>

1. Composition: scan jobs cannot exist without their document, and deleting the document deletes them (ON DELETE CASCADE).
2. One finding can be targeted by zero or many redaction items; each redaction item refers to exactly one finding.
3. The `alt` frame, first section `[file rejected]`.
4. No — there is no arrow. It must be reopened (or confirmed) first.
5. The deployment diagram.
</details>

---

## 4. Data modelling

### 4.1 From nouns to tables

Read the requirements and underline the **nouns** that must be remembered: document, scan, finding, review, redaction, audit event. Each becomes an **entity** → a **table**. Their properties become **columns**.

### 4.2 Keys

- **Primary key (PK)** — the unique identity of a row (`documents.id`). We use **UUIDs** (random 128-bit IDs) rather than 1, 2, 3 so IDs in URLs are not guessable or countable.
- **Foreign key (FK)** — a column that points to another table's PK (`scans.document_id → documents.id`). SQLite only enforces FKs when you run `PRAGMA foreign_keys = ON` on each connection — easy to forget, so `db/connection.py` does it once.
- **Composite key** — `redaction_items` is identified by (`redaction_id`, `finding_id`) together.

### 4.3 Relationships and cardinality

- **One-to-many**: one document → many scans (FK on the "many" side).
- **Many-to-many**: redactions ↔ findings, stored through the **junction table** `redaction_items`, which also records the outcome for each finding.

### 4.4 Constraints protect data quality

- `NOT NULL` — the column must have a value.
- `UNIQUE` — no duplicates (`stored_name`).
- `CHECK` — allowed values (`review_status IN ('open','confirmed','false_positive','resolved')`).
- `ON DELETE CASCADE` — deleting a document deletes its scans, then their findings.
- `ON DELETE SET NULL` — deleting a document keeps its audit events but blanks the link.

### 4.5 Normalisation (just enough)

Store each fact **once**. The risk level lives on the scan, not copied onto every finding; the document name lives in `documents`, not in every finding. Duplicated facts drift apart.

### 4.6 Indexes

An **index** is a sorted lookup structure that makes `WHERE category = ?` fast without reading every row. We index the columns used by filters and joins. Indexes cost a little space and slow inserts slightly — a classic trade-off.

### 4.7 Privacy by design: what we deliberately do *not* store

A DLP tool's database must not become a second copy of the secrets. For each finding we store:

- a **masked value**: `•••• •••• •••• 4242`;
- a **keyed hash**: `HMAC-SHA256(secret_key, rule_id + value)`.

**Hash vs HMAC vs encryption:**

| Technique | Reversible? | Weakness | Used for |
|---|---|---|---|
| Encryption | Yes, with the key | Key theft reveals everything | Not used for findings |
| Plain hash (SHA-256) | No | Short values (8-digit IDs) can be guessed by hashing all possibilities | Document fingerprint (`sha256` of the file) |
| **HMAC** (keyed hash) | No | Needs the secret key to guess; DB alone is useless | Matching findings to values during redaction |

### Check yourself

1. Why does `audit_events.document_id` use `SET NULL` instead of `CASCADE`?
2. Why is `redaction_items` needed — couldn't `findings` have a `redaction_id` column?
3. Why would storing `SHA-256(card_number)` be unsafe?
4. Which constraint stops a typo like `review_status = 'resloved'`?

<details><summary>Answers</summary>

1. The audit trail must survive deletion — that is the point of auditing.
2. One finding can be part of several redactions (re-done after a failure) and each redaction has many findings: many-to-many needs a junction table. It also stores the outcome per pair.
3. There are few enough valid card numbers per issuer prefix that an attacker can hash candidates and compare. HMAC requires the secret key.
4. The `CHECK` constraint on `review_status`.
</details>

---

## 5. Security and threat modelling

### 5.1 The CIA triad

- **Confidentiality** — only authorised people see data (masked values, no raw secrets in logs).
- **Integrity** — data is not changed improperly (CSRF tokens, verified redaction).
- **Availability** — the system works when needed (upload limits against DoS).

### 5.2 Threat modelling in four questions

1. **What are we building?** → architecture and data-flow diagram.
2. **What can go wrong?** → STRIDE per element and boundary.
3. **What are we doing about it?** → mitigations linked to requirements.
4. **Did we do a good job?** → security tests (ST-01 … ST-15), reviewed every milestone.

### 5.3 Assets and trust boundaries

An **asset** is something worth protecting (originals, sanitized copies, findings, keys). A **trust boundary** is where data passes from a less-trusted zone to a more-trusted one: browser → Flask, *uploaded bytes → PDF parser*, Flask → disk. Attacks almost always enter at a boundary, so that is where validation goes.

### 5.4 STRIDE

| Letter | Threat | Violates | SecureWaste example | Typical defence |
|---|---|---|---|---|
| **S** | Spoofing | Authentication | Forged request from another site (CSRF) | Tokens, authentication |
| **T** | Tampering | Integrity | Path traversal overwrites files; fake redaction | Validation, safe names, verification |
| **R** | Repudiation | Accountability | "I never marked that false positive" | Audit log |
| **I** | Information disclosure | Confidentiality | Card number in a log line | Masking, no-leak tests |
| **D** | Denial of service | Availability | 2 GB upload, PDF bomb, ReDoS | Limits, timeouts |
| **E** | Elevation of privilege | Authorisation | Parser bug runs code; debug console exposed | Updates, least privilege, debug off |

### 5.5 Risk, mitigation, residual risk

**Risk ≈ likelihood × impact.** A **mitigation** lowers one or both. What is left is **residual risk**, which must be *accepted consciously* and written down with a date to revisit (e.g. R-01: no authentication in a single-user localhost MVP).

### 5.6 Key defences used in SecureWaste

| Defence | Stops |
|---|---|
| Validate the real file type (magic bytes), size and pages | Malicious or oversized uploads |
| Random server-side file names, path check | Path traversal |
| Jinja2 auto-escaping + Content-Security-Policy | XSS |
| CSRF tokens + `SameSite` cookies | CSRF |
| Parameterised SQL | SQL injection |
| Masking + HMAC, no raw values in logs | Information disclosure |
| True redaction + re-extraction verification + metadata scrub | Leaky "redacted" PDFs |
| `127.0.0.1` binding, debug off, secrets in `.env` | Remote access, debugger RCE, leaked keys |
| `pip-audit`, pinned dependencies | Known vulnerable libraries |

### 5.7 Masking vs redaction

**Masking** changes how a value is *displayed* (`•••• 4242`) — the original is untouched. **Redaction** permanently *removes* content from a document. SecureWaste masks everywhere in its UI and redacts only on request, producing a new file.

### Check yourself

1. Classify with STRIDE: "an attacker uploads a 10,000-page PDF to freeze the app".
2. Why is the PDF parser behind its own trust boundary even though it runs inside our process?
3. What is the residual risk if the laptop is stolen while unlocked?
4. Name two ways a "redacted" PDF could still leak data even if the visible text is gone.

<details><summary>Answers</summary>

1. **D**enial of service (T-17), mitigated by the page limit and character cap.
2. It processes untrusted bytes in native C code; a bug there could crash or compromise the process (T-19).
3. An attacker with the open session can read originals — accepted as R-01/R-04 (no auth, no encryption at rest in MVP).
4. Metadata (author, title, XMP), annotations, embedded files, or hidden text layers — hence metadata scrubbing, `garbage=4` saving and re-extraction verification.
</details>

---

## 6. Architecture Decision Records (ADRs)

### 6.1 The idea

An **ADR** is a one-page note recording a single important decision. Six months later, when someone asks "why SQLite and not PostgreSQL?", the answer is in [`docs/adr/0003`](../adr/0003-sqlite-with-plain-sql.md), not in someone's memory.

### 6.2 Structure

| Part | Content |
|---|---|
| Title + number | `ADR-0004: PyMuPDF for PDF extraction and redaction` |
| Status | Proposed → Accepted → (Superseded by ADR-00NN) |
| Context | The forces: requirements, constraints, facts |
| Decision | "We will …" |
| Alternatives | Options considered and why they lost |
| Consequences | **(+)** benefits and **(−)** costs/new risks |

### 6.3 Rules of thumb

- Write one when a decision is **hard to reverse**, **affects several people**, or **will be questioned later**.
- Never edit an accepted ADR's decision — write a new one that supersedes it. The history is the value.
- Add the ADR in the same pull request as the change it explains.

Example worth studying: [ADR-0004](../adr/0004-pymupdf-for-extraction-and-redaction.md) shows a technical choice with a **licence consequence** (AGPL), something students often overlook.

### Check yourself

1. The team decides to switch to SQLAlchemy in Milestone 3. What do you do with ADR-0003?
2. Does "use 4 spaces for indentation" need an ADR?
3. Which section of an ADR should mention new security risks?

<details><summary>Answers</summary>

1. Write ADR-0011 "Use SQLAlchemy Core" with status Accepted, and set ADR-0003's status to "Superseded by ADR-0011". Don't rewrite ADR-0003.
2. No — that is a convention (CONTRIBUTING.md / formatter config), easy to change, not an architectural decision.
3. Consequences (the **(−)** items).
</details>

---

## 7. The risk score, step by step

The model is defined in [Architecture §8](../02-architecture.md#8-risk-scoring-model). Let's score a synthetic invoice containing an e-mail, a phone number, a Luhn-valid card, a valid IBAN and the word CONFIDENTIAL.

| Step | Calculation | Points |
|---|---|---|
| E-mail (weight 3, confidence 0.9) | 3 × 0.9 | 2.7 |
| Phone (4, 0.6) | 4 × 0.6 | 2.4 |
| Card (40, 0.95) | 40 × 0.95 | 38 |
| IBAN (25, 0.95) | 25 × 0.95 | 23.75 |
| Label CONFIDENTIAL (10, 1.0) | 10 × 1.0 | 10 |
| Combination bonus (card + IBAN both ≥ 25) | +10 | 10 |
| Label amplifier (label + high-sensitivity data) | +10 | 10 |
| **Total** | rounded, capped at 100 | **97 → critical** |

Now Youssef marks the card as a **false positive** (it was a documented test number). Remove 38; the combination bonus disappears (only IBAN is ≥ 25 now) → 2.7 + 2.4 + 23.75 + 10 + 10 = 48.85 → **49 → medium**. The UI explains each line, so nobody has to trust a magic number.

### Check yourself

1. A TXT file contains only one high-confidence AWS-style access key (weight 45, confidence 0.9). What is the score and level?
2. Why does the model add only 20 % of the weight for repeated findings?

<details><summary>Answers</summary>

1. 45 × 0.9 = 40.5 → 41 (medium), but the **floor** for a high-confidence secret raises it to **75 → critical**.
2. Ten e-mail addresses are worse than one, but not ten times worse; diminishing returns stop long contact lists from outranking a single leaked key.
</details>

---

## 8. Glossary

| Term | Meaning |
|---|---|
| Acceptance criteria | Conditions that prove a requirement or issue is done |
| ADR | Architecture Decision Record |
| Application factory | A function (`create_app`) that builds and configures the Flask app |
| Artifact (UML) | A deployable file (package, database file) |
| Asset | Something worth protecting |
| CI | Continuous Integration — automatic tests on every change |
| Composition | "Owns, deleted together" relationship |
| CSP | Content-Security-Policy header restricting what the browser loads |
| CSRF | Cross-Site Request Forgery |
| DLP | Data Loss Prevention |
| False positive / negative | Harmless value flagged / sensitive value missed |
| Foreign key | Column referencing another table's primary key |
| HMAC | Keyed hash; cannot be recomputed without the secret key |
| HTTP status code | Three-digit result of a request (200, 404 …) |
| IBAN / mod-97 | International bank account number / its check calculation |
| Jinja2 | Flask's template engine, auto-escapes HTML |
| Lifeline | Vertical dashed line under a participant in a sequence diagram |
| Luhn | Check-digit algorithm used by payment cards |
| Masking | Hiding most of a value for display |
| MoSCoW | Must / Should / Could / Won't prioritisation |
| Multiplicity | How many objects can be linked (`1`, `0..*`) |
| NFR | Non-functional requirement (quality attribute) |
| Persona | Fictional, realistic description of a user type |
| Primary key | Unique identifier of a table row |
| Redaction | Permanent removal of content from a document |
| ReDoS | Denial of service through slow regular expressions |
| Residual risk | Risk remaining after mitigations, consciously accepted |
| SQL injection | Attack that changes a query through unescaped input |
| STRIDE | Spoofing, Tampering, Repudiation, Information disclosure, DoS, Elevation of privilege |
| Swimlane | Column of an activity diagram owned by one actor/layer |
| Trust boundary | Line where data passes between zones of different trust |
| User story | "As a…, I want…, so that…" requirement format |
| UUID | Random 128-bit identifier |
| Virtual environment | Per-project folder of Python libraries |
| XSS | Cross-Site Scripting — injected script runs in another user's browser |
