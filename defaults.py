DEFAULT_BASE_STATS = Stats(str=4, dex=4, int=4, luk=4)

def make_character_input(
    level: int,
    job: JobGroup,
    base_stats: Stats | None = None,
    maple_warrior_percent: float = 0.0,
) -> CharacterInput:
    if base_stats is None:
        base_stats = DEFAULT_BASE_STATS
    return CharacterInput(
        level=level,
        job=job,
        base_stats=base_stats,
        maple_warrior_percent=maple_warrior_percent,
    )
