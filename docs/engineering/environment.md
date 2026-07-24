# Clinify Development Environment

> Canonical development environment for the Clinify Healthcare Operating System.

---

# Purpose

This document defines the officially supported development environment for the Clinify project.

Maintaining a consistent development environment ensures reproducible builds, reliable testing, predictable deployments, and simplified onboarding for future developers.

---

# Development Platform

| Component | Value |
|-----------|-------|
| Operating System | Ubuntu 22.04.5 LTS |
| Environment | Windows Subsystem for Linux (WSL2) |
| Distribution | Ubuntu Jammy |
| Architecture | x86_64 |

---

# Development Stack

| Component | Version |
|-----------|---------|
| Python | 3.10.12 |
| Node.js | 18.20.8 |
| npm | 10.8.2 |
| Yarn | 1.22.22 |

---

# Clinify Platform

| Component | Version |
|-----------|---------|
| Bench | 5.28.0 |
| Frappe | 15.107.3 |
| ERPNext | 15.108.0 |
| Healthcare | 15.1.19 |
| Clinify | 0.0.1 |

---

# Infrastructure Components

| Component | Version |
|-----------|---------|
| MariaDB | 10.6.22 |
| Redis | 6.0.16 |
| Git | 2.34.1 |

---

# Repository

GitHub Repository

https://github.com/asifnb7/clinify

---

# Local Development Paths

Bench

```
~/clinify-bench
```

Application

```
~/clinify-bench/apps/clinify
```

Documentation

```
~/clinify-bench/apps/clinify/docs
```

---

# Engineering Workflow

Development follows the engineering workflow below.

```
Architecture
        ↓
Engineering Specification
        ↓
Implementation
        ↓
Bench Build
        ↓
Bench Migrate
        ↓
Testing
        ↓
Git Commit
        ↓
Git Push
        ↓
Production Deployment
```

---

# Environment Management Principles

The Clinify development environment follows these principles:

- Maintain version consistency across development environments.
- Avoid unnecessary dependency upgrades during active development.
- Test upgrades before adopting them.
- Keep production and development environments aligned wherever practical.
- Document significant environment changes in this repository.

---

# Related Documents

- README.md
- repository.md
- git-workflow.md
- architecture.md

---

# Revision History

This document is maintained through Git version control.
