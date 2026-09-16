# How Arthur decides

Arthur answers in **four layers**. Each one is tried in order. The first that
knows, answers. When none of them knows, **he says so**.

```
        ┌──────────────────────────────────────────────┐
  you   │  "What is the Zorglub circuit?"              │
        └───────────────────┬──────────────────────────┘
                            ▼
        ┌──────────────────────────────────────────────┐
  L1    │  TOOLS — reads live state                    │  1–10 ms
        │  clock, running services, network            │  local
        └───────────────────┬──────────────────────────┘
                            ▼ nothing
        ┌──────────────────────────────────────────────┐
  L2    │  RULES — 233 written topics                  │  0.14 ms
        │  whole-word match, rare words weigh more     │  local, offline
        └───────────────────┬──────────────────────────┘
                            ▼ nothing
        ┌──────────────────────────────────────────────┐
  L3    │  DOCUMENTS — what was ingested               │  ~300 ms
        │  100 documents, 1197 chunks                  │  local network
        └───────────────────┬──────────────────────────┘
                            ▼ nothing
        ┌──────────────────────────────────────────────┐
  L4    │  NEMOTRON — nvidia/Llama-3_3-Nemotron-       │  ~2 s
        │  Super-49B-v1_5, hosted on Nebius            │  cloud
        └───────────────────┬──────────────────────────┘
                            ▼ nothing
        ┌──────────────────────────────────────────────┐
        │  ADMISSION — "I don't know."                 │  1 ms
        │  Never a guess. Never a fabrication.         │
        └──────────────────────────────────────────────┘
```

## Why layers, and why in this order

**Cost and honesty both go down the stack.** A written rule is free, instant,
and cannot hallucinate. A large model is slow, costs money, and *can* invent.
So the cheap, safe layers answer first — and the model is the last resort, not
the first reflex.

Every answer carries its **source**: `outil`, `regles`, `documents`,
`nemotron`, or `aveu`. You always know which layer spoke.

## The admission layer is the product

Measured on 15 September 2026, same question to both:

```
"Which vulnerability affects the Debian Linux kernel recently?"

A common 3B model  ->  "CVE-2023-2687"   FABRICATED, dated 2023
Arthur             ->  "I don't know."
```

A confident wrong answer is worse than silence. Layer 5 exists so that silence
is always available.

## Two hard rules, enforced in code

**Questions about the house never reach the cloud.** Measured: the large model
scores **0 out of 7** on questions about this specific domain — and it invents.
So if a question contains house vocabulary and no rule matches, Arthur admits
rather than asking a model that will guess.

**Health questions are refused before layer 1.** Arthur is not built for
doctors, and the refusal happens before any layer runs.

## Plugins

Plugins sit **beside** the stack, not inside it. A plugin runs only when its
own trigger words appear, and Arthur's own rules always win. A disabled plugin
is never loaded. A crashing plugin is caught and reported — it cannot take
Arthur down.

Cost when no plugin applies: **0.011 ms**.

## Offline

Layers 1 and 2 need nothing. With the network cable pulled, Arthur still
answers about the domain in **0 ms** and admits ignorance for everything else.
Verified by `test_haichi_hors_ligne.py` — 6 checks, all green.

## What is measured, and where

| Claim | Command |
|---|---|
| answers correctly, never health | `python3 test_haichi_repond_juste.py` |
| tools read live state | `python3 test_haichi_outils.py` |
| routing across layers | `python3 test_haichi_trois_etages.py` |
| works offline | `python3 test_haichi_hors_ligne.py` |
| Nemotron layer | `python3 test_etage_nemotron.py` |
| plugins | `python3 test_haichi_greffons.py` |
| a stranger can install it | `bash test_installation.sh` |
