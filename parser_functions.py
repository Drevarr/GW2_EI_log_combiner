import config

# Top stats dictionary to store combined log data
top_stats = config.top_stats

team_colors = config.team_colors

buff_data = {}

skill_data = {}

def get_enemys_by_fight(fight_num: int, targets: list) -> None:
    """
    Organize targets by enemy for a fight.

    Args:
        fight_num (int): The number of the fight.
        targets (list): The list of targets in the fight.
    """
    if fight_num not in top_stats["fight"]:
        top_stats["fight"][fight_num] = {}

    for target in targets:
        if target["isFake"]:
            continue

        top_stats["fight"][fight_num]["enemy_count"] += 1

        team = target["teamID"]

        if team in team_colors:
            team = "enemy_" + team_colors[team]
        else:
            team = "enemy_Unk"

        if team not in top_stats["fight"][fight_num]:
            # Create a new team if it doesn't exist
            top_stats["fight"][fight_num][team] = 0

        top_stats["fight"][fight_num][team] += 1


def get_parties_by_fight(fight_num: int, players: list) -> None:
    """
    Organize players by party for a fight.

    Args:
        fight_num (int): The number of the fight.
        players (list): The list of players in the fight.
    """
    if fight_num not in top_stats["parties_by_fight"]:
        top_stats["parties_by_fight"][fight_num] = {}

    for player in players:
        if player["notInSquad"]:
            # Count players not in a squad
            top_stats["fight"][fight_num]["non_squad_count"] += 1
            continue
        top_stats["fight"][fight_num]["squad_count"] += 1
        group = player["group"]
        name = player["name"]
        if group not in top_stats["parties_by_fight"][fight_num]:
            # Create a new group if it doesn't exist
            top_stats["parties_by_fight"][fight_num][group] = []
        if name not in top_stats["parties_by_fight"][fight_num][group]:
            # Add the player to the group
            top_stats["parties_by_fight"][fight_num][group].append(name)


def get_stat_by_key(fight_num: int, player: dict, stat_category: str, name_prof: str) -> None:
    """
    Add player stats by key to top_stats dictionary

    Args:
        filename (str): The filename of the fight.
        player (dict): The player dictionary.
        stat_category (str): The category of stats to collect.
        name_prof (str): The name of the profession.
    """
    for stat, value in player[stat_category][0].items():
        top_stats['player'][name_prof][stat_category][stat] = top_stats['player'][name_prof][stat_category].get(stat, 0) + value
        top_stats['fight'][fight_num][stat_category][stat] = top_stats['fight'][fight_num][stat_category].get(stat, 0) + value
        top_stats['overall'][stat_category][stat] = top_stats['overall'][stat_category].get(stat, 0) + value


def get_stat_by_target_and_skill(fight_num: int, player: dict, stat_category: str, name_prof: str) -> None:
    """
    Add player stats by target and skill to top_stats dictionary

    Args:
        filename (str): The filename of the fight.
        player (dict): The player dictionary.
        stat_category (str): The category of stats to collect.
        name_prof (str): The name of the profession.
    """
    for target in player[stat_category]:
        if target[0]:
            for skill in target[0]:
                skill_id = skill['id']

                if skill_id not in top_stats['player'][name_prof][stat_category]:
                    top_stats['player'][name_prof][stat_category][skill_id] = {}
                if skill_id not in top_stats['fight'][fight_num][stat_category]:
                    top_stats['fight'][fight_num][stat_category][skill_id] = {}
                if skill_id not in top_stats['overall'][stat_category]:
                    top_stats['overall'][stat_category][skill_id] = {}
                    
                for stat, value in skill.items():
                    if stat != 'id':
                        top_stats['player'][name_prof][stat_category][skill_id][stat] = top_stats['player'][name_prof][stat_category][skill_id].get(
                            stat, 0) + value
                        top_stats['fight'][fight_num][stat_category][skill_id][stat] = top_stats['fight'][fight_num][stat_category][skill_id].get(
                            stat, 0) + value
                        top_stats['overall'][stat_category][skill_id][stat] = top_stats['overall'][stat_category][skill_id].get(stat, 0) + value


def get_stat_by_target(fight_num: int, player: dict, stat_category: str, name_prof: str) -> None:
    """
    Add player stats by target to top_stats dictionary

    Args:
        filename (str): The filename of the fight.
        player (dict): The player dictionary.
        stat_category (str): The category of stats to collect.
        name_prof (str): The name of the profession.
    """
    if stat_category not in top_stats['player'][name_prof]:
        top_stats['player'][name_prof][stat_category] = {}

    for target in player[stat_category]:
        if target[0]:
            for stat, value in target[0].items():
                top_stats['player'][name_prof][stat_category][stat] = top_stats['player'][name_prof][stat_category].get(stat, 0) + value
                top_stats['fight'][fight_num][stat_category][stat] = top_stats['fight'][fight_num][stat_category].get(stat, 0) + value
                top_stats['overall'][stat_category][stat] = top_stats['overall'][stat_category].get(stat, 0) + value


def get_stat_by_skill(fight_num: int, player: dict, stat_category: str, name_prof: str) -> None:
    """
    Add player stats by skill to top_stats dictionary

    Args:
        filename (str): The filename of the fight.
        player (dict): The player dictionary.
        stat_category (str): The category of stats to collect.
        name_prof (str): The name of the profession.
    """
    for skill in player[stat_category][0]:
        if skill:
            skill_id = skill['id']
            if skill_id not in top_stats['player'][name_prof][stat_category]:
                top_stats['player'][name_prof][stat_category][skill_id] = {}
            if skill_id not in top_stats['fight'][fight_num][stat_category]:
                top_stats['fight'][fight_num][stat_category][skill_id] = {}
            if skill_id not in top_stats['overall'][stat_category]:
                top_stats['overall'][stat_category][skill_id] = {}

            for stat, value in skill.items():
                if stat != 'id':
                    top_stats['player'][name_prof][stat_category][skill_id][stat] = top_stats['player'][name_prof][stat_category][skill_id].get(stat, 0) + value
                    top_stats['fight'][fight_num][stat_category][skill_id][stat] = top_stats['fight'][fight_num][stat_category][skill_id].get(stat, 0) + value
                    top_stats['overall'][stat_category][skill_id][stat] = top_stats['overall'][stat_category][skill_id].get(stat, 0) + value


def get_buff_uptimes(fight_num: int, player: dict, stat_category: str, name_prof: str, fight_duration: int, active_time: int) -> None:
    """
    Calculate buff uptime stats for a player

    Args:
        filename (str): The filename of the fight.
        player (dict): The player dictionary.
        stat_category (str): The category of stats to collect.
        name_prof (str): The name of the profession.
        fight_duration (int): The duration of the fight in milliseconds.
        active_time (int): The duration of the player's active time in milliseconds.

    Returns:
        None
    """
    for buff in player[stat_category]:
        buff_id = buff['id']
        buff_uptime_ms = buff['buffData'][0]['uptime'] * fight_duration / 100
        buff_presence = buff['buffData'][0]['presence']

        if buff_id not in top_stats['player'][name_prof][stat_category]:
            top_stats['player'][name_prof][stat_category][buff_id] = {}
        if buff_id not in top_stats['fight'][fight_num][stat_category]:
            top_stats['fight'][fight_num][stat_category][buff_id] = {}
        if buff_id not in top_stats['overall'][stat_category]:
            top_stats['overall'][stat_category][buff_id] = {}

        if stat_category == 'buffUptimes':
            stat_value = buff_presence * fight_duration / 100 if buff_presence else buff_uptime_ms
        elif stat_category == 'buffUptimesActive':
            stat_value = buff_presence * active_time / 100 if buff_presence else buff_uptime_ms

        top_stats['player'][name_prof][stat_category][buff_id]['uptime_ms'] = top_stats['player'][name_prof][stat_category][buff_id].get('uptime_ms', 0) + stat_value
        top_stats['fight'][fight_num][stat_category][buff_id]['uptime_ms'] = top_stats['fight'][fight_num][stat_category][buff_id].get('uptime_ms', 0) + stat_value
        top_stats['overall'][stat_category][buff_id]['uptime_ms'] = top_stats['overall'][stat_category][buff_id].get('uptime_ms', 0) + stat_value


def get_buff_generation(fight_num: int, player: dict, stat_category: str, name_prof: str, duration: int, buff_data: dict, squad_count: int, group_count: int) -> None:
    """
    Calculate buff generation stats for a player

    Args:
        fight_num (int): The number of the fight.
        player (dict): The player dictionary.
        stat_category (str): The category of stats to collect.
        name_prof (str): The name of the profession.
        duration (int): The duration of the fight in milliseconds.
        buff_data (dict): A dictionary of buff IDs to their data.
        squad_count (int): The number of players in the squad.
        group_count (int): The number of players in the group.
    """
    for buff in player.get(stat_category, []):
        buff_id = str(buff['id'])
        buff_stacking = buff_data[buff_id].get('stacking', False)

        if buff_id not in top_stats['player'][name_prof][stat_category]:
            top_stats['player'][name_prof][stat_category][buff_id] = {}
        if buff_id not in top_stats['fight'][fight_num][stat_category]:
            top_stats['fight'][fight_num][stat_category][buff_id] = {}
        if buff_id not in top_stats['overall'][stat_category]:
            top_stats['overall'][stat_category][buff_id] = {}

        buff_generation = buff['buffData'][0].get('generation', 0)
        buff_wasted = buff['buffData'][0].get('wasted', 0)

        if buff_stacking:
            if stat_category == 'squadBuffs':
                buff_generation *= duration * (squad_count - 1)
                buff_wasted *= duration * (squad_count - 1)
            elif stat_category == 'groupBuffs':
                buff_generation *= duration * (group_count - 1)
                buff_wasted *= duration * (group_count - 1)
            elif stat_category == 'selfBuffs':
                buff_generation *= duration
                buff_wasted *= duration

        else:
            if stat_category == 'squadBuffs':
                buff_generation = (buff_generation / 100) * duration * (squad_count-1)
                buff_wasted = (buff_wasted / 100) * duration * (squad_count-1)
            elif stat_category == 'groupBuffs':
                buff_generation = (buff_generation / 100) * duration * (group_count-1)
                buff_wasted = (buff_wasted / 100) * duration * (group_count-1)
            elif stat_category == 'selfBuffs':
                buff_generation = (buff_generation / 100) * duration
                buff_wasted = (buff_wasted / 100) * duration

                
        top_stats['player'][name_prof][stat_category][buff_id]['generation'] = top_stats['player'][name_prof][stat_category][buff_id].get('generation', 0) + buff_generation
        top_stats['player'][name_prof][stat_category][buff_id]['wasted'] = top_stats['player'][name_prof][stat_category][buff_id].get('wasted', 0) + buff_wasted

        top_stats['fight'][fight_num][stat_category][buff_id]['generation'] = top_stats['fight'][fight_num][stat_category][buff_id].get('generation', 0) + buff_generation
        top_stats['fight'][fight_num][stat_category][buff_id]['wasted'] = top_stats['fight'][fight_num][stat_category][buff_id].get('wasted', 0) + buff_wasted

        top_stats['overall'][stat_category][buff_id]['generation'] = top_stats['overall'][stat_category][buff_id].get('generation', 0) + buff_generation
        top_stats['overall'][stat_category][buff_id]['wasted'] = top_stats['overall'][stat_category][buff_id].get('wasted', 0) + buff_wasted


def get_skill_cast_by_prof_role(fight_num: int, player: dict, stat_category: str, name_prof: str) -> None:
    name = player['name']
    profession = player['profession']
    role = player['role']
    prof_role = profession + ' {{' + role + '}}'
    
    
    if prof_role not in top_stats['skill_casts_by_role']:
        top_stats['skill_casts_by_role'][prof_role] = {
            'total': {}
        }

    if name_prof not in top_stats['skill_casts_by_role'][prof_role]:
        top_stats['skill_casts_by_role'][prof_role][name_prof] = {}


    for skill in player['rotation']:
        skill_id = skill['id']

        if skill_id not in top_stats['skill_casts_by_role'][prof_role][name_prof]:
            top_stats['skill_casts_by_role'][prof_role][name_prof][skill_id] = 0
        if skill_id not in top_stats['skill_casts_by_role'][prof_role]['total']:
            top_stats['skill_casts_by_role'][prof_role]['total'][skill_id] = 0

        top_stats['skill_casts_by_role'][prof_role]['total'][skill_id] = top_stats['skill_casts_by_role'][prof_role]['total'][skill_id].get('total', 0) + 1
        top_stats['skill_casts_by_role'][prof_role][name_prof][skill_id] = top_stats['skill_casts_by_role'][prof_role][name_prof].get(skill_id, 0) + 1