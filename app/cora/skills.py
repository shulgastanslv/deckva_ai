"""Skill → carousel structure. Mirrors deckva_web_client prompt-skills."""

from __future__ import annotations

from typing import Any, Literal

SkillId = Literal[
    "launch",
    "howto",
    "offer",
    "tips",
    "story",
    "comparison",
    "checklist",
    "myths",
    "framework",
    "pricing",
    # One editorial skill — cover family randomized on the server
    "aesthetic",
]

# Old separate editorial skills → aesthetic
_SKILL_ALIASES: dict[str, str] = {
    "manifesto": "aesthetic",
    "niches": "aesthetic",
    "lookbook": "aesthetic",
}

# Fixed mid roles/layouts per skill (first = cover/hook, last = cta).
_SKILL_SPECS: dict[str, dict[str, Any]] = {
    "launch": {
        "slidesCount": 6,
        "hasCover": True,
        "midRoles": ["hook", "offer", "howto", "proof"],
        "midLayouts": ["statement", "list", "list", "statement"],
        "preferredContentLayouts": ["statement", "tips", "funnel", "results"],
        "brief": (
            "Product-launch carousel. Structure: hook → offer → who it's for → "
            "proof → details → clear CTA. Keep claims concrete."
        ),
    },
    "howto": {
        "slidesCount": 7,
        "hasCover": True,
        "midRoles": ["howto", "howto", "howto", "howto", "proof"],
        "midLayouts": ["list", "list", "list", "list", "statement"],
        "preferredContentLayouts": ["tips", "statement", "funnel"],
        "brief": (
            "How-to carousel. Each mid slide is one clear step; last mid can be "
            "the result; final slide is CTA."
        ),
    },
    "offer": {
        "slidesCount": 5,
        "hasCover": True,
        "midRoles": ["pain", "offer", "proof"],
        "midLayouts": ["statement", "list", "statement"],
        "preferredContentLayouts": ["statement", "funnel", "results"],
        "brief": (
            "Offer carousel: problem → solution → proof → value → next step CTA."
        ),
    },
    "tips": {
        "slidesCount": 7,
        "hasCover": True,
        "midRoles": ["list", "list", "list", "list", "list"],
        "midLayouts": ["list", "list", "list", "list", "list"],
        "preferredContentLayouts": ["tips", "statement"],
        "brief": (
            "Tips carousel. Slide 1 theme/cover; each following mid slide is one "
            "concrete tip; end with recap CTA."
        ),
    },
    "story": {
        "slidesCount": 6,
        "hasCover": True,
        "midRoles": ["story", "lesson", "howto", "proof"],
        "midLayouts": ["statement", "quote", "list", "statement"],
        "preferredContentLayouts": ["statement", "orange_quote", "results"],
        "brief": (
            "Case-study / story: context → tension → what changed → result → "
            "takeaway → CTA."
        ),
    },
    "comparison": {
        "slidesCount": 5,
        "hasCover": True,
        "midRoles": ["pain", "shift", "offer"],
        "midLayouts": ["list", "list", "statement"],
        "preferredContentLayouts": ["tips", "statement", "results"],
        "brief": (
            "Comparison (before/after or A vs B). Keep claims concrete; end with "
            "a recommendation CTA."
        ),
    },
    "checklist": {
        "slidesCount": 6,
        "hasCover": True,
        "midRoles": ["list", "list", "list", "list"],
        "midLayouts": ["list", "list", "list", "list"],
        "preferredContentLayouts": ["tips", "list", "statement"],
        "brief": (
            "Checklist carousel. Cover states the goal; each mid slide is one "
            "checklist item (or a small group) to complete; end with a ready CTA."
        ),
    },
    "myths": {
        "slidesCount": 6,
        "hasCover": True,
        "midRoles": ["pain", "shift", "pain", "shift"],
        "midLayouts": ["statement", "quote", "statement", "quote"],
        "preferredContentLayouts": ["statement", "orange_quote", "results"],
        "brief": (
            "Myth-busting carousel. Each mid pair: state a common myth, then the "
            "truth with a short proof; close with a clear takeaway CTA."
        ),
    },
    "framework": {
        "slidesCount": 7,
        "hasCover": True,
        "midRoles": ["howto", "howto", "howto", "howto", "proof"],
        "midLayouts": ["list", "list", "list", "list", "statement"],
        "preferredContentLayouts": ["funnel", "tips", "statement"],
        "brief": (
            "Framework carousel: name the model on the cover, walk through 3–4 "
            "stages one per slide, then show how to apply it; end with CTA."
        ),
    },
    "pricing": {
        "slidesCount": 5,
        "hasCover": True,
        "midRoles": ["offer", "offer", "proof"],
        "midLayouts": ["list", "list", "statement"],
        "preferredContentLayouts": ["funnel", "results", "statement"],
        "brief": (
            "Pricing carousel: introduce tiers, who each is for, what’s included, "
            "and how to choose; end with a purchase / book CTA."
        ),
    },
    "aesthetic": {
        "slidesCount": 6,
        "hasCover": True,
        "midRoles": ["offer", "howto", "proof", "lesson"],
        "midLayouts": ["statement", "tips", "quote", "statement"],
        "preferredContentLayouts": ["statement", "tips", "orange_quote"],
        "brief": (
            "Aesthetic / editorial lifestyle carousel (quiet-luxury, lookbook, manifesto mood). "
            "Cover layout is CHOSEN ON THE SERVER — write copy that works for any of: "
            "centered poetic title, left cream hook with a [bracketed] word, vertical diptych "
            "title, 2×2 collage bar, stacked manifesto slogan, or niche tags. "
            "Cover heading: short poetic line (3–8 words); callout = soft /сохраняй/-style cue; "
            "tag = blog footer or bio line; badges = optional 1–2 short meta labels; "
            "items = optional 4–8 short niche/tag words (косметолог, фотограф…) when it fits. "
            "Mid: one calm tip, frame idea, or stance line per slide. "
            "image_prompt every photo slide (english Unsplash 4–8 words, lifestyle / flat-lay / "
            "fashion / coffee / autumn). CTA: soft invitation, not salesy."
        ),
    },
}


def normalize_skill_id(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower()
    key = _SKILL_ALIASES.get(key, key)
    return key if key in _SKILL_SPECS else None


def skill_spec(skill_id: str | None) -> dict[str, Any] | None:
    key = normalize_skill_id(skill_id)
    if not key:
        return None
    return dict(_SKILL_SPECS[key])


def apply_skill_to_design(
    design: dict[str, Any],
    *,
    skill_id: str | None,
    slides_count: int,
    force_cover: bool = False,
) -> dict[str, Any]:
    """Override random mid roles/layouts when a skill is selected."""
    spec = skill_spec(skill_id)
    out = dict(design)
    if not spec:
        if force_cover:
            out["hasCover"] = True
            if not out.get("photoRatio"):
                out["photoRatio"] = 0.48
        return out

    out["hasCover"] = True if force_cover else bool(spec.get("hasCover", True))
    if out["hasCover"] and not out.get("photoRatio"):
        out["photoRatio"] = 0.48

    mid_n = max(0, slides_count - 2)
    roles = list(spec.get("midRoles") or [])
    layouts = list(spec.get("midLayouts") or [])
    out["midRoles"] = [roles[i % len(roles)] for i in range(mid_n)] if roles else out.get("midRoles", [])
    out["midLayouts"] = (
        [layouts[i % len(layouts)] for i in range(mid_n)] if layouts else out.get("midLayouts", [])
    )
    preferred = spec.get("preferredContentLayouts")
    if preferred:
        out["preferredContentLayouts"] = list(preferred)
    out["skillId"] = normalize_skill_id(skill_id)
    out["skillBrief"] = spec.get("brief") or ""
    if out.get("skillId") == "aesthetic":
        out["mood"] = "pinterest_editorial"
        out["gridMode"] = "none"
        out["photoRatio"] = 1.0
        out["accentBias"] = 0.2
        out.pop("engine", None)
    return out


def skill_prompt_brief(skill_id: str | None) -> str:
    spec = skill_spec(skill_id)
    if not spec:
        return ""
    return str(spec.get("brief") or "")
