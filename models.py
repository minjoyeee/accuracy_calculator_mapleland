from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class JobGroup(str, Enum):
    WARRIOR = "warrior"
    ARCHER = "archer"
    THIEF = "thief"
    MAGE = "mage"


class EquipSlot(str, Enum):
    HELMET = "helmet"
    TOP = "top"
    BOTTOM = "bottom"
    OVERALL = "overall"
    SHOES = "shoes"
    GLOVES = "gloves"
    CAPE = "cape"
    WEAPON = "weapon"

    PENDANT = "pendant"       # 1개
    EARRING = "earring"
    RING = "ring"             # 1개

    EYE_EVENT = "eye_event"   # 기본 빈값
    FACE_EVENT = "face_event" # 기본 빈값
    BELT_EVENT = "belt_event" # 기본 빈값
    TITLE = "title"           # 기본 빈값
    PET_EQUIP = "pet_equip"   # 기본 빈값


@dataclass(frozen=True)
class Stats:
    str: int = 0
    dex: int = 0
    int: int = 0
    luk: int = 0

    def __add__(self, other: "Stats") -> "Stats":
        return Stats(
            str=self.str + other.str,
            dex=self.dex + other.dex,
            int=self.int + other.int,
            luk=self.luk + other.luk,
        )


@dataclass(frozen=True)
class Effect:
    stats: Stats = Stats()
    acc: int = 0

    def __add__(self, other: "Effect") -> "Effect":
        return Effect(stats=self.stats + other.stats, acc=self.acc + other.acc)


@dataclass(frozen=True)
class Item:
    item_id: str
    name: str
    slot: EquipSlot
    effect: Effect
    icon_url: Optional[str] = None


@dataclass
class EquipmentState:
    use_overall: bool = False
    equipped: Dict[EquipSlot, Optional[Item]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for slot in EquipSlot:
            self.equipped.setdefault(slot, None)

    def iter_effects(self) -> Effect:
        total = Effect()
        for slot, item in self.equipped.items():
            if item is None:
                continue

            if self.use_overall:
                if slot in (EquipSlot.TOP, EquipSlot.BOTTOM):
                    continue
            else:
                if slot == EquipSlot.OVERALL:
                    continue

            total = total + item.effect
        return total


@dataclass
class BuffState:
    # UI에서는 분리(버프스킬/도핑)지만, 효과 합산은 동일하게 처리
    skill_buffs: Dict[str, Effect] = field(default_factory=dict)
    doping: Dict[str, Effect] = field(default_factory=dict)

    def total_effect(self) -> Effect:
        total = Effect()
        for e in self.skill_buffs.values():
            total = total + e
        for e in self.doping.values():
            total = total + e
        return total


@dataclass(frozen=True)
class CharacterInput:
    level: int
    job: JobGroup
    base_stats: Stats
    maple_warrior_percent: float  # 0.0, 0.1, 0.15 ...


@dataclass(frozen=True)
class DerivedResult:
    base_after_mw: Stats
    bonus_stats: Stats
    total_stats: Stats
    acc_from_stats: int
    acc_bonus: int
    acc_total: int
