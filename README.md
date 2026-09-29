# Arthur (Code Name: `nominomi`) — the assistant that says "I don't know"

**Codename:** `nominomi`

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

One command, from nothing to running. Nothing to configure.

```bash
git clone https://github.com/fotsopatrick/arthur-desktop-ai && cd arthur-desktop-ai && bash INSTALLER.sh
```

Already cloned? Then simply:

```bash
bash INSTALLER.sh
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
| 1 — tools | reads live state: clock, services, network, **System C governance & agents** | 1–10 ms |
| 2 — rules | 229 written topics about your own domain | **0.14 ms** |
| 3 — documents | searches `documents/` on this machine (`rag_local.py`, BM25, no network), then remote stores if configured — **quotes the file** when no large model is available | ~1 ms local |
| 4 — large model | **NVIDIA Nemotron**, hosted on **Nebius** | ~2 s |
| — admission | when none of the four knows, **he says so** | 1 ms |

No embeddings. No weights. No GPU. No API key required for layers 1, 2 and 3.

### Local documents (RAG)

Drop `.md` or `.txt` files into `documents/` (or list other folders under
`"rag_dossiers"` in `reglages-maison.json`, or in `ARTHUR_DOCUMENTS`). Arthur
searches them with no network and no dependency. He answers only when the
passages really contain the important words of the question, and he names
the file he read. Otherwise: "I don't know".

```bash
python3 rag_local.py --etat                          # which folders, how many passages
python3 rag_local.py --json-chercher "my question"   # what he would read
```

### The decision graph (LangGraph)

`arthur_graphe.py` draws the same decision path as an explicit graph:

```
local ──(knows, or refuses)─────────────────────────────────► end
  └─(doesn't know, may ask)─► remote_documents ─► large_model ─► end
                                                      └─(nothing)─► admission
```

Health, secrets, gibberish and domain questions without a written rule are
settled at `local` and **never** reach the large model. With `pip install
langgraph` the graph runs on LangGraph (and `--dessin` prints it as Mermaid);
without it, a built-in runner walks the exact same nodes.

```bash
python3 arthur_graphe.py "what is the capital of Cameroon?"
python3 arthur_graphe.py --dessin
```

### Choose the large model (layer 4) in one command

```bash
python3 arthur_cerveau.py            # which model answers now, and the choices
python3 arthur_cerveau.py nebius     # NVIDIA Nemotron on Nebius Token Factory (needs NEBIUS_API_KEY)
python3 arthur_cerveau.py qwen       # a Qwen server on your own network
python3 arthur_cerveau.py local      # Nemotron through ollama, on this machine
```

**Any other large model, interchangeably.** DeepSeek, Claude, Mistral,
OpenRouter, Groq, OpenAI, a local ollama model — declare it once under
`"cerveaux"` in `reglages-maison.json` (copy from `cerveaux.exemple.json`),
then pick it by name:

```bash
python3 arthur_cerveau.py deepseek   # or claude, mistral, ollama...
python3 fournisseurs.py              # every brain, paid or free
```

`fournisseurs.py` speaks the OpenAI-compatible `/chat/completions` format,
Claude through the official `anthropic` SDK, and ollama. API keys never go in
the file — only the *name* of the environment variable holding them. If the
chosen brain is silent, Arthur falls back to `"cerveau_repli"` (default: Qwen).

**Spending is off by default.** Every paid brain goes through
`budget_nebius.py`: nothing leaves until `~/.config/budget-nebius.json` holds
`"paiement_autorise": 1`, a price (`euros_par_million`) and a cap
(`euros_max`), on top of daily and lifetime token caps.

It takes effect on the next question, no restart. Any coding agent (Claude Code,
opencode, Antigravity) can run it; agents that speak MCP also get the
`arthur_cerveau` tool from `mcp_arthur_server.py`. If Nebius runs out of credit,
Arthur **says so** and falls back to the next brain — he never invents.

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

The cloud layer uses **`nvidia/Nemotron-3-Ultra-550b-a55b`**, served by
**Nebius**. It is the *last* resort, never the first reflex — and questions
about your own domain never reach it.

We also report a real bug we hit there — reasoning models returning an empty
answer with no error: see [RAPPORT-BUG-NEBIUS.md](RAPPORT-BUG-NEBIUS.md).

## Security

See [SECURITE.md](SECURITE.md). Short version: Arthur reads, he does not write,
and he sends nothing anywhere.

## License

MIT. See [LICENSE](LICENSE).
