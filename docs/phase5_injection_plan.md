# Phase 5 — Injection Point Plan

## Starter Round

The starter round injects errors only at the Research Agent output stage.

This keeps the first injection experiments simple and isolates the effect of an
error introduced into the upstream Research output before it is passed to
downstream agents.

| Error Type | Research Output | Summary Output |
|---|---|---|
| Factual | Inject | Deferred |
| Numerical | Inject | Deferred |
| False Premise | Inject | Deferred |

## Injection Stage

For the current starter round:

**Research Agent output → Error Injector → Summarizer Agent → Action Agent**

The injector modifies the Research Agent output before that output is passed
downstream.

## Deferred Expansion

Summary-stage injection will be added only after the Research-stage injection
round is working correctly.

This follows the Phase 5 roadmap requirement to start with Research-stage
injection and add Summary-stage injection afterward.
