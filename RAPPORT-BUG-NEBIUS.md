# Bug report — Nebius Token Factory: reasoning models silently return empty `content`

**Reported:** 18 September 2026
**Endpoint:** `POST https://api.studio.nebius.com/v1/chat/completions`
**Reporter:** Patrick Fotso — Code Nomi Nomi (`nominomi`), Nebius × NVIDIA Global AI Hackathon, Personal AI track
**Severity:** High — silent data loss, no error raised, standard clients crash

---

## Summary

On Nebius Token Factory, reasoning models spend their token budget on the
reasoning step **first**. When `max_tokens` is too small, the reasoning
consumes the entire budget, the final answer is never written, and the API
returns:

```json
{
  "choices": [{
    "message": { "content": null, "reasoning_content": "…scratch notes…" },
    "finish_reason": "length"
  }]
}
```

**No error is raised.** The HTTP call succeeds with `200 OK`. The response is
simply empty — and the standard OpenAI client crashes downstream on
`NoneType has no attribute 'strip'`.

This is not a model quality issue. It is a **silent-failure** issue: the caller
cannot distinguish "the model had nothing to say" from "we ran out of room
before the model said anything".

---

## Environment

- Endpoint: Nebius Token Factory, OpenAI-compatible `/v1/chat/completions`
- Client: standard `openai` Python client (and plain `urllib.request`)
- Temperature: `0`
- Date of measurement: 15–16 September 2026
- Same prompt, same settings, only `max_tokens` varied

---

## Affected models

All four NVIDIA Nemotron models served by Nebius were tested on the same
probe, at three budgets. Values are the length of `message.content` in
characters; **EMPTY** means `content` was `null` / `""`.

| Model | `max_tokens: 100` | `max_tokens: 300` | `max_tokens: 900` |
|---|---|---|---|
| `nvidia/Nemotron-3-Ultra-550b-a55b` | 205 chars | 205 chars | 205 chars |
| **`nemotron-3-super-120b-a12b`** | **EMPTY** | **EMPTY** | 153 chars |
| `NVIDIA-Nemotron-3-Nano-30B-A3B` | 151 chars | 151 chars | 151 chars |
| `Nemotron-3_5-Lightning` | 399 chars | 1244 chars | 149 chars |

`nemotron-3-super-120b-a12b` is the clear offender: two of three budgets
return nothing at all, and even at 900 tokens it is the shortest.

---

## Steps to reproduce

### 1. Plain HTTP (no SDK)

```bash
curl -s https://api.studio.nebius.com/v1/chat/completions \
  -H "Authorization: Bearer $NEBIUS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nemotron-3-super-120b-a12b",
    "messages": [{"role": "user", "content": "What is the capital of Cameroon?"}],
    "max_tokens": 300,
    "temperature": 0
  }'
```

Observed: `choices[0].message.content == null`,
`choices[0].finish_reason == "length"`, HTTP `200`.

### 2. Standard OpenAI client — crashes

```python
from openai import OpenAI

client = OpenAI(base_url="https://api.studio.nebius.com/v1/",
                api_key=NEBIUS_API_KEY)

r = client.chat.completions.create(
    model="nemotron-3-super-120b-a12b",
    messages=[{"role": "user", "content": "What is the capital of Cameroon?"}],
    max_tokens=300,
)
print(r.choices[0].message.content.strip())
# AttributeError: 'NoneType' object has no attribute 'strip'
```

The crash is not the bug — the **silence** is. A caller who does not know to
check for `null` will treat the empty string as the model's answer.

---

## Expected behaviour

One of:

1. `content` is populated with the final answer; **or**
2. `finish_reason` distinguishes "ran out of budget during reasoning" from a
   normal stop; **or**
3. An explicit error/field states that the budget was exhausted before the
   answer was produced.

Ideally, the reasoning tokens should not consume the budget reserved for the
answer — or the response should expose how many tokens the reasoning used, so
the caller can retry with a larger budget.

## Actual behaviour

`content: null`, `finish_reason: "length"`, HTTP `200`, no warning. The
reasoning text is available in `reasoning_content`, but it is **scratch notes,
not a claim** — it must never be handed back to a user as the answer.

---

## Root cause (as understood by the reporter)

Reasoning models generate a private chain of thought before the visible
answer. When `max_tokens` covers the reasoning but not the answer, generation
stops (`finish_reason: "length"`) with the answer unwritten. Because the
request itself succeeded, nothing surfaces the truncation except the empty
`content`.

---

## Workaround we ship

Arthur (our assistant) treats an empty `content` as a **first-class outcome**,
not as an answer:

- he never returns `reasoning_content` as if it were the answer;
- he says, in plain language, that the model thought too long and had no room
  left to answer;
- he raises the default budget to 900 tokens for these models;
- he logs the `finish_reason` so the failure is visible.

See `nemotron_nebius.py` in this repository (`if not texte:` branch).

---

## Suggested fixes for Nebius

1. **Reserve answer budget** separately from reasoning budget, or warn when
   `max_tokens` is below the model's typical reasoning length.
2. **Expose `reasoning_tokens`** in the usage block so callers can retry.
3. **Return a distinct `finish_reason`** (e.g. `reasoning_budget_exhausted`)
   instead of the generic `length`.
4. **Document it.** The model card should state the recommended `max_tokens`
   floor for reasoning models.

---

## Impact

Any application using these models with a "normal" `max_tokens` (e.g. 100–300,
perfectly reasonable for non-reasoning models) can silently receive nothing
and display it as the model's answer. For assistants whose whole value is
honesty, a silent empty answer is the worst possible failure.

---

## Reproduce-it-yourself harness

`test_etage_nemotron.py` in this repository exercises the Nebius layer and
prints the exact request that would be sent. `test_nemotron_branche.py` makes a
real call and shows the model, the latency, and the answer.
