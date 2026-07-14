<!--
Sync Impact Report
- Version change: [TEMPLATE] → 1.0.0 (initial ratification; no prior concrete version existed)
- Modified principles: N/A (first concrete set, replacing template placeholders)
- Added sections:
  - I. Test-First Development (NON-NEGOTIABLE)
  - II. Pattern-Driven Extensibility
  - III. Review-Gated Production Releases (NON-NEGOTIABLE)
  - Quality & Design Standards
  - Development Workflow
  - Governance (concrete rules)
- Removed sections: none (template placeholders only)
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md (Constitution Check gate derives from this file dynamically; no static edits needed)
  - ✅ .specify/templates/spec-template.md (no hardcoded principle references found)
  - ✅ .specify/templates/tasks-template.md (no hardcoded principle references found)
  - ✅ .specify/templates/checklist-template.md (no hardcoded principle references found)
- Follow-up TODOs: none
-->

# Telegram Bible Bot Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)

Every feature, integration, and bug fix MUST be developed test-first: write a failing test
that specifies the desired behavior, confirm it fails for the expected reason, then write
the minimum code required to make it pass, refactoring only once green (Red-Green-Refactor).
No change may be merged without automated tests that demonstrate the behavior it introduces
or fixes. Tests are written before implementation, not retrofitted after.

**Rationale**: TDD is this project's foundational engineering discipline. It is the
mechanism that guarantees correctness for a bot that handles live user interactions and
delivers scripture content, where silent regressions directly reach end users.

### II. Pattern-Driven Extensibility

Every new integration (additional messaging platforms, Bible translation/content sources,
notification channels, etc.) or feature MUST be added through a deliberate, appropriate
design pattern (e.g., Adapter or Strategy for external integrations, Factory for content
source selection, Observer for event/notification fan-out) rather than ad-hoc conditionals
layered onto existing code. The developer proposing the change is responsible for selecting
a pattern that keeps core bot logic closed for modification and open for extension, and MUST
state the chosen pattern and reasoning in the PR or plan description when it is not obvious.
A pattern MUST NOT be introduced speculatively — only when at least two current or clearly
planned use cases justify it.

**Rationale**: The project is expected to accumulate integrations and features over time;
consistent, intentional design is what keeps that growth from degrading into unmaintainable
branching logic.

### III. Review-Gated Production Releases (NON-NEGOTIABLE)

No change reaches production without prior review and explicit approval. Every change MUST
pass through: (1) an independent code review verifying tests exist and were written first,
correctness, design-pattern appropriateness, and compliance with this constitution, and (2)
an explicit approval step, before deployment. Self-merged, unreviewed, or CI-green-only
changes MUST NOT be deployed to production.

**Rationale**: A review-first gate catches correctness, security, and design issues before
they reach real Telegram users, and creates accountability for what goes live.

## Quality & Design Standards

All integrations and features MUST include automated tests at the appropriate level (unit
tests at minimum; integration tests for external dependencies such as the Telegram API or
Bible content providers). Design-pattern choices for new integrations MUST be stated
explicitly in the PR or plan description — which pattern, and why. Abstractions and patterns
MUST NOT be introduced ahead of demonstrated need (YAGNI): favor the simplest design that
satisfies Principle II without over-engineering for hypothetical future integrations.

## Development Workflow

Work proceeds as: write failing test(s) → implement the minimal passing solution → open a
pull request → independent review → explicit approval → merge → deploy to production.
Reviewers MUST verify tests were written first, correctness, design-pattern appropriateness,
and constitution compliance before approving. No direct commits to the production deployment
branch are permitted; all changes flow through pull request review, and a production deploy
MUST NOT be triggered without an explicit, recorded approval.

## Governance

This constitution supersedes ad-hoc practices and prior undocumented conventions. Amendments
require a documented rationale, a version bump per the semantic versioning policy below, and
propagation to any dependent templates or workflow docs that reference changed principles.

Versioning policy:
- **MAJOR**: Backward-incompatible governance changes, or removal/redefinition of a principle.
- **MINOR**: A new principle or materially expanded guidance is added.
- **PATCH**: Clarifications, wording, or non-semantic refinements.

All pull requests and reviews MUST verify compliance with these principles; reviewers MUST
block merges that skip test-first development, omit design-pattern justification for new
integrations, or bypass the review-approval gate before production deployment. Any added
complexity (new pattern, new dependency, new abstraction layer) MUST be justified in the PR
description against a simpler alternative.

**Version**: 1.0.0 | **Ratified**: 2026-07-13 | **Last Amended**: 2026-07-13
