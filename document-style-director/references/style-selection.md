# Context-led interactive style selection

Use this reference only for new documents, major repackages, or explicit
redesigns that do not already have a controlling template or exact visual
direction.

## 1. Build the context envelope

Read enough of the actual content to classify the reading task. A subject such
as "AI strategy" is not sufficient by itself: an executive decision memo, a
training handbook, and a customer proposal about that subject need different
designs.

Capture these fields mentally or in task-local notes:

| Field | Decision it should change |
|---|---|
| Archetype | hierarchy, opening, navigation, dominant form factors |
| Audience | assumed knowledge, formality, scan depth, annotation needs |
| Reader action | lead callout, evidence order, steps, comparison, or form space |
| Content geometry | prose rhythm, table intensity, visual anchors, appendix use |
| Stakes | restraint, traceability, branding tolerance, accessibility |
| Length | cover budget, running furniture, TOC/navigation, density |
| Surface | Word polish versus Google Docs-native restraint |
| Constraints | brand colors/fonts, print, localization, accessibility |

When several audiences exist, design for the primary decision-maker and make
secondary readers easy to serve through summaries, appendices, or navigation.

## 2. Generate three genuinely different candidates

Use the resolver's ranking, then assign the candidates these roles:

- **Recommended fit:** the strongest balance of purpose, audience, content
  geometry, and surface.
- **Reserved alternative:** a quieter or more conventional direction.
- **Expressive alternative:** a more distinctive direction that remains
  credible for the context.

The three must differ in visual system or opening treatment, not merely accent
color. Exclude a candidate when its main strength is irrelevant to the content;
for example, do not recommend `data_forward` for a prose-only reflective essay.

Each card should fit in four short lines:

```text
1. Boardroom Navy — recommended
   Best for a time-constrained executive decision and mixed evidence.
   Arial, navy/slate, balanced density, memo masthead.
   Tradeoff: intentionally conservative rather than expressive.
```

Localize display names and descriptions to the user's language. Keep stable
recipe IDs internal unless they aid reproducibility.

## 3. Ask once, then converge

When `request_user_input` is available, use it once with no more than three
questions. The direction question carries the actual contextual recommendation;
density and opening are optional refinement axes. The first option of every
question is `Use your judgment (Recommended)`.

When the picker is unavailable, present the three cards in chat and ask for one
number. A short modifier may accompany the number, such as "2, 조금 더 여유롭게"
or "1, 회사 색상은 초록". Treat that as a named override and continue.

Do not ask abstract questions such as "professional or modern?" without showing
what the answer changes. Do not present more than three directions unless the
user explicitly asks to browse the catalog.

## 4. Resolve overrides safely

User instructions win, subject to legibility and format constraints. Common
safe overrides include:

- a supplied brand accent color with checked contrast;
- airy or compact density;
- a minimal or feature-led opening;
- a compatible font from the approved fallback chain;
- reduced decorative furniture for printing or Google Docs.

Do not silently combine heading styles, table fills, paragraph rhythms, or page
furniture from multiple visual systems. Record every cross-system exception as
a named override in the locked style brief.

## 5. Auto and Exact modes

In Auto mode, select the resolver's top candidate and state the choice in one
sentence before authoring. In Exact mode, honor the chosen recipe or explicit
tokens. Ask only when the requested combination would create a meaningful
quality, accessibility, rendering, or surface problem.

## 6. Templates and references

A user-supplied template or retained reference is the design authority. Do not
run this selection flow unless the user asks to depart from it. If the user asks
to browse templates, route to the `documents` artifact-template picker; do not
replace that picker with this catalog.

A locked style brief from this flow is visual direction. Once locked, continue
to authoring without opening the template picker.
