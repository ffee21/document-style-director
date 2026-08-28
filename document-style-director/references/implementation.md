# Applying a resolved style contract

Read this reference after a recipe is selected and before DOCX authoring. The
`documents` skill remains authoritative for artifact operations, rendering,
Google Docs import, and delivery.

## Token resolution

Use `<this-skill-dir>/scripts/resolve_style.py --choose ... --output
style-spec.json`, resolving `<this-skill-dir>` to the folder containing the
skill's `SKILL.md`. The result deep-merges the shared base, selected visual
system, density, and opening tokens. Treat the resulting values as exact. Do not
rely on Word, theme, list, or table defaults for any field represented in the
contract.

Store user changes under `named_overrides`; do not mutate the catalog for a
one-off request. Apply the same override everywhere that semantic role appears.

## Typography and fonts

Apply the resolved font to both the normal run properties and the OOXML
`w:rFonts` ASCII/HAnsi/eastAsia fields. Check that the primary fonts are
available in the authoring/rendering environment. If not, use the first
available fallback and record `font_fallback` as a named override.

Never reduce body text below 9.5 pt or table text below 8.5 pt to force content
onto a page. Prefer wrapping, column adjustment, a cleaner page break, or a
slightly denser certified profile.

## Page, paragraph, and heading geometry

Encode page size, margins, header/footer distance, paragraph before/after, and
line spacing explicitly. Keep heading hierarchy semantic through real Word
Heading 1/2/3 styles. Avoid a heading at the bottom of a page without enough
following content to establish the section.

## Lists and tables

Use real numbering definitions. Apply the resolved marker alignment, text
indent, hanging indent, paragraph spacing, and line spacing.

For every table, keep `tblW`, `tblGrid`, and each `tcW` consistent with the
resolved 9360 DXA content width unless a named compact-table override is used.
Set `tblInd` to the resolved start margin. Never use fixed row heights. Apply
resolved cell margins and align each column by data type.

## Openings and page furniture

Apply exactly one opening pattern. `opening` tokens control title alignment,
top space, metadata arrangement, rule behavior, and optional feature element.
Do not mix a centered cover, memo metadata stack, metric banner, and pull quote
on the same first page.

Keep running headers and footers quiet. For short one-page documents, omit them
unless they carry essential status or confidentiality information.

## Google Docs

For native Google Docs, prefer recipes whose visual system supports
`google-docs`. Reduce ornamental furniture that does not import reliably. The
`documents` skill's plain-title implementation and deterministic title
sanitizer remain mandatory.

## Audit and render loop

Before rendering, compare the DOCX against `style-spec.json`:

- fonts, sizes, colors, spacing, and line spacing;
- list definitions and indents;
- table width, indent, grid, cell widths, margins, fills, and borders;
- callout and opening tokens;
- running header/footer behavior;
- named overrides and unexplained direct formatting.

Then render every page, inspect every PNG at 100%, and iterate. A successful
catalog validation does not replace visual inspection of the actual document.
