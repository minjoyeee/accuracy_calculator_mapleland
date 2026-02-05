from __future__ import annotations

from math import floor

from models import BuffState, CharacterInput, DerivedResult, EquipmentState, JobGroup, Stats


def apply_maple_warrior(base: Stats, mw_percent: float) -> Stats:
    # 메용: 순스탯에만 % 적용, 소수점 버림
    return Stats(
        str=floor(base.str * (1.0 + mw_percent)),
        dex=floor(base.dex * (1.0 + mw_percent)),
        int=floor(base.int * (1.0 + mw_percent)),
        luk=floor(base.luk * (1.0 + mw_percent)),
    )


def calc_accuracy_from_stats(job: JobGroup, total_stats: Stats) -> int:
    if job == JobGroup.MAGE:
        # 마법 명중: (INT/10) + (LUK/10), 각각 버림 후 더함
        return (total_stats.int // 10) + (total_stats.luk // 10)

    # 물리 직업(전사/궁수/도적): floor(DEX*0.8 + LUK*0.5)
    return floor(total_stats.dex * 0.8 + total_stats.luk * 0.5)


def derive_character_result(
    ch: CharacterInput,
    equipment: EquipmentState,
    buffs: BuffState,
) -> DerivedResult:
    equip_effect = equipment.iter_effects()
    buff_effect = buffs.total_effect()

    base_after_mw = apply_maple_warrior(ch.base_stats, ch.maple_warrior_percent)

    bonus_stats = equip_effect.stats + buff_effect.stats
    total_stats = base_after_mw + bonus_stats

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
