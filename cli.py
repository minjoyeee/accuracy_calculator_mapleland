import argparse

from .defaults import DEFAULT_BASE_STATS
from .engine import derive_character_result, check_hit
from .models import BuffState, CharacterInput, EquipmentState, JobGroup, Stats, Monster, EquipSlot, Effect, Item, Stats
from .data_store import load_monsters, load_effect_catalog, load_items, load_named_effect_catalog

import json
from pathlib import Path

def parse_kv_int_list(spec: str) -> dict[str, int]:
    """
    "acc=7,dex=3,luk=1" -> {"acc":7,"dex":3,"luk":1}
    """
    out: dict[str, int] = {}
    if not spec:
        return out
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"커스텀 옵션 형식 오류: '{part}' (key=value 필요)")
        k, v = part.split("=", 1)
        k = k.strip().lower()
        v = v.strip()
        out[k] = int(v)
    return out

def make_custom_item(slot: "EquipSlot", kv: dict[str, int]) -> Item:
    acc = kv.pop("acc", 0)
    s = Stats(
        str=kv.pop("str", 0),
        dex=kv.pop("dex", 0),
        int=kv.pop("int", 0),
        luk=kv.pop("luk", 0),
    )
    if kv:
        raise ValueError(f"허용되지 않은 키: {list(kv.keys())} (허용: str,dex,int,luk,acc)")
    return Item(
        item_id=f"custom_{slot.value}",
        name=f"(커스텀 {slot.value})",
        slot=slot,
        effect=Effect(stats=s, acc=acc),
        icon_url=None,
    )

def make_custom_effect(kv: dict[str, int]) -> Effect:
    acc = kv.pop("acc", 0)
    s = Stats(
        str=kv.pop("str", 0),
        dex=kv.pop("dex", 0),
        int=kv.pop("int", 0),
        luk=kv.pop("luk", 0),
    )
    if kv:
        raise ValueError(f"허용되지 않은 키: {list(kv.keys())} (허용: str,dex,int,luk,acc)")
    return Effect(stats=s, acc=acc)

def export_build_json(path: str, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def import_build_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def format_effect(e: "Effect") -> str:
    s = e.stats
    parts = []
    if s.str: parts.append(f"STR {s.str:+d}")
    if s.dex: parts.append(f"DEX {s.dex:+d}")
    if s.int: parts.append(f"INT {s.int:+d}")
    if s.luk: parts.append(f"LUK {s.luk:+d}")
    if e.acc: parts.append(f"ACC {e.acc:+d}")
    return " / ".join(parts) if parts else "(효과 없음)"


def add_effect(a: "Effect", b: "Effect") -> "Effect":
    # Effect.__add__가 이미 있으니 a+b로 써도 되지만, 의도를 명확히 하려고 분리
    return a + b


def parse_custom_effect_from_rhs(rhs: str) -> "Effect":
    # rhs: "custom:acc=10,dex=3"
    kv = parse_kv_int_list(rhs[len("custom:"):])
    return make_custom_effect(kv)


#############################
##### main func section #####
#############################

def main() -> None:
    ##### arguments section #####
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", type=int, default=30)
    parser.add_argument("--job", type=str, default="archer", choices=["warrior","archer","thief","mage"])
    parser.add_argument("--str", dest="st", type=int, default=4)
    parser.add_argument("--dex", type=int, default=4)
    parser.add_argument("--int", dest="it", type=int, default=4)
    parser.add_argument("--luk", type=int, default=4)
    # parser.add_argument("--mw", type=float, default=0.15)  # 예: 0.15
    parser.add_argument("--mw", type=float, default=0.0, help="메용 퍼센트(소수). 예: 0.15")
    parser.add_argument("--mw-on", action="store_true", help="메용 적용(마스터 15%)")

    parser.add_argument("--mw-percent", type=int, default=None, help="메용 퍼센트로 입력(예: 15). 주면 --mw보다 우선")

    parser.add_argument("--monster", type=str, default="test_mob", help="대상 몬스터 선택")
    parser.add_argument("--buff", action="append", default=[])   # 여러 번 가능: --buff bless
    parser.add_argument("--doping", action="append", default=[]) # 여러 번 가능: --doping acc_pill
    parser.add_argument("--equip", action="append",default=[], help="장비 장착: --equip gloves=work_gloves (여러번 가능)",)
    
    parser.add_argument("--list-items", type=str, default=None, help="슬롯별 아이템 목록 출력 후 종료. 예) --list-items gloves",)
    parser.add_argument("--list-items-all", action="store_true", help="전체 아이템 프리셋 목록 출력 후 종료")
    parser.add_argument("--find-item", type=str, default=None, help="아이템 이름 부분검색 후 종료. 예) --find-item 장갑")

    parser.add_argument("--list-buffs", action="store_true", help="버프 스킬 프리셋 목록 출력 후 종료")
    parser.add_argument("--list-doping", action="store_true", help="도핑 프리셋 목록 출력 후 종료")
    parser.add_argument("--list-monsters", action="store_true", help="몬스터 프리셋 목록 출력 후 종료")
    parser.add_argument("--find-monster", type=str, default=None, help="몬스터 이름 부분검색 후 종료. 예) --find-monster 스텀프")
    parser.add_argument("--equip-find", action="append", default=[], help="형식: slot=키워드  (검색 결과 1개면 자동 장착). 예) --equip-find gloves=작업")

    


    
    parser.add_argument("--export", type=str, default=None, help="현재 입력을 JSON으로 저장. 예) --export build.json")
    parser.add_argument("--import", dest="import_path", type=str, default=None, help="JSON 빌드 불러오기. 예) --import build.json")
    parser.add_argument("--show-loadout", action="store_true", help="현재 적용된 장비/버프/도핑 목록 출력")
    
    ##### End arguments section #####

    args = parser.parse_args()
    
    if args.import_path is not None:
        build = import_build_json(args.import_path)

        # build에서 args를 덮어쓰기(혼란 방지 목적: import가 있으면 build 기준)
        args.level = int(build["character"]["level"])
        args.job = str(build["character"]["job"])
        bs = build["character"]["base_stats"]
        args.st = int(bs["str"])
        args.dex = int(bs["dex"])
        args.it = int(bs["int"])
        args.luk = int(bs["luk"])

        args.mw_on = bool(build["character"].get("mw_on", False))
        args.mw = float(build["character"].get("mw", 0.0))

        args.monster = str(build["monster"]["id"])
        args.equip = list(build.get("equip", []))
        args.buff = list(build.get("buff", []))
        args.doping = list(build.get("doping", []))


    monsters = load_monsters()
    
    if args.list_monsters:
        print("[MONSTERS]")
        for mid, m in monsters.items():
            print(f"- {mid}: {m.name} (Lv{m.level}, EVA{m.evasion})")
        return

    if args.find_monster is not None:
        key = args.find_monster.strip().lower()
        print(f"[MONSTER SEARCH] keyword='{args.find_monster}'")
        found = False
        for mid, m in monsters.items():
            if key in m.name.lower():
                print(f"- {mid}: {m.name} (Lv{m.level}, EVA{m.evasion})")
                found = True
        if not found:
            print("(no matches)")
        return
    
    buff_catalog = load_effect_catalog("buff_skills.json")
    doping_catalog = load_effect_catalog("doping.json")
    
    named_buff = load_named_effect_catalog("buff_skills.json")
    named_doping = load_named_effect_catalog("doping.json")
    
    items = load_items()
    
    if args.list_items_all:
        print("[ITEMS ALL]")
        for it in items.values():
            print(f"- {it.item_id}: {it.name} (slot={it.slot.value})  |  {format_effect(it.effect)}")
        return

    if args.find_item is not None:
        key = args.find_item.strip().lower()
        print(f"[ITEM SEARCH] keyword='{args.find_item}'")
        found = False
        for it in items.values():
            if key in it.name.lower():
                print(f"- {it.item_id}: {it.name} (slot={it.slot.value})  |  {format_effect(it.effect)}")
                found = True
        if not found:
            print("(no matches)")
        return

    
    if args.list_items is not None:
        slot = EquipSlot(args.list_items)
        print(f"[ITEMS] slot={slot.value}")
        for item in items.values():
            if item.slot == slot:
                e = item.effect
                s = e.stats
                print(f"- {item.item_id}: {item.name} | +ACC {e.acc} | STR {s.str} DEX {s.dex} INT {s.int} LUK {s.luk}")
        return
    
    if args.list_buffs:
        print("[BUFF SKILLS]")
        for bid, (name, e) in named_buff.items():
            print(f"- {bid}: {name}  |  {format_effect(e)}")
        return

    if args.list_doping:
        print("[DOPING]")
        for did, (name, e) in named_doping.items():
            print(f"- {did}: {name}  |  {format_effect(e)}")
        return

    mw = args.mw
    
    if args.mw_on and mw == 0.0:
        mw = 0.15  # 마스터 기준

    ch = CharacterInput(
        level=args.level,
        job=JobGroup(args.job),
        base_stats=Stats(str=args.st, dex=args.dex, int=args.it, luk=args.luk),
        maple_warrior_percent=mw,
    )
    
    # export용 payload (입력 상태 저장)
    export_payload = {
        "version": 1,
        "character": {
            "level": args.level,
            "job": args.job,
            "base_stats": {"str": args.st, "dex": args.dex, "int": args.it, "luk": args.luk},
            "mw_on": bool(args.mw_on),
            "mw": float(mw),
        },
        "monster": {"id": args.monster},
        "equip": list(args.equip),
        "buff": list(args.buff),
        "doping": list(args.doping),
    }

    if args.export is not None:
        export_build_json(args.export, export_payload)
        print(f"[EXPORTED] {args.export}")


    equipment = EquipmentState(use_overall=False)
    
    # --equip-find gloves=작업  (해당 슬롯에서 이름 부분검색)
    for spec in args.equip_find:
        slot_s, keyword = spec.split("=", 1)
        slot = EquipSlot(slot_s)
        key = keyword.strip().lower()

        candidates = [it for it in items.values() if it.slot == slot and key in it.name.lower()]
        if len(candidates) == 0:
            raise ValueError(f"[equip-find] 검색 결과 없음: slot={slot.value}, keyword='{keyword}'")
        if len(candidates) > 1:
            print(f"[equip-find] 검색 결과가 여러 개입니다: slot={slot.value}, keyword='{keyword}'")
            for it in candidates:
                print(f"- {it.item_id}: {it.name}  |  {format_effect(it.effect)}")
            raise ValueError("[equip-find] 하나로 좁혀주세요(키워드 구체화)")

        chosen = candidates[0]
        equipment.equipped[slot] = chosen
        print(f"[equip-find] equipped {slot.value} = {chosen.item_id} ({chosen.name})")

    
    # ✅ (추가) --equip 처리 블록은 여기!
    for spec in args.equip:
        slot_s, rhs = spec.split("=", 1)
        slot = EquipSlot(slot_s)

        # 1) 커스텀: custom:acc=7,dex=3
        if rhs.startswith("custom:"):
            kv = parse_kv_int_list(rhs[len("custom:"):])
            item = make_custom_item(slot, kv)

        # 2) 프리셋 아이템 id: work_gloves
        else:
            item = items[rhs]
            if item.slot != slot:
                raise ValueError(
                    f"아이템 슬롯 불일치: {item.name}는 {item.slot.value}인데 {slot.value}에 장착 시도"
                )

        equipment.equipped[slot] = item
    
    buffs = BuffState()

    # 버프 스킬 적용: 프리셋 id 또는 custom:
    for i, bid in enumerate(args.buff):
        if bid.startswith("custom:"):
            e = parse_custom_effect_from_rhs(bid)
            buffs.skill_buffs[f"custom_buff_{i}"] = EffectSpec(name="(커스텀 버프)", effect=e, acc_group=None)
        else:
            buffs.skill_buffs[bid] = named_buff[bid]

    # 도핑 적용: 프리셋 id 또는 custom:
    for i, did in enumerate(args.doping):
        if did.startswith("custom:"):
            e = parse_custom_effect_from_rhs(did)
            buffs.doping[f"custom_doping_{i}"] = EffectSpec(name="(커스텀 도핑)", effect=e, acc_group=None)
        else:
            buffs.doping[did] = named_doping[did]

    if args.show_loadout:
        print("[LOADOUT]")

        # 1) 장비 출력 + 합계
        equip_total = Effect()
        if args.equip:
            print("Equipments:")
            for spec in args.equip:
                slot_s, rhs = spec.split("=", 1)
                slot = EquipSlot(slot_s)

                if rhs.startswith("custom:"):
                    e = parse_custom_effect_from_rhs(rhs)
                    name = f"(커스텀 장비)"
                else:
                    it = items[rhs]
                    e = it.effect
                    name = it.name

                equip_total = equip_total + e
                print(f"- {slot.value}: {name}  |  {format_effect(e)}")
        else:
            print("Equipments: (없음)")

        # 2) 버프 스킬 출력 + 합계
        buff_total = Effect()
        if args.buff:
            print("Buff Skills:")
            for bid in args.buff:
                if bid.startswith("custom:"):
                    e = parse_custom_effect_from_rhs(bid)
                    name = "(커스텀 버프)"
                else:
                    spec = named_buff[bid]
                    name = spec.name
                    e = spec.effect


                buff_total = buff_total + e
                print(f"- {name}  |  {format_effect(e)}")
        else:
            print("Buff Skills: (없음)")

        # 3) 도핑 출력 + 합계
        doping_total = Effect()
        if args.doping:
            print("Doping:")
            for did in args.doping:
                if did.startswith("custom:"):
                    e = parse_custom_effect_from_rhs(did)
                    name = "(커스텀 도핑)"
                else:
                    spec = named_doping[did]
                    name = spec.name
                    e = spec.effect


                doping_total = doping_total + e
                print(f"- {name}  |  {format_effect(e)}")
        else:
            print("Doping: (없음)")

        # 4) 합계 요약 (⚠️ 버프/도핑은 중첩 규칙을 BuffState.total_effect()로 반영)
        buffs_effect = buffs.total_effect()          # 스탯 합산 + ACC 그룹 max 규칙 적용 결과
        equip_effect = equipment.iter_effects()      # 장비는 그대로 합산

        total_bonus = equip_effect + buffs_effect

        print("Summary:")
        print(f"- Equip total : {format_effect(equip_effect)}")
        print(f"- Buff+Doping (rule): {format_effect(buffs_effect)}")
        print(f"- Bonus total : {format_effect(total_bonus)}")
        print()
        
    result = derive_character_result(ch, equipment, buffs)

    mob = monsters[args.monster]
    hit = check_hit(result.acc_total, ch.level, mob)

    print("base_after_mw:", result.base_after_mw)
    print("bonus_stats:", result.bonus_stats)
    print("total_stats:", result.total_stats)
    print("acc_total:", result.acc_total, "(acc_from_stats:", result.acc_from_stats, "+ acc_bonus:", result.acc_bonus, ")")
    print("monster:", mob.name, f"(Lv{mob.level}, EVA{mob.evasion})")
    print("acc_required:", hit.acc_required)
    print("hit:", "충분" if hit.is_sufficient else "부족", "margin:", hit.margin)
    print("mw:", mw)

if __name__ == "__main__":
    main()
