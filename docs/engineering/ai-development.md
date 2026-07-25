# AI Development Guide

> Standard operating guide for AI coding assistants working on Clinify.

---

# Purpose

This document defines how AI coding assistants must operate when contributing to the Clinify project.

It supplements the existing engineering documentation and must be read before implementation.

---

# Read First

Before making any code changes, review:

- README.md
- architecture.md
- coding-standards.md
- git-workflow.md
- repository.md
- environment.md

These documents are the primary engineering references.

---

# AI Operating Principles

AI assistants must:

- Preserve the existing architecture.
- Prefer extension over modification.
- Keep ERPNext and Frappe core untouched unless explicitly instructed.
- Keep business logic in Python.
- Keep JavaScript focused on presentation.
- Produce maintainable, readable code.
- Avoid duplicate implementations.
- Ask before introducing schema changes.

---

# Development Workflow

Every feature follows:

Architecture
→ Sprint Specification
→ Backend
→ Frontend
→ Bench Build
→ Bench Migrate
→ Browser Testing
→ Git Commit
→ Documentation Update

---

# Allowed Changes

Typical implementation files include:

- clinify/reception.py
- clinify/billing.py
- clinify/patient.py
- clinify/public/
- clinify/page/
- fixtures/

---

# Forbidden Changes

Do not modify:

- Frappe core
- ERPNext core
- Healthcare core

unless explicitly approved.

---

# Output Expectations

Implementations should include:

- Exact file paths
- Full replacement functions when appropriate
- Testing steps
- Bench commands
- Suggested Git commit message

---

# Documentation

If an architectural decision changes, update the relevant documentation in the repository.
