from defaults import DEFAULT_BASE_STATS
from engine import derive_character_result
from models import BuffState, CharacterInput, EquipmentState, JobGroup


def main() -> None:
    ch = CharacterInput(
        level=30,
        job=JobGroup.ARCHER,
        base_stats=DEFAULT_BASE_STATS,      # 기본 4/4/4/4
        maple_warrior_percent=0.15,         # 예: 메용 15%
    )

    equipment = EquipmentState(use_overall=False)
    buffs = BuffState()

    # 예시로 버프/도핑 효과 하나 넣어보기 (나중에 프리셋으로 교체)
    # buffs.skill_buffs["bless"] = Effect(stats=Stats(dex=0, luk=0), acc=20)

    result = derive_character_result(ch, equipment, buffs)

    print("base_after_mw:", result.base_after_mw)
    print("bonus_stats:", result.bonus_stats)
    print("total_stats:", result.total_stats)
    print("acc_total:", result.acc_total, "(acc_from_stats:", result.acc_from_stats, "+ acc_bonus:", result.acc_bonus, ")")


if __name__ == "__main__":
    main()
