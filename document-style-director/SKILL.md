---
name: document-style-director
description: Interactively choose and lock a context-aware, high-quality visual system for new DOCX, Word, or Google Docs documents and major visual redesigns. Use alongside the documents skill when the user has not supplied a controlling template or exact visual direction; do not use for minor edits, conversions, or template-faithful work.
---

# Document Style Director

Choose the document's visual direction from its content and real reading context,
then let the `documents` skill perform authoring, OOXML work, rendering, and QA.
This skill augments `documents`; it does not replace any of that skill's quality,
Google Docs, editing, or delivery requirements.

## Priority and scope

Apply this skill before authoring when the task is a new document, a major
repackage, or an explicit redesign. Skip style selection when:

- a supplied or retained template/reference is the design authority;
- the user already specified an exact visual system and it is feasible;
- the task is a minor/local edit, conversion, redline, comment pass, or repair;
- the user explicitly declines style exploration.

A style brief locked by this skill counts as user-provided visual direction for
the `documents` skill. Do not subsequently open the artifact-template picker
unless the user asked to browse templates or selected that route during style
selection.

## Read context before asking

Inspect the prompt, conversation, attachments, source content, and destination.
Infer a context envelope:

- document job/archetype;
- primary audience and their familiarity;
- reader action: decide, approve, learn, operate, compare, complete, or trust;
- content geometry: prose, data, steps, tables, forms, visuals, or mixed;
- tone and stakes;
- expected length and reading conditions;
- Word versus native Google Docs destination;
- brand, accessibility, locale, and printing constraints.

Do not ask the user to repeat information already available. If a missing fact
would materially change the document itself, clarify that fact before style
selection. Otherwise make a reasonable inference and expose it in the candidate
rationale.

## Selection modes

- **Guided (default):** recommend three context-fit directions and obtain a
  choice before authoring.
- **Auto:** choose and lock the top direction without pausing when the user says
  to use judgment, choose freely, surprise them, avoid questions, or optimize
  for speed.
- **Exact:** resolve the user's named style and ask only about a consequential
  incompatibility.

Read [references/style-selection.md](references/style-selection.md) for Guided
mode, candidate construction, and elicitation rules.

## Resolve candidates

Resolve `<this-skill-dir>` to the directory containing this `SKILL.md`. Use the
deterministic resolver after inferring the context envelope:

```bash
python <this-skill-dir>/scripts/resolve_style.py \
  --archetype decision_memo \
  --audience executive \
  --purpose decide \
  --shape mixed \
  --tone formal \
  --surface word
```

The resolver returns three certified recipes with distinct visual systems when
possible. Never present raw style IDs alone. For each candidate, communicate:

1. its localized display name;
2. why it fits this specific content and audience;
3. typography, palette, density, and opening treatment;
4. one honest tradeoff.

Do not improvise an unregistered cross-product. Choose a certified recipe or
apply a user-requested change as a named override after checking compatibility.
The catalog is [references/style_catalog.json](references/style_catalog.json).

## Interactive choice

In Guided mode, use `request_user_input` once when it is available. Use up to
three questions:

1. **Direction.** The first option label must be exactly
   `Use your judgment (Recommended)` and its description must name the top
   context-fit recipe. The other two options are the distinct alternatives.
2. **Density.** Offer judgment, airy, or compact only when density materially
   affects usability.
3. **Opening.** Offer judgment, minimal, or feature-led only when the opening
   treatment materially affects the document.

If `request_user_input` is unavailable, ask one concise chat question containing
the three candidate cards and say that replying with just a number is enough.
Pause before authoring. Do not turn Guided mode into a long design interview.

Interpret `Use your judgment` as authorization to select the top recipe and its
recommended density/opening, not as a request for another question.

## Lock the style brief

After the choice, generate the fully resolved style contract before drafting:

```bash
python <this-skill-dir>/scripts/resolve_style.py \
  --choose executive-decision-navy \
  --density balanced \
  --opening memo_masthead \
  --surface word \
  --output style-spec.json
```

The locked contract must record the recipe, archetype, visual system, density,
opening, exact token map, rationale, and named overrides. Keep it stable through
the document. Reopen style selection only when the user changes direction or
rendered evidence shows that the selected density/form is unusable.

## Authoring and quality contract

Read [references/implementation.md](references/implementation.md) before using
a resolved contract in a DOCX builder. Then follow the `documents` skill in
full, including:

- real Word styles and real numbering definitions;
- exact DXA table geometry and deliberate cell padding;
- Google Docs title sanitization and native import rules;
- preset/style audit before final review;
- render every page to PNG, inspect every page, fix, and repeat.

Visual novelty never outranks readability, accessibility, factual correctness,
or the reader's task. If a requested treatment conflicts with those goals,
offer the closest safe expression and explain the constraint briefly.

## Catalog maintenance

Run both checks after any catalog or resolver change:

```bash
python <this-skill-dir>/scripts/resolve_style.py --validate
python <this-skill-dir>/scripts/resolve_style.py --self-test
```

Add a recipe only when it has a clear document job, a complete resolved token
map, a useful distinction from existing recipes, and a plausible render-review
path. Prefer a small set of certified combinations over an unbounded style
cross-product.
