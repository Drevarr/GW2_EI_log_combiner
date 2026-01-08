#    This file contains the configuration for computing the detailed top stats in arcdps logs as parsed by Elite Insights.
#    Copyright (C) 2024 John Long (Drevarr)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


import config
import gzip
import json
import math
import requests
import time
from typing import Optional, Dict
from requests.exceptions import RequestException, HTTPError, Timeout, ConnectionError
from collections import OrderedDict, defaultdict

# Top stats dictionary to store combined log data
top_stats = config.top_stats

stats_per_fight = defaultdict(
	lambda: defaultdict(          # name_prof
		lambda: defaultdict(list) # stat → [values]
	)
)			


team_colors = config.team_colors
team_code_missing = []
mesmer_shatter_skills = config.mesmer_shatter_skills
mesmer_clone_usage = {}
enemy_avg_damage_per_skill = {}
player_damage_mitigation = {}
player_minion_damage_mitigation = {}

# Buff and skill data collected from all logs
buff_data = {}
skill_data = {}
damage_mod_data = {}
high_scores = {}
fb_pages = {}
mechanics = {}
minions = {}
personal_damage_mod_data = {
	"total": [],
}
personal_buff_data = {
	"total": [],
}

players_running_healing_addon = []

On_Tag = 600
Run_Back = 5000
death_on_tag = {}
commander_tag_positions = {}
commander_summary_data = {}

DPSStats = {}
stacking_uptime_Table = {}
IOL_revive = {}
debuff_damage = {}
fight_data = {}
killing_blow_rallies = {
	"total": 0,
	'kb_players': {}
}

health_data = {}

def get_player_account(player):
	"""
	Get the account name of a player

	Args:
		player (dict): The player data from the log

	Returns:
		str: The account name of the player
	"""
	if len(player['account'].split('-')) >=1:
		account = player['account'].replace("-", ".")
	else:
		account = player['account']
	return account


def get_fight_data(player, fight_num):
	"""
	Get the fight data for a player in a given fight

	Args:
		player (dict): The player data from the log
		fight_num (int): The fight number to add the data to

	Returns:
		None
	"""
	account = get_player_account(player)
	player_id = f"{account}-{player['profession']}-{player['name']}"
	if fight_num not in fight_data:
		fight_data[fight_num] = {
			"damage1S": {},
			"damageTaken1S": {},
			"players": {}
		}

	if player['dpsAll'][0]['dps'] >= 700:
		if player_id not in fight_data[fight_num]["players"]:
			fight_data[fight_num]["players"][player_id] = {
				"damage1S": {},
				"damageTaken1S": player["damageTaken1S"][0]
			}
			for target in player["targetDamage1S"]:
				prior_damage = 0
				for sec_index in range(len(target[0])):
					cur_damage = target[0][sec_index] - prior_damage
					fight_data[fight_num]["damage1S"][sec_index] = fight_data[fight_num]["damage1S"].get(sec_index, 0) + cur_damage
					fight_data[fight_num]["players"][player_id]["damage1S"][sec_index] = fight_data[fight_num]["players"][player_id]["damage1S"].get(sec_index, 0)+cur_damage

					prior_damage = target[0][sec_index]
					
	last_index = 0

	for index in range(len(player["damageTaken1S"][0])):
		current_damage_taken = player["damageTaken1S"][0][index] - player["damageTaken1S"][0][last_index]
		fight_data[fight_num]["damageTaken1S"][index] = fight_data[fight_num]["damageTaken1S"].get(index, 0) + current_damage_taken
		last_index = index


def check_burst1S_high_score(fight_data, player, fight_num):
	for player_id in fight_data[fight_num]["players"]:
		account, profession, name = player_id.split("-")
		max_burst1S_key = max(fight_data[fight_num]["players"][player_id]["damage1S"], key=fight_data[fight_num]["players"][player_id]["damage1S"].get)
		max_burst1S_value = fight_data[fight_num]["players"][player_id]["damage1S"][max_burst1S_key]

		update_high_score(
			"burst_damage1S",
			"{{"+profession+"}}"+name+"-"+account+"-"+str(fight_num)+"-burst1S",
			round(max_burst1S_value, 2)	
		)
			


def determine_log_type_and_extract_fight_name(fight_name: str) -> tuple:
	"""
	Determine if the log is a PVE or WVW log and extract the fight name.

	If the log is a WVW log, the fight name is extracted after the " - " delimiter.
	If the log is a PVE log, the original fight name is returned.

	Args:
		fight_name (str): The name of the fight.

	Returns:
		tuple: A tuple containing the log type and the extracted fight name.
	"""
	if "Detailed WvW" in fight_name:
		# WVW log
		log_type = "WVW"
		fight_name = fight_name.split(" - ")[1]
	elif "World vs World" in fight_name:
		# WVW log
		log_type = "WVW-Not-Detailed"
		fight_name = fight_name.split(" - ")[1]
	elif "Detailed" in fight_name:
		log_type = "WVW"
		fight_name = fight_name.replace("Detailed ", "")
	else:
		# PVE log
		log_type = "PVE"
	return log_type, fight_name

def calculate_resist_offset(resist_data: dict, state_data: dict) -> int:
	"""
	Calculate the total time a player has resist during a set of states.

	Args:
		resist_data (dict): A dictionary mapping resist start times to end times.
		state_data (dict): A dictionary mapping state start times to end times.

	Returns:
		int: The total resist offset time.
	"""
	total_offset = 0
	for state_start in state_data:
		state_end = state_data[state_start]
		for resist_start in resist_data:
			resist_end = resist_data[resist_start]
			if resist_start <= state_end <= resist_end and state_start >= resist_start:
				total_offset += state_end - state_start
			elif state_end > resist_end and state_start >= resist_start and state_start <= resist_end:
				total_offset += resist_end - state_start
			elif state_end < resist_end and state_end >= resist_start and state_start < resist_start:
				total_offset += state_end - resist_start
	return total_offset

def determine_clone_usage(player, skill_map, mesmer_shatter_skills):
	"""
	Determine Mesmer clone usage for a given player.

	This function loops over each skill in the player's rotation and checks if the skill is a Mesmer shatter skill.
	If the skill is a Mesmer shatter skill, this function then loops over each cast of the skill and checks what clone state the Mesmer was in at the time of the cast.
	The total time the Mesmer was in each clone state is then recorded in the mesmer_clone_usage dictionary.

	Args:
		player (dict): A dictionary containing information about the player.
		skill_map (dict): A dictionary mapping skill IDs to skill names.
		mesmer_shatter_skills (list): A list of Mesmer shatter skills.

	Returns:
		None
	"""
	active_clones = {}
	name_prof = f"{player['name']}_{player['profession']}_{get_player_account(player)}"
	if name_prof not in mesmer_clone_usage:
		mesmer_clone_usage[name_prof] = {}
	if "activeClones" in player:
		for timestamp in player['activeClones']:
			active_clones[timestamp[0]] = timestamp[1]
	if "rotation" in player:
		for skill in player["rotation"]:
			skill_id = f"s{skill['id']}"
			if skill_id in mesmer_shatter_skills:
				skill_name = skill_map[skill_id]['name']

				if skill_name not in mesmer_clone_usage[name_prof]:
					mesmer_clone_usage[name_prof][skill_name] = {}

				for item in skill['skills']:
					cast_time = item['castTime']
					for key, value in reversed(list(active_clones.items())):
						if key <= cast_time:
							mesmer_clone_usage[name_prof][skill_name][value] = mesmer_clone_usage[name_prof][skill_name].get(value, 0) + 1 #value
							break

def get_buff_states(buff_states: list) -> dict:
	"""
	Convert a list of (time, state) pairs into a dictionary mapping start times to end times for a buff.

	:param buff_states: A list of (time, state) pairs where state is 1 when the buff is active and 0 when it is inactive.
	:return: A dictionary mapping start times to end times for the buff.
	"""
	start_times = []
	end_times = []

	for time, state in buff_states:
		if time == 0 and state == 0:
			continue
		elif state == 1:
			start_times.append(time)
		elif state == 0:
			end_times.append(time)

	return dict(zip(start_times, end_times))

def calculate_moving_average(data: list, window_size: int) -> list:
	"""
	Calculate the moving average of a list of numbers with a specified window size.

	Args:
		data (list): The list of numbers to calculate the moving average for.
		window_size (int): The number of elements to include in the moving average calculation.

	Returns:
		list: A list of the moving averages for each element in the input list.
	"""
	ma = []
	for i in range(len(data)):
		start_index = max(0, i - window_size)
		end_index = min(len(data), i + window_size)
		sub_data = data[start_index:end_index + 1]
		ma.append(sum(sub_data) / len(sub_data))
	return ma

def find_lowest(dict):
	"""
	Find the key-value pair(s) with the lowest value in a dictionary.

	Args:
		dict (dict): A dictionary where the values are comparable.

	Returns:
		list: A list containing the key(s) and the lowest value found in the dictionary.
	"""

	temp = min(dict.values())
	res = []
	for key, value in dict.items():
		if(value == temp):
			res.append(key)
			res.append(value)
	return res

def find_smallest_value(my_dict):
	"""
	Find the key with the smallest value in a dictionary.

	Args:
		my_dict (dict): A dictionary where the values are comparable.

	Returns:
		str: The key with the smallest value in the dictionary, or "Dictionary is empty" if the dictionary is empty.
	"""
	if not my_dict:
		return "Dictionary is empty"
	
	min_key = min(my_dict, key=my_dict.get)
	return min_key

def calculate_damage_during_buff(player, target_idx, buff_start, buff_end, damage_type):

	"""
	Calculate the damage a player did to a target during a given buff window.

	Args:
		player (dict): A dictionary containing information about the player.
		target_idx (int): The index of the target in the player's targets list.
		buff_start (float): The start time of the buff window in milliseconds.
		buff_end (float): The end time of the buff window in milliseconds.
		damage_type (str): The type of damage to calculate (e.g. "dps", "powerDps", etc.).

	Returns:
		float: The damage the player did to the target during the buff window.
	"""
	start_idx = math.floor(buff_start / 1000)
	end_idx = math.ceil(buff_end / 1000)

	current_damage = player[damage_type][target_idx][0][end_idx] - player[damage_type][target_idx][0][start_idx]
			
	return current_damage

def check_target_for_buff_start_end(targets, players, damage_buff_ids):
	"""
	Check each target for active buffs and calculate the total damage done by players during the buff duration.

	This function iterates over a list of targets and checks for specific buffs in each target. For each buff found,
	it calculates the damage done by each player during the active duration of the buff. The damage is accumulated for
	each player and stored in a global dictionary `debuff_damage`.

	Args:
		targets (list): A list of target dictionaries containing buff information.
		players (dict): A dictionary containing player information.
		damage_buff_ids (set): A set of buff IDs that should be checked for damage calculation.

	Returns:
		None
	"""

	for target in targets:
		if "buffs" in target:
			for buff in target["buffs"]:
				if buff['id'] in damage_buff_ids:
					for player, phases in buff['statsPerSource'].items():
						buff_start_time = None
						total_damage = 0
						for phase in phases:
							if phase[1] != 0 and buff_start_time is None:
								buff_start_time = phase[0]
							elif phase[1] == 0 and buff_start_time is not None:
								buff_end_time = phase[0]
								damage, name_prof = calculate_damage_during_buff(players, target, player, buff_start_time, buff_end_time)
								total_damage += damage
								buff_start_time = None
						if total_damage > 0:
							if name_prof not in debuff_damage:
								debuff_damage[name_prof] = {}
							debuff_damage[name_prof][buff['id']] = debuff_damage[name_prof].get(buff['id'], 0) + total_damage

def update_high_score(stat_name: str, key: str, value: float) -> None:
	"""
	Update the high scores dictionary with a new value if it is higher than the current lowest value.

	Args:
		stat_name (str): The name of the stat to update.
		key (str): The key to store the value under.
		value (float): The value to store.
	"""

	if stat_name not in high_scores:
		high_scores[stat_name] = {}

	if key in high_scores[stat_name]:
		if value > high_scores[stat_name][key]:
			high_scores[stat_name][key] = value
	elif len(high_scores[stat_name]) < 5:
		high_scores[stat_name][key] = value
	else:
		lowest_key = min(high_scores[stat_name], key=high_scores[stat_name].get)
		lowest_value = high_scores[stat_name][lowest_key]
		if value > lowest_value:
			del high_scores[stat_name][lowest_key]
			high_scores[stat_name][key] = value


def determine_player_role(player_data: dict) -> str:
	"""
	Determine the role of a player in combat based on their stats.

	Args:
		player_data (dict): The player data.

	Returns:
		str: The role of the player.
	"""
	crit_rate = player_data["statsAll"][0]["criticalRate"]
	total_dps = player_data["dpsAll"][0]["damage"]
	power_dps = player_data["dpsAll"][0]["powerDamage"]
	condi_dps = player_data["dpsAll"][0]["condiDamage"]
	if "extHealingStats" in player_data:
		total_healing = player_data["extHealingStats"]["outgoingHealing"][0]["healing"]
	else:
		total_healing = 0
	if "extBarrierStats" in player_data:
		total_barrier = player_data["extBarrierStats"]["outgoingBarrier"][0]["barrier"]
	else:
		total_barrier = 0

	if total_healing > total_dps:
		return "Support"
	if total_barrier > total_dps:
		return "Support"
	if condi_dps > power_dps:
		return "Condi"
	if crit_rate <= 40:
		return "Support"
	else:
		return "DPS"

def calculate_defensive_hits_and_glances(player_data):
	"""
	Calculate the number of direct and glancing hits taken by a player based on the total damage taken.

	Args:
		player_data (dict): The player data.

	Returns:
		tuple: The number of direct hits and glancing hits taken by the player as a tuple (direct_hits, glancing_hits).
	"""
	direct_hits = 0
	glancing_hits = 0
	for skill in player_data['totalDamageTaken'][0]:
		glancing_hits += skill['glance']
		if not skill['indirectDamage']:
			direct_hits += skill['hits']

	return direct_hits, glancing_hits

def get_commander_tag_data(fight_json):
	"""Extract commander tag data from the fight JSON."""
	
	commander_tag_positions = []
	earliest_death_time = fight_json['durationMS']
	has_died = False

	for player in fight_json["players"]:
		if player["hasCommanderTag"] and not player["notInSquad"]:
			commander_name = f"{player['name']}|{player['profession']}|{get_player_account(player)}"
			if commander_name not in commander_summary_data:
				commander_summary_data[commander_name] = {
					'heal_stats': {},
					'support': {},
					'statsAll': {},
					'defenses': {},
					'totalDamageTaken': {},
					'prot_mods': {
						'hitCount': 0,
						'totalHitCount': 0,
						'damageGain': 0,
						'totalDamage': 0
					}
				}
			replay_data = player.get("combatReplayData", {})
			commander_tag_positions = replay_data.get("positions", [])

			for death_time, _ in replay_data.get("dead", []):
				if death_time > 0:
					earliest_death_time = min(death_time, earliest_death_time)
					has_died = True
					break

	return commander_tag_positions, earliest_death_time, has_died

def get_player_death_on_tag(
    player,
    commander_tag_positions,
    dead_tag_mark,
    dead_tag,
    inch_to_pixel,
    polling_rate,
):
    """
    Calculate the distance to the commander tag for each player in the log,
    and store it in the death_on_tag dictionary.

    Args:
        player (dict): The player data.
        commander_tag_positions (list[tuple[float, float]]): Positions of the commander tag.
        dead_tag_mark (int): The mark at which the commander tag was last alive.
        dead_tag (bool): Whether the commander tag was dead.
        inch_to_pixel (float): Conversion factor between inches and pixels.
        polling_rate (int): The rate at which the combat log is polled.
    """

    # helpers
    def safe_position(positions, idx):
        """Return a valid position from positions with bounds checking."""
        if not positions:
            return (0, 0)
        if idx < len(positions):
            return positions[idx]
        elif idx - 1 < len(positions):
            return positions[idx - 1]
        return positions[-1]

    def avg_distance(positions, tag_positions, poll, inch_to_pixel):
        """Return average distance between player and tag up to poll index."""
        distances = [
            math.hypot(px - tx, py - ty)
            for (px, py), (tx, ty) in zip(positions[:poll], tag_positions[:poll])
        ]
        if not distances:
            return 0
        return round((sum(distances) / len(distances)) / inch_to_pixel)

    # Setup player entry
    name_prof = f"{player.get('name', 'Unknown')}|{player.get('profession', 'Unknown')}|{get_player_account(player)}"
    if name_prof not in death_on_tag:
        death_on_tag[name_prof] = {
            "name": player.get("name", ""),
            "profession": player.get("profession", ""),
            "account": get_player_account(player),
            "distToTag": [],
            "On_Tag": 0,
            "Off_Tag": 0,
            "Run_Back": 0,
            "After_Tag_Death": 0,
            "Total": 0,
            "Ranges": [],
        }
    entry = death_on_tag[name_prof]

    # Distance to commander (static)
    stats_all = player.get("statsAll", [{}])
    dist_to_com = stats_all[0].get("distToCom", "Infinity")
    player_dist_to_tag = 0 if dist_to_com == "Infinity" else round(dist_to_com)

    # Combat replay data
    combat_data = player.get("combatReplayData", {})
    if not combat_data or "positions" not in combat_data:
        return  # nothing to process

    player_positions = combat_data["positions"]
    player_deaths = dict(combat_data.get("dead", {}))
    player_downs = dict(combat_data.get("down", {}))
    player_offset = math.floor(combat_data.get("start", 0) / polling_rate)

    # Process deaths
    if player_deaths and player_downs and commander_tag_positions:
        for death_key, death_value in player_deaths.items():
            if death_key < 0:
                continue  # before squad combat log starts

            position_mark = max(0, math.floor(death_key / polling_rate)) - player_offset

            for down_key, down_value in player_downs.items():
    			
                if death_key != down_value:
                    continue

                # Player & Tag positions at death
                x1, y1 = safe_position(player_positions, position_mark)
                x2, y2 = safe_position(commander_tag_positions, position_mark)

                # Distance at death
                death_distance = math.hypot(x1 - x2, y1 - y2)
                death_range = round(death_distance / inch_to_pixel)
                entry["Total"] += 1

                # Average distance calculation
                if int(down_key) > int(dead_tag_mark) and dead_tag:
                    # After commander tag death
                    player_dead_poll = max(1, int(dead_tag_mark / polling_rate))
                    player_dist_to_tag = avg_distance(
                        player_positions, commander_tag_positions, player_dead_poll, inch_to_pixel
                    )
                    entry["After_Tag_Death"] += 1
                else:
                    # Before tag death
                    player_dead_poll = position_mark
                    player_dist_to_tag = avg_distance(
                        player_positions, commander_tag_positions, player_dead_poll, inch_to_pixel
                    )

                # Classification
                if death_range <= On_Tag:
                    entry["On_Tag"] += 1
                elif death_range <= Run_Back:
                    entry["Off_Tag"] += 1
                    entry["Ranges"].append(death_range)
                else:
                    entry["Run_Back"] += 1

    # Record distance
    if player_dist_to_tag <= Run_Back:
        entry["distToTag"].append(player_dist_to_tag)


def get_player_fight_dps(dpsTargets: dict, name: str, profession: str, account: str, fight_num: int, fight_time: int) -> None:
	"""
	Get the maximum damage hit by skill.

	Args:
		fight_data (dict): The fight data.

	"""
	target_damage = 0
	for target in dpsTargets:
		target_damage += target[0]["damage"]

	target_damage = round(target_damage / fight_time,2)

	update_high_score(
		"fight_dps",
		"{{"+profession+"}}"+name+"-"+str(account)+"-"+str(fight_num)+"-DPS",
		target_damage
		)

def get_combat_start_from_player_json(initial_time, player_json):
	"""
	Determine the start time of combat for a player based on health and damage changes.

	This function analyzes the player's health percentages and power damage over time to
	identify when combat began. It checks for the first instance of health reduction or 
	change in power damage to infer the start of combat.

	Args:
		initial_time (int): The initial timestamp to start checking from.
		player_json (dict): The player's JSON data containing 'healthPercents' and 'damage1S'.

	Returns:
		int: The timestamp representing the start of combat, or -1 if no combat is found.
	"""

	start_combat = -1
	if 'healthPercents' not in player_json:
		return start_combat 
	last_health_percent = 100
	for change in player_json['healthPercents']:
		if change[0] < initial_time:
			last_health_percent = change[1]
			continue
		if change[1] - last_health_percent < 0:
			# got dmg
			start_combat = change[0]
			break
		last_health_percent = change[1]
	for i in range(math.ceil(initial_time/1000), len(player_json['damage1S'][0])):
		if i == 0:
			continue
		if player_json['powerDamage1S'][0][i] != player_json['powerDamage1S'][0][i-1]:
			if start_combat == -1:
				start_combat = i*1000
			else:
				start_combat = min(start_combat, i*1000)
			break
	return start_combat

def get_combat_time_breakpoints(player_json):
	"""
	Calculate combat time breakpoints for a player based on their combat replay data.

	Args:
		player_json (dict): The player's JSON data.

	Returns:
		list: A list of [start, end] tuples representing combat time breakpoints.
	"""
	# Get the initial combat start time
	start_combat = get_combat_start_from_player_json(0, player_json)

	# Check if 'combatReplayData' is available, use 'activeTimes' if not
	if 'combatReplayData' not in player_json:
		print("WARNING: combatReplayData not in json, using activeTimes as time in combat")
		return [[start_combat, player_json.get('activeTimes', 0)]]

	replay = player_json['combatReplayData']

	# Check if 'dead' data is available in replay, use 'activeTimes' if not
	if 'dead' not in replay:
		return [[start_combat, player_json.get('activeTimes', 0)]]

	breakpoints = []
	player_deaths = dict(replay['dead'])
	player_downs = dict(replay['down'])

	# Iterate over player deaths and downs to calculate breakpoints
	for death_key, death_value in player_deaths.items():
		for down_key, down_value in player_downs.items():
			if death_key == down_value:
				if start_combat != -1:
					breakpoints.append([start_combat, death_key])
				start_combat = get_combat_start_from_player_json(death_value + 1000, player_json)
				break

	# Determine the end of combat based on damage data
	end_combat = len(player_json['damage1S'][0]) * 1000
	if start_combat != -1:
		breakpoints.append([start_combat, end_combat])

	return breakpoints

def sum_breakpoints(breakpoints):
	"""
	Calculate the total combat time from a list of combat breakpoints.

	Args:
		breakpoints (list): A list of [start, end] tuples representing combat time breakpoints

	Returns:
		int: The total combat time in milliseconds
	"""
	combat_time = 0
	for [start, end] in breakpoints:
		combat_time += end - start
	return combat_time

def split_boon_states(states, duration):
	"""
	Split boon states into individual start/end times and stack counts.

	Args:
		states (list): List of (start, stack_count) tuples
		duration (int): Duration of the fight in milliseconds

	Returns:
		list: List of (start, end, stack_count) tuples
	"""
	split_states = []
	num_states = len(states) - 1
	for index, (start, stacks) in enumerate(states):
		# If this is the last state, end at the duration
		if index == num_states:
			if start < duration:
				split_states.append([start, duration, stacks])
		else:
			# Otherwise, end at the next state's start time
			split_states.append([start, min(states[index + 1][0], duration), stacks])
	return split_states

def split_boon_states_by_combat_breakpoints(states, breakpoints, duration):
	"""
	Split boon states into individual start/end times and stack counts, split by combat breakpoints.

	Args:
		states (list): List of (start, stack_count) tuples
		breakpoints (list): List of [start, end] tuples representing combat time breakpoints
		duration (int): Duration of the fight in milliseconds

	Returns:
		list: List of (start, end, stack_count) tuples
	"""
	if not breakpoints:
		return []

	breakpoints_copy = breakpoints[:]
	split_states = split_boon_states(states, duration)
	new_states = []

	while(len(breakpoints_copy) > 0 and len(split_states) > 0):
		[combat_start, combat_end] = breakpoints_copy.pop(0)
		[start_state, end_state, stacks] = split_states.pop(0)

		while(end_state < combat_start):
			if len(split_states) == 0:
				break
			[start_state, end_state, stacks] = split_states.pop(0)

		if end_state < combat_start:
			break

		new_start = combat_start if combat_start > start_state else start_state
		new_end = combat_end if combat_end < end_state else end_state
		if new_end > new_start:
			new_states.append([new_start, new_end, stacks])

		while(len(split_states) > 0 and split_states[0][1] <= combat_end):
			[start_state, end_state, stacks] = split_states.pop(0)

			new_start = combat_start if combat_start > start_state else start_state
			new_end = combat_end if combat_end < end_state else end_state

			if new_end > new_start:
				new_states.append([
					combat_start if combat_start > start_state else start_state,
					combat_end if combat_end < end_state else end_state,
					stacks
				])

	return new_states

def get_stacking_uptime_data(player, damagePS, duration, fight_ticks, blacklist):
	"""
	Get uptime and damage data for stacking buffs like might and stability
	"""
	# Track Stacking Buff Uptimes
	boons = {
		'b740': "Might", 'b725': "Fury", 'b1187': "Quickness", 'b30328': "Alacrity", 
		'b717': "Protection", 'b718': "Regeneration", 'b726': "Vigor", 'b743': "Aegis",
		'b1122': "Stability", 'b719': "Swiftness", 'b26980': "Resistance", 'b873': "Resolution"
	}

	player_prof_name = f"{player['name']}|{player['profession']}|{get_player_account(player)}"
	if player["account"] in blacklist:
		return
	if player_prof_name not in stacking_uptime_Table:
		stacking_uptime_Table[player_prof_name] = {}
		stacking_uptime_Table[player_prof_name]["account"] = get_player_account(player)
		stacking_uptime_Table[player_prof_name]["name"] = player['name']
		stacking_uptime_Table[player_prof_name]["profession"] = player['profession']
		stacking_uptime_Table[player_prof_name]["duration_Might"] = 0
		stacking_uptime_Table[player_prof_name]["duration_Stability"] = 0
		stacking_uptime_Table[player_prof_name]["Might"] = [0] * 26
		stacking_uptime_Table[player_prof_name]["Stability"] = [0] * 26
		for buff_id in boons:
			buff_name = boons[buff_id]
			stacking_uptime_Table[player_prof_name]["damage_with_"+buff_name] = [0] * 26 if buff_name == 'Might' else [0] * 2
		
	player_damage = damagePS
	player_damage_per_tick = [player_damage[0]]
	for fight_tick in range(fight_ticks - 1):
		player_damage_per_tick.append(player_damage[fight_tick + 1] - player_damage[fight_tick])

	player_combat_breakpoints = get_combat_time_breakpoints(player)

	for item in player['buffUptimesActive']:
		buffId = "b"+str(item['id'])	
		if buffId not in boons:
			continue

		buff_name = boons[buffId]

		states = split_boon_states_by_combat_breakpoints(item['states'], player_combat_breakpoints, duration*1000)

		total_time = 0
		for idx, [state_start, state_end, stacks] in enumerate(states):
			if buff_name in ['Stability', 'Might']:
				uptime = state_end - state_start
				total_time += uptime
				stacking_uptime_Table[player_prof_name][buff_name][min(stacks, 25)] += uptime

			start_sec = state_start / 1000
			end_sec = state_end / 1000

			start_sec_int = int(start_sec)
			start_sec_rem = start_sec - start_sec_int

			end_sec_int = int(end_sec)
			end_sec_rem = end_sec - end_sec_int

			damage_with_stacks = 0
			if start_sec_int == end_sec_int:
				damage_with_stacks = player_damage_per_tick[start_sec_int] * (end_sec - start_sec)
			else:
				damage_with_stacks = player_damage_per_tick[start_sec_int] * (1.0 - start_sec_rem)
				damage_with_stacks += sum(player_damage_per_tick[start_sec_int + s] for s in range(1, end_sec_int - start_sec_int))
				damage_with_stacks += player_damage_per_tick[end_sec_int] * end_sec_rem

			if idx == 0:
				# Get any damage before we have boon states
				damage_with_stacks += player_damage_per_tick[start_sec_int] * (start_sec_rem)
				damage_with_stacks += sum(player_damage_per_tick[s] for s in range(0, start_sec_int))
			if idx == len(states) - 1:
				# leave this as if, not elif, since we can have 1 state which is both the first and last
				# Get any damage after we have boon states
				damage_with_stacks += player_damage_per_tick[end_sec_int] * (1.0 - end_sec_rem)
				damage_with_stacks += sum(player_damage_per_tick[s] for s in range(end_sec_int + 1, len(player_damage_per_tick)))
			elif len(states) > 1 and state_end != states[idx + 1][0]:
				# Get any damage between deaths, this is usually a small amount of condis that are still ticking after death
				next_state_start = states[idx + 1][0]
				next_state_sec = next_state_start / 1000
				next_start_sec_int = int(next_state_sec)
				next_start_sec_rem = next_state_sec - next_start_sec_int

				damage_with_stacks += player_damage_per_tick[end_sec_int] * (1.0 - end_sec_rem)
				damage_with_stacks += sum(player_damage_per_tick[s] for s in range(end_sec_int + 1, next_start_sec_int))
				damage_with_stacks += player_damage_per_tick[next_start_sec_int] * (next_start_sec_rem)

			if buff_name == 'Might':
				stacking_uptime_Table[player_prof_name]["damage_with_"+buff_name][min(stacks, 25)] += damage_with_stacks
			else:
				stacking_uptime_Table[player_prof_name]["damage_with_"+buff_name][min(stacks, 1)] += damage_with_stacks

		if buff_name in ['Stability', 'Might']:
			stacking_uptime_Table[player_prof_name]["duration_"+buff_name] += total_time

def calculate_dps_stats(fight_json, blacklist):
	"""
	Calculates the various DPS stats from the fight JSON.

	Does the following:

	* Calculates the total damage done by each player
	* Calculates the total damage done by the squad
	* Calculates the coordination damage, which is the damage done by each player weighted by the amount of time they are coordinated with the squad
	* Calculates the chunk damage, which is the damage done by each player within X seconds of a target dying
	* Calculates the carrion damage, which is the damage done to targets that die
	* Calculates the burst damage, which is the maximum damage done by each player in X seconds
	* Calculates the ch5Ca burst damage, which is the maximum damage done by each player in X seconds, but only counting damage done while Ch5Ca is active

	"""
	fight_ticks = len(fight_json['players'][0]["damage1S"][0])
	duration = round(fight_json['durationMS']/1000)

	damage_ps = {}
	for index, target in enumerate(fight_json['targets']):
		if 'enemyPlayer' in target:	#and target['enemyPlayer'] == True
			for player in fight_json['players']:
				if player['notInSquad']:
					continue
				player_prof_name = player['profession'] + " " + player['name'] + " " + get_player_account(player)
				if player_prof_name not in damage_ps:
					damage_ps[player_prof_name] = [0] * fight_ticks

				damage_on_target = player["targetDamage1S"][index][0]
				for i in range(fight_ticks):
					damage_ps[player_prof_name][i] += damage_on_target[i]

	squad_damage_per_tick = []
	for fight_tick in range(fight_ticks - 1):
		squad_damage_on_tick = 0
		for player in fight_json['players']:
			if player['notInSquad']:
				continue
			combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
			if combat_time:
				player_prof_name = player['profession'] + " " + player['name'] + " " + get_player_account(player)
				player_damage = damage_ps[player_prof_name]
				squad_damage_on_tick += player_damage[fight_tick + 1] - player_damage[fight_tick]
		squad_damage_per_tick.append(squad_damage_on_tick)

	squad_damage_total = sum(squad_damage_per_tick)
	squad_damage_per_tick_ma = calculate_moving_average(squad_damage_per_tick, 1)
	squad_damage_ma_total = sum(squad_damage_per_tick_ma)

	CHUNK_DAMAGE_SECONDS = 21
	ch5_ca_damage_1s = {}

	for player in fight_json['players']:
		if player['notInSquad']:
			continue
		if player['account'] in blacklist:
			continue
		player_prof_name = player['profession'] + " " + player['name']+ " " + get_player_account(player)
		combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
		if combat_time:
			if player_prof_name not in DPSStats:
				DPSStats[player_prof_name] = {
					"account": get_player_account(player),
					"name": player["name"],
					"profession": player["profession"],
					"duration": 0,
					"combatTime": 0,
					"coordinationDamage": 0,
					"chunkDamage": [0] * CHUNK_DAMAGE_SECONDS,
					"chunkDamageTotal": [0] * CHUNK_DAMAGE_SECONDS,
					"carrionDamage": 0,
					"carrionDamageTotal": 0,
					"damageTotal": 0,
					"squadDamageTotal": 0,
					"burstDamage": [0] * CHUNK_DAMAGE_SECONDS,
					"ch5CaBurstDamage": [0] * CHUNK_DAMAGE_SECONDS,
					"downs": 0,
					"kills": 0,
				}
				
			ch5_ca_damage_1s[player_prof_name] = [0] * fight_ticks
				
			player_damage = damage_ps[player_prof_name]
			
			DPSStats[player_prof_name]["duration"] += duration
			DPSStats[player_prof_name]["combatTime"] += combat_time
			DPSStats[player_prof_name]["damageTotal"] += player_damage[fight_ticks - 1]
			DPSStats[player_prof_name]["squadDamageTotal"] += squad_damage_total

			for stats_target in player["statsTargets"]:
				DPSStats[player_prof_name]["downs"] += stats_target[0]['downed']
				DPSStats[player_prof_name]["kills"] += stats_target[0]['killed']

			# Coordination_Damage: Damage weighted by coordination with squad
			player_damage_per_tick = [player_damage[0]]
			for fight_tick in range(fight_ticks - 1):
				player_damage_per_tick.append(player_damage[fight_tick + 1] - player_damage[fight_tick])

			player_damage_ma = calculate_moving_average(player_damage_per_tick, 1)

			for fight_tick in range(fight_ticks - 1):
				player_damage_on_tick = player_damage_ma[fight_tick]
				if player_damage_on_tick == 0:
					continue

				squad_damage_on_tick = squad_damage_per_tick_ma[fight_tick]
				if squad_damage_on_tick == 0:
					continue

				squad_damage_percent = squad_damage_on_tick / squad_damage_ma_total

				DPSStats[player_prof_name]["coordinationDamage"] += player_damage_on_tick * squad_damage_percent * duration
			
			get_stacking_uptime_data(player, player_damage, duration, fight_ticks, blacklist)

	# Chunk damage: Damage done within X seconds of target down
	for index, target in enumerate(fight_json['targets']):
		if 'enemyPlayer' in target and target['enemyPlayer'] == True and 'combatReplayData' in target and len(target['combatReplayData']['down']):
			for chunk_damage_seconds in range(1, CHUNK_DAMAGE_SECONDS):
				targetDowns = dict(target['combatReplayData']['down'])
				for targetDownsIndex, (downKey, downValue) in enumerate(targetDowns.items()):
					downIndex = math.floor(downKey / 1000)
					startIndex = max(0, downIndex - chunk_damage_seconds)
					if targetDownsIndex > 0:
						lastDownKey, lastDownValue = list(targetDowns.items())[targetDownsIndex - 1]
						lastDownIndex = math.floor(lastDownKey / 1000)
						if lastDownIndex == downIndex:
							# Probably an ele in mist form
							continue
						startIndex = max(startIndex, lastDownIndex)

					squad_damage_on_target = 0
					for player in fight_json['players']:
						if player['notInSquad']:
							continue
						if player['account'] in blacklist:
							continue
						combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
						if combat_time:
							player_prof_name = player['profession'] + " " + player['name'] + " " + get_player_account(player)	
							damage_on_target = player["targetDamage1S"][index][0]
							player_damage = damage_on_target[downIndex] - damage_on_target[startIndex]
							#player_damage = player["targetDamage1S"][downIndex][0] - player["targetDamage1S"][startIndex][0]

							DPSStats[player_prof_name]["chunkDamage"][chunk_damage_seconds] += player_damage
							squad_damage_on_target += player_damage

							if chunk_damage_seconds == 5:
								for i in range(startIndex, downIndex):
									ch5_ca_damage_1s[player_prof_name][i] += damage_on_target[i + 1] - damage_on_target[i]

					for player in fight_json['players']:
						if player['notInSquad']:
							continue
						if player['account'] in blacklist:
							continue
						combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
						if combat_time:
							player_prof_name = player['profession'] + " " + player['name'] + " " + get_player_account(player)

							DPSStats[player_prof_name]["chunkDamageTotal"][chunk_damage_seconds] += squad_damage_on_target

	# Carrion damage: damage to downs that die 
	for index, target in enumerate(fight_json['targets']):
		if 'enemyPlayer' in target and target['enemyPlayer'] == True and 'combatReplayData' in target and len(target['combatReplayData']['dead']):
			targetDeaths = dict(target['combatReplayData']['dead'])
			targetDowns = dict(target['combatReplayData']['down'])
			for deathKey, deathValue in targetDeaths.items():
				for downKey, downValue in targetDowns.items():
					if deathKey == downValue:
						dmgEnd = math.ceil(deathKey / 1000)
						dmgStart = math.ceil(downKey / 1000)

						total_carrion_damage = 0
						for player in fight_json['players']:
							if player['notInSquad']:
								continue
							if player['account'] in blacklist:
								continue
							combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
							if combat_time:
								player_prof_name = player['profession'] + " " + player['name'] + " " + get_player_account(player)
								damage_on_target = player["targetDamage1S"][index][0]
								carrion_damage = damage_on_target[dmgEnd] - damage_on_target[dmgStart]

								DPSStats[player_prof_name]["carrionDamage"] += carrion_damage
								total_carrion_damage += carrion_damage

								for i in range(dmgStart, dmgEnd):
									ch5_ca_damage_1s[player_prof_name][i] += damage_on_target[i + 1] - damage_on_target[i]

						for player in fight_json['players']:
							if player['notInSquad']:
								continue
							if player['account'] in blacklist:
								continue
							combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
							if combat_time:
								player_prof_name = player['profession'] + " " + player['name'] + " " + get_player_account(player)
								DPSStats[player_prof_name]["carrionDamageTotal"] += total_carrion_damage

	# Burst damage: max damage done in n seconds
	for player in fight_json['players']:
		if player['notInSquad']:
			continue
		if player['account'] in blacklist:
			continue
		combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
		if combat_time:
			player_prof_name = player['profession'] + " " + player['name'] + " " + get_player_account(player)
			player_damage = damage_ps[player_prof_name]
			for i in range(1, CHUNK_DAMAGE_SECONDS):
				for fight_tick in range(i, fight_ticks):
					dmg = player_damage[fight_tick] - player_damage[fight_tick - i]
					DPSStats[player_prof_name]["burstDamage"][i] = max(dmg, DPSStats[player_prof_name]["burstDamage"][i])

	# Ch5Ca Burst damage: max damage done in n seconds
	for player in fight_json['players']:
		if player['notInSquad']:
			continue
		if player['account'] in blacklist:
			continue
		combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
		if combat_time:
			player_prof_name = player['profession'] + " " + player['name'] + " " + get_player_account(player)
			player_damage_ps = ch5_ca_damage_1s[player_prof_name]
			player_damage = [0] * len(player_damage_ps)
			player_damage[0] = player_damage_ps[0]
			for i in range(1, len(player_damage)):
				player_damage[i] = player_damage[i - 1] + player_damage_ps[i]
			for i in range(1, CHUNK_DAMAGE_SECONDS):
				for fight_tick in range(i, fight_ticks):
					dmg = player_damage[fight_tick] - player_damage[fight_tick - i]
					DPSStats[player_prof_name]["ch5CaBurstDamage"][i] = max(dmg, DPSStats[player_prof_name]["ch5CaBurstDamage"][i])

def get_player_stats_targets(statsTargets: dict, name: str, profession: str, account: str, fight_num: int, fight_time: int) -> None:
	"""
	Gets the stats for a player in a fight for a given stat

	Args:
		statsTargets (dict): A dictionary of stats for the player
		name (str): The name of the player
		profession (str): The profession of the player
		account (str): The account of the player
		fight_num (int): The number of the fight
		fight_time (int): The length of the fight

	Returns:
		None
	"""
	fight_stats = ["killed", "downed", "downContribution", "appliedCrowdControl"]
	for stat in fight_stats:
		fight_stat_value= 0
		for target in statsTargets:
			if target[0] and stat in target[0]:
				fight_stat_value += target[0][stat]

		fight_stat_value = round(fight_stat_value / fight_time, 3)

		update_high_score(f"statTarget_{stat}", "{{"+profession+"}}"+name+"-"+str(account)+"-"+str(fight_num)+"-"+stat, fight_stat_value)	

def get_total_shield_damage(fight_data: dict) -> int:
	"""
	Extract the total shield damage from the fight data.

	Args:
		fight_data (dict): The fight data.

	Returns:
		int: The total shield damage.
	"""
	total_shield_damage = 0
	for skill in fight_data["targetDamageDist"]:
		total_shield_damage += skill["shieldDamage"]
	return total_shield_damage

def get_buffs_data(buff_map: dict) -> None:
	"""
	Collect buff data across all fights.

	Args:
		buff_map (dict): The dictionary of buff data.
	"""
	for buff in buff_map:
		buff_id = buff
		name = buff_map[buff]['name']
		stacking = buff_map[buff]['stacking']
		icon = buff_map[buff].get('icon', 'unknown.png')
		classification = buff_map[buff].get('classification', 'unknown')
		if buff_id not in buff_data:
			buff_data[buff_id] = {
				'name': name,
				'stacking': stacking,
				'icon': icon,
				'classification': classification
			}
		elif buff_data[buff_id]['icon'] in ("https://render.guildwars2.com/file/1D55D34FB4EE20B1962E315245E40CA5E1042D0E/62248.png", "unknown.png"):
			if icon not in ("https://render.guildwars2.com/file/1D55D34FB4EE20B1962E315245E40CA5E1042D0E/62248.png", "unknown.png"):
				buff_data[buff_id]['icon'] = icon

				
def get_skills_data(skill_map: dict) -> None:
	"""
	Collect skill data across all fights.

	Args:
		skill_map (dict): The dictionary of skill data.
	"""
	for skill in skill_map:
		skill_id = skill
		name = skill_map[skill]['name']
		auto_attack = skill_map[skill]['autoAttack']
		icon = skill_map[skill].get('icon', 'unknown.png')
		if skill_id not in skill_data:
			skill_data[skill_id] = {
				'name': name,
				'auto': auto_attack,
				'icon': icon
			}
		elif skill_data[skill_id]['icon'] in ("https://render.guildwars2.com/file/1D55D34FB4EE20B1962E315245E40CA5E1042D0E/62248.png", "unknown.png"):
			if icon not in ("https://render.guildwars2.com/file/1D55D34FB4EE20B1962E315245E40CA5E1042D0E/62248.png", "unknown.png"):
				skill_data[skill_id]['icon'] = icon

def get_damage_mods_data(damage_mod_map: dict, personal_damage_mod_data: dict) -> None:
	"""
	Collect damage mod data across all fights.

	Args:
		damage_mod_map (dict): The dictionary of damage mod data.
	"""
	for mod in damage_mod_map:
		name = damage_mod_map[mod]['name']
		icon = damage_mod_map[mod]['icon']
		if 'incoming' in damage_mod_map[mod]:
			incoming = damage_mod_map[mod]['incoming']
		else:
			incoming = False
		shared = False
		if mod in personal_damage_mod_data['total']:
			shared = False

		else:
			shared = True

		if mod not in damage_mod_data:
			damage_mod_data[mod] = {
				'name': name,
				'icon': icon,
				'shared': shared,
				'incoming': incoming
			}

def get_personal_mod_data(personal_damage_mods: dict) -> None:
	"""
	Populate the personal_damage_mod_data dictionary with modifiers from personal_damage_mods.

	Args:
		personal_damage_mods (dict): A dictionary where keys are professions and values are lists of modifier IDs.
	"""
	for profession, mods in personal_damage_mods.items():
		if profession not in personal_damage_mod_data:
			personal_damage_mod_data[profession] = []
		for mod_id in mods:
			mod_id = "d" + str(mod_id)
			if mod_id not in personal_damage_mod_data[profession]:
				personal_damage_mod_data[profession].append(mod_id)
				personal_damage_mod_data['total'].append(mod_id)

def get_personal_buff_data(personal_buffs: dict) -> None:
	"""
	Populate the global personal_buff_data dictionary with buffs from personal_buffs.

	- Buff IDs are normalized into the format 'b<ID>'.
	- Each profession gets its own list of buffs.
	- A special 'total' list contains all unique buffs across professions.

	Args:
		personal_buffs (dict): Keys are professions, values are lists of buff IDs.
	"""
	if "total" not in personal_buff_data:
		personal_buff_data["total"] = []

	for profession, buffs in personal_buffs.items():
		if profession not in personal_buff_data:
			personal_buff_data[profession] = []

		for buff_id in buffs:
			normalized = f"b{buff_id}"

			# Add to profession if not already present
			if normalized not in personal_buff_data[profession]:
				personal_buff_data[profession].append(normalized)

			# Add to total if not already present
			if normalized not in personal_buff_data["total"]:
				personal_buff_data["total"].append(normalized)

def get_enemies_by_fight(fight_num: int, targets: dict) -> None:
	"""
	Organize targets by enemy for a fight.

	Args:
		fight_num (int): The number of the fight.
		targets (list): The list of targets in the fight.
	"""
	if fight_num not in top_stats["fight"]:
		top_stats["fight"][fight_num] = {}

	if fight_num not in top_stats["enemies_by_fight"]:
		top_stats["enemies_by_fight"][fight_num] = {}

	for target in targets:
		if target["isFake"]:
			continue

		if target['enemyPlayer']:
			team = target["teamID"]
			enemy_prof = target['name'].split(" ")[0]

			if team in team_colors:
				colorTeam = team_colors[team]
				team = "enemy_" + team_colors[team]
			else:
				colorTeam = "Unk"
				if team not in team_code_missing:
					team_code_missing.append(team)
				team = "enemy_Unk"
			
			if team not in top_stats["fight"][fight_num]:
				# Create a new team if it doesn't exist
				top_stats["fight"][fight_num][team] = 0
			if colorTeam not in top_stats["enemies_by_fight"][fight_num]:
				top_stats["enemies_by_fight"][fight_num][colorTeam] = {}

			if enemy_prof not in top_stats["enemies_by_fight"][fight_num][colorTeam]:
				top_stats["enemies_by_fight"][fight_num][colorTeam][enemy_prof] = 0

			top_stats["enemies_by_fight"][fight_num][colorTeam][enemy_prof] += 1

			top_stats["fight"][fight_num][team] += 1

		top_stats["fight"][fight_num]["enemy_count"] += 1
		top_stats['overall']['enemy_count'] = top_stats['overall'].get('enemy_count', 0) + 1

def get_enemy_downed_and_killed_by_fight(fight_num: int, targets: dict, players: dict, log_type: str) -> None:
	"""
	Count enemy downed and killed for a fight.

	Args:
		fight_num (int): The number of the fight.
		targets (list): The list of targets in the fight.
	"""
	enemy_downed = 0
	enemy_killed = 0

	if fight_num not in top_stats["fight"]:
		top_stats["fight"][fight_num] = {}

	if log_type == "WVW":  # WVW doesn't have target[defense] data, must be "Detailed WvW" or "PVE"
		for target in targets:
			if target["isFake"]:
				continue

			if target['defenses'][0]['downCount']:
				enemy_downed += target['defenses'][0]['downCount']
			if target['defenses'][0]['deadCount']:
				enemy_killed += target['defenses'][0]['deadCount']
	else:
			for player in players:
				enemy_downed += sum(enemy[0]['downed'] for enemy in player['statsTargets'])
				enemy_killed += sum(enemy[0]['killed'] for enemy in player['statsTargets'])
	
	top_stats["fight"][fight_num]["enemy_downed"] = enemy_downed
	top_stats["fight"][fight_num]["enemy_killed"] = enemy_killed
	top_stats['overall']['enemy_downed'] = top_stats['overall'].get('enemy_downed', 0) + enemy_downed
	top_stats['overall']['enemy_killed'] = top_stats['overall'].get('enemy_killed', 0) + enemy_killed

def get_parties_by_fight(fight_num: int, players: list, blacklist: list) -> None:
	"""
	Organize players by party for a fight.

	Args:
		fight_num (int): The number of the fight.
		players (list): The list of players in the fight.
	"""
	if fight_num not in top_stats["parties_by_fight"]:
		top_stats["parties_by_fight"][fight_num] = {}

	for player in players:
		if player["account"] in blacklist:
			continue
		if player["notInSquad"]:
			# Count players not in a squad
			top_stats["fight"][fight_num]["non_squad_count"] += 1
			continue
		top_stats["fight"][fight_num]["squad_count"] += 1
		group = player["group"]
		name = player["name"]
		profession = player["profession"]
		prof_name = profession+"|"+name
		if group not in top_stats["parties_by_fight"][fight_num]:
			# Create a new group if it doesn't exist
			top_stats["parties_by_fight"][fight_num][group] = []
		if prof_name not in top_stats["parties_by_fight"][fight_num][group]:
			# Add the player to the group
			top_stats["parties_by_fight"][fight_num][group].append(prof_name)

def get_stat_by_key(fight_num: int, player: dict, stat_category: str, name_prof: str) -> None:
	"""
	Add player stats by key to top_stats dictionary

	Args:
		filename (str): The filename of the fight.
		player (dict): The player dictionary.
		stat_category (str): The category of stats to collect.
		name_prof (str): The name of the profession.
	"""
	player_stats = player[stat_category][0]
	active_time_seconds = player['activeTimes'][0] / 1000 if player['activeTimes'] else 0

	for stat, value in player_stats.items():
		if stat in ['boonStripsTime', 'condiCleanseTime', 'condiCleanseTimeSelf'] and value > 999999:
			value = 0
		if stat in ['distToCom', 'stackDist'] and value == "Infinity":
			print(f"Invalid stat: {stat} with value: {value} for player: {player['name']}. The log for fight {fight_num} needs review.")
			value = 0
		if stat in config.high_scores:
			high_score_value = round(value / active_time_seconds, 3) if active_time_seconds > 0 else 0
			update_high_score(
				f"{stat_category}_{stat}",
				f"{{{{{player['profession']}}}}}{player['name']}-{get_player_account(player)}-{str(fight_num)} | {stat}",
				high_score_value
			)
		top_stats['player'][name_prof][stat_category][stat] = top_stats['player'][name_prof][stat_category].get(stat, 0) + value
		stats_per_fight[stat_category][stat][name_prof].append(value)
		top_stats['fight'][fight_num][stat_category][stat] = top_stats['fight'][fight_num][stat_category].get(stat, 0) + value
		top_stats['overall'][stat_category][stat] = top_stats['overall'][stat_category].get(stat, 0) + value

		if player.get('hasCommanderTag'):
			commander_name = f"{player['name']}|{player['profession']}|{get_player_account(player)}"
			if commander_name not in commander_summary_data:
				commander_summary_data[commander_name] = {stat_category: {}}
			elif stat_category not in commander_summary_data[commander_name]:
				commander_summary_data[commander_name][stat_category] = {}
			commander_summary_data[commander_name][stat_category][stat] = commander_summary_data[commander_name][stat_category].get(stat, 0) + value

def get_defense_hits_and_glances(fight_num: int, player: dict, stat_category: str, name_prof: str) -> None:
	"""
	Add defensive hits and glances to top_stats dictionary

	Args:
		fight_num (int): The number of the fight.
		player (dict): The player dictionary.
		stat_category (str): The category of stats to collect.
		name_prof (str): The name of the profession.
	"""
	direct_hits, glancing_hits = calculate_defensive_hits_and_glances(player)
	top_stats['player'][name_prof][stat_category]['directHits'] = top_stats['player'][name_prof][stat_category].get('directHits', 0) + direct_hits
	top_stats['player'][name_prof][stat_category]['glanceCount'] = top_stats['player'][name_prof][stat_category].get('glanceCount', 0) + glancing_hits	
	top_stats['fight'][fight_num][stat_category]['directHits'] = top_stats['fight'][fight_num][stat_category].get('directHits', 0) + direct_hits
	top_stats['fight'][fight_num][stat_category]['glanceCount'] = top_stats['fight'][fight_num][stat_category].get('glanceCount', 0) + glancing_hits
	top_stats['overall'][stat_category]['directHits'] = top_stats['overall'][stat_category].get('directHits', 0) + direct_hits
	top_stats['overall'][stat_category]['glanceCount'] = top_stats['overall'][stat_category].get('glanceCount', 0) + glancing_hits

def get_stat_by_target_and_skill(fight_num: int, player: dict, stat_category: str, name_prof: str) -> None:
	"""
	Add player stats by target and skill to top_stats dictionary

	Args:
		filename (str): The filename of the fight.
		player (dict): The player dictionary.
		stat_category (str): The category of stats to collect.
		name_prof (str): The name of the profession.
	"""
	for index, target in enumerate(player[stat_category]):
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
					if stat == 'max':
						update_high_score(f"statTarget_{stat}", "{{"+player["profession"]+"}}"+player["name"]+"-"+get_player_account(player)+"-"+str(fight_num)+"-"+str(index)+" | "+str(skill_id), value)
						if value > top_stats['player'][name_prof][stat_category][skill_id].get(stat, 0):
							top_stats['player'][name_prof][stat_category][skill_id][stat] = value
							top_stats['fight'][fight_num][stat_category][skill_id][stat] = value
							top_stats['overall'][stat_category][skill_id][stat] = value
					elif stat == 'min':
						if value <= top_stats['player'][name_prof][stat_category][skill_id].get(stat, 0):
							top_stats['player'][name_prof][stat_category][skill_id][stat] = value
							top_stats['fight'][fight_num][stat_category][skill_id][stat] = value
							top_stats['overall'][stat_category][skill_id][stat] = value
					elif stat not in ['id', 'max', 'min']:
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
	Add player stats by skill to top_stats dictionary.

	Args:
		fight_num (int): The fight number.
		player (dict): The player dictionary.
		stat_category (str): The category of stats to collect.
		name_prof (str): The name of the profession.
	"""

	# Defensive guard: skip if no data for this category
	if stat_category not in player or not player[stat_category]:
		return

	for skill in player[stat_category][0]:
		if not skill or "id" not in skill:
			continue

		skill_id = skill["id"]

		# Ensure dict structure exists
		for level in ("player", "fight", "overall"):
			if level == "player":
				container = top_stats[level][name_prof][stat_category]
			elif level == "fight":
				container = top_stats[level][fight_num][stat_category]
			else:  # "overall"
				container = top_stats[level][stat_category]

			if skill_id not in container:
				container[skill_id] = {}

		# Process each stat for this skill
		for stat, value in skill.items():
			if stat == "id":
				continue

			# Update high score tracking
			if stat == "max":
				update_high_score(
					f"{stat_category}_{stat}",
					f"{{{{{player['profession']}}}}}{player['name']}-{get_player_account(player)}-{fight_num} | {skill_id}",
					value,
				)

			# Aggregate into top_stats
			top_stats["player"][name_prof][stat_category][skill_id][stat] = (
				top_stats["player"][name_prof][stat_category][skill_id].get(stat, 0) + value
			)
			top_stats["fight"][fight_num][stat_category][skill_id][stat] = (
				top_stats["fight"][fight_num][stat_category][skill_id].get(stat, 0) + value
			)
			top_stats["overall"][stat_category][skill_id][stat] = (
				top_stats["overall"][stat_category][skill_id].get(stat, 0) + value
			)

			# Commander-specific summary
			if player.get("hasCommanderTag"):
				commander_name = f"{player['name']}|{player['profession']}|{get_player_account(player)}"
				if skill_id not in commander_summary_data[commander_name][stat_category]:
					commander_summary_data[commander_name][stat_category][skill_id] = {}

				commander_summary_data[commander_name][stat_category][skill_id][stat] = (
					commander_summary_data[commander_name][stat_category][skill_id].get(stat, 0) + value
				) 

def get_buff_uptimes(fight_num: int, player: dict, group: str, stat_category: str, name_prof: str, fight_duration: int, active_time: int) -> None:
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
	ResistanceBuff = [26980, 'b26980']
	resist_data = {}
	for buff in player[stat_category]:
		buff_id = 'b'+str(buff['id'])
		if buff_id in ResistanceBuff:
			resist_state = buff['states']
			resist_data = get_buff_states(resist_state)
			break

	for buff in player[stat_category]:
		buff_id = 'b'+str(buff['id'])
		buff_uptime_ms = buff['buffData'][0]['uptime'] * fight_duration / 100
		buff_presence = buff['buffData'][0]['presence']
		state_changes = len(buff['states'])//2
		buff_state = buff['states']
		state_data = get_buff_states(buff_state)

		if buff_id not in top_stats['player'][name_prof][stat_category]:
			top_stats['player'][name_prof][stat_category][buff_id] = {}
		if buff_id not in top_stats['fight'][fight_num][stat_category]:
			top_stats['fight'][fight_num][stat_category][buff_id] = {}
		if buff_id not in top_stats['overall'][stat_category]:
			top_stats['overall'][stat_category][buff_id] = {}
		if "group" not in top_stats['overall'][stat_category]:
			top_stats['overall'][stat_category]["group"] = {}
		if group not in top_stats['overall'][stat_category]["group"]:
			top_stats['overall'][stat_category]["group"][group] = {}
		if buff_id not in top_stats['overall'][stat_category]["group"][group]:
			top_stats['overall'][stat_category]["group"][group][buff_id] = {}

		if stat_category == 'buffUptimes':
			stat_value = buff_presence * fight_duration / 100 if buff_presence else buff_uptime_ms
		elif stat_category == 'buffUptimesActive':
			stat_value = buff_presence * active_time / 100 if buff_presence else buff_uptime_ms

		non_damaging_conditions = [
			'b720', #'Blinded'
			'b721', #'Crippled' 
			'b722', #'Chilled' 
			'b727', #'Immobile' 
			'b742', #'Weakness' 
			'b791', #'Fear' 
			'b26766', #'Slow' 
			'b27705', #'Taunt'
		]
		resist_offset = 0
		if buff_id in non_damaging_conditions and resist_data:
			resist_offset += calculate_resist_offset(resist_data, state_data)

		top_stats['player'][name_prof][stat_category][buff_id]['uptime_ms'] = top_stats['player'][name_prof][stat_category][buff_id].get('uptime_ms', 0) + stat_value
		top_stats['player'][name_prof][stat_category][buff_id]['state_changes'] = top_stats['player'][name_prof][stat_category][buff_id].get('state_changes', 0) + state_changes
		top_stats['fight'][fight_num][stat_category][buff_id]['uptime_ms'] = top_stats['fight'][fight_num][stat_category][buff_id].get('uptime_ms', 0) + stat_value
		top_stats['overall'][stat_category][buff_id]['uptime_ms'] = top_stats['overall'][stat_category][buff_id].get('uptime_ms', 0) + stat_value
		top_stats['overall'][stat_category]["group"][group][buff_id]['uptime_ms'] = top_stats['overall'][stat_category]["group"][group][buff_id].get('uptime_ms', 0) + stat_value
		top_stats['player'][name_prof][stat_category][buff_id]['resist_reduction'] = top_stats['player'][name_prof][stat_category][buff_id].get('resist_reduction', 0) + resist_offset
		top_stats['fight'][fight_num][stat_category][buff_id]['resist_reduction'] = top_stats['fight'][fight_num][stat_category][buff_id].get('resist_reduction', 0) + resist_offset
		top_stats['overall'][stat_category][buff_id]['resist_reduction'] = top_stats['overall'][stat_category][buff_id].get('resist_reduction', 0) + resist_offset
		top_stats['overall'][stat_category]["group"][group][buff_id]['resist_reduction'] = top_stats['overall'][stat_category]["group"][group][buff_id].get('resist_reduction', 0) + resist_offset

def get_target_buff_data(fight_num: int, player: dict, targets: dict, stat_category: str, name_prof: str) -> None:
	"""
	Calculate buff uptime stats for a target caused by squad player

	Args:
		filename (str): The filename of the fight.
		player (dict): The player dictionary.
		targets (dict): The targets dictionary.
		stat_category (str): The category of stats to collect.
		name_prof (str): The name of the profession.
		fight_duration (int): The duration of the fight in milliseconds.

	Returns:
		None
	"""
	x =  {"b70350": 0.10, "b70806": 0.10}
	debuff_data = {
		"b70350": [0.10,'targetDamage1S'], #Dragonhunter Relic
		"b70806": [0.10,'targetPowerDamage1S'] #Isgarren Relic
	}
	target_idx = 0
	for target in targets:
		if 'buffs' in target:
			for buff in target['buffs']:
				buff_id = 'b'+str(buff['id'])

				if player['name'] in buff['statesPerSource']:
					name = player['name']
					buffTime = 0
					buffOn = 0
					firstTime = 0
					conditionTime = 0
					appliedCounts = 0
					damage_with_buff = 0
					for stateChange in buff['statesPerSource'][name]:
						if stateChange[0] == 0:
							continue
						elif stateChange[1] >=1 and buffOn == 0:
							if stateChange[1] > buffOn:
								appliedCounts += 1
							buffOn = stateChange[1]
							firstTime = stateChange[0]

						elif stateChange[1] == 0 and buffOn:
							buffOn = 0
							secondTime = stateChange[0]
							buffTime = secondTime - firstTime
							if buff_id in debuff_data:
								damage_with_buff = calculate_damage_during_buff(player, target_idx, firstTime, secondTime, debuff_data[buff_id][1])
					conditionTime += buffTime

					#if buff_id not in top_stats['player'][name_prof][stat_category]:
					if buff_id not in top_stats['player'][name_prof][stat_category]:
						top_stats['player'][name_prof][stat_category][buff_id] = {
							'uptime_ms': 0,
							'applied_counts': 0,
						}
						if buff_id in debuff_data:
							top_stats['player'][name_prof][stat_category][buff_id]['damage_gained'] = 0
					if buff_id not in top_stats['fight'][fight_num][stat_category]:
						top_stats['fight'][fight_num][stat_category][buff_id] = {
							'uptime_ms': 0,
							'applied_counts': 0,
						}
					if buff_id not in top_stats['overall'][stat_category]:
						top_stats['overall'][stat_category][buff_id] = {
							'uptime_ms': 0,
							'applied_counts': 0,
						}

					top_stats['player'][name_prof][stat_category][buff_id]['uptime_ms'] += conditionTime
					top_stats['player'][name_prof][stat_category][buff_id]['applied_counts'] += appliedCounts
					if buff_id in debuff_data:
						top_stats['player'][name_prof][stat_category][buff_id]['damage_gained'] += damage_with_buff * debuff_data[buff_id][0]

					top_stats['fight'][fight_num][stat_category][buff_id]['uptime_ms'] += conditionTime
					top_stats['fight'][fight_num][stat_category][buff_id]['applied_counts'] += appliedCounts

					top_stats['overall'][stat_category][buff_id]['uptime_ms'] += conditionTime
					top_stats['overall'][stat_category][buff_id]['applied_counts'] += appliedCounts

		target_idx += 1

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
		buff_id = 'b'+str(buff['id'])
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
		stats_per_fight[stat_category][buff_id][name_prof].append(buff_generation)
		top_stats['fight'][fight_num][stat_category][buff_id]['generation'] = top_stats['fight'][fight_num][stat_category][buff_id].get('generation', 0) + buff_generation
		top_stats['fight'][fight_num][stat_category][buff_id]['wasted'] = top_stats['fight'][fight_num][stat_category][buff_id].get('wasted', 0) + buff_wasted

		top_stats['overall'][stat_category][buff_id]['generation'] = top_stats['overall'][stat_category][buff_id].get('generation', 0) + buff_generation
		top_stats['overall'][stat_category][buff_id]['wasted'] = top_stats['overall'][stat_category][buff_id].get('wasted', 0) + buff_wasted

def get_skill_cast_by_prof_role(active_time, player: dict, stat_category: str, name_prof: str) -> None:
	"""
	Add player skill casts by profession and role to top_stats dictionary

	Args:
		'active_time' (int): player active time in milliseconds.
		player (dict): The player dictionary.
		stat_category (str): The category of stats to collect.
		name_prof (str): The name of the profession.
	"""

	profession = player['profession']
	role = determine_player_role(player)
	prof_role = f"{profession}-{role}"
	active_time /= 1000
	
	if 'skill_casts_by_role' not in top_stats:
		top_stats['skill_casts_by_role'] = {}

	if profession not in top_stats['skill_casts_by_role']:
		top_stats['skill_casts_by_role'][profession] = {
			'total': {}
		}

	if name_prof not in top_stats['skill_casts_by_role'][profession]:
		top_stats['skill_casts_by_role'][profession][name_prof] = {
			'ActiveTime': 0,
			'total': 0,
			'total_no_auto': 0,
			'account': get_player_account(player),
			'Skills': {}
		}

	top_stats['skill_casts_by_role'][profession][name_prof]['ActiveTime'] += active_time

	for skill in player[stat_category]:
		skill_id = 's'+str(skill['id'])
		cast_count = len(skill['skills'])

		top_stats['skill_casts_by_role'][profession][name_prof]['total'] += cast_count
		if not skill_data[skill_id]['auto']:
			top_stats['skill_casts_by_role'][profession][name_prof]['total_no_auto'] += cast_count
			
		if skill_id not in top_stats['skill_casts_by_role'][profession][name_prof]['Skills']:
			top_stats['skill_casts_by_role'][profession][name_prof]['Skills'][skill_id] = 0
		if skill_id not in top_stats['skill_casts_by_role'][profession]['total']:
			top_stats['skill_casts_by_role'][profession]['total'][skill_id] = 0

		top_stats['skill_casts_by_role'][profession]['total'][skill_id] += cast_count
		top_stats['skill_casts_by_role'][profession][name_prof]['Skills'][skill_id] = top_stats['skill_casts_by_role'][profession][name_prof]['Skills'].get(skill_id, 0) + cast_count

def get_healStats_data(fight_num: int, player: dict, players: dict, stat_category: str, name_prof: str, fight_time: int) -> None:
	"""
	Collect data for extHealingStats and extBarrierStats

	Args:
		fight_num (int): The fight number.
		player (dict): The player dictionary.
		players (dict): The players dictionary.
		stat_category (str): The category of stats to collect.
		name_prof (str): The name of the profession.
	"""
	fight_healing = 0

	if stat_category == 'extHealingStats' and 'extHealingStats' in player:
		healer_name = player['name']
		healer_group = player['group']
		for index, heal_target in enumerate(player[stat_category]['outgoingHealingAllies']):
			heal_target_name = players[index]['name']
			heal_target_group = players[index]['group']
			heal_target_notInSquad = players[index]['notInSquad']
			heal_target_tag = players[index]['hasCommanderTag']
			outgoing_healing = heal_target[0]['healing'] - heal_target[0]['downedHealing']
			downed_healing = heal_target[0]['downedHealing']

			fight_healing += outgoing_healing

			if outgoing_healing or downed_healing:

				if heal_target_tag:
					commander_name = f"{heal_target_name}|{players[index]['profession']}|{players[index]['account']}"

					if name_prof not in commander_summary_data[commander_name]['heal_stats']:
						commander_summary_data[commander_name]['heal_stats'][name_prof] = {
							'outgoing_healing': 0,
							'downed_healing': 0,
							'outgoing_barrier': 0
						}

					commander_summary_data[commander_name]['heal_stats'][name_prof]['outgoing_healing'] += outgoing_healing
					commander_summary_data[commander_name]['heal_stats'][name_prof]['downed_healing'] += downed_healing


				if 'heal_targets' not in top_stats['player'][name_prof][stat_category]:
					top_stats['player'][name_prof][stat_category]['heal_targets'] = {}

				if heal_target_name not in top_stats['player'][name_prof][stat_category]['heal_targets']:
					top_stats['player'][name_prof][stat_category]['heal_targets'][heal_target_name] = {
						'outgoing_healing': 0,
						'downed_healing': 0
					}

				top_stats['player'][name_prof][stat_category]['outgoing_healing'] = (
					top_stats['player'][name_prof][stat_category].get('outgoing_healing', 0) + outgoing_healing
				)

				if heal_target_notInSquad:
					top_stats['player'][name_prof][stat_category]['off_squad_healing'] = (
						top_stats['player'][name_prof][stat_category].get('off_squad_healing', 0) + outgoing_healing
					)
					top_stats['player'][name_prof][stat_category]['off_squad_downed_healing'] = (
						top_stats['player'][name_prof][stat_category].get('off_squad_downed_healing', 0) + downed_healing
					)					
				else:
					top_stats['player'][name_prof][stat_category]['squad_healing'] = (
						top_stats['player'][name_prof][stat_category].get('squad_healing', 0) + outgoing_healing
					)
					top_stats['player'][name_prof][stat_category]['squad_downed_healing'] = (
						top_stats['player'][name_prof][stat_category].get('squad_downed_healing', 0) + downed_healing
					)					

				if heal_target_group == healer_group:

					top_stats['player'][name_prof][stat_category]['group_healing'] = (
						top_stats['player'][name_prof][stat_category].get('group_healing', 0) + outgoing_healing
					)
					top_stats['player'][name_prof][stat_category]['group_downed_healing'] = (
						top_stats['player'][name_prof][stat_category].get('group_downed_healing', 0) + downed_healing
					)

				if heal_target_name == healer_name:

					top_stats['player'][name_prof][stat_category]['self_healing'] = (
						top_stats['player'][name_prof][stat_category].get('self_healing', 0) + outgoing_healing
					)
					top_stats['player'][name_prof][stat_category]['self_downed_healing'] = (
						top_stats['player'][name_prof][stat_category].get('self_downed_healing', 0) + downed_healing
					)
					

				top_stats['player'][name_prof][stat_category]['heal_targets'][heal_target_name]['outgoing_healing'] = (
					top_stats['player'][name_prof][stat_category]['heal_targets'][heal_target_name].get('outgoing_healing', 0) + outgoing_healing
				)

				top_stats['fight'][fight_num][stat_category]['outgoing_healing'] = (
					top_stats['fight'][fight_num][stat_category].get('outgoing_healing', 0) + outgoing_healing
				)

				top_stats['overall'][stat_category]['outgoing_healing'] = (
					top_stats['overall'][stat_category].get('outgoing_healing', 0) + outgoing_healing
				)

				top_stats['player'][name_prof][stat_category]['downed_healing'] = (
					top_stats['player'][name_prof][stat_category].get('downed_healing', 0) + downed_healing
				)
				top_stats['player'][name_prof][stat_category]['heal_targets'][heal_target_name]['downed_healing'] = (
					top_stats['player'][name_prof][stat_category]['heal_targets'][heal_target_name].get('downed_healing', 0) + downed_healing
				)
				top_stats['fight'][fight_num][stat_category]['downed_healing'] = (
					top_stats['fight'][fight_num][stat_category].get('downed_healing', 0) + downed_healing
				)
				top_stats['overall'][stat_category]['downed_healing'] = (
					top_stats['overall'][stat_category].get('downed_healing', 0) + downed_healing
				)
		update_high_score(f"{stat_category}_Healing", "{{"+player["profession"]+"}}"+player["name"]+"-"+get_player_account(player)+"-"+str(fight_num)+" | Healing", round(fight_healing/(fight_time/1000), 2))	

	fight_barrier = 0
	if stat_category == 'extBarrierStats' and 'extBarrierStats' in player:
		healer_name = player['name']
		healer_group = player['group']		
		for index, barrier_target in enumerate(player[stat_category]['outgoingBarrierAllies']):
			barrier_target_name = players[index]['name']
			barrier_target_group = players[index]['group']
			barrier_target_notInSquad = players[index]['notInSquad']
			heal_target_tag = players[index]['hasCommanderTag']
			outgoing_barrier = barrier_target[0]['barrier']

			fight_barrier += outgoing_barrier

			if outgoing_barrier:
				if heal_target_tag:
					commander_name = f"{barrier_target_name}|{players[index]['profession']}|{players[index]['account']}"

					if name_prof not in commander_summary_data[commander_name]['heal_stats']:
						commander_summary_data[commander_name]['heal_stats'][name_prof] = {
							'outgoing_healing': 0,
							'downed_healing': 0,
							'outgoing_barrier': 0
						}

					commander_summary_data[commander_name]['heal_stats'][name_prof]['outgoing_barrier'] += outgoing_barrier	


				if 'barrier_targets' not in top_stats['player'][name_prof][stat_category]:
					top_stats['player'][name_prof][stat_category]['barrier_targets'] = {}

				if barrier_target_name not in top_stats['player'][name_prof][stat_category]['barrier_targets']:
					top_stats['player'][name_prof][stat_category]['barrier_targets'][barrier_target_name] = {
						'outgoing_barrier': 0
					}

				top_stats['player'][name_prof][stat_category]['outgoing_barrier'] = (
					top_stats['player'][name_prof][stat_category].get('outgoing_barrier', 0) + outgoing_barrier
				)

				if barrier_target_notInSquad:
					#off_squad_barrier
					top_stats['player'][name_prof][stat_category]['off_squad_barrier'] = (
						top_stats['player'][name_prof][stat_category].get('off_squad_barrier', 0) + outgoing_barrier
					)
				else:
					top_stats['player'][name_prof][stat_category]['squad_barrier'] = (
						top_stats['player'][name_prof][stat_category].get('squad_barrier', 0) + outgoing_barrier
					)

				if barrier_target_group == healer_group:

					top_stats['player'][name_prof][stat_category]['group_barrier'] = (
						top_stats['player'][name_prof][stat_category].get('group_barrier', 0) + outgoing_barrier
					)

				if barrier_target_name == healer_name:

					top_stats['player'][name_prof][stat_category]['self_barrier'] = (
						top_stats['player'][name_prof][stat_category].get('self_barrier', 0) + outgoing_barrier
					)

				top_stats['player'][name_prof][stat_category]['barrier_targets'][barrier_target_name]['outgoing_barrier'] = (
					top_stats['player'][name_prof][stat_category]['barrier_targets'][barrier_target_name].get('outgoing_barrier', 0) + outgoing_barrier
				)

				top_stats['fight'][fight_num][stat_category]['outgoing_barrier'] = (
					top_stats['fight'][fight_num][stat_category].get('outgoing_barrier', 0) + outgoing_barrier
				)

				top_stats['overall'][stat_category]['outgoing_barrier'] = (
					top_stats['overall'][stat_category].get('outgoing_barrier', 0) + outgoing_barrier
				)
		update_high_score(f"{stat_category}_Barrier", "{{"+player["profession"]+"}}"+player["name"]+"-"+get_player_account(player)+"-"+str(fight_num)+" | Barrier", round(fight_barrier/(fight_time/1000), 2))

def get_healing_skill_data(player: dict, stat_category: str, name_prof: str) -> None:
	"""
	Collect data for extHealingStats and extBarrierStats

	Args:
		player (dict): The player dictionary.
		stat_category (str): The category of stats to collect.
		name_prof (str): The name of the profession.
	"""
	if 'alliedHealingDist' in player[stat_category]:
		for heal_target in player[stat_category]['alliedHealingDist']:
			for skill in heal_target[0]:
				skill_id = 's'+str(skill['id'])
				hits = skill['hits']
				min_value = skill['min']
				max_value = skill['max']

				if 'skills' not in top_stats['player'][name_prof][stat_category]:
					top_stats['player'][name_prof][stat_category]['skills'] = {}

				if skill_id not in top_stats['player'][name_prof][stat_category]['skills']:
					top_stats['player'][name_prof][stat_category]['skills'][skill_id] = {}

				top_stats['player'][name_prof][stat_category]['skills'][skill_id]['hits'] = (
					top_stats['player'][name_prof][stat_category]['skills'][skill_id].get('hits', 0) + hits
				)

				current_min = top_stats['player'][name_prof][stat_category]['skills'][skill_id].get('min', 0)
				current_max = top_stats['player'][name_prof][stat_category]['skills'][skill_id].get('max', 0)

				if min_value < current_min or current_min == 0:
					top_stats['player'][name_prof][stat_category]['skills'][skill_id]['min'] = min_value
				if max_value > current_max or current_max == 0:
					top_stats['player'][name_prof][stat_category]['skills'][skill_id]['max'] = max_value

				total_healing = skill['totalHealing']
				downed_healing = skill['totalDownedHealing']
				healing = total_healing - downed_healing

				top_stats['player'][name_prof][stat_category]['skills'][skill_id]['totalHealing'] = (
					top_stats['player'][name_prof][stat_category]['skills'][skill_id].get('totalHealing', 0) + total_healing
				)

				top_stats['player'][name_prof][stat_category]['skills'][skill_id]['downedHealing'] = (
					top_stats['player'][name_prof][stat_category]['skills'][skill_id].get('downedHealing', 0) + downed_healing
				)

				top_stats['player'][name_prof][stat_category]['skills'][skill_id]['healing'] = (
					top_stats['player'][name_prof][stat_category]['skills'][skill_id].get('healing', 0) + healing
				)

def get_barrier_skill_data(player: dict, stat_category: str, name_prof: str) -> None:
	"""
	Collect data for extHealingStats and extBarrierStats

	Args:
		player (dict): The player dictionary.
		stat_category (str): The category of stats to collect.
		name_prof (str): The name of the profession.
	"""
	if 'extBarrierStats' in player and 'alliedBarrierDist' in player[stat_category]:
		for barrier_target in player[stat_category]['alliedBarrierDist']:
			for skill in barrier_target[0]:
				skill_id = 's'+str(skill['id'])
				hits = skill['hits']
				min_value = skill['min']
				max_value = skill['max']

				if 'skills' not in top_stats['player'][name_prof][stat_category]:
					top_stats['player'][name_prof][stat_category]['skills'] = {}

				if skill_id not in top_stats['player'][name_prof][stat_category]['skills']:
					top_stats['player'][name_prof][stat_category]['skills'][skill_id] = {}

				top_stats['player'][name_prof][stat_category]['skills'][skill_id]['hits'] = (
					top_stats['player'][name_prof][stat_category]['skills'][skill_id].get('hits', 0) + hits
				)

				current_min = top_stats['player'][name_prof][stat_category]['skills'][skill_id].get('min', 0)
				current_max = top_stats['player'][name_prof][stat_category]['skills'][skill_id].get('max', 0)

				if min_value < current_min or current_min == 0:
					top_stats['player'][name_prof][stat_category]['skills'][skill_id]['min'] = min_value
				if max_value > current_max or current_max == 0:
					top_stats['player'][name_prof][stat_category]['skills'][skill_id]['max'] = max_value

				total_barrier = skill['totalBarrier']

				top_stats['player'][name_prof][stat_category]['skills'][skill_id]['totalBarrier'] = (
					top_stats['player'][name_prof][stat_category]['skills'][skill_id].get('totalBarrier', 0) + total_barrier
				)

def get_damage_mod_by_player(fight_num: int, player: dict, name_prof: str) -> None:
	"""
	Collect and update damage modifier statistics for a player.

	This function iterates through various categories of damage modifiers for a given player and updates
	the statistics in the top_stats dictionary for individual players, specific fights, and overall stats.
	It also updates the commander summary if the player has a commander tag.

	Args:
		fight_num (int): The fight number.
		player (dict): The player dictionary containing player-specific data.
		name_prof (str): The player's name and profession identifier.
	"""
	mod_list = ["damageModifiers", "damageModifiersTarget", "incomingDamageModifiers", "incomingDamageModifiersTarget"]
	commander_tag = player['hasCommanderTag']

	for mod_cat in mod_list:
		if mod_cat in player:
			for modifier in player[mod_cat]:
				if "id" not in modifier:
					continue

				mod_id = "d" + str(modifier['id'])
				mod_hit_count = modifier["damageModifiers"][0]['hitCount']
				mod_total_hit_count = modifier["damageModifiers"][0]['totalHitCount']
				mod_damage_gain = modifier["damageModifiers"][0]['damageGain']
				mod_total_damage = modifier["damageModifiers"][0]['totalDamage']

				# Update commander summary data if the player has a commander tag
				if commander_tag:
					commander_name = f"{player['name']}|{player['profession']}|{get_player_account(player)}"
					if mod_id == 'd-58':
						commander_summary_data[commander_name]['prot_mods']['hitCount'] += mod_hit_count
						commander_summary_data[commander_name]['prot_mods']['totalHitCount'] += mod_total_hit_count
						commander_summary_data[commander_name]['prot_mods']['damageGain'] += mod_damage_gain
						commander_summary_data[commander_name]['prot_mods']['totalDamage'] += mod_total_damage

				# Update player's damage modifier statistics
				if mod_id not in top_stats['player'][name_prof]['damageModifiers']:
					top_stats['player'][name_prof]['damageModifiers'][mod_id] = {}

				top_stats['player'][name_prof]['damageModifiers'][mod_id]['hitCount'] = (
					top_stats['player'][name_prof]['damageModifiers'][mod_id].get('hitCount', 0) + mod_hit_count
				)
				top_stats['player'][name_prof]['damageModifiers'][mod_id]['totalHitCount'] = (
					top_stats['player'][name_prof]['damageModifiers'][mod_id].get('totalHitCount', 0) + mod_total_hit_count
				)
				top_stats['player'][name_prof]['damageModifiers'][mod_id]['damageGain'] = (
					top_stats['player'][name_prof]['damageModifiers'][mod_id].get('damageGain', 0) + mod_damage_gain
				)
				top_stats['player'][name_prof]['damageModifiers'][mod_id]['totalDamage'] = (
					top_stats['player'][name_prof]['damageModifiers'][mod_id].get('totalDamage', 0) + mod_total_damage
				)

				# Update fight-specific damage modifier statistics
				if mod_id not in top_stats['fight'][fight_num]['damageModifiers']:
					top_stats['fight'][fight_num]['damageModifiers'][mod_id] = {}

				top_stats['fight'][fight_num]['damageModifiers'][mod_id]['hitCount'] = (
					top_stats['fight'][fight_num]['damageModifiers'][mod_id].get('hitCount', 0) + mod_hit_count
				)
				top_stats['fight'][fight_num]['damageModifiers'][mod_id]['totalHitCount'] = (
					top_stats['fight'][fight_num]['damageModifiers'][mod_id].get('totalHitCount', 0) + mod_total_hit_count
				)
				top_stats['fight'][fight_num]['damageModifiers'][mod_id]['damageGain'] = (
					top_stats['fight'][fight_num]['damageModifiers'][mod_id].get('damageGain', 0) + mod_damage_gain
				)
				top_stats['fight'][fight_num]['damageModifiers'][mod_id]['totalDamage'] = (
					top_stats['fight'][fight_num]['damageModifiers'][mod_id].get('totalDamage', 0) + mod_total_damage
				)

				# Update overall damage modifier statistics
				if mod_id not in top_stats['overall']['damageModifiers']:
					top_stats['overall']['damageModifiers'][mod_id] = {}

				top_stats['overall']['damageModifiers'][mod_id]['hitCount'] = (
					top_stats['overall']['damageModifiers'][mod_id].get('hitCount', 0) + mod_hit_count
				)
				top_stats['overall']['damageModifiers'][mod_id]['totalHitCount'] = (
					top_stats['overall']['damageModifiers'][mod_id].get('totalHitCount', 0) + mod_total_hit_count
				)
				top_stats['overall']['damageModifiers'][mod_id]['damageGain'] = (
					top_stats['overall']['damageModifiers'][mod_id].get('damageGain', 0) + mod_damage_gain
				)
				top_stats['overall']['damageModifiers'][mod_id]['totalDamage'] = (
					top_stats['overall']['damageModifiers'][mod_id].get('totalDamage', 0) + mod_total_damage
				)

def get_firebrand_pages(player, name_prof, name, account, fight_duration_ms):
	"""
	Collects data for firebrand pages (skills).

	Args:
		player (dict): The player dictionary.
		name_prof (str): The name and profession of the player.
		name (str): The name of the player.
		account (str): The account of the player.
		fight_duration_ms (int): The duration of the fight in milliseconds.
	"""
	if player['profession'] == "Firebrand" and "rotation" in player:
		if name_prof not in fb_pages:
			fb_pages[name_prof] = {}
			fb_pages[name_prof]["account"] = account
			fb_pages[name_prof]["name"] = name
			fb_pages[name_prof]["fightTime"] = 0
			fb_pages[name_prof]["firebrand_pages"] = {}
		
		# Track Firebrand Buffs
		tome1_skill_ids = ["41258", "40635", "42449", "40015", "42898"]
		tome2_skill_ids = ["45022", "40679", "45128", "42008", "42925"]
		tome3_skill_ids = ["42986", "41968", "41836", "40988", "44455"]
		tome_skill_ids = [
			*tome1_skill_ids,
			*tome2_skill_ids,
			*tome3_skill_ids,
		]

		fb_pages[name_prof]["fightTime"] += fight_duration_ms
		for rotation_skill in player['rotation']:
			skill_id = str(rotation_skill['id'])
			if skill_id in tome_skill_ids:
				pages_data = fb_pages[name_prof]["firebrand_pages"]
				pages_data[skill_id] = pages_data.get(skill_id, 0) + len(rotation_skill['skills'])

def get_mechanics_by_fight(fight_number, mechanics_map: dict, players: dict, log_type: str) -> None:
	"""
	Collects mechanics data from a fight and stores it in a dictionary.

	Args:
		fight_number (int): The fight number for the data.
		mechanics_map (dict): The dictionary of mechanics data.
		players (dict): The players data.
		log_type (str): The type of log, either PVE or WVW.
	"""
	if log_type == "PVE":
		# Initialize the mechanics dictionary for a PVE fight
		if fight_number not in mechanics:
			mechanics[fight_number] = {
				"player_list": [],
				"enemy_list": [],
				}
	else:
		# Initialize the mechanics dictionary for a WVW fight
		fight_number = "WVW"
		if fight_number not in mechanics:
			mechanics[fight_number] = {
				"player_list": [],
				"enemy_list": [],
				}

	# Loop through each mechanic in the fight
	for mechanic_data in mechanics_map:
		mechanic_name = mechanic_data['name']
		description = mechanic_data['description']
		is_eligible = mechanic_data['isAchievementEligibility']

		# Initialize the mechanics dictionary for the mechanic if it doesn't exist
		if mechanic_name not in mechanics[fight_number]:
			mechanics[fight_number][mechanic_name] = {
				'tip': description,
				'eligibile': is_eligible,
				'data': {},
				'enemy_data': {}
			}

		# Loop through each data item for the mechanic
		for data_item in mechanic_data['mechanicsData']:
			actor = data_item['actor']
			prof_name = None
			# Loop through each player in the fight
			for player in players:
				if player['name'] == actor:
					# Get the player's profession and name
					prof_name = player['profession'] + "|" + player['name'] + "|" + get_player_account(player)

			# If the actor is a player, add it to the player list
			if prof_name:
				if prof_name not in mechanics[fight_number]['player_list']:
					mechanics[fight_number]['player_list'].append(prof_name)
				# Increment the player's data for the mechanic
				if prof_name not in mechanics[fight_number][mechanic_name]['data']:
					mechanics[fight_number][mechanic_name]['data'][prof_name] = 1
				else:
					mechanics[fight_number][mechanic_name]['data'][prof_name] += 1
			else:
				# If the actor is an enemy, add it to the enemy list
				if actor not in mechanics[fight_number]['enemy_list']:
					mechanics[fight_number]['enemy_list'].append(actor)
				# Increment the enemy's data for the mechanic
				if actor not in mechanics[fight_number][mechanic_name]['enemy_data']:
					mechanics[fight_number][mechanic_name]['enemy_data'][actor] = 1
				else:
					mechanics[fight_number][mechanic_name]['enemy_data'][actor] += 1

def get_rally_mechanics_by_fight(mechanics_map, players):
	"""
	Get the number of rallies by fight from the mechanics map.

	Args:
		mechanics_map (dict): The mechanics map from the log.
		players (list): A list of player data from the log.

	Returns:
		int: The number of rallies by fight.
	"""
	got_ups = {}
	got_up_cnts = {}
	killing_blows = {}
	killing_blows_cnts = {}
	rallies = 0

	for mechanic_data in mechanics_map:
		mechanic_name = mechanic_data['name']
		if "Got" in mechanic_name:
			got_ups = mechanic_data['mechanicsData']
			for entry in got_ups:
				gu_time = entry['time']
				if gu_time not in got_up_cnts:
					got_up_cnts[gu_time] = 0
				got_up_cnts[gu_time] += 1

		if mechanic_name == "Kllng.Blw.Player":
			killing_blows = mechanic_data['mechanicsData']
			for entry in killing_blows:
				kb_time = entry['time']
				kb_actor = entry['actor']
				kb_key = f"{kb_time}|{kb_actor}"
				if kb_key not in killing_blows_cnts:
					killing_blows_cnts[kb_key] = 0
				killing_blows_cnts[kb_key] += 1		

	for gu_entry in got_up_cnts:
		rally_time = gu_entry
		for kb_entry in killing_blows_cnts:
			kb_time, kb_actor = kb_entry.split('|')
			for player in players:
				if player['name'] == kb_actor:
					kb_actor = f"{player['profession']}|{player['name']}|{get_player_account(player)}"
			if str(kb_time) == str(rally_time):
				rally_count = got_up_cnts[gu_entry] if got_up_cnts[gu_entry] < killing_blows_cnts[kb_entry] else killing_blows_cnts[kb_entry]
				killing_blow_rallies['total'] += rally_count
				rallies += rally_count
				if kb_actor not in killing_blow_rallies['kb_players']:
					killing_blow_rallies['kb_players'][kb_actor] = 0
				killing_blow_rallies['kb_players'][kb_actor] = killing_blow_rallies['kb_players'].get(kb_actor,0) + rally_count

	return rallies

def get_damage_mitigation_data(fight_num: int, players: dict, targets: dict, skill_data: dict, buff_data: dict) -> None:
	"""
	Collects damage mitigation data from a fight and stores it in a dictionary.

	Args:
		fight_num (int): The fight number for the data.
		players (dict): The players data.
		targets (dict): The targets data.
		skill_data (dict): The skill data.
		buff_data (dict): The buff data.
	"""
	for target in targets:
		if 'totalDamageDist' in target:
			for skill in target['totalDamageDist'][0]:
				skill_id = skill['id']
				if f"s{skill_id}" in skill_data:
					skill_name = skill_data[f"s{skill_id}"]['name']
				elif f"b{skill_id}" in buff_data:
					skill_name = buff_data[f"b{skill_id}"]['name']
				else:
					skill_name = f"Unknown Skill {skill_id}"
				if skill_name not in enemy_avg_damage_per_skill:
					enemy_avg_damage_per_skill[skill_name] = {
						'dmg': 0,
						'hits': 0,
						'min': []
					}
				enemy_avg_damage_per_skill[skill_name]['dmg'] += skill['totalDamage']
				enemy_avg_damage_per_skill[skill_name]['hits'] += skill['connectedHits']
				enemy_avg_damage_per_skill[skill_name]['min'].append(skill['min'])

	for player in players:
		if player['notInSquad']:
			continue
		name_prof = f"{player['name']}|{player['profession']}|{get_player_account(player)}"
		if 'totalDamageTaken' in player:
			if name_prof not in player_damage_mitigation:
				player_damage_mitigation[name_prof] = {}
			for skill in player['totalDamageTaken'][0]:
				skill_id = skill['id']
				if f"s{skill_id}" in skill_data:
					skill_name = skill_data[f"s{skill_id}"]['name']
				elif f"b{skill_id}" in buff_data:
					skill_name = buff_data[f"b{skill_id}"]['name']
				else:
					skill_name = f"Unknown Skill {skill_id}"
				if skill_name not in player_damage_mitigation[name_prof]:
					player_damage_mitigation[name_prof][skill_name] = {
						'blocked': 0,
						'blocked_dmg': 0,
						'evaded': 0,
						'evaded_dmg': 0,
						'glanced': 0,
						'glanced_dmg': 0,
						'missed': 0,
						'missed_dmg': 0,
						'invulned': 0,
						'invulned_dmg': 0,
						'interrupted': 0,
						'interrupted_dmg': 0,
						'total_dmg': 0,
						'skill_hits': 0,
						'total_hits': 0,
						'avg_dmg': 0,
						'min_dmg': 0,
						'avoided_damage': 0,
						'min_avoided_damage': 0
					}

				if skill_name not in enemy_avg_damage_per_skill:
					enemy_avg_dmg = 1
					enemy_min_dmg = 1
				else:
					enemy_min_dmg = sum(enemy_avg_damage_per_skill[skill_name]['min']) / len(enemy_avg_damage_per_skill[skill_name]['min']) if skill_name in enemy_avg_damage_per_skill else 0
					enemy_avg_dmg = enemy_avg_damage_per_skill[skill_name]['dmg'] / enemy_avg_damage_per_skill[skill_name]['hits'] if enemy_avg_damage_per_skill[skill_name]['hits'] > 0 else 0
				player_damage_mitigation[name_prof][skill_name]['blocked'] += skill['blocked']
				player_damage_mitigation[name_prof][skill_name]['evaded'] += skill['evaded']
				player_damage_mitigation[name_prof][skill_name]['glanced'] += skill['glance']
				player_damage_mitigation[name_prof][skill_name]['missed'] += skill['missed']
				player_damage_mitigation[name_prof][skill_name]['invulned'] += skill['invulned']
				player_damage_mitigation[name_prof][skill_name]['interrupted'] += skill['interrupted']
				player_damage_mitigation[name_prof][skill_name]['total_dmg'] = enemy_avg_damage_per_skill[skill_name]['dmg'] if skill_name in enemy_avg_damage_per_skill else 0
				player_damage_mitigation[name_prof][skill_name]['skill_hits'] += skill['hits']
				player_damage_mitigation[name_prof][skill_name]['total_hits'] = enemy_avg_damage_per_skill[skill_name]['hits'] if skill_name in enemy_avg_damage_per_skill else 0
				if player_damage_mitigation[name_prof][skill_name]['total_hits'] > 0:
					player_damage_mitigation[name_prof][skill_name]['avg_dmg'] = enemy_avg_dmg
					player_damage_mitigation[name_prof][skill_name]['min_dmg'] = enemy_min_dmg
					avoided_damage = (
						player_damage_mitigation[name_prof][skill_name]['glanced'] * player_damage_mitigation[name_prof][skill_name]['avg_dmg'] / 2
						+ (
							(
							player_damage_mitigation[name_prof][skill_name]['blocked']
							+ player_damage_mitigation[name_prof][skill_name]['evaded']
							+ player_damage_mitigation[name_prof][skill_name]['missed']
							+ player_damage_mitigation[name_prof][skill_name]['invulned']
							+ player_damage_mitigation[name_prof][skill_name]['interrupted']
						) * player_damage_mitigation[name_prof][skill_name]['avg_dmg']
						)
					)
					min_avoided_damage = (
						player_damage_mitigation[name_prof][skill_name]['glanced'] * player_damage_mitigation[name_prof][skill_name]['min_dmg'] / 2
						+ (
							(
							player_damage_mitigation[name_prof][skill_name]['blocked']
							+ player_damage_mitigation[name_prof][skill_name]['evaded']
							+ player_damage_mitigation[name_prof][skill_name]['missed']
							+ player_damage_mitigation[name_prof][skill_name]['invulned']
							+ player_damage_mitigation[name_prof][skill_name]['interrupted']
						) * player_damage_mitigation[name_prof][skill_name]['min_dmg']
						)
					)
					player_damage_mitigation[name_prof][skill_name]['blocked_dmg'] += player_damage_mitigation[name_prof][skill_name]['blocked'] * player_damage_mitigation[name_prof][skill_name]['avg_dmg']
					player_damage_mitigation[name_prof][skill_name]['evaded_dmg'] += player_damage_mitigation[name_prof][skill_name]['evaded'] * player_damage_mitigation[name_prof][skill_name]['avg_dmg']
					player_damage_mitigation[name_prof][skill_name]['glanced_dmg'] += player_damage_mitigation[name_prof][skill_name]['glanced'] * (player_damage_mitigation[name_prof][skill_name]['avg_dmg']/2)
					player_damage_mitigation[name_prof][skill_name]['missed_dmg'] += player_damage_mitigation[name_prof][skill_name]['missed'] * player_damage_mitigation[name_prof][skill_name]['avg_dmg']
					player_damage_mitigation[name_prof][skill_name]['invulned_dmg'] += player_damage_mitigation[name_prof][skill_name]['invulned'] * player_damage_mitigation[name_prof][skill_name]['avg_dmg']
					player_damage_mitigation[name_prof][skill_name]['interrupted_dmg'] += player_damage_mitigation[name_prof][skill_name]['interrupted'] * player_damage_mitigation[name_prof][skill_name]['avg_dmg']
					player_damage_mitigation[name_prof][skill_name]['avoided_damage'] += avoided_damage
					player_damage_mitigation[name_prof][skill_name]['min_avoided_damage'] += min_avoided_damage

		if "minions" in player:
			for minion in player["minions"]:
				if 'totalDamageTakenDist' not in minion:
					continue
				minion_name = minion["name"].replace("Juvenile ", "")
				if "UNKNOWN" in minion_name:
					minion_name = "Unknown"
				for skill in minion['totalDamageTakenDist'][0]:
					skill_id = skill['id']
					if f"s{skill_id}" in skill_data:
						skill_name = skill_data[f"s{skill_id}"]['name']
					elif f"b{skill_id}" in buff_data:
						skill_name = buff_data[f"b{skill_id}"]['name']
					else:
						skill_name = f"Unknown Skill {skill_id}"

					if name_prof not in player_minion_damage_mitigation:
						player_minion_damage_mitigation[name_prof] = {}
					if minion_name not in player_minion_damage_mitigation[name_prof]:
						player_minion_damage_mitigation[name_prof][minion_name] = {}
					if skill_name not in player_minion_damage_mitigation[name_prof][minion_name]:
						player_minion_damage_mitigation[name_prof][minion_name][skill_name] = {
							'blocked': 0,
							'blocked_dmg': 0,
							'evaded': 0,
							'evaded_dmg': 0,
							'glanced': 0,
							'glanced_dmg': 0,
							'missed': 0,
							'missed_dmg': 0,
							'invulned': 0,
							'invulned_dmg': 0,
							'interrupted': 0,
							'interrupted_dmg': 0,
							'total_dmg': 0,
							'skill_hits': 0,
							'total_hits': 0,
							'avg_dmg': 0,
							'min_dmg': 0,
							'avoided_damage': 0,
							'min_avoided_damage': 0							
						}
					if skill_name not in enemy_avg_damage_per_skill:
						enemy_avg_dmg = 1
						enemy_min_dmg = 1
					else:
						enemy_min_dmg = sum(enemy_avg_damage_per_skill[skill_name]['min']) / len(enemy_avg_damage_per_skill[skill_name]['min']) if skill_name in enemy_avg_damage_per_skill else 0
						enemy_avg_dmg = enemy_avg_damage_per_skill[skill_name]['dmg'] / enemy_avg_damage_per_skill[skill_name]['hits'] if enemy_avg_damage_per_skill[skill_name]['hits'] > 0 else 0
					player_minion_damage_mitigation[name_prof][minion_name][skill_name]['blocked'] += skill['blocked']
					player_minion_damage_mitigation[name_prof][minion_name][skill_name]['evaded'] += skill['evaded']
					player_minion_damage_mitigation[name_prof][minion_name][skill_name]['glanced'] += skill['glance']
					player_minion_damage_mitigation[name_prof][minion_name][skill_name]['missed'] += skill['missed']
					player_minion_damage_mitigation[name_prof][minion_name][skill_name]['invulned'] += skill['invulned']
					player_minion_damage_mitigation[name_prof][minion_name][skill_name]['interrupted'] += skill['interrupted']
					player_minion_damage_mitigation[name_prof][minion_name][skill_name]['skill_hits'] += skill['hits']
					player_minion_damage_mitigation[name_prof][minion_name][skill_name]['total_dmg'] = enemy_avg_damage_per_skill[skill_name]['dmg'] if skill_name in enemy_avg_damage_per_skill else 0
					player_minion_damage_mitigation[name_prof][minion_name][skill_name]['total_hits'] = enemy_avg_damage_per_skill[skill_name]['hits'] if skill_name in enemy_avg_damage_per_skill else 0

					if player_minion_damage_mitigation[name_prof][minion_name][skill_name]['skill_hits'] > 0:
						player_minion_damage_mitigation[name_prof][minion_name][skill_name]['avg_dmg'] = enemy_avg_dmg
						if skill_name in enemy_avg_damage_per_skill:
							player_minion_damage_mitigation[name_prof][minion_name][skill_name]['min_dmg'] = enemy_min_dmg
						else:
							player_minion_damage_mitigation[name_prof][minion_name][skill_name]['min_dmg'] = 0
						avoided_damage = (
							player_minion_damage_mitigation[name_prof][minion_name][skill_name]['glanced'] * player_minion_damage_mitigation[name_prof][minion_name][skill_name]['avg_dmg']/2
							+(
								(
									#player_minion_damage_mitigation[name_prof][minion_name][
									player_minion_damage_mitigation[name_prof][minion_name][skill_name]['blocked']
									+ player_minion_damage_mitigation[name_prof][minion_name][skill_name]['evaded']
									+ player_minion_damage_mitigation[name_prof][minion_name][skill_name]['missed']
									+ player_minion_damage_mitigation[name_prof][minion_name][skill_name]['invulned']
									+ player_minion_damage_mitigation[name_prof][minion_name][skill_name]['interrupted']

								)* player_minion_damage_mitigation[name_prof][minion_name][skill_name]['avg_dmg']
							)
						)
						min_avoided_damage = (
							player_minion_damage_mitigation[name_prof][minion_name][skill_name]['glanced'] * player_minion_damage_mitigation[name_prof][minion_name][skill_name]['min_dmg']/2
							+(
								(
									player_minion_damage_mitigation[name_prof][minion_name][skill_name]['blocked']
									+player_minion_damage_mitigation[name_prof][minion_name][skill_name]['evaded']
									+player_minion_damage_mitigation[name_prof][minion_name][skill_name]['missed']
									+player_minion_damage_mitigation[name_prof][minion_name][skill_name]['invulned']
									+player_minion_damage_mitigation[name_prof][minion_name][skill_name]['interrupted']

								)*player_minion_damage_mitigation[name_prof][minion_name][skill_name]['min_dmg']
							)
						)
						player_minion_damage_mitigation[name_prof][minion_name][skill_name]['blocked_dmg'] = player_minion_damage_mitigation[name_prof][minion_name][skill_name]['blocked'] * player_minion_damage_mitigation[name_prof][minion_name][skill_name]['avg_dmg']
						player_minion_damage_mitigation[name_prof][minion_name][skill_name]['evaded_dmg'] = player_minion_damage_mitigation[name_prof][minion_name][skill_name]['evaded'] * player_minion_damage_mitigation[name_prof][minion_name][skill_name]['avg_dmg']
						player_minion_damage_mitigation[name_prof][minion_name][skill_name]['glanced_dmg'] = player_minion_damage_mitigation[name_prof][minion_name][skill_name]['glanced'] * (player_minion_damage_mitigation[name_prof][minion_name][skill_name]['avg_dmg']/2)
						player_minion_damage_mitigation[name_prof][minion_name][skill_name]['missed_dmg'] = player_minion_damage_mitigation[name_prof][minion_name][skill_name]['missed'] * player_minion_damage_mitigation[name_prof][minion_name][skill_name]['avg_dmg']
						player_minion_damage_mitigation[name_prof][minion_name][skill_name]['invulned_dmg'] = player_minion_damage_mitigation[name_prof][minion_name][skill_name]['invulned'] * player_minion_damage_mitigation[name_prof][minion_name][skill_name]['avg_dmg']
						player_minion_damage_mitigation[name_prof][minion_name][skill_name]['interrupted_dmg'] = player_minion_damage_mitigation[name_prof][minion_name][skill_name]['interrupted'] * player_minion_damage_mitigation[name_prof][minion_name][skill_name]['avg_dmg']
						player_minion_damage_mitigation[name_prof][minion_name][skill_name]['avoided_damage'] = avoided_damage
						player_minion_damage_mitigation[name_prof][minion_name][skill_name]['min_avoided_damage'] = min_avoided_damage

def get_minions_by_player(player_data: dict, player_name: str, profession: str) -> None:
	"""
	Collects minions created by a player and stores them in a global dictionary.

	Args:
		player_data (dict): The player data containing minions information.
		player_name (str): The name of the player.
		profession (str): The profession of the player.

	Returns:
		None
	"""
	player_name = player_name+"|"+profession+"|"+get_player_account(player_data)
	if "minions" in player_data:
		if profession not in minions:
			minions[profession] = {"player": {}, "pets_list": [], "pet_skills_list": []}

		for minion in player_data["minions"]:
			minion_name = minion["name"].replace("Juvenile ", "")
			if "UNKNOWN" in minion_name:
				minion_name = "Unknown"
			if 'combatReplayData' in minion:
				minion_count = len(minion["combatReplayData"])
			else:
				minion_count = 1
			if minion_name not in minions[profession]["pets_list"]:
				minions[profession]["pets_list"].append(minion_name)
			if player_name not in minions[profession]["player"]:
				minions[profession]["player"][player_name] = {}
			if minion_name not in minions[profession]["player"][player_name]:
				minions[profession]["player"][player_name][minion_name] = minion_count
				minions[profession]["player"][player_name][minion_name+"Skills"] = {}
			else:
				minions[profession]["player"][player_name][minion_name] += minion_count
			if "totalDamageTaken" in minion:
				minions[profession]["player"][player_name][minion_name+"DamageTaken"] = minions[profession]["player"][player_name].get(minion_name+"DamageTaken", 0) + minion['totalDamageTaken'][0]
			else:
				minions[profession]["player"][player_name][minion_name+"DamageTaken"] = 0
			if "totalShieldDamage" in minion:
				minions[profession]["player"][player_name][minion_name+"ShieldDamage"] = minions[profession]["player"][player_name].get(minion_name+"ShieldDamage", 0) + minion['totalShieldDamage'][0]
			else:
				minions[profession]["player"][player_name][minion_name+"ShieldDamage"] = 0
			if 'extHealingStats' in minion and 'totalIncomingHealing' in minion['extHealingStats']:
				minions[profession]["player"][player_name][minion_name+"IncomingHealing"] = minions[profession]["player"][player_name].get(minion_name+"IncomingHealing", 0) + minion['extHealingStats']['totalIncomingHealing'][0]
			else:
				minions[profession]["player"][player_name][minion_name+"IncomingHealing"] = 0
			if "rotation" in minion:
				for skill in minion["rotation"]:
					if skill["id"] not in minions[profession]["pet_skills_list"]:
						minions[profession]["pet_skills_list"].append(skill["id"])
					skill_count = len(skill["skills"])
					if skill["id"] not in minions[profession]["player"][player_name][minion_name+"Skills"]:
						minions[profession]["player"][player_name][minion_name+"Skills"][skill["id"]] = skill_count
					else:
						minions[profession]["player"][player_name][minion_name+"Skills"][skill["id"]] += skill_count


def fetch_guild_data(guild_id: str, api_key: str, max_retries: int = 3, backoff_factor: float = 0.5) -> Optional[Dict]:
    """
    Fetches guild data from the Guild Wars 2 API with retry logic and enhanced error handling.

    Args:
        guild_id: The ID of the guild to fetch data for.
        api_key: The API key to use for the request.
        max_retries: Maximum number of retry attempts for failed requests (default: 3).
        backoff_factor: Factor for exponential backoff delay between retries (default: 0.5).

    Returns:
        A dictionary containing the guild data if the request is successful, otherwise None.
    """
    url = f"https://api.guildwars2.com/v2/guild/{guild_id}/members?access_token={api_key}"
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return json.loads(response.text)
        
        except Timeout:
            print(f"Warning: Timeout fetching guild data for guild ID {guild_id}, attempt {attempt}/{max_retries}")
            if attempt == max_retries:
                print(f"Error: Max retries reached for guild ID {guild_id}: Timeout")
                return None
            time.sleep(backoff_factor * (2 ** (attempt - 1)))  # Exponential backoff
        
        except ConnectionError:
            print(f"Warning: Connection error for guild ID {guild_id}, attempt {attempt}/{max_retries}")
            if attempt == max_retries:
                print(f"Error: Max retries reached for guild ID {guild_id}: Connection error")
                return None
            time.sleep(backoff_factor * (2 ** (attempt - 1)))
        
        except HTTPError as e:
            status_code = e.response.status_code
            if status_code == 429:  # Rate limit exceeded
                print(f"Warning: Rate limit exceeded for guild ID {guild_id}, attempt {attempt}/{max_retries}")
                retry_after = int(e.response.headers.get('Retry-After', 5))
                time.sleep(retry_after)
            elif status_code >= 500:  # Server errors
                print(f"Warning: Server error {status_code} for guild ID {guild_id}, attempt {attempt}/{max_retries}")
                if attempt == max_retries:
                    print(f"Error: Max retries reached for guild ID {guild_id}: Server error {status_code}")
                    return None
                time.sleep(backoff_factor * (2 ** (attempt - 1)))
            else:
                print(f"Error: HTTP error {status_code} for guild ID {guild_id}: {str(e)}")
                return None
        
        except RequestException as e:
            print(f"Error: Unexpected error for guild ID {guild_id}: {str(e)}")
            return None
    
    return None

def find_member(guild_data: list, member_account: str) -> str:
	"""
	Finds a member in the guild data and returns their rank. If the member is not found, it returns "--==Non Member==--".

	Args:
		guild_data (list): A list of dictionaries containing guild data.
		member_account (str): The name of the account to find.

	Returns:
		str: The rank of the member if found, otherwise "--==Non Member==--".
	"""
	status = "--==Non Member==--"
	for guild_member in guild_data:
		if guild_member["name"] == member_account:
			status = guild_member["rank"]
	return status

def get_illusion_of_life_data(players: dict, durationMS: int) -> None:
	"""
	Collects data about the "Illusion of Life" skill used by Mesmers and their specializations.

	Args:
		players (dict): A dictionary containing the player data.
		durationMS (int): The duration of the encounter in milliseconds.

	Returns:
		None
	"""
	for player in players:
		playerName = player['name']
		playerProf = player['profession']

		if 'buffUptimes' in player:
			for item in player['buffUptimes']:
				if item['id'] in [10244, 10346]:
					for caster in item['buffData'][0]['generated']:
						caster_name = caster
						caster_generated = item['buffData'][0]['generated'][caster]
						caster_wasted = item['buffData'][0]['wasted'][caster_name]
					
						if caster_name not in IOL_revive:
							IOL_revive[caster_name] = {
								'prof': "",
								'casts': 0,
								'hits': 0,
								'generated': 0,
								'wasted': 0,
								'gen_plus_wasted':0
							}
						generated = ((caster_generated/100)*durationMS)/1000
						wasted = ((caster_wasted/100)*durationMS)/1000
						total_gen_wasted = round((generated+wasted), 0)
						hits = math.ceil(total_gen_wasted/15)
						IOL_revive[caster_name]['hits'] = IOL_revive[caster_name].get('hits',0) + hits
						IOL_revive[caster_name]['generated'] = IOL_revive[caster_name].get('generated',0) + round(generated,0)
						IOL_revive[caster_name]['wasted'] = IOL_revive[caster_name].get('wasted',0) + round(wasted,0)
						IOL_revive[caster_name]['gen_plus_wasted'] = IOL_revive[caster_name].get('gen_plus_wasted',0) + round(total_gen_wasted,0)
			
		if 'rotation' in player and playerProf in ['Mesmer', 'Mirage', 'Chronomancer','Virtuoso']:
			
			for item in player['rotation']:
				if item['id'] in [10244, 10346]:
					rotationCasts = len(item['skills'])

					if playerName not in IOL_revive:
						IOL_revive[playerName] = {}
					IOL_revive[playerName]['casts'] = IOL_revive[playerName].get('casts', 0) + rotationCasts
					IOL_revive[playerName]['prof'] = playerProf


def get_health_percent_data(player, name_prof, name, prof, group) -> None:

	BUCKET_SIZE = 10

	def health_bucket(h):
		# Clamp 100% into the 90–100 bucket
		bucket_start = int(h // BUCKET_SIZE) * BUCKET_SIZE
		bucket_start = min(bucket_start, 90)
		bucket_end = bucket_start + BUCKET_SIZE

		return f"{bucket_end}-{bucket_start}"

	def accumulate_health_time(data):
		"""
		data: list of [timeMS, healthPercent]
		returns: dict { "bucket_range": time_ms }
		"""
		bucket_time = defaultdict(int)

		for (t1, h1), (t2, _) in zip(data[:-1], data[1:]):
			dt = t2 - t1
			if dt <= 0:
				continue

			bucket = health_bucket(h1)
			bucket_time[bucket] += dt

		return dict(bucket_time)

	if 'healthPercents' in player:
		data = player['healthPercents']
		if name_prof not in health_data:
			health_data[name_prof] = {
				"Name": name,
				"Profession": prof,
				"Group": group,
				"Fights": 0,
				"Health_Buckets": {}
				}
		health_data[name_prof]["Fights"] += 1
		health_data[name_prof]["Group"] = group
		player_health_data = accumulate_health_time(data)

		for item in player_health_data:
			if item not in health_data[name_prof]['Health_Buckets']:
				health_data[name_prof]['Health_Buckets'][item]=player_health_data[item]
			else:
				health_data[name_prof]['Health_Buckets'][item]+=player_health_data[item]


def parse_file(file_path, fight_num, guild_data, fight_data_charts, blacklist):
	"""
	Parses a single log file and stores the data in a global top_stats dictionary.

	Arguments:
	file_path: The path to the log file to be parsed.
	fight_num: The fight number of the log file. Used to distinguish between different
		fights in the same log.
	guild_data: A dictionary of guild data, used to determine the guild status of
		each player.
	fight_data_charts: A boolean indicating whether to store detailed fight data
		for each player.

	Side effects:
	Modifies the global top_stats dictionary.
	"""
	json_stats = config.json_stats

	if file_path.endswith('.gz'):
		with gzip.open(file_path, mode="r") as f:
			json_data = json.loads(f.read().decode('utf-8'))
	else:
		json_datafile = open(file_path, encoding='utf-8')
		json_data = json.load(json_datafile)

	if 'usedExtensions' not in json_data:
		players_running_healing_addon = []
	else:
		extensions = json_data['usedExtensions']
		for extension in extensions:
			if extension['name'] == "Healing Stats":
				players_running_healing_addon = extension['runningExtension']
	
	players = json_data['players']
	targets = json_data['targets']
	skill_map = json_data['skillMap']
	buff_map = json_data['buffMap']
	if 'mechanics' in json_data:
		mechanics_map = json_data['mechanics']
	else:
		mechanics_map = {}
	damage_mod_map = json_data.get('damageModMap', {})
	personal_buffs = json_data.get('personalBuffs', {})
	personal_damage_mods = json_data.get('personalDamageMods', {})
	fight_date, fight_end, fight_utc = json_data['timeEnd'].split(' ')
	if 'combatReplayMetaData' in json_data:
		inches_to_pixel = json_data['combatReplayMetaData']['inchToPixel']
		polling_rate = json_data['combatReplayMetaData']['pollingRate']
	upload_link = json_data['uploadLinks'][0]
	fight_duration = json_data['duration']
	fight_duration_ms = json_data['durationMS']
	fight_name = json_data['fightName']
	fight_link = json_data['uploadLinks'][0]
	dist_to_com = []
	player_in_combat = 0

	enemy_engaged_count = sum(1 for enemy in targets if not enemy['isFake'])

	log_type, fight_name = determine_log_type_and_extract_fight_name(fight_name)

	calculate_dps_stats(json_data, blacklist)

	top_stats['overall']['last_fight'] = f"{fight_date}-{fight_end}"
	#Initialize fight_num stats
	top_stats['fight'][fight_num] = {
		'log_type': log_type,
		'fight_name': fight_name,
		'fight_link': fight_link,
		'fight_date': fight_date,
		'fight_end': fight_end,
		'fight_utc': fight_utc,
		'fight_duration': fight_duration,
		'fight_durationMS': fight_duration_ms,
		'commander': "",
		'squad_count': 0,
		'non_squad_count': 0,
		'enemy_downed': 0,
		'enemy_killed': 0,
		'enemy_count': 0,
		'enemy_Red': 0,
		'enemy_Green': 0,
		'enemy_Blue': 0,
		'enemy_Unk': 0,
		'rallies': 0,
	}

	for stat_cat in json_stats:
		top_stats['fight'][fight_num].setdefault(stat_cat, {})
		top_stats['overall'].setdefault(stat_cat, {})	

	#get commander data
	commander_tag_positions, dead_tag_mark, dead_tag = get_commander_tag_data(json_data)

	#collect player counts and parties
	get_parties_by_fight(fight_num, players, blacklist)

	get_enemy_downed_and_killed_by_fight(fight_num, targets, players, log_type)

	#collect enemy counts and team colors
	get_enemies_by_fight(fight_num, targets)

	#collect buff data
	get_buffs_data(buff_map)

	#collect skill data
	get_skills_data(skill_map) 

	#collect damage mods data
	get_personal_mod_data(personal_damage_mods)
	get_damage_mods_data(damage_mod_map, personal_damage_mod_data)

	#collect personal buff data
	get_personal_buff_data(personal_buffs)

	#collect mechanics data
	get_mechanics_by_fight(fight_num, mechanics_map, players, log_type)

	#top_stats['fight'][fight_num]['rallies'] = get_rally_mechanics_by_fight(mechanics_map)
	top_stats['fight'][fight_num]['rallies'] = get_rally_mechanics_by_fight(mechanics_map, players)
	top_stats['overall']['rallies'] = top_stats['overall'].get('rallies', 0) + top_stats['fight'][fight_num]['rallies']

	#collect damage mitigation data
	get_damage_mitigation_data(fight_num, players, targets, skill_map, buff_map)

	get_illusion_of_life_data(players, fight_duration_ms)
	
	#process each player in the fight
	for player in players:
		# skip players not in squad
		if player['notInSquad']:
			continue
		name = player['name']
		profession = player['profession']
		account = get_player_account(player)

		#skip blacklisted accounts
		if account in blacklist:
			continue

		group = player['group']
		group_count = len(top_stats['parties_by_fight'][fight_num][group])
		squad_count = top_stats['fight'][fight_num]['squad_count']

		name_prof = name + "|" + profession + "|" + account
		tag = player['hasCommanderTag']
		if tag:	#Commander Tracking
			top_stats['fight'][fight_num]['commander'] = name_prof

		combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
		if not combat_time:
			continue
		
		if 'teamID' in player:
			team = player['teamID']
		else:
			team = None
		active_time = player['activeTimes'][0]

		if name in players_running_healing_addon:
			if name_prof not in top_stats['players_running_healing_addon']:
				top_stats['players_running_healing_addon'].append(name_prof)

		if 'guildID' in player:
			guild_id = player['guildID']
		else:
			guild_id = None

		if guild_data:
			guild_status = find_member(guild_data, account)
		else:
			guild_status = ""

		if name_prof not in top_stats['player']:
			print('Found new player: '+name_prof)
			top_stats['player'][name_prof] = {
				'name': name,
				'profession': profession,
				'account': account,
				"guild_status": guild_status,
				'team': team,
				'guild': guild_id,
				'num_fights': 0,
				'enemy_engaged_count': 0,
				'minions': {},
			}

		get_health_percent_data(player, name_prof, name, profession, group)

		# store last party the player was a member
		top_stats['player'][name_prof]['last_party'] = group
		if fight_data_charts:
			get_fight_data(player, fight_num)

			check_burst1S_high_score(fight_data, player, fight_num)

		get_firebrand_pages(player, name_prof, name, account,fight_duration_ms)

		get_player_fight_dps(player["dpsTargets"], name, profession, account, fight_num, (fight_duration_ms/1000))
		get_player_stats_targets(player["statsTargets"], name, profession, account, fight_num, (fight_duration_ms/1000))

		get_minions_by_player(player, name, profession)

		if player["profession"] in ["Mesmer", "Chronomancer", "Mirage"]:
			determine_clone_usage(player, skill_map, mesmer_shatter_skills)

		get_player_death_on_tag(player, commander_tag_positions, dead_tag_mark, dead_tag, inches_to_pixel, polling_rate)

		# Cumulative group and squad supported counts
		top_stats['player'][name_prof]['num_fights'] = top_stats['player'][name_prof].get('num_fights', 0) + 1
		top_stats['player'][name_prof]['group_supported'] = top_stats['player'][name_prof].get('group_supported', 0) + group_count
		top_stats['player'][name_prof]['squad_supported'] = top_stats['player'][name_prof].get('squad_supported', 0) + squad_count
		top_stats['player'][name_prof]['enemy_engaged_count'] = top_stats['player'][name_prof].get('enemy_engaged_count', 0) + enemy_engaged_count

		#Cumulative fight time  for player, fight and overall    
		top_stats['player'][name_prof]['fight_time'] = top_stats['player'][name_prof].get('fight_time', 0) + fight_duration_ms
		top_stats['fight'][fight_num]['fight_time'] = top_stats['fight'][fight_num].get('fight_time', 0) + fight_duration_ms
		top_stats['overall']['fight_time'] = top_stats['overall'].get('fight_time', 0) + fight_duration_ms
		if group not in top_stats['overall']['group_data']:
			top_stats['overall']['group_data'][group] = {
				'fight_count': 0,
			}
		top_stats['overall']['group_data'][group]['fight_time'] = top_stats['overall']['group_data'][group].get('fight_time', 0) + fight_duration_ms

		#Cumulative active time  for player, fight and overall
		top_stats['player'][name_prof]['active_time'] = top_stats['player'][name_prof].get('active_time', 0) + active_time
		top_stats['fight'][fight_num]['active_time'] = top_stats['fight'][fight_num].get('active_time', 0) + active_time
		top_stats['overall']['active_time'] = top_stats['overall'].get('active_time', 0) + active_time

		for stat_cat in json_stats:

			# Initialize dictionaries for player, fight, and overall stats if they don't exist
			top_stats['player'].setdefault(name_prof, {}).setdefault(stat_cat, {})
			#top_stats['fight'][fight_num].setdefault(stat_cat, {})
			#top_stats['overall'].setdefault(stat_cat, {})
			
			# format: player[stat_category][0][stat]
			if stat_cat in ['defenses', 'support', 'statsAll']:
				get_stat_by_key(fight_num, player, stat_cat, name_prof)
				if stat_cat in ['defenses']:
					get_defense_hits_and_glances(fight_num, player, stat_cat, name_prof)

			# format: player[stat_cat][target][0][skill][stat]
			if stat_cat in ['targetDamageDist']:
				get_stat_by_target_and_skill(fight_num, player, stat_cat, name_prof)

			# format: player[stat_cat][target[0][stat:value]
			if stat_cat in ['dpsTargets', 'statsTargets']:
				get_stat_by_target(fight_num, player, stat_cat, name_prof)

			# format: player[stat_cat][0][skill][stat:value]
			if stat_cat in ['totalDamageTaken']:
				get_stat_by_skill(fight_num, player, stat_cat, name_prof)

			# format: player[stat_cat][buff][buffData][0][stat:value]
			if stat_cat in ['buffUptimes', 'buffUptimesActive']:
				get_buff_uptimes(fight_num, player, group, stat_cat, name_prof, fight_duration_ms, active_time)

			# format: player[stat_category][buff][buffData][0][generation]
			if stat_cat in ['squadBuffs', 'groupBuffs', 'selfBuffs']:
				get_buff_generation(fight_num, player, stat_cat, name_prof, fight_duration_ms, buff_data, squad_count, group_count)
			if stat_cat in ['squadBuffsActive', 'groupBuffsActive', 'selfBuffsActive']:                
				get_buff_generation(fight_num, player, stat_cat, name_prof, active_time, buff_data, squad_count, group_count)

			# format: player[stat_category][skill][skills][casts]
			if stat_cat == 'rotation' and 'rotation' in player:
				get_skill_cast_by_prof_role(active_time, player, stat_cat, name_prof)

			if stat_cat in ['extHealingStats', 'extBarrierStats'] and name in players_running_healing_addon:
				get_healStats_data(fight_num, player, players, stat_cat, name_prof, fight_duration_ms)
				if stat_cat == 'extHealingStats':
					get_healing_skill_data(player, stat_cat, name_prof)
				else:
					get_barrier_skill_data(player, stat_cat, name_prof)

			if stat_cat in ['targetBuffs']:
				get_target_buff_data(fight_num, player, targets, stat_cat, name_prof)

			if stat_cat in ['damageModifiers']:
				get_damage_mod_by_player(fight_num, player, name_prof)
