# Clinify Project Knowledge Base (CPKB)

> **Healthcare, Simplified.**

Welcome to the Clinify Project Knowledge Base (CPKB).

The CPKB is the permanent knowledge repository for the Clinify project. It exists alongside the source code and is maintained under version control as part of the Git repository.

Its purpose is to preserve the project's architecture, engineering decisions, product vision, and development workflow so that every contributor—human or AI—can quickly understand the project without relying on previous conversations.

---

# What is Clinify?

Clinify is a clinic-first Healthcare Operating System built on top of ERPNext Healthcare and the Frappe Framework.

ERPNext Healthcare provides the transactional healthcare platform.

Clinify provides the workflow, user experience, automation, and clinical intelligence required for modern outpatient clinics.

---

# Purpose of the CPKB

The CPKB serves as the project's single source of truth for:

- Product Vision
- Engineering Principles
- Architecture
- Development Rules
- Sprint Planning
- Major Engineering Decisions
- Founder Notes

The objective is to ensure that project knowledge evolves together with the source code.

---

# Repository Structure

```
docs/

README.md

00_PROJECT_STATUS.md
01_PRODUCT_VISION.md
02_DEVELOPMENT_RULES.md
04_SPRINT_BOARD.md
05_PROJECT_DECISIONS.md
99_FOUNDER_NOTES.md

modules/
adr/
```

---

# How to Use the CPKB

Every development session should begin by reviewing the following documents:

1. 00_PROJECT_STATUS.md
2. 04_SPRINT_BOARD.md
3. 05_PROJECT_DECISIONS.md

These documents describe the current state of the project and should always be considered the authoritative reference.

---

# Engineering Philosophy

Clinify follows a workflow-first approach.

The software is designed around how clinics operate rather than how databases are structured.

Every engineering decision should satisfy three perspectives:

- Clinical
- Engineering
- Business

---

# CPKB Principles

- The CPKB is part of the Git repository.
- The CPKB evolves together with the application.
- Every completed sprint updates the relevant CPKB documents.
- Every architectural decision has one authoritative location.
- The CPKB records accepted architecture and implemented decisions—not brainstorming or discarded ideas.

---

# Current Development Phase

Clinify Pilot v1

Current Sprint:

Doctor Workflow

Refer to:

- 00_PROJECT_STATUS.md
- 04_SPRINT_BOARD.md

for the latest project status.

---

Maintained by:

Clinify Engineering Team
