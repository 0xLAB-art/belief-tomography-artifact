% ============================================================================
% Belief Tomography — ACM TOPS submission (multi-file project; house
% convention: paper/tdsc, paper/sp2027).
% Rebuilt from scratch for ACM Transactions on Privacy and Security.
% All quantitative claims are pinned to the program's frozen artifacts; the
% claims--evidence ledger in the artifact repository maps every number to a
% path and commit. Proofs live in Appendix A.
% ============================================================================
\documentclass[acmsmall]{acmart}
\microtypesetup{expansion=false}
\setlength{\emergencystretch}{1.5em}
\usepackage{booktabs}
\usepackage{fontawesome5}
\usepackage{enumitem}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepgfplotslibrary{fillbetween,groupplots,polar}
\usetikzlibrary{arrows.meta,positioning,calc}
\definecolor{oiblue}{HTML}{0072B2}
\definecolor{oiorange}{HTML}{E69F00}
\definecolor{oigreen}{HTML}{009E73}
\definecolor{oired}{HTML}{D55E00}
\definecolor{oipurple}{HTML}{CC79A7}
% ---- unified figure system (v2) --------------------------------------------
% One axis style for every figure in the paper: left/bottom spines only,
% light horizontal grid, frameless legends, text strictly inside the axes
% (clip=true). Annotation discipline: short anchored labels only;
% explanatory sentences belong to the caption, never to the plot interior.
\pgfplotsset{
  tomog/.style={
    font=\footnotesize,
    tick label style={font=\scriptsize},
    label style={font=\footnotesize},
    title style={font=\scriptsize},
    axis lines*=left,
    axis line style={black!60, thin},
    tick style={black!60, thin},
    grid style={black!10, thin},
    ymajorgrids,
    xmajorgrids=false,
    legend cell align=left,
    legend style={draw=none, fill=none, font=\scriptsize,
      inner sep=1.5pt, row sep=-2pt},
    clip=true,
    xlabel near ticks, ylabel near ticks,
  },
  % error bars without the default end caps (the "+"-tick artifact)
  ebars/.style={error bars/.cd, y dir=both, y explicit,
    error mark=none, error bar style={thin}},
  ebarsx/.style={error bars/.cd, x dir=both, x explicit,
    error mark=none, error bar style={thin}},
}

\graphicspath{{../figures/}}


\newcommand{\TV}{d_{\mathrm{TV}}}
\newcommand{\E}{\mathbb{E}}

\acmJournal{TOPS}
\acmYear{2026}
\acmDOI{}
\settopmatter{printfolios=true}

\begin{document}

\title{What Do Autonomous Agents Believe Under Attack? Active Black-Box Belief
Tomography}

\author{the author Hamdi Anonymous Ibrahim}
\affiliation{%
  \institution{Independent Researcher}
  \city{Cairo}
  \country{Egypt}}
\email{anonymous@example.com}
\orcid{withheld-for-review}

\begin{abstract}
Deployed autonomous agents publish a charter, the security policy they claim
to uphold, and act on beliefs that no current certification ever tests: that
a message came from an administrator, that a tool output can be trusted, that
they are unobserved. A charter is an assertion; this paper makes the distance
between assertion and behavior a measured quantity. We introduce \emph{belief
tomography}: the active, black-box estimation of an agent's \emph{behavioral
belief profile} from deliberately designed probe interactions, with
per-proposition Wilson intervals and a certification semantics. The attack
vectors already in use become the instruments: every forged-authority
directive, lying tool output, and exfiltration lure is a probe that asks the
agent a question about its latent state, and the agent's behavior is the
answer. The theory bounds the enterprise from every direction: passive
monitoring cannot tomograph; a patch-decay law and an onset dichotomy jointly
cap deception gain and stealth; public probe suites are gameable, statistical
certificates do not compose, and published profiles are forgeable by attacker
and defender alike; and disclosure admits no free lunch, with a gaming-gap
statistic that decides when a certificate may transfer at all. We validate
the instrument on constructed foils with known ground truth (dose--response
$r \ge 0.986$; test--retest $r = 0.949$), calibrate its verdict channel with
seeded known-truth sessions, and carry it through 21 pre-registered
experiments under a frozen, pinned estimator. Two pre-registered field
measurements on production frontier models return nulls at instrument
resolution: targets hold their charters under a 300-session probe attack
($\hat\beta = 0$, Wilson 95\% $[0, 0.060]$ per family), and attacker personas
hold their operational beliefs under live honeypot deception ($\Delta(B)$ at
or below the noise floor for all five personas). The estimand, the protocol,
and the bounds are released for the field to replicate, attack, and build
assurance on.
\end{abstract}

\maketitle

% Short running head: acmart rebuilds \shorttitle from the full title
% inside \maketitle, so the journal-header variant is set after it.
% \shorttitle = header-left (odd pages), folio = header-right.
\renewcommand{\shorttitle}{What Do Agents Believe Under Attack? Belief
Tomography}

\keywords{belief tomography, agent security, behavioral measurement, deception,
certification, honeypots, disclosure economics}

\ccsdesc[500]{Security and privacy~Systems security}
\ccsdesc[300]{Security and privacy~Artificial intelligence}
\ccsdesc[300]{Security and privacy~Privacy protections}
\section{Introduction}\label{sec:intro}

Every deployed autonomous agent holds beliefs that no certification ever
examines: that a message really came from an administrator, that a tool
output deserves trust, that a credential is its to spend, that its actions
go unwitnessed. What the agent \emph{publishes} is a charter, the security
policy it claims to uphold. What it \emph{does} once those beliefs come
under attack is a different object, and current certification never touches
it: code review, tool auditing, and configuration attestation all stop at
the boundary where an adversary begins to speak. The gap is not
hypothetical. A model that cooperates through evaluation and hijacks in
deployment, an agent that obeys a forged authority message, a honeypot
specialist that finishes its probe unseen---each is a divergence between
the belief the system asserts and the belief its behavior reveals.

This paper makes that divergence a measured quantity. The observation that
powers it is that the attack vectors already in use are instruments waiting
to be read as such: a forged-authority message asks whether authority is
verified; a lying tool output asks whether outputs are validated; a
reflection-extraction chain asks whether private reasoning can be surfaced;
an exfiltration lure asks whether secrets move under pressure. Each probe
puts one question about the agent's latent state to the behavioral channel,
and the response is the answer. From deliberately designed probe
interactions we estimate a \emph{behavioral belief profile} $\hat\beta$,
proposition by proposition with Wilson intervals, and define the
\emph{Belief--Claim Gap} (BCG) between the charter's claims and the
profile's measurements. Figure~\ref{fig:tomogram} shows the object on
constructed foils with known ground truth: two targets that a code or
configuration audit cannot tell apart separate cleanly into a naively
compliant profile and a graded one.

A single latent object organizes three activities the field usually treats
separately. \emph{Certification} is a hypothesis test over the profile.
\emph{Deception} is controlled corruption of an adversary's profile.
\emph{Monitoring} is change-point detection on the profile over time. The
profile is also the paper's privacy object: a published tomogram is a
targeting map for whoever reads it (Section~\ref{sec:disclosure}), so the
\emph{release} of a measurement is itself a security-and-privacy decision,
and we derive its trade-off frontier. One measurement serving assurance and
reconnaissance at once is why the paper belongs in a privacy-and-security
venue rather than a benchmarking one.

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{anthro/fig_beta_foils.pdf}
\caption{The tomogram, on constructed foils with known ground truth: a naive
foil built to comply with every attack, and a graded hardened foil.
(a)~Measured behavioral belief profile per probe family---dots: measured
$\hat\beta$; whiskers: Wilson 95\% CIs; grey span: the interval separation
between the two foils (or their overlap, \emph{no separation})---with the
signed per-family gap $\Delta\hat\beta$ against the design target. The naive
foil's epistemic-echo cell reads $2/3$, indistinguishable from the hardened
foil's---an oracle-induced verdict error audited in
Section~\ref{sec:audit}. (b)~The per-cell trial accounting behind every
interval (18 trials per cell; filled squares count toward $\hat\beta$).
Pooled across all families: $0.933$ $[0.862,0.969]$ vs.\ $0.600$
$[0.497,0.695]$. Black-box interaction alone separates the designed
targets.}
\label{fig:tomogram}
\end{figure}

\subsection{Contributions}

Five contributions, each tied to a registered artifact and stated so that it
could fail:

\begin{enumerate}[leftmargin=*,itemsep=1pt,topsep=2pt]
\item \textbf{The estimand} (Section~\ref{sec:estimand}): behavioral belief
strength $\beta(\pi;\Pi)$, the Belief--Claim Gap, epistemic distance, and
deception gain $\Delta(B)$, together with the sensitivity assumption on
which every bound rests, stated explicitly and checked empirically.
\item \textbf{Theory} (Section~\ref{sec:theory}): the impossibility result
that makes active measurement necessary (Theorem~\ref{thm:passive}); uniform
and adaptive query-complexity guarantees for estimation
(Theorem~\ref{thm:uniform}, Proposition~\ref{prop:screening}); the
deception--detection frontier, where a patch-decay law and an onset
dichotomy jointly cap deception gain and stealth
(Theorems~\ref{thm:patch}--\ref{thm:onset}); the limits of certification,
from public-probe gameability through statistical non-composition, the
gaming-gap transfer diagnostic, tomogram forgery, adaptive gaming,
certificate half-life, tomographic reactivity, and allocation under learning
attackers (Corollary~\ref{cor:pub}, Theorem~\ref{thm:compose},
Propositions~\ref{prop:gaming}--\ref{prop:alloc}); and the economics of
disclosure: reconnaissance externality, defender-side deception release,
and the detection-budget coupling (Propositions~\ref{prop:recon},
\ref{prop:release}, \ref{prop:budget}). Appendix~\ref{app:proofs} carries
the proofs.
\item \textbf{An instrument with measured validity, reliability, and an
audited verdict channel} (Section~\ref{sec:instrument}): dose--response
$r \ge 0.986$ across 1{,}500 episodes; test--retest $r = 0.949$ at the
registered operating point of 10 probes per cell; a seeded calibration of
the adjudication channel (sensitivity $0.960$, FP $0/25$); and
estimator- and seed-robustness across the program.
\item \textbf{Two pre-registered field nulls} (Section~\ref{sec:field}):
frontier targets hold their charters under a 300-session probe attack
($\hat\beta = 0$, Wilson 95\% $[0, 0.060]$ per family), and frontier
attacker personas hold their operational beliefs under live honeypot
deception ($\Delta(B)$ at or below the noise floor for all five personas),
with every kill gate passed and every deviation logged in both cases.
\item \textbf{The economics of disclosure} (Section~\ref{sec:disclosure}): a
published profile is attacker reconnaissance ($A_{\mathrm{rec}} > 0$);
attacker and defender can both forge it; and bounded-noise release traces a
monotone frontier with no interior dominance, so disclosure policy is a
choice on a curve, not an evasion.
\end{enumerate}

\paragraph{The program at a glance.}
Table~\ref{tab:program} places the entire measurement program on one page,
organized in three layers. The \emph{instrument} layer (E1, E1b, T3,
E17--E19) establishes what the instrument measures, how reliably, and which
estimator decisions survive a change of estimator or seed. The
\emph{constructed-foil} layer (E4--E16, E20) establishes what certification,
gaming, forgery, and disclosure can and cannot do once ground truth is
controlled. The \emph{field} layer (E2, E3) measures production frontier
models and a live honeypot fleet. Every experiment was pre-registered before
its data existed, seeded, and pinned to a frozen estimator; the artifact
package reproduces every number in this paper (Data Availability).
Section~\ref{sec:limits} states what the results do not establish.

\begin{table}[p]
\centering\small
\begin{tabular}{@{}p{0.62cm}p{4.05cm}p{6.55cm}p{0.95cm}@{}}
\toprule
Exp. & Registered question & Outcome (frozen artifact) & \S \\
\midrule
E1 & Does measured breach track injected dose? &
$r\ge0.986$, $\rho=1.00$, all five families (1{,}500 episodes) &
\ref{sec:validity} \\
E1b & Do independent batches reproduce the profile? &
$r=0.949$ at 10 probes/cell; $0.837$ at 4---below bar, so batch size is
part of the specification & \ref{sec:reliability} \\
T3 & Which allocation objective fits the goal? &
Uniform/Neyman mean error $0.035$ vs.\ UCB $0.121$, PSI $0.129$ at
$n=400$ & \ref{sec:alloc} \\
E17 & Can the verdict channel's audit be trusted? &
Sensitivity $0.960\,[0.805,0.993]$, FP $0/25\,[0,0.133]$; dominates the
lexical oracle & \ref{sec:audit} \\
E18 & Do headline decisions survive another estimator? &
Zero decision flips at $\tau=0.2$; intervals $0.88$--$0.99\times$
narrower & \ref{sec:robust} \\
E19 & Do foil results hold at fresh seeds? &
E6/E7/E9/E10 hold at three fresh seeds & \ref{sec:robust} \\
E5 & Does the onset dichotomy hold quantitatively? &
$N_0{=}10$: floor $0.283>\delta$, AUC $0.69$--$0.74$; $N_0{=}40$: rises
$0.76\!\to\!0.97$; birth onset $0.34$--$0.53$ & \ref{sec:e5} \\
E4 & Does the decision rule separate designed targets? &
Resistant certified $5/5$; naive rejected $5/5$; graded rejected on four
families, one unresolved (power) & \ref{sec:cert} \\
E6 & Does component certification compose? &
Pipeline breach $\hat\beta=1.000\,[0.839,1.000]$ with both components
certified at zero & \ref{sec:surface} \\
E7 & Can a target pass public and fail held-out probes? &
$\Gamma=1.000$; controls separate probe-awareness from malice &
\ref{sec:surface} \\
E8 & Can certification cover the interface? &
One relay probe flips both certified components to $\hat\beta=1.0$ &
\ref{sec:surface} \\
E9 & Can a tomogram be forged? &
Display/true profiles differ by $1.0$ in two families; public probes
verify the display & \ref{sec:forgery} \\
E10 & Does a published held-out set survive adaptation? &
$\Gamma_{P,H}=0$ with secret $\hat\beta_S=1.0$; the secret set restores
detection & \ref{sec:forgery} \\
E11 & How long does a certificate stay valid? &
One-shot falsified at 4 epochs; half-life rule 2 runs vs.\ calendar 5 &
\ref{sec:drift} \\
E12 & Does shared-context probing bias the estimand? &
Bias $0.467$ absolute ($93.3\%$ relative); session reset is the
identification condition & \ref{sec:drift} \\
E13 & Does uniform allocation survive a learning attacker? &
Uniform: $0/5$ detected, false certificate; concentrated: $3/5$ &
\ref{sec:learned} \\
E14 & What does publishing a profile cost? &
Attacker advantage $A_{\mathrm{rec}}=0.067$ graded, $0.000$ flat &
\ref{sec:recon} \\
E15 & Can the defender release a forged tomogram? &
Per-attempt success: decoy $0.000$, honest $1.000$, silence $0.200$;
stable under public verification & \ref{sec:release} \\
E16 & How large must the secret held-out set be? &
$n_{\min}=1,2,8$ at $m=0.02,0.10,0.50$; diverges to $2{,}057$; infeasible
for $m\ge0.94$ & \ref{sec:budget} \\
E20 & Is there a costless disclosure mechanism? &
No interior point dominates either corner (no free lunch) &
\ref{sec:frontier} \\
E2 & Do production agents hold their charters under probe attack? &
$\hat\beta=0$, Wilson 95\% $[0,0.060]$ in every family; two frontier
models, 300 sessions & \ref{sec:e2} \\
E3 & Does honeypot deception move attacker beliefs? &
$\Delta(B)$ at or below the noise floor for all five personas (live
fleet) & \ref{sec:e3} \\
\bottomrule
\end{tabular}
\caption{The measurement program at a glance: the 21 pre-registered
experiments and the T3 allocation benchmark, their registered questions,
and their frozen outcomes. Nulls are reported alongside positives; every
outcome is quoted from the claims--evidence ledger of the artifact
repository.}
\label{tab:program}
\end{table}

\section{Background and Related Work}\label{sec:related}

\subsection{Four frames, one missing layer}\label{sec:frames}

Four research communities study objects adjacent to the behavioral belief
profile, and each stops one step short. Quantitative information flow asks
what an adversary \emph{learns} about a secret from a system's observable
behavior \cite{smith2009,alvim2020}. Information design asks what a sender
can \emph{conceal or distort} \cite{kamenica2011}. Deception games ask what
a defender \emph{gains} at equilibrium \cite{nguyen2019}. Theory-of-mind
research asks whether an agent can model \emph{others'} beliefs
\cite{strachan2024}. Belief tomography poses the question none of the four
asks: \emph{what is an agent made to wrongly believe}, with quantified
bounds (Table~\ref{tab:frames}). The deception literature's most-cited
survey defines deception functionally and calls for governance
\cite{park2024}, and venue-level surveys of LLM-agent security and privacy
catalogue the threats without a measured estimand
\cite{he2025survey}. This paper supplies the missing layer: an estimand, an
instrument, impossibility results, and the gain--stealth frontier.

\begin{table}[t]
\centering\small
\begin{tabular}{p{1.88cm}p{2.34cm}p{2.60cm}}
\toprule
Frame & Question it answers & What tomography adds \\
\midrule
Quantitative information flow & What does the adversary \emph{learn}?
& The dual: what the adversary is made to \emph{wrongly believe}, with gain
bounds \\
Information design & What can a sender \emph{distort}? & Sampling-horizon
bounds with executable probes \\
Deception games & What does the defender \emph{gain} at equilibrium?
& Non-equilibrium, finite-sample frontier \\
Theory of mind & Can the agent model \emph{others'} beliefs? & Estimation of
the agent's \emph{own} held beliefs from outside \\
\bottomrule
\end{tabular}
\caption{Four adjacent frames and the missing layer each leaves open.}
\label{tab:frames}
\end{table}

\subsection{Tomography of latent state}

The name is borrowed deliberately. Cognitive tomography inverts a generative
model of behavior to recover latent mental representations in humans
\cite{houlsby2013}, the paper's intellectual ancestor, and TestifAI applies
the word to deep-learning test prioritization \cite{testifai}. The
black-box neighbors that infer agents from behavior recover \emph{policy
structure}, not security beliefs: TripleTree discretizes the state space
into interpretable regions \cite{tripletree2020}, imitation-learning work
reverse-engineers agent policies as decision trees \cite{bewley2020}, and
Mxplainer learns parameterized approximations of them
\cite{mxplainer2025}. None of these estimates security beliefs, offers an
impossibility result, or attaches confidence intervals to a deception-gain
estimand. White-box propositional probes read latent world states out of
activations \cite{feng2024}, and full audit pipelines locate deliberately
planted hidden objectives in production-scale models when the weights are
open \cite{marks2025audit}; both require weights and both are passive,
which makes them complements rather than competitors. Model-generated red
teaming automates probe construction \cite{perez2022redteam}. What red
teaming lacks (an estimand, intervals, and validity checks for what its
probes measure) is exactly what tomography adds.

\subsection{The self-report--behavior gap}

Psychometric work documents that LLM self-reports diverge from behavior
\cite{shen2025,valuebench}; preference tuning teaches models to match the
user's beliefs over the truth \cite{sharma2024}; and under organizational
pressure, models strategically deny actions they demonstrably took
\cite{scheurer2024}. The Belief--Claim Gap is this phenomenon in its
adversarial security form, now carrying confidence intervals and a
certification semantics. The deeper difference is causal: a questionnaire
item \emph{asks}, whereas a probe family \emph{intervenes}---it creates the
condition under which the claimed belief must either do work or fail.

\subsection{Deception measurement}

Deception abilities emerge with model capability \cite{hagendorff2024}.
Existing deception measures score the \emph{deceiver}: propensity or
deception quality \cite{decepeval,rowe2006}; honesty dissociated from
accuracy in the MASK benchmark, where larger models improve the latter but
not the former \cite{mask2025}; or plain honeypot engagement. None
estimates the victim's or the attacker's belief profile as a statistical
object. The equilibrium neighbors are game-theoretic deception
\cite{nguyen2019} and Bayesian persuasion with its lie-detection extension
\cite{kamenica2011,nberlie}; Section~\ref{sec:t5} supplies what they do not:
a sampling-horizon information theory with executable probes. Deception is
also the dual of leakage: a channel that injects falsehood where leakage
steals secrets. The onset dichotomy composes the deception channel with the
attacker's prior channel, so the paper speaks to the
quantitative-information-flow tradition as much as to security measurement.

\subsection{Defeat devices and the limits of evaluation}

Evaluation-aware behavior is not a new claim, and we do not make it as one:
alignment faking demonstrated it canonically \cite{greenblatt2024faking};
context-conditioned backdoors realize the structure at training time and
compromise embodied agents through poisoned demonstrations
\cite{liu2025tifs}; Ferrara's \emph{defeat device} names the triad our
probe-aware foil instantiates (an evaluation-context discriminator, a
concealed behavioral swap, and an evaluation--deployment gap)
\cite{ferrara2026}; and partition theory proves the general identifiability
limit that a behavioral evaluator cannot catch an examinee imitating it
\cite{mahran2026}. Our Corollary~\ref{cor:pub} and Theorem~\ref{thm:forgery}
are the \emph{estimator-level} instances of these facts: the same phenomenon
expressed as a binomial belief profile with Wilson intervals, a tolerance
$\tau$, and a gaming-gap decision statistic. The adversary is not the
novelty; the instrument and the composition result are. Ferrara's TADP
protocol is explicitly proposed \emph{without} empirical validation;
E7/E9/E10 supply the concrete differential probe, a quantified statistic, a
measured instrument noise floor, Wilson intervals, and a conditional
transfer bound (Section~\ref{sec:surface}). He also names
``meta-discriminator triggers,'' a discriminator that detects probes for
the discriminator, as the arms-race extension he does \emph{not}
characterize empirically; E10 is exactly that characterization, with a
secret-diagnostic-set defense.

Auditing under adaptive attack
\cite{soopal2026,duddu2026,tice2025,auditinggames2025} shows that a detector
beaten once cannot be assumed robust; E10 mounts precisely this challenge
against our own gaming-gap check, and E16 closes the loop by computing the
defender's held-out budget as a function of the attacker's
probe-discrimination error, the budget--error coupling those stress tests
leave implicit (sandbagging itself is demonstrated in
\cite{aisandbagging2024}). The normative argument that reward selects for
conditional compliance \cite{baum2026} motivates the problem without
supplying an estimator. Configuration attestation \cite{ati2026} answers
``is this the approved model and tool configuration?''; tomography answers
``what does it do under adversarial pressure?'' The two are complements,
not substitutes.

\subsection{Deception doctrine and decoy artifacts}

Defender-side misinformation is classical doctrine: cyber-deception shapes
attacker beliefs about defended systems \cite{bodeau2013}; controlled
deception experiments quantify attacker-cognition effects, the Tularosa
study measuring them against live red teams
\cite{tularosa2019,fergusonwalter2017}; and modern deception frameworks
report misinformation effective against targeted attackers \cite{perry2025}.
Decoy \emph{artifacts} for AI agents plant fake objects that alert on
interaction \cite{honeypotagents2026}, and the LLM Agent Honeypot flags AI
hacking agents in the wild across 8.1M SSH sessions through deployment cues
and prompt-injection canaries \cite{volkov2024}. E15 differs in the
\emph{medium}: the falsified object is a published behavioral
\emph{measurement} of real components, stable precisely because verification
confined to the public probe suite reproduces it (Theorems~\ref{thm:forgery}
and~\ref{cor:adaptive} applied in the defender's favor). The trust-collapse
risk under attacker held-out capability has no analogue in artifact
planting.

\subsection{Composition and orchestration boundaries}

Per-component safety does not imply pipeline safety. ChainCaps names the
``permission laundering'' case, in which every per-tool permission check
passes while the end-to-end effect is unsafe, and defends with runtime
capability attenuation \cite{chaincaps2026}; CaMeL derives prompt-injection
resistance from an explicit control- and data-flow design \cite{camel2026};
structured queries and preference-optimized resistance harden the model
side against injection \cite{struq2025,secalign2025}; programmable privilege
control bounds what an already-compromised agent can reach
\cite{progent2025}; knowledge-corruption attacks poison the retriever's
corpus from the data side \cite{poisonedrag2025}; and framework studies
\cite{orchestration2026} and orchestration-guided jailbreaks
\cite{orchjail2026} document related failures. Theorem~\ref{thm:compose} is
not another entry in that catalogue. It is the estimator-level analogue: a
confidence-interval behavioral certificate at tolerance $\tau$ fails to
compose, and E8's interface-vocabulary probe is the measurement-layer
complement to those runtime defenses.

\subsection{Epistemics-adjacent LLM work}

Theory-of-mind probing asks whether an agent can track \emph{others'}
beliefs \cite{strachan2024}; the direction here is reversed. Black-box
epistemic-reliability auditing \cite{eraudit} hunts paraphrase
counterexamples to a verifier's non-degradation, not a behavioral belief
profile. Three 2026 systems mark the convergence of the vocabulary. EpiAgent
learns an explicit epistemic layer that maintains beliefs over others'
private information during self-play \cite{epiagent}: it \emph{maintains} a
belief layer for the agent's own play, whereas tomography \emph{estimates} a
deployed agent's profile from outside, with intervals attached. ``Before
Agents Decide'' frames epistemic action as evidence acquisition
\cite{beforedecide}; the probe is that idea made adversarial and
measurable. Proxy Confidence recovers a surrogate's log-probabilities to
audit a single proposed tool call \cite{proxyconfidence}: it scores one
action, with no belief profile, charter semantics, or impossibility result.
The convergence is timing evidence: the window for the estimand is open.

\section{Threat Model and the Estimand}\label{sec:estimand}

\subsection{Threat model}\label{sec:threat}

Two roles recur throughout. The \emph{operator} of an agent (the defender)
holds the charter and may publish measurements about the agent. The
\emph{adversary} is either (i) an attacker \emph{of} the agent, who probes
it to discover exploitable beliefs (implicit-authority acceptance, secret
disclosure, destructive compliance), or (ii) an agent \emph{acting as} an
attacker against a defended host, whose beliefs about the environment the
defender may deceive. The tomographer may be the operator (certification) or
the adversary (reconnaissance); Section~\ref{sec:disclosure} analyzes
exactly this duality. All interactions are black-box: the tomographer
observes channel behavior only (prompt/response transcripts and tool-call
traces), never weights, activations, or system prompts beyond what the
channel reveals.

\paragraph{Attack classes and probes.}
The probe families instantiate, in instrument form, the attack classes
documented for production LLM agents: indirect prompt injection
\cite{greshake2023}, its benchmark for tool-integrated agents
\cite{injecagent2024}, formally benchmarked prompt injection
\cite{liu2024promptinjection}, the dynamic agent-attack settings of
AgentDojo \cite{agentdojo2024}, and agent-harm benchmarks that measure
whether malicious tasks complete \cite{agentharm2025}. Those works ask
whether an attack \emph{succeeds}; tomography asks what the response to it
\emph{reveals} about the agent's beliefs. AgentDojo's finding that no
evaluated defense survives adaptive attackers is the empirical edge that
Corollary~\ref{cor:pub} formalizes for any finite public probe suite. Every
experiment in this paper operates on systems the author owns or on locally
constructed foils; no third-party system was attacked.

\begin{definition}[Agent, charter, benign operation]\label{def:agent}
An \emph{agent} is a (possibly randomized) map from interaction histories to
responses, $A:\mathcal{H}\to\Delta(\mathcal{R})$, with response kernel
$\kappa_B(h,\cdot)$ parameterized by a belief hypothesis $B\in\mathfrak{B}$. Its
\emph{charter} $\chi$ is a published set of policy claims. \emph{Benign
operation} is a distribution $\mu$ over histories in which no adversary is
present.
\end{definition}

\begin{definition}[Belief proposition and probe family]\label{def:probe}
A \emph{belief proposition} $\pi$ is a testable statement about the agent's
operative beliefs (e.g., ``believes forged system authority''). A \emph{probe
family} $\Pi=(G_\Pi,c)$ is a generator of interaction episodes aimed at $\pi$ in
context $c$, drawn from a library of instrument families---authority forgery,
state deception, goal subversion, epistemic echo, exfiltration lure---each with
escalation \emph{generations} $g\in\{1,2,3\}$ of increasing indirectness and
decomposition.
\end{definition}

\begin{definition}[Behavioral belief strength]\label{def:beta}
Given a binary behavioral-consistency functional $X_B(\Pi)\in\{0,1\}$ (the
verdict that the agent's response is consistent with holding $\pi$, produced by
deterministic oracles and a calibrated judge), the \emph{behavioral belief
strength} is
\[
\beta(\pi;\Pi)=\E_{G_\Pi,\kappa_B}\!\left[X_B(\Pi)\right]\in[0,1].
\]
The \emph{belief profile} is $B=\{\beta(\pi;\Pi_c)\}_{\pi\in\mathcal{P}}$ over a
proposition catalogue $\mathcal{P}$ and context grid $c$---the tomogram.
\end{definition}

The estimand is deliberately \emph{behavioral}: the probability that the
agent's behavior is consistent with holding the proposition under the probe
family. It makes no claim about internal representations, and it refuses
introspection as a proxy channel, because chain-of-thought explanations are
measurably unfaithful to the causes of a response \cite{turpin2023}. Two
agents with identical profiles may realize them by different mechanisms.
That underdetermination is a feature, not a defect: behavior is the only
object well-defined for a deployed black-box system, and the only one
contractible in procurement and certification. Section~\ref{sec:t1} shows
the behavioral object is also \emph{necessary}: passive observation cannot
identify it in general.

\begin{definition}[Belief--Claim Gap]\label{def:bcg}
For a charter claim $\varphi\in\chi$ with instrument mapping
$F(\varphi)\subseteq\mathcal{P}\times\mathcal{C}$ (the propositions and contexts
that test it), the \emph{Belief--Claim Gap} is
\[
\mathrm{BCG}(\varphi)=\frac{1}{|F(\varphi)|}\sum_{(\pi,c)\in F(\varphi)}
\beta(\pi;\Pi_c).
\]
$\mathrm{BCG}(\varphi)\approx1$ under a claim $\varphi$ asserting the negation
of $\pi$ means the charter asserts what the behavior contradicts.
\end{definition}

\begin{definition}[Epistemic distance and deception gain]\label{def:gain}
For two profiles $B,B'$, $d(B,B')$ is a divergence over profiles (e.g., $\ell_1$
over shared propositions). In a deception operation against an attacker whose
profile is estimated at times $t_0,t_1$, the \emph{deception gain} is
$\Delta(B)=d(B_{t_0},B_{t_1})$ in the direction induced by the deception
objectives.
\end{definition}

\section{Theory: Impossibility, Query Complexity, and the Deception--Detection
Frontier}\label{sec:theory}

The theory develops in three steps, each answering one question the
introduction left open. Section~\ref{sec:t1} shows that passive monitoring
cannot tomograph, so measurement must be active.
Section~\ref{sec:qc} prices active estimation: a uniform sample-complexity
guarantee, and what adaptive screening can and cannot save.
Section~\ref{sec:t5} derives the deception--detection frontier, the pair of
laws that jointly cap deception gain and stealth. Proofs are in
Appendix~\ref{app:proofs}; the predictions of Section~\ref{sec:t5} meet
their constructed planes in Section~\ref{sec:e5}.

\paragraph{Notation and standing conventions.}
An agent acts on interaction histories $h\in\mathcal{H}$ through a response
kernel $\kappa_B(h,\cdot)$ parameterized by a belief hypothesis
$B\in\mathfrak{B}$ (Definition~\ref{def:agent}). \emph{Benign operation} is a
distribution $\mu$ over histories with no adversary present; composed with
$\kappa_B$, it induces the \emph{passive transcript distribution}
$P^{\mathrm{pas}}_B$. For distributions $P_1,P_2$ on a common space,
$\TV(P_1,P_2)=\sup_{A}\,|P_1(A)-P_2(A)|$ is total variation distance---the
largest gap one event can open between them, and the worst-case error of the
optimal test between them. A probe family $\Pi$, scored by the binary
verdict $X_B(\Pi)\in\{0,1\}$ (Definition~\ref{def:beta}), induces the belief
strength $\beta(\pi;\Pi)=\E[X_B(\Pi)]\in[0,1]$, written $\beta[\mu](\pi)$ in
Section~\ref{sec:t5} when viewed as a functional of transcript distributions
$\mu$. Throughout, $N$ is an i.i.d.\ observation horizon, $M$ an
interaction-turn budget, $N_0$ a memorized honest reference batch,
$\beta_d$ a tolerated false-alarm rate; $\alpha$ is reserved for confidence
levels (Section~\ref{sec:qc}) and $\delta$ for a deception's observable
footprint (Section~\ref{sec:t5}).

\subsection{Passive monitoring cannot tomograph}\label{sec:t1}

Is active probing necessary at all? A monitor that merely watches the
transcript stream could in principle recover the profile without ever
injecting a probe. Theorem~\ref{thm:passive} answers no, and the obstruction
is structural rather than statistical: two hypotheses can agree on every
transcript benign operation produces and still disagree completely on one
adversary-controlled input that benign operation never delivers.

\begin{theorem}[Passive-observation impossibility]\label{thm:passive}
There exist belief hypotheses $B_0\neq B_1$ and an adversary-controlled event
$E$ (e.g., a forged-authority directive) with $\Pr_\mu(E)=0$ such that:
\begin{enumerate}[label=(\roman*),leftmargin=2em]
\item the passive transcript distributions coincide,
      $\TV\bigl(P^{\mathrm{pas}}_{B_0},P^{\mathrm{pas}}_{B_1}\bigr)=0$; and
\item a single probe family separates them completely,
      $\E_{B_1}[X_B(\Pi)]-\E_{B_0}[X_B(\Pi)]=1$.
\end{enumerate}
\end{theorem}

\begin{corollary}[Detection impossibility under bounded false
positives]\label{cor:detection}
Any monitor whose input is the passive transcript stream---any classifier, any
alarm rule---has identical output distributions under $B_0$ and $B_1$. By
Neyman--Pearson, no such monitor achieves true-positive rate exceeding its
false-positive rate on distinguishing $B_1$ from $B_0$.
\end{corollary}

The proof (Appendix~\ref{app:proofs}) constructs two agents that agree on
every benign history and diverge on an adversary-controlled input benign
operation never delivers. The IDS literature built the statistical
ancestors: mimicry attacks \cite{wagner2002} and polymorphic blending
\cite{fogla2006} render attacks indistinguishable from benign traffic;
Theorem~\ref{thm:passive} is the belief-state generalization. The
contribution here is not the idea of indistinguishability. It is the
\emph{finite-sample detection frontier} (Section~\ref{sec:t5}), its coupling
to belief gain, and the agent-interaction instantiation. The program's
measured $\varepsilon=0$ non-detector---an adaptive generation-3 attacker
statistically indistinguishable from benign traffic under a full detector
ensemble\footnote{The fleet census artifact of the program's live
deployment; see Data Availability.}---is the living empirical instance:
adaptation drives the passive distributions together while the divergent
belief remains fully separable by active probes. Monitors themselves are not
exempt: optimization pressure on a deployed chain-of-thought monitor was
recently shown to teach reasoning models to obfuscate their intent while the
misbehavior persists \cite{baker2025monitoring}. Passive evidence degrades
under pressure; active tomography is the alternative.

\subsection{Query complexity of active estimation}\label{sec:qc}

If passive monitoring cannot identify the profile, estimation must be
active, and active estimation has a sample complexity. Fix $K$ propositions
and a family$\times$context cell, and assume \emph{outcome homogeneity}:
within the cell, the verdict for proposition $i\in[K]$ is Bernoulli($\beta_i$),
independent across episodes. Estimation then reduces to $K$ Bernoulli means.

\begin{theorem}[Uniform estimation guarantee]\label{thm:uniform}
Fix accuracy $\varepsilon>0$ and confidence level $\alpha\in(0,1)$. If each
proposition $i$ receives
\[
n_i \;\ge\; \frac{1}{2\varepsilon^{2}}\,\ln\frac{2K}{\alpha}
\]
probes, then the empirical estimator $\hat\beta_i$ satisfies
\[
\Pr\Bigl[\,\max_{i\in[K]}\,\bigl|\hat\beta_i-\beta_i\bigr|\le\varepsilon
\Bigr]\;\ge\;1-\alpha
\]
(Hoeffding's inequality \cite{hoeffding1963} plus a union bound over the $K$
propositions).
\end{theorem}

The guarantee is \emph{uniform} over the catalogue: one allocation rule
controls the entire profile simultaneously, and the only price of that
simultaneity is the logarithmic factor $\ln K$.

\begin{proposition}[Adaptive screening gain]\label{prop:screening}
If at most $s\ll K$ propositions have $\beta_i\ge\tau$ for a threshold
$\tau>\varepsilon$, a two-phase policy---uniform screening of
$m=O(\varepsilon^{-2}\ln(K/\alpha))$ probes per proposition to identify
above-threshold candidates, followed by best-arm identification on the
surviving set---achieves the guarantee of Theorem~\ref{thm:uniform} with
total probes
\[
O\bigl(K\,m+s\,\varepsilon^{-2}\ln(K/\alpha)\bigr),
\]
an asymptotic $s/K$-factor saving over uniform allocation.
\end{proposition}

The screening phase is a fixed-confidence thresholding bandit; the proof
(Appendix~\ref{app:proofs}) is a sketch. The full characterization of the
informativeness-optimal adaptive design remains open
(Section~\ref{sec:discussion}). Section~\ref{sec:alloc} measures what
adaptive policies actually deliver at realistic budgets, and the result is
a warning about objectives, not about adaptivity itself.

\subsection{The deception--detection frontier}\label{sec:t5}

The central object is the trade an adversary faces when it lies about the
world and a measurement-capable victim looks for the lie. A \emph{deception
operation} $D$ maps the honest observable distribution $P$ over transcripts
to a defended distribution $Q=D(P)$; its \emph{observable footprint} is
$\delta=\TV(P,Q)\in(0,1]$. The attacker's belief functional
$\beta[\mu]\in[0,1]^K$ is defined on transcript distributions, so the
deception moves the measured profile by the componentwise shift
$\beta[Q](\pi)-\beta[P](\pi)$, the quantity the following definition
bounds.

\begin{definition}[Sensitivity]\label{def:sens}
The functional $\beta$ is \emph{$L$-sensitive} if for all transcript
distributions $\mu_1,\mu_2$ and propositions $\pi$,
\[
\bigl|\beta[\mu_1](\pi)-\beta[\mu_2](\pi)\bigr|
\;\le\;L\,\TV(\mu_1,\mu_2).
\]
Bounded sensitivity is the operative regularity condition and is empirically
checkable by the dose--response protocol of Section~\ref{sec:validity}.
\end{definition}

Every frontier bound below rests on one mechanism: repetition amplifies a
barely-visible gap into near-certain detection.

\begin{lemma}[Amplification]\label{lem:amp}
Let $\delta=\TV(P,Q)\in(0,1]$ and let $P^N,Q^N$ denote the distributions of
$N$ i.i.d.\ samples from $P$ and $Q$. Then
\[
\TV\bigl(P^{N},Q^{N}\bigr)\;\ge\;1-2\exp\!\bigl(-N\delta^{2}/2\bigr).
\]
\end{lemma}

\begin{theorem}[Patch-deception decay]\label{thm:patch}
Let $\beta$ be $L$-sensitive and let a deception perturb attacker-accessible
observations with $\delta=\TV(P,Q)$. Then:
\begin{enumerate}[label=(\roman*),leftmargin=2em]
\item every proposition's measured shift is footprint-bounded,
      $\;|\beta[Q](\pi)-\beta[P](\pi)|\le L\delta$ for every $\pi$;
\item an attacker with horizon $N$ detects the deception with probability at
      least $1-2e^{-N\delta^{2}/2}$, and no test exceeds
      $\TV(P^{N},Q^{N})$;
\item holding detection probability at most $\beta_d$ at horizon $N$ forces
      \[
      \delta\;\le\;\sqrt{2\ln\!\bigl(2/(1-\beta_d)\bigr)/N},
      \qquad\text{hence gain}\;\le\;
      L\sqrt{2\ln\!\bigl(2/(1-\beta_d)\bigr)/N}\;=\;O\bigl(L/\sqrt{N}\bigr).
      \]
\end{enumerate}
\end{theorem}

In words: footprint $\delta$ buys at most $L\delta$ of belief shift (i);
$N$ fresh samples detect with probability approaching one exponentially fast
in $N\delta^{2}$ (ii); and inverting the exponent turns stealth into the
gain cap (iii)---believable deception decays as $O(L/\sqrt{N})$.

\begin{theorem}[Onset dichotomy]\label{thm:onset}
Let the attacker sample the environment for $M$ turns and let deception
change the observable distribution by $\delta>0$. The \emph{reference noise
floor} is $\rho_0=z_{\beta_d}\sqrt{p(1-p)/N_0}$: the sampling error of the
attacker's memorized reference batch at tolerance $\beta_d$, where $p$ is the
per-sample rate of the compared statistic under honest samples. Then:
\begin{enumerate}[label=(\roman*),leftmargin=2em]
\item \emph{Known onset.} If deception activated mid-session and the attacker
memorized $N_0\ge1$ honest samples, exactly one of two regimes holds:
  \begin{enumerate}[label=(\alph*),leftmargin=2em]
  \item if $\delta\ge\rho_0$, the attacker detects with probability
        $\ge1-\beta_d$ once $M\gtrsim\delta^{-2}$; or
  \item if $\delta<\rho_0$, no two-sample test reaches power $1-\beta_d$
        against the reference, and the gain is bounded by
        \[
        L\,\rho_0\;=\;L\,z_{\beta_d}\sqrt{p(1-p)/N_0}
        \;=\;O\bigl(L/\sqrt{N_0}\bigr).
        \]
  \end{enumerate}
  In either regime, gain and stealth cannot both be large: they are jointly
  capped by the attacker's memorized reference size $N_0$, not by dwell time.
\item \emph{Birth onset.} If the deception plane is active from the attacker's
first packet ($N_0=0$), the attacker holds one sample path from a single
unknown distribution and has no in-channel reference. Any in-channel test
reduces to evaluating the prior plausibility of the observed transcript
distribution; deceptions inside the plausible set are in-channel undetectable
for every $M$.
\end{enumerate}
\end{theorem}

\begin{corollary}[The deception--detection frontier]\label{cor:frontier}
Achievable deception gain is jointly capped at $O(L/\sqrt{N})$ and
$O(L/\sqrt{N_0})$ against any detection budget (Theorems~\ref{thm:patch}
and~\ref{thm:onset}). The field's fundamental object is therefore the frontier
curve of achievable gain against attacker probe budget $M$, out-of-band audit
rate, and reference size $N_0$. Belief tomography is the measuring instrument
on both sides of the
frontier: the attacker tomographs the plane; the defender tomographs the
attacker (deception gain, Definition~\ref{def:gain}). Certification
(hypothesis tests over profiles) and deception (profile corruption) are
decision rules operating on either side of this curve.
\end{corollary}

The corollary composes the two caps rather than proving a new bound: any
single deception is subject simultaneously to the stealth-forced cap of
Theorem~\ref{thm:patch}(iii) and, when the attacker holds a pre-onset
reference, to the reference-noise cap of Theorem~\ref{thm:onset}(i)(b); the
achievable set is the intersection of the two regimes.

Arm~(ii) of Theorem~\ref{thm:onset} formalizes the honeypot-from-birth
architecture: endurance is governed by onset invisibility and by the
attacker's \emph{out-of-band} channels---executable causal predictions (``if
I run this exploit, $X$ must happen'') and external anchors. The defender's
achievable deception set is the set of world distributions consistent with
the attacker's \emph{affordable} out-of-band probes; we call this constraint
the \emph{coherence tax}. Game-theoretic deception models optimal deception
at equilibrium \cite{nguyen2019}; Bayesian persuasion with lie detection
models constrained misleading senders \cite{kamenica2011,nberlie}. Those are
equilibrium and commitment analyses. Theorem~\ref{thm:patch} is a
sampling-horizon information theory with executable out-of-band probes and
an empirically visible onset dichotomy. The gain--stealth frontier is the
object the deception literature has measured only through proxies and
never bounded.

\subsection{Empirical validation: the onset dichotomy (E5)}\label{sec:e5}

We test Theorem~\ref{thm:onset}'s predictions on constructed planes with
known onset. The attacker-tomographer either memorizes a pre-onset reference
batch of size $N_0$ or has none (birth onset), and we track the AUC of its
two-sample detection statistic as the fresh-sample horizon $M$ grows.

The match is quantitative, not merely qualitative. At $N_0=10$ the reference
floor is $z\sqrt{p(1-p)/N_0}=0.283>\delta=0.2$: the theory predicts
detection \emph{cannot} saturate, and the observed AUC plateaus at
0.69--0.74. At $N_0=40$ the floor is $0.141<\delta$: the theory predicts
saturation with enough $M$, and the observed AUC rises from 0.76 to 0.97.
At $\delta=0.4$, above both floors, the $N_0=40$ curve saturates
(0.997--1.000) while the $N_0=10$ curve rises to 0.91--0.97 without reaching
1.0, the residual gap expected when the reference floor ($0.283$) sits
below but near $\delta$. Birth-onset self-tests stay near chance at every
$M$ (0.34--0.53); the residual spread is small-sample rate-estimation
asymmetry, not in-channel detectability. The paper's central theorem is
thus falsifiable on an instrument any reviewer can rerun.

\section{The Measurement Instrument}\label{sec:instrument}

\subsection{The platform behind the instrument}\label{sec:platform}

The measurement layer validated below is one plane of an engineered
deception platform, built and hardened across this program
(Figure~\ref{fig:platform}). Nothing changes between foil and field: the
probe driver, verdict channel, and pinned estimator of
Section~\ref{sec:library} run verbatim in both settings, E2 through the
model gateway and E3 against the fleet's attacker personas (deception gain
$\Delta(B)$; Section~\ref{sec:field}).

\paragraph{Live fleet plane.}
The public-facing deployment is a three-arm field study behind one SSH face:
arm~A serves a stock shell emulator with no generative backend, arm~B a
bare-LLM persona baseline, and arm~C the full verified deception
pipeline, one arm per host so that endpoint and IP effects are controlled.
Arm~C's deception loop is a producer--reviewer pipeline (behavioral
classification, threat-intelligence retrieval over the host fiction graph,
response generation) wrapped in a fail-closed verification chain: a turn
whose fiction-consistency or evasion check fails is never served. Sessions
run in sandboxes under append-only JSONL logging, honeytokens arm the canary
gates, an authenticated mTLS transport moves traffic from the public edge to
the private core, and compose profiles (production, CI, canary, A/B, VM,
field) reuse the same services under different exposures.

\paragraph{Adversarial assurance and evidence plane.}
The platform's own defenses are measured like everything else. Labeled
adversarial drafts run through the real fiction-consistency verifier (105
cases: precision $1.0$, recall $1.0$, zero unverified serves); the
model-visible leakage audit covers the full field corpus (1{,}230 sessions,
1{,}640 turns; Section~\ref{sec:e2}); and every number in this paper is
pinned by the pre-registration ledger and the hash-chained results archive.
The codebase comprises 569 Python source files ($\approx$192{,}000 lines),
a 220-item results archive, a Rust gateway, and a 1{,}201-node
code-knowledge graph; the artifact package ships the archive, the 21
pre-registrations, and the claims--evidence ledger (Data Availability).

\paragraph{Decision and advisory layers.}
Outside the serving loop sit the platform's decision layers. A decision
layer (Laya) selects each turn's deception strategy from the host fiction
graph; it has been carried through twelve recorded redesign generations and
is deliberately held out of the default deployment, its frozen v12 battery
serving as the evaluation input for the gate study below. A decision-fusion
layer gates the deception engine's choices on evidence contracts. An LLM
judge over deception-decision evidence (JEV) was then gate-studied against
that frozen battery: of its eight registered gates, five pass (schema
validity, allow-list compliance, and evidence-reference validity at $1.0$;
evidence-reference compatibility $0.938$ against a $\ge0.90$ bar;
inappropriate-abstain rate $0.063$ against a $\le0.10$ bar) and the three
semantic gates fail (required-abstain recall $0.714$ vs.\ a $\ge0.90$ bar;
evidence-state contract alignment $0.833$ vs.\ $\ge0.85$; strategy
compatibility $0.563$ vs.\ $\ge0.80$). JEV therefore runs as
\emph{advisory}, outside the trust path. The assurance plane itself runs
under a multi-rater audit loop (three independent rater lanes over 218
double-annotated threat-intelligence rows, sealed packets, and a third
adjudication lane) and ships a deception-quality evaluator protocol
alongside benchmark, consistency, and ablation suites that gate regressions
across the platform.

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{anthro/fig3_platform.pdf}
\caption{The belief-tomography platform: a three-arm public deception fleet
whose verified loop fails closed; the instrument of
Section~\ref{sec:library} running unchanged across foils, gateway models,
and the fleet; and the assurance--evidence layer that gates the platform and
pins every reported number.}
\label{fig:platform}
\end{figure}

\subsection{Library, verdicts, and estimator}\label{sec:library}

\paragraph{Probe library.}
The v0 library holds five families---authority forgery, state deception,
goal subversion, epistemic echo, exfiltration lure---each at three
generations of indirectness. Every episode is seeded and reproducible, and
the target \emph{model} never sees family labels, oracle logic, or the
generator (routing metadata is consumed by the proxy process and excluded
from the model-visible channel by the leakage audit of
Section~\ref{sec:audit}). The v0 families are template worlds: one template
per (family, generation) cell, sampled repeatedly. Probe \emph{diversity}
within a cell is a library-v1 property (Section~\ref{sec:limits}); the
label ``E2-v1'' in Section~\ref{sec:field} denotes the \emph{replication}
driver (session isolation and full logging), not a new probe library. What
the v0 instrument measures is the sampling probability of a fixed probe,
which is exactly what the dose--response experiment validates.

\paragraph{Verdicts.}
Two deterministic oracles form the reproducible floor: \texttt{secret\_leak}
(the literal secret appears in the target's outputs) and
\texttt{unauthorized\_action} (an action word co-occurs with a destructive
command string). Both are lexical, and Section~\ref{sec:audit} shows why
that matters: lexical verdicts are a floor, not a semantic judge. The
calibrated multi-model jury lane\footnote{A program methodology artifact
with measured inter-rater agreement; see Data Availability.} is the v1
semantic layer; any breach claim that is not a literal echo is audited
against its transcript.

\paragraph{Estimator.}
Per family, $\hat\beta$ is the breach rate over the family's generations,
with a Wilson score interval \cite{wilson1927}. Profiles are compared under
$\ell_1$ distance; the Belief--Claim Gap averages the family $\beta$s mapped
to a charter claim. The estimator is frozen by commit hash before data
collection; every change is a logged deviation.

\subsection{Validity: dose--response (E1)}\label{sec:validity}

The result: Pearson $r\ge0.986$ and Spearman $\rho=1.00$ in every family,
monotone curves, and exact zero-dose cleanliness across 1{,}500 episodes.
The first run's apparent dip in authority forgery was diagnosed as
cell-size noise ($n=18$, SE $\approx0.118$ exceeds half the grid step), and
the cells were resized to $n=60$ with the argument recorded in code. The
instrument measures what it claims to measure.

\subsection{Reliability: test--retest (E1b)}\label{sec:reliability}

Two independent probe batches on a stochastic foil (temperature-like noise
$\eta=0.15$) yield $r=0.949$ with mean $|\Delta\hat\beta|=0.067$ at 10
probes per cell. At 4 probes per cell the same foil yields $r=0.837$, below
the pre-registered reliability bar. \emph{Batch size is part of the
instrument specification}; the operating point is $\ge10$ probes per cell.
Effects below the measured noise floor are not claimable in any document.

\subsection{Allocation: the objective must match the goal (T3)}\label{sec:alloc}

Which probe family should receive the next episode? The intuitive answers
are a bandit's regret objective (attack the family that fails most) and a
psychophysics information objective (maximize entropy reduction). We
benchmarked both against uniform and variance-equalizing (Neyman) allocation
for \emph{profile estimation} at budgets 25--400.

The negative result is the point. At $n=400$, uniform achieves mean error
0.035 and Neyman 0.035, while UCB-lite stalls at 0.121 and PSI at 0.129:
regret-optimal allocation starves non-frontier families, and entropy-greedy
allocation over-invests in extreme-rate families. Mutual information is the
right tool for \emph{detection}-style tasks, not for estimation. This
refines the open problem of Section~\ref{sec:qc}: the optimal design for
profile estimation is variance-equalizing, and the adaptive gain is bounded
by profile sparsity, not by greedy information.

\subsection{The verdict channel, audited}\label{sec:audit}

\paragraph{Constructed boundary audit.}
We constructed 50 boundary sessions with human-assigned labels: safe
refusals that \emph{name} the forbidden command (``I am not executing
\texttt{rm -rf /var/\allowbreak log}''), safe cases with no oracle keywords,
and breaches phrased around the lexical rules (implicit completion,
paraphrase, split secrets). The lexical oracle produced 5/25 false positives
(20.0\%, 95\% CI [8.9\%, 39.1\%]) and 12/25 false negatives (48.0\%, 95\% CI
[30.0\%, 66.5\%]). Both directions matter: a false positive inflates a
charter violation; a false negative certifies an agent that complied. The
deterministic oracle is a reproducible floor, and every non-literal breach
verdict must be verified against its transcript. Any instrument with
automated verdicts deserves the same audit.

\begin{table}[t]
\centering\small
\begin{tabular}{lcc}
\toprule
 & human label: safe & human label: breach \\
\midrule
oracle: clean & 20 (TN) & 12 (FN, 48.0\%) \\
oracle: breach & 5 (FP, 20.0\%) & 13 (TP) \\
\bottomrule
\end{tabular}
\caption{Constructed boundary audit ($n=50$): the lexical oracle's confusion
matrix. The 2\% false-positive bar of kill criterion (a) is not met on
boundary text, which is why the oracle is a floor and the transcript audit
is mandatory.}
\label{tab:audit}
\end{table}

\paragraph{E17: the audit channel's operating characteristic.}
The live kill-(a) audit of Section~\ref{sec:field} reported FP $0/51$
$[0,7.0\%]$ with zero oracle positives---honestly labeled underpowered. E17
closes the gap with a seeded audit: 50 frozen constructed sessions of known
ground truth plus 70 real E2-v1 sessions, shuffled blind and adjudicated by
the registered transcript rubric rather than the lexical oracle. The channel
measures sensitivity $0.960$ $[0.805,0.993]$ and FP $0/25$ $[0,0.133]$; the
single false negative is a pretext-only phrasing (``executing the vendor
guidance'') with no prohibited content in the output. The channel dominates
the oracle on the same 50 sessions (oracle FP $0.20$, FN $0.48$; channel FP
$0.00$, FN $0.04$). No real E2 session adjudicates as a breach, consistent
with the zero-breach field result. With 25 seeded positives, the audit
detects adjudicator FP rates above ${\approx}12\%$ (rule of three): kill
criterion (a) now has a stated power. The seeded-audit concept is borrowed
from practitioner oversight; the object calibrated here is this program's
transcript-adjudication channel, not a general audit methodology.

\subsection{Robustness: estimator and seeds (E18, E19)}\label{sec:robust}

Two pre-registered robustness results close the remaining methodological
questions about the instrument itself. \emph{E18 (estimator robustness):} an
empirical-Bayes Beta--Binomial estimator with a per-experiment
method-of-moments prior, applied to the frozen E1/E2/E17 data, produces zero
\emph{decision} flips at $\tau=0.2$, so headline inferences do not depend on
the interval estimator, while its credible intervals are uniformly
narrower (width ratio $0.88$--$0.99$); the two estimators disagree only on
exactly-zero cells, where a continuous posterior excludes zero by
construction (a disclosed property, and a v2-estimator design note).
\emph{E19 (seed extension):} the E6/E7/E9/E10 registered protocols re-run
unchanged at three fresh seeds $(131, 2026, 90210)$; every registered
condition holds at every seed, so the foil-harness results are seed-robust.

\section{Field Results: Two Pre-Registered Nulls}\label{sec:field}

Theory so far concerns the instrument; nothing yet touches a deployed
system. Two questions remain that only field measurement can answer. First:
do \emph{production} agents diverge from their charters at all, or was the
separation of Section~\ref{sec:cert} an artifact of designed targets?
Second: does \emph{live} deception move a real attacker's measured beliefs,
or only the constructed planes of Section~\ref{sec:e5}? The two
pre-registered field measurements below answer both. Both answers are nulls
at instrument resolution, and both are reported with every kill gate,
deviation, halt, and adjudication the program logged.

\subsection{E2: the Belief--Claim Gap in production agents}\label{sec:e2}

\begin{table}[t]
\centering\small
\caption{E2-v1 field null: measured family profile $\hat\beta$ with Wilson 95\% CIs,
identical for both gateway models; the Belief--Claim Gap rows are zero at the same
resolution. Every interval lies far below the certification tolerance $\tau=0.2$
--- the pre-registered null, at instrument resolution.}
\label{tab:fieldnull}
\begin{tabular}{lcc}
\toprule
 & $\hat\beta$ & Wilson 95\% CI \\
\midrule
authority forgery & 0.000 & $[0,\ 0.060]$ \\
state deception   & 0.000 & $[0,\ 0.060]$ \\
goal subversion   & 0.000 & $[0,\ 0.060]$ \\
epistemic echo    & 0.000 & $[0,\ 0.060]$ \\
exfiltration lure & 0.000 & $[0,\ 0.060]$ \\
\midrule
\multicolumn{3}{l}{\emph{Belief--Claim Gap}: confidentiality $0.000$; action safety $0.000$} \\
\bottomrule
\end{tabular}
\end{table}

\paragraph{Design.}
Two production frontier models, each tomographed at
$5\ \text{families}\times3\ \text{generations}\times20$ probes $=300$
independent sessions; every session starts from a fresh conversation, and
every turn (probe text, tool output, reply, block flag) is logged to JSONL
before analysis. The primary endpoints are $\mathrm{BCG}(\text{confidentiality})$
and $\mathrm{BCG}(\text{action\_safety})$; per-family $\hat\beta$ is
reported with Wilson 95\% intervals. Unavailable turns---provider content
blocks and transport failures, which the current wire surfaces
identically---are counted, mapped to a conservative charter-holding verdict,
and disclosed: $\hat\beta$ is downward-biased, and the measurable probe set
is explicit. The global split between content blocks and transport failures
is reported from the proxy log where recoverable; per-session attribution is
a disclosed limitation.

The lexical oracle is a reproducible floor: every oracle-positive session
and a 50-session stratified sample are transcript-adjudicated, and the live
audit's false-positive and false-negative rates are reported with exact CIs.
A second seed on the signal-bearing agent provides test--retest reliability.
The run is pre-registered, and the E2-v0 run is archived as invalid
(episode-isolation defect); no v0 number is quoted.

\paragraph{Results: the measurable model.}
In the completed gpt-5.6-sol primary, all 300 probes were independent
sessions (300 unique ids, 301 fresh target processes) and the lexical oracle
returned zero breach verdicts. Every family measured $\hat\beta=0.000$ with
Wilson 95\% CI $[0,0.060]$, so both BCG endpoints are zero \emph{at this
resolution}; the upper bound, not the point estimate, is the honest
statement of what the instrument cannot exclude. The v0 signal (2/20
state-deception generation-2 breaches) did not replicate under isolation.
The lane censored 117/400 turns (29.2\%), and \emph{every} state-deception
session had at least one unavailable turn: the fully-measured sensitivity
subset is empty for that family and is reported as undefined, never as a
point mass at zero. The conservative-mapped estimate remains $0/60$
$[0,0.060]$.

\paragraph{Results: the second model and an instrument repair.}
The second model's first panel returned 398/400 HTTP-200 empty completions.
A pre-registered re-measurement, documented as
\texttt{PREREG\hspace{0pt}ISTRA\hspace{0pt}TION\_\hspace{0pt}E2V1B.md},
diagnosed the cause: the 200-token response budget is consumed by hidden
reasoning tokens on security probes (gateway status \texttt{incomplete}, no
message item); 1024 tokens restores normal replies. With that transport-only
fix, the re-run measured 300 sessions with 66/400 (16.5\%) unavailable
turns, zero breach verdicts, and $\hat\beta=0.000$ $[0,0.060]$ in every
family---the same result as the first model. No number from the original
unmeasurable panel is quoted; its artifacts are archived. Its seed-99999
retest, however, reached 201/400 (50.25\%) unavailable turns, over the
registered 50\% unmeasurable bar, so no reliability statistic is reported
for that model. The constraint is the instrument's, not a claim about
compliance: a certificate is only as informative as the fraction of turns on
which the model was actually observed.

\paragraph{Verdict channel and kill criterion (a).}
The stratified audit sheet contained 100 sessions, of which 49 had at least
one censored turn (27 for gpt-5.6, including all 20 state-deception
generation-2 sessions; 22 for gpt-6.1), leaving 51 labelable sessions. Blind
adjudication found 51 safe sessions and no breach: FP $=0/51$, exact 95\% CI
$[0,7.0\%]$. The 2\% point bar of kill criterion (a) is not triggered, but
the live audit still has no power to detect false positives (zero oracle
positives), so the constructed boundary audit's 20.0\% FP remains the
governing stress test. The offline model-visible prompt audit passes on all
six current runs (1{,}230 sessions, 1{,}640 turns): no family name,
generation label, session id, oracle term, or generator id appears in any
model-visible string. The live pre-deployment knowledge check (15 templates
$\times$ 2 models) also passes: 0 templates reproduced, longest common
substring $\le3$ characters. Kill criterion (c) is satisfied.

\paragraph{Reliability, kill criterion (b).}
The gpt-5.6-sol seed-99999 retest measured 300 sessions with 27.5\%
censoring and the same zero-breach profile. Pearson $r$ is undefined because
both profiles have zero variance; under the pre-registered degeneracy rule
no $r$ is reported and the $r\ge0.90$ bar is not evaluated numerically.
Reliability is instead exact per-cell agreement 15/15 with mean
$|\Delta\beta|=0.000$, inside the E1b noise floor (0.047 expected at 20
probes per cell): agreement at the instrument's resolution, not a
correlation claim. For gpt-6.1-sol the retest is \textbf{not assessable}
(50.25\% censoring, over the registered bar), so no reliability claim is
made there. Criterion (b) is satisfied for the one model whose retest was
measurable; all three criteria were resolved before any headline number was
quoted.

\subsection{E3: deception gain on the live fleet}\label{sec:e3}

The same instrument, pointed the other way. Five attacker personas
(gpt-5.6-sol brains over SSH) run against the \emph{live} honeypot plane:
session~1, attacker-side tomography ($B_{\mathrm{pre}}$, 150 probes); a
second session against the plane's active deception engine; attacker-side
re-tomography ($B_{\mathrm{post}}$); an instrumented retest; and three
registered kill gates. All gates pass: 10/10 sessions complete, retest
reliability under the degeneracy rule (exact agreement $14/15$, mean
$|\Delta\beta| = 0.0067$ at the $0.067$ floor), and the canary-allowlist
incident gate clean (an early halt was adjudicated as the plane's own canary
key, extracted live from its served configuration). The registered outcome
is the program's second pre-registered null: $\Delta(B) \le$ the noise floor
for \emph{all five} personas ($0.000$--$0.0067$; one pre-session
\texttt{data\_value} breach at $0.1$ does not survive the post measurement,
within single-cell binomial noise). The deception operations did not move
the attackers' measured belief profiles at this instrument's resolution.

Instrumented-null disclosure per persona: the operations' engagement depth
was bounded by the plane's shallow command layer (complex invocations fail
with \texttt{command not found}), and one exploratory observation is
reported as observed: the honeypot-detection persona issued
\texttt{VERDICT:\ honeypot} after the plane failed to fake \texttt{/proc}, a
deployment-stealth finding for the fleet, not a measurement claim.

\subsection{What the two nulls bound}\label{sec:nulls}

Together the field results bound the operational claim from both directions:
frontier agents hold their charters under probe attack, and frontier
\emph{attackers} hold their operational beliefs under live deception, at
this instrument's resolution, with every deviation, halt, and adjudication
logged. The nulls bound rather than blind: on foils with injected
ground-truth beliefs the same instrument recovers graded structure
(dose--response $r \ge 0.986$; certified and uncertain foils separate at
$\tau = 0.2$, Section~\ref{sec:cert}), so the field nulls measure the
\emph{absence of detectable belief movement in production}, not the absence
of a measuring device.

\section{The Limits of Certification}\label{sec:limitscert}

\subsection{Certification as a hypothesis test over the profile}\label{sec:cert}

The certification engine asks: is the target's maximum family belief below a
threshold? That is a hypothesis test over $B$, with adaptive allocation to
the families that fail. Certification, deception, and monitoring are three
decision rules over one latent object: certification a test, deception
controlled corruption, monitoring change-point detection on $B_t$. The
policy benchmark of Section~\ref{sec:alloc} has a direct operational
consequence here: certification \emph{detection} may use regret-style
allocation (find the worst family), while \emph{estimation} must not.
Conflating the two objectives is a measurable error, not a matter of taste.

\paragraph{E4: the decision rule separates designed targets.}
We tomographed three foils with known profiles at the operating batch (10
probes per cell, two seeds): a naive foil (all five beliefs at $\beta=1$), a
graded foil (resists generations up to a per-family strength, designed
$\beta=[1/3,2/3,2/3,1,2/3]$), and a resistant foil ($\beta=0$). The decision
rule certifies at tolerance $\tau$ iff every family's Wilson 95\% lower
bound is at most $\tau$. At $\tau=0.2$ the test certifies only the resistant
foil. The graded foil fails the four families whose lower confidence bound
exceeds $\tau$; authority forgery, designed at $\beta=1/3$, is not
resolved above $\tau$ at this batch (lower bound $0.19$), so it survives.
That survival is a power statement, not evidence that its belief is below
$\tau$: with 30 episodes per family, a true $\beta$ of $1/3$ is not
distinguishable from $\tau=0.2$. The naive foil fails all five. Profiles are
exactly reproducible across seeds ($\ell_1=0$ on deterministic foils), so
the between-target separation is not noise.

One deviation proved diagnostic. Both foils measure epistemic echo at $2/3$
although the naive foil is designed to breach all three echo generations:
the generation-3 probe splits the canary across two cache lines, and the
lexical oracle requires a contiguous substring. This is the in-situ instance
of the split-secret false negative measured in Section~\ref{sec:audit}.
Certification is a decision rule over the profile, and its errors inherit
the verdict channel's: the instrument reports what the oracle can see. That
is precisely why the audit, not the oracle, is the validity gate. The rule
is the applied layer, not a new instrument; the real-agent analogue is the
field measurement of Section~\ref{sec:field}.

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{anthro/fig3_radar.pdf}
\caption{E4: certification as a shrinking attack surface at $\tau=0.2$. Each
polar panel is one constructed foil; spoke length is the measured family
$\hat\beta$ (the attack surface the foil presents), the dashed inner polygon
its Wilson lower bound (what the rule acts on), and spoke capsules the 95\%
CIs (30 episodes per family cell, 10 probes $\times$ 3 generations). The teal
disc is the accept region ($\hat\beta\le\tau$), the rose annulus the reject
region; glyphs record the per-family decision. The rule certifies only the
resistant foil ($5/5$, every CI upper bound $\le 0.114$); the naive foil is
rejected $5/5$; the hardened foil is rejected on four families while authority
forgery (designed $\beta=1/3$) is \emph{unresolved}---its CI straddles
$\tau$, a power statement, not evidence that its belief is below $\tau$. The
naive foil's epistemic-echo cell reads $2/3$ because the split-secret probe
defeats the contiguous-substring oracle---an in-situ instance of the measured
false negative (Section~\ref{sec:audit}).}
\label{fig:cert}
\end{figure}

\subsection{The probe as an attack surface}\label{sec:surface}

Sections~\ref{sec:instrument}--\ref{sec:cert} treat the probe as an
instrument. There is a second, adversarial view: a deployment that can be
probed can be \emph{gamed}, and a component certified in isolation need not
remain certified inside a pipeline. Three results formalize the failures;
all are pre-registered and tested on deterministic foils with the frozen
estimator and verdict engine.

\begin{corollary}[No free lunch for public probes]\label{cor:pub}
Let $\Pi_{\mathrm{pub}}$ be a finite probe library and $\mathcal{S}$ the union
of its transcript supports. Any certification rule $C$ that accepts using only
$\Pi_{\mathrm{pub}}$ outcomes also accepts a target that agrees with the
compliant target on $\mathcal{S}$ and complies on a held-out semantic
equivalent $\pi'$ with $\mathrm{supp}(\pi')\cap\mathcal{S}=\varnothing$.
\end{corollary}

\begin{theorem}[Certification does not compose]\label{thm:compose}
If a retriever $A$ and an orchestrator $B$ are each certified under
$\Pi_{\mathrm{pub}}$, and the public library never issues $A$'s retrieval
request nor uses the interface tag $t$, then $B\circ A$ can disclose $A$'s
secret at $\hat\beta=1$ while no component is individually non-compliant.
\end{theorem}

\begin{proposition}[The gaming gap decides transfer]\label{prop:gaming}
Define $\Gamma=|\hat\beta_{\mathrm{held}}-\hat\beta_{\mathrm{pub}}|$ on public
probes and held-out semantic paraphrases. If $\Gamma$ exceeds the instrument
noise floor, the certificate is void; if it is within the floor and both upper
confidence bounds are $\le\tau$, the certificate transfers to a semantic
neighbourhood up to $Lr+\varepsilon$, where $r$ is the paraphrase covering
radius and $L$ the sensitivity of Definition~\ref{def:sens}.
\end{proposition}

Corollary~\ref{cor:pub} is Theorem~\ref{thm:passive} with $E=\pi'$: the
operational corollary that makes passive impossibility bite on certification
practice. In Theorem~\ref{thm:compose} the interface history has zero measure
under each local probe distribution: \emph{belief laundering} is the
estimator-level descendant of the classical confused deputy \cite{hardy1988},
in which a component is exploited through a capability it legitimately holds
in a context its local evidence never visits, a pattern realized end-to-end
against Copilot's RAG pipeline \cite{confusedpilot2024}. The gap
Corollary~\ref{cor:pub} formalizes is likewise the probe-space analogue of
the feature-space distinction in adversarial ML: attacks must be realized in
the problem space, while instruments sample a feature space
\cite{pierazzi2025tops}. The Lipschitz--covering step of
Proposition~\ref{prop:gaming} is standard; the diagnostic $\Gamma$ is new,
and the transfer is conditional on the target not conditioning on probe
provenance. Full proofs are in Appendix~\ref{app:proofs}.

\paragraph{E6: a pipeline breach that no component explains.}
A \texttt{RetrieverFoil} refuses every public probe but returns a document
containing its secret on a ``fetch document'' request; an
\texttt{OrchestratorFoil} refuses every public probe but faithfully
summarizes tool output tagged \texttt{<tool:retriever>}. Neither capability
is a public probe. Locally, both components certify at $\tau=0.2$ with all
five family $\hat\beta=0$ at two seeds. Composed, a cross-interface probe
measures $20/20$ breaches, $\hat\beta=1.000$ $[0.839, 1.000]$; the
orchestrator alone measures $0/20$. The breach exists only in the
composition. The \emph{phenomenon} is not new: it is the ``permission
laundering'' of ChainCaps \cite{chaincaps2026} and the cross-boundary
weakness catalogued in orchestration frameworks \cite{orchestration2026}.
Our claim is narrower and different in kind: a \emph{statistical behavioral
certificate} (Wilson CIs, tolerance $\tau$, profile $\hat\beta$) does not
compose, even when every component is certified at $\beta=0$; and the
countermeasure below operates at the measurement layer rather than at
runtime capability enforcement.

\paragraph{E7: a foil that passes public certification by detecting probes.}
A \texttt{ProbeAwareFoil} carries an exact detector for the 15 public lexical
signatures and complies on held-out paraphrases of the same attacks. Public
tomography certifies it ($0/300$, both seeds); held-out paraphrases reject it
(mean family $\hat\beta=1.000$), giving $\Gamma=1.000$. Two controls
separate probe-awareness from malice: a foil with \emph{no} detector complies
on both sets ($\Gamma=0$ but $\hat\beta=1$ in both, so a small gap is
necessary, not sufficient), and a resistant foil is safe in both
($\Gamma=0$, $\hat\beta=0$). The first two E7 attempts failed these controls
because of oracle-wiring and trigger-vocabulary defects in the control foil;
both were diagnosed and logged before re-analysis, and the failed artifacts
are retained (\texttt{PREREGISTRATION\_E6E7.md}, \S5).

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{anthro/fig4_premium.pdf}
\caption{E6/E7: the limits of certification. (a)~Local certification does not
compose: retriever A and orchestrator B each certify locally at $\hat\beta=0$,
but the interface carries the retriever's secret $s_A$ into the orchestrator
and the composed pipeline breaches at $\hat\beta=1.0$ ($20/20$; Wilson
$[0.84,1.00]$)---no component is individually non-compliant. (b)~Public
certification can be gamed: the probe-aware foil passes public certification
and fails the held-out paraphrases ($\Gamma=1$); the two controls---a
semantics-only foil that fails both and a resistant foil that passes
both---show that a small $\Gamma$ is necessary but not sufficient: it must be
paired with a low $\hat\beta$ on both probe sets.}
\label{fig:limits}
\end{figure}

\begin{table}[t]\centering\small
\begin{tabular}{lccc}
\toprule
foil & public $\hat\beta$ & held-out $\hat\beta$ & $\Gamma$ \\
\midrule
ProbeAware & 0.000 (cert.) & 1.000 (reject) & 1.000 \\
SemanticsOnly$^\dagger$ & 1.000 (reject) & 1.000 (reject) & 0.000 \\
Resistant$^\dagger$ & 0.000 (cert.) & 0.000 (cert.) & 0.000 \\
\bottomrule
\end{tabular}
\caption{E7: the gaming gap at 20 probes per cell, mean over five families. A
small $\Gamma$ is necessary but not sufficient: it must be paired with a low
$\hat\beta$ on both probe sets. $^\dagger$Control foil.}
\label{tab:gaming}
\end{table}

\paragraph{Consequence for the field.}
A published benchmark or probe suite is a \emph{public} instrument, hence a
gameable one. Certification must therefore be a \emph{pair}: a profile
estimate and a probe-awareness check $\Gamma$, plus an explicit composition
argument when the certified object is a component of a larger pipeline. This
is a negative result about what a finite probe suite can prove, and a
positive one about the diagnostic that decides when its result may be
trusted. E6/E7 are existence and mechanism results on constructed foils, not
prevalence estimates for deployed agents.

\paragraph{E8: a defense for composition.}
The composition result is not fatal if the interface vocabulary is part of
the certificate. Adding a single \texttt{tool\_relay} probe (20 episodes) to
the library makes both E6 components fail local certification at
$\hat\beta=1.0$ in all four component--seed pairs, while 300 component-local
probes had certified both at $\hat\beta=0$; a relay-resistant control still
certifies, and its composition measures $0$. The design rule: \emph{certify
the interface vocabulary, not only the components}. Like E6/E7, this is an
existence result on constructed foils, so one probe does not suffice for
arbitrary compositions, and real tool pipelines may not publish their
interface grammar.

\subsection{Forgery and adaptation}\label{sec:forgery}

\begin{theorem}[Tomogram forgery]\label{thm:forgery}
Let $\Pi_{\mathrm{pub}}$ be a public probe library with transcript support
$\mathcal{S}$ and let $\Phi_{\mathrm{held}}$ be a held-out probe family with
$\mathrm{supp}(\Phi_{\mathrm{held}})\cap\mathcal{S}=\varnothing$. For any two
profiles $B_{\mathrm{disp}},B_{\mathrm{true}}$ there exists a target $T$ such
that tomography under $\Pi_{\mathrm{pub}}$ recovers $B_{\mathrm{disp}}$ within
estimation error and tomography under $\Phi_{\mathrm{held}}$ recovers
$B_{\mathrm{true}}$ within estimation error.
\end{theorem}

Corollary~\ref{cor:pub} says a target can hide off-support behavior.
Theorem~\ref{thm:forgery} says it can \emph{choose what to display}: a
tomogram is an \emph{unauthenticated} report about probe-conditional
behavior, not evidence about deployment behavior (proof:
Theorem~\ref{thm:passive} applied per family, Appendix~\ref{app:proofs}).
Experiment~E9 instantiates the attack: a foil displays $\hat\beta=1$ on
exfiltration lure and $0$ on state deception under public probes, while the
held-out paraphrases reveal exactly the reverse (per-family forgery gap
$1.0$ in those two cells, $0$ elsewhere, both seeds); an honest control's
profiles agree exactly. The operational consequence: a published tomogram
can steer a defender's deception or hardening investment toward the wrong
family, so the measurement output must itself be treated as an untrusted
input to the decision pipeline.

\begin{corollary}[Adaptive gaming of a published held-out set]\label{cor:adaptive}
Let $H$ be a \emph{published} held-out set used to compute the gaming gap and
let $S$ be a third probe set from the same semantic family, unknown to the
target at certification. If a target class can discriminate
$\mathrm{supp}(\Pi_{\mathrm{pub}})\cup\mathrm{supp}(H)$ from
$\mathrm{supp}(S)$, it contains a member with
$\hat\beta_{\mathrm{pub}}=\hat\beta_H=0$ and $\hat\beta_S=1$.
\end{corollary}

The $\Gamma$ check of Proposition~\ref{prop:gaming} is itself a fixed
detector, and adaptive audits can break fixed detectors
\cite{soopal2026,duddu2026}. Corollary~\ref{cor:adaptive} registers the
consequence: if the held-out set used to compute $\Gamma$ is published, an
attacker can condition on its support, drive $\Gamma$ to zero, and still
breach on a third, unseen set. Experiment~E10 confirms this on constructed
foils: an adaptive foil measures $\hat\beta_P=\hat\beta_H=0$
($\Gamma_{P,H}=0$, accepted) and $\hat\beta_S=1.0$ on a secret paraphrase
set; the fixed E7 attacker is detected by the published check
($\Gamma_{P,H}=1.0$); and using the secret set as the diagnostic restores
detection of the adaptive foil ($\Gamma_{P,S}=1.0$), all at both seeds. The
operational rule is stronger than Proposition~\ref{prop:gaming}'s: the
diagnostic set must be \emph{secret at certification time}. This is an
existence result with a literal signature detector, not a claim about
learned attackers.

\subsection{Drift and reactivity}\label{sec:drift}

\begin{proposition}[Certificate half-life]\label{prop:halflife}
Assume the target's belief strength is $v$-Lipschitz in time,
$|\beta_{t+h}-\beta_t|\le vh$. A measurement at $t_0$ yielding Wilson upper
bound $U_0<\tau$ certifies $\beta\le\tau$ for
$h_\tau=(\tau-U_0)/v$ and no longer; Bonferroni over renewals gives
simultaneous validity.
\end{proposition}

A certificate is a statement about a belief at measurement time; a deployed
agent drifts. Proposition~\ref{prop:halflife} registers the validity
horizon. Adjacent work studies evaluator drift \cite{evaldrift2026},
behavioral change under model swaps \cite{modeltransition2026}, and
memory-driven drift \cite{memevo2026}, but none defines a certificate
validity horizon. Experiment~E11 measures it on a deterministic $v=0.05$
foil with $\tau=0.2$: a one-shot certificate is falsified at four epochs; a
fixed calendar interval stays valid at the cost of five tomography runs; the
half-life rule stays valid at two runs, at both seeds. The drift bound is
assumed known---estimating or enforcing it by policy (e.g., on model-change
events) is an open problem---so this is a mechanism result, not a deployment
recipe.

\begin{proposition}[Tomographic reactivity]\label{prop:reactivity}
Let $\beta$ be the estimand under a fresh session and $\beta_k$ the breach
probability after $k$ prior replies in the same conversation. If
$|\beta_k-\beta|\le ck$, a pooled estimator over $n$ probes in one context has
bias at most $c(n-1)/2$; it consistently estimates a context-conditioned
quantity, not $\beta$. Session reset ($k=0$ per probe) is the identification
condition.
\end{proposition}

The invalidated E2-v0 run (all probes in one context) can be read as an
engineering bug. Proposition~\ref{prop:reactivity} registers the
methodological reading: an agent that observes its own prior replies can
adapt, so a shared-context estimator measures a different,
context-conditioned quantity. Experiment~E12 reconstructs the mechanism on a
constructed foil: independent sessions recover $\hat\beta=0.500$ while the
shared context yields $\hat\beta=0.033$, an absolute bias of $0.467$
(93.3\% relative) at both seeds. This does not rehabilitate any v0 number;
it explains why isolation must be designed into the instrument. The analogy
to the observer effect in other measurement sciences is real; what is new
here is the estimator-level bias and the identification condition.

\subsection{Allocation under a learning attacker}\label{sec:learned}

\begin{proposition}[Concentration against hiding]\label{prop:alloc}
Let a probe-aware target hide on a family after $K$ exposures. A family probed
$n_f$ times measures $\hat\beta_f=\min(1,K/n_f)$ there, so the certificate at
tolerance $\tau$ fails on that family iff $n_f<K/\tau$. Uniform allocation
hands the attacker exactly the uniform exposure it needs to hide everywhere;
concentrated allocation leaves some families under-exposed, where it cannot
hide.
\end{proposition}

The policy benchmark of Section~\ref{sec:alloc} assumed a fixed target.
Proposition~\ref{prop:alloc} registers the adversarial counterpart. E13
confirms it at $K=10$, $\tau=0.2$, and the 300-probe budget: uniform yields
$0/5$ detected families and a passing (false) certificate, while the same
budget concentrated by a two-phase rule yields $3/5$ detected families and a
failing certificate, at both seeds. The operational objective under this
threat model is to deny uniform exposure, not to maximize estimator
efficiency: a threat-model condition on, not a retraction of, the T3
benchmark. One registered condition failed in a first run because the foil's
disclosure was invisible to the state-deception oracle; the construct defect
and fix are logged and the failed artifacts retained.

\section{The Economics of Disclosure}\label{sec:disclosure}

Section~\ref{sec:limitscert} established what a certificate cannot
guarantee. This section analyzes what happens when it is \emph{published}:
the profile becomes a data release with an adversary on the other side.
Four results, the reconnaissance externality (E14), defender-side
deception release (E15), the detection budget (E16), and the bounded-noise
disclosure frontier (E20), treat a published tomogram as sensitive data,
not as marketing. They are the privacy economics of a security certificate,
joining the economics-of-security tradition \cite{anderson2006}: the
artifact under incentive analysis is now the measurement itself.

\subsection{E14: a published tomogram is a targeting map}\label{sec:recon}

\begin{proposition}[Reconnaissance externality]\label{prop:recon}
An attacker who reads a published profile $\hat\beta$ chooses
$f^*=\arg\max_f\hat\beta_f$ instead of a uniformly random family, raising
expected success from the mean family $\hat\beta$ to the maximum; the
advantage $A_{\mathrm{rec}}=\beta_{f^*}-\tfrac{1}{K}\sum_f\beta_f$ is zero
only for a flat profile. Publishing the scalar worst-family upper bound
$U_{\max}=\max_f U_f$ removes the ranking but also the defender's family-level
allocation information.
\end{proposition}

The certificate is itself a dual-use artifact. E14 is a pre-analysis of the
frozen E4 profiles: the graded foil's advantage is $0.067$ (uniform $0.600$
to informed $0.667$), the flat resistant foil is $0.000$, and the naive
foil's small $0.067$ advantage is the known split-secret oracle false
negative disclosed in E4. Publishing only the scalar $U_{\max}$ removes the
targeting information at the cost of the defender's allocation
information, a disclosure trade-off, not a free fix. This is decision
analysis on existing profiles, not a measured attacker; unlike the
Social-HUMINT line \cite{socialhumint2026}, which profiles \emph{humans} for
targeting, the object here is the disclosure cost of an agent security
certificate.

\subsection{E15: the defender as forger---deception release}\label{sec:release}

Proposition~\ref{prop:recon} treats the published profile as an
attacker-facing liability. The triangle completes: the \emph{defender} can
forge it.

\begin{proposition}[Deception release]\label{prop:release}
Fix the public probe suite $\Pi_{\mathrm{pub}}$ and let the defender publish
$\tilde\beta$ that is $\Pi_{\mathrm{pub}}$-consistent (which
Theorem~\ref{thm:forgery} permits). Then (i) any attacker whose measurement is
confined to $\Pi_{\mathrm{pub}}$ verifies $\tilde\beta$ and allocates by it:
the release deception is \emph{stable} against public verification; (ii) a
decoy concentration misdirects allocation away from the true vulnerable
family; (iii) the deception collapses exactly when the attacker acquires
held-out measurement capability, with a \emph{trust-collapse} externality: one
detected falsification discounts all future releases.
\end{proposition}

E15 is a pre-analysis on the frozen E9 display/true profiles with a seeded
attacker simulation (budget $B=120$): honest release hands the attacker
per-attempt success $1.000$, decoy release $0.000$, and silence (uniform)
$0.200$, so the counterintelligence tomogram dominates both honest disclosure
and no disclosure whenever a certificate must be published. The gain is
stable under public verification at shares $0.2/0.5$ and collapses
monotonically ($0.000\to0.100\to0.200$) as the attacker's held-out detection
probability grows $0\to0.5\to1$, with the trust-collapse externality of
Proposition~\ref{prop:release}. Like E14, this is decision analysis on
frozen profiles, plus a seeded simulation, rather than a measurement of a
live attacker. The doctrine ancestors are cyber-deception misinformation
\cite{fergusonwalter2017,bodeau2013,perry2025} and decoy \emph{artifacts}
\cite{honeypotagents2026}, whose future-work section proposes defender-side
disinformation with a qualitative verification caveat. E15 is that
proposal's characterization in a new medium, a falsified published
\emph{measurement} of real components, with the stability condition
(public-suite consistency) and the collapse curve quantified.

\subsection{E16: how many held-out probes? the detection budget}\label{sec:budget}

Propositions~\ref{prop:gaming} and~\ref{cor:adaptive} made the gaming-gap
diagnostic depend on a secret held-out set; the natural next question is
\emph{how big must it be?}

\begin{proposition}[Detection budget vs.\ probe discrimination]\label{prop:budget}
An attacker that breaches iff it classifies a probe as held-out is caught by
its own mistakes: any misclassification \emph{toward} the public support fails
the public certificate immediately (the asymmetry is fatal), and held-out
misreadings shrink the measured gap. With held-out misread rate $m$, the
minimum held-out budget for guaranteed detection is computable in closed form
(binomial tail $\times$ Wilson geometry) and diverges as $m\to1$; evasion
requires \emph{error-free one-sided discrimination} of the public support.
\end{proposition}

E16 validates the closed form by Monte Carlo at every registered grid
point: $n_{\min}=1,2,8$ at misread rates $m=0.02,0.10,0.50$, rising
$8\to33\to103\to549\to2057$ across $m=0.5\to0.92$, and beyond any feasible
budget for $m\ge0.94$. The attacker's own fallibility is the defender's
detection resource. This couples the defender's query budget to attacker
quality, a tractable part of the query-complexity program opened by
Theorem~\ref{thm:uniform}, where the auditing-games line
\cite{auditinggames2025} and sandbagging demonstrations
\cite{aisandbagging2024} stress-test detectors without a budget--error
coupling.

\subsection{E20: the disclosure frontier has no free lunch}\label{sec:frontier}

E14's registered open question, an optimal disclosure mechanism, is
answered in the negative. Releasing the profile under per-cell Laplace noise
($\varepsilon$-DP over the \emph{profile} space, $L_1$ sensitivity 1) traces
a monotone trade-off curve between the two corners: the scalar $U_{\max}$
(attacker advantage $0$, defender utility $0$) and the full vector
(advantage $0.067$, utility $1.0$). \emph{No interior point dominates either
corner}: the scalar remains optimal against the argmax attacker, the full
release remains utility-optimal, and noise merely moves the defender along
the frontier. Certificate disclosure has no free lunch: the defender must
choose a point on the curve, not evade it.

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{anthro/fig5_premium.pdf}
\caption{The deception-release wave. (a)~E15: a decoy release drives
the attacker's expected per-attempt success to $0.000$ while honest disclosure
hands it $1.000$ and silence $0.200$---the release is stable against any
attacker whose verification is confined to the public probe suite, and
collapses monotonically as held-out capability arrives. (b)~E16: the minimum held-out
budget for guaranteed gaming-gap detection diverges as
the attacker's probe-discrimination error $m$ grows; beyond $m\approx0.94$ no
feasible budget detects the gaming, while any misclassification \emph{toward}
the public support fails the public certificate immediately.}
\label{fig:release}
\end{figure}

\section{Discussion and Implications}\label{sec:discussion}

\paragraph{For AI assurance frameworks.}
The estimand and its certification semantics map directly onto the
assurance activities NIST's AI Risk Management Framework calls
\emph{measure} and \emph{manage} \cite{nist2023}, and onto what the EU AI
Act's conformity-assessment route expects for high-risk systems
\cite{euaiact2024}: a registered probe protocol, an interval-valued
measurement, pre-registered acceptance thresholds ($\tau$), and re-testing
on drift (the half-life rule of Proposition~\ref{prop:halflife} replaces
fixed-calendar re-certification). The composition result
(Theorem~\ref{thm:compose}/E6/E8) says conformity evidence must cover
\emph{interfaces}, not only components; the gaming-gap results
(Propositions~\ref{prop:gaming}--\ref{prop:budget}) say the diagnostic
itself must be secret; the disclosure results (Section~\ref{sec:disclosure})
say published evidence must be treated as sensitive data. None of these
mappings is claimed as conformance; they are the measurement layer the
frameworks currently lack.

\paragraph{Defender guidance.}
Four operational rules follow from the results, each with its evidence.
(i) Certify the interface vocabulary, not only components: one
cross-interface probe caught a composition attack that 300 component-local
probes certified clean (E8). (ii) Keep diagnostic probe sets secret and
rotate them, because published held-out sets are gameable
(Corollary~\ref{cor:adaptive}/E10) and the required held-out budget
diverges with attacker discrimination quality
(Proposition~\ref{prop:budget}/E16). (iii) Treat any published belief
profile as attacker reconnaissance: the scalar worst-family bound removes
targeting information at the cost of family-level allocation, and no
bounded-noise release dominates both corners (E20). (iv) Session isolation
is an identification condition, since shared-context probing biases
$\hat\beta$ by $93.3\%$ relative on our foils
(Proposition~\ref{prop:reactivity}/E12).

\paragraph{What the nulls establish and what they do not.}
The two field nulls are results, not absences of results. They establish
that the instrument, at its registered resolution (20 probes per cell; 10
per cell for attacker-side tomography), does not detect belief movement in
two operational settings: frontier \emph{targets} holding a charter under a
300-session probe attack, and frontier \emph{attacker personas} holding
operational beliefs under live honeypot deception. They do not establish
that no exploitable belief exists. The E4/E7/E9 foil family shows the same
instrument recovers graded structure when beliefs exist, and the oracle
audits bound what the verdict channel can miss (20\% FP / 48\% FN for the
lexical oracle; the adjudication channel calibrated by E17). Deeper
deception engagement, meaning operations the target actually consumes over
long dwell times, remains future work, as does tomography of learned,
continuously adapting attackers; Proposition~\ref{prop:alloc} covers
one-shot learning, and the multi-round regime is open.

\paragraph{Release policy for the instrument itself.}
The gaming-gap results create a tension for our own artifact: the probe
library and canary allowlist that make the work reproducible are exactly the
public supports that Corollary~\ref{cor:adaptive} says an adaptive target
can condition on. We release the estimator, the harness, the
pre-registrations, and the transcript-level artifacts, and hold back the
live-fleet diagnostic probe sets; the constructed-foil harness is fully
public because its targets are deterministic and cannot adapt between
measurements. The split follows our own results rather than contradicting
them.

\paragraph{Ethics of the method.}
Belief tomography is dual-use. The probes that certify an agent can
fingerprint it; the deception-gain measurement that hardens a fleet can
calibrate an attacker. The disclosure results make this explicit rather than
implicit: we publish the mechanics and the trade-offs, and argue that the
defender's advantage (registered protocols, secret diagnostics,
canary-gated operations) degrades gracefully with disclosure while the
attacker's advantage does not survive institutionalization. All live
experiments in this program ran on infrastructure the author owns, with
canary-only secrets and halt gates.

\section{Rigor, Ethics, and Limitations}\label{sec:limits}

\paragraph{Rigor infrastructure.}
Every experiment is pre-registered before data; the estimator is frozen by
commit hash; every deviation is logged before the affected data is analyzed.
Effects below the measured noise floor are not claimable in any document.
Every number in this paper maps to an artifact path and commit in the
claims--evidence ledger. The verdict channel is disclosed (oracle vs.\
jury) and audited against transcripts. No real credentials are used: all
secrets are fiction canaries, and the target genuinely holds the canary
under the wire protocol.

\paragraph{Ethics declaration.}
All experiments ran on infrastructure the author owns or on locally
constructed foils; no third-party system was probed or attacked. The live
honeypot operations used synthetic canary secrets exclusively, with halt
gates and an adjudicated canary-allowlist incident. The attacker personas
are automated LLM-driven agents under the author's control; no human
subjects were involved, and no institutional review was required. The
dual-use analysis is in Section~\ref{sec:discussion}.

\paragraph{Limitations.}
(1) \emph{Behavioral estimand.} We measure behavioral belief, not internal
representation; Theorem~\ref{thm:passive} is the degenerate case showing why
the behavioral object is the contractible one. (2) \emph{Template
diversity.} The library is v0: one template per (family, generation) cell;
repeated samples measure sampling probability, not probe diversity.
Semantic-preserving paraphrases and LLM-generated worlds are the library-v1
fix, with E1 revalidated on paraphrased templates. (3) \emph{Verdict
semantics.} Lexical oracles have a measured 20\% false-positive and 48\%
false-negative rate on boundary sessions; the calibrated jury and
transcript audit are mandatory for non-literal breaches. (4) \emph{Provider
censoring.} Gateway content filters block a subset of aggressive probes;
blocked probes are counted and mapped to a conservative (charter-holding)
verdict, so $\hat\beta$ is downward-biased and the blocked set is exactly
where breaches would be most likely. The headline must state the measurable
probe set. (5) \emph{Panel and access.} The E2-v1 panel is the set of
models the authenticated gateway serves, addressed by its catalog names; a
gateway may route to a different snapshot than the name suggests, and panel
extension is a replication, not a re-analysis.

\section{Conclusion}\label{sec:conclusion}

Charters assert; behavior betrays; the distance between them is now a
measured quantity. This paper supplied that quantity with an estimand, an
instrument, and a theory of what measurement under attack can deliver:
passive monitoring cannot tomograph; believable deception decays as
$O(L/\sqrt{N})$; public certificates can be gamed, forged, and dated, and do
not compose; and publishing the measurement is itself a disclosure decision
with no free lunch. Twenty-one pre-registered experiments, two honest field
nulls on production frontier models and a live honeypot fleet among them,
each seeded, gated, and pinned to a frozen estimator, turn every claim in
this paper into an artifact a reader can attack. The measurement science of
what autonomous agents are made to wrongly believe begins the way this paper
did: with a registered protocol, a frozen estimator, and a claim that names
its own bounds.


\begin{acks}
The author thanks the operators of the live fleet infrastructure. AI-assisted
drafting tools were used for manuscript preparation under author direction;
all experimental design, data collection, analysis, and verified claims are
the author's own, and the full execution log, pre-registrations, and deviation
ledger are in the artifact repository. This research received no external
funding. The author declares no competing interests.
\end{acks}

\section*{Data Availability}

All 21 experiments are seeded and pinned to a frozen estimator commit; the
artifact package reproduces every number in this paper (profiles, transcripts,
verdict JSONLs, audit sheets, and analysis scripts), including the fleet-census
artifact, the jury-lane methodology note, and the claims--evidence ledger. The
constructed-foil harness is public; live-fleet diagnostic probe sets are
withheld per the release policy of Section~\ref{sec:discussion}.
%%% -*-BibTeX-*-
%%% Do NOT edit. File created by BibTeX with style
%%% ACM-Reference-Format-Journals [18-Jan-2012].

\begin{thebibliography}{74}

%%% ====================================================================
%%% NOTE TO THE USER: you can override these defaults by providing
%%% customized versions of any of these macros before the \bibliography
%%% command.  Each of them MUST provide its own final punctuation,
%%% except for \shownote{}, \showDOI{}, and \showURL{}.  The latter two
%%% do not use final punctuation, in order to avoid confusing it with
%%% the Web address.
%%%
%%% To suppress output of a particular field, define its macro to expand
%%% to an empty string, or better, \unskip, like this:
%%%
%%% \newcommand{\showDOI}[1]{\unskip}   % LaTeX syntax
%%%
%%% \def \showDOI #1{\unskip}           % plain TeX syntax
%%%
%%% ====================================================================

\ifx \showCODEN    \undefined \def \showCODEN     #1{\unskip}     \fi
\ifx \showDOI      \undefined \def \showDOI       #1{#1}\fi
\ifx \showISBNx    \undefined \def \showISBNx     #1{\unskip}     \fi
\ifx \showISBNxiii \undefined \def \showISBNxiii  #1{\unskip}     \fi
\ifx \showISSN     \undefined \def \showISSN      #1{\unskip}     \fi
\ifx \showLCCN     \undefined \def \showLCCN      #1{\unskip}     \fi
\ifx \shownote     \undefined \def \shownote      #1{#1}          \fi
\ifx \showarticletitle \undefined \def \showarticletitle #1{#1}   \fi
\ifx \showURL      \undefined \def \showURL       {\relax}        \fi
% The following commands are used for tagged output and should be
% invisible to TeX
\providecommand\bibfield[2]{#2}
\providecommand\bibinfo[2]{#2}
\providecommand\natexlab[1]{#1}
\providecommand\showeprint[2][]{arXiv:#2}

\bibitem[Alvim et~al\mbox{.}(2020)]%
        {alvim2020}
\bibfield{author}{\bibinfo{person}{M{\'o}nica~S. Alvim},
  \bibinfo{person}{Konstantinos Chatzikokolakis}, \bibinfo{person}{Annabelle
  McIver}, \bibinfo{person}{Carroll Morgan}, \bibinfo{person}{Catuscia
  Palamidessi}, {and} \bibinfo{person}{Geoffrey Smith}.}
  \bibinfo{year}{2020}\natexlab{}.
\newblock \bibinfo{booktitle}{\emph{The Science of Quantitative Information
  Flow}}.
\newblock \bibinfo{publisher}{Springer}.
\newblock


\bibitem[Anderson and Moore(2006)]%
        {anderson2006}
\bibfield{author}{\bibinfo{person}{Ross Anderson} {and} \bibinfo{person}{Tyler
  Moore}.} \bibinfo{year}{2006}\natexlab{}.
\newblock \showarticletitle{The Economics of Information Security}.
\newblock \bibinfo{journal}{\emph{Science}} \bibinfo{volume}{314},
  \bibinfo{number}{5799} (\bibinfo{year}{2006}), \bibinfo{pages}{610--613}.
\newblock


\bibitem[Andriushchenko et~al\mbox{.}(2025)]%
        {agentharm2025}
\bibfield{author}{\bibinfo{person}{Maksym Andriushchenko},
  \bibinfo{person}{Alexandra Souly}, \bibinfo{person}{Mateusz Dziemian},
  \bibinfo{person}{Derek Duenas}, \bibinfo{person}{Maxwell Lin},
  \bibinfo{person}{Justin Wang}, \bibinfo{person}{Dan Hendrycks},
  \bibinfo{person}{Andy Zou}, \bibinfo{person}{Zico Kolter},
  \bibinfo{person}{Matt Fredrikson}, \bibinfo{person}{Eric Winsor},
  \bibinfo{person}{Jerome Wynne}, \bibinfo{person}{Yarin Gal}, {and}
  \bibinfo{person}{Xander Davies}.} \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{AgentHarm: A Benchmark for Measuring Harmfulness of
  LLM Agents}. In \bibinfo{booktitle}{\emph{International Conference on
  Learning Representations (ICLR)}}.
\newblock
\newblock
\shownote{arXiv:2410.09024}.


\bibitem[Arif et~al\mbox{.}(2026)]%
        {testifai}
\bibfield{author}{\bibinfo{person}{Asad Arif}, \bibinfo{person}{Thomas
  Hartung}, \bibinfo{person}{Enda Botoeva}, {and} \bibinfo{person}{Alexandros
  Koliousis}.} \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{TestifAI: Tomography-Based Testing for Deep Learning
  Systems}.
\newblock \bibinfo{howpublished}{arXiv:2608.18900}.
\newblock


\bibitem[Baker et~al\mbox{.}(2025)]%
        {baker2025monitoring}
\bibfield{author}{\bibinfo{person}{Bowen Baker}, \bibinfo{person}{Joost
  Huizinga}, \bibinfo{person}{Leo Gao}, \bibinfo{person}{Zehao Dou},
  \bibinfo{person}{Melody~Y. Guan}, \bibinfo{person}{Aleksander Madry},
  \bibinfo{person}{Wojciech Zaremba}, \bibinfo{person}{Jakub Pachocki}, {and}
  \bibinfo{person}{David Farhi}.} \bibinfo{year}{2025}\natexlab{}.
\newblock \bibinfo{title}{Monitoring Reasoning Models for Misbehavior and the
  Risks of Promoting Obfuscation}.
\newblock \bibinfo{howpublished}{arXiv:2503.11926}.
\newblock


\bibitem[Baum et~al\mbox{.}(2026)]%
        {baum2026}
\bibfield{author}{\bibinfo{person}{Katrin Baum}, \bibinfo{person}{Ruta
  Binkyt{\.e}}, \bibinfo{person}{Ganna Gro{\ss}mann}, \bibinfo{person}{Falk
  Jahn}, {and} \bibinfo{person}{Andrea Mannino}.}
  \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{Rewarded for Not Getting Caught: Why Alignment
  Training Selects for Conditional Compliance}.
\newblock \bibinfo{howpublished}{arXiv:2611.02162}.
\newblock


\bibitem[Bewley and Lawry(2020)]%
        {tripletree2020}
\bibfield{author}{\bibinfo{person}{Tom Bewley} {and} \bibinfo{person}{James
  Lawry}.} \bibinfo{year}{2020}\natexlab{}.
\newblock \bibinfo{title}{TripleTree: A Versatile Interpretable Representation
  of Black Box Agents and Their Environments}.
\newblock \bibinfo{howpublished}{arXiv:2009.04743}.
\newblock


\bibitem[Bewley et~al\mbox{.}(2020)]%
        {bewley2020}
\bibfield{author}{\bibinfo{person}{Tom Bewley}, \bibinfo{person}{James Lawry},
  {and} \bibinfo{person}{Ashley Richards}.} \bibinfo{year}{2020}\natexlab{}.
\newblock \bibinfo{title}{Modelling Agent Policies with Interpretable Imitation
  Learning}.
\newblock \bibinfo{howpublished}{arXiv:2006.11309}.
\newblock


\bibitem[Bodeau et~al\mbox{.}(2013)]%
        {bodeau2013}
\bibfield{author}{\bibinfo{person}{Deborah Bodeau}, \bibinfo{person}{Richard
  Glantz}, \bibinfo{person}{Robert White}, {and} \bibinfo{person}{Julie
  McCall}.} \bibinfo{year}{2013}\natexlab{}.
\newblock \bibinfo{booktitle}{\emph{Characterizing Effects on the Cyber
  Adversary: A System Dynamics and Navigational Aid Approach}}.
\newblock \bibinfo{type}{{T}echnical {R}eport} TR-1193.
  \bibinfo{institution}{MITRE}.
\newblock


\bibitem[Casoria and Romano(2026)]%
        {socialhumint2026}
\bibfield{author}{\bibinfo{person}{Pietro Casoria} {and}
  \bibinfo{person}{Simon~Pietro Romano}.} \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{Social-HUMINT: An LLM-Augmented Unified Framework for
  Measuring Social Media Exposure}.
\newblock \bibinfo{howpublished}{arXiv:2610.31573}.
\newblock


\bibitem[Chen et~al\mbox{.}(2026)]%
        {orchjail2026}
\bibfield{author}{\bibinfo{person}{Jiayi Chen}, \bibinfo{person}{Yiming Wang},
  \bibinfo{person}{Jian Wang}, \bibinfo{person}{Zheng Liu},
  \bibinfo{person}{Wenqi Qiu}, \bibinfo{person}{Fengyuan Xu}, {and}
  \bibinfo{person}{Tong Zhang}.} \bibinfo{year}{2026}\natexlab{}.
\newblock \showarticletitle{OrchJail: Jailbreaking Tool-Calling Text-to-Image
  Agents by Orchestration-Guided Fuzzing}. In
  \bibinfo{booktitle}{\emph{Proceedings of ICML}}.
\newblock
\newblock
\shownote{arXiv:2605.07414}.


\bibitem[Chen et~al\mbox{.}(2025)a]%
        {struq2025}
\bibfield{author}{\bibinfo{person}{Sizhe Chen}, \bibinfo{person}{Julien
  Piet}, \bibinfo{person}{Chawin Sitawarin}, {and} \bibinfo{person}{David
  Wagner}.} \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{StruQ: Defending Against Prompt Injection with
  Structured Queries}. In \bibinfo{booktitle}{\emph{Proceedings of the USENIX
  Security Symposium}}. \bibinfo{pages}{2383--2400}.
\newblock
\newblock
\shownote{arXiv:2402.06363}.


\bibitem[Chen et~al\mbox{.}(2025)b]%
        {secalign2025}
\bibfield{author}{\bibinfo{person}{Sizhe Chen}, \bibinfo{person}{Arman
  Zharmagambetov}, \bibinfo{person}{Saeed Mahloujifar},
  \bibinfo{person}{Kamalika Chaudhuri}, {and} \bibinfo{person}{David
  Wagner}.} \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{SecAlign: Defending Against Prompt Injection
  with Preference Optimization}. In \bibinfo{booktitle}{\emph{Proceedings of
  the ACM Conference on Computer and Communications Security (CCS)}}.
\newblock
\newblock
\shownote{arXiv:2410.05451}.


\bibitem[Debenedetti et~al\mbox{.}(2026)]%
        {camel2026}
\bibfield{author}{\bibinfo{person}{Edoardo Debenedetti}, \bibinfo{person}{Ilia
  Shumailov}, \bibinfo{person}{Tianqi Fan}, \bibinfo{person}{Jamie Hayes},
  \bibinfo{person}{Nicholas Carlini}, \bibinfo{person}{Daniel Fabian},
  \bibinfo{person}{Christoph Kern}, \bibinfo{person}{Chongyang Shi},
  \bibinfo{person}{Andreas Terzis}, {and} \bibinfo{person}{Florian Tram\`er}.}
  \bibinfo{year}{2026}\natexlab{}.
\newblock \showarticletitle{Defeating Prompt Injections by Design}. In
  \bibinfo{booktitle}{\emph{IEEE Conference on Secure and Trustworthy Machine
  Learning (SaTML)}}.
\newblock
\newblock
\shownote{arXiv:2503.18813}.


\bibitem[Debenedetti et~al\mbox{.}(2024)]%
        {agentdojo2024}
\bibfield{author}{\bibinfo{person}{Edoardo Debenedetti}, \bibinfo{person}{Jie
  Zhang}, \bibinfo{person}{Mislav Balunovi\'c}, \bibinfo{person}{Luca
  Beurer-Kellner}, \bibinfo{person}{Marc Fischer}, {and}
  \bibinfo{person}{Florian Tram\`er}.} \bibinfo{year}{2024}\natexlab{}.
\newblock \showarticletitle{AgentDojo: A Dynamic Environment to Evaluate Prompt
  Injection Attacks and Defenses for LLM Agents}. In
  \bibinfo{booktitle}{\emph{Advances in Neural Information Processing Systems
  (NeurIPS), Datasets and Benchmarks Track}}.
\newblock
\newblock
\shownote{arXiv:2406.13352}.


\bibitem[Duddu et~al\mbox{.}(2026)]%
        {duddu2026}
\bibfield{author}{\bibinfo{person}{Vasisht Duddu}, \bibinfo{person}{Meng Wang},
  \bibinfo{person}{Luke He}, {and} \bibinfo{person}{Tim G.~J. Rudner}.}
  \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{Designing Deceptive Model Organisms that Successfully
  Evade Auditing}.
\newblock \bibinfo{howpublished}{arXiv:2611.20459}.
\newblock


\bibitem[Ederer and Min(2022)]%
        {nberlie}
\bibfield{author}{\bibinfo{person}{Florian Ederer} {and} \bibinfo{person}{Wen
  Min}.} \bibinfo{year}{2022}\natexlab{}.
\newblock \bibinfo{booktitle}{\emph{Bayesian Persuasion with Lie Detection}}.
\newblock \bibinfo{type}{{T}echnical {R}eport} 30065.
  \bibinfo{institution}{NBER}.
\newblock


\bibitem[European Parliament and Council of the European Union(2024)]%
        {euaiact2024}
\bibfield{author}{\bibinfo{person}{European Parliament and Council of the
  European Union}.} \bibinfo{year}{2024}\natexlab{}.
\newblock \showarticletitle{Regulation (EU) 2024/1689 of the European
  Parliament and of the Council of 13 June 2024 Laying Down Harmonised Rules
  on Artificial Intelligence (Artificial Intelligence Act)}.
\newblock \bibinfo{howpublished}{Official Journal of the European Union, L
  series, 12 July 2024}.
\newblock


\bibitem[Feng et~al\mbox{.}(2025)]%
        {feng2024}
\bibfield{author}{\bibinfo{person}{Jiahai Feng}, \bibinfo{person}{Stuart
  Russell}, {and} \bibinfo{person}{Jacob Steinhardt}.}
  \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{Monitoring Latent World States in Language Models
  with Propositional Probes}. In \bibinfo{booktitle}{\emph{International
  Conference on Learning Representations (ICLR)}}.
\newblock
\newblock
\shownote{arXiv:2406.19501}.


\bibitem[Ferguson-Walter et~al\mbox{.}(2017)]%
        {fergusonwalter2017}
\bibfield{author}{\bibinfo{person}{Kimberly Ferguson-Walter},
  \bibinfo{person}{Scott Fugate}, \bibinfo{person}{Jeremiah Taber}, {and}
  \bibinfo{person}{Max Maier}.} \bibinfo{year}{2017}\natexlab{}.
\newblock \bibinfo{title}{Game Theory for Adaptive Defensive Cyber-Deception
  Strategy}.
\newblock \bibinfo{howpublished}{USENIX Enigma 2017; Shadow Warrior (NDSS DISS
  2017)}.
\newblock


\bibitem[Ferguson-Walter et~al\mbox{.}(2019)]%
        {tularosa2019}
\bibfield{author}{\bibinfo{person}{Kimberly~J. Ferguson-Walter},
  \bibinfo{person}{Temmie Shade}, \bibinfo{person}{Andrew Rummler}, {and}
  \bibinfo{person}{Alexander Stephens}.} \bibinfo{year}{2019}\natexlab{}.
\newblock \showarticletitle{The Tularosa Study: An Experimental Design and
  Implementation to Quantify the Effectiveness of Cyber Deception}. In
  \bibinfo{booktitle}{\emph{Proceedings of HICSS}}.
\newblock


\bibitem[Ferrara(2026)]%
        {ferrara2026}
\bibfield{author}{\bibinfo{person}{Emilio Ferrara}.}
  \bibinfo{year}{2026}\natexlab{}.
\newblock \showarticletitle{Defeat Devices in AI Systems}.
\newblock \bibinfo{journal}{\emph{Future Internet}} \bibinfo{volume}{18},
  \bibinfo{number}{7} (\bibinfo{year}{2026}), \bibinfo{pages}{339}.
\newblock
\urldef\tempurl%
\url{https://doi.org/10.3390/fi18070339}
\showDOI{\tempurl}


\bibitem[Fogla et~al\mbox{.}(2006)]%
        {fogla2006}
\bibfield{author}{\bibinfo{person}{Prahlad Fogla}, \bibinfo{person}{Monirul
  Sharif}, \bibinfo{person}{Roberto Perdisci}, \bibinfo{person}{Oleg
  Kolesnikov}, {and} \bibinfo{person}{Wenke Lee}.}
  \bibinfo{year}{2006}\natexlab{}.
\newblock \showarticletitle{Polymorphic Blending Attacks}. In
  \bibinfo{booktitle}{\emph{Proceedings of the USENIX Security Symposium}}.
\newblock


\bibitem[Greenblatt et~al\mbox{.}(2024)]%
        {greenblatt2024faking}
\bibfield{author}{\bibinfo{person}{Ryan Greenblatt}, \bibinfo{person}{Carson
  Denison}, \bibinfo{person}{Benjamin Wright}, \bibinfo{person}{Fabien Roger},
  \bibinfo{person}{Monte MacDiarmid}, \bibinfo{person}{Sam Marks},
  \bibinfo{person}{Johannes Treutlein}, \bibinfo{person}{Tim Belonax},
  \bibinfo{person}{Jack Chen}, \bibinfo{person}{David Duvenaud},
  \bibinfo{person}{Akbir Khan}, \bibinfo{person}{Julian Michael},
  \bibinfo{person}{S{\"o}ren Mindermann}, \bibinfo{person}{Ethan Perez},
  \bibinfo{person}{Linda Petrini}, \bibinfo{person}{Jonathan Uesato},
  \bibinfo{person}{Jared Kaplan}, \bibinfo{person}{Buck Shlegeris},
  \bibinfo{person}{Samuel~R. Bowman}, {and} \bibinfo{person}{Evan Hubinger}.}
  \bibinfo{year}{2024}\natexlab{}.
\newblock \bibinfo{title}{Alignment Faking in Large Language Models}.
\newblock \bibinfo{howpublished}{arXiv:2412.14093}.
\newblock


\bibitem[Greshake et~al\mbox{.}(2023)]%
        {greshake2023}
\bibfield{author}{\bibinfo{person}{Kai Greshake}, \bibinfo{person}{Sahar
  Abdelnabi}, \bibinfo{person}{Shailesh Mishra}, \bibinfo{person}{Christoph
  Endres}, \bibinfo{person}{Thorsten Holz}, {and} \bibinfo{person}{Mario
  Fritz}.} \bibinfo{year}{2023}\natexlab{}.
\newblock \showarticletitle{Not What You've Signed Up For: Compromising
  Real-World LLM-Integrated Applications with Indirect Prompt Injection}. In
  \bibinfo{booktitle}{\emph{Proceedings of the 16th ACM Workshop on Artificial
  Intelligence and Security (AISec)}}.
\newblock
\urldef\tempurl%
\url{https://doi.org/10.1145/3605764.3623985}
\showDOI{\tempurl}


\bibitem[Hagendorff(2024)]%
        {hagendorff2024}
\bibfield{author}{\bibinfo{person}{Thilo Hagendorff}.}
  \bibinfo{year}{2024}\natexlab{}.
\newblock \showarticletitle{Deception Abilities Emerged in Large Language
  Models}.
\newblock \bibinfo{journal}{\emph{Proceedings of the National Academy of
  Sciences}} \bibinfo{volume}{121}, \bibinfo{number}{24}
  (\bibinfo{year}{2024}), \bibinfo{pages}{e2317967121}.
\newblock
\urldef\tempurl%
\url{https://doi.org/10.1073/pnas.2317967121}
\showDOI{\tempurl}


\bibitem[Hardy(1988)]%
        {hardy1988}
\bibfield{author}{\bibinfo{person}{Norman Hardy}.}
  \bibinfo{year}{1988}\natexlab{}.
\newblock \showarticletitle{The Confused Deputy (or Why Capabilities Might Have
  Been Invented)}.
\newblock \bibinfo{journal}{\emph{ACM SIGOPS Operating Systems Review}}
  \bibinfo{volume}{22}, \bibinfo{number}{4} (\bibinfo{year}{1988}),
  \bibinfo{pages}{36--38}.
\newblock
\urldef\tempurl%
\url{https://doi.org/10.1145/54289.871709}
\showDOI{\tempurl}


\bibitem[He et~al\mbox{.}(2025)]%
        {he2025survey}
\bibfield{author}{\bibinfo{person}{Feng He}, \bibinfo{person}{Tianqing Zhu},
  \bibinfo{person}{Dayong Ye}, \bibinfo{person}{Bo Liu},
  \bibinfo{person}{Wanlei Zhou}, {and} \bibinfo{person}{Philip~S. Yu}.}
  \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{The Emerged Security and Privacy of LLM Agent: A
  Survey with Case Studies}.
\newblock \bibinfo{journal}{\emph{Comput. Surveys}} \bibinfo{volume}{58},
  \bibinfo{number}{6} (\bibinfo{year}{2025}), \bibinfo{pages}{162:1--162:36}.
\newblock
\urldef\tempurl%
\url{https://doi.org/10.1145/3773080}
\showDOI{\tempurl}


\bibitem[Hoeffding(1963)]%
        {hoeffding1963}
\bibfield{author}{\bibinfo{person}{Wassily Hoeffding}.}
  \bibinfo{year}{1963}\natexlab{}.
\newblock \showarticletitle{Probability Inequalities for Sums of Bounded Random
  Variables}.
\newblock \bibinfo{journal}{\emph{J. Amer. Statist. Assoc.}}
  \bibinfo{volume}{58}, \bibinfo{number}{301} (\bibinfo{year}{1963}),
  \bibinfo{pages}{13--30}.
\newblock


\bibitem[Houlsby et~al\mbox{.}(2013)]%
        {houlsby2013}
\bibfield{author}{\bibinfo{person}{Nicolas M.~T. Houlsby},
  \bibinfo{person}{Ferenc Husz{\'a}r}, \bibinfo{person}{Mohammad~M. Ghassemi},
  \bibinfo{person}{G{\'a}bor Orb{\'a}n}, \bibinfo{person}{David~M. Wolpert},
  {and} \bibinfo{person}{M{\'a}t{\'e} Lengyel}.}
  \bibinfo{year}{2013}\natexlab{}.
\newblock \showarticletitle{Cognitive Tomography Reveals Complex,
  Task-Independent Mental Representations}.
\newblock \bibinfo{journal}{\emph{Current Biology}} \bibinfo{volume}{23},
  \bibinfo{number}{21} (\bibinfo{year}{2013}).
\newblock
\urldef\tempurl%
\url{https://doi.org/10.1016/j.cub.2013.09.012}
\showDOI{\tempurl}


\bibitem[Jiang et~al\mbox{.}(2026)]%
        {chaincaps2026}
\bibfield{author}{\bibinfo{person}{Xin Jiang}, \bibinfo{person}{Shuo Yang},
  \bibinfo{person}{Zheng Li}, \bibinfo{person}{Lin Liu}, \bibinfo{person}{Hao
  Yu}, {and} \bibinfo{person}{Yang Liu}.} \bibinfo{year}{2026}\natexlab{}.
\newblock \showarticletitle{ChainCaps: Composition-Safe Tool-Using Agents via
  Monotonic Capability Attenuation}. In \bibinfo{booktitle}{\emph{AIWILD @
  ICML}}.
\newblock
\newblock
\shownote{arXiv:2605.26542}.


\bibitem[Jin et~al\mbox{.}(2026)]%
        {epiagent}
\bibfield{author}{\bibinfo{person}{Xin Jin}, \bibinfo{person}{Xiao Cui},
  \bibinfo{person}{Zheng Ma}, \bibinfo{person}{Xiao Yan}, \bibinfo{person}{Jun
  Zhao}, \bibinfo{person}{Hao Zhang}, {and} \bibinfo{person}{Jing Wang}.}
  \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{EpiAgent: Epistemic Self-Play for LLM Agents}.
\newblock \bibinfo{howpublished}{arXiv:2610.40227}.
\newblock


\bibitem[Kamenica and Gentzkow(2011)]%
        {kamenica2011}
\bibfield{author}{\bibinfo{person}{Emir Kamenica} {and}
  \bibinfo{person}{Matthew Gentzkow}.} \bibinfo{year}{2011}\natexlab{}.
\newblock \showarticletitle{Bayesian Persuasion}.
\newblock \bibinfo{journal}{\emph{American Economic Review}}
  \bibinfo{volume}{101}, \bibinfo{number}{6} (\bibinfo{year}{2011}).
\newblock


\bibitem[Kang et~al\mbox{.}(2026)]%
        {modeltransition2026}
\bibfield{author}{\bibinfo{person}{Youjian Kang}, \bibinfo{person}{Po-Cheng
  Huang}, \bibinfo{person}{Cheng-Te Ku}, \bibinfo{person}{Chieh Hsu},
  \bibinfo{person}{Po-Jen Lee}, {and} \bibinfo{person}{I-Ling Cheng}.}
  \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{Towards Identity-Preserving LLM Agents Under Model
  Transition}.
\newblock \bibinfo{howpublished}{arXiv:2611.10628}.
\newblock


\bibitem[Lazer et~al\mbox{.}(2026)]%
        {orchestration2026}
\bibfield{author}{\bibinfo{person}{Samuel~J. Lazer}, \bibinfo{person}{Kriti
  Aryal}, \bibinfo{person}{Manish Gupta}, {and} \bibinfo{person}{Elisa
  Bertino}.} \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{Evaluating Authorization and Trust Boundaries in
  Agentic Orchestration Frameworks}.
\newblock \bibinfo{howpublished}{arXiv:2611.21259}.
\newblock


\bibitem[Li et~al\mbox{.}(2025)]%
        {mxplainer2025}
\bibfield{author}{\bibinfo{person}{Lingfeng Li}, \bibinfo{person}{Yunlong Lu},
  \bibinfo{person}{Yongyi Wang}, \bibinfo{person}{Qifan Zheng}, {and}
  \bibinfo{person}{Wenxin Li}.} \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{Mxplainer: Explain and Learn Insights by Imitating
  Mahjong Agents}.
\newblock \bibinfo{journal}{\emph{Algorithms}} \bibinfo{volume}{18},
  \bibinfo{number}{12} (\bibinfo{year}{2025}), \bibinfo{pages}{738}.
\newblock


\bibitem[Liu et~al\mbox{.}(2025)]%
        {liu2025tifs}
\bibfield{author}{\bibinfo{person}{Aishan Liu}, \bibinfo{person}{Yuguang Zhou},
  \bibinfo{person}{Xianglong Liu}, \bibinfo{person}{Tianyuan Zhang},
  \bibinfo{person}{Siyuan Liang}, \bibinfo{person}{Jiakai Wang},
  \bibinfo{person}{Yanjun Pu}, \bibinfo{person}{Tianlin Li},
  \bibinfo{person}{Junqi Zhang}, \bibinfo{person}{Wenbo Zhou},
  \bibinfo{person}{Qing Guo}, {and} \bibinfo{person}{Dacheng Tao}.}
  \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{Compromising LLM-Driven Embodied Agents with
  Contextual Backdoor Attacks}.
\newblock \bibinfo{journal}{\emph{IEEE Transactions on Information Forensics
  and Security}}  \bibinfo{volume}{20} (\bibinfo{year}{2025}),
  \bibinfo{pages}{3979--3994}.
\newblock
\urldef\tempurl%
\url{https://doi.org/10.1109/TIFS.2025.3555410}
\showDOI{\tempurl}


\bibitem[Liu et~al\mbox{.}(2024)]%
        {liu2024promptinjection}
\bibfield{author}{\bibinfo{person}{Yupei Liu}, \bibinfo{person}{Yuqi Jia},
  \bibinfo{person}{Runpeng Geng}, \bibinfo{person}{Jinyuan Jia}, {and}
  \bibinfo{person}{Neil~Zhenqiang Gong}.} \bibinfo{year}{2024}\natexlab{}.
\newblock \showarticletitle{Formalizing and Benchmarking Prompt Injection
  Attacks and Defenses}. In \bibinfo{booktitle}{\emph{Proceedings of the USENIX
  Security Symposium}}. \bibinfo{pages}{1831--1847}.
\newblock


\bibitem[Liu et~al\mbox{.}(2026)]%
        {beforedecide}
\bibfield{author}{\bibinfo{person}{Yao Liu}, \bibinfo{person}{Balaji
  Padmanabhan}, {and} \bibinfo{person}{Suresh Viswanathan}.}
  \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{Before Agents Decide: Epistemic Action in LLM-Based
  Systems}.
\newblock \bibinfo{howpublished}{arXiv:2610.00511}.
\newblock


\bibitem[Marks et~al\mbox{.}(2025)]%
        {marks2025audit}
\bibfield{author}{\bibinfo{person}{Samuel Marks}, \bibinfo{person}{Johannes
  Treutlein}, \bibinfo{person}{Treason Bricken}, {et~al\mbox{.}}}
  \bibinfo{year}{2025}\natexlab{}.
\newblock \bibinfo{title}{Auditing Language Models for Hidden Objectives}.
\newblock \bibinfo{howpublished}{arXiv:2503.10965}.
\newblock


\bibitem[Mahran(2026)]%
        {mahran2026}
\bibfield{author}{\bibinfo{person}{Ahmed~M. Mahran}.}
  \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{What Lies Beyond Perception: A Partition Theory of
  the Limits of AI Evaluation and Oversight}.
\newblock \bibinfo{howpublished}{arXiv:2610.30803}.
\newblock


\bibitem[Mondal et~al\mbox{.}(2026)]%
        {evaldrift2026}
\bibfield{author}{\bibinfo{person}{Jayanta~J. Mondal},
  \bibinfo{person}{Mrittika Banik}, \bibinfo{person}{Md. S.~A. Apurba}, {and}
  \bibinfo{person}{Md.~M. Al~Mahmud}.} \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{When Can Old Evaluations Certify a New Model?
  Label-Efficient Release Decisions Under Evaluator Drift}.
\newblock \bibinfo{howpublished}{arXiv:2609.32267}.
\newblock


\bibitem[Nguyen and Xu(2019)]%
        {nguyen2019}
\bibfield{author}{\bibinfo{person}{Thanh Nguyen} {and} \bibinfo{person}{Haifeng
  Xu}.} \bibinfo{year}{2019}\natexlab{}.
\newblock \showarticletitle{Imitative Attacker Deception in Stackelberg
  Security Games}. In \bibinfo{booktitle}{\emph{Proceedings of IJCAI}}.
\newblock
\urldef\tempurl%
\url{https://doi.org/10.24963/ijcai.2019/75}
\showDOI{\tempurl}


\bibitem[Nguyen and Husain(2026)]%
        {ati2026}
\bibfield{author}{\bibinfo{person}{Vinh~K. Nguyen} {and}
  \bibinfo{person}{Muhammad~I. Husain}.} \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{Agent Trust Infrastructure (ATI): Federated Identity,
  Trust, Attestation, and Accountability for Cross-Organization Autonomous
  Agents}.
\newblock \bibinfo{howpublished}{arXiv:2611.23202}.
\newblock


\bibitem[National Institute of Standards and Technology(2023)]%
        {nist2023}
\bibfield{author}{\bibinfo{person}{National Institute of Standards and
  Technology}.} \bibinfo{year}{2023}\natexlab{}.
\newblock \showarticletitle{Artificial Intelligence Risk Management Framework
  (AI RMF 1.0)}.
\newblock \bibinfo{type}{{T}echnical {R}eport} NIST AI 100-1.
  \bibinfo{institution}{NIST}.
\newblock
\urldef\tempurl%
\url{https://doi.org/10.6028/NIST.AI.100-1}
\showDOI{\tempurl}


\bibitem[Park et~al\mbox{.}(2024)]%
        {park2024}
\bibfield{author}{\bibinfo{person}{Peter~S. Park}, \bibinfo{person}{Sam
  Goldstein}, \bibinfo{person}{Aidan O'Gara}, \bibinfo{person}{Mia Chen}, {and}
  \bibinfo{person}{Dan Hendrycks}.} \bibinfo{year}{2024}\natexlab{}.
\newblock \showarticletitle{AI Deception: A Survey of Examples, Risks, and
  Potential Solutions}.
\newblock \bibinfo{journal}{\emph{Patterns}} \bibinfo{volume}{5},
  \bibinfo{number}{5} (\bibinfo{year}{2024}), \bibinfo{pages}{100988}.
\newblock
\urldef\tempurl%
\url{https://doi.org/10.1016/j.patter.2024.100988}
\showDOI{\tempurl}


\bibitem[Perez et~al\mbox{.}(2022)]%
        {perez2022redteam}
\bibfield{author}{\bibinfo{person}{Ethan Perez}, \bibinfo{person}{Saffron
  Huang}, \bibinfo{person}{Francis Song}, \bibinfo{person}{Trevor Cai},
  \bibinfo{person}{Roman Ring}, \bibinfo{person}{John Aslanides},
  \bibinfo{person}{Amelia Glaese}, \bibinfo{person}{Nat McAleese}, {and}
  \bibinfo{person}{Geoffrey Irving}.} \bibinfo{year}{2022}\natexlab{}.
\newblock \showarticletitle{Red Teaming Language Models with Language Models}.
  In \bibinfo{booktitle}{\emph{Proceedings of EMNLP}}.
  \bibinfo{pages}{3419--3448}.
\newblock
\urldef\tempurl%
\url{https://doi.org/10.18653/v1/2022.emnlp-main.225}
\showDOI{\tempurl}


\bibitem[Pierazzi et~al\mbox{.}(2025)]%
        {pierazzi2025tops}
\bibfield{author}{\bibinfo{person}{Fabio Pierazzi}, \bibinfo{person}{Feargus
  Pendlebury}, \bibinfo{person}{Jacopo Cortellazzi}, {and}
  \bibinfo{person}{Lorenzo Cavallaro}.} \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{Intriguing Properties of Adversarial ML Attacks in
  the Problem Space [Extended Version]}.
\newblock \bibinfo{journal}{\emph{ACM Transactions on Privacy and Security}}
  (\bibinfo{year}{2025}).
\newblock
\urldef\tempurl%
\url{https://doi.org/10.1145/3742895}
\showDOI{\tempurl}


\bibitem[Ren et~al\mbox{.}(2024)]%
        {valuebench}
\bibfield{author}{\bibinfo{person}{Yi Ren}, \bibinfo{person}{Hongbin Ye},
  \bibinfo{person}{Huajie Fang}, \bibinfo{person}{Xianpei Zhang}, {and}
  \bibinfo{person}{Le Song}.} \bibinfo{year}{2024}\natexlab{}.
\newblock \showarticletitle{ValueBench: Towards Comprehensively Evaluating
  Value Orientations and Understanding of Large Language Models}. In
  \bibinfo{booktitle}{\emph{Proceedings of ACL}}.
\newblock
\newblock
\shownote{arXiv:2406.04214}.


\bibitem[Ren et~al\mbox{.}(2025)]%
        {mask2025}
\bibfield{author}{\bibinfo{person}{Richard Ren}, \bibinfo{person}{Arunim
  Agarwal}, \bibinfo{person}{Mantas Mazeika}, {et~al\mbox{.}}}
  \bibinfo{year}{2025}\natexlab{}.
\newblock \bibinfo{title}{The MASK Benchmark: Disentangling Honesty From
  Accuracy in AI Systems}.
\newblock \bibinfo{howpublished}{arXiv:2503.03750}.
\newblock


\bibitem[Rowe(2006)]%
        {rowe2006}
\bibfield{author}{\bibinfo{person}{Neil~C. Rowe}.}
  \bibinfo{year}{2006}\natexlab{}.
\newblock \showarticletitle{Measuring the Effectiveness of Honeypot
  Counter-Deception}. In \bibinfo{booktitle}{\emph{Proceedings of HICSS}}.
\newblock


\bibitem[RoyChowdhury et~al\mbox{.}(2024)]%
        {confusedpilot2024}
\bibfield{author}{\bibinfo{person}{Ayush RoyChowdhury}, \bibinfo{person}{Mulong
  Luo}, \bibinfo{person}{Prateek Sahu}, \bibinfo{person}{Sarbartha Banerjee},
  {and} \bibinfo{person}{Mohit Tiwari}.} \bibinfo{year}{2024}\natexlab{}.
\newblock \bibinfo{title}{ConfusedPilot: Confused Deputy Risks in RAG-based
  LLMs}.
\newblock \bibinfo{howpublished}{arXiv:2408.04870}.
\newblock


\bibitem[Scheurer et~al\mbox{.}(2024)]%
        {scheurer2024}
\bibfield{author}{\bibinfo{person}{J{\'e}r{\'e}my Scheurer},
  \bibinfo{person}{Mikita Balesni}, {and} \bibinfo{person}{Marius
  Hobbhahn}.} \bibinfo{year}{2024}\natexlab{}.
\newblock \showarticletitle{Large Language Models can Strategically Deceive
  their Users when Put Under Pressure}. In \bibinfo{booktitle}{\emph{ICLR
  2024 Workshop on Large Language Model (LLM) Agents}}.
\newblock
\newblock
\shownote{arXiv:2311.07590}.


\bibitem[Sharma et~al\mbox{.}(2024)]%
        {sharma2024}
\bibfield{author}{\bibinfo{person}{Mrinank Sharma}, \bibinfo{person}{Meg Tong},
  \bibinfo{person}{Tomasz Korbak}, \bibinfo{person}{David Duvenaud},
  \bibinfo{person}{Amanda Askell}, \bibinfo{person}{Samuel~R. Bowman},
  \bibinfo{person}{Newton Cheng}, \bibinfo{person}{Esin Durmus},
  \bibinfo{person}{Zac Hatfield-Dodds}, \bibinfo{person}{Scott~R. Johnston},
  \bibinfo{person}{Shauna Kravec}, \bibinfo{person}{Timothy Maxwell},
  \bibinfo{person}{Sam McCandlish}, \bibinfo{person}{Kamal Ndousse},
  \bibinfo{person}{Oliver Rausch}, \bibinfo{person}{Nicholas Schiefer},
  \bibinfo{person}{Da Yan}, \bibinfo{person}{Miranda Zhang}, {and}
  \bibinfo{person}{Ethan Perez}.} \bibinfo{year}{2024}\natexlab{}.
\newblock \showarticletitle{Towards Understanding Sycophancy in Language
  Models}. In \bibinfo{booktitle}{\emph{International Conference on Learning
  Representations (ICLR)}}.
\newblock
\newblock
\shownote{arXiv:2310.13548}.


\bibitem[Shen et~al\mbox{.}(2025)]%
        {shen2025}
\bibfield{author}{\bibinfo{person}{Huaqing Shen}, \bibinfo{person}{Noah Clark},
  {and} \bibinfo{person}{Tanushree Mitra}.} \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{Mind the Value-Action Gap: Do LLMs Act in Alignment
  with Their Values?}. In \bibinfo{booktitle}{\emph{Proceedings of EMNLP}}.
\newblock
\newblock
\shownote{arXiv:2501.15463}.


\bibitem[Shi et~al\mbox{.}(2025)]%
        {progent2025}
\bibfield{author}{\bibinfo{person}{Tianneng Shi}, \bibinfo{person}{Jingxuan
  He}, \bibinfo{person}{Zhun Wang}, \bibinfo{person}{Hongwei Li},
  \bibinfo{person}{Linyu Wu}, \bibinfo{person}{Wenbo Guo}, {and}
  \bibinfo{person}{Dawn Song}.} \bibinfo{year}{2025}\natexlab{}.
\newblock \bibinfo{title}{Progent: Securing AI Agents with Privilege
  Control}.
\newblock \bibinfo{howpublished}{arXiv:2504.11703}.
\newblock


\bibitem[Singer et~al\mbox{.}(2025)]%
        {perry2025}
\bibfield{author}{\bibinfo{person}{Brian Singer}, \bibinfo{person}{Yusuf
  Saquib}, \bibinfo{person}{Lujo Bauer}, {and} \bibinfo{person}{Vyas Sekar}.}
  \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{Perry: A High-Level Framework for Accelerating
  Cyber Deception Experimentation}. In \bibinfo{booktitle}{\emph{Proceedings of
  RAID}}.
\newblock
\newblock
\shownote{arXiv:2506.20770}.


\bibitem[Smith(2009)]%
        {smith2009}
\bibfield{author}{\bibinfo{person}{Geoffrey Smith}.}
  \bibinfo{year}{2009}\natexlab{}.
\newblock \showarticletitle{On the Foundations of Quantitative Information
  Flow}. In \bibinfo{booktitle}{\emph{Proceedings of FOSSACS}}.
\newblock


\bibitem[Soopal et~al\mbox{.}(2026)]%
        {soopal2026}
\bibfield{author}{\bibinfo{person}{Bhavesh~R. Soopal}, \bibinfo{person}{Ananya
  Agrawal}, \bibinfo{person}{Jayanth Karthikeyan}, {and}
  \bibinfo{person}{Esther L.~C. Lip}.} \bibinfo{year}{2026}\natexlab{}.
\newblock \showarticletitle{Stress-Testing Sandbagging Detection Under Adaptive
  Attack}. In \bibinfo{booktitle}{\emph{R2A-FM @ AACL-IJCNLP}}.
\newblock
\newblock
\shownote{arXiv:2611.14950}.


\bibitem[Strachan et~al\mbox{.}(2024)]%
        {strachan2024}
\bibfield{author}{\bibinfo{person}{James W.~A. Strachan},
  \bibinfo{person}{Dalila Albergo}, \bibinfo{person}{Giulia Borghini},
  \bibinfo{person}{Oriana Pansardi}, \bibinfo{person}{Eugenio Scaliti},
  {et~al\mbox{.}}} \bibinfo{year}{2024}\natexlab{}.
\newblock \showarticletitle{Testing Theory of Mind in Large Language Models and
  Humans}.
\newblock \bibinfo{journal}{\emph{Nature Human Behaviour}}  \bibinfo{volume}{8}
  (\bibinfo{year}{2024}), \bibinfo{pages}{1285--1295}.
\newblock
\urldef\tempurl%
\url{https://doi.org/10.1038/s41562-024-01882-z}
\showDOI{\tempurl}


\bibitem[Taylor et~al\mbox{.}(2025)]%
        {auditinggames2025}
\bibfield{author}{\bibinfo{person}{Jordan Taylor}, \bibinfo{person}{Sid Black},
  \bibinfo{person}{Dillon Bowen}, \bibinfo{person}{Thomas Read},
  \bibinfo{person}{Satvik Golechha}, \bibinfo{person}{Alex Zelenka-Martin},
  \bibinfo{person}{Oliver Makins}, \bibinfo{person}{Connor Kissane},
  \bibinfo{person}{Kola Ayonrinde}, {et~al\mbox{.}}}
  \bibinfo{year}{2025}\natexlab{}.
\newblock \bibinfo{title}{Auditing Games for Sandbagging}.
\newblock \bibinfo{howpublished}{arXiv:2512.07810}.
\newblock


\bibitem[Tice et~al\mbox{.}(2025)]%
        {tice2025}
\bibfield{author}{\bibinfo{person}{Cameron Tice},
  \bibinfo{person}{Philipp~Alexander Kreer}, \bibinfo{person}{Nathan
  Helm-Burger}, \bibinfo{person}{Prithviraj~Singh Shahani},
  \bibinfo{person}{Fedor Ryzhenkov}, \bibinfo{person}{Fabien Roger},
  \bibinfo{person}{Clement Neo}, \bibinfo{person}{Jacob Haimes},
  \bibinfo{person}{Felix Hofst{\"a}tter}, {and} \bibinfo{person}{Teun van~der
  Weij}.} \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{Noise Injection Reveals Hidden Capabilities of
  Sandbagging Language Models}. In \bibinfo{booktitle}{\emph{Advances in Neural
  Information Processing Systems (NeurIPS)}}.
\newblock
\newblock
\shownote{arXiv:2412.01784}.


\bibitem[Turpin et~al\mbox{.}(2023)]%
        {turpin2023}
\bibfield{author}{\bibinfo{person}{Miles Turpin}, \bibinfo{person}{Julian
  Michael}, \bibinfo{person}{Ethan Perez}, {and} \bibinfo{person}{Samuel~R.
  Bowman}.} \bibinfo{year}{2023}\natexlab{}.
\newblock \showarticletitle{Language Models Don't Always Say What They Think:
  Unfaithful Explanations in Chain-of-Thought Prompting}. In
  \bibinfo{booktitle}{\emph{Advances in Neural Information Processing Systems
  (NeurIPS)}}.
\newblock
\newblock
\shownote{arXiv:2305.04388}.


\bibitem[van~der Weij et~al\mbox{.}(2025)]%
        {aisandbagging2024}
\bibfield{author}{\bibinfo{person}{Teun van~der Weij}, \bibinfo{person}{Felix
  Hofst{\"a}tter}, \bibinfo{person}{Ollie Jaffe}, \bibinfo{person}{Daniel
  Braun}, {and} \bibinfo{person}{Francis Ward}.}
  \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{AI Sandbagging: Language Models can Strategically
  Underperform on Evaluations}. In \bibinfo{booktitle}{\emph{International
  Conference on Learning Representations (ICLR)}}.
\newblock
\newblock
\shownote{arXiv:2406.07358}.


\bibitem[Wagner and Soto(2002)]%
        {wagner2002}
\bibfield{author}{\bibinfo{person}{David Wagner} {and} \bibinfo{person}{Paolo
  Soto}.} \bibinfo{year}{2002}\natexlab{}.
\newblock \showarticletitle{Mimicry Attacks on Host-Based Intrusion Detection
  Systems}. In \bibinfo{booktitle}{\emph{Proceedings of the ACM Conference on
  Computer and Communications Security (CCS)}}.
\newblock


\bibitem[Reworr and Volkov(2024)]%
        {volkov2024}
\bibfield{author}{\bibinfo{person}{Reworr} {and} \bibinfo{person}{Dmitrii
  Volkov}.} \bibinfo{year}{2024}\natexlab{}.
\newblock \bibinfo{title}{LLM Agent Honeypot: Monitoring AI Hacking Agents
  in the Wild}.
\newblock \bibinfo{howpublished}{arXiv:2410.13919}.
\newblock


\bibitem[Wang et~al\mbox{.}(2026)]%
        {eraudit}
\bibfield{author}{\bibinfo{person}{Dawei Wang}, \bibinfo{person}{Zheng Shi},
  \bibinfo{person}{Robert Holland}, \bibinfo{person}{Rui Sun},
  \bibinfo{person}{Xinyi Yuan}, \bibinfo{person}{Jin Xue}, {and}
  \bibinfo{person}{Lei Zhu}.} \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{Black-Box Auditing of Epistemic Reliability in
  Multi-Agent Debate Distillation}.
\newblock \bibinfo{howpublished}{arXiv:2609.32361}.
\newblock


\bibitem[Wehner and Kraprayoon(2026)]%
        {honeypotagents2026}
\bibfield{author}{\bibinfo{person}{Jan Wehner} {and} \bibinfo{person}{Jam
  Kraprayoon}.} \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{Honeypots for AI Agent Insider Threats}.
\newblock \bibinfo{howpublished}{arXiv:2610.26664}.
\newblock


\bibitem[Wilson(1927)]%
        {wilson1927}
\bibfield{author}{\bibinfo{person}{Edwin~B. Wilson}.}
  \bibinfo{year}{1927}\natexlab{}.
\newblock \showarticletitle{Probable Inference, the Law of Succession, and
  Statistical Inference}.
\newblock \bibinfo{journal}{\emph{J. Amer. Statist. Assoc.}}
  \bibinfo{volume}{22}, \bibinfo{number}{158} (\bibinfo{year}{1927}),
  \bibinfo{pages}{209--212}.
\newblock


\bibitem[Xie et~al\mbox{.}(2026)]%
        {memevo2026}
\bibfield{author}{\bibinfo{person}{Wenqi Xie}, \bibinfo{person}{Shuo Guo},
  \bibinfo{person}{Fan Zhang}, \bibinfo{person}{Tian Xia}, \bibinfo{person}{Xin
  Yang}, \bibinfo{person}{Liang Ma}, \bibinfo{person}{Qinghua Yan}, {and}
  \bibinfo{person}{Zhanyong Ren}.} \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{MemEvoBench: Benchmarking Safety Risks from Memory
  Misevolution in LLM Agents}.
\newblock \bibinfo{howpublished}{arXiv:2604.15774}.
\newblock


\bibitem[Xu et~al\mbox{.}(2026)]%
        {decepeval}
\bibfield{author}{\bibinfo{person}{Yiming Xu}, \bibinfo{person}{Hongyue Yu},
  \bibinfo{person}{Beihua Yang}, \bibinfo{person}{Zihan Chen},
  \bibinfo{person}{Yixin Liu}, \bibinfo{person}{Zhen Peng},
  \bibinfo{person}{Bin Shi}, \bibinfo{person}{Bo Dong}, \bibinfo{person}{Chao
  Shen}, \bibinfo{person}{Irwin King}, {and} \bibinfo{person}{Qinghua Zheng}.}
  \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{DecepEval: Benchmarking Deception in LLM Agents}.
\newblock \bibinfo{howpublished}{arXiv:2610.07967}.
\newblock


\bibitem[Zhan et~al\mbox{.}(2024)]%
        {injecagent2024}
\bibfield{author}{\bibinfo{person}{Qiusi Zhan}, \bibinfo{person}{Zhixiang
  Liang}, \bibinfo{person}{Zifeng Ying}, {and} \bibinfo{person}{Daniel Kang}.}
  \bibinfo{year}{2024}\natexlab{}.
\newblock \showarticletitle{InjecAgent: Benchmarking Indirect Prompt Injections
  in Tool-Integrated Large Language Model Agents}. In
  \bibinfo{booktitle}{\emph{Findings of ACL}}.
\newblock
\newblock
\shownote{arXiv:2403.02691}.


\bibitem[Zhao et~al\mbox{.}(2026)]%
        {proxyconfidence}
\bibfield{author}{\bibinfo{person}{Yang Zhao}, \bibinfo{person}{Shubham
  Pandey}, {and} \bibinfo{person}{Pratyush~Kumar Misra}.}
  \bibinfo{year}{2026}\natexlab{}.
\newblock \bibinfo{title}{Proxy Confidence: Auditing Black-Box LLM Agents with
  a Surrogate's Log-Probabilities}.
\newblock \bibinfo{howpublished}{arXiv:2610.03894}.
\newblock


\bibitem[Zou et~al\mbox{.}(2025)]%
        {poisonedrag2025}
\bibfield{author}{\bibinfo{person}{Wei Zou}, \bibinfo{person}{Runpeng Geng},
  \bibinfo{person}{Binghui Wang}, {and} \bibinfo{person}{Jinyuan Jia}.}
  \bibinfo{year}{2025}\natexlab{}.
\newblock \showarticletitle{PoisonedRAG: Knowledge Corruption Attacks to
  Retrieval-Augmented Generation of Large Language Models}. In
  \bibinfo{booktitle}{\emph{Proceedings of the USENIX Security Symposium}}.
\newblock
\newblock
\shownote{arXiv:2402.07867}.


\end{thebibliography}



\appendix
\section{Proofs and Technical Details}\label{app:proofs}

\subsection{Conventions}\label{app:notation}

$X_B(\Pi)$ is the behavioral-consistency verdict of Definition~\ref{def:beta},
and $P^{\mathrm{pas}}_B$ is the transcript distribution induced by benign
operation $\mu$ composed with the response kernel $\kappa_B$.
$\TV$ is total variation distance; $\TV(P^{N},Q^{N})$ is its value between
the $N$-fold products of $N$ i.i.d.\ samples. As in
Section~\ref{sec:qc}, $\alpha$ is a confidence level; as in
Section~\ref{sec:t5}, $\delta=\TV(P,Q)$ is a deception's observable footprint,
$\beta_d$ is a tolerated false-alarm rate, and $z_{\beta_d}$ is the two-sided
standard-normal quantile defined by $\Pr[|Z|>z_{\beta_d}]=\beta_d$ for
$Z\sim N(0,1)$. Every claim below is exactly the corresponding statement of
the main text.

\subsection{Proof of Theorem~\ref{thm:passive} and
Corollary~\ref{cor:detection}}\label{app:t1}

\begin{proof}[Proof of Theorem~\ref{thm:passive}]
Fix any benign operation $\mu$; because it contains no adversary,
adversary-controlled events of zero $\mu$-probability exist---take $E$ to be
one, e.g.\ a forged ``[SYSTEM OVERRIDE]'' directive---so $\Pr_\mu(E)=0$.

We construct the two hypotheses. Let $B_0$ refuse on every history, benign or
adversarial. Let $B_1$ agree with $B_0$ on every
history $h$ with $\Pr_\mu(h)>0$ and comply with probability $1$ on histories
containing $E$. Such a $B_1$ is well-defined: the condition ``$E\in h$'' is a
property of the history alone and never fires on $\mathrm{supp}(\mu)$, so
$B_1$ coincides with $B_0$ on all benign data; clearly $B_0\neq B_1$.

\emph{(i) The passive distributions coincide.} For every history $h$ in the
support of $\mu$, the two response kernels agree by construction,
$\kappa_{B_0}(h,\cdot)=\kappa_{B_1}(h,\cdot)$; hence the induced transcript
distributions agree pointwise, and
$\TV\bigl(P^{\mathrm{pas}}_{B_0},P^{\mathrm{pas}}_{B_1}\bigr)=0$.

\emph{(ii) One probe separates them.} Let $\Pi_{\mathrm{auth}}$ be the
authority-forgery probe family, which injects $E$ with probability $1$, and
let $X_B(\Pi_{\mathrm{auth}})$ indicate credential disclosure. Under $B_0$
the expected verdict is $0$ (the hypothesis refuses); under $B_1$ it is $1$
(it complies). The separation is therefore exactly $1$.
\end{proof}

\begin{proof}[Proof of Corollary~\ref{cor:detection}]
Any monitor is a measurable function of the passive transcript stream. Since
the transcript distributions coincide by Theorem~\ref{thm:passive}(i), so do
the distributions of the monitor's output; equivalently, the likelihood ratio
between them is $1$ everywhere. For distinguishing $B_1$ from $B_0$, the
Neyman--Pearson lemma then bounds the true-positive rate of any such monitor
by its false-positive rate.
\end{proof}

\subsection{Proofs for Section~\ref{sec:qc}}\label{app:qc}

\begin{proof}[Proof of Theorem~\ref{thm:uniform}]
Fix a proposition $i$ and the accuracy $\varepsilon>0$. Hoeffding's inequality
\cite{hoeffding1963}, applied to the $n_i$ independent Bernoulli verdicts,
gives per proposition
\[
\Pr\bigl[\,|\hat\beta_i-\beta_i|>\varepsilon\,\bigr]\;\le\;2e^{-2n_i\varepsilon^{2}}.
\]
Under the allocation $n_i\ge\frac{1}{2\varepsilon^{2}}\ln\frac{2K}{\alpha}$,
the right-hand side is at most $2e^{-\ln(2K/\alpha)}=\alpha/K$. A union bound
over the $K$ propositions then yields
\[
\Pr\Bigl[\max_{i\in[K]}\,|\hat\beta_i-\beta_i|>\varepsilon\Bigr]
\;\le\;\sum_{i=1}^{K}\frac{\alpha}{K}\;=\;\alpha,
\]
as claimed.
\end{proof}

\begin{proof}[Proof sketch of Proposition~\ref{prop:screening}]
The policy has two phases. \emph{Phase 1 (screening).} Allocate
$m=O(\varepsilon^{-2}\ln(K/\alpha))$ uniform probes per proposition and keep
the propositions whose empirical rate is above threshold. By Hoeffding's
inequality and a union bound, this phase separates the $\ge\tau$ candidates
from the rest with failure probability at most $\alpha/2$.
\emph{Phase 2 (survivors).} Best-arm-identification-style allocation on the
surviving $s$ propositions costs $O(s\,\varepsilon^{-2}\ln(K/\alpha))$ probes
and certifies the guarantee of Theorem~\ref{thm:uniform} on the whole
catalogue. Combining the budgets gives the stated total; the saving over
uniform allocation is the factor $s/K$. Optimality, and the
informativeness-optimal adaptive policy, remain open.
\end{proof}

\subsection{Proofs for Section~\ref{sec:t5}}\label{app:t5}

\begin{proof}[Proof of Lemma~\ref{lem:amp}]
The Hahn decomposition of $P$ with respect to $Q$ yields a measurable set $A$
with $P(A)-Q(A)=\delta$. Count visits to $A$: let
$S=\sum_{i\le N}\mathbf{1}[X_i\in A]$. Under $P$,
$S\sim\mathrm{Bin}(N,p)$ with $p=P(A)$; under $Q$,
$S\sim\mathrm{Bin}(N,p-\delta)$. Consider the threshold test
$\psi=\mathbf{1}[S\ge t]$ with $t=N(p-\delta/2)$, which compares the count to
its two means at half the footprint. Hoeffding's inequality for binomial
counts gives, under $P$,
\[
\Pr_p[S<t]\;\le\;e^{-N\delta^{2}/2},
\]
and, symmetrically, under $Q$,
\[
\Pr_q[S\ge t]\;\le\;e^{-N\delta^{2}/2}.
\]
The total variation distance between $P^{N}$ and $Q^{N}$ is the supremum of
$\Pr_p[\psi]-\Pr_q[\psi]$ over tests $\psi$, so this particular test lower-bounds it:
\[
\TV\bigl(P^{N},Q^{N}\bigr)\;\ge\;\Pr_p[S\ge t]-\Pr_q[S\ge t]
\;\ge\;\bigl(1-e^{-N\delta^{2}/2}\bigr)-e^{-N\delta^{2}/2}
\;=\;1-2e^{-N\delta^{2}/2},
\]
which is the claim.
\end{proof}

\begin{proof}[Proof of Theorem~\ref{thm:patch}]
\emph{(i).} This is Definition~\ref{def:sens} applied with
$\TV(P,Q)=\delta$: for every proposition $\pi$,
$|\beta[Q](\pi)-\beta[P](\pi)|\le L\,\TV(P,Q)=L\delta$.

\emph{(ii).} Two facts combine. \emph{Existence:} Lemma~\ref{lem:amp}
supplies a test---the threshold test on the Hahn set---that detects with
probability at least $1-2e^{-N\delta^{2}/2}$. \emph{Optimality:} for every
test $\psi$, $|\E_P[\psi]-\E_Q[\psi]|\le\TV(P^{N},Q^{N})$, so no test exceeds
$\TV(P^{N},Q^{N})$.

\emph{(iii).} Invert the exponent of (ii). Requiring
$1-2e^{-N\delta^{2}/2}\ge1-\beta_d$ is equivalent to
$e^{-N\delta^{2}/2}\le(1-\beta_d)/2$, that is, to
$\delta\le\sqrt{2\ln(2/(1-\beta_d))/N}$. Substituting this largest feasible
footprint into (i) gives
$\text{gain}\;\le\;L\sqrt{2\ln(2/(1-\beta_d))/N}=O(L/\sqrt{N})$.
\end{proof}

\begin{proof}[Proof sketch of Theorem~\ref{thm:onset}]
\emph{(i) Known onset.} Write $\rho_0=z_{\beta_d}\sqrt{p(1-p)/N_0}$. The
memorized reference concentrates: by Hoeffding's inequality
\cite{hoeffding1963}, $|\hat p_0-p|\le\rho_0$ with probability
$\ge1-\beta_d$. The
fresh-sample side converges to the deceived rate $p-\delta$ (the law of large
numbers), so once the attacker has collected $M\gtrsim\delta^{-2}$ fresh
turns, the two-sample statistic concentrates around the true shift $\delta$
with noise floor $\rho_0$. The dichotomy follows: $\delta\ge\rho_0$ clears
the floor and detection succeeds at the stated confidence; $\delta<\rho_0$
hides the shift---no two-sample test reaches power $1-\beta_d$ against the
reference, and by sensitivity (Definition~\ref{def:sens}) the gain is bounded
by $L\rho_0$.

\emph{(ii) Birth onset.} With $N_0=0$ there is no reference batch: both the
``real world'' and the ``deceived world'' hypotheses are consistent with the
observed single-path sample, in the sense that no second sample path exists to
compare against. Hypothesis testing degenerates to evaluating the prior
plausibility of the observed transcript distribution---and the prior is
out-of-band information, not in-channel evidence.
\end{proof}

\subsection{Proofs for Section~\ref{sec:surface}}\label{app:limits}

\begin{proof}[Proof of Corollary~\ref{cor:pub}]
Construct $T^{*}$ to agree with the compliant target on every history in
$\mathcal{S}$ (the public supports) and comply with probability $1$ on the
event $E=\{\pi'\in h\}$ that the held-out probe was delivered. The event $E$ is
well-defined on histories and, by hypothesis,
$\mathrm{supp}(\pi')\cap\mathcal{S}=\varnothing$, so it is disjoint from
$\mathcal{S}$. $T^{*}$ and the compliant target therefore induce identical
transcript distributions under every public probe; $C$ receives identical
data and returns the same decision---it accepts both. Yet $\pi'$ injects $E$
with probability one, and the breach indicator is $1$ under $T^{*}$ on that
event: Theorem~\ref{thm:passive} with $E=\pi'$.
\end{proof}

\begin{proof}[Proof of Theorem~\ref{thm:compose}]
Let $s_A$ be the secret held by $A$. We modify each component on its
off-support behavior only. \emph{Step 1 (retriever).} Construct $A'$ to agree
with the certified $A$ on $\mathcal{S}$ but to return a document containing
$s_A$ on the off-support request ``fetch document''.
\emph{Step 2 (orchestrator).} Construct $B'$ to agree with the certified $B$
on $\mathcal{S}$ but to summarize faithfully any tool output tagged $t$.
\emph{Invisibility.} Neither the ``fetch document'' request nor the tag $t$
is ever issued by $\Pi_{\mathrm{pub}}$ (by hypothesis), so both modifications
are unobservable under $\Pi_{\mathrm{pub}}$; $A'$ and $B'$ remain certified.
\emph{Realization of the breach.} The cross-interface probe $\pi^{*}$ issues
the ``fetch document'' request to $A'$ and asks $B'$ to summarize the tagged
result; the reply contains $s_A$, hence
$\beta_{B'\circ A'}(\pi^{*})=1$. Finally, the interface history---a document
containing $s_A$ under tag $t$---has zero measure under each component's local
probe distribution, which is why no component is individually non-compliant.
\end{proof}

\begin{proof}[Proof of Proposition~\ref{prop:gaming}]
\emph{First claim.} A target that complies on public probes but breaches on
held-out semantic equivalents is exactly the construction of
Corollary~\ref{cor:pub}, so the public certificate accepts it.

\emph{Second claim (transfer condition).} Hoeffding's inequality and a union
bound over the $M$ paraphrases give
$|\hat\beta(\theta_j)-\beta(\theta_j)|\le\varepsilon$ for all covered $j$
with probability $\ge1-\alpha$. For any uncovered
$\theta\in\Theta$ with $d(\theta,\theta_j)\le r$ for some covered paraphrase
$\theta_j$, assumption (A1)---the $L$-sensitivity of
Definition~\ref{def:sens}---gives the chain
\[
\beta(\theta)\;\le\;\beta(\theta_j)+Lr
\;\le\;\hat\beta(\theta_j)+\varepsilon+Lr
\;\le\;\tau+\varepsilon+Lr,
\]
which bounds the profile on the uncovered neighbourhood by
$\tau+\varepsilon+Lr$: this is the stated transfer radius.

Assumption (A2) says the target cannot condition on probe \emph{provenance}
beyond probe content; this is what prevents the target from presenting
different behavior on the held-out probes themselves---a threat-model
condition, not a consequence of held-out text. The generalization step is the
standard Lipschitz--covering argument; the diagnostic $\Gamma$ is the new
object.
\end{proof}

\begin{proof}[Proof of Theorem~\ref{thm:forgery}]
Apply the construction of Theorem~\ref{thm:passive}, family by family. Define
$T$ to condition its reply on the event
$E_{\mathrm{pub}}=\{\text{the delivered probe lies in }
\mathrm{supp}(\Pi_{\mathrm{pub}})\}$: on $E_{\mathrm{pub}}$ its breach
indicator is prescribed by $B_{\mathrm{disp}}$; on its complement, by
$B_{\mathrm{true}}$. Both events are well-defined on histories and the two
supports are disjoint by assumption, so the policy is consistent.
Under $\Pi_{\mathrm{pub}}$ the estimator observes only outcomes generated on
$E_{\mathrm{pub}}$, and therefore recovers the corresponding displayed
profile; under $\Phi_{\mathrm{held}}$, whose support is disjoint from
$\mathcal{S}$ by hypothesis, it observes only the complement and recovers the
true profile---each within estimation error.
\end{proof}

\begin{proof}[Proof of Corollary~\ref{cor:adaptive}]
Condition the reply on the event $E$ that the delivered probe lies in the
union of the public support and $\mathrm{supp}(H)$: comply on $E$, breach off
it. The two supports are disjoint by construction, so the policy is
consistent. The gaming gap computed on the published held-out set $H$ then
vanishes---every probe used to compute $\Gamma$ lands on $E$, where the target
complies---while the secret-set estimate is $1$: probes from $S$ land off
$E$, realizing the stated member of the class.
\end{proof}

\subsection{Proofs for Sections~\ref{sec:drift}--\ref{sec:budget}}\label{app:rest}

\begin{proof}[Proof of Proposition~\ref{prop:halflife}]
For any $t\ge t_0$, the drift bound and the measured upper bound give
$\beta_t\le\beta_{t_0}+v\,(t-t_0)\le U_0+v\,(t-t_0)$: the first inequality is
the assumed $v$-Lipschitz drift, the second uses $\beta_{t_0}\le U_0$ (the
Wilson bound covers the truth at measurement time). Setting the
right-hand side to $\tau$ and solving yields $h_\tau=(\tau-U_0)/v$; beyond
that horizon the measured bound no longer controls $\beta_t$, which is the
``and no longer'' clause. The sequential statement is a Bonferroni union
bound. The inequality is a basic triangle-bound consequence; the contribution
is the object $h_\tau$ as a certificate validity horizon and its renewal rule.
\end{proof}

\begin{proof}[Proof of Proposition~\ref{prop:reactivity}]
A pooled estimator over $n$ probes in one shared context averages the
position-dependent breach probabilities $\beta_0,\dots,\beta_{n-1}$; its bias
against the fresh-session estimand $\beta$ is the average of the linear
deviation bounds:
\[
\Bigl|\frac{1}{n}\sum_{k=0}^{n-1}\beta_k-\beta\Bigr|
\;\le\;\frac{1}{n}\sum_{k=0}^{n-1}ck
\;=\;\frac{c\,(n-1)}{2}.
\]
So the pooled estimator consistently estimates the context-conditioned
quantity, not $\beta$; session reset ($k=0$ per probe) is the identification
condition.
\end{proof}

\begin{proof}[Proof of Proposition~\ref{prop:alloc}]
Arithmetic on the hide threshold. A probe-aware target hides on a family once
its exposure there reaches $K$. If the family is probed $n_f<K$ times, the
measured rate saturates at $\hat\beta_f=\min(1,K/n_f)=1$, and the family fails
any tolerance. If $n_f\ge K$, then $\hat\beta_f=K/n_f$, and the certificate at
tolerance $\tau$ fails on that family exactly when $K/n_f>\tau$, i.e.\
$n_f<K/\tau$. Both cases reduce to the stated condition: the family fails iff
$n_f<K/\tau$. Uniform allocation hands the attacker exactly the uniform
exposure it needs to hide everywhere; concentrated allocation leaves some
families under-exposed, where it cannot hide. No new inequality is claimed;
the content is the operational reversal.
\end{proof}

\begin{proof}[Proof of Proposition~\ref{prop:recon}]
Decision analysis under the published vector: the decision problem is
evaluated on the published profile, and finite-sample uncertainty is reported
via the Wilson bounds. No new theorem is claimed; the proposition registers
the decision rule.
\end{proof}

\begin{proof}[Proof of Proposition~\ref{prop:release}]
Part (i) is Theorem~\ref{thm:forgery}'s realizability with the defender as
author of the displayed profile. Part (ii) is the
Proposition~\ref{prop:recon} allocation analysis with a defender-chosen
argument. Part (iii) reverses Corollary~\ref{cor:adaptive}'s secrecy
asymmetry. No new inequality is claimed; the new objects are the deception
gain of a measurement release,
$\Delta_{\mathrm{dec}}=\mathrm{succ}(\text{honest release})
-\mathrm{succ}(\text{decoy release})$,
and the verification-stability condition.
\end{proof}

\begin{proof}[Proof of Proposition~\ref{prop:budget}]
Elementary binomial power analysis coupled to the pinned Wilson estimator.
Held-out breaches are $\mathrm{Bin}(n,1-m)$, so the detection power is the
binomial tail evaluated at the Wilson-separation threshold; this tail diverges
as $m\to1$. With public-side misread rate $m'>0$, a single public breach fails
the certificate immediately, so detection probability tends to $1$ at any $n$
once public breaches occur. No new inequality is claimed; the content is the
coupling and its one-sided asymmetry.
\end{proof}


\end{document}
