# ADR-0001: Use a monorepo

- Status: Accepted
- Date: 2026-07-18

## Context

Fleet-OS spans robot code, versioned contracts, control-plane services, deployment assets,
tests, and a dashboard. Changes frequently cross those boundaries and must be tested together.

## Decision

Keep all Fleet-OS components in one repository. Each service remains independently buildable,
while root Make targets provide contract generation, linting, tests, and integration checks.
Generated contract code is committed so consumers and reviewers see the exact wire bindings.

## Consequences

Atomic contract-and-consumer changes are straightforward and CI can test the complete system.
Build contexts and workflows must use path filtering and caching as the repository grows.

