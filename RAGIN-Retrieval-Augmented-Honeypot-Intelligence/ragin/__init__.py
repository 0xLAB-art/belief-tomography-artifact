"""
RAGIN Cloud LLM Migration - Core Package

Three-component migration from 20-node Docker cluster to cloud-native services:
- Component A: Chrollo (Behavioral Classification) - ML service with feature store
- Component B: Don (Hybrid RAG Engine) - Vector DB + keyword search with RAG defenses
- Component C: Hisoka (Adaptive Deception Layer) - OpenRouter LLM with session isolation

Additional modules:
- Intelligence Cycle — closed feedback loop between Don (CTI analysis) and Hisoka (deception)
- Honeytoken Engine — canary token injection and trigger detection
- CTI Feed Connectors — MISP, AlienVault OTX, RSS/Atom, CISA KEV
- ATT&CK Heatmap — Navigator-compatible JSON layer generation
- Deception Effectiveness Benchmark — metrics, scoring, and comparative benchmarks
- Jev System One — free additive behavior-key assessment for classification
  and orchestration (ragin.jev): typed noul/choice/score answers over state
- RAGIN HTTP server — also exposes Jev via /api/assess (component=jev)
"""

__version__ = "1.0.0"
__components__ = ["chrollo", "don", "hisoka", "jev", "cycle", "intelligence", "benchmark"]
