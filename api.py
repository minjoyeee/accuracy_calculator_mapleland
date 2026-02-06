from pydantic import BaseModel, Field, ConfigDict

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from accuracy_cal.data_store import (
    load_monsters,
    load_items,
    load_named_effect_catalog,
)
from accuracy_cal.models import (
    Stats,
    CharacterInput,
    JobGroup,
    EquipmentState,
    BuffState,
    EquipSlot,
    EffectSpec,
)
from accuracy_cal.engine import derive_character_result, check_hit

app = FastAPI(title="Accuracy Calculator API")

# ---- in-memory catalogs (simple cache) ----
MONSTERS = load_monsters()
ITEMS = load_items()
BUFFS = load_named_effect_catalog("buff_skills.json")   # id -> EffectSpec
DOPING = load_named_effect_catalog("doping.json")       # id -> EffectSpec


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/catalog")
def catalog() -> Dict[str, Any]:
    return {
        "monsters": {
            mid: {"name": m.name, "level": m.level, "evasion": m.evasion, "image_url": m.image_url}
            for mid, m in MONSTERS.items()
        },
        "items": {
            iid: {"name": it.name, "slot": it.slot.value, "effect": {"stats": it.effect.stats.__dict__, "acc": it.effect.acc}, "image_url": it.icon_url}
            for iid, it in ITEMS.items()
        },
        "buffs": {
            bid: {"name": spec.name, "acc_group": spec.acc_group, "effect": {"stats": spec.effect.stats.__dict__, "acc": spec.effect.acc}}
            for bid, spec in BUFFS.items()
        },
        "doping": {
            did: {"name": spec.name, "acc_group": spec.acc_group, "effect": {"stats": spec.effect.stats.__dict__, "acc": spec.effect.acc}}
            for did, spec in DOPING.items()
        },
    }


# ---- request/response models ----
class StatsIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    str_: int = Field(4, alias="str")
    dex: int = 4
    int_: int = Field(4, alias="int")
    luk: int = 4



class CalcRequest(BaseModel):
    level: int = Field(..., ge=1, le=300)
    job: str
    base_stats: StatsIn
    mw_on: bool = False
    mw_percent: int = Field(15, ge=0, le=100)  # mw_on=True이면 이 퍼센트를 적용 (현재 기본 15)
    monster_id: str

    equip: List[str] = []   # 예: ["gloves=work_gloves", "weapon=basic_bow", "gloves=custom:acc=7,dex=3"]
    buff: List[str] = []    # 예: ["bless", "custom:acc=10"]
    doping: List[str] = []  # 예: ["acc_pill", "custom:acc=10,dex=3"]


def parse_kv_int_list(spec: str) -> dict[str, int]:
    out: dict[str, int] = {}
    if not spec:
        return out
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        k, v = part.split("=", 1)
        out[k.strip().lower()] = int(v.strip())
    return out

def make_custom_item(slot: EquipSlot, rhs: str):
    # rhs: "custom:acc=7,dex=3"
    kv = parse_kv_int_list(rhs[len("custom:"):])
    acc = kv.pop("acc", 0)
    s = Stats(
        str=kv.pop("str", 0),
        dex=kv.pop("dex", 0),
        int=kv.pop("int", 0),
        luk=kv.pop("luk", 0),
    )
    if kv:
        raise ValueError(f"invalid keys: {list(kv.keys())}")

    from accuracy_cal.models import Effect, Item
    return Item(
        item_id="custom",
        name="(커스텀 장비)",
        slot=slot,
        effect=Effect(stats=s, acc=acc),
        icon_url=None,
    )

def make_custom_effectspec(kind_name: str, rhs: str) -> EffectSpec:
    # rhs: "custom:acc=10,dex=3"
    kv = parse_kv_int_list(rhs[len("custom:"):])
    acc = kv.pop("acc", 0)
    s = Stats(
        str=kv.pop("str", 0),
        dex=kv.pop("dex", 0),
        int=kv.pop("int", 0),
        luk=kv.pop("luk", 0),
    )
    if kv:
        raise ValueError(f"invalid keys: {list(kv.keys())}")
    from accuracy_cal.models import Effect
    return EffectSpec(name=f"(커스텀 {kind_name})", effect=Effect(stats=s, acc=acc), acc_group=None)


@app.post("/calc")
def calc(req: CalcRequest) -> Dict[str, Any]:
    job = JobGroup(req.job)

    mw = (req.mw_percent / 100.0) if req.mw_on else 0.0

    ch = CharacterInput(
        level=req.level,
        job=job,
        base_stats=Stats(str=req.base_stats.str_, dex=req.base_stats.dex, int=req.base_stats.int_, luk=req.base_stats.luk),
        maple_warrior_percent=mw,
    )

    equipment = EquipmentState(use_overall=False)
    buffs = BuffState()

    # equip 적용 (id/custom)
    for spec in req.equip:
        slot_s, rhs = spec.split("=", 1)
        slot = EquipSlot(slot_s)

        if rhs.startswith("custom:"):
            it = make_custom_item(slot, rhs)
        else:
            it = ITEMS[rhs]
            if it.slot != slot:
                raise ValueError("slot mismatch")

        equipment.equipped[slot] = it

    # buff 적용
    for i, bid in enumerate(req.buff):
        if bid.startswith("custom:"):
            buffs.skill_buffs[f"custom_buff_{i}"] = make_custom_effectspec("버프", bid)
        else:
            buffs.skill_buffs[bid] = BUFFS[bid]

    # doping 적용
    for i, did in enumerate(req.doping):
        if did.startswith("custom:"):
            buffs.doping[f"custom_doping_{i}"] = make_custom_effectspec("도핑", did)
        else:
            buffs.doping[did] = DOPING[did]

    result = derive_character_result(ch, equipment, buffs)

    mob = MONSTERS[req.monster_id]
    hit = check_hit(result.acc_total, ch.level, mob)

    return {
        "mw": mw,
        "base_after_mw": result.base_after_mw.__dict__,
        "bonus_stats": result.bonus_stats.__dict__,
        "total_stats": result.total_stats.__dict__,
        "acc_from_stats": result.acc_from_stats,
        "acc_bonus": result.acc_bonus,
        "acc_total": result.acc_total,
        "monster": {"name": mob.name, "level": mob.level, "evasion": mob.evasion},
        "acc_required": hit.acc_required,
        "is_sufficient": hit.is_sufficient,
        "margin": hit.margin,
    }
