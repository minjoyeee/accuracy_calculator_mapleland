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
    # TODO: 직업군별 명중 공식 연결
    # 지금은 Step(1) 합산 파이프라인 테스트용으로 0 반환
    return 0


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
