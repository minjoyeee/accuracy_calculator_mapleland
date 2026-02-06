import json
from pathlib import Path
from typing import Dict

from .models import Effect, Item, Monster, Stats, EquipSlot, EffectSpec

DATA_DIR = Path(__file__).resolve().parent / "data"

def _effect_from_dict(d: dict) -> Effect:
    s = d.get("stats", {})
    return Effect(
        stats=Stats(
            str=int(s.get("str", 0)),
            dex=int(s.get("dex", 0)),
            int=int(s.get("int", 0)),
            luk=int(s.get("luk", 0)),
        ),
        acc=int(d.get("acc", 0)),
    )

def load_monsters() -> Dict[str, Monster]:
    path = DATA_DIR / "monsters.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, Monster] = {}
    for r in rows:
        out[r["id"]] = Monster(
            name=r["name"],
            level=int(r["level"]),
            evasion=int(r["evasion"]),
            image_url=r.get("image_url"),
        )
    return out

def load_effect_catalog(filename: str) -> Dict[str, Effect]:
    path = DATA_DIR / filename
    rows = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, Effect] = {}
    for r in rows:
        out[r["id"]] = _effect_from_dict(r["effect"])
    return out

def load_named_effect_catalog(filename: str) -> dict[str, EffectSpec]:
    path = DATA_DIR / filename
    rows = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, EffectSpec] = {}
    for r in rows:
        out[r["id"]] = EffectSpec(
            name=r["name"],
            acc_group=r.get("acc_group"),
            effect=_effect_from_dict(r["effect"]),
        )
    return out

def load_items() -> dict[str, Item]:
    path = DATA_DIR / "items.json"
    rows = json.loads(path.read_text(encoding="utf-8"))

    out: dict[str, Item] = {}
    for r in rows:
        slot = EquipSlot(r["slot"])  # "gloves" -> EquipSlot.GLOVES
        out[r["id"]] = Item(
            item_id=r["id"],
            name=r["name"],
            slot=slot,
            effect=_effect_from_dict(r["effect"]),
            icon_url=r.get("image_url"),
        )
    return out
