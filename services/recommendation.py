"""
Parts/consumables recommendation. Ships with sensible generic defaults and
is easy to extend per-vehicle (e.g. by parsing the "Specifications" section
of an ingested manual for exact oil viscosity/tire sizes).
"""
from __future__ import annotations
from typing import Dict

GENERIC_RECOMMENDATIONS = {
    "engine_oil": {
        "item": "Yamalube / 10W-40 semi-synthetic, API SG+ (JASO MA/MA2)",
        "note": "Confirm exact spec against your manual's Specifications section.",
    },
    "tires": {
        "item": "IRC Road Winner (or equivalent OE-spec radial/tube tire)",
        "note": "Match front/rear sizes exactly — never mix tire brands front/rear.",
    },
    "battery": {
        "item": "YTZ4V or equivalent 12V VRLA (sealed) battery",
        "note": "Check the exact model code on your battery compartment label.",
    },
    "chain_lube": {
        "item": "O-ring safe chain lubricant",
        "note": "Non O-ring-safe lubricants can degrade the chain's O-rings over time.",
    },
    "brake_fluid": {
        "item": "DOT 3 or DOT 4 brake fluid",
        "note": "Never mix DOT 3/4 with DOT 5 (silicone) fluid.",
    },
}


def get_recommendations(vehicle_key: str = None) -> Dict:
    # Placeholder for per-vehicle overrides; falls back to generic defaults.
    return GENERIC_RECOMMENDATIONS
