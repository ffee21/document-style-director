#!/usr/bin/env python3
"""Rank certified document styles and resolve one into an exact token contract."""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = SKILL_DIR / "references" / "style_catalog.json"
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


class CatalogError(ValueError):
    """Raised when a style catalog or requested resolution is invalid."""


def load_catalog(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError as exc:
        raise CatalogError(f"Catalog not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CatalogError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CatalogError("Catalog root must be an object")
    return value


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def index_by_id(items: Iterable[dict[str, Any]], kind: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise CatalogError(f"Every {kind} needs a non-empty string id")
        if item_id in result:
            raise CatalogError(f"Duplicate {kind} id: {item_id}")
        result[item_id] = item
    return result


def get_path(value: dict[str, Any], dotted: str) -> Any:
    cursor: Any = value
    for part in dotted.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            raise CatalogError(f"Missing resolved token: {dotted}")
        cursor = cursor[part]
    return cursor


def set_path(value: dict[str, Any], dotted: str, replacement: Any) -> None:
    parts = dotted.split(".")
    cursor = value
    for part in parts[:-1]:
        child = cursor.get(part)
        if child is None:
            child = {}
            cursor[part] = child
        if not isinstance(child, dict):
            raise CatalogError(f"Cannot set {dotted}: {part} is not an object")
        cursor = child
    cursor[parts[-1]] = replacement


def parse_scalar(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def split_values(values: list[str] | None) -> list[str]:
    if not values:
        return []
    result: list[str] = []
    for value in values:
        result.extend(part.strip().lower() for part in value.split(",") if part.strip())
    return sorted(set(result))


def luminance(hex_color: str) -> float:
    rgb = [int(hex_color[index : index + 2], 16) / 255.0 for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    light = max(luminance(foreground), luminance(background))
    dark = min(luminance(foreground), luminance(background))
    return (light + 0.05) / (dark + 0.05)


def contract_quality_errors(tokens: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        page_width = int(get_path(tokens, "page.content_width_dxa"))
        table_width = int(get_path(tokens, "tables.width_dxa"))
        if page_width != 9360 or table_width != page_width:
            errors.append("page and table width must remain 9360 DXA")

        body_size = float(get_path(tokens, "typography.body.size_pt"))
        table_size = float(get_path(tokens, "typography.table_text.size_pt"))
        if body_size < float(get_path(tokens, "accessibility.minimum_body_size_pt")):
            errors.append("body size is below the accessibility minimum")
        if table_size < float(get_path(tokens, "accessibility.minimum_table_size_pt")):
            errors.append("table text size is below the accessibility minimum")

        background = get_path(tokens, "colors.page_background")
        minimum_text = float(get_path(tokens, "accessibility.minimum_text_contrast_ratio"))
        if not isinstance(background, str) or not HEX_COLOR.match(background):
            errors.append("page background is not a six-digit hex color")
        else:
            for role in ("body", "h1", "h2", "h3"):
                color = get_path(tokens, f"typography.{role}.color")
                if not isinstance(color, str) or not HEX_COLOR.match(color):
                    errors.append(f"{role} color is not a six-digit hex color")
                elif contrast_ratio(color, background) + 1e-9 < minimum_text:
                    errors.append(f"{role} contrast is below {minimum_text}:1")

        for role in ("body", "heading", "mono", "east_asia_sans", "east_asia_serif"):
            primary = get_path(tokens, f"fonts.{role}.primary")
            fallbacks = get_path(tokens, f"fonts.{role}.fallbacks")
            if not isinstance(primary, str) or not primary.strip():
                errors.append(f"font role {role} has no primary font")
            if not isinstance(fallbacks, list) or not fallbacks:
                errors.append(f"font role {role} has no fallback chain")

        margins = get_path(tokens, "tables.cell_margins_dxa")
        if any(int(margins[side]) <= 0 for side in ("top", "bottom", "start", "end")):
            errors.append("table cell margins must be positive")
        if float(get_path(tokens, "opening.title_size_pt")) < 20:
            errors.append("opening title size is below 20 pt")
    except (CatalogError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def resolve_recipe(
    catalog: dict[str, Any],
    recipe_id: str,
    *,
    surface: str | None = None,
    density_id: str | None = None,
    opening_id: str | None = None,
    named_overrides: list[str] | None = None,
) -> dict[str, Any]:
    recipes = index_by_id(catalog.get("recipes", []), "recipe")
    visuals = index_by_id(catalog.get("visual_systems", []), "visual system")
    densities = index_by_id(catalog.get("densities", []), "density")
    openings = index_by_id(catalog.get("openings", []), "opening")

    if recipe_id not in recipes:
        raise CatalogError(f"Unknown recipe: {recipe_id}")
    recipe = recipes[recipe_id]
    visual = visuals[recipe["visual_system"]]
    density = densities[density_id or recipe["density"]]
    opening = openings[opening_id or recipe["opening"]]
    selected_surface = surface or recipe["surfaces"][0]

    if selected_surface not in recipe["surfaces"]:
        raise CatalogError(f"Recipe {recipe_id} does not support surface {selected_surface}")
    if selected_surface not in visual["surfaces"]:
        raise CatalogError(f"Visual system {visual['id']} does not support surface {selected_surface}")
    if selected_surface not in opening["surfaces"]:
        raise CatalogError(f"Opening {opening['id']} does not support surface {selected_surface}")

    tokens = deep_merge(catalog["base"], visual.get("overrides", {}))
    tokens = deep_merge(tokens, density.get("overrides", {}))
    tokens["opening"] = copy.deepcopy(opening["tokens"])

    overrides: dict[str, Any] = {}
    for assignment in named_overrides or []:
        if "=" not in assignment:
            raise CatalogError(f"Named override must use path=value: {assignment}")
        path, raw = assignment.split("=", 1)
        path = path.strip()
        if not path:
            raise CatalogError("Named override path cannot be empty")
        parsed = parse_scalar(raw.strip())
        set_path(tokens, path, parsed)
        overrides[path] = parsed

    quality_errors = contract_quality_errors(tokens)
    if quality_errors:
        raise CatalogError("Resolved contract failed quality checks: " + "; ".join(quality_errors))

    return {
        "style_contract_version": "1.0.0",
        "catalog_version": catalog["catalog_version"],
        "recipe_id": recipe["id"],
        "display_name": recipe["label"],
        "archetype": recipe["archetype"],
        "visual_system": {"id": visual["id"], "label": visual["label"], "voice": visual["voice"]},
        "density": {"id": density["id"], "label": density["label"]},
        "opening": {"id": opening["id"], "label": opening["label"]},
        "surface": selected_surface,
        "tradeoff": recipe["tradeoff"],
        "named_overrides": overrides,
        "tokens": tokens,
    }


def validate_catalog(catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_top = ["catalog_version", "base", "visual_systems", "densities", "openings", "recipes"]
    for key in required_top:
        if key not in catalog:
            errors.append(f"Missing top-level key: {key}")
    if errors:
        return errors

    try:
        visuals = index_by_id(catalog["visual_systems"], "visual system")
        densities = index_by_id(catalog["densities"], "density")
        openings = index_by_id(catalog["openings"], "opening")
        recipes = index_by_id(catalog["recipes"], "recipe")
    except CatalogError as exc:
        return [str(exc)]

    minimum = catalog.get("minimum_certified_recipes", 1)
    if len(recipes) < minimum:
        errors.append(f"Expected at least {minimum} certified recipes, found {len(recipes)}")

    for recipe in recipes.values():
        recipe_id = recipe["id"]
        for field in ("label", "archetype", "visual_system", "density", "opening", "surfaces", "audiences", "purposes", "shapes", "tones", "tradeoff"):
            if field not in recipe or recipe[field] in (None, "", []):
                errors.append(f"Recipe {recipe_id} missing {field}")
        if recipe.get("visual_system") not in visuals:
            errors.append(f"Recipe {recipe_id} references unknown visual system {recipe.get('visual_system')}")
            continue
        if recipe.get("density") not in densities:
            errors.append(f"Recipe {recipe_id} references unknown density {recipe.get('density')}")
            continue
        if recipe.get("opening") not in openings:
            errors.append(f"Recipe {recipe_id} references unknown opening {recipe.get('opening')}")
            continue
        for surface in recipe.get("surfaces", []):
            if surface not in visuals[recipe["visual_system"]].get("surfaces", []):
                errors.append(f"Recipe {recipe_id}: {surface} unsupported by visual system")
            if surface not in openings[recipe["opening"]].get("surfaces", []):
                errors.append(f"Recipe {recipe_id}: {surface} unsupported by opening")

        try:
            contract = resolve_recipe(catalog, recipe_id)
            tokens = contract["tokens"]
            required_tokens = [
                "page.content_width_dxa",
                "fonts.body.primary",
                "fonts.heading.primary",
                "fonts.east_asia_sans.primary",
                "typography.body.size_pt",
                "typography.body.color",
                "typography.body.after_pt",
                "typography.body.line_spacing",
                "typography.title.size_pt",
                "typography.h1.size_pt",
                "typography.h2.size_pt",
                "typography.h3.size_pt",
                "lists.bullet_level_0.text_indent_at_dxa",
                "lists.decimal_level_0.text_indent_at_dxa",
                "tables.width_dxa",
                "tables.indent_dxa",
                "tables.cell_margins_dxa.start",
                "opening.title_size_pt",
                "accessibility.minimum_body_size_pt",
            ]
            for dotted in required_tokens:
                get_path(tokens, dotted)

            if get_path(tokens, "page.content_width_dxa") != 9360:
                errors.append(f"Recipe {recipe_id}: page content width must be 9360 DXA")
            if get_path(tokens, "tables.width_dxa") != 9360:
                errors.append(f"Recipe {recipe_id}: table width must be 9360 DXA")
            body_size = float(get_path(tokens, "typography.body.size_pt"))
            minimum_body = float(get_path(tokens, "accessibility.minimum_body_size_pt"))
            if body_size < minimum_body:
                errors.append(f"Recipe {recipe_id}: body size {body_size} is below {minimum_body}")
            table_size = float(get_path(tokens, "typography.table_text.size_pt"))
            minimum_table = float(get_path(tokens, "accessibility.minimum_table_size_pt"))
            if table_size < minimum_table:
                errors.append(f"Recipe {recipe_id}: table size {table_size} is below {minimum_table}")

            background = get_path(tokens, "colors.page_background")
            minimum_text = float(get_path(tokens, "accessibility.minimum_text_contrast_ratio"))
            for role in ("body", "h1", "h2", "h3"):
                color = get_path(tokens, f"typography.{role}.color")
                if not HEX_COLOR.match(color) or not HEX_COLOR.match(background):
                    errors.append(f"Recipe {recipe_id}: invalid color for {role}")
                elif contrast_ratio(color, background) + 1e-9 < minimum_text:
                    ratio = contrast_ratio(color, background)
                    errors.append(f"Recipe {recipe_id}: {role} contrast {ratio:.2f} is below {minimum_text}")
        except CatalogError as exc:
            errors.append(f"Recipe {recipe_id}: {exc}")

    return errors


def infer_archetype(context: str, hints: dict[str, list[str]]) -> str | None:
    lowered = context.lower()
    scored: list[tuple[int, str]] = []
    for archetype, phrases in hints.items():
        score = sum(len(phrase) for phrase in phrases if phrase.lower() in lowered)
        if score:
            scored.append((score, archetype))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][1]


def score_recipe(recipe: dict[str, Any], query: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    matches: list[str] = []
    archetype = query.get("archetype")
    if archetype and recipe["archetype"] == archetype:
        score += 14
        matches.append(f"archetype {archetype}")
    elif recipe["archetype"] == "general_report":
        score += 1

    weights = (("audiences", "audience", 3.0), ("purposes", "purpose", 4.0), ("shapes", "shape", 2.5), ("tones", "tone", 2.0))
    for recipe_field, query_field, weight in weights:
        overlap = sorted(set(recipe[recipe_field]) & set(query.get(query_field, [])))
        if overlap:
            score += weight * len(overlap)
            matches.append(f"{query_field} {', '.join(overlap)}")

    if query["surface"] in recipe["surfaces"]:
        score += 2
        matches.append(f"surface {query['surface']}")
    return score, matches


def rank_candidates(catalog: dict[str, Any], query: dict[str, Any], count: int) -> list[dict[str, Any]]:
    visuals = index_by_id(catalog["visual_systems"], "visual system")
    openings = index_by_id(catalog["openings"], "opening")
    ranked: list[dict[str, Any]] = []
    for recipe in catalog["recipes"]:
        if query["surface"] not in recipe["surfaces"]:
            continue
        score, matches = score_recipe(recipe, query)
        ranked.append(
            {
                "recipe": recipe,
                "score": score,
                "matches": matches,
                "visual": visuals[recipe["visual_system"]],
                "opening": openings[recipe["opening"]],
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["recipe"]["id"]))
    if not ranked:
        raise CatalogError(f"No certified recipes support surface {query['surface']}")

    selected: list[dict[str, Any]] = []
    used_visuals: set[str] = set()
    used_openings: set[str] = set()
    for item in ranked:
        visual_id = item["recipe"]["visual_system"]
        opening_id = item["recipe"]["opening"]
        if selected and visual_id in used_visuals:
            continue
        if (
            len(selected) >= 2
            and opening_id in used_openings
            and item["recipe"]["archetype"] != query.get("archetype")
        ):
            continue
        selected.append(item)
        used_visuals.add(visual_id)
        used_openings.add(opening_id)
        if len(selected) == count:
            break
    if len(selected) < count:
        selected_ids = {item["recipe"]["id"] for item in selected}
        for item in ranked:
            if item["recipe"]["id"] in selected_ids:
                continue
            selected.append(item)
            if len(selected) == count:
                break

    candidates: list[dict[str, Any]] = []
    for position, item in enumerate(selected, start=1):
        recipe = item["recipe"]
        reason = "; ".join(item["matches"][:5]) or "general certified fit"
        candidates.append(
            {
                "rank": position,
                "recipe_id": recipe["id"],
                "display_name": recipe["label"],
                "score": round(item["score"], 2),
                "fit_reason": reason,
                "visual_system": {"id": item["visual"]["id"], "label": item["visual"]["label"], "voice": item["visual"]["voice"]},
                "density": recipe["density"],
                "opening": {"id": item["opening"]["id"], "label": item["opening"]["label"]},
                "tradeoff": recipe["tradeoff"],
            }
        )
    return candidates


def print_candidates(candidates: list[dict[str, Any]], query: dict[str, Any]) -> None:
    print(f"Context: archetype={query.get('archetype') or 'unspecified'}, surface={query['surface']}")
    for candidate in candidates:
        recommended = " [recommended]" if candidate["rank"] == 1 else ""
        print(f"{candidate['rank']}. {candidate['display_name']}{recommended}")
        print(f"   Fit: {candidate['fit_reason']}")
        print(f"   System: {candidate['visual_system']['label']}; density={candidate['density']}; opening={candidate['opening']['label']}")
        print(f"   Tradeoff: {candidate['tradeoff']}")


def run_self_test(catalog: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    scenarios = [
        ({"archetype": "decision_memo", "audience": ["executive"], "purpose": ["decide"], "shape": ["mixed"], "tone": ["formal"], "surface": "word"}, "decision_memo"),
        ({"archetype": "research_report", "audience": ["academic"], "purpose": ["inform"], "shape": ["prose"], "tone": ["scholarly"], "surface": "word"}, "research_report"),
        ({"archetype": "technical_spec", "audience": ["technical"], "purpose": ["document"], "shape": ["tables"], "tone": ["technical"], "surface": "word"}, "technical_spec"),
        ({"archetype": "sop", "audience": ["operator"], "purpose": ["operate"], "shape": ["steps"], "tone": ["accessible"], "surface": "google-docs"}, "sop"),
    ]
    for query, expected in scenarios:
        candidates = rank_candidates(catalog, query, 3)
        if candidates[0]["recipe_id"] not in {recipe["id"] for recipe in catalog["recipes"] if recipe["archetype"] == expected}:
            failures.append(f"Scenario {expected}: unexpected top candidate {candidates[0]['recipe_id']}")
        if len({candidate["visual_system"]["id"] for candidate in candidates}) < min(3, len(candidates)):
            failures.append(f"Scenario {expected}: candidates are not visually diverse")
        if any(query["surface"] not in index_by_id(catalog["recipes"], "recipe")[candidate["recipe_id"]]["surfaces"] for candidate in candidates):
            failures.append(f"Scenario {expected}: returned unsupported surface")

    inferred = infer_archetype("이 연구 보고서는 정책 효과를 분석한다", catalog.get("keyword_hints", {}))
    if inferred != "research_report":
        failures.append(f"Korean context inference expected research_report, got {inferred}")

    contract = resolve_recipe(
        catalog,
        "executive-decision-navy",
        surface="word",
        named_overrides=["colors.accent=\"#006B5E\""],
    )
    if get_path(contract, "tokens.colors.accent") != "#006B5E":
        failures.append("Named override did not reach resolved tokens")
    if get_path(contract, "tokens.tables.width_dxa") != 9360:
        failures.append("Resolved contract lost table geometry")
    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--context", default="", help="Free-text context used for lightweight archetype inference")
    parser.add_argument("--archetype")
    parser.add_argument("--audience", action="append")
    parser.add_argument("--purpose", action="append")
    parser.add_argument("--shape", action="append")
    parser.add_argument("--tone", action="append")
    parser.add_argument("--surface", choices=("word", "google-docs"), default="word")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--choose", help="Resolve this exact certified recipe")
    parser.add_argument("--density", help="Override the recipe density")
    parser.add_argument("--opening", help="Override the recipe opening")
    parser.add_argument("--set", dest="named_overrides", action="append", help="Named token override as dotted.path=JSON_VALUE")
    parser.add_argument("--output", type=Path, help="Write the resolved contract or candidates as JSON")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--list", action="store_true", help="List all certified recipes")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        catalog = load_catalog(args.catalog)
        validation_errors = validate_catalog(catalog)
        if args.validate or args.self_test:
            if validation_errors:
                for error in validation_errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"Catalog valid: {len(catalog['visual_systems'])} visual systems, {len(catalog['densities'])} densities, {len(catalog['openings'])} openings, {len(catalog['recipes'])} certified recipes.")
            if args.self_test:
                failures = run_self_test(catalog)
                if failures:
                    for failure in failures:
                        print(f"FAIL: {failure}", file=sys.stderr)
                    return 1
                print("Self-test passed: ranking, diversity, Korean inference, surfaces, overrides, and geometry.")
            return 0

        if validation_errors:
            raise CatalogError("Catalog validation failed; run --validate for details")

        if args.list:
            for recipe in catalog["recipes"]:
                print(f"{recipe['id']}\t{recipe['label']}\t{recipe['archetype']}\t{recipe['visual_system']}\t{recipe['density']}\t{recipe['opening']}")
            return 0

        if args.choose:
            result: Any = resolve_recipe(
                catalog,
                args.choose,
                surface=args.surface,
                density_id=args.density,
                opening_id=args.opening,
                named_overrides=args.named_overrides,
            )
        else:
            archetype = args.archetype or infer_archetype(args.context, catalog.get("keyword_hints", {}))
            query = {
                "archetype": archetype,
                "audience": split_values(args.audience),
                "purpose": split_values(args.purpose),
                "shape": split_values(args.shape),
                "tone": split_values(args.tone),
                "surface": args.surface,
            }
            result = {"context": query, "candidates": rank_candidates(catalog, query, max(1, args.count))}

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(args.output)
        elif args.format == "json" or args.choose:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_candidates(result["candidates"], result["context"])
        return 0
    except (CatalogError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
