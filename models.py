from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import floor
from typing import Dict, Optional


# -------------------------
# 1) 기본 모델
# -------------------------

class JobGroup(str, Enum):
    WARRIOR = "warrior"
    ARCHER = "archer"
    THIEF = "thief"
    MAGE = "mage"


class EquipSlot(str, Enum):
    HELMET = "helmet"            # 투구
    TOP = "top"                  # 상의
    BOTTOM = "bottom"            # 하의
    OVERALL = "overall"          # 한벌옷
    SHOES = "shoes"              # 신발
    GLOVES = "gloves"            # 장갑
    CAPE = "cape"                # 망토
    WEAPON = "weapon"            # 무기

    PENDANT = "pendant"          # 펜던트(1)
    EARRING = "earring"          # 귀고리
    RING = "ring"                # 반지(1)

    EYE_EVENT = "eye_event"      # 눈장식(이벤트/기간제) - 기본 빈값
    FACE_EVENT = "face_event"    # 얼굴장식(이벤트/기간제) - 기본 빈값
    BELT_EVENT = "belt_event"    # 벨트(이벤트/기간제) - 기본 빈값

    TITLE = "title"              # 칭호 - 기본 빈값
    PET_EQUIP = "pet_equip"      # 펫장비 - 기본 빈값


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
    acc: int = 0  # +명중(ACC)

    def __add__(self, other: "Effect") -> "Effect":
        return Effect(stats=self.stats + other.stats, acc=self.acc + other.acc)


@dataclass(frozen=True)
class Item:
    item_id: str
    name: str
    slot: EquipSlot
    effect: Effect
    icon_url: Optional[str] = None  # 나중에 몬스터/장비 이미지용


@dataclass
class EquipmentState:
    """
    - 슬롯별 장착 아이템
    - 상의/하의 vs 한벌옷은 토글로 관리
    """
    use_overall: bool = False
    equipped: Dict[EquipSlot, Optional[Item]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # 기본 슬롯을 다 만들어두되, 기본값은 None(빈 장착)
        for slot in EquipSlot:
            self.equipped.setdefault(slot, None)

    def iter_effects(self) -> Effect:
        total = Effect()
        for slot, item in self.equipped.items():
            if item is None:
                continue

            # 상/하의 vs 한벌옷 토글 처리
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
    """
    버프 스킬 / 도핑을 분리하되, 엔진에서는 같은 Effect로 합산 가능
    """
    skill_buffs: Dict[str, Effect] = field(default_factory=dict)  # key: buff_id
    doping: Dict[str, Effect] = field(default_factory=dict)       # key: doping_id

    def total_effect(self) -> Effect:
        total = Effect()
        for e in self.skill_buffs.values():
            total = total + e
        for e in self.doping.values():
            total = total + e
        return total


@dataclass
class CharacterInput:
    level: int
    job: JobGroup
    base_stats: Stats               # 순스탯(AP)
    maple_warrior_percent: float    # 예: 0.0, 0.1, 0.15, 0.2


@dataclass(frozen=True)
class DerivedResult:
    base_after_mw: Stats
    bonus_stats: Stats
    total_stats: Stats
    acc_from_stats: int
    acc_bonus: int
    acc_total: int


# -------------------------
# 2) 핵심 계산(버림 적용)
# -------------------------

def apply_maple_warrior(base: Stats, mw_percent: float) -> Stats:
    """
    메용: 순스탯에만 % 적용. 소수점은 버림.
    """
    return Stats(
        str=floor(base.str * (1.0 + mw_percent)),
        dex=floor(base.dex * (1.0 + mw_percent)),
        int=floor(base.int * (1.0 + mw_percent)),
        luk=floor(base.luk * (1.0 + mw_percent)),
    )


def calc_accuracy_from_stats(job: JobGroup, total_stats: Stats) -> int:
    """
    TODO: 직업군별 '스탯 -> 명중(ACC)' 공식
    - 다음 스텝에서 여기만 채우면 전체가 동작함
    """
    raise NotImplementedError("직업군별 명중 공식을 아직 연결하지 않았습니다.")


def derive_character_result(
    ch: CharacterInput,
    equipment: EquipmentState,
    buffs: BuffState,
) -> DerivedResult:
    equip_effect = equipment.iter_effects()
    buff_effect = buffs.total_effect()

    base_after_mw = apply_maple_warrior(ch.base_stats, ch.maple_warrior_percent)

    # 부가 = 장비 + (버프스킬 + 도핑) 에서 오는 스탯 증가
    bonus_stats = equip_effect.stats + buff_effect.stats

    total_stats = base_after_mw + bonus_stats

    # 명중 보너스 = 장비/버프/도핑에서 오는 +ACC 총합
    acc_bonus = equip_effect.acc + buff_effect.acc

    acc_from_stats = calc_accuracy_from_stats(ch.job, total_stats)
    acc_total = acc_from_stats + acc_bonus

    return DerivedResult(
        base_after_mw=base_after_mw,
        bonus_stats=bonus_stats,
        total_stats=total_stats,
        acc_from_stats=acc_from_stats,
        acc_bonus=acc_bonus,
        acc_total=acc_total,
    )
