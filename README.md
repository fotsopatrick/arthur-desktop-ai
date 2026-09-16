# Arthur — the assistant that says "I don't know"

Arthur answers from **written rules**, on your own machine, **with no network**.
When he doesn't know, he says so. He never invents.

<p align="center">
  <img src="haichi.png" alt="Arthur" width="180"/>
</p>

## Why this exists

AI assistants invent answers — confidently. Measured on 15 September 2026, the
same question asked twice:

```
Q: "Which vulnerability affects the Debian Linux kernel recently?"

A common 3B model  ->  "CVE-2023-2687"    FABRICATED, and dated 2023
Arthur             ->  "I don't know."
```

And on something that does not exist at all:

```
Q: "What is the Zorglub circuit?"

A common 3B model  ->  "a motor race held on the Eiffel Tower"
Arthur             ->  "I don't know. No written rule covers this."
```

The second answer is worthless. The third one is **trustworthy**. That is the
entire product.

## Install

One command. Nothing to configure.

```bash
./INSTALLER.sh
```

It checks Python, verifies every file is present, runs the full test suite, and
tells you exactly what works. **It downloads nothing and contacts no server.**

## Run it

```bash
python3 haichi_avatar.py                      # the desktop companion
python3 haichi_avatar.py "who is Victor"      # ask a question right away
```

## Check it yourself

Don't take our word for it. Every claim below is a test you can run:

| Command | What it proves |
|---|---|
| `python3 test_haichi_repond_juste.py` | answers correctly, never discusses health |
| `python3 test_haichi_outils.py` | his tools read live state, not stale rules |
| `python3 test_haichi_hors_ligne.py` | **works with the network cable pulled** |
| `python3 test_haichi_greffons.py` | plugins load, fail safely, and stay out of the way |
| `bash test_haichi_avatar.sh` | the window is borderless, on top, transparent |
| `bash test_installation.sh` | a stranger can install this from scratch |

## How he decides

| Layer | What it does | Measured |
|---|---|---|
| 1 — tools | reads live state: clock, services, network | 1–10 ms |
| 2 — rules | 233 written topics about your own domain | **0.14 ms** |
| 3 — documents | searches what has been ingested | ~300 ms |
| 4 — large model | **NVIDIA Nemotron**, hosted on **Nebius** | ~2 s |
| — admission | when none of the four knows, **he says so** | 1 ms |

No embeddings. No weights. No GPU. No API key required for layers 1 and 2.

## Offline by design

Layers 1 and 2 need **nothing**. Pull the network cable and Arthur still answers
about your own domain in **0 ms**, and admits ignorance for everything else.

Measured, not claimed: `test_haichi_hors_ligne.py` — 6 checks, all green.

## Plugins

Add a capability without touching his brain. A plugin is a folder with two files:

```
greffons/whatsapp/greffon.json    name, trigger words, on/off
greffons/whatsapp/greffon.py      one function: repondre(question, settings)
```

Rules, each one learned the hard way:

1. A disabled plugin is **never loaded**.
2. A crashing plugin **does not break Arthur** — he reports it and moves on.
3. Arthur's own rules always win over a plugin.
4. **Whole words only.** French *tour* is spelled inside *dé-**tour**-nement*;
   that bug once made him answer with the HIV replication cycle.
5. Plugins cost **0.011 ms** when they don't apply.

## Traps already paid for

- **A word hidden inside another word.** See rule 4 above. Real bug, real fix.
- **A procedure matched on one common word.** "how much is 17 times 4" returned
  an internal procedure, because *fois* (times) belonged only to it. Rare in
  **our data** does not mean rare in **the language**. Now a procedure needs two
  matching words.
- **Health questions.** Refused outright. This is not built for doctors.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full diagram of the four layers
and why they run in that order.

The cloud layer uses **`nvidia/Llama-3_3-Nemotron-Super-49B-v1_5`**, served by
**Nebius**. It is the *last* resort, never the first reflex — and questions
about your own domain never reach it.

## Security

See [SECURITE.md](SECURITE.md). Short version: Arthur reads, he does not write,
and he sends nothing anywhere.

## License

MIT. See [LICENSE](LICENSE).
