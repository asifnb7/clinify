# Clinify Engineering Knowledge Base

> Engineering documentation for the Clinify Healthcare Operating System.

---

# Purpose

The Clinify Engineering Knowledge Base (EKB) is the central repository for all technical documentation related to the Clinify application.

Its purpose is to document the project's engineering philosophy, architecture, development workflow, repository structure, coding standards, deployment strategy, and operational practices.

The Engineering Knowledge Base is maintained under version control and evolves together with the source code.

---

# Engineering Philosophy

Clinify is engineered as a modern, clinic-first Healthcare Operating System built on top of ERPNext Healthcare and the Frappe Framework.

The project emphasizes:

- Simplicity
- Maintainability
- Scalability
- Upgrade safety
- Developer productivity
- Long-term sustainability

Engineering decisions prioritize maintainability over short-term convenience.

---

# Core Engineering Principles

The following principles guide every engineering decision:

- Architecture before implementation.
- Extend ERPNext whenever possible instead of modifying core code.
- Backend → Frontend → UX.
- Test before commit.
- Commit before deployment.
- Git is the single source of version history.
- Documentation evolves with the product.
- Conversations are temporary. Documentation is permanent.

---

# Engineering Documentation

The Engineering Knowledge Base is divided into focused documents.

| Document | Description |
|-----------|-------------|
| environment.md | Development environment and software versions |
| repository.md | Repository layout and organization |
| git-workflow.md | Git workflow and branching strategy |
| architecture.md | Technical architecture and design philosophy |
| coding-standards.md | Engineering rules and coding conventions |

Additional engineering documents will be added as the project evolves.

---

# Development Workflow

Every significant feature follows the same engineering lifecycle.

```
Idea
    ↓
Product Definition
    ↓
Architecture
    ↓
Engineering Specification
    ↓
Implementation
    ↓
Testing
    ↓
Git Commit
    ↓
Deployment
    ↓
Documentation Update
```

---

# Documentation Philosophy

Documentation is treated as part of the product.

Important engineering knowledge should be preserved inside the repository rather than relying on memory or previous conversations.

Every document should focus on one topic and serve as the single source of truth for that topic.

---

# Related Documentation

- ../README.md
- ../01_PRODUCT_VISION.md
- ../02_DEVELOPMENT_RULES.md
- ../05_PROJECT_DECISIONS.md

---

# Revision History

This document is maintained through Git version control.

Refer to Git history for all revisions.
