# GitCompass Evolution Roadmap (`PHASE_PLAN.md`)

> **Location:** `docs/PHASE_PLAN.md`  
> **Purpose:** Outline the long-term evolutionary stages of GitCompass, transitioning from a basic Git-history visualizer to an advanced AI-driven repository archaeology tool.

---

## 🏛 Core Architectural Philosophy

The fundamental principle guiding this roadmap is **separation of extraction and reasoning**:
1. **Deterministic Extraction:** Do not use LLMs for tasks that can be solved with static analysis (e.g., detecting languages, parsing ASTs, mapping dependencies). Use code for extraction.
2. **Repository Knowledge Model:** Aggregate all extracted deterministic data (Git history + Static Code Analysis) into a single, highly structured internal representation.
3. **AI Reasoning Layer:** The LLM is strictly a reasoning engine. It operates *on top of* the Repository Knowledge Model to synthesize insights, correlate events, and answer questions.

---

## 🗺 Implementation Stages

```text
                ┌──────────────────┐
                │   Git Repository │
                └────────┬─────────┘
                         ↓
                  ┌─────────────┐
                  │   Stage 0   │
                  │ Git Analyzer│
                  └──────┬──────┘
                         │
             ┌───────────┴───────────┐
             ↓                       ↓
      ┌─────────────┐         ┌─────────────┐
      │   Stage 1   │         │   Stage 2   │
      │  Structure  │         │ Dependencies│
      └──────┬──────┘         └──────┬──────┘
             │                       │
             └───────────┬───────────┘
                         ↓
                  ┌─────────────┐
                  │   Stage 3   │
                  │ Source Code │
                  │   Analyzer  │
                  └──────┬──────┘
                         ↓
                  ┌─────────────┐
                  │   Stage 4   │
                  │ Repository  │
                  │ Knowledge   │
                  │    Model    │
                  └──────┬──────┘
                         ↓
                  ┌─────────────┐
                  │   Stage 5   │
                  │ Code + Git  │
                  └──────┬──────┘
                         ↓
                  ┌─────────────┐
                  │   Stage 6   │
                  │ Evolution   │
                  │   Engine    │
                  └──────┬──────┘
                         ↓
                  ┌─────────────┐
                  │   Stage 7   │
                  │ AI Reasoning│
                  └──────┬──────┘
                         ↓
              ┌──────────┴──────────┐
              ↓                     ↓
       Stage 8: Q&A          Stage 9: Visuals
              │                     │
              └──────────┬──────────┘
                         ↓
                 Stage 10: Archaeology
```

### Stage 0 — Stabilize Git Analyzer
**Status:** 🔴 Active / In Progress
**Goal:** Make the existing Git-history pipeline reliable before expanding it.
- Repository cloning and transient cleanup.
- Commit traversal and metadata extraction (author, date, message).
- File diffs (additions, deletions, status).
- Persisting accurate Git history datasets for every repository.

### Stage 1 — Repository Structure Analyzer
**Status:** 🔴 High Priority Next Step
**Goal:** Understand what the repository contains before understanding what the code does.
- Directory scanner to detect languages, frameworks, and build tools.
- Identify core structural components: source directories, test directories, configuration files, CI/CD files.
- Output: A high-level structural map (e.g., "Java, Spring Boot, 3 Modules").

### Stage 2 — Dependency & Configuration Analyzer
**Status:** 🔴 High Priority
**Goal:** Understand the technology stack and external dependencies.
- Parse package managers (`package.json`, `pom.xml`, `requirements.txt`, etc.).
- Extract frameworks, libraries, databases, and cloud services.
- Inspect configuration files for ports, service names, and environment structures.
- **Security Constraint:** Strictly redact/exclude secrets, tokens, and `.env` values from the knowledge model.

### Stage 3 — Source-Code Analyzer
**Status:** 🔴 High Priority
**Goal:** Extract the actual structure of the code using static analysis/AST parsing.
- Extract file-level structures (imports, classes, functions, exports).
- Map class relationships (methods, fields, inheritance, dependencies).
- Detect API surfaces (REST routes, RPC endpoints).

### Stage 4 — Build the Repository Knowledge Model
**Status:** 🔴 High Priority Architecture Goal
**Goal:** Create the centralized "Brain" of GitCompass.
- Aggregate outputs from Stages 0, 1, 2, and 3 into a single cohesive internal representation.
- The model must unify: `Metadata` + `Structure` + `Technologies` + `Dependencies` + `Code AST` + `Git History`.

### Stage 5 — Connect Code + Git History
**Status:** ✅ Complete
**Goal:** Correlate structural code knowledge with temporal Git history.
- Cross-reference static analysis with commit timelines.
- Detect architectural events: When was a service introduced? When was a major dependency swapped?
- Track the lifecycle and evolution of specific APIs or modules over time.
- **Implementation:** `server/app/services/evolution_analyzer.py`, `server/app/routers/evolution.py`, `server/supabase/migrations/009_evolution_events.sql`

### Stage 6 — Architecture Evolution Engine
**Status:** 🔴 High Priority (Next Stage)
**Goal:** Deterministically group code/git events into a cohesive historical model.
- Deterministic detection of what changed and when.
- Group raw temporal changes into logical phases (e.g., "Foundation", "Feature Expansion").
- Identify candidate architectural events.
- Collect hard, deterministic evidence for each event (e.g., "File X deleted, Module Y created").

### Stage 7 — AI Reasoning Layer
**Status:** 🟠 Medium Priority
**Goal:** Introduce the LLM as a reasoning engine over the structured Evolution Model.
- Feed the deterministic evidence and Repository Knowledge Model to the LLM.
- Infer likely motivations behind the collected evidence.
- Synthesize the evidence into readable architectural stories and explain decisions.
- **Critical Constraint:** Explicitly distinguish factual evidence from AI inferences.

### Stage 8 — Repository Q&A
**Status:** 🟠 Medium Priority
**Goal:** Context-aware conversational interface.
- Retrieve specific slices of the Knowledge Model (e.g., dependency graph + commit history for a specific file).
- Use the LLM to synthesize highly accurate, context-rich answers to user queries (e.g., "Why was Redis introduced here?").

### Stage 9 — Architecture Visualization
**Status:** 🟡 Lower Priority (Refinement)
**Goal:** Frontend interactive visualization of the Knowledge Model.
- Node/Edge graphing of services, modules, and dependencies.
- Interactive drill-downs: clicking a service reveals its file count, commit velocity, and history.

### Stage 10 — Advanced Repository Archaeology
**Status:** 🟢 Future Milestone
**Goal:** Expert-level insights and technical debt analysis.
- **Architectural Drift:** Detecting when a codebase deviates from its original patterns.
- **Hotspots:** Intersecting high churn, high complexity, and multi-author metrics.
- **Knowledge Concentration:** Identifying bus-factor risks on a per-module basis.
- **Historical Context:** Explaining the historical / debt-driven reasons behind specific code blocks.
