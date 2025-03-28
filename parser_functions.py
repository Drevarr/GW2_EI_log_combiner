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

# Top stats dictionary to store combined log data
top_stats = config.top_stats

team_colors = config.team_colors

mesmer_shatter_skills = config.mesmer_shatter_skills
mesmer_clone_usage = {}
enemy_avg_damage_per_skill = {}
player_damage_mitigation = {}

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
	active_clones = {}
	name_prof = f"{player['name']}_{player['profession']}"
	if name_prof not in mesmer_clone_usage:
		mesmer_clone_usage[name_prof] = {}
	if "activeClones" in player:
		for timestamp in player['activeClones']:
			active_clones[timestamp[0]] = timestamp[1]
	if "rotation" in player:
		for skill in player["rotation"]:
			skill_id = f"s{skill['id']}"
			if skill_map[skill_id]['name'] in mesmer_shatter_skills:
				skill_name = skill_map[skill_id]['name']

				if skill_name not in mesmer_clone_usage[name_prof]:
					mesmer_clone_usage[name_prof][skill_name] = {}

				for item in skill['skills']:
					cast_time = item['castTime']
					for key, value in reversed(list(active_clones.items())):
						if key <= cast_time:
							mesmer_clone_usage[name_prof][skill_name][value] = mesmer_clone_usage[name_prof][skill_name].get(value, 0) + value
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
    temp = min(dict.values())
    res = []
    for key, value in dict.items():
        if(value == temp):
            res.append(key)
            res.append(value)
    return res

def find_smallest_value(my_dict):
    if not my_dict:
        return "Dictionary is empty"
    
    min_key = min(my_dict, key=my_dict.get)
    return min_key

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

	if len(high_scores[stat_name]) < 5:
		high_scores[stat_name][key] = value
		return

	lowest_key = min(high_scores[stat_name], key=high_scores[stat_name].get)
	lowest_value = high_scores[stat_name][lowest_key]

	if value >= lowest_value and key not in high_scores[stat_name]:
		del high_scores[stat_name][lowest_key]
		high_scores[stat_name][key] = value
	#elif value > lowest_value and key in high_scores[stat_name]:
	#	high_scores[stat_name][key] = value

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

def calculate_defensive_hits_and_glances(player_data: dict) -> dict:
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
			commander_name = f"{player['name']}|{player['profession']}"
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


def get_player_death_on_tag(player, commander_tag_positions, dead_tag_mark, dead_tag, inch_to_pixel, polling_rate):
		name_prof = player['name'] + "|" + player['profession'] 
		if name_prof not in death_on_tag:
			death_on_tag[name_prof] = {
			"name": player['name'],
			"profession": player['profession'],
			"distToTag": [],
			"On_Tag": 0,
			"Off_Tag": 0,
			"Run_Back": 0,
			"After_Tag_Death": 0,
			"Total": 0,
			"Ranges": [],
			}
			
		player_dist_to_tag = round(player['statsAll'][0]['distToCom'])

		if player['combatReplayData']['dead'] and player['combatReplayData']['down'] and commander_tag_positions:
			player_deaths = dict(player['combatReplayData']['dead'])
			player_downs = dict(player['combatReplayData']['down'])

			for death_key, death_value in player_deaths.items():
				if death_key < 0:  # Handle death on the field before main squad combat log starts
					continue

				position_mark = max(1, math.floor(death_key / polling_rate))
				player_positions = player['combatReplayData']['positions']
				
				for down_key, down_value in player_downs.items():
					if death_key == down_value:
						# process data for downKey
						x1, y1 = player_positions[position_mark]
						#y1 = player_positions[position_mark][1]
						x2, y2 = commander_tag_positions[position_mark]
						#y2 = commander_tag_positions[position_mark][1]
						death_distance = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
						death_range = round(death_distance / inch_to_pixel)
						death_on_tag[name_prof]["Total"] += 1

						if int(down_key) > int(dead_tag_mark) and dead_tag:
							death_on_tag[name_prof]["After_Tag_Death"] += 1

							# Calc Avg distance through dead tag final mark
							player_dead_poll = max(1, int(dead_tag_mark / polling_rate))
							player_distances = []
							for position, tag_position in zip(player_positions[:player_dead_poll], commander_tag_positions[:player_dead_poll]):
								delta_x = position[0] - tag_position[0]
								delta_y = position[1] - tag_position[1]
								player_distances.append(math.sqrt(delta_x * delta_x + delta_y * delta_y))

							player_dist_to_tag = round((sum(player_distances) / len(player_distances)) / inch_to_pixel)
						else:
							player_dead_poll = position_mark
							player_positions = player['combatReplayData']['positions']
							player_distances = []
							for position, tag_position in zip(player_positions[:player_dead_poll], commander_tag_positions[:player_dead_poll]):
								delta_x = position[0] - tag_position[0]
								delta_y = position[1] - tag_position[1]
								player_distances.append(math.sqrt(delta_x * delta_x + delta_y * delta_y))
							player_dist_to_tag = round((sum(player_distances) / len(player_distances)) / inch_to_pixel)

						if death_range <= On_Tag:
							death_on_tag[name_prof]["On_Tag"] += 1

						if death_range > On_Tag and death_range <= Run_Back:
							death_on_tag[name_prof]["Off_Tag"] += 1
							death_on_tag[name_prof]["Ranges"].append(death_range)

						if death_range > Run_Back:
							death_on_tag[name_prof]["Run_Back"] += 1

		if player_dist_to_tag <= Run_Back:
			death_on_tag[name_prof]["distToTag"].append(player_dist_to_tag)

def get_player_fight_dps(dpsTargets: dict, name: str, profession: str, fight_num: int, fight_time: int) -> None:
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
		"{{"+profession+"}}"+name+"-"+str(fight_num)+" | DPS",
		target_damage
		)

def get_combat_start_from_player_json(initial_time, player_json):
	start_combat = -1
	# TODO check healthPercents exists
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
	start_combat = get_combat_start_from_player_json(0, player_json)
	if 'combatReplayData' not in player_json:
		print("WARNING: combatReplayData not in json, using activeTimes as time in combat")
		return [start_combat, player_json.get('activeTimes', 0)]
	replay = player_json['combatReplayData']
	if 'dead' not in replay:
		return [start_combat, player_json.get('activeTimes', 0)]

	breakpoints = []
	playerDeaths = dict(replay['dead'])
	playerDowns = dict(replay['down'])
	for deathKey, deathValue in playerDeaths.items():
		for downKey, downValue in playerDowns.items():
			if deathKey == downValue:
				if start_combat != -1:
					breakpoints.append([start_combat, deathKey])
				start_combat = get_combat_start_from_player_json(deathValue + 1000, player_json)
				break
	end_combat = (len(player_json['damage1S'][0]))*1000
	if start_combat != -1:
		breakpoints.append([start_combat, end_combat])

	return breakpoints


def sum_breakpoints(breakpoints):
	combat_time = 0
	for [start, end] in breakpoints:
		combat_time += end - start
	return combat_time

def calculate_dps_stats(fight_json):

	fight_ticks = len(fight_json['players'][0]["damage1S"][0])
	duration = round(fight_json['durationMS']/1000)

	damage_ps = {}
	for index, target in enumerate(fight_json['targets']):
		if 'enemyPlayer' in target:	#and target['enemyPlayer'] == True
			for player in fight_json['players']:
				if player['notInSquad']:
					continue
				player_prof_name = player['profession'] + " " + player['name']
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
				player_prof_name = player['profession'] + " " + player['name']
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
		player_prof_name = player['profession'] + " " + player['name']
		combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
		if combat_time:
			if player_prof_name not in DPSStats:
				DPSStats[player_prof_name] = {
					"account": player["account"],
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

	# Chunk damage: Damage done within X seconds of target down
	for index, target in enumerate(fight_json['targets']):
		if 'enemyPlayer' in target and target['enemyPlayer'] == True and 'combatReplayData' in target and len(target['combatReplayData']['down']):
			for chunk_damage_seconds in range(1, CHUNK_DAMAGE_SECONDS):
				targetDowns = dict(target['combatReplayData']['down'])
				for targetDownsIndex, (downKey, downValue) in enumerate(targetDowns.items()):
					downIndex = math.ceil(downKey / 1000)
					startIndex = max(0, math.ceil(downKey / 1000) - chunk_damage_seconds)
					if targetDownsIndex > 0:
						lastDownKey, lastDownValue = list(targetDowns.items())[targetDownsIndex - 1]
						lastDownIndex = math.ceil(lastDownKey / 1000)
						if lastDownIndex == downIndex:
							# Probably an ele in mist form
							continue
						startIndex = max(startIndex, lastDownIndex)

					squad_damage_on_target = 0
					for player in fight_json['players']:
						if player['notInSquad']:
							continue
						combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
						if combat_time:
							player_prof_name = player['profession'] + " " + player['name']	
							damage_on_target = player["targetDamage1S"][index][0]
							player_damage = damage_on_target[downIndex] - damage_on_target[startIndex]

							DPSStats[player_prof_name]["chunkDamage"][chunk_damage_seconds] += player_damage
							squad_damage_on_target += player_damage

							if chunk_damage_seconds == 5:
								for i in range(startIndex, downIndex):
									ch5_ca_damage_1s[player_prof_name][i] += damage_on_target[i + 1] - damage_on_target[i]

					for player in fight_json['players']:
						if player['notInSquad']:
							continue
						combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
						if combat_time:
							player_prof_name = player['profession'] + " " + player['name']

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
							combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
							if combat_time:
								player_prof_name = player['profession'] + " " + player['name']
								damage_on_target = player["targetDamage1S"][index][0]
								carrion_damage = damage_on_target[dmgEnd] - damage_on_target[dmgStart]

								DPSStats[player_prof_name]["carrionDamage"] += carrion_damage
								total_carrion_damage += carrion_damage

								for i in range(dmgStart, dmgEnd):
									ch5_ca_damage_1s[player_prof_name][i] += damage_on_target[i + 1] - damage_on_target[i]

						for player in fight_json['players']:
							if player['notInSquad']:
								continue
							combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
							if combat_time:
								player_prof_name = player['profession'] + " " + player['name']
								DPSStats[player_prof_name]["carrionDamageTotal"] += total_carrion_damage

	# Burst damage: max damage done in n seconds
	for player in fight_json['players']:
		if player['notInSquad']:
			continue
		combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
		if combat_time:
			player_prof_name = player['profession'] + " " + player['name']
			player_damage = damage_ps[player_prof_name]
			for i in range(1, CHUNK_DAMAGE_SECONDS):
				for fight_tick in range(i, fight_ticks):
					dmg = player_damage[fight_tick] - player_damage[fight_tick - i]
					DPSStats[player_prof_name]["burstDamage"][i] = max(dmg, DPSStats[player_prof_name]["burstDamage"][i])

	# Ch5Ca Burst damage: max damage done in n seconds
	for player in fight_json['players']:
		if player['notInSquad']:
			continue
		combat_time = round(sum_breakpoints(get_combat_time_breakpoints(player)) / 1000)
		if combat_time:
			player_prof_name = player['profession'] + " " + player['name']
			player_damage_ps = ch5_ca_damage_1s[player_prof_name]
			player_damage = [0] * len(player_damage_ps)
			player_damage[0] = player_damage_ps[0]
			for i in range(1, len(player_damage)):
				player_damage[i] = player_damage[i - 1] + player_damage_ps[i]
			for i in range(1, CHUNK_DAMAGE_SECONDS):
				for fight_tick in range(i, fight_ticks):
					dmg = player_damage[fight_tick] - player_damage[fight_tick - i]
					DPSStats[player_prof_name]["ch5CaBurstDamage"][i] = max(dmg, DPSStats[player_prof_name]["ch5CaBurstDamage"][i])

def get_player_stats_targets(statsTargets: dict, name: str, profession: str, fight_num: int, fight_time: int) -> None:
	#fight_stat_value= 0
	fight_stats = ["killed", "downed", "downContribution", "appliedCrowdControl"]
	for stat in fight_stats:
		fight_stat_value= 0
		for target in statsTargets:
			if target[0] and stat in target[0]:
				fight_stat_value += target[0][stat]

		fight_stat_value = round(fight_stat_value / fight_time, 3)

		update_high_score(f"statTarget_{stat}", "{{"+profession+"}}"+name+"-"+str(fight_num)+" | "+stat, fight_stat_value)	


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
		if 'icon' in buff_map[buff]:
			icon = buff_map[buff]['icon']
		else:
			icon = "unknown.png"
		if buff_id not in buff_data:
			buff_data[buff_id] = {
				'name': name,
				'stacking': stacking,
				'icon': icon
			}
		

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
		if 'icon' in skill_map[skill]:
			icon = skill_map[skill]['icon']
		else:
			icon = "unknown.png"
		if skill_id not in skill_data:
			skill_data[skill_id] = {
				'name': name,
				'auto': auto_attack,
				'icon': icon
			}


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
	Populate the personal_buff_data dictionary with buffs from personal_buffs.

	Args:
		personal_buffs (dict): A dictionary where keys are professions and values are lists of buff IDs.
	"""
	for profession, buffs in personal_buffs.items():
		if profession not in personal_buff_data:
			personal_buff_data[profession] = []
		for buff_id in buffs:
			# Convert the buff ID to the format used in buff_data
			buff_id = "b" + str(buff_id)
			if buff_id not in personal_buff_data[profession]:
				personal_buff_data[profession].append(buff_id)
				# Add the buff to the total list
				personal_buff_data['total'].append(buff_id)


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
				team = "enemy_" + team_colors[team]
			else:
				team = "enemy_Unk"
			
			if team not in top_stats["fight"][fight_num]:
				# Create a new team if it doesn't exist
				top_stats["fight"][fight_num][team] = 0

			if enemy_prof not in top_stats["enemies_by_fight"][fight_num]:
				top_stats["enemies_by_fight"][fight_num][enemy_prof] = 0
			top_stats["enemies_by_fight"][fight_num][enemy_prof] += 1

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
	for stat, value in player[stat_category][0].items():
		if stat == 'boonStripsTime' and value > 999999:
			value = 0	
		if stat in config.high_scores:
			active_time_seconds = player['activeTimes'][0] / 1000
			high_score_value = round(value / active_time_seconds, 3) if active_time_seconds > 0 else 0
			update_high_score(f"{stat_category}_{stat}", "{{"+player["profession"]+"}}"+player["name"]+"-"+str(fight_num)+" | "+stat, high_score_value)
		top_stats['player'][name_prof][stat_category][stat] = top_stats['player'][name_prof][stat_category].get(stat, 0) + value
		top_stats['fight'][fight_num][stat_category][stat] = top_stats['fight'][fight_num][stat_category].get(stat, 0) + value
		top_stats['overall'][stat_category][stat] = top_stats['overall'][stat_category].get(stat, 0) + value

		commander_tag = player['hasCommanderTag']
		if commander_tag:
			commander_name = f"{player['name']}|{player['profession']}"
			if commander_name not in commander_summary_data:
				commander_summary_data[commander_name] = {stat_category: {}}
			elif stat_category not in commander_summary_data[commander_name]:
				commander_summary_data[commander_name][stat_category] = {}
			commander_summary_data[commander_name][stat_category][stat] = commander_summary_data[commander_name][stat_category].get(stat, 0) + value

def get_defense_hits_and_glances(fight_num: int, player: dict, stat_category: str, name_prof: str) -> None:
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
						update_high_score(f"statTarget_{stat}", "{{"+player["profession"]+"}}"+player["name"]+"-"+str(fight_num)+"-"+str(index)+" | "+str(skill_id), value)
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
					if stat == 'max':
						update_high_score(f"{stat_category}_{stat}", "{{"+player["profession"]+"}}"+player["name"]+"-"+str(fight_num)+" | "+str(skill_id), value)	
					top_stats['player'][name_prof][stat_category][skill_id][stat] = top_stats['player'][name_prof][stat_category][skill_id].get(stat, 0) + value
					top_stats['fight'][fight_num][stat_category][skill_id][stat] = top_stats['fight'][fight_num][stat_category][skill_id].get(stat, 0) + value
					top_stats['overall'][stat_category][skill_id][stat] = top_stats['overall'][stat_category][skill_id].get(stat, 0) + value

					if player['hasCommanderTag']:
						commander_name = f"{player['name']}|{player['profession']}"
						if skill_id not in commander_summary_data[commander_name][stat_category]:
							commander_summary_data[commander_name][stat_category][skill_id] = {}
						if stat not in commander_summary_data[commander_name][stat_category][skill_id]:
							commander_summary_data[commander_name][stat_category][skill_id][stat] = 0

						commander_summary_data[commander_name][stat_category][skill_id][stat] += value
						#commander_summary_data[name_prof][stat_category][skill_id].get(stat, 0) + value	 


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
					conditionTime += buffTime

					#if buff_id not in top_stats['player'][name_prof][stat_category]:
					if buff_id not in top_stats['player'][name_prof][stat_category]:
						top_stats['player'][name_prof][stat_category][buff_id] = {
							'uptime_ms': 0,
							'applied_counts': 0,
						}
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

					top_stats['fight'][fight_num][stat_category][buff_id]['uptime_ms'] += conditionTime
					top_stats['fight'][fight_num][stat_category][buff_id]['applied_counts'] += appliedCounts

					top_stats['overall'][stat_category][buff_id]['uptime_ms'] += conditionTime
					top_stats['overall'][stat_category][buff_id]['applied_counts'] += appliedCounts


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

		top_stats['fight'][fight_num][stat_category][buff_id]['generation'] = top_stats['fight'][fight_num][stat_category][buff_id].get('generation', 0) + buff_generation
		top_stats['fight'][fight_num][stat_category][buff_id]['wasted'] = top_stats['fight'][fight_num][stat_category][buff_id].get('wasted', 0) + buff_wasted

		top_stats['overall'][stat_category][buff_id]['generation'] = top_stats['overall'][stat_category][buff_id].get('generation', 0) + buff_generation
		top_stats['overall'][stat_category][buff_id]['wasted'] = top_stats['overall'][stat_category][buff_id].get('wasted', 0) + buff_wasted


def get_skill_cast_by_prof_role(active_time: int, player: dict, stat_category: str, name_prof: str) -> None:
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
			'account': player['account'],
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
					commander_name = f"{heal_target_name}|{players[index]['profession']}"

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
		update_high_score(f"{stat_category}_Healing", "{{"+player["profession"]+"}}"+player["name"]+"-"+str(fight_num)+" | Healing", round(fight_healing/(fight_time/1000), 2))	

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
					commander_name = f"{barrier_target_name}|{players[index]['profession']}"

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
		update_high_score(f"{stat_category}_Barrier", "{{"+player["profession"]+"}}"+player["name"]+"-"+str(fight_num)+" | Barrier", round(fight_barrier/(fight_time/1000), 2))


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

				if commander_tag:
					commander_name = f"{player['name']}|{player['profession']}"
					if mod_id == 'd-58':
						commander_summary_data[commander_name]['prot_mods']['hitCount'] += mod_hit_count
						commander_summary_data[commander_name]['prot_mods']['totalHitCount'] += mod_total_hit_count
						commander_summary_data[commander_name]['prot_mods']['damageGain'] += mod_damage_gain
						commander_summary_data[commander_name]['prot_mods']['totalDamage'] += mod_total_damage


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

def get_mechanics_by_fight(fight_number, mechanics_map, players, log_type):
	"""Collects mechanics data from a fight and stores it in a dictionary."""
	if log_type == "PVE":
		if fight_number not in mechanics:
			mechanics[fight_number] = {
				"player_list": [],
				"enemy_list": [],
				}
	else:
		fight_number = "WVW"
		if fight_number not in mechanics:
			mechanics[fight_number] = {
				"player_list": [],
				"enemy_list": [],
				}

	for mechanic_data in mechanics_map:
		mechanic_name = mechanic_data['name']
		description = mechanic_data['description']
		is_eligible = mechanic_data['isAchievementEligibility']

		if mechanic_name not in mechanics[fight_number]:
			mechanics[fight_number][mechanic_name] = {
				'tip': description,
				'eligibile': is_eligible,
				'data': {},
				'enemy_data': {}
			}

		for data_item in mechanic_data['mechanicsData']:
			actor = data_item['actor']
			prof_name = None
			for player in players:
				if player['name'] == actor:
					prof_name = "{{" + player['profession'] + "}} " + player['name']
			if prof_name:
				if prof_name not in mechanics[fight_number]['player_list']:
					mechanics[fight_number]['player_list'].append(prof_name)
				if prof_name not in mechanics[fight_number][mechanic_name]['data']:
					mechanics[fight_number][mechanic_name]['data'][prof_name] = 1
				else:
					mechanics[fight_number][mechanic_name]['data'][prof_name] += 1
			else:
				if actor not in mechanics[fight_number]['enemy_list']:
					mechanics[fight_number]['enemy_list'].append(actor)
				if actor not in mechanics[fight_number][mechanic_name]['enemy_data']:
					mechanics[fight_number][mechanic_name]['enemy_data'][actor] = 1
				else:
					mechanics[fight_number][mechanic_name]['enemy_data'][actor] += 1

def get_damage_mitigation_data(fight_num: int, players: dict, targets: dict, skill_data: dict, buff_data: dict) -> None:
	"""Collects damage mitigation data from a fight and stores it in a dictionary."""
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
		name_prof = f"{player['name']}|{player['profession']}"
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
					player_damage_mitigation[name_prof][skill_name]['avg_dmg'] = player_damage_mitigation[name_prof][skill_name]['total_dmg'] / player_damage_mitigation[name_prof][skill_name]['total_hits']
					player_damage_mitigation[name_prof][skill_name]['min_dmg'] = sum(enemy_avg_damage_per_skill[skill_name]['min']) / len(enemy_avg_damage_per_skill[skill_name]['min'])
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
	if "minions" in player_data:
		if profession not in minions:
			minions[profession] = {"player": {}, "pets_list": []}

		for minion in player_data["minions"]:
			minion_name = minion["name"].replace("Juvenile ", "").replace("UNKNOWN", "Unknown")
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
			else:
				minions[profession]["player"][player_name][minion_name] += minion_count


def fetch_guild_data(guild_id: str, api_key: str) -> dict:
	"""
	Fetches the guild data from the Guild Wars 2 API.

	Args:
		guild_id: The ID of the guild to fetch data for.
		api_key: The API key to use for the request.

	Returns:
		A dictionary containing the guild data if the request is successful, otherwise None.
	"""
	url = f"https://api.guildwars2.com/v2/guild/{guild_id}/members?access_token={api_key}"
	try:
		response = requests.get(url, timeout=5)
		response.raise_for_status()
		return json.loads(response.text)
	except requests.exceptions.RequestException:
		return None

def find_member(guild_data: list, member_account: str) -> str:
	for guild_member in guild_data:
		if guild_member["name"] == member_account:
			return guild_member["rank"]
	return "--==Non Member==--"


def parse_file(file_path, fight_num, guild_data):
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

	calculate_dps_stats(json_data)

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
	}

	for stat_cat in json_stats:
		top_stats['fight'][fight_num].setdefault(stat_cat, {})
		top_stats['overall'].setdefault(stat_cat, {})	

	#get commander data
	commander_tag_positions, dead_tag_mark, dead_tag = get_commander_tag_data(json_data)

	#collect player counts and parties
	get_parties_by_fight(fight_num, players)

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

	get_damage_mitigation_data(fight_num, players, targets, skill_map, buff_map)
	#process each player in the fight
	for player in players:
		# skip players not in squad
		if player['notInSquad']:
			continue

		name = player['name']
		profession = player['profession']
		account = player['account']
		group = player['group']
		group_count = len(top_stats['parties_by_fight'][fight_num][group])
		squad_count = top_stats['fight'][fight_num]['squad_count']

		name_prof = name + "|" + profession
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


		# store last party the player was a member
		top_stats['player'][name_prof]['last_party'] = group

		get_firebrand_pages(player, name_prof, name, account,fight_duration_ms)

		get_player_fight_dps(player["dpsTargets"], name, profession, fight_num, (fight_duration_ms/1000))
		get_player_stats_targets(player["statsTargets"], name, profession, fight_num, (fight_duration_ms/1000))

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
