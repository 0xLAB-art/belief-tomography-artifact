# Cover letter — IEEE Transactions on Dependable and Secure Computing

Dear Editor-in-Chief,

I submit **"Measuring the Belief–Claim Gap: Active Black-Box Tomography of
Autonomous Agents and the Limits of Certification"** for consideration as a
regular paper in IEEE Transactions on Dependable and Secure Computing.

**What the paper does.** Deployed autonomous agents publish a security policy,
a charter, and act on beliefs that no certification mechanism tests: that a
message came from an administrator, that a tool output can be trusted, that
they are unobserved. The paper makes the distance between the published claim
and the measured behavior a quantity. I introduce *belief tomography*: active,
black-box estimation of an agent's behavioral belief profile from deliberately
designed probe interactions, with per-proposition Wilson intervals and a
certification semantics. The attack vectors already in use become the
measurement instruments.

**Contributions.** (i) An estimand and an instrument with measured validity,
reliability, and an audited verdict channel. (ii) An impossibility result that
makes active measurement necessary, query-complexity bounds, and a
deception–detection frontier. (iii) Limits on certification—gameability of
public probe suites, non-composition of statistical certificates, forgery,
half-life, reactivity, and censoring—each paired with an experiment on
constructed foils with known ground truth. (iv) Disclosure economics for
published measurements. (v) Two registered field predictions, both refuted at
instrument resolution, with the two measurement-error classes the program
caught in itself.

**Fit with TDSC.** The subject is security assurance: whether a claimed
security policy can be certified from behavior, and what such a certificate
cannot establish. The non-composition and forgery results are negative results
for certification practice, and the censoring floor applies to any black-box
evaluation conducted behind a filtering provider API.

**Originality, review status, and disclosure.** The manuscript is original and
is not under review elsewhere. All thirty experiments are registered, seeded,
and pinned to a frozen estimator; a claims–evidence ledger and a SHA-256
manifest accompany the submission and map every number to an artifact. The
headline transcript audit, which is author-side, was additionally
re-adjudicated on a blinded 20% sample by three independent coders: 45/46
agreement on the full sample (Cohen's κ = 0.96) and 39/39 with each coder's
own panel excluded (κ = 1.00), with the sample, coder sheets, and sealing key
in the artifact package. No
human subjects were involved. Third-party model endpoints were probed under
paid, metered, rate-limited terms with fictional canaries only, and no
destructive command was executed on any host. AI-assisted drafting tools were
used for language editing under my direction; all experimental design, data
collection, analysis, and verified claims are my own.

I would be glad to answer any question the editors or reviewers may have.

Sincerely,

Anonymous
Independent Researcher, Cairo, Egypt
anonymous@example.com
ORCID: withheld-for-review
