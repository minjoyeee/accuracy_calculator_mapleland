from defaults import DEFAULT_BASE_STATS
from models import Stats, JobGroup, CharacterInput, EquipmentState, BuffState
from engine import derive_character_result

def main():
    ch = CharacterInput(
        level=50,
        job=JobGroup.ARCHER,
        base_stats=DEFAULT_BASE_STATS,  # 기본 4/4/4/4
        maple_warrior_percent=0.0,
    )
    equipment = EquipmentState()
    buffs = BuffState()

    # 아직 calc_accuracy_from_stats 미구현이면 임시로 0 반환 처리 필요
    result = derive_character_result(ch, equipment, buffs)
    print(result)

if __name__ == "__main__":
    main()
