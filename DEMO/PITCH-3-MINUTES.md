# Pactra 3-Minute Pitch

## Problem

For a small business, making a payment is easy; governing it is not. Requests
arrive through forms and messages, spending rules live in people's heads, and
approval evidence gets separated from the financial record. Adding AI can
make initiation faster while increasing the risk that intent is mistaken for
authority.

## Product

Pactra is a payment-governance workspace. A business configures deterministic
limits, category budgets, restricted vendors, and an approval threshold. Every
request—manual or AI-assisted—enters the same authenticated backend service.

The service evaluates policy in a fixed order, reserves simulated funds once,
and chooses one truthful state: blocked, pending approval, executing,
completed, failed, rejected, cancelled, or reversed. A preview never replaces
the final server decision.

## Why the AI is safe by design

Gemini can select a declared function and extract structured intent. Pactra
still treats that output as untrusted input. The backend validates the function
and arguments, scopes the action to the authenticated tenant, and applies the
same policy and approval rules as the manual workflow. The model cannot approve
itself, call PayPal directly, or mutate wallet and ledger records.

When Gemini is slow or unavailable, bounded error handling records the failure
and deterministic fallback preserves the governed workflow. Provider success
is never inferred from a text response.

## Accountability

Each transaction has a receipt containing the policy trace, approval event,
execution attempt, ordered lifecycle, and balanced ledger entries. PayPal
Sandbox submission, when enabled, belongs only to a leased background worker.
Pactra waits for item-level success before capture, preserves reservations for
unknown outcomes, and reconciles stable identifiers instead of blindly
retrying.

## Current boundary and future

Pactra is a sandbox-only product. It does not claim to be a bank, audited
financial infrastructure, or a live-money processor. The current value is the
governance and evidence layer. A future release could add separate approver
roles, stronger operational telemetry, and additional regulated provider
integrations through the same deterministic control boundary.
