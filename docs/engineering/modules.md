# Clinify Modules

> Functional architecture and module map for the Clinify Healthcare Operating System.

---

# Purpose

This document describes the major functional modules of Clinify, their responsibilities, dependencies, and implementation locations.

It serves as the architectural map for developers and AI coding assistants, helping them understand where functionality belongs and how modules interact.

---

# Engineering Principles

Every module should follow the core engineering philosophy:

- Preserve existing architecture.
- Extend ERPNext through supported extension mechanisms.
- Keep business logic in Python.
- Keep JavaScript focused on presentation.
- Avoid duplicate implementations.
- Maintain upgrade safety.

---

# Patient Module

## Purpose

Manage patient registration and demographic information.

### Primary DocTypes

- Patient

### Backend

- clinify/patient.py

### Frontend

- ERPNext Patient Form

### Responsibilities

- Patient registration
- Patient ID generation
- Demographic management

---

# Appointment Module

## Purpose

Manage patient appointments and scheduling.

### Primary DocTypes

- Patient Appointment

### Backend

- clinify/reception.py

### Frontend

- Reception Dashboard
- Appointment List

### Responsibilities

- Appointment scheduling
- Daily appointment queue
- Appointment status tracking

---

# Reception Workspace

## Purpose

Provide reception staff with a unified operational dashboard.

### Backend

- clinify/reception.py

### Frontend

- clinify/page/reception_dashboard/

### Responsibilities

- Patient search
- Patient summary
- Appointment history
- Billing queue
- Ready for billing queue

---

# Doctor Workspace

## Purpose

Support efficient clinical consultations.

### Primary DocTypes

- Patient Encounter

### Backend

- clinify/encounter.py

### Responsibilities

- Consultation workflow
- Clinical notes
- Diagnosis
- Prescription
- Procedures

---

# Billing Module

## Purpose

Generate and manage patient billing.

### Primary DocTypes

- Sales Invoice

### Backend

- clinify/billing.py

### Responsibilities

- Invoice generation
- Billing validation
- Payment status
- Outstanding balance

---

# Dental Module

## Purpose

Manage dental treatment planning and procedure billing.

### Primary DocTypes

- Dental Treatment Plan
- Dental Planned Procedure

### Backend

- clinify/billing.py

### Responsibilities

- Treatment planning
- Procedure completion
- Procedure-to-item mapping
- Invoice generation

---

# Pharmacy Module

## Purpose

Manage prescriptions and medication dispensing.

### Primary DocTypes

- Prescription
- Sales Invoice

### Status

Planned

---

# Laboratory Module

## Purpose

Manage laboratory investigations and reports.

### Status

Planned

---

# Inventory Module

## Purpose

Manage medical inventory and consumables.

### Status

Planned

---

# Reporting Module

## Purpose

Provide operational and management reporting.

### Status

Planned

---

# SaaS Platform

## Purpose

Support multi-tenant deployment, subscription management, and platform administration.

### Status

Future Phase

---

# Module Dependencies

Patient
    ↓
Appointment
    ↓
Reception
    ↓
Doctor
    ↓
Billing
    ↓
Payment
    ↓
Reporting

Dental extends the standard consultation and billing workflow.

---

# Related Documents

- README.md
- architecture.md
- repository.md
- ai-development.md

---

# Revision History

Maintained through Git version control.
