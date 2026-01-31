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
import json
#import os
import requests
import sqlite3
import xlsxwriter
from glicko2 import Player as GlickoPlayer
from collections import defaultdict
from typing import Dict, Any, List, Tuple, Optional
from requests.exceptions import RequestException, Timeout, ConnectionError

#list of tid files to output
tid_list = []


def create_new_tid_from_template(
	title: str,
	caption: str,
	text: str,
	tags: list[str] = None,
	modified: str = None,
	created: str = None,
	creator: str = None,
	fields: dict = None,
) -> dict:
	"""
	Create a new TID from the template.

	Args:
		title (str): The title of the TID.
		caption (str): The caption of the TID.
		text (str): The text of the TID.
		tags (list[str], optional): The tags for the TID. Defaults to None.
		modified (str, optional): The modified date of the TID. Defaults to None.
		created (str, optional): The created date of the TID. Defaults to None.
		creator (str, optional): The creator of the TID. Defaults to None.
		field (dict, optional): The field to add to the TID. Defaults to None.

	Returns:
		dict: The new TID.
	"""
	temp_tid = {}
	temp_tid['title'] = title
	temp_tid['caption'] = caption
	temp_tid['text'] = text
	if tags:
		temp_tid['tags'] = tags
	if modified:
		temp_tid['modified'] = modified
	if created:
		temp_tid['created'] = created
	if creator:
		temp_tid['creator'] = creator
	if fields:
		for field, value in fields.items():
			temp_tid[field] = value

	return temp_tid

def append_tid_for_output(input, output):
	output.append(input)
	print(input['title']+'.tid has been created.')

def write_tid_list_to_json(tid_list: list, output_filename: str) -> None:
	"""
	Write the list of tid files to a json file

	Args:
		tid_list (list): The list of tid files.
		output_filename (str): The name of the output file.

	Returns:
		None
	"""
	with open(output_filename, 'w') as outfile:
		json.dump(tid_list, outfile, indent=4, sort_keys=True)

def convert_duration(milliseconds: int) -> str:
	"""
	Convert a duration in milliseconds to a human-readable string.

	Args:
		milliseconds (int): The duration in milliseconds.

	Returns:
		str: A string representing the duration in a human-readable format.
	"""
	seconds, milliseconds = divmod(milliseconds, 1000)
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	days, hours = divmod(hours, 24)

	duration_parts = []
	if days:
		duration_parts.append(f"{days}d")
	if hours:
		duration_parts.append(f"{hours:02}h")
	if minutes:
		duration_parts.append(f"{minutes:02}m")
	duration_parts.append(f"{seconds:02}s {milliseconds:03}ms")

	return " ".join(duration_parts)

def calculate_average_squad_count(fight_data: dict) -> tuple:
	"""
	Calculate the average squad count for a fight.

	Args:
		fight_data (dict): The fight data.

	Returns:
		tuple: The average squad count, average ally count, and average enemy count.
	"""
	total_squad_count = 0
	total_ally_count = 0
	total_enemy_count = 0

	for fight in fight_data:
		total_squad_count += fight["squad_count"]
		total_ally_count += fight["non_squad_count"]
		total_enemy_count += fight["enemy_count"]

	avg_squad_count = total_squad_count / len(fight_data)
	avg_ally_count = total_ally_count / len(fight_data)
	avg_enemy_count = total_enemy_count / len(fight_data)

	return avg_squad_count, avg_ally_count, avg_enemy_count

def extract_gear_buffs_and_skills(buff_data: dict, skill_data: dict) -> tuple:
	"""
	Extract gear buffs and skills from the top stats data.

	Args:
		buff_data (dict): The buff data.
		skill_data (dict): The skill data.

	Returns:
		tuple: A tuple containing a list of gear buff IDs and a list of gear skill IDs.
	"""
	gear_buff_ids = []
	gear_skill_ids = []

	for buff, buff_data in buff_data.items():
		if "Relic of" in buff_data["name"] or "Superior Sigil of" in buff_data["name"] or "Gear" in buff_data["classification"]:
			gear_buff_ids.append(buff)

	for skill, skill_data in skill_data.items():
		if "Relic of" in skill_data["name"] or "Superior Sigil of" in skill_data["name"]:
			gear_skill_ids.append(skill)

	return gear_buff_ids, gear_skill_ids

def build_gear_buff_summary(top_stats: dict, gear_buff_ids: list, buff_data: dict, tid_date_time: str) -> str:
	rows = []
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	header = "|thead-dark table-caption-top table-hover sortable|k\n"
	header += "|!Name | !Prof | !{{FightTime}} |"
	for buff_id in gear_buff_ids:
		buff_icon = buff_data[buff_id]["icon"]
		buff_name = buff_data[buff_id]["name"]
		header += f" ![img width=24 [{buff_name}|{buff_icon}]] |"
	header += "h"
	rows.append(header)

	for player in top_stats["player"].values():
		fight_time = player["active_time"]
		if fight_time == 0:
			continue
		account = player["account"]
		name = player["name"]
		tt_name = f'<div class="xtooltip"> {name} <span class="xtooltiptext" style="padding-left: 5px"> {account} </span></div>'
		profession = "{{"+player["profession"]+"}}"
		row = f"|{tt_name} | {profession} | {fight_time/1000:,.1f}|"

		for buff_id in gear_buff_ids:
			if buff_id in player["buffUptimes"]:
				buff_uptime_ms = player["buffUptimes"][buff_id]['uptime_ms']
				uptime_pct = f"{((buff_uptime_ms / fight_time) * 100):.1f}%"
			else:
				uptime_pct = " - "

			row += f" {uptime_pct} |"
		rows.append(row)
	rows.append(f"| Gear Buff Uptime Table|c")
	rows.append('\n\n</div>\n\n')
		#push table to tid_list for output
	tid_text = "\n".join(rows)
	temp_title = f"{tid_date_time}-Gear-Buff-Uptimes"

	append_tid_for_output(
		create_new_tid_from_template(temp_title, "Gear Buff Uptimes", tid_text),
		tid_list
		)    

def build_gear_skill_summary(top_stats: dict, gear_skill_ids: list, skill_data: dict, tid_date_time: str) -> str:
	rows = []
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	header = "|thead-dark table-caption-top table-hover sortable|k\n"
	header += "|!Name | !Prof | !{{FightTime}} |"
	
	for skill_id in gear_skill_ids:
		skill_icon = skill_data[skill_id]["icon"]
		skill_name = skill_data[skill_id]["name"]
		header += f" ![img width=24 [{skill_name}|{skill_icon}]] |"
	header += "h"
	rows.append(header)

	for player in top_stats["player"].values():
		fight_time = player["active_time"]
		account = player["account"]
		name = player["name"]
		tt_name = f'<div class="xtooltip"> {name} <span class="xtooltiptext" style="padding-left: 5px"> {account} </span></div>'
		profession = "{{"+player["profession"]+"}}"
		row = f"|{tt_name} | {profession} | {fight_time/1000:,.1f}|"

		for skill in gear_skill_ids:
			_skill = int(skill[1:])
			if _skill in player["targetDamageDist"]:
				totalDamage = player["targetDamageDist"][_skill]["totalDamage"]
				connectedHits = player["targetDamageDist"][_skill]["connectedHits"]
				crit = player["targetDamageDist"][_skill]["crit"]
				crit_pct = f"{crit/connectedHits*100:.2f}" if crit > 0 else "0"
				critDamage = player["targetDamageDist"][_skill]["critDamage"]
				tooltip = f"Connected Hits: {connectedHits} <br>Crit: {crit} - ({crit_pct}%) <br>Crit Damage: {critDamage:,.0f}"
				detailEntry = f'<div class="xtooltip"> {totalDamage:,.0f} <span class="xtooltiptext" style="padding-left: 5px">'+tooltip+'</span></div>'
			else:
				detailEntry = " - "
			row += f" {detailEntry} |"
		rows.append(row)
	rows.append(f"| Gear Skill Damage Table|c")
	rows.append('\n\n</div>\n\n')

	#push table to tid_list for output
	tid_text = "\n".join(rows)
	temp_title = f"{tid_date_time}-Gear-Skill-Damage"

	append_tid_for_output(
		create_new_tid_from_template(temp_title, "Gear Skill Damage", tid_text),
		tid_list
	)

def get_total_shield_damage(fight_data: dict) -> int:
	"""Extract the total shield damage from the fight data.

	Args:
		fight_data (dict): The fight data.

	Returns:
		int: The total shield damage.
	"""
	total_shield_damage = 0
	for skill_id, skill_data in fight_data["targetDamageDist"].items():
		total_shield_damage += skill_data["shieldDamage"]
	return total_shield_damage

def get_boxplot_data(players, stats_per_fight, category, stat):
    """
    Extract the boxplot data for the given category and stat.

    Args:
        players (dict): The players data.
        stats_per_fight (dict): The stats per fight data.
        category (str): The category of stats to extract.
        stat (str): The stat to extract.

    Returns:
        tuple: A tuple containing the names, professions, and boxplot data.

    """
    names = []
    profs = []
    boxplot_data = []

    for player, pData in players.items():
        
        if player in stats_per_fight[category][stat]:
            names.append(pData["name"])
            profs.append(pData["profession"])
            boxplot_data.append(stats_per_fight[category][stat][player])
            
    return names, profs, boxplot_data

def build_tag_summary(top_stats):
	"""Build a summary of tags from the top stats data.

	Args:
		top_stats (dict): The top stats data.

	Returns:
		dict: A dictionary of tag summaries, where the keys are the tag names, and the values are dictionaries with the following keys:

			- num_fights (int): The number of fights for the tag.
			- fight_time (int): The total fight time for the tag in milliseconds.
			- kills (int): The total number of kills for the tag.
			- downs (int): The total number of downs for the tag.
			- downed (int): The total number of times the tag was downed.
			- deaths (int): The total number of deaths for the tag.

	"""
	tag_summary = {}
	tag_list = []
	for fight, fight_data in top_stats["fight"].items():
		commander = fight_data["commander"]
		if commander in top_stats["player"]:
			cmd_account = top_stats["player"][commander]["account"],
		else:
			cmd_account = "No Tag"
		if commander not in tag_summary:
			tag_summary[commander] = {
				"account": cmd_account,
				"num_fights": 0,
				"fight_time": 0,
				"enemy_killed": 0,
				"enemy_downed": 0,
				"squad_downed": 0,
				"squad_deaths": 0,
			}
		if commander.split("|")[0] not in tag_list:
			tag_list.append(commander.split("|")[0])
		if commander in top_stats["player"]:
			tag_summary[commander]["account"] = top_stats["player"][commander]["account"]
		else:
			tag_summary[commander]["account"] = "No Tag"
		tag_summary[commander]["num_fights"] += 1
		tag_summary[commander]["fight_time"] += fight_data["fight_durationMS"]
		tag_summary[commander]["enemy_killed"] += fight_data["enemy_killed"]
		tag_summary[commander]["enemy_downed"] += fight_data["enemy_downed"]
		tag_summary[commander]["squad_downed"] += fight_data.get("defenses", {}).get("downCount", 0)
		tag_summary[commander]["squad_deaths"] += fight_data.get("defenses", {}).get("deadCount", 0)

	return tag_summary, tag_list

def output_tag_summary(LATEST_VERSION, tag_summary: dict, tid_date_time) -> None:
	"""Output a summary of the tag data in a human-readable format."""
	rows = []
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	if LATEST_VERSION:
		rows.append(f'New version available: {LATEST_VERSION} \n\n')
	rows.append("|thead-dark table-caption-top table-hover sortable|k")
	rows.append("| Summary by Command Tag |c")
	rows.append(
		"| | | | Enemy |<| Squad|<| |h"
	)	
	rows.append(
		"|Name | Prof | Fights | {{DownedEnemy}} | {{killed}} | {{DownedAlly}} | {{DeadAlly}} | KDR |h"
	)
	for tag, tag_data in tag_summary.items():
		name = tag.split("|")[0]
		if len(tag.split("|")) > 1:
			profession = "{{"+tag.split("|")[1]+"}}"
		else:
			profession = ""
		account = tag_data["account"]
		fights = tag_data["num_fights"]
		downs = tag_data["enemy_downed"]
		kills = tag_data["enemy_killed"]
		downed = tag_data["squad_downed"]
		deaths = tag_data["squad_deaths"]
		tt_name = f'<span class="tooltip tooltip-right" data-tooltip="{account}">  {name}  </span>'
		kdr = kills / deaths if deaths else kills
		rows.append(
			f"|{tt_name} | {profession} | {fights} | {downs} | {kills} | {downed} | {deaths} | {kdr:.2f}|"
		)

		# Sum all tags
		total_fights = sum(tag_data["num_fights"] for tag_data in tag_summary.values())
		total_kills = sum(tag_data["enemy_killed"] for tag_data in tag_summary.values())
		total_downs = sum(tag_data["enemy_downed"] for tag_data in tag_summary.values())
		total_downed = sum(tag_data["squad_downed"] for tag_data in tag_summary.values())
		total_deaths = sum(tag_data["squad_deaths"] for tag_data in tag_summary.values())
		total_kdr = total_kills / total_deaths if total_deaths else total_kills

	rows.append(
		f"|Totals |<| {total_fights} | {total_downs} | {total_kills} | {total_downed} | {total_deaths} | {total_kdr:.2f}|f"
	)
	rows.append("\n\n</div>")

	text = "\n".join(rows)

	append_tid_for_output(
		create_new_tid_from_template(F"{tid_date_time}-Tag_Stats", "Tag Summary", text),
		tid_list
		)

def build_fight_summary(top_stats: dict, fight_data_charts, caption: str, tid_date_time : str) -> None:
	"""
	Build a summary of the top stats for each fight.

	Print a table with the following columns:
		- Fight number
		- Date-Time[upload link]
		- End time
		- Duration
		- Squad count
		- Ally count
		- Enemy count
		- R/G/B team count
		- Downs
		- Kills
		- Downed
		- Deaths
		- Damage out
		- Damage in
		- Barrier damage
		- Barrier percentage
		- Shield damage
		- Shield percentage

	Args:
		top_stats (dict): The top_stats dictionary containing the overall stats.
		caption (str): The table caption

	Returns:
		None
	"""
	rows = []
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	header = "|thead-dark table-caption-top table-hover|k\n"
	header += f"| {caption} |c\n"
	if fight_data_charts:
		header += "|!# |!Fight Link | !Duration | !Squad | !Allies | !Enemy | !R/G/B | !{{DownedEnemy}} | !{{killed}} | !{{DownedAlly}} | ![img width=24 [Rallies|https://wiki.guildwars2.com/images/6/6e/Renown_Heart_%28map_icon%29.png]] | !{{DeadAlly}} | !{{Damage}} | !{{Damage Taken}} | !{{damageBarrier}} | !{{damageBarrier}} % | !{{damageShield}} | !{{damageShield}} % |!Fight Chart|h"
	else:
		header += "|!# |!Fight Link | !Duration | !Squad | !Allies | !Enemy | !R/G/B | !{{DownedEnemy}} | !{{killed}} | !{{DownedAlly}} | ![img width=24 [Rallies|https://wiki.guildwars2.com/images/6/6e/Renown_Heart_%28map_icon%29.png]] | !{{DeadAlly}} | !{{Damage}} | !{{Damage Taken}} | !{{damageBarrier}} | !{{damageBarrier}} % | !{{damageShield}} | !{{damageShield}} % |h"

	rows.append(header)

	
	last_fight = 0
	last_end = ""
	total_durationMS = 0
	
	# Calculate average squad count
	avg_squad_count, avg_ally_count, avg_enemy_count = calculate_average_squad_count(top_stats["fight"].values())
	# Get the total downs, deaths, and damage out/in/barrier/shield
	enemy_downed = top_stats['overall']['enemy_downed']
	enemy_killed = top_stats['overall']['enemy_killed']
	squad_down = top_stats['overall']['defenses']['downCount']
	squad_dead = top_stats['overall']['defenses']['deadCount']
	total_rallies = top_stats['overall']['rallies']
	total_damage_out = top_stats['overall']['dpsTargets']['damage']
	total_damage_in = top_stats['overall']['defenses']['damageTaken']
	total_barrier_damage = top_stats['overall']['defenses']['damageBarrier']
	total_shield_damage = get_total_shield_damage(top_stats['overall'])
	total_shield_damage_percent = (total_shield_damage / total_damage_out) * 100 if total_damage_out != 0 else 0
	total_barrier_damage_percent = (total_barrier_damage / total_damage_in) * 100 if total_damage_in != 0 else 0

	# Iterate over each fight and build the row
	for fight_num, fight_data in top_stats["fight"].items():
		row = ""
		# Get the total shield damage for this fight
		fight_shield_damage = get_total_shield_damage(fight_data)

		# Abbreviate the fight location
		abbrv=""
		for word in fight_data['fight_name'].split():
			abbrv += word[0]
		# construct the fight link    
		if fight_data['fight_link'] == "":
			fight_link = f"{fight_data['fight_date']} - {fight_data['fight_end']} - {abbrv}"
		else:
			fight_link = f"[[{fight_data['fight_date']} - {fight_data['fight_end']} - {abbrv}|{fight_data['fight_link']}]]"
		
		# Build the row
		damage_taken = fight_data['defenses'].get('damageTaken', 0)
		downed = fight_data.get('enemy_downed', 0)
		killed = fight_data.get('enemy_killed', 0)
		def_down = fight_data['defenses'].get('downCount', 0)
		def_dead = fight_data['defenses'].get('deadCount', 0)
		rallies = fight_data.get('rallies', 0)
		dmg_out = fight_data['dpsTargets'].get('damage', 0)
		def_barrier = fight_data['defenses'].get('damageBarrier', 0)
		def_barrier_pct = (def_barrier / damage_taken) * 100 if damage_taken > 0 else 0
		row += f"|{fight_num} |{fight_link} | {fight_data['fight_duration']}| {fight_data['squad_count']} | {fight_data['non_squad_count']} | {fight_data['enemy_count']} "
		row += f"| {fight_data['enemy_Red']}/{fight_data['enemy_Green']}/{fight_data['enemy_Blue']} | {downed} | {killed} "
		row += f"| {def_down} | {rallies} | {def_dead} | {dmg_out:,}| {damage_taken:,}"
		row += f"| {def_barrier:,}| {def_barrier_pct:.2f}%| {fight_shield_damage:,}"
		# Calculate the shield damage percentage
		shield_damage_pct = (fight_shield_damage / dmg_out) * 100 if dmg_out else 0
		row += f"| {shield_damage_pct:.2f}%|"
		if fight_data_charts:
			row += f"[[F-{fight_num} Chart|{tid_date_time}_Fight_{str(fight_num).zfill(2)}_Damage_Output_Review]]|"

		# Keep track of the last fight number, end time, and total duration
		last_fight = fight_num
		total_durationMS += fight_data['fight_durationMS']

		rows.append(row)

	raid_duration = convert_duration(total_durationMS)
	# Build the footer
	if fight_data_charts:
		footer = f"|Total Fights: {last_fight}|<| {raid_duration}| {avg_squad_count:.1f},,avg,,| {avg_ally_count:.1f},,avg,,| {avg_enemy_count:.1f},,avg,,|     | {enemy_downed} | {enemy_killed} | {squad_down} | {total_rallies} | {squad_dead} | {total_damage_out:,}| {total_damage_in:,}| {total_barrier_damage:,}| {total_barrier_damage_percent:.2f}%| {total_shield_damage:,}| {total_shield_damage_percent:.2f}%| |f"
	else:
		footer = f"|Total Fights: {last_fight}|<| {raid_duration}| {avg_squad_count:.1f},,avg,,| {avg_ally_count:.1f},,avg,,| {avg_enemy_count:.1f},,avg,,|     | {enemy_downed} | {enemy_killed} | {squad_down} | {total_rallies} | {squad_dead} | {total_damage_out:,}| {total_damage_in:,}| {total_barrier_damage:,}| {total_barrier_damage_percent:.2f}%| {total_shield_damage:,}| {total_shield_damage_percent:.2f}%|f"
	rows.append(footer)
	rows.append("\n\n</div>")
	# push the table to tid_list

	tid_text = "\n".join(rows)

	append_tid_for_output(
		create_new_tid_from_template(f"{tid_date_time}-{caption}", "Fight Summary", tid_text),
		tid_list
		)

def build_damage_summary_table(top_stats: dict, caption: str, tid_date_time: str) -> None:
	"""
	Build a damage summary table.

	Args:
		top_stats (dict): The top_stats dictionary containing the overall stats.
		caption (str): The table caption

	Returns:
		None
	"""
	rows = []
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	# Build the table header
	header = "|thead-dark table-caption-top table-hover sortable|k\n"
	header += f"| {caption} |c\n"
	header += "|!Party |!Name | !Prof | !{{FightTime}} |"
	header += " !{{Target_Damage}} | !{{Target_Damage_PS}} | !{{Target_Power}} | !{{Target_Power_PS}} | !{{Target_Condition}} | !{{Target_Condition_PS}} | !{{Target_Breakbar_Damage}} | !{{All_Damage}}| !{{All_Power}} | !{{All_Condition}} | !{{All_Breakbar_Damage}} |h"

	rows.append(header)

	# Build the table body
	for player, player_data in top_stats["player"].items():
		fighttime = player_data["active_time"] / 1000
		if fighttime == 0:
			continue
		account = player_data["account"]
		name = player_data["name"]
		tt_name = f'<span data-tooltip="{account}">{name}</span>'
		row = f"| {player_data['last_party']} |{tt_name} |"+" {{"+f"{player_data['profession']}"+"}}"+f" {player_data['profession'][:3]} "+f"| {fighttime:,.1f}|"
		row += " {:,}| {:,.0f}| {:,}| {:,.0f}| {:,}| {:,.0f}| {:,}| {:,}| {:,}| {:,}| {:,}|".format(
			player_data["dpsTargets"]["damage"],
			player_data["dpsTargets"]["damage"]/fighttime,
			player_data["dpsTargets"]["powerDamage"],
			player_data["dpsTargets"]["powerDamage"]/fighttime,			
			player_data["dpsTargets"]["condiDamage"],
			player_data["dpsTargets"]["condiDamage"]/fighttime,
			player_data["dpsTargets"]["breakbarDamage"],
			player_data["statsAll"]["totalDmg"],
			player_data["statsAll"]["directDmg"],
			player_data["statsAll"]["totalDmg"] - player_data["statsAll"]["directDmg"],
			player_data["dpsTargets"]["breakbarDamage"],
		)

		rows.append(row)

	rows.append("\n\n</div>")
	#push table to tid_list for output
	tid_text = "\n".join(rows)

	append_tid_for_output(
		create_new_tid_from_template(f"{tid_date_time}-{caption}", caption, tid_text),
		tid_list
		)


def build_category_summary_report(
    top_stats: Dict[str, Any],
    category_stats: Dict[str, str],
    enable_hide_columns: bool,
    caption: str,
    tid_date_time: str,
    tid_list: list,
    layout: str = "summary",  # "summary" or "detailed"
    sort_mode: str = "Stat/1s",  # which column to sort by in detailed layout
) -> None:
    """
    Unified generator for category summary tables.

    layout="summary" - single large table (all stats as columns)
    layout="detailed" - one table+chart per stat with Total/Stat/1s/60s columns
    """

    TOGGLES = ["Total", "Stat/1s", "Stat/60s"]

    alt_stat_icon = {
		"damage":"{{totalDmg}}",
		"boonStripDownContribution":"{{boonStrips}}{{downed}}",
		"boonStripDownContributionTime":"{{boonStripsTime}}{{downed}}",
		"appliedCrowdControlDownContribution":"{{appliedCrowdControl}}{{downed}}",
		"appliedCrowdControlDurationDownContribution":"{{appliedCrowdControlDuration}}{{downed}}",
		"damageTakenCount": '{{damageTaken}}[img width=16 [Hits|hits.png]]',
		"conditionDamageTakenCount": '{{conditionDamageTaken}}[img width=16 [Hits|hits.png]]',
		"powerDamageTakenCount": '{{powerDamageTaken}}[img width=16 [Hits|hits.png]]',
		"downedDamageTakenCount": '{{downedDamageTaken}}[img width=16 [Hits|hits.png]]',
		"damageBarrierCount": '{{damageBarrier}}[img width=16 [Hits|hits.png]]',
		"downContribPct": '{{downContribution}} %'
		}
    pct_stats = {
		"criticalRate": "critableDirectDamageCount", "flankingRate":"connectedDirectDamageCount", "glanceRate":"connectedDirectDamageCount", "againstMovingRate": "connectedDamageCount"
	}
    time_stats = ["resurrectTime", "condiCleanseTime", "condiCleanseTimeSelf", "boonStripsTime", "removedStunDuration", "boonStripDownContributionTime"]

    # === Helper to compute per-player values ===
    def compute_values(player, stat, category):
        fight_time = player.get("active_time", 0) / 1000
        if fight_time == 0:
            return {"Total": 0, "Stat/1s": 0, "Stat/60s": 0}
        if stat in pct_stats:
            divisor_value = player[category].get(pct_stats[stat], 0)
            if divisor_value == 0:
                return {"Total": 0, "Stat/1s": 0, "Stat/60s": 0}
            val = round((player[category].get(stat, 0) / divisor_value) * 100, 2)
            return {"Total": val, "Stat/1s": val, "Stat/60s": val}
        val = player[category].get(stat, 0)
        if stat in ["receivedCrowdControlDuration","appliedCrowdControlDuration", "appliedCrowdControlDurationDownContribution"]:
            val = val / 1000
        if stat == "downContribPct":
            divisor_value = player[category].get("totalDmg", 0)
            if divisor_value == 0:
                return {"Total": 0, "Stat/1s": 0, "Stat/60s": 0}
            val = round((player[category].get("downContribution", 0) / divisor_value) * 100,2)
            return {"Total": val, "Stat/1s": val, "Stat/60s": val}
        return {
            "Total": val,
            "Stat/1s": val / fight_time,
            "Stat/60s": val / (fight_time / 60),
        }
	
    rows: List[str] = []
    rows.append('<div style="overflow-y:auto;width:100%;overflow-x:auto;">\n')

    # Optional column toggles for summary layout
    if enable_hide_columns and layout == "summary":
        rows.append('<style>')
        col_count = 26
        for i in range(4, col_count):
            if i == col_count - 1:
                rows.append(f".col-toggle:has(#toggle-col{i}:not(:checked)) tr > *:nth-child({i}) {{\n  display: none;}}")
            else:
                rows.append(f".col-toggle:has(#toggle-col{i}:not(:checked)) tr > *:nth-child({i}),")
        rows.append("""
.col-controls {
  display:flex;flex-wrap:wrap;gap:0.3em 0.5em;align-items:center;
  background:#343a40;color:#eee;border-radius:0.5em;
  padding:0.6em 1em;margin-bottom:0.8em;font-size:0.9em;
}
.col-controls label {
  display:flex;align-items:center;gap:0.2em;
  background:#333;padding:0.2em 0.5em;border-radius:0.3em;cursor:pointer;
  transition:background 0.2s;
}
.col-controls label:hover{background:#444;}
.col-controls input[type="checkbox"]{accent-color:#6cf;}
</style>
					
<div class='col-toggle'>
<div class="col-controls">
Uncheck to Hide: """)
        rows.append
        for i, stat in enumerate(category_stats.keys(), start=5):
            stat_icon = alt_stat_icon.get(stat, "{{"+stat+"}}")
            rows.append(f"<label><input type='checkbox' id='toggle-col{i}' checked> {stat_icon}</label>")
        rows.append("</div>\n")

    #Detailed Layout (table + chart per stat)
    if layout == "detailed":
        rows.append("""
<style>
.btn {
  display: inline-block;
  font-weight: 400;
  text-align: center;
  white-space: nowrap;
  vertical-align: middle;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
  border: 1px solid transparent;
  padding: 0.375rem 0.75rem;
  font-size: 1rem;
  line-height: 1.5;
  border-radius: 0.25rem;
  margin: 1px;
  transition: color 0.15s ease-in-out, background-color 0.15s ease-in-out, border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.btn-dark {
  color: #fff;
  background-color: #343a40;
  border-color: #343a40;
}

.btn-dark:hover {
  color: #fff;
  background-color: #23272b;
  border-color: #1d2124;
}

.btn-dark:focus, .btn-dark.focus {
  box-shadow: 0 0 0 0.2rem rgba(52, 58, 64, 0.5);
}

.btn-dark.disabled, .btn-dark:disabled {
  color: #fff;
  background-color: #343a40;
  border-color: #343a40;
}
.btn-sm{
  padding: 0.2rem 0.4rem;
  font-size: 0.75rem;
  line-height: 1.5;
  border-radius: 0.2rem;
}
</style>
""")

        # Radio buttons for selecting stat focus
        default_stat = list(category_stats.keys())[0]
        for stat in category_stats:
            stat_icon = alt_stat_icon.get(stat, "{{"+stat+"}}")
            rows.append(
                f'<$radio class="btn btn-sm btn-dark" tiddler="$:/temp/detailed_state" default="{default_stat}" field="{caption}_selected" value="{stat}"> {stat_icon} </$radio>'
            )

        # One table and chart per stat
        for stat, category in category_stats.items():
            # Compute values per player
            chart_data = []
            for player in top_stats.get("player", {}).values():
                vals = compute_values(player, stat, category)
                chart_data.append({
                    "Party": player["last_party"],
                    "Name": player["name"],
                    "Prof": player["profession"],
					"Acct": player["account"],
                    "FightTime": player["active_time"] / 1000,
                    **{k: round(v, 2) for k, v in vals.items()},
                })

            # Sort by Stat/1s descending
            chart_data.sort(key=lambda x: x[sort_mode], reverse=True)

            # === Build table ===
            rows.append(f'<$reveal stateTitle="$:/temp/detailed_state" stateField="{caption}_selected" default="{default_stat}" type="match" text="{stat}" animate="yes">')
            rows.append('<div class="flex-row">\n    <div class="flex-col border">\n\n')
            format_stat = stat[0].upper() + stat[1:]
            rows.append(f"!! {format_stat}\n")
            rows.append("|thead-dark table-caption-top table-hover sortable|k\n")
            rows.append("|!Party |!Name |!Prof |!{{FightTime}} |!Total|!Stat/1s|!Stat/60s|h")

            for p in chart_data:
                tt_name = f"<span data-tooltip=\"{p['Acct']}\">{p['Name']}</span>"
                rows.append(
                    f"| {p['Party']} |{tt_name} | {{{{{p['Prof']}}}}} {p['Prof'][:3]} | "
                    f"{p['FightTime']:,.1f} | {p['Total']:,}| {p['Stat/1s']:,}| {p['Stat/60s']:,}|"
                )

            rows.append("\n    </div>\n    <div class='flex-col border'>\n\n")
            # Sort chart by requested metric
            sorted_chart = sorted(chart_data, key=lambda x: x.get(sort_mode, 0), reverse=True)
            #json_chart = json.dumps(sorted_chart)

            # Chart: Echart Bar or Boxplot future state
            chart_block = build_bar_echart(sorted_chart, format_stat, caption)
            rows.append(chart_block)
            rows.append("\n    </div>\n</div>\n\n")
            rows.append("</$reveal>\n")

        rows.append("</div>")
        tid_text = "\n".join(rows)
        temp_title = f"{tid_date_time}-{caption}-Detailed"
        append_tid_for_output(
            create_new_tid_from_template(
                temp_title,
                f"{caption} - Detailed",
                tid_text,
                fields={f"{caption}_selected": next(iter(category_stats.keys()), "")},
            ),
            tid_list,
        )

    # === Summary Layout (one large table) ===
    elif layout == "summary":
        for toggle in TOGGLES:
            rows.append(f'<$reveal stateTitle="$:/temp/detailed_state" default="Total" stateField="category_radio" '
                        f'type="match" text="{toggle}" animate="yes">\n')

            header = "|thead-dark table-caption-top table-hover sortable|k\n"
            header += "|!Party |!Name | !Prof | !{{FightTime}} |"
            for stat in category_stats.keys():
                stat_icon = alt_stat_icon.get(stat, "{{"+stat+"}}")
                header += f" !{stat_icon} |"
            header += "h"
            rows.append(header)

            for player in top_stats.get("player", {}).values():
                fight_time = player.get("active_time", 0) / 1000
                if fight_time == 0:
                    continue
                tt_name = f"<span data-tooltip=\"{player['account']}\">{player['name']}</span>"
                row = (f"| {player['last_party']} |{tt_name} | "
                       f"{{{{{player['profession']}}}}} {player['profession'][:3]} | "
                       f"{fight_time:,.1f} |")
                for stat, category in category_stats.items():
                    val = compute_values(player, stat, category)[toggle]
                    if stat in pct_stats or stat == "downContribPct":
                        val = f" {val:,.2f}%"
                    elif stat in time_stats:
                        val = f" {val:,.1f}"
                    else:
                        if toggle == "Stat/60s":
                            val = f" {val:,.2f}"
                        elif toggle == "Stat/1s":
                            val = f" {val:,.3f}"
                        else:
                            val = f" {val:,.0f}"

                    row += f" {val}|"
                rows.append(row)

            rows.append(f'|<$radio tiddler="$:/temp/detailed_state" field="category_radio" default="Total" value="Total"> Total  </$radio>'
                        f' - <$radio  tiddler="$:/temp/detailed_state" field="category_radio" value="Stat/1s"> Stat/1s  </$radio>'
                        f' - <$radio  tiddler="$:/temp/detailed_state" field="category_radio" value="Stat/60s"> Stat/60s  </$radio>'
                        f' - {caption} Table|c\n</$reveal>')

        if enable_hide_columns:
            rows.append("</div>\n</div>")

        tid_text = "\n".join(rows)
        temp_title = f"{tid_date_time}-{caption}-Summary"
        append_tid_for_output(
            create_new_tid_from_template(
                temp_title,
                f"{caption} - Summary",
                tid_text,
                fields={"category_radio": "Total"},
            ),
            tid_list,
        )
    else:
        raise ValueError("layout must be 'summary' or 'detailed'")
	

CATEGORY_ORDER = ["selfBuffs", "groupBuffs", "squadBuffs", "totalBuffs"]
CATEGORY_CAPTIONS = {
    "selfBuffs": "Self Generation",
    "groupBuffs": "Group Generation",
    "squadBuffs": "Squad Generation",
    "totalBuffs": "Total Generation",
}
TOGGLES = ["Total", "Average", "Uptime"]



def safe_div(a: float, b: float, default: float = 0.0) -> float:
    try:
        return a / b if b != 0 else default
    except Exception:
        return default


def compute_boon_metrics(
    player: Dict[str, Any],
    boon_id: str,
    category: str,
    buff_data: Dict[str, Any],
) -> Tuple[float, float, float, float]:
    """
    Returns a tuple (generation_ms, wasted_ms, uptime_pct_raw, wasted_pct_raw)
    - uptime_pct_raw/wasted_pct_raw are *raw numeric* values (not formatted strings).
    The caller decides how to format for stacking vs not-stacking and toggle.
    """
    stacking = buff_data.get(boon_id, {}).get("stacking", False)
    active_time = player.get("active_time", 0)
    num_fights = player.get("num_fights", 1)
    group_supported = player.get("group_supported", 1)
    squad_supported = player.get("squad_supported", 1)

    # When category is missing, treat as zero
    generation_ms = 0
    wasted_ms = 0

    if category == "totalBuffs":
        # accumulate from self and squad
        if boon_id in player.get("selfBuffs", {}):
            generation_ms += player["selfBuffs"][boon_id].get("generation", 0)
            wasted_ms += player["selfBuffs"][boon_id].get("wasted", 0)
        if boon_id in player.get("squadBuffs", {}):
            generation_ms += player["squadBuffs"][boon_id].get("generation", 0)
            wasted_ms += player["squadBuffs"][boon_id].get("wasted", 0)
    else:
        # normal single-category lookup (self/group/squad)
        generation_ms = player.get(category, {}).get(boon_id, {}).get("generation", 0)
        wasted_ms = player.get(category, {}).get(boon_id, {}).get("wasted", 0)

    # Compute uptime / wasted percentages
    if category == "selfBuffs":
        if stacking:
            uptime_raw = safe_div(generation_ms, active_time)
            wasted_raw = safe_div(wasted_ms, active_time)
        else:
            uptime_raw = safe_div(generation_ms, active_time) * 100
            wasted_raw = safe_div(wasted_ms, active_time) * 100

    elif category == "groupBuffs":
        denom = safe_div((group_supported - num_fights), num_fights, default=0)
        if denom == 0:
            denom = 1
        if stacking:
            uptime_raw = safe_div(generation_ms, active_time) / denom
            wasted_raw = safe_div(wasted_ms, active_time) / denom
        else:
            uptime_raw = safe_div(generation_ms, active_time) / denom * 100
            wasted_raw = safe_div(wasted_ms, active_time) / denom * 100

    elif category == "squadBuffs":
        denom = safe_div((squad_supported - num_fights), num_fights, default=0)
        if denom == 0:
            denom = 1
        if stacking:
            uptime_raw = safe_div(generation_ms, active_time) / denom
            wasted_raw = safe_div(wasted_ms, active_time) / denom
        else:
            uptime_raw = safe_div(generation_ms, active_time) / denom * 100
            wasted_raw = safe_div(wasted_ms, active_time) / denom * 100

    elif category == "totalBuffs":
        denom = squad_supported if squad_supported != 0 else 1
        if stacking:
            uptime_raw = safe_div(generation_ms, active_time) / denom
            wasted_raw = safe_div(wasted_ms, active_time) / denom
        else:
            uptime_raw = safe_div(generation_ms, active_time) / denom * 100
            wasted_raw = safe_div(wasted_ms, active_time) / denom * 100

    else:
        raise ValueError(f"Invalid category: {category}")

    return generation_ms, wasted_ms, uptime_raw, wasted_raw


def format_entry(
    generation_ms: float,
    wasted_ms: float,
    uptime_raw: float,
    wasted_raw: float,
    toggle: str,
    stacking: bool,
    active_time: int,
) -> Tuple[str, float]:
    """
    Return (html_cell, numeric_value_for_chart)
    - html_cell: the HTML string to put in the table cell
    - numeric_value_for_chart: numeric value to add to chart dataset (Total/Avg/Uptime)
    """
    if toggle == "Total":
        wasted_total = wasted_ms / 1000.0
        generated_total = generation_ms / 1000.0
        entry = f'<span data-tooltip="{wasted_total:,.2f} Wasted">{generated_total:,.2f}</span>'
        chart_val = generated_total
    elif toggle == "Average":
        # generation per ms of active time
        active_time_safe = active_time if active_time != 0 else 1
        wasted_average = safe_div(int(wasted_ms), active_time_safe)
        generated_average = safe_div(int(generation_ms), active_time_safe)
        entry = f'<span data-tooltip="{wasted_average:,.2f} Wasted">{generated_average:,.2f}</span>'
        chart_val = generated_average
    else:  # Uptime
        if stacking:
            chart_val = uptime_raw
            uptime_display = f"{uptime_raw:.2f}"
            wasted_display = f"{wasted_raw:.2f}"
            entry = f'<span data-tooltip="{wasted_display} Wasted">{uptime_display}</span>'
        else:
            chart_val = uptime_raw
            uptime_display = f"{uptime_raw:.2f}%"
            wasted_display = f"{wasted_raw:.2f}%"
            entry = f'<span data-tooltip="{wasted_display} Wasted">{uptime_display}</span>'

    return entry, chart_val


def build_table_header(
    boons_meta: Dict[str, Dict[str, Any]],
    include_icons: bool = False,
    single_boon: bool = False,
) -> str:
    """
    Construct the table header.
    - boons_meta: mapping boon_id -> {name, icon, stacking}
    - include_icons: when True, use icon img markup for each boon (used in single-boon table)
    - single_boon: if True, header includes the boon as a single column (used by per-boon tables)
    """
    header = "|thead-dark table-caption-top table-hover sortable|k\n"
    header += "|!Party |!Name | !Prof | !{{FightTime}} |"
    if single_boon:
        # one column for the single boon (header built elsewhere if needed)
        # We'll still append a placeholder column marker; the caller will insert caption text
        header += "!Boons|"
    else:
        for boon_id, meta in boons_meta.items():
            if include_icons:
                skillIcon = meta.get("icon", "")
                boon_name = meta.get("name", "")
                header += f" ![img width=24 [{boon_name}|{skillIcon}]] |"
            else:
                header += "!{{" + f"{meta.get('name','')}" + "}}|"
    header += "h"
    return header


def build_player_basic_cells(player: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """
    Return the initial row fragment (party/name/prof/time) and a chart-row list seed.
    """
    account = player.get("account", "")
    name = player.get("name", "")
    tt_name = f'<span data-tooltip="{account}">{name}</span>'
    row_prefix = f"| {player.get('last_party','')} |{tt_name} |{{{{{player.get('profession','')}}}}} {player.get('profession','')[:3]} | {player.get('active_time',0)/1000:,.1f}|"
    chart_seed = [player.get("last_party", ""), name, player.get("profession", "")[:3], player.get("active_time", 0)/1000]
    return row_prefix, chart_seed


def build_player_row(
    player: Dict[str, Any],
    boons_meta: Dict[str, Dict[str, Any]],
    category: str,
    toggle: str,
    buff_data: Dict[str, Any],
    single_boon_id: Optional[str] = None,
) -> Tuple[str, Optional[List[Any]]]:
    """
    Build a single player's row for the given set of boons.
    - If single_boon_id is provided, boons_meta should contain just that boon and we return a chart row.
    Returns (row_html, chart_row or None)
    """
    if player.get("active_time", 0) == 0:
        return "", None

    row, chart_row = build_player_basic_cells(player)
    chart_values_for_sort = []

    # decide boons to iterate
    if single_boon_id:
        iterate_boons = [single_boon_id]
    else:
        iterate_boons = list(boons_meta.keys())

    for boon_id in iterate_boons:
        # if the player's category doesn't include the boon (for non-total category), mark as '-'
        if category != "totalBuffs" and boon_id not in player.get(category, {}):
            entry = " - "
            chart_val = 0
        else:
            stacking = buff_data.get(boon_id, {}).get("stacking", False)
            generation_ms, wasted_ms, uptime_raw, wasted_raw = compute_boon_metrics(player, boon_id, category, buff_data)
            entry, chart_val = format_entry(generation_ms, wasted_ms, uptime_raw, wasted_raw, toggle, stacking, player.get("active_time",0))
        row += f" {entry}|"
        chart_row.append(chart_val)
        chart_values_for_sort.append(chart_val)

    return row, chart_row


def build_boon_report(
    top_stats: Dict[str, Any],
    boons: Dict[str, str],
    buff_data: Dict[str, Any],
    tid_date_time: str,
    tid_list,
    layout: str = "focus",  # "focus" or "summary"
    category: Optional[str] = None,  # required if layout="summary"
    boon_type: Optional[str] = None,
) -> None:
    """
    Generator for boon reports.

    layout="focus"  → per-boon tables, toggles, and ECharts blocks.
    layout="summary" → single big table (boons as columns) for given category.

    Args:
        top_stats: player data.
        boons: mapping boon_id -> boon_name.
        buff_data: metadata (icon, stacking flag).
        tid_date_time: prefix for tiddler title.
        tid_list: mutable list of tiddlers to append to.
        layout: "focus" or "summary".
        category: which generation type to show if summary (e.g. "selfBuffs").
        boon_type: optional label for summary output.
    """
    rows: List[str] = []
    rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')

    if layout == "focus":
        # --- Focus Layout (per-boon tables + charts) ---
        rows.append("""
<style>
.btn {
  display:inline-block; font-weight:400; text-align:center; white-space:nowrap;
  border:1px solid transparent; padding:0.375rem 0.75rem; font-size:1rem;
  line-height:1.5; border-radius:0.25rem; margin:1px;
  transition:color .15s ease-in-out, background-color .15s ease-in-out, border-color .15s ease-in-out;
}
.btn-dark { color:#fff; background-color:#343a40; border-color:#343a40; }
.btn-dark:hover { background-color:#23272b; border-color:#1d2124; }
.btn-sm { padding:0.2rem 0.4rem; font-size:0.75rem; border-radius:0.2rem; }
</style>
""")

        # Button bar
        for boon_id, boon_name in boons.items():
            if boon_id not in buff_data:
                continue
            rows.append(
                f'<$radio class="btn btn-sm btn-dark"'
				f' tiddler="$:/temp/selectedBoon" default="Might"'
                f' field="boon_selected" value="{boon_name}"> '
                f'{{{{{boon_name}}}}} {boon_name}'
                f' </$radio>'
            )

        # Per-boon sections
        for boon_id, boon_name in boons.items():
            if boon_id not in buff_data:
                continue

            skillIcon = buff_data[boon_id].get("icon", "")
            stacking = buff_data[boon_id].get("stacking", False)

            rows.append(f'<$reveal stateTitle="$:/temp/selectedBoon" stateField="boon_selected" default="Might"'
                        f'type="match" text="{boon_name}" animate="yes">\n')
            rows.append('\n<div class="flex-row">\n<div class="flex-col border">\n\n')
            rows.append(f"! [img width=24 [{boon_name}|{skillIcon}]] {boon_name}\n")

            for toggle in TOGGLES:
                rows.append(f'<$reveal stateTitle="$:/temp/selectedBoon" default="Total" stateField="boon_radio" '
                            f'type="match" text="{toggle}" animate="yes">\n')

                header = "|thead-dark table-caption-top table-hover sortable|k\n"
                header += "|!Party |!Name | !Prof | !{{FightTime}} | !Self Gen | !Group Gen | !Squad Gen | !Total Gen |h"
                rows.append(header)

                chart_data: List[List[Any]] = []
                for player in top_stats.get("player", {}).values():
                    if player.get("active_time", 0) == 0:
                        continue
                    row_prefix, chart_seed = build_player_basic_cells(player)
                    per_row_chart = chart_seed.copy()
                    row = row_prefix
                    for cat in ["selfBuffs", "groupBuffs", "squadBuffs", "totalBuffs"]:
                        if cat != "totalBuffs" and boon_id not in player.get(cat, {}):
                            entry, val = " - ", 0
                        else:
                            gen, waste, up, wastep = compute_boon_metrics(player, boon_id, cat, buff_data)
                            entry, val = format_entry(gen, waste, up, wastep, toggle, stacking, player["active_time"])
                        row += f" {entry}|"
                        per_row_chart.append(val)
                    chart_data.append(per_row_chart)
                    rows.append(row)
                try:
                    sorted_pairs = sorted(
						zip(chart_data, rows[-len(chart_data):]),  # last chart_data rows belong to this boon
						key=lambda x: float(x[0][6]) if len(x[0]) > 6 else 0,
						reverse=True
					)
                    chart_data, table_rows = zip(*sorted_pairs)
                    rows[-len(chart_data):] = table_rows  # replace unsorted rows
                except Exception as e:
                    print(f"Sorting failed: {e}")

                rows.append(
                    f'|<$radio tiddler="$:/temp/selectedBoon" default="Total" field="boon_radio" value="Total"> Total Gen  </$radio>'
                    f' - <$radio tiddler="$:/temp/selectedBoon" default="Total" field="boon_radio" value="Average"> Gen/Sec  </$radio>'
                    f' - <$radio tiddler="$:/temp/selectedBoon" default="Total" field="boon_radio" value="Uptime"> Uptime Gen  </$radio>'
                    f' - {boon_name} Table|c'
                )
                rows.append("\n</$reveal>")

            # Sorted data for chart
            try:
                sorted_chart = sorted(chart_data, key=lambda x: float(x[6]) if len(x) > 6 else 0, reverse=True)
            except Exception:
                sorted_chart = chart_data

            json_chart = json.dumps(sorted_chart)
            boon_chart = f"""
<$echarts $text=```
option = {{
title: {{ text: '{boon_name} Uptime Generation', subtext: 'selectable legend for generation types' }},
legend: {{ orient:'horizontal', top:'10%', selected:{{'Total Gen':false,'Squad Gen':true,'Group Gen':false,'Self Gen':false}} }},
grid:{{top:'15%', containLabel:true}},
tooltip:{{top:'center'}},
dataset:{{dimensions:["Party","Name","Prof","Total Fight Time","Self Gen","Group Gen","Squad Gen","Total Gen"],source:{json_chart}}},
xAxis:{{}}, yAxis:{{type:'category',inverse:true}},
dataZoom:[{{type:'slider',yAxisIndex:0,filterMode:'none', start:0, end:60}},{{type:'inside',yAxisIndex:0,filterMode:'none'}}],
series:[{{type:'bar',name:'Total Gen',encode:{{x:'Total Gen',y:'Name'}}}},
{{type:'bar',name:'Squad Gen',encode:{{x:'Squad Gen',y:'Name'}}}},
{{type:'bar',name:'Group Gen',encode:{{x:'Group Gen',y:'Name'}}}},
{{type:'bar',name:'Self Gen',encode:{{x:'Self Gen',y:'Name'}}}}]
}};
```$height="900px" $width="100%" $theme="dark"/>
"""
            rows.append('  </div>\n  <div class="flex-col border">\n\n')
            rows.append(boon_chart)
            rows.append("\n  </div>\n</div>\n")
            rows.append("\n</$reveal>")

        rows.append("\n</div>")
        tid_text = "\n".join(rows)
        temp_title = f"{tid_date_time}-Boon-Generation-Detailed"
        append_tid_for_output(
            create_new_tid_from_template(
                temp_title,
                "Boons - Detailed",
                tid_text,
                fields={"boon_radio": "Total", "boon_selected": next(iter(boons.values()), "")},
            ),
            tid_list,
        )

    elif layout == "summary":
        # --- Summary Layout (one big table with all boons as columns) ---
        if category not in CATEGORY_ORDER:
            raise ValueError(f"Invalid category for summary layout: {category}")

        boons_meta = {
            bid: {
                "name": name,
                "icon": buff_data.get(bid, {}).get("icon", ""),
                "stacking": buff_data.get(bid, {}).get("stacking", False),
            }
            for bid, name in boons.items()
            if bid in buff_data
        }

        for toggle in TOGGLES:
            rows.append(f'<$reveal stateTitle="$:/temp/selectedBoon" default="Total" stateField="boon_radio" '
                        f'type="match" text="{toggle}" animate="yes">\n')
            rows.append(build_table_header(boons_meta, include_icons=bool(boon_type)))

            for player in top_stats.get("player", {}).values():
                if player.get("active_time", 0) == 0:
                    continue
                row_html, _ = build_player_row(player, boons_meta, category, toggle, buff_data)
                rows.append(row_html)

            caption = CATEGORY_CAPTIONS.get(category, category)
            rows.append(
                f'|<$radio tiddler="$:/temp/selectedBoon" default="Total" field="boon_radio" value="Total"> Total Gen  </$radio>'
                f' - <$radio tiddler="$:/temp/selectedBoon" default="Total" field="boon_radio" value="Average"> Gen/Sec  </$radio>'
                f' - <$radio tiddler="$:/temp/selectedBoon" default="Total" field="boon_radio" value="Uptime"> Uptime Gen  </$radio>'
                f' - {caption} Table|c'
            )
            rows.append("\n</$reveal>")

        rows.append("\n</div>")
        tid_text = "\n".join(rows)
        caption_out = f"{boon_type+'-' if boon_type else ''}{CATEGORY_CAPTIONS.get(category, category)}"
        temp_title = f"{tid_date_time}-{caption_out.replace(' ','-')}"
        append_tid_for_output(
            create_new_tid_from_template(
                temp_title,
                caption_out,
                tid_text,
                fields={"boon_radio": "Total", "boon_selected": next(iter(boons.values()), "")},
            ),
            tid_list,
        )

    else:
        raise ValueError("layout must be 'focus' or 'summary'")

def build_boon_summary(top_stats: dict, boons: dict, category: str, buff_data: dict, tid_date_time: str, boon_type = None) -> None:
	"""Print a table of boon uptime stats for all players in the log."""
	
	# Initialize a list to hold the rows of the table
	rows = []
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	
	# Iterate for "Total" and "Average" views
	for toggle in ["Total", "Average", "Uptime"]:
		# Add a reveal widget to toggle between Total and Average views
		rows.append(f'<$reveal stateTitle=<<currentTiddler>> stateField="boon_radio" type="match" text="{toggle}" animate="yes">\n')

		# Create table header
		header = "|thead-dark table-caption-top table-hover sortable|k\n"
		header += "|!Party |!Name | !Prof | !{{FightTime}} |"
		# Add a column for each boon
		for boon_id, boon_name in boons.items():
			if boon_type:
				skillIcon = buff_data[boon_id]["icon"]
				header += f" ![img width=24 [{boon_name}|{skillIcon}]] |"
			else:
				header += "!{{"+f"{boon_name}"+"}}|"
		header += "h"

		rows.append(header)

		# Create a mapping from category to caption
		category_caption = {
			'selfBuffs': "Self Generation", 
			'groupBuffs': "Group Generation", 
			'squadBuffs': "Squad Generation", 
			'totalBuffs': "Total Generation"
		}
		# Get the caption for the current category
		caption = category_caption[category] or ""

		# Build the table body by iterating over each player
		for player in top_stats["player"].values():
			if player["active_time"] == 0:
				continue
			account = player["account"]
			name = player["name"]
			tt_name = f'<span data-tooltip="{account}">{name}</span>'
			#print(f"Check Logs for {account} {name} with ActiveTime: {player['active_time']} and Num_Fights: {player['num_fights']}")
			# Create a row for the player with basic info
			row = f"| { player['last_party']} |{tt_name} | {{{{{player['profession']}}}}} {player['profession'][:3]} | {player['active_time'] / 1000:,.1f}|"

			# Iterate over each boon
			for boon_id in boons:
				# Check if the boon is not in player's category, set entry to "-"
				if boon_id not in player[category]:
					entry = " - "
				else:
					# Determine if the boon is stacking
					stacking = buff_data[boon_id].get('stacking', False)                
					num_fights = player["num_fights"]
					group_supported = player["group_supported"]
					squad_supported = player["squad_supported"]

					# Calculate generation and uptime percentage based on category
					if category == "selfBuffs":
						generation_ms = player[category][boon_id]["generation"]
						wasted_ms = player[category][boon_id]["wasted"]
						if stacking:
							uptime_percentage = round((generation_ms / player['active_time']), 3)
							wasted_percentage = round((wasted_ms / player['active_time']), 3)
						else:
							uptime_percentage = round((generation_ms / player['active_time']) * 100, 3)
							wasted_percentage = round((wasted_ms / player['active_time']) * 100, 3)
					elif category == "groupBuffs":
						generation_ms = player[category][boon_id]["generation"]
						wasted_ms = player[category][boon_id]["wasted"]
						if group_supported == num_fights:
							uptime_percentage = 0
							wasted_percentage = 0
						elif stacking:
							uptime_percentage = round((generation_ms / player['active_time']) / ((group_supported - num_fights)/num_fights), 3)
							wasted_percentage = round((wasted_ms / player['active_time']) / ((group_supported - num_fights)/num_fights), 3)
						else:
							uptime_percentage = round((generation_ms / player['active_time']) / ((group_supported - num_fights)/num_fights) * 100, 3)
							wasted_percentage = round((wasted_ms / player['active_time']) / ((group_supported - num_fights)/num_fights) * 100, 3)
					elif category == "squadBuffs":
						generation_ms = player[category][boon_id]["generation"]
						wasted_ms = player[category][boon_id]["wasted"]
						if stacking:
							uptime_percentage = round((generation_ms / player['active_time']) / ((squad_supported - num_fights)/num_fights), 3)
							wasted_percentage = round((wasted_ms / player['active_time']) / ((squad_supported - num_fights)/num_fights), 3)
						else:
							uptime_percentage = round((generation_ms / player['active_time']) / ((squad_supported - num_fights)/num_fights) * 100, 3)
							wasted_percentage = round((wasted_ms / player['active_time']) / ((squad_supported - num_fights)/num_fights) * 100, 3)
					elif category == "totalBuffs":
						generation_ms = 0
						wasted_ms = 0
						if boon_id in player["selfBuffs"]:
							generation_ms += player["selfBuffs"][boon_id]["generation"]
							wasted_ms += player["selfBuffs"][boon_id]["wasted"] 
						if boon_id in player["squadBuffs"]:
							generation_ms += player["squadBuffs"][boon_id]["generation"]
							wasted_ms += player["squadBuffs"][boon_id]["wasted"]
						if stacking:
							uptime_percentage = round((generation_ms / player['active_time']) / (squad_supported), 3)
							wasted_percentage = round((wasted_ms / player['active_time']) / (squad_supported), 3)
						else:
							uptime_percentage = round((generation_ms / player['active_time']) / (squad_supported) * 100, 3)
							wasted_percentage = round((wasted_ms / player['active_time']) / (squad_supported) * 100, 3)
					else:
						raise ValueError(f"Invalid category: {category}")
					
					# Determine entry based on toggle

					if toggle == "Total":
						#entry = f"{generation_ms/1000:,.1f}"
						entry = f'<span data-tooltip="{(int(wasted_ms)/1000):,.2f} Wasted">{(int(generation_ms)/1000):,.1f}</span>'
					elif toggle == "Average":
						#entry = f"{generation_ms/player['active_time']:,.1f}"
						active_time = player['active_time']
						entry = f'<span data-tooltip="{(int(wasted_ms)/active_time):,.2f} Wasted">{(int(generation_ms)/active_time):,.1f}</span>'
					else:
						if stacking:
							uptime_percentage = f"{uptime_percentage:.2f}"
							wasted_percentage = f"{wasted_percentage:.2f}"
							entry = f'<span data-tooltip="{wasted_percentage} Wasted">{uptime_percentage}</span>'					
						else:
							uptime_percentage = f"{uptime_percentage:.2f}%"
							wasted_percentage = f"{wasted_percentage:.2f}%"							
							entry = f'<span data-tooltip="{wasted_percentage} Wasted">{uptime_percentage}</span>'
				# Append entry to the row
				row += f" {entry}|"
			
			# Append the row to the rows list
			rows.append(row)
		
		# Append the footer with radio buttons to toggle views
		rows.append(f'|<$radio field="boon_radio" value="Total"> Total Gen  </$radio> - <$radio field="boon_radio" value="Average"> Gen/Sec  </$radio> - <$radio field="boon_radio" value="Uptime"> Uptime Gen  </$radio> - {caption} Table|c')
		rows.append("\n</$reveal>")
	
	rows.append("\n\n</div>")
	
	# Join rows into a single text block
	tid_text = "\n".join(rows)

	if boon_type:
		caption = f"{boon_type}-{caption}"
	# Create a title for the table
	temp_title = f"{tid_date_time}-{caption.replace(' ','-')}"

	# Append the table to the output list
	append_tid_for_output(
		create_new_tid_from_template(temp_title, caption, tid_text, fields={"boon_radio": "Total", "boon_selected": "Might",}),
		tid_list
	)    


def build_uptime_summary(top_stats: dict, boons: dict, buff_data: dict, caption: str, tid_date_time: str, boon_type = None) -> None:
	"""Print a table of boon uptime stats for all players in the log.

	The table will contain the following columns:

	- Name
	- Profession
	- Account
	- Fight Time
	- Average uptime for each boon
	"""
	rows = []
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	# Build the player table header
	header = "|thead-dark table-caption-top table-hover sortable|k\n"
	header += "|!Party |!Name | !Prof | !{{FightTime}} |"
	for boon_id, boon_name in boons.items():
		if boon_id not in buff_data:
			continue
		skillIcon = buff_data[boon_id]["icon"]

		header += f" ![img width=24 [{boon_name}|{skillIcon}]] |"
	header += "h"

	non_damaging_conditions = [
		'b720', #Blinded
		'b721', #Crippled
		'b722', #Chilled
		'b727', #Immobile
		'b742', #Weakness
		'b791', #Fear
		'b26766', #Slow
		'b27705' #Taunt
		]
	# Build the Squad table rows
	header2 = f"|Squad Average Uptime |<|<|<|"
	for boon_id in boons:
		if boon_id not in buff_data:
			continue
		if boon_id not in top_stats["overall"]["buffUptimes"]:
			detailEntry = " - "
		elif boon_id in non_damaging_conditions:
			offset_uptime_ms = top_stats["overall"]["buffUptimes"][boon_id]["uptime_ms"] - top_stats["overall"]["buffUptimes"][boon_id]["resist_reduction"]
			offset_uptime_percentage = round((offset_uptime_ms / top_stats['overall']["active_time"]) * 100, 3)
			offset_uptime_percentage = f"{offset_uptime_percentage:.3f}%"			
			uptime_ms = top_stats["overall"]["buffUptimes"][boon_id]["uptime_ms"]
			uptime_percentage = round((uptime_ms / top_stats['overall']["active_time"]) * 100, 3)
			uptime_percentage = f"{uptime_percentage:.3f}%"
			tooltip = f"Uptime without resist reduction:<br>{uptime_percentage}"
			# Add the tooltip to the row
			detailEntry = f'<div class="xtooltip"> @@color:green; {offset_uptime_percentage}% @@ <span class="xtooltiptext" style="padding-left: 5px">'+tooltip+'</span></div>'
		else:
			uptime_ms = top_stats["overall"]["buffUptimes"][boon_id]["uptime_ms"]
			uptime_percentage = round((uptime_ms / top_stats['overall']["active_time"]) * 100, 3)
			detailEntry = f"{uptime_percentage:.3f}%"
		header2 += f" {detailEntry}|" 
	header2 += "h"

	rows.append(header)
	rows.append(header2)
	#build party table rows
	
	#footer, moved to header 
	for group in top_stats["overall"]["buffUptimes"]['group']:
		footer = f"|Party-{group} Average Uptime |<|<|<|"
		for boon_id in boons:
			if boon_id not in buff_data:
				continue
			if boon_id not in top_stats["overall"]["buffUptimes"]['group'][group]:
				detailEntry = " - "
			elif boon_id in non_damaging_conditions:
				offset_uptime_ms = top_stats["overall"]["buffUptimes"]['group'][group][boon_id]["uptime_ms"] - top_stats["overall"]["buffUptimes"]['group'][group][boon_id]["resist_reduction"]
				offset_uptime_percentage = round((offset_uptime_ms / top_stats['overall']['group_data'][group]['fight_time']) * 100, 3)
				offset_uptime_percentage = f"{offset_uptime_percentage:.3f}%"
				uptime_ms = top_stats["overall"]["buffUptimes"]['group'][group][boon_id]["uptime_ms"]
				uptime_percentage = round((uptime_ms / top_stats['overall']['group_data'][group]['fight_time']) * 100, 3)
				uptime_percentage = f"{uptime_percentage:.3f}%"
				tooltip = f"Uptime without resist reduction:<br>{uptime_percentage}"
				# Add the tooltip to the row
				detailEntry = f'<div class="xtooltip"> @@color:green; {offset_uptime_percentage}% @@ <span class="xtooltiptext" style="padding-left: 5px">'+tooltip+'</span></div>'
			else:
				uptime_ms = top_stats["overall"]["buffUptimes"]['group'][group][boon_id]["uptime_ms"]
				uptime_percentage = round((uptime_ms / top_stats['overall']['group_data'][group]['fight_time']) * 100, 3)
				detailEntry = f"{uptime_percentage:.3f}%"
			footer += f" {detailEntry}|"
		footer += "h"	#footer, moved to header
		rows.append(footer)

	# Build the table body
	for player in top_stats["player"].values():
		if player["active_time"] == 0:
			continue	
		account = player["account"]
		name = player["name"]
		tt_name = f'<span data-tooltip="{account}">{name}</span>'
		row = f"| {player['last_party']} |{tt_name} |"+" {{"+f"{player['profession']}"+"}}"+f" {player['profession'][:3]} "+f"| {player['active_time'] / 1000:,.1f}|"
		for boon_id in boons:
			if boon_id not in buff_data:
				continue

			if boon_id not in player["buffUptimes"]:
				detailEntry = " - "
			elif boon_id in non_damaging_conditions:
				offset_uptime_ms = player["buffUptimes"][boon_id]["uptime_ms"] - player["buffUptimes"][boon_id]["resist_reduction"]
				offset_uptime_percentage = round(offset_uptime_ms / player['active_time'] * 100, 3)
				offset_uptime_percentage = f"{offset_uptime_percentage:.3f}%"
				uptime_ms = player["buffUptimes"][boon_id]["uptime_ms"]
				uptime_percentage = round(uptime_ms / player['active_time'] * 100, 3)
				uptime_percentage = f"{uptime_percentage:.3f}%"
				tooltip = f"Uptime without resist reduction:<br>{uptime_percentage}"
				# Add the tooltip to the row
				detailEntry = f'<div class="xtooltip"> @@color:green; {offset_uptime_percentage}% @@ <span class="xtooltiptext" style="padding-left: 5px">'+tooltip+'</span></div>'
			else:
				uptime_ms = player["buffUptimes"][boon_id]["uptime_ms"]
				uptime_percentage = round(uptime_ms / player['active_time'] * 100, 3)
				detailEntry = f"{uptime_percentage:.3f}%"

			row += f" {detailEntry}|"
		rows.append(row)
	rows.append(f"|{caption} Table|c")

	rows.append("\n\n</div>")
	#push table to tid_list for output
	tid_text = "\n".join(rows)

	if boon_type:
		caption = f"{boon_type}-{caption}"
	append_tid_for_output(
		create_new_tid_from_template(f"{tid_date_time}-{caption.replace(' ','-')}", caption, tid_text),
		tid_list
	)

def build_debuff_uptime_summary(top_stats: dict, boons: dict, buff_data: dict, caption: str, tid_date_time: str) -> None:
	"""Print a table of boon uptime stats for all players in the log.

	The table will contain the following columns:

	- Name
	- Profession
	- Account
	- Fight Time
	- Average uptime for each boon
	- Count of applied debuffs

	Args:
		top_stats (dict): Dictionary containing top statistics for players.
		boons (dict): Dictionary containing boons and their names.
		buff_data (dict): Dictionary containing information about each buff.
		caption (str): The caption for the table.
		tid_date_time (str): A string to use as the date and time for the table id.
	"""
	rows = []
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	# Build the player table header
	header = "|thead-dark table-caption-top table-hover sortable|k\n"
	header += "|!Party |!Name | !Prof | !{{FightTime}} |"
	for boon_id, boon_name in boons.items():
		if boon_id not in buff_data:
			continue
		skillIcon = buff_data[boon_id]["icon"]

		header += f"! [img width=24 [{boon_name}|{skillIcon}]] |"
	header += " !Count|"
	header += "h"

	# Build the Squad table rows
	header2 = f"|Total Generated |<|<|<|"
	applied_counts = 0
	for boon_id in boons:
		if boon_id not in buff_data:
			continue
		if boon_id not in top_stats["overall"]["targetBuffs"]:
			uptime_percentage = " - "
		else:
			applied_counts += top_stats["overall"]["targetBuffs"][boon_id]["applied_counts"]
			uptime_ms = top_stats["overall"]["targetBuffs"][boon_id]["uptime_ms"]
			uptime_percentage = round((uptime_ms / 1000), 3)			
			uptime_percentage = f"{uptime_percentage:,.0f}"
		header2 += f" {uptime_percentage}|" 
	header2 += f" {applied_counts}|" 
	header2 += "h"

	rows.append(header)
	rows.append(header2)

	# Build the table body
	for player in top_stats["player"].values():
		debuff_data = {"b70350": [0.10,'targetDamage1S'], "b70806": [0.10,'targetPowerDamage1S']}
		account = player["account"]
		name = player["name"]
		tt_name = f'<span data-tooltip="{account}">{name}</span>'
		row = f"| {player['last_party']} |{tt_name} |"+" {{"+f"{player['profession']}"+"}}"+f" {player['profession'][:3]} "+f"| {player['active_time'] / 1000:,.1f}|"
		applied_counts = 0
		for boon_id in boons:
			entry = ""
			if boon_id not in buff_data:
				continue

			if boon_id not in player["targetBuffs"]:
				uptime_percentage = " - "
			else:
				applied_counts += player["targetBuffs"][boon_id]["applied_counts"]
				uptime_ms = player["targetBuffs"][boon_id]["uptime_ms"]
				uptime_percentage = round((uptime_ms / 1000), 3)				
				uptime_percentage = f"{uptime_percentage:,.0f}"
				if boon_id in debuff_data:
					damage_gained = player['targetBuffs'][boon_id]['damage_gained']
					entry = f'<span data-tooltip="Damage Gained: {damage_gained:,.0f}">{uptime_percentage}</span>'
				else:
					entry = uptime_percentage

			row += f" {entry}|"
		row += f" {applied_counts:,.0f}|"

		rows.append(row)
	rows.append(f"|{caption} Table|c")

	rows.append("\n\n</div>")
	#push table to tid_list for output
	tid_text = "\n".join(rows)

	append_tid_for_output(
		create_new_tid_from_template(f"{tid_date_time}-{caption.replace(' ','-')}", caption, tid_text),
		tid_list
	)

def build_healing_summary(top_stats: dict, caption: str, tid_date_time: str) -> None:
	"""Build and print a table of healing stats for all players in the log.

	Args:
		top_stats (dict): Dictionary containing top statistics for players.
		caption (str): The caption for the table.
		tid_date_time (str): A string to use as the date and time for the table id.
	"""
	# Dictionary to store healing statistics for each player
	healing_stats = {}

	# Collect healing and barrier stats for players
	for healer in top_stats['players_running_healing_addon']:
		name = healer.split('|')[0]
		profession = healer.split('|')[1]
		account = top_stats['player'][healer]['account']
		fight_time = top_stats['player'][healer]['active_time']
		last_party = top_stats['player'][healer]['last_party']

		healing_stats[healer] = {
			'name': name,
			'profession': profession,
			'account': account,
			'fight_time': fight_time,
			"last_party": last_party,
		}

		# Get healing stats if available
		if 'extHealingStats' in top_stats['player'][healer]:
			healing_stats[healer]['healing'] = top_stats['player'][healer]['extHealingStats'].get('outgoing_healing', 0)
			healing_stats[healer]['downed_healing'] = top_stats['player'][healer]['extHealingStats'].get('downed_healing', 0)
			healing_stats[healer]['squad_healing'] = top_stats['player'][healer]['extHealingStats'].get('squad_healing', 0)
			healing_stats[healer]['group_healing'] = top_stats['player'][healer]['extHealingStats'].get('group_healing', 0)
			healing_stats[healer]['self_healing'] = top_stats['player'][healer]['extHealingStats'].get('self_healing', 0)
			healing_stats[healer]['off_squad_healing'] = top_stats['player'][healer]['extHealingStats'].get('off_squad_healing', 0)
			healing_stats[healer]['squad_downed_healing'] = top_stats['player'][healer]['extHealingStats'].get('squad_downed_healing', 0)
			healing_stats[healer]['group_downed_healing'] = top_stats['player'][healer]['extHealingStats'].get('group_downed_healing', 0)
			healing_stats[healer]['self_downed_healing'] = top_stats['player'][healer]['extHealingStats'].get('self_downed_healing', 0)
			healing_stats[healer]['off_squad_downed_healing'] = top_stats['player'][healer]['extHealingStats'].get('off_squad_downed_healing', 0)

		# Get barrier stats if available
		if 'extBarrierStats' in top_stats['player'][healer]:
			healing_stats[healer]['barrier'] = top_stats['player'][healer]['extBarrierStats'].get('outgoing_barrier', 0)
			healing_stats[healer]['squad_barrier'] = top_stats['player'][healer]['extBarrierStats'].get('squad_barrier', 0)
			healing_stats[healer]['group_barrier'] = top_stats['player'][healer]['extBarrierStats'].get('group_barrier', 0)
			healing_stats[healer]['self_barrier'] = top_stats['player'][healer]['extBarrierStats'].get('self_barrier', 0)
			healing_stats[healer]['off_squad_barrier'] = top_stats['player'][healer]['extBarrierStats'].get('off_squad_barrier', 0)

	# Sort healing stats by total healing amount in descending order
	sorted_healing_stats = sorted(healing_stats.items(), key=lambda x: x[1]['healing'], reverse=True)
	
	# Initialize HTML rows for the table
	rows = []
	rows.append('<div class="flex-row">\n    <div class="flex-col border">\n')
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	
	# Build the table header
	for toggle in ["Total", "Squad", "Group", "Self", "OffSquad"]:
		rows.append(f'<$reveal stateTitle=<<currentTiddler>> stateField="category_heal" type="match" text="{toggle}" animate="yes">\n')
		header = "|thead-dark table-caption-top table-hover sortable|k\n"
		header += "|!Party |!Name | !Prof | !{{FightTime}} | !{{Healing}} | !{{HealingPS}} | !{{Barrier}} | !{{BarrierPS}} | !{{DownedHealing}} | !{{DownedHealingPS}} |h"
		rows.append(header)

		# Build the table body
		for healer in sorted_healing_stats:
			name = healer[0].split('|')[0]
			account = healer[1]['account']
			tt_name = f'<span data-tooltip="{account}">{name}</span>'
			if (healer[1]['healing'] + healer[1]['downed_healing'] + healer[1]['barrier']):
				fighttime = healer[1]['fight_time'] / 1000
				if toggle == "Total":
					row = f"| {healer[1]['last_party']} |{tt_name} |"+" {{"+f"{healer[1]['profession']}"+"}}"+f" {healer[1]['profession'][:3]}"+" "+f"| {fighttime:,.1f}|"
					row += f" {healer[1]['healing']:,}| {healer[1]['healing'] / fighttime:,.2f}| {healer[1]['barrier']:,}|"
					row += f"{healer[1]['barrier'] / fighttime:,.2f}| {healer[1]['downed_healing']:,}| {healer[1]['downed_healing'] / fighttime:,.2f}|"
				elif toggle == "Squad":
					row = f"| {healer[1]['last_party']} |{tt_name} |"+" {{"+f"{healer[1]['profession']}"+"}}"+f" {healer[1]['profession'][:3]}"+" "+f"| {fighttime:,.1f}|"
					row += f" {healer[1]['squad_healing']:,}| {healer[1]['squad_healing'] / fighttime:,.2f}| {healer[1]['squad_barrier']:,}|"
					row += f"{healer[1]['squad_barrier'] / fighttime:,.2f}| {healer[1]['squad_downed_healing']:,}| {healer[1]['squad_downed_healing'] / fighttime:,.1f}|"
				elif toggle == "Group":
					row = f"| {healer[1]['last_party']} |{tt_name} |"+" {{"+f"{healer[1]['profession']}"+"}}"+f" {healer[1]['profession'][:3]}"+" "+f"| {fighttime:,.1f}|"
					row += f" {healer[1]['group_healing']:,}| {healer[1]['group_healing'] / fighttime:,.2f}| {healer[1]['group_barrier']:,}|"
					row += f"{healer[1]['group_barrier'] / fighttime:,.2f}| {healer[1]['group_downed_healing']:,}| {healer[1]['group_downed_healing'] / fighttime:,.1f}|"
				elif toggle == "Self":
					row = f"| {healer[1]['last_party']} |{tt_name} |"+" {{"+f"{healer[1]['profession']}"+"}}"+f" {healer[1]['profession'][:3]}"+" "+f"| {fighttime:,.1f}|"
					row += f" {healer[1]['self_healing']:,}| {healer[1]['self_healing'] / fighttime:,.2f}| {healer[1]['self_barrier']:,}|"
					row += f"{healer[1]['self_barrier'] / fighttime:,.2f}| {healer[1]['self_downed_healing']:,}| {healer[1]['self_downed_healing'] / fighttime:,.1f}|"
				elif toggle == "OffSquad":
					row = f"| {healer[1]['last_party']} |{tt_name} |"+" {{"+f"{healer[1]['profession']}"+"}}"+f" {healer[1]['profession'][:3]}"+" "+f"| {fighttime:,.1f}|"
					row += f" {healer[1]['off_squad_healing']:,}| {healer[1]['off_squad_healing'] / fighttime:,.2f}| {healer[1]['off_squad_barrier']:,}|"
					row += f"{healer[1]['off_squad_barrier'] / fighttime:,.2f}| {healer[1]['off_squad_downed_healing']:,}| {healer[1]['off_squad_downed_healing'] / fighttime:,.1f}|"
				rows.append(row)

	# Add caption row and finalize table
		rows.append(f'|<$radio field="category_heal" value="Total"> Total  </$radio> - <$radio field="category_heal" value="Squad"> Squad  </$radio> - <$radio field="category_heal" value="Group"> Group  </$radio> - <$radio field="category_heal" value="Self"> Self  </$radio>  - <$radio field="category_heal" value="OffSquad"> OffSquad  </$radio>- {caption} Table|c')
		rows.append("\n</$reveal>")
	#rows.append(f"|{caption} Table|c")
	rows.append("\n\n</div>")
	rows.append('</div>\n    <div class="flex-col border">')
	Barrier_Boxplot = f"{tid_date_time}-extBarrierStats-squad_barrier-boxplot"
	Healing_BoxPlot = f"{tid_date_time}-extHealingStats-squad_healing-boxplot"
	rows.append("{{"+Healing_BoxPlot+"}}\n\n{{"+Barrier_Boxplot+"}}\n\n</div>\n\n</div>\n\n")

	
	# Convert rows to text and append to output list
	tid_text = "\n".join(rows)
	append_tid_for_output(
		create_new_tid_from_template(f"{tid_date_time}-{caption.replace(' ','-')}", caption, tid_text, fields={"category_heal": "Group"}),
		tid_list
	)

def build_personal_damage_modifier_summary(top_stats: dict, personal_damage_mod_data: dict, damage_mod_data: dict, caption: str, tid_date_time: str) -> None:
	"""Print a table of personal damage modifier stats for all players in the log running the extension.

	This function iterates over the personal_damage_mod_data dictionary, which contains lists of modifier IDs for each profession.
	It then builds a table with the following columns:
		- Name
		- Prof
		- Account
		- Fight Time
		- Damage Modifier Icons

	The table will have one row for each player running the extension, and the columns will contain the player's name, profession, account name, fight time, and the icons of the modifiers they have active.

	The function will also add the table to the tid_list for output.
	"""
	for profession in personal_damage_mod_data:
		if profession == 'total':
			continue
		prof_mod_list = personal_damage_mod_data[profession]

		rows = []
		
		rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
		# Build the table header
		header = "|thead-dark table-caption-top table-hover sortable|k\n"
		# Add the caption to the header
		header += f"| {caption} |c\n"
		# Add the columns to the header
		header += "|!Party |!Name | !Prof | !{{FightTime}} |"
		
		for mod_id in prof_mod_list:
			# Get the icon and name of the modifier
			icon = damage_mod_data[mod_id]["icon"]
			name = damage_mod_data[mod_id]["name"]
			# Add the icon and name to the header
			header += f"![img width=24 [{name}|{icon}]]|"
		# Add the header separator
		header += "h"

		rows.append(header)

		# Build the table body
		for player_name, player_data in top_stats['player'].items():
			# Check if the player is running the extension
			if player_data['profession'] == profession:
				account = player_data['account']
				name = player_data['name']
				tt_name = f'<span data-tooltip="{account}">{name}</span>'
				# Build the row
				row = f"| {player_data['last_party']} |{tt_name} | {player_data['profession']} | {player_data['active_time'] / 1000:,.1f}|"
				# Iterate over each modifier and add the details to the row
				for mod in prof_mod_list:
					if mod in player_data['damageModifiers']:
						# Get the hit count and total hit count
						hit_count = player_data['damageModifiers'][mod]['hitCount']
						total_count = player_data['damageModifiers'][mod]['totalHitCount']
						# Get the damage gain and total damage
						damage_gain = player_data['damageModifiers'][mod]['damageGain']
						total_damage = player_data['damageModifiers'][mod]['totalDamage']
						# Calculate the damage percentage and hit percentage
						if damage_gain == 0:
							damage_pct =  0
						else:
							damage_pct = damage_gain / total_damage * 100
						if total_count == 0:
							hit_pct = 0
						else:								
							hit_pct = hit_count / total_count * 100
						# Build the tooltip
						tooltip = f"{hit_count} of {total_count} ({hit_pct:.2f}% hits)<br>Damage Gained: {damage_gain:,.0f}<br>"
						# Add the tooltip to the row
						detailEntry = f'<div class="xtooltip"> {damage_pct:.2f}% <span class="xtooltiptext" style="padding-left: 5px">'+tooltip+'</span></div>'
						row += f" {detailEntry}|"
					else:
						# If the modifier is not active, add a - to the row
						row += f" - |"
				# Add the row to the table
				rows.append(row)

		# Add the table to the tid_list for output
		tid_text = "\n".join(rows)

		append_tid_for_output(
			create_new_tid_from_template(f"{tid_date_time}-{caption.replace(' ','-')}-{profession}", "{{"+f"{profession}"+"}}", tid_text),
			tid_list
		)

def build_shared_damage_modifier_summary(top_stats: dict, damage_mod_data: dict, caption: str, tid_date_time: str) -> None:
	"""Print a table of shared damage modifier stats for all players in the log running the extension.

	This function iterates over the damage_mod_data dictionary, which contains data about each damage modifier.
	For each modifier, it checks if the modifier is shared and if it is, it adds the modifier to the shared_mod_list.
	The function then builds a table with the following columns:
	* Name (player name)
	* Prof (profession icon)
	* {{FightTime}} (fight time)
	* columns for each shared modifier with the following data:
		+ hits (number of hits with the modifier)
		+ hits percentage (percentage of total hits with the modifier)
		+ damage gain (total damage gained from the modifier)
		+ damage percentage (percentage of total damage gained from the modifier)

	The function then pushes the table to the tid_list for output.
	"""
	shared_mod_list = []
	for modifier in damage_mod_data:
		if damage_mod_data[modifier]['shared'] and modifier not in shared_mod_list:
			shared_mod_list.append(modifier)

	rows = []
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	header = "|thead-dark table-caption-top table-hover sortable|k\n"
	header += f"| {caption} |c\n"
	header += "|!Name | !Prof |!Account | !{{FightTime}} |"
	for mod_id in shared_mod_list:
		icon = damage_mod_data[mod_id]["icon"]
		name = damage_mod_data[mod_id]["name"]
		header += f"![img width=24 [{name}|{icon}]]|"
	header += "h"

	rows.append(header)

	for player in top_stats['player'].values():
		row = f"|{player['name']} |"+" {{"+f"{player['profession']}"+"}} "+f"|{player['account'][:32]} | {player['active_time'] / 1000:,.1f}|"
		for modifier_id in shared_mod_list:
			if modifier_id in player['damageModifiers']:
				modifier_data = player['damageModifiers'][modifier_id]
				hit_count = modifier_data['hitCount']
				total_count = modifier_data['totalHitCount']
				damage_gain = modifier_data['damageGain']
				total_damage = modifier_data['totalDamage']
				damage_pct = 0
				if total_damage > 0:
					damage_pct = (damage_gain / total_damage) * 100
				hit_pct = 0
				if total_count > 0:
					hit_pct = hit_count / total_count * 100
				tooltip = f" {hit_count} of {total_count} ({hit_pct:.2f}% hits)<br> Damage Gained: {damage_gain:,.0f}"
				detail_entry = f'<div class="xtooltip"> {damage_pct:.2f}% <span class="xtooltiptext" style="padding-left: 5px"> {tooltip} </span></div>'
				row += f" {detail_entry}|"
			else:
				row += f" - |"
		rows.append(row)
	rows.append(f"|{caption} Damage Modifiers Table|c")

	rows.append("\n\n</div>")

	# Push table to tid_list for output
	tid_text = "\n".join(rows)

	append_tid_for_output(
		create_new_tid_from_template(f"{tid_date_time}-{caption.replace(' ','-')}", caption, tid_text),
		tid_list
	)

def build_skill_cast_summary(skill_casts_by_role: dict, skill_data: dict, caption: str, skill_casts_by_role_limit: int, tid_date_time: str) -> None:
	"""
	Print a table of skill cast stats for all players in the log running the extension.

	This function iterates over the skill_casts_by_role dictionary, which contains the total number of casts for each skill and the number of casts per player.

	The function builds a table with the following columns:
	* Name (player name)
	* Prof (profession icon)
	* {{FightTime}} (fight time)
	* [skill_name] (total number of casts per skill per minute)

	The function appends the table to the tid_list for output.
	"""
	for prof_role, cast_data in skill_casts_by_role.items():
		# Get the total number of casts per skill
		cast_skills = cast_data['total']
		sorted_cast_skills = sorted(cast_skills.items(), key=lambda x: x[1], reverse=True)
		rows = []
		
		rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
		header = "|thead-dark table-caption-top table-hover sortable|k\n"
		header += f"| {caption} |c\n"
		header += "|!Name | !Prof |!Account | !{{FightTime}} |!"
		apm_entry = f'<div class="xtooltip"> APM <span class="xtooltiptext" style="padding-left: 5px">Total Actions per Minute /<br>APM without Autos</span></div>'
		header += f" {apm_entry}|"
		# Add the skill names to the header
		i = 0
		for skill, count in sorted_cast_skills:
			if i < skill_casts_by_role_limit:
				skill_icon = skill_data[skill]['icon']
				skill_name = skill_data[skill]['name']
				skill_auto = skill_data[skill]['auto']
				if skill_auto:
					header += f'![img width=24 class="tc-test-case-wrapper" [{skill_name}|{skill_icon}]]|'				
				else:
					header += f"![img width=24 [{skill_name}|{skill_icon}]]|"
			i+=1
		header += "h"

		rows.append(header)

		# Iterate over each player and add their data to the table
		for player, player_data in cast_data.items():
			if player == 'total' or player_data['ActiveTime'] == 0:
				continue

			name, profession, account = player.split("|")
			profession = "{{" + profession + "}}"
			#account = player_data['account']
			time_secs = player_data['ActiveTime']
			time_mins = time_secs / 60
			apm = round(player_data['total']/time_mins)
			apm_no_auto = round(player_data['total_no_auto']/time_mins)
		
			row = f"|{name} |" + " " + f"{profession} " + f"|{account} |" + f"{time_secs:,.1f}|" + f" {apm}/{apm_no_auto} |"
			# Add the skill casts per minute to the row
			i = 0
			for skill, count in sorted_cast_skills:
				if i < skill_casts_by_role_limit:
					if skill in player_data['Skills']:
						row += f" {(player_data['Skills'][skill] / time_mins):.2f}|"
					else:
						row += f" - |"
				i+=1
			rows.append(row)

		rows.append(f"|{caption} / Minute|c")

		rows.append("\n\n</div>")
		# Push table to tid_list for output
		tid_text = "\n".join(rows)
		tid_title = f"{tid_date_time}-{caption.replace(' ','-')}-{prof_role}"
		tid_caption = profession + f"-{prof_role}"

		append_tid_for_output(
			create_new_tid_from_template(tid_title, tid_caption, tid_text),
			tid_list
		)

def build_combat_resurrection_stats_tid(top_stats: dict, skill_data: dict, buff_data: dict, IOL_revive: dict, killing_blow_rallies: dict, caption: str, tid_date_time: str) -> None:
	"""Build a table of combat resurrection stats for all players in the log running the extension.

	This function iterates over the top_stats dictionary and builds a dictionary with the following structure:
	{
		'res_skills': {skill_name: total_downed_healing},
		'players': {profession_name | player_name | active_time: {skill_name: downed_healing}}
	}

	The function then builds a table with the following columns:
	* Name (player name)
	* Prof (profession icon)
	* {{FightTime}} (fight time)
	* [skill_name] (total downed healing per skill)

	The function appends the table to the tid_list for output.

	"""
	combat_resurrect = {
		'res_skills': {},
		'players': {}
		}

	for player, player_data in top_stats['player'].items():
		prof_name = player_data['profession'] + '|' + player_data['name'] + '|' + str(player_data['account']) + '|' + str(player_data['last_party']) + '|' + str(player_data['active_time'])
		if 'skills' in player_data['extHealingStats']:

			for skill in player_data['extHealingStats']['skills']:

				if 'downedHealing' in player_data['extHealingStats']['skills'][skill]:
					if player_data['extHealingStats']['skills'][skill]['downedHealing'] > 0:
						downed_healing = player_data['extHealingStats']['skills'][skill]['downedHealing']
						total_hits = player_data['extHealingStats']['skills'][skill]['hits']

						if skill not in combat_resurrect['res_skills']:
							combat_resurrect['res_skills'][skill] = 0
						combat_resurrect['res_skills'][skill] = combat_resurrect['res_skills'].get(skill, 0) + downed_healing

						if prof_name not in combat_resurrect['players']:
							combat_resurrect['players'][prof_name] = {}

						if skill not in combat_resurrect['players'][prof_name]:
							combat_resurrect['players'][prof_name][skill] = {
								'total': 0,
								'hits': 0
							}

						combat_resurrect['players'][prof_name][skill]['total'] = combat_resurrect['players'][prof_name][skill].get('total', 0) + downed_healing
						combat_resurrect['players'][prof_name][skill]['hits'] = combat_resurrect['players'][prof_name][skill].get('hits', 0) + total_hits

		if player_data['name'] in IOL_revive:
			if 's10244' not in combat_resurrect['res_skills']:
				combat_resurrect['res_skills']['s10244'] = IOL_revive[player_data['name']]['casts']
			else:
				combat_resurrect['res_skills']['s10244'] = combat_resurrect['res_skills']['s10244'] + IOL_revive[player_data['name']]['casts']

			if prof_name not in combat_resurrect['players']:
				combat_resurrect['players'][prof_name] = {}

			if 's10244' not in combat_resurrect['players'][prof_name]:
				combat_resurrect['players'][prof_name]['s10244'] = {
					'total': 0,
					'hits': 0
				}
				combat_resurrect['players'][prof_name]['s10244']['total']  = IOL_revive[player_data['name']].get('hits', 0)
				combat_resurrect['players'][prof_name]['s10244']['hits']  = IOL_revive[player_data['name']].get('casts', 0)	

		kb_actor = f"{player_data['profession']}|{player_data['name']}|{player_data['account']}"
		if kb_actor in killing_blow_rallies['kb_players']:
			if 'kb_rally' not in combat_resurrect['res_skills']:
				combat_resurrect['res_skills']['kb_rally'] = killing_blow_rallies['kb_players'][kb_actor]
			else:
				combat_resurrect['res_skills']['kb_rally'] = combat_resurrect['res_skills']['kb_rally'] + killing_blow_rallies['kb_players'][kb_actor]

			if prof_name not in combat_resurrect['players']:
				combat_resurrect['players'][prof_name] = {}

			if 'kb_rally' not in combat_resurrect['players'][prof_name]:
				combat_resurrect['players'][prof_name]['kb_rally'] = {
					'total': 0,
					'hits': 0
				}
				combat_resurrect['players'][prof_name]['kb_rally']['total']  = killing_blow_rallies['kb_players'][kb_actor]
				combat_resurrect['players'][prof_name]['kb_rally']['hits']  = killing_blow_rallies['kb_players'][kb_actor]

	sorted_res_skills = sorted(combat_resurrect['res_skills'], key=combat_resurrect['res_skills'].get, reverse=True)

	combat_resurrect_tags = f"{tid_date_time}"
	combat_resurrect_title = f"{tid_date_time}-Combat-Resurrect"
	combat_resurrect_caption = f"{caption}"
	combat_resurrect_text = ""

	rows = []
	rows.append('Tooltip for `Total hits` may be overstated if the skill does more than just downed healing\n\n')
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	header = "|thead-dark table-caption-top table-hover sortable|k\n"
	header += "|Party |!@@display:block;width:150px;Name@@| !Prof | !{{FightTime}} |"
	for skill in sorted_res_skills:
		if skill in skill_data:
			skill_icon = skill_data[skill]['icon']
			skill_name = skill_data[skill]['name']
		elif skill.replace(skill[0], "b", 1) in buff_data:
			skill_icon = buff_data[skill.replace(skill[0], "b", 1)]['icon']
			skill_name = buff_data[skill.replace(skill[0], "b", 1)]['name']
		elif skill == "kb_rally":
			skill_icon = "https://wiki.guildwars2.com/images/6/6e/Renown_Heart_%28map_icon%29.png"
			skill_name = "Killing Blow Rally"
		else:
			skill_icon = "unknown.png"
			skill_name = skill
		header += f" ![img width=24 [{skill} - {skill_name}|{skill_icon}]]|"

	header += "h"

	rows.append(header)

	for player in combat_resurrect['players']:
		profession, name, account, group, active_time = player.split('|')
		time_secs = int(active_time) / 1000

		abbrv = profession[:3]
		profession = "{{" + profession + "}}"
		row = f"|{group} |<span data-tooltip='{account}'> {name} </span>| {profession} {abbrv} | {time_secs:,.1f}|"
		for skill in sorted_res_skills:
			if skill in combat_resurrect['players'][player]:
				total = f"{combat_resurrect['players'][player][skill].get('total', 0):,.0f}"
				hits = f"{combat_resurrect['players'][player][skill].get('hits', 0):,.0f}"
				if skill == 's10244':
					row += f' <span data-tooltip="{hits} Casts"> {total} </span>|'
				elif skill == 'kb_rally':
					row += f' <span data-tooltip="{total} Rallies"> {total} </span>|'
				else:
					row += f' <span data-tooltip="{hits} Total hits"> {total} </span>|'
			else:
				row += f' |'

		rows.append(row)
	rows.append(f"| {caption} |c")
	rows.append('\n\n</div>\n\n')
	combat_resurrect_text = "\n".join(rows)
	append_tid_for_output(
		create_new_tid_from_template(combat_resurrect_title, combat_resurrect_caption, combat_resurrect_text, combat_resurrect_tags),
		tid_list
	)

def build_main_tid(datetime, tag_list, guild_name, description_append):
	tag_str = ""
	for tag in tag_list:
		if tag == "":
			continue
		if tag == tag_list[-1] and len(tag_list) > 1:
			tag_str += f"and {tag}"
		if tag != tag_list[-1] and len(tag_list) > 1:
			tag_str += f"{tag}, "
		if len(tag_list) == 1:
			tag_str += f"{tag} "
		
	if tag_str == "": 
		tag_str = " - No Tags"
	else:
		tag_str = f"with {tag_str}"

	main_created = f"{datetime}"
	main_modified = f"{datetime}"
	main_tags = f'{datetime[0:4]} {datetime[0:7]} Logs'
	main_title = f"{datetime}-Log-Summary"
	
	if description_append:
		main_caption = f"{datetime} - {guild_name} - Log Summary {tag_str} - {description_append}"
	else:
		main_caption = f"{datetime} - {guild_name} - Log Summary {tag_str}"
	main_creator = f"Drevarr@github.com"

	main_text = "{{"+datetime+"-Tag_Stats}}\n\n{{"+datetime+"-Menu}}"

	append_tid_for_output(
		create_new_tid_from_template(main_title, main_caption, main_text, main_tags, main_modified, main_created, main_creator),
		tid_list
	)

def build_menu_tid(datetime: str, db_update: bool) -> None:
	"""
	Build a TID for the main menu.

	Args:
		datetime (str): The datetime string of the log.

	Returns:
		None
	"""
	tags = f"{datetime}"
	title = f"{datetime}-Menu"
	caption = "Menu"
	if db_update:
		text = (
		f'<<tabs "[[{datetime}-Overview]] [[{datetime}-General-Stats]] [[{datetime}-Buffs]] '
		f'[[{datetime}-Damage-Modifiers]] [[{datetime}-Mechanics]] [[{datetime}-Skill-Usage]] '
		f'[[{datetime}-Minions]] [[{datetime}-High-Scores]] [[{datetime}-Top-Damage-By-Skill]] '
		f'[[{datetime}-Player-Damage-By-Skill]] [[{datetime}-Squad-Composition]] [[{datetime}-On-Tag-Review]] '
		f'[[{datetime}-DPS-Stats]] [[{datetime}-Defense-Damage-Mitigation]] [[{datetime}-Attendance]] '
		f'[[{datetime}-commander-summary-menu]] [[{datetime}-Dashboard]] [[{datetime}-Leaderboard]] [[{datetime}-high_scores_Leaderboard]]" '
		f'"{datetime}-Overview" "$:/temp/menutab1">>'			
		)
	else:
		text = (
			f'<<tabs "[[{datetime}-Overview]] [[{datetime}-General-Stats]] [[{datetime}-Buffs]] '
			f'[[{datetime}-Damage-Modifiers]] [[{datetime}-Mechanics]] [[{datetime}-Skill-Usage]] '
			f'[[{datetime}-Minions]] [[{datetime}-High-Scores]] [[{datetime}-Top-Damage-By-Skill]] '
			f'[[{datetime}-Player-Damage-By-Skill]] [[{datetime}-Squad-Composition]] [[{datetime}-On-Tag-Review]] '
			f'[[{datetime}-DPS-Stats]] [[{datetime}-Defense-Damage-Mitigation]] [[{datetime}-Attendance]] '
			f'[[{datetime}-commander-summary-menu]] [[{datetime}-Dashboard]]" '
			f'"{datetime}-Overview" "$:/temp/menutab1">>'
		)

	append_tid_for_output(
		create_new_tid_from_template(title, caption, text, tags, 
							   fields={
									'radio': 'Total',
									'boon_radio': 'Total',
									'boon_selected': 'Might', 'Defenses_selected': 'damageTaken',
									'Offensive_selected': 'downContribution', 'Support_selected': 'condiCleanse',
									"category_radio": "Total", "category_heal": "Squad", "stacking_item": "might",
									'damage_with_buff': 'might', 'mitigation': 'Player'}),
		tid_list
	)

def build_general_stats_tid(datetime, offensive_detailed, defenses_detailed, support_detailed):
	"""
	Build a TID for general stats menu.
	"""
	tags = f"{datetime}"
	title = f"{datetime}-General-Stats"
	caption = "General Stats"
	creator = "Drevarr@github.com"

	text_parts = []
	text_parts .append(f"<<tabs '[[{datetime}-Damage]] [[{datetime}-Damage-With-Buffs]]")
	if offensive_detailed:
		text_parts.append(f"[[{datetime}-Offensive-Summary]] [[{datetime}-Offensive-Detailed]]")
	else:
		text_parts.append(f"[[{datetime}-Offensive-Summary]]")

	if defenses_detailed:
		text_parts.append(f"[[{datetime}-Defenses-Summary]] [[{datetime}-Defenses-Detailed]]")
	else:
		text_parts.append(f"[[{datetime}-Defenses-Summary]]")

	if support_detailed:
		text_parts.append(f"[[{datetime}-Support-Summary]] [[{datetime}-Support-Detailed]]")
	else:
		text_parts.append(f"[[{datetime}-Support-Summary]]")

	text = " ".join(text_parts)
	text += f"[[{datetime}-Heal-Stats]] [[{datetime}-Healers]] [[{datetime}-Combat-Resurrect]] [[{datetime}-FB-Pages]] [[{datetime}-Mesmer-Clone-Usage]]"
	text += f"[[{datetime}-Pull-Skills]] [[{datetime}-Squad-Health-Pct]]' '{datetime}-Offensive-Summary' '$:/temp/tab1'>>"

	append_tid_for_output(
		create_new_tid_from_template(title, caption, text, tags, creator=creator, fields={'radio': 'Total', 'damage_with_buff': 'might', 'boon_selected':'Might', 'Support_selected': 'condiCleanse', 'Offensive_selected': 'downContribution', 'Defenses_selected': 'damageTaken'}),
		tid_list
	)

def build_dashboard_menu_tid(datetime: str) -> None:
	"""
	Build a TID for the dashboard menu.
	"""

	tags = f"{datetime}"
	title = f"{datetime}-Dashboard"
	caption = "Dashboard"
	creator = "Drevarr@github.com"

	text = (f"<<tabs '[[{datetime}-Support-Bubble-Chart]] [[{datetime}-DPS-Bubble-Chart]] [[{datetime}-Utility-Bubble-Chart]] [[{datetime}-Total-Squad-Boon-Generation]] [[{datetime}-Total-Condition-Output-Generation]]' "
			f"'{datetime}-Support-Bubble-Chart' '$:/temp/tab1'>>")

	append_tid_for_output(
		create_new_tid_from_template(title, caption, text, tags, creator=creator),
		tid_list
	)

def build_damage_modifiers_menu_tid(datetime: str) -> None:
	"""
	Build a TID for the damage modifiers menu.
	"""

	tags = f"{datetime}"
	title = f"{datetime}-Damage-Modifiers"
	caption = "Damage Modifiers"
	creator = "Drevarr@github.com"

	text = (f"<<tabs '[[{datetime}-Shared-Damage-Mods]] [[{datetime}-Profession_Damage_Mods]]' "
			f"'{datetime}-Shared-Damage-Mods' '$:/temp/tab1'>>")

	append_tid_for_output(
		create_new_tid_from_template(title, caption, text, tags, creator=creator),
		tid_list
	)

def build_buffs_stats_tid(datetime, boons_detailed):
	"""
	Build a TID for buffs menu.
	"""
	tags = f"{datetime}"
	title = f"{datetime}-Buffs"
	caption = "Buffs"
	creator = "Drevarr@github.com"
	if boons_detailed:
		text = (f"<<tabs '[[{datetime}-Boons]] [[{datetime}-Boon-Generation-Detailed]] [[{datetime}-Stacking-Buffs]] [[{datetime}-Personal-Buffs]] [[{datetime}-Offensive-Buffs]] [[{datetime}-Support-Buffs]] [[{datetime}-Defensive-Buffs]]"
				f" [[{datetime}-Gear-Buff-Uptimes]] [[{datetime}-Gear-Skill-Damage]]"
				f"[[{datetime}-Conditions-In]] [[{datetime}-Debuffs-In]] [[{datetime}-Conditions-Out]] [[{datetime}-Debuffs-Out]]' "
				f"'{datetime}-Boons' '$:/temp/tab1'>>")
	else:
		text = (f"<<tabs '[[{datetime}-Boons]] [[{datetime}-Stacking-Buffs]] [[{datetime}-Personal-Buffs]] [[{datetime}-Offensive-Buffs]] [[{datetime}-Support-Buffs]] [[{datetime}-Defensive-Buffs]]"
				f" [[{datetime}-Gear-Buff-Uptimes]] [[{datetime}-Gear-Skill-Damage]]"
				f"[[{datetime}-Conditions-In]] [[{datetime}-Debuffs-In]] [[{datetime}-Conditions-Out]] [[{datetime}-Debuffs-Out]]' "
				f"'{datetime}-Boons' '$:/temp/tab1'>>")

	append_tid_for_output(
		create_new_tid_from_template(title, caption, text, tags, creator=creator),
		tid_list
	)

def build_dps_stats_menu(datetime):
	buff_stats_tags = f"{datetime}"
	buff_stats_title = f"{datetime}-DPS-Stats"
	buff_stats_caption = f"DPS Stats"
	buff_stats_creator = f"Drevarr@github.com"
	buff_stats_text = "!!!`Experimental DPS stats `\n"
	buff_stats_text += "* `Ch (t)s` = Damage/second done `t` seconds before an enemy goes down \n"
	buff_stats_text += "* `Bur (t)s` = Maximum damage/second done over any `t` second interval \n"
	buff_stats_text += "* `Ch5Ca (t)s` = Maximum Chunk(5) + Carrion damage/second done over any `t` second interval \n\n"

	buff_stats_text += f"<<tabs '[[{datetime}-DPS-Stats-Ch-Total]] [[{datetime}-DPS-Stats-Ch-DPS]] [[{datetime}-DPS-Stats-Bur-Total]] [[{datetime}-DPS-Stats-Bur-DPS]] [[{datetime}-DPS-Stats-Ch5Ca-Total]] [[{datetime}-DPS-Stats-Ch5Ca-DPS]]' '{datetime}-DPS-Stats-Ch-DPS' '$:/temp/tab1'>>"
	#tabs = {"Ch Total": "chunkDamage","Ch DPS": "chunkDamage", "Bur Total": "burstDamage",  "Bur DPS": "burstDamage", "Ch5Ca Total": "ch5CaBurstDamage", "Ch5Ca DPS": "ch5CaBurstDamage"}
	append_tid_for_output(
		create_new_tid_from_template(buff_stats_title, buff_stats_caption, buff_stats_text, buff_stats_tags, creator=buff_stats_creator),
		tid_list
	)

def build_boon_stats_tid(datetime):
	buff_stats_tags = f"{datetime}"
	buff_stats_title = f"{datetime}-Boons"
	buff_stats_caption = f"Boons"
	buff_stats_creator = f"Drevarr@github.com"

	buff_stats_text = f"<<tabs '[[{datetime}-Uptimes]] [[{datetime}-Self-Generation]] [[{datetime}-Group-Generation]] [[{datetime}-Squad-Generation]]' '{datetime}-Uptimes' '$:/temp/tab1'>>"

	append_tid_for_output(
		create_new_tid_from_template(buff_stats_title, buff_stats_caption, buff_stats_text, buff_stats_tags, creator=buff_stats_creator),
		tid_list
	)


def build_other_boon_stats_tid(datetime, boon_type=None):
	buff_stats_tags = f"{datetime}"
	buff_stats_title = f"{datetime}-{boon_type}-Buffs"
	buff_stats_caption = f"{boon_type} Buffs"
	buff_stats_creator = f"Drevarr@github.com"

	buff_stats_text = f"<<tabs '[[{datetime}-{boon_type}-Uptimes]] [[{datetime}-{boon_type}-Self-Generation]] [[{datetime}-{boon_type}-Group-Generation]] [[{datetime}-{boon_type}-Squad-Generation]]' '{datetime}-{boon_type}-Uptimes' '$:/temp/tab1'>>"

	append_tid_for_output(
		create_new_tid_from_template(buff_stats_title, buff_stats_caption, buff_stats_text, buff_stats_tags, creator=buff_stats_creator),
		tid_list
	)


def build_profession_damage_modifier_stats_tid(personal_damage_mod_data: dict, caption: str, tid_date_time: str):

	prof_mod_stats_tags = f"{tid_date_time}"
	prof_mod_stats_title = f"{tid_date_time}-Profession_Damage_Mods"
	prof_mod_stats_caption = f"Profession Damage Modifiers"
	prof_mod_stats_creator = f"Drevarr@github.com"
	prof_mod_stats_text = f'<$macrocall $name="tabs" tabsList="[prefix[{tid_date_time}-Damage-Modifiers-]]" '+'default={{{'+f'[prefix[{tid_date_time}-Damage-Modifiers-]first[]]'+'}}} state="$:/temp/sel_dmgMod"/>'

	append_tid_for_output(
		create_new_tid_from_template(prof_mod_stats_title, prof_mod_stats_caption, prof_mod_stats_text, prof_mod_stats_tags, creator=prof_mod_stats_creator),
		tid_list
	)   

def build_skill_usage_stats_tid(skill_casts_by_role: dict, caption: str, tid_date_time: str):
	skill_stats_tags = f"{tid_date_time}"
	skill_stats_title = f"{tid_date_time}-Skill-Usage"
	skill_stats_caption = f"{caption}"
	skill_stats_creator = f"Drevarr@github.com"
	skill_stats_text = f'<$macrocall $name="tabs" tabsList="[prefix[{tid_date_time}-Skill-Usage-]]" '+'default={{{'+f'[prefix[{tid_date_time}-Skill-Usage-]first[]]'+'}}} state="$:/temp/sel_skillUsage"/>'

	append_tid_for_output(
		create_new_tid_from_template(skill_stats_title, skill_stats_caption, skill_stats_text, skill_stats_tags, creator=skill_stats_creator),
		tid_list
	)

def fmt_firebrand_page_total(page_casts: int, page_cost: float, fight_time: float, page_total: int) -> str:
	"""
	Format the total page casts and cost for a firebrand player.

	Args:
		page_casts (int): Number of times the page was cast.
		page_cost (float): Cost of the page in terms of pages.
		fight_time (float): Duration of the fight in seconds.
		page_total (int): Total number of pages available.

	Returns:
		str: Formatted string of the total page casts and cost.
	"""
	output_string = ' <span data-tooltip="'

	if page_cost:
		output_string += "{:.2f}".format(round(100 * page_casts * page_cost / page_total, 4))
		output_string += '% of total pages '
		output_string += "{:.2f}".format(round(60 * page_casts / fight_time, 4))
		output_string += ' casts / minute">'
	else:
		output_string += "{:.2f}".format(round(100 * page_casts / page_total, 4))
		output_string += '% of total pages">'

	if page_cost:
		output_string += "{:.2f}".format(round(60 * page_casts * page_cost / fight_time, 4))
	else:
		output_string += "{:.2f}".format(round(60 * page_casts / fight_time, 4))

	output_string += '</span>|'

	return output_string

def build_fb_pages_tid(fb_pages: dict, caption: str, tid_date_time: str):
	"""
	Build a table of high score statistics for each category.

	Args:
		fb_pages (dict): Dictionary containing firebrand page usage data for each player.
		caption (str): The caption for the table.
		tid_date_time (str): The timestamp for the table id.
	"""
	# Firebrand pages
	tome1_skill_ids = ["41258", "40635", "42449", "40015", "42898"]
	tome2_skill_ids = ["45022", "40679", "45128", "42008", "42925"]
	tome3_skill_ids = ["42986", "41968", "41836", "40988", "44455"]

	tome_skill_ids = [
		*tome1_skill_ids,
		*tome2_skill_ids,
		*tome3_skill_ids,
	]

	tome_skill_page_cost = {
		"41258": 1, "40635": 1, "42449": 1, "40015": 1, "42898": 1,
		"45022": 1, "40679": 1, "45128": 1, "42008": 2, "42925": 2,
		"42986": 1, "41968": 1, "41836": 2, "40988": 2, "44455": 2,
	}
	rows = []	
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	header = "|table-caption-top|k\n"
	header += "|Firebrand page utilization, pages/minute|c\n"
	header += "|thead-dark table-hover sortable|k"
	rows.append(header)

	output_header =  '|!Name '
	output_header += ' | ! <span data-tooltip="Number of seconds player was in squad logs">Seconds</span>'
	output_header += '| !Pages/min| | !T1 {{Tome_of_Justice}}| !C1 {{Chapter_1_Searing_Spell}}| !C2 {{Chapter_2_Igniting_Burst}}| !C3 {{Chapter_3_Heated_Rebuke}}| !C4 {{Chapter_4_Scorched_Aftermath}}| !Epi {{Epilogue_Ashes_of_the_Just}}| | !T2 {{Tome_of_Resolve}} | !C1 {{Chapter_1_Desert_Bloom}}| !C2 {{Chapter_2_Radiant_Recovery}}| !C3 {{Chapter_3_Azure_Sun}}| !C4 {{Chapter_4_Shining_River}}| !Epi {{Epilogue_Eternal_Oasis}}|  | !T3 {{Tome_of_Courage}}| !C1 {{Chapter_1_Unflinching_Charge}}| !C2 {{Chapter_2_Daring_Challenge}}| !C3 {{Chapter_3_Valiant_Bulwark}}| !C4 {{Chapter_4_Stalwart_Stand}}| !Epi {{Epilogue_Unbroken_Lines}}'
	output_header += '|h'
	rows.append(output_header)

	pages_sorted_stacking_uptime_Table = []
	for player_name, player_data in fb_pages.items():

		fight_time = player_data["fightTime"]/1000 or 1

		firebrand_pages = player_data['firebrand_pages']
		all_tomes_total = 0

		for skill_id in tome_skill_ids:
			all_tomes_total += firebrand_pages.get(skill_id, 0) * tome_skill_page_cost[skill_id]

		pages_sorted_stacking_uptime_Table.append([player_name, all_tomes_total / fight_time])
	pages_sorted_stacking_uptime_Table = sorted(pages_sorted_stacking_uptime_Table, key=lambda x: x[1], reverse=True)
	pages_sorted_stacking_uptime_Table = list(map(lambda x: x[0], pages_sorted_stacking_uptime_Table))

	for player_name in pages_sorted_stacking_uptime_Table:
		name = fb_pages[player_name]['name']
		fight_time = fb_pages[player_name]["fightTime"]/1000 or 1
		firebrand_pages = fb_pages[player_name]['firebrand_pages']

		tome1_total = 0
		for skill_id in tome1_skill_ids:
			tome1_total += firebrand_pages.get(skill_id, 0) * tome_skill_page_cost[skill_id]

		tome2_total = 0
		for skill_id in tome2_skill_ids:
			tome2_total += firebrand_pages.get(skill_id, 0) * tome_skill_page_cost[skill_id]
	
		tome3_total = 0
		for skill_id in tome3_skill_ids:
			tome3_total += firebrand_pages.get(skill_id, 0) * tome_skill_page_cost[skill_id]
	
		all_tomes_total = tome1_total + tome2_total + tome3_total

		if all_tomes_total == 0:
			continue

		row = f"|{name}"
		row += f" | {fight_time:.2f} | "
		row += f"{round(60 * all_tomes_total / fight_time, 4):.2f} | |"

		row += fmt_firebrand_page_total(tome1_total, 0, fight_time, all_tomes_total)
		for skill_id in tome1_skill_ids:
			page_total = firebrand_pages.get(skill_id, 0)
			page_cost = tome_skill_page_cost[skill_id]
			row += fmt_firebrand_page_total(page_total, page_cost, fight_time, all_tomes_total)
		row += " |"

		row += fmt_firebrand_page_total(tome2_total, 0, fight_time, all_tomes_total)
		for skill_id in tome2_skill_ids:
			page_total = firebrand_pages.get(skill_id, 0)
			page_cost = tome_skill_page_cost[skill_id]
			row += fmt_firebrand_page_total(page_total, page_cost, fight_time, all_tomes_total)
		row += " |"

		row += fmt_firebrand_page_total(tome3_total, 0, fight_time, all_tomes_total)
		for skill_id in tome3_skill_ids:
			page_total = firebrand_pages.get(skill_id, 0)
			page_cost = tome_skill_page_cost[skill_id]
			row += fmt_firebrand_page_total(page_total, page_cost, fight_time, all_tomes_total)

		rows.append(row)
	rows.append("| Firebrand Pages |c")
	rows.append("\n\n</div>")
	firebrand_pages_tags = f"{tid_date_time}"
	firebrand_pages_title = f"{tid_date_time}-FB-Pages"
	firebrand_pages_caption = f"{caption}"
	firebrand_pages_text = "\n".join(rows)
	append_tid_for_output(
		create_new_tid_from_template(firebrand_pages_title, firebrand_pages_caption, firebrand_pages_text, firebrand_pages_tags),
		tid_list
	)

def build_high_scores_tid(high_scores: dict, skill_data: dict, buff_data: dict, caption: str, tid_date_time: str) -> None:
	"""
	Build a table of high score statistics for each category.

	Args:
		high_scores (dict): Dictionary containing high scores for each category.
		skill_data (dict): Dictionary containing skill data including name and icon.
		buff_data (dict): Dictionary containing buff data including name and icon.
		caption (str): The caption for the table.
		tid_date_time (str): A string to use as the date and time for the table id.
	"""
	# Define mapping for categories to their titles
	caption_dict = {
		"burst_damage1S": "Highest 1s Burst Damage",
		"statTarget_max": "Highest Outgoing Skill Damage", 
		"totalDamageTaken_max": "Highest Incoming Skill Damage",
		"fight_dps": "Damage per Second", 
		"statTarget_killed": "Kills per Second", 
		"statTarget_downed": "Downs per Second", 
		"statTarget_downContribution": "Down Contrib per Second",
		"defenses_blockedCount": "Blocks per Second", 
		"defenses_evadedCount": "Evades per Second", 
		"defenses_dodgeCount": "Dodges per Second", 
		"defenses_invulnedCount": "Invulned per Second",
		"support_condiCleanse": "Cleanses per Second", 
		"support_boonStrips": "Strips per Second", 
		"extHealingStats_Healing": "Healing per Second", 
		"extBarrierStats_Barrier": "Barrier per Second",
		"statTarget_appliedCrowdControl": "Crowd Control-Out per Second", 
		"defenses_receivedCrowdControl": "Crowd Control-In per Second",
	}

	# Initialize the HTML components
	high_scores_tags = f"{tid_date_time}"
	high_scores_title = f"{tid_date_time}-High-Scores"
	high_scores_caption = f"{caption}"
	rows = []
	rows.append('<div style="overflow-x:auto;">\n\n')
	rows.append('<div class="flex-row">\n\n')

	# Iterate over each category to build the table
	for category, table_title in caption_dict.items():
		if category not in high_scores:
			continue
		header = '    <div class="flex-col">\n\n'
		header += "|thead-dark table-caption-top table-hover|k\n"
		
		# Determine the header based on category
		if category in ["statTarget_max", "totalDamageTaken_max"]:
			header += "|@@display:block;width:200px;Player-Fight@@  |@@display:block;width:250px;Skill@@ | @@display:block;width:100px;Score@@|h"
		else:
			header += "|@@display:block;width:200px;Player-Fight@@ | @@display:block;width:100px;Score@@|h"
		
		rows.append(header)

		# Sort high scores for the current category
		sorted_high_scores = sorted(high_scores[category].items(), key=lambda x: x[1], reverse=True)
		
		# Build rows for each player
		for player in sorted_high_scores:
			player, score = player
			player_string = player.split("-")
			prof_name = player_string[0]
			acct = player_string[1]
			fight = player_string[2]
			fight = fight.split("|")[0]


			
			if category in ["statTarget_max", "totalDamageTaken_max"]:
				skill_id = player.split("| ")[1]
				if "s" + str(skill_id) in skill_data:
					skill_name = skill_data["s" + str(skill_id)]['name']
					skill_icon = skill_data["s" + str(skill_id)]['icon']
				elif "b" + str(skill_id) in buff_data:
					skill_name = buff_data["b" + str(skill_id)]['name']
					skill_icon = buff_data["b" + str(skill_id)]['icon']
				else:
					skill_name = skill_id
					skill_icon = "unknown.png"
				
				detailEntry = f'[img width=24 [{skill_name}|{skill_icon}]]-{skill_name}'
				row = f"|<span class='tooltip tooltip-right' data-tooltip='{acct}'> {prof_name} </span>-{fight}|{detailEntry} | {score:03,.2f}|"
			else:
				row = f"|<span class='tooltip tooltip-right' data-tooltip='{acct}'> {prof_name} </span>-{fight}| {score:03,.2f}|"
			rows.append(row)

		# Add table title and close the div
		rows.append(f"| ''{table_title}'' |c")
		rows.append("\n\n    </div>\n\n")
		
		# Add a new row for the next category if applicable
		if category == "totalDamageTaken_max":
			rows.append('\n<div class="flex-row">\n\n')

	# Close all divs and join rows
	rows.append("</div>\n\n")
	rows.append("</div>\n\n")
	high_scores_text = "\n".join(rows)

	# Append the high scores table to the output list
	append_tid_for_output(
		create_new_tid_from_template(high_scores_title, high_scores_caption, high_scores_text, high_scores_tags),
		tid_list
	)

def build_mechanics_tid(mechanics: dict, players: dict, caption: str, tid_date_time: str) -> None:
	"""
	Build a table of fight mechanics for all players in the log running the extension.
	Args:
		mechanics (dict): A dictionary of fight mechanics with player lists and mechanic data.
		players (dict): A dictionary of player data.
		caption (str): A string to use as the caption for the table.
		tid_date_time (str): A string to use as the date and time for the table id.
	"""
	rows = []
	for fight in mechanics:
		player_list = mechanics[fight]['player_list']
		mechanics_list = []
		for mechanic in mechanics[fight]:
			if mechanic in ['player_list', 'enemy_list']:
				continue
			else:
				mechanics_list.append(mechanic)

		
		rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
		header = "|thead-dark table-caption-top-left table-hover sortable|k\n"
		header += "|!Player |"
		for mechanic in mechanics_list:
			tooltip = f"{mechanics[fight][mechanic]['tip']}"
			detailed_entry = f"<span class='tooltip' data-tooltip='{tooltip}'> {mechanic} </span>"
			header += f" !{detailed_entry} |"

		header += "h"
		rows.append(header)

		for player in player_list:
			prof, name, account = player.split("|")
			if prof == name:
				prof_name = "{{"+prof+"}} "+account
			else:
				prof_name = "{{"+prof+"}} "+name
			row = f"|<span class='tooltip tooltip-right' data-tooltip='{account}'> {prof_name} </span>|"
			for mechanic in mechanics_list:
				if player in mechanics[fight][mechanic]['data']:
					row += f" {mechanics[fight][mechanic]['data'][player]} |"
				else:
					row += " - |"
			rows.append(row)
		if fight == "WVW":
			rows.append(f"|''Fight-WVW-Mechanics'' |c")
		else:
			rows.append(f"|''Fight-{fight:02d}-Mechanics'' |c")
		rows.append("\n\n</div>\n\n")
	text = "\n".join(rows)
	mechanics_title = f"{tid_date_time}-Mechanics"
	append_tid_for_output(
		create_new_tid_from_template(f"{mechanics_title}", caption, text, tid_date_time),
		tid_list
	)

def build_personal_buff_summary(top_stats: dict, buff_data: dict, personal_buff_data: dict, caption: str, tid_date_time: str) -> None:
	"""Print a table of personal buff stats for all players in the log running the extension.

	Args:
		top_stats (dict): Dictionary containing top statistics for players.
		buff_data (dict): Dictionary containing buff stats for each player.
		caption (str): The caption for the table.
		tid_date_time (str): A string to use as the date and time for the table id.
	"""
	personal_buffs_tags = f"{tid_date_time}"
	personal_buff_title = f"{tid_date_time}-Personal-Buffs"
	personal_buff_caption = f"{caption}"
	personal_buff_creator = f"Drevarr@github.com"
	personal_buff_text ="<<tabs '"
	tab_name = ""
	for profession in personal_buff_data:
		if profession == 'total':
			continue
		tab_name = f"{tid_date_time}-{caption.replace(' ','-')}-{profession}"
		personal_buff_text += f'[[{tab_name}]]'
	personal_buff_text += f"' '{tab_name}' '$:/temp/tab1'>>"
	append_tid_for_output(
		create_new_tid_from_template(personal_buff_title, personal_buff_caption, personal_buff_text, personal_buffs_tags, creator=personal_buff_creator),
		tid_list
	)

	for profession in personal_buff_data:
		if profession == 'total':
			continue
		prof_buff_list = personal_buff_data[profession]

		rows = []
		
		rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
		# Build the table header
		header = "|thead-dark table-caption-top table-hover sortable|k\n"
		header += "|!Party |!Name | !Prof | !{{FightTime}} |"
		for buff_id in prof_buff_list:
			if buff_id not in buff_data:
				continue
			skillIcon = buff_data[buff_id]["icon"]
			header += f"! [img width=24 [{buff_data[buff_id]['name']}|{skillIcon}]] |"
		header += "h"
		rows.append(header)

		# Build the table body	
		for player, player_data in top_stats['player'].items():
			if player_data['active_time'] == 0:
				continue
			if player_data['profession'] == profession:
				account = player_data['account']
				name = player_data['name']
				tt_name = f'<span data-tooltip="{account}">{name}</span>'

				# Build the row
				row = f"| {player_data['last_party']} |{tt_name} | {{{{{player_data['profession']}}}}} | {player_data['active_time'] / 1000:,.1f}|"

				for buff_id in prof_buff_list:
					if buff_id in player_data['buffUptimes']:
						buff_id_uptime = round((player_data['buffUptimes'][buff_id]['uptime_ms'] / player_data['active_time']) * 100, 2)
						state_changes = player_data['buffUptimes'][buff_id]['state_changes']
						tooltip = f"{state_changes} state changes"
						detail_entry = f'<span data-tooltip="{tooltip}"> {buff_id_uptime:.2f}% </span>'

						row += f" {detail_entry} |"
					else:
						row += f" - |"
				rows.append(row)

		# Add caption row and finalize table
		rows.append(f"|{caption} Table|c")
		rows.append("\n\n</div>")

		# Convert rows to text and append to output list
		tid_text = "\n".join(rows)
		personal_buff_title = f"{tid_date_time}-{caption.replace(' ','-')}-{profession}"
		profession = "{{"+f"{profession}"+"}}"
		prof_caption = f"{profession}-Personal-Buffs"	
		append_tid_for_output(
			create_new_tid_from_template(f"{personal_buff_title}", prof_caption, tid_text),
			tid_list
		)

def build_minions_tid(minions: dict, players: dict, skill_data: dict, caption: str, tid_date_time: str) -> None:
	"""
	Build a table of minions for each player in the log.

	This function generates a table displaying the number of fights a player has
	participated in and the total fight time for each player. It also lists the
	number of times each minion was used by the player.

	Args:
		minions (dict): A dictionary with the minion stats for each player.
		players (dict): A dictionary with the player stats.
		caption (str): The caption for the table.
		tid_date_time (str): The date and time for the table.
	"""
	minion_stats_tags = f"{tid_date_time}"
	minion_stats_title = f"{tid_date_time}-Minions"
	minion_stats_caption = f"{caption}"
	minion_stats_creator = f"Drevarr@github.com"
	minion_stats_text ="<<tabs '"
	tab_name = ""
	for profession in minions:
		tab_name = f"{tid_date_time}-{caption.replace(' ','-')}-{profession}"
		minion_stats_text += f'[[{tab_name}]]'
	minion_stats_text += f"' '{tab_name}' '$:/temp/tab1'>>"
	append_tid_for_output(
		create_new_tid_from_template(minion_stats_title, minion_stats_caption, minion_stats_text, minion_stats_tags, creator=minion_stats_creator),
		tid_list
	)

	for profession in minions:
		rows = []
		
		rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
		toggle_options = ["Total", "Stat/1s", "Stat/60s"]

		for toggle in toggle_options:
			rows.append(f'<$reveal stateTitle=<<currentTiddler>> stateField="category_radio" type="match" text="{toggle}" animate="yes">\n')
			
			header = "|thead-dark table-caption-top-left table-hover sortable|k\n"
			header += "|,Player |, Num|, Active|"
			sub_header = "|, !Stats |, Fight|, !Time|"

			for minion in minions[profession]['pets_list']:
				header += f" {minion} |<|<|"
				sub_header += " !Count | !{{damageTaken}}| {{Healing}}|"
				
			header += " Total Minion Data |<|<|h"
			sub_header += " !Count | !{{damageTaken}}| {{Healing}}|h"

			rows.append(header)
			rows.append(sub_header)

			for player_key in minions[profession]['player']:
				total_count = 0
				total_damage_taken = 0
				total_healing = 0
				player_name, player_profession, player_account = player_key.split("|")
				fights = players[player_key]['num_fights']
				total_fight_time = players[player_key]['active_time'] / 1000
				fight_time_str = f"{total_fight_time:,.1f}"
				fight_minutes = total_fight_time / 60

				if player_name == player_profession:
					row = f'|<span class="tooltip tooltip-right" data-tooltip="{player_account}">{player_account}</span>| {fights}| {fight_time_str}|'
				else:
					row = f'|<span class="tooltip tooltip-right" data-tooltip="{player_account}">{player_name}</span>| {fights}| {fight_time_str}|'

				for minion in minions[profession]['pets_list']:
					minion_count = 0
					minion_damage_taken = 0
					minion_healing = 0

					if minion in minions[profession]['player'][player_key]:
						minion_count = minions[profession]['player'][player_key][minion]
						minion_damage_taken = minions[profession]['player'][player_key][minion + 'DamageTaken'] / 1000
						minion_healing = minions[profession]['player'][player_key][minion + 'IncomingHealing'] / 1000

						total_count += minion_count
						total_damage_taken += minion_damage_taken
						total_healing += minion_healing

					if toggle == "Stat/1s":
						row += f" {minion_count / total_fight_time:,.3f} | {minion_damage_taken / total_fight_time:,.2f}K| {minion_healing / total_fight_time:,.2f}K|"
					elif toggle == "Stat/60s":
						row += f" {minion_count / fight_minutes:,.3f} | {minion_damage_taken / fight_minutes:,.2f}K| {minion_healing / fight_minutes:,.2f}K|"
					elif toggle == "Total":
						row += f" {minion_count:,.2f} | {minion_damage_taken:,.2f}K| {minion_healing:,.2f}K|"

				if toggle == "Total":
					row += f" {total_count:,.1f} | {total_damage_taken:,.2f}K| {total_healing:,.2f}K|"
				elif toggle == "Stat/1s":
					row += f" {total_count / total_fight_time:,.2f} | {total_damage_taken / total_fight_time:,.2f}K| {total_healing / total_fight_time:,.2f}K|"
				elif toggle == "Stat/60s":
					row += f" {total_count / fight_minutes:,.2f} | {total_damage_taken / fight_minutes:,.2f}K| {total_healing / fight_minutes:,.2f}K|"

				rows.append(row)

			radio_buttons = ' - '.join([f'<$radio field="category_radio" value="{option}"> {option} </$radio>' for option in toggle_options])
			rows.append(f'| {radio_buttons} - Minion Table |c')
			rows.append("\n</$reveal>")
		
		rows.append("\n\n")
		rows.append("---")
		rows.append("\n\n")

		header3 = "|thead-dark table-caption-top-left table-hover sortable|k\n"
		header3 += "| Skill Casts / Minute |c\n"
		header3 += "|!Player | !Fights| !Fight Time|!Minion |"
		for pet_skill in minions[profession]['pet_skills_list']:
			pet_skill_icon = skill_data[f"s{pet_skill}"]['icon']
			pet_skill_name = skill_data[f"s{pet_skill}"]['name']
			skill_entry = f"![img width=24 [{pet_skill_name}|{pet_skill_icon}]]"
			header3 += f" {skill_entry} |"
		header3 += "h"
		rows.append(header3)

		for player in minions[profession]['player']:
			total_count = 0
			total_damage_taken = 0
			total_healing = 0
			name, profession, account = player.split("|")
			fights = players[player]['num_fights']
			fight_time = f"{players[player]['active_time']/1000:,.1f}"
			fight_minutes = (players[player]['active_time']/1000)/60

			for minion in minions[profession]['pets_list']:
				if minion in minions[profession]['player'][player]:
					if name == profession:
						row = f'|<span class="tooltip tooltip-right" data-tooltip="{account}">{account}</span>| {fights}| {fight_time}|{minion} |'
					else:
						row = f'|<span class="tooltip tooltip-right" data-tooltip="{account}">{name}</span>| {fights}| {fight_time}|{minion} |'
					for pet_skill in minions[profession]['pet_skills_list']:
						if pet_skill in minions[profession]['player'][player][f"{minion}Skills"]:
							skill_count = minions[profession]['player'][player][f"{minion}Skills"][pet_skill]
							skill_minute = f"{skill_count/fight_minutes:,.2f}"
							row += f" {skill_minute} |"
						else:
							row += " - |"
					rows.append(row)



		#rows.append(f"| {profession}_{caption} |c")
		rows.append("\n\n</div>\n\n")
		text = "\n".join(rows)
		minion_stats_title = f"{tid_date_time}-{caption.replace(' ','-')}-{profession}"
		profession = "{{"+f"{profession}"+"}}"
		prof_caption = f"{profession}-Minions"

		append_tid_for_output(
			create_new_tid_from_template(minion_stats_title, prof_caption, text, tid_date_time),
			tid_list
		)

def build_top_damage_by_skill(total_damage_taken: dict, target_damage_dist: dict, skill_data: dict, buff_data: dict, caption: str, tid_date_time: str) -> None:
	"""
	Builds a table of top damage by skill.

	This function generates a table displaying the top 25 skills by damage output and damage taken.
	It sorts the skills based on their total damage and formats them into a presentable HTML table.

	Args:
		total_damage_taken (dict): A dictionary with skill IDs as keys and their damage taken stats as values.
		target_damage_dist (dict): A dictionary with skill IDs as keys and their damage output stats as values.
		skill_data (dict): A dictionary containing skill metadata, such as name and icon.
		buff_data (dict): A dictionary containing buff metadata, such as name and icon.
		caption (str): A string caption for the table.
		tid_date_time (str): A string representing the timestamp or unique identifier for the TID.
	"""
	# Sort skills by total damage in descending order
	sorted_total_damage_taken = dict(sorted(total_damage_taken.items(), key=lambda item: item[1]["totalDamage"], reverse=True))
	sorted_target_damage_dist = dict(sorted(target_damage_dist.items(), key=lambda item: item[1]["totalDamage"], reverse=True))

	# Calculate total damage values for percentage calculations
	total_damage_taken_value = sum(skill["totalDamage"] for skill in sorted_total_damage_taken.values())
	total_damage_distributed_value = sum(skill["totalDamage"] for skill in sorted_target_damage_dist.values())

	# Prepare HTML rows for the table
	rows = []
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	rows.append("|thead-dark table-borderless w-75 table-center|k")
	rows.append("|!Top 25 Skills by Damage Output|")
	rows.append("\n\n")
	rows.append('\n<div class="flex-row">\n\n    <div class="flex-col">\n\n')

	# Header for damage output table
	header = "|thead-dark table-caption-top-left table-hover table-center sortable|k\n"
	header += "|!Skill Name | !Damage | !Down Contrib | !% of Total|h"
	rows.append(header)
	
	# Populate the table with top 25 skills by damage output
	for i, (skill_id, skill) in enumerate(sorted_target_damage_dist.items()):
		if i < 25:
			skill_name = skill_data.get(f"s{skill_id}", {}).get("name", buff_data.get(f"b{skill_id}", {}).get("name", ""))
			skill_icon = skill_data.get(f"s{skill_id}", {}).get("icon", buff_data.get(f"b{skill_id}", {}).get("icon", ""))
			entry = f"[img width=24 [{skill_name}|{skill_icon}]]-{skill_name}"
			down_contrib = skill.get("downContribution", 0)
			row = f"|{entry} | {skill['totalDamage']:,.0f} | {down_contrib:,.0f} | {skill['totalDamage']/total_damage_distributed_value*100:,.1f}% |"
			rows.append(row)

	rows.append(f"| Squad Damage Output |c")
	rows.append('\n\n</div>\n\n    <div class="flex-col">\n\n')

	# Header for damage taken table
	header = "|thead-dark table-caption-top-left table-hover table-center sortable|k\n"
	header += "|!Skill Name | !Damage | !% of Total|h"
	rows.append(header)

	# Populate the table with top 25 skills by damage taken
	for i, (skill_id, skill) in enumerate(sorted_total_damage_taken.items()):
		if i < 25:
			skill_name = skill_data.get(f"s{skill_id}", {}).get("name", buff_data.get(f"b{skill_id}", {}).get("name", ""))
			skill_icon = skill_data.get(f"s{skill_id}", {}).get("icon", buff_data.get(f"b{skill_id}", {}).get("icon", ""))
			entry = f"[img width=24 [{skill_name}|{skill_icon}]]-{skill_name}"
			row = f"|{entry} | {skill['totalDamage']:,.0f} | {skill['totalDamage']/total_damage_taken_value*100:,.1f}% |"
			rows.append(row)

	rows.append(f"| Enemy Damage Output |c")
	rows.append("\n\n</div>\n\n</div>")

	rows.append("\n\n</div>\n\n")
	text = "\n".join(rows)

	# Define the title for the TID
	top_skills_title = f"{tid_date_time}-{caption.replace(' ', '-')}"

	# Append the TID for output
	append_tid_for_output(
		create_new_tid_from_template(top_skills_title, caption, text, tid_date_time),
		tid_list
	)

def build_healer_menu_tabs(top_stats: dict, caption: str, tid_date_time: str) -> None:
	"""Builds a menu tab macro for healers."""

	# Build the menu tab macro
	menu_tags = f"{tid_date_time}"
	menu_title = f"{tid_date_time}-Healers"
	menu_caption = f"Healer - Outgoing"
	menu_creator = f"Drevarr@github.com"
	menu_text = f'<$macrocall $name="tabs" tabsList="[prefix[{tid_date_time}-Healers-]]" '+'default={{{'+f'[prefix[{tid_date_time}-Healers-]first[]]'+'}}} state="$:/temp/sel_healer"/>'

	# Push the menu tab to the output list
	append_tid_for_output(
		create_new_tid_from_template(menu_title, menu_caption, menu_text, menu_tags, creator=menu_creator),
		tid_list
	)

def build_healer_outgoing_tids(top_stats: dict, skill_data: dict, buff_data: dict, caption: str, tid_date_time: str) -> None:
	"""
	Builds tables of outgoing healing and barrier by player and skill.

	Iterates through each healer and builds a table of their outgoing healing and barrier by skill.
	It also builds a table of the total healing and barrier by target.
	"""

	# Iterate through each healer
	for healer in top_stats['players_running_healing_addon']:
		name, profession, account = healer.split('|')
		healer_name = name
		healer_profession = profession
		healer_tags = f"{tid_date_time}"
		healer_title = f"{tid_date_time}-{caption.replace(' ', '-')}-{healer_profession}-{healer_name}-{account}"
		healer_caption = "{{"+healer_profession+"}}"+f" - <span data-tooltip='{account}'>{healer_name}       </span>"
		#<span data-tooltip='{account}'>{healer_name}       </span>
		rows = []

		rows.append("---\n\n")
		
		rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
		rows.append("|thead-dark table-borderless w-75 table-center|k")
		rows.append("|!Healer Outgoing Stats - excludes downed healing|")
		rows.append("\n\n")
		rows.append('\n<div class="flex-row">\n\n    <div class="flex-col">\n\n')

		header = "|thead-dark table-caption-top table-hover sortable|k\n"
		header += "|!Skill Name |!Hits | !Total| !Avg| !Max| !Pct|h"
		rows.append(header)

		outgoing_healing = top_stats['player'][healer]['extHealingStats'].get('outgoing_healing', 0)
		if outgoing_healing:
			for skill in top_stats['player'][healer]['extHealingStats']['skills']:
				skill_name = skill_data.get(skill, {}).get("name", buff_data.get(skill.replace("s", "b"), {}).get("name", ""))
				skill_icon = skill_data.get(skill, {}).get("icon", buff_data.get(skill.replace("s", "b"), {}).get("icon", ""))
				entry = f"[img width=24 [{skill_name}|{skill_icon}]]-{skill_name}"
				hits = top_stats['player'][healer]['extHealingStats']['skills'][skill]['hits']
				total_healing = top_stats['player'][healer]['extHealingStats']['skills'][skill]['healing']
				avg_healing = total_healing/hits if hits > 0 else 0
				max_heal = top_stats['player'][healer]['extHealingStats']['skills'][skill]['max'] if total_healing > 0 else 0

				row = f"|{entry} | {hits:,.0f} | {total_healing:,.0f}| {avg_healing:,.0f}| {max_heal:,.0f}| {total_healing/outgoing_healing*100:,.2f}%|"

				rows.append(row)

		rows.append(f"| Total Healing |c")

		rows.append("\n\n</div>")

		rows.append("\n\n")
		rows.append('\n<div class="flex-col">\n\n')

		header = "|thead-dark table-caption-top table-hover sortable|k\n"
		header += "| Total Barrier |c\n"
		header += "|!Skill Name |!Hits | !Total| !Avg| !Max| !Pct|h"
		rows.append(header)

		outgoing_barrier = top_stats['player'][healer]['extBarrierStats'].get('outgoing_barrier', 0)
		if outgoing_barrier:

			for skill in top_stats['player'][healer]['extBarrierStats']['skills']:
				skill_name = skill_data.get(skill, {}).get("name", buff_data.get(skill.replace("s", "b"), {}).get("name", ""))
				skill_icon = skill_data.get(skill, {}).get("icon", buff_data.get(skill.replace("s", "b"), {}).get("icon", ""))
				entry = f"[img width=24 [{skill_name}|{skill_icon}]]-{skill_name}"
				max_barrier = top_stats['player'][healer]['extBarrierStats']['skills'][skill]['max']
				hits = top_stats['player'][healer]['extBarrierStats']['skills'][skill]['hits']
				total_barrier = top_stats['player'][healer]['extBarrierStats']['skills'][skill]['totalBarrier']
				avg_barrier = total_barrier/hits if hits > 0 else 0

				row = f"|{entry} | {hits:,.0f} | {total_barrier:,.0f}| {avg_barrier:,.0f}| {max_barrier:,.0f}| {total_barrier/outgoing_barrier*100:,.2f}%|"

				rows.append(row)

		rows.append("\n\n</div>")

		rows.append("\n\n")
		rows.append('\n<div class="flex-col">\n\n')

		header = "|thead-dark table-caption-top table-hover sortable|k\n"
		header += "| Heal/Barrier by Target |c\n"
		header += "|!Player |!Healing | !Downed Healing| !Barrier|h"
		rows.append(header)

		targets_used = []
		if 'heal_targets' in top_stats['player'][healer]['extHealingStats']:
			for target in top_stats['player'][healer]['extHealingStats']['heal_targets']:
				target_barrier = 0
				targets_used.append(target)
				target_healing = top_stats['player'][healer]['extHealingStats']['heal_targets'][target]['outgoing_healing']
				target_downed = top_stats['player'][healer]['extHealingStats']['heal_targets'][target]['downed_healing']
				if 'barrier_targets' in top_stats['player'][healer]['extBarrierStats']:
					if target in top_stats['player'][healer]['extBarrierStats']['barrier_targets']:
						target_barrier = top_stats['player'][healer]['extBarrierStats']['barrier_targets'][target]['outgoing_barrier']

				row = f"|{target} | {target_healing:,.0f} | {target_downed:,.0f}| {target_barrier:,.0f}|"

				rows.append(row)

		if 'barrier_targets' in top_stats['player'][healer]['extBarrierStats']:
			for target in top_stats['player'][healer]['extBarrierStats']['barrier_targets']:
				if target not in targets_used:
					target_healing = 0
					target_downed = 0
					target_barrier = top_stats['player'][healer]['extBarrierStats']['barrier_targets'][target]['outgoing_barrier']

				row = f"|{target} | {target_healing:,.0f} | {target_downed:,.0f}| {target_barrier:,.0f}|"

				rows.append(row)

		rows.append("\n\n</div>\n\n</div>")

		rows.append("\n\n</div>")

		text = "\n".join(rows)

		append_tid_for_output(
			create_new_tid_from_template(healer_title, healer_caption, text, healer_tags),
			tid_list
		)

def build_damage_outgoing_by_skill_tid(tid_date_time: str, tid_list: list) -> None:
	"""
	Build a table of damage outgoing by player and skill.

	This function will build a table of damage outgoing by player and skill. It will
	also add the table to the tid_list for output.

	Args:
		tid_date_time (str): A string to use as the date and time for the table id.
		tid_list (list): A list of tiddlers to which the new tid will be added.
	"""
	rows = []
	# Set the title, caption and tags for the table
	tid_title = f"{tid_date_time}-Player-Damage-By-Skill"
	tid_caption = "Player Damage by Skill"
	tid_tags = tid_date_time

	# Add the select component to the table
	rows.append('\n!!!Select players(ctrl+click):')
	rows.append('<$let state=<<qualify $:/temp/selectedPlayer>>>')
	rows.append('<$select tiddler=<<state>> multiple>')
	rows.append(f'   <$list filter="[prefix[{tid_date_time}-Damage-By-Skill-]]">')
	rows.append('      <option value=<<currentTiddler>>>{{!!caption}}</option>')
	rows.append('   </$list>')
	rows.append('</$select>')

	# Add the table to the output
	rows.append('\n<<vspace height:"55px">>\n')
	rows.append('<div class="flex-row">')
	rows.append('   <$list filter="[<state>get[text]enlist-input[]]">')
	rows.append('    <div class="flex-col">')
	rows.append('      <$transclude mode="block"/>')
	rows.append('</div>')	
	rows.append('   </$list>')
	rows.append('\n\n</div>')

	# Create the new tid from the template and add it to the tid_list
	text = "\n".join(rows)

	append_tid_for_output(
		create_new_tid_from_template(tid_title, tid_caption, text, tid_tags),
		tid_list
	)
	
def build_damage_outgoing_by_player_skill_tids(top_stats: dict, skill_data: dict, buff_data: dict, tid_date_time: str, tid_list: list) -> None:
	"""
	Build a table of damage outgoing by player and skill.

	Args:
		top_stats (dict): A dictionary containing top stats for each player.
		skill_data (dict): A dictionary containing skill metadata, such as name and icon.
		buff_data (dict): A dictionary containing buff metadata, such as name and icon.
		tid_date_time (str): A string representing the timestamp or unique identifier for the TID.
		tid_list (list): A list of TIDs to which the generated TID should be appended.
	"""
	# Sort players by total damage output in descending order
	damage_totals = {
		player: data['dpsTargets']['damage']
		for player, data in top_stats['player'].items()
		if data['statsTargets']['critableDirectDamageCount'] > 0
		and (data['statsTargets']['criticalRate'] / data['statsTargets']['critableDirectDamageCount']) > 0.45
	}	

	sorted_damage_totals = sorted(damage_totals.items(), key=lambda x: x[1], reverse=True)

	# Iterate over each player and build a table of their damage output by skill
	for player, total_damage in sorted_damage_totals:
		player_damage = {
			skill_id: skill_data['totalDamage']
			for skill_id, skill_data in top_stats['player'][player]['targetDamageDist'].items()
		}
		sorted_player_damage = sorted(player_damage.items(), key=lambda x: x[1], reverse=True)

		# Initialize the HTML components
		rows = []
		name, profession, account = player.split("|")

		# Build the table header
		
		rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')		
		header = "|thead-dark table-caption-top table-hover sortable w-75 table-center|k\n"
		header += "|{{"+profession+"}}"+f" - {name} - {account}|c\n"
		header += "|!Skill Name | !Damage | !Down Contrib | !Hits | !Dmg/Hit | !% of Total|h"
		rows.append(header)

		# Populate the table with the player's damage output by skill
		for skill_id, damage in sorted_player_damage:
			skill_name = skill_data.get(f"s{skill_id}", {}).get("name", buff_data.get(f"b{skill_id}", {}).get("name", ""))
			skill_icon = skill_data.get(f"s{skill_id}", {}).get("icon", buff_data.get(f"b{skill_id}", {}).get("icon", ""))
			connect_hits = top_stats['player'][player]['targetDamageDist'][skill_id]['connectedHits']
			down_contrib = top_stats['player'][player]['targetDamageDist'][skill_id].get('downContribution', 0)
			if connect_hits == 0:
				connect_hits = 1
			entry = f"[img width=24 [{skill_name}|{skill_icon}]]-{skill_name[:30]}"
			row = f"|{entry} | {damage:,.0f} | {down_contrib:,.0f} | {connect_hits} | {damage / connect_hits:,.1f} | {damage / total_damage * 100:,.1f}%|"
			rows.append(row)
		rows.append("\n</div>\n")
		# Create the TID
		text = "\n".join(rows)
		player_title = f"{tid_date_time}-Damage-By-Skill-{profession}-{name}-{account}"
		if profession == name:
			player_caption = f"{{{profession}}} - {account}"
		else:
			player_caption = f"{{{profession}}} - {name}"

		append_tid_for_output(
			create_new_tid_from_template(player_title, player_caption, text, tid_date_time),
			tid_list
		)

def build_squad_composition(top_stats: dict, tid_date_time: str, tid_list: list) -> None:
	"""
	Build a table of the squad composition for each fight.

	This function will build a table of the squad composition for each fight. It
	will also add the table to the tid_list for output.

	Args:
		top_stats (dict): The top_stats dictionary containing the overall stats.
		tid_date_time (str): A string representing the timestamp or unique identifier
			for the TID.
		tid_list (list): A list of TIDs to which the generated TID should be appended.
	"""
	rows = []

	# Add the select component to the table
	rows.append('<div class="flex-row">')
	rows.append('<div class="flex-col">')
	rows.append("\n\n|thead-dark table-caption-top table-hover table-center|k")
	rows.append("| Squad Composition |h")
	rows.append('</div>')
	rows.append('<div class="flex-col">')
	rows.append("\n\n|thead-dark table-caption-top table-hover table-center|k")
	rows.append("| Enemy Composition |h")
	rows.append('</div>\n\n</div>\n')

	for fight in top_stats['parties_by_fight']:
		# Add the table header for the fight
		rows.append('<div class="flex-row">\n\n')
		rows.append('<div class="flex-col">\n\n')
		header = "\n\n|thead-dark table-caption-top table-hover sortable table-center|k\n"
		header += f"|Fight - {fight} |c"
		rows.append(header)			
		for group in top_stats['parties_by_fight'][fight]:
			# Add the table rows for the group
			row = f"|{group:02} |"
			for player in top_stats['parties_by_fight'][fight][group]:
				profession, name = player.split("|")
				profession = "{{"+profession+"}}"
				tooltip = f" {name} "
				detailEntry = f'<div class="xtooltip"> {profession} <span class="xtooltiptext" style="padding_left: 5px;">'+name+'</span></div>'
				row += f" {detailEntry} |"
			rows.append(row)			
		rows.append("</div>\n\n")

		rows.append('<div class="flex-col">\n\n')
		for team in top_stats["enemies_by_fight"][fight]:
			#rows.append('<div class="flex-col">\n\n')
			header = "\n\n|thead-dark table-caption-top table-hover sortable table-center|k\n"
			header += f"|Fight - {fight} : {team} Composition |c"
			rows.append(header)
			sorted_profs = dict(sorted(top_stats['enemies_by_fight'][fight][team].items(), key=lambda x: x[1], reverse=True))
			#len_profs = len(top_stats['enemies_by_fight'][fight])
			#table_size = len(top_stats['parties_by_fight'][fight])
			row_length = 4

			count = 0
			row = ""

			#for key, value in top_stats['enemies_by_fight'][fight].items():
			for key, value in sorted_profs.items():
				row += "|{{"+key+"}} : "+str(value)
				count += 1
				if count % row_length == 0:
					row +="|\n"
				else:
					row += " |"
			row +="\n"
			rows.append(row)
		rows.append("</div>\n\n")

		rows.append("</div>\n\n\n")
		rows.append("---\n\n\n")
	text = "\n".join(rows)

	tid_title = f"{tid_date_time}-Squad-Composition"
	tid_caption = "Squad Composition"
	tid_tags = tid_date_time

	append_tid_for_output(
		create_new_tid_from_template(tid_title, tid_caption, text, tid_tags),
		tid_list
	)

def build_on_tag_review(death_on_tag, tid_date_time):
	"""
	Build a table of on tag review stats for all players in the log running the extension.

	This function iterates over the death_on_tag dictionary, which contains data about each player's deaths including distance to tag, and whether they died on, off, or after tag, and whether they were able to run back after dying off tag.

	The function builds a table with the following columns:
		- Player (player name)
		- Profession (profession icon and abbreviated name)
		- Avg Dist (average distance to tag for the player)
		- On-Tag (number of deaths on tag)
		- Off-Tag (number of deaths off tag)
		- After-Tag (number of deaths after tag)
		- Run-Back (number of times the player was able to run back after dying off tag)
		- Total (total number of deaths for the player)
		- OffTag Ranges (ranges of off tag distances)

	The function then pushes the table to the tid_list for output.
	"""
	rows = []
	# Set the title, caption and tags for the table
	tid_title = f"{tid_date_time}-On-Tag-Review"
	tid_caption = "Player On Tag Review"
	tid_tags = tid_date_time

	# Add the select component to the table
	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	rows.append("\n\n|thead-dark table-caption-top table-hover sortable|k")
	rows.append("| On Tag Review |c")
	header = "|!Player |!Profession | !Avg Dist| !On-Tag<br>{{deadCount}} | !Off-Tag<br>{{deadCount}} | !After-Tag<br>{{deadCount}} | !Run-Back<br>{{deadCount}} | !Total<br>{{deadCount}} |!OffTag Ranges|h"
	rows.append(header)
	for name_prof in death_on_tag:
		player = death_on_tag[name_prof]['name']
		profession = death_on_tag[name_prof]['profession']
		account = death_on_tag[name_prof]['account']
		if len(death_on_tag[name_prof]['distToTag']):
			avg_dist = round(sum(death_on_tag[name_prof]['distToTag']) / len(death_on_tag[name_prof]['distToTag']))
		else:
			avg_dist = "n/a"
		on_tag = death_on_tag[name_prof]['On_Tag']
		off_tag = death_on_tag[name_prof]['Off_Tag']
		after_tag = death_on_tag[name_prof]['After_Tag_Death']
		run_back = death_on_tag[name_prof]['Run_Back']
		total = death_on_tag[name_prof]['Total']
		off_tag_ranges = death_on_tag[name_prof]['Ranges']
		row = f"|<span class='tooltip tooltip-right' data-tooltip=' {account}'> {player} </span> | {{{{{profession}}}}} {profession[:3]} | {avg_dist} | {on_tag} | {off_tag} | {after_tag} | {run_back} | {total} |{off_tag_ranges} |"
		rows.append(row)

	rows.append("</div>\n\n\n")
	

	text = "\n".join(rows)

	append_tid_for_output(
		create_new_tid_from_template(tid_title, tid_caption, text, tid_tags),
		tid_list
	)

def build_dps_stats_tids(DPSStats: dict, tid_date_time: str, tid_list: list) -> None:
	"""
	Build a table of DPS stats for all players in the log running the extension.

	This function iterates over the DPSStats dictionary, which contains data about each player's damage output, including total damage, fight time, and several types of DPS stats.

	The function builds a table with the following columns:
		- Player (player name)
		- Profession (profession icon and abbreviated name)
		- Seconds (number of seconds player was in squad logs)
		- DPS (total damage divided by fight time)
		- Chunk DPS (total chunk damage divided by fight time)
		- Burst DPS (total burst damage divided by fight time)
		- Ch5Ca DPS (total chunk damage divided by fight time for 5 player chunks)

	The function then pushes the table to the tid_list for output.
	"""
	tabs = {"Ch-Total": "chunkDamage","Ch-DPS": "chunkDamage", "Bur-Total": "burstDamage",  "Bur-DPS": "burstDamage", "Ch5Ca-Total": "ch5CaBurstDamage", "Ch5Ca-DPS": "ch5CaBurstDamage"}
	sorted_DPSStats = []
	for player_prof in DPSStats:
		player = DPSStats[player_prof]['name']
		profession = DPSStats[player_prof]['profession']
		account = DPSStats[player_prof]['account']
		fightTime = DPSStats[player_prof]['duration']

		if DPSStats[player_prof]['damageTotal'] / fightTime < 500:
			continue
		sorted_DPSStats.append([player_prof, DPSStats[player_prof]['damageTotal'] / fightTime])
	sorted_DPSStats = sorted(sorted_DPSStats, key=lambda x: x[1], reverse=True)
	sorted_DPSStats = list(map(lambda x: x[0], sorted_DPSStats))

	for tab in tabs.keys():
		rows = []

		# Set the title, caption and tags for the table
		tid_title = f"{tid_date_time}-DPS-Stats-{tab}"
		tid_caption = tab
		tid_tags = tid_date_time

		# Add the select component to the table
		rows.append("\n\n|thead-dark table-caption-top table-hover sortable|k")
		rows.append(f"| DPS Stats - {tab} |c")
		header = "|!Player |!Profession | ! <span data-tooltip=`Number of seconds player was in squad logs`>Seconds</span>| !DPS| !Total|"
		for i in range(1, 11):
			header += f" !{tab} ({i})s|"
		header += "h"
		rows.append(header)
		for player_prof in sorted_DPSStats:
			player = DPSStats[player_prof]["name"]
			profession = DPSStats[player_prof]["profession"]
			account = DPSStats[player_prof]["account"]
			fightTime = DPSStats[player_prof]['duration']
			DPS = '<span data-tooltip="'+f"{DPSStats[player_prof]['damageTotal']:,.0f}"+' total damage">'+f"{round(DPSStats[player_prof]['damageTotal'] / fightTime):,.0f}</span>"
			TOTAL = '<span data-tooltip="'+f"{DPSStats[player_prof]['damageTotal']:,.0f}"+' total damage">'+f"{DPSStats[player_prof]['damageTotal']:,.0f}</span>"
			row = f"|<span data-tooltip='{account}'>{player}</span> | {{{{{profession}}}}} {profession[:3]}| {fightTime} | {DPS} | {TOTAL}|"
			for i in range(1, 11):
				if tab == "Ch-DPS":
					row += ' <span data-tooltip="'+f"{DPSStats[player_prof][tabs[tab]][i]:,.0f}"+f' chunk({i}) damage">'+f"{round(DPSStats[player_prof][tabs[tab]][i] / fightTime):,.0f}</span>|"
				elif tab == "Ch-Total":
					row += ' <span data-tooltip="'+f"{round(DPSStats[player_prof][tabs[tab]][i] / fightTime):,.0f}"+f' chunk({i}) damage">'+f"{DPSStats[player_prof][tabs[tab]][i]:,.0f}</span>|"
				elif tab in ["Bur-Total","Ch5Ca-Total"]:
					row += ' <span data-tooltip="'+f"{round(DPSStats[player_prof][tabs[tab]][i] / i):,.0f}"+f' chunk({i}) damage">'+f"{DPSStats[player_prof][tabs[tab]][i]:,.0f}</span>|"
				else:
					row += ' <span data-tooltip="'+f"{DPSStats[player_prof][tabs[tab]][i]:,.0f}"+f' chunk({i}) damage">'+f"{round(DPSStats[player_prof][tabs[tab]][i] / i):,.0f}</span>|"

			rows.append(row)	

		text = "\n".join(rows)

		append_tid_for_output(
			create_new_tid_from_template(tid_title, tid_caption, text, tid_tags),
			tid_list
		)

def build_utility_bubble_chart(top_stats: dict, boons: dict, weights: dict, tid_date_time: str, tid_list: list, profession_colors: dict) -> None:
	"""
	Build a bubble chart of utility stats for all players in the log running the extension.

	This function iterates over the top_stats dictionary, which contains data about each player's utility output, including total strips, uptime, and several types of utility stats.

	The function builds a table with the following columns:
		- Player (player name)
		- Profession (profession icon and abbreviated name)
		- Condition Score (sum of weighted uptime of all conditions)
		- Strips/Sec (total strips divided by fight time)
		- Boon Score (sum of weighted boon generation)

	The function then pushes the table to the tid_list for output.
	"""
	tid_title = f"{tid_date_time}-Utility-Bubble-Chart"
	tid_caption = "Utility Bubble Chart"
	tid_tags = tid_date_time

	chart_data = []
	chart_min = 100
	chart_max = 0
	chart_xAxis = "Strips/Sec"
	chart_yAxis = "Condition/Sec"
	chart_xData = "Strips/Sec"
	chart_yData = "Condition Score"

	data_header = ["Name", "Profession", "Strips/Sec", "Condition Score", "Boon Score", "color"]
	chart_data.append(data_header)

	for player, player_data in top_stats['player'].items():
		name = player_data["name"]
		profession = player_data["profession"]
		fight_time = round(player_data["active_time"]/1000)
		if fight_time == 0:
			continue
		xdata = round(player_data["support"].get("boonStrips", 0)/fight_time,2)

		cps=0
		for condition in boons:
			if condition in player_data["targetBuffs"] and player_data["targetBuffs"][condition]["uptime_ms"] > 0:
				condi_name = boons[condition]['name'].lower()
				condi_wt = float(weights["Condition_Weights"].get(condi_name, 0))				
				condi_generated = (player_data["targetBuffs"][condition]["uptime_ms"] / 1000) * condi_wt
				cps += round(condi_generated / fight_time, 2)

		cps = round(cps, 2)
		player_entry = [name, profession, xdata, cps]

		boon_ps = 0
		for boon in boons:
			if boon in player_data["squadBuffs"] and player_data["squadBuffs"][boon]["generation"] > 0:
				boon_name = boons[boon]['name'].lower()
				boon_wt = float(weights["Boon_Weights"].get(boon_name, 0))
				generated = (player_data["squadBuffs"][boon]["generation"] / 1000) * boon_wt
				boon_ps += round(generated / fight_time, 2)
		player_entry.append(round(boon_ps, 2))

		if boon_ps > chart_max:
			chart_max = boon_ps
		if boon_ps < chart_min:
			chart_min = boon_ps
		player_color = profession_colors[profession]
		player_entry.append(player_color)

		chart_data.append(player_entry)

	text = "__''Utility Bubble Chart''__\n"
	text += "\n,,Bubble size based on boon score,,\n\n"
	text += "{{"+f"{tid_date_time}-Utility-Bubble-Chart||BubbleChart_Template"+"}}"

	append_tid_for_output(
		create_new_tid_from_template(tid_title, tid_caption, text, tid_tags, fields={"data": str(chart_data)[1:-1], "max": str(chart_max), "min": str(chart_min), "xAxis": chart_xAxis, "yAxis": chart_yAxis, "xData": chart_xData, "yData": chart_yData}),
		tid_list
	)

def build_support_bubble_chart(top_stats: dict, boons: dict, weights: dict, tid_date_time: str, tid_list: list, profession_colors: dict) -> None:
	"""
	Build a bubble chart of support stats for all players in the log.

	This function generates a bubble chart based on support metrics for each player,
	including healing per second, barrier per second, and boon generation. The chart
	displays the following data columns:
		- Name: Player's name
		- Profession: Player's profession
		- Hps + Bps: Combined healing and barrier per second
		- Cleanse/Sec: Condition cleanses per second
		- Boon Score: Weighted boon generation score
		- Color: Color representing the player's profession

	Args:
		top_stats (dict): Dictionary containing statistics for each player.
		boons (dict): Dictionary containing boons and their names.
		weights (dict): Dictionary containing weights for conditions and boons.
		tid_date_time (str): String representing the date and time for the chart.
		tid_list (list): List to append the generated chart data.
		profession_colors (dict): Dictionary mapping professions to their respective colors.
	"""

	tid_title = f"{tid_date_time}-Support-Bubble-Chart"
	tid_caption = "Support Bubble Chart"
	tid_tags = tid_date_time

	chart_data = []
	chart_min = 100
	chart_max = 0
	chart_xAxis = "Cleanse/Sec"
	chart_yAxis = "Hps + Bps"
	chart_xData = "Cleanse/Sec"
	chart_yData = "Hps + Bps"

	data_header = ["Name", "Profession", "Hps + Bps", "Cleanse/Sec", "Boon Score", "color"]
	chart_data.append(data_header)

	for player, player_data in top_stats['player'].items():
		name = player_data["name"]
		profession = player_data["profession"]
		fight_time = round(player_data["active_time"]/1000)
		if fight_time == 0:
			continue
		hpt = player_data["extHealingStats"].get("outgoing_healing", 0)
		bpt = player_data["extBarrierStats"].get("outgoing_barrier", 0)
		hps_bps = round((hpt+bpt)/fight_time)
		cps = round(player_data["support"].get("condiCleanse", 0)/fight_time,2)
		player_entry = [name, profession, hps_bps, cps]
		boon_ps = 0
		for boon in boons:
			if boon in player_data["squadBuffs"] and player_data["squadBuffs"][boon]["generation"] > 0:
				boon_name = boons[boon]['name'].lower()
				boon_wt = float(weights["Boon_Weights"].get(boon_name, 0))
				generated = (player_data["squadBuffs"][boon]["generation"] / 1000) * boon_wt
				boon_ps += round(generated / fight_time, 2)
		player_entry.append(round(boon_ps, 2))
		if boon_ps > chart_max:
			chart_max = boon_ps
		if boon_ps < chart_min:
			chart_min = boon_ps
		player_color = profession_colors[profession]
		player_entry.append(player_color)

		chart_data.append(player_entry)

	text = "__''Support Bubble Chart''__\n"
	text += "\n,,Bubble size based on weighted boon generation,,\n\n"
	text += "{{"+f"{tid_date_time}-Support-Bubble-Chart||BubbleChart_Template"+"}}"

	append_tid_for_output(
		create_new_tid_from_template(tid_title, tid_caption, text, tid_tags, fields={"data": str(chart_data)[1:-1], "max": str(chart_max), "min": str(chart_min), "xAxis": chart_xAxis, "yAxis": chart_yAxis, "xData": chart_xData, "yData": chart_yData}),
		tid_list
	)
	
def build_DPS_bubble_chart(top_stats: dict, tid_date_time: str, tid_list: list, profession_colors: dict) -> None:
	"""
	Build a bubble chart of DPS stats for all players in the log running the extension.

	The bubble size is based on the percentage of damage that was against downed targets.
	The x-axis is the percentage of damage that was down contribution.
	The y-axis is the damage per second.

	The function builds a table with the following columns:
		- Player (player name)
		- Profession (profession icon and abbreviated name)
		- Damage/Sec (total damage divided by fight time)
		- Down Contr % (down contribution divided by damage per second)
		- Dmg to Down % (damage against downed targets divided by damage per second)

	The function then pushes the table to the tid_list for output.
	"""
	tid_title = f"{tid_date_time}-DPS-Bubble-Chart"
	tid_caption = "DPS Bubble Chart"
	tid_tags = tid_date_time

	chart_data = []
	chart_min = 1000
	chart_max = 0
	chart_yAxis = "Damage/Sec"
	chart_xAxis = "Down Contr %"
	chart_yData = "Damage/Sec"
	chart_xData = "Down Contr %"

	data_header = ["Name", "Profession", "Damage/Sec", "Down Contr %", "Dmg to Down %", "color"]
	chart_data.append(data_header)

	for player, player_data in top_stats['player'].items():
		name = player_data["name"]
		profession = player_data["profession"]
		fight_time = round(player_data["active_time"]/1000)
		if fight_time == 0:
			continue
		Dps = round(player_data["statsTargets"].get("totalDmg", 0)/fight_time)
		DCps = 0.00
		DDps = 0.00
		if Dps > 0:
			DCps = round((player_data["statsTargets"].get("downContribution", 0)/fight_time)/Dps,4)
			DCps = round(DCps*100,2)
			DDps = round((player_data["statsTargets"].get("againstDownedDamage", 0)/fight_time)/Dps,2)
			DDps = round(DDps*100,2)
		player_entry = [name, profession, Dps, DCps, DDps]
		if DDps > chart_max:
			chart_max = DDps
		if DDps < chart_min:
			chart_min = DDps
		player_color = profession_colors[profession]
		player_entry.append(player_color)

		chart_data.append(player_entry)

	text = "__''DPS Bubble Chart''__\n"
	text += "\n,,Bubble size based on against downed damage % of Damage"
	text += "{{"+f"{tid_date_time}-DPS-Bubble-Chart||BubbleChart_Template"+"}}"

	append_tid_for_output(
		create_new_tid_from_template(tid_title, tid_caption, text, tid_tags, fields={"data": str(chart_data)[1:-1], "max": str(chart_max), "min": str(chart_min), "xAxis": chart_xAxis, "yAxis": chart_yAxis, "xData": chart_xData, "yData": chart_yData}),
		tid_list
	)

def build_boon_generation_bar_chart(top_stats: dict, boons: dict, weights: dict, tid_date_time: str, tid_list: list) -> None:
	total_boon_generation = []
	playerCount = 0

	for player, player_data in top_stats['player'].items():
		player_active_time = int(player_data['active_time'])
		if player_active_time == 0:
			continue
		playerCount += 1
		player_boon_generation = []
		name = player_data['name']
		profession = player_data['profession']
		prof_name = "{{"+profession+"}} - "+name
		player_total = 0
		player_boon_generation.append(prof_name)
		
		for boon in boons:			
			if boon in ['b5974', 'b13017', 'b10269']:
				continue
			generation_ms = player_data['squadBuffs'].get(boon, {}).get('generation', 0)
			boon_weight = float(weights['Boon_Weights'].get(boons[boon].lower(), 0))
			#print(f"Boon Wt Type: {type(boon_weight)}")
			gen_per_sec = (generation_ms / player_active_time)
			wt_gen_per_sec = gen_per_sec * boon_weight
			#player_boon_generation.append(f"{wt_gen_per_sec:.3g}")
			player_boon_generation.append(round(wt_gen_per_sec,3))
			player_total += (wt_gen_per_sec)
		#player_boon_generation.append(f"{player_total:.3g}")
		player_boon_generation.append(round(player_total,3))
		player_boon_generation.append(profession)

		total_boon_generation.append(player_boon_generation)

	calcHeight = str(playerCount*25)
	sorted_total_boon_generation = sorted(total_boon_generation, key=lambda x: x[13])
	key_list = ['Player',"Might", "Fury", "Quickness", "Alacrity", "Protection", "Regeneration", "Vigor", "Aegis", "Stability", "Swiftness", "Resistance", "Resolution",'Total','Profession']
	chart_dataset = [key_list] + sorted_total_boon_generation

	chart_text = f"""
<$echarts $text=```
const boonColors = [
    '#e69f00',  // Orange
    '#56b4e9',  // Sky blue
    '#009e73',  // Bluish green
    '#f0e442',  // Yellow
    '#0072b2',  // Blue
    '#d55e00',  // Vermillion
    '#cc79a7',  // Reddish purple
    '#999999',  // Gray
    '#6a3d9a',  // Deep purple
    '#b15928',  // Brown
    '#17becf',  // Cyan
    '#bcbd22',  // Olive green
];

option = {{
  title:{{
    text: 'Weighted Total Squad Boon Generation',
    subtext: 'Generation per Second',
    top: 'top',
    right: 'center'
  }},  
  color: boonColors,
  legend: {{
    type: 'scroll',
    orient: 'vertical',
    left: 10,
    top: 20,
    bottom: 20,
    }},
  tooltip: {{trigger: 'axis'}},
  grid: {{left: '25%', top: '10%'}},
  dataset: [
    {{
      source: {chart_dataset}
    }},
  ],
  yAxis: {{
    type: 'category',
  }},
  xAxis: {{}},
  dataZoom: [
    {{
      type: 'slider',
      yAxisIndex: 0,
      filterMode: 'none'
    }},
    {{
      type: 'inside',
      yAxisIndex: 0,
      filterMode: 'none'
    }}
  ],    
  series: [
    {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}},
    {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}},
    {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}},
    {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}}
    ]
}};
```$height="{calcHeight}px" $width="100%" $theme="dark"/>
"""
	tid_title = f"{tid_date_time}-Total-Squad-Boon-Generation"
	tid_caption = "Total Squad Boon Generation"
	tid_tags = tid_date_time
	append_tid_for_output(
		create_new_tid_from_template(tid_title, tid_caption, chart_text, tid_tags),
		tid_list
	)

def build_condition_generation_bar_chart(top_stats: dict, conditions: dict, weights: dict, tid_date_time: str, tid_list: list) -> None:
	total_condition_generation = []
	playerCount = 0

	for player, player_data in top_stats['player'].items():
		player_active_time = int(player_data['active_time'])
		if player_active_time == 0:
			continue
		playerCount += 1
		player_condition_generation = []
		name = player_data['name']
		profession = player_data['profession']
		prof_name = "{{"+profession+"}} - "+name
		player_total = 0
		player_condition_generation.append(prof_name)
		
		for boon in conditions:			
			if boon in ['b5974', 'b13017', 'b10269']:
				continue
			generation_ms = player_data['targetBuffs'].get(boon, {}).get('uptime_ms', 0)
			boon_weight = float(weights['Condition_Weights'].get(conditions[boon].lower(), 0))
			gen_per_sec = (generation_ms / player_active_time)
			wt_gen_per_sec = gen_per_sec * boon_weight
			#player_condition_generation.append(f"{wt_gen_per_sec:.3g}")
			player_condition_generation.append(round(wt_gen_per_sec,3))
			player_total += (wt_gen_per_sec)
		#player_condition_generation.append(f"{player_total:.3g}")
		player_condition_generation.append(round(player_total,3))
		player_condition_generation.append(profession)

		total_condition_generation.append(player_condition_generation)

	calcHeight = str(playerCount*25)
	sorted_total_condition_generation = sorted(total_condition_generation, key=lambda x: x[15])		
	key_list = ['Player',"Bleeding", "Burning", "Confusion", "Poison", "Torment", "Blind", "Chilled", "Crippled", "Fear", "Immobile", "Slow", "Weakness", "Taunt",  "Vulnerability",'Total','Profession']
	chart_dataset = [key_list] + sorted_total_condition_generation	
	chart_text = f"""
<$echarts $text=```
const boonColors = [
	'#b22222',  // red
	'#FD6124',  // orange-red
	'#800000',  // maroon
	'#710193',  // purple
	'#848482',  // gray
	'#228B22',  // forest green
	'#00008B',  // dark blue
	'#0095B6',  // teal blue
	'#494F55',  // dark gray
	'#F1C40F',  // yellow
	'#d3d3d3',  // light gray
	'#D891EF',  // lavender
	'#FF7F50',  // coral
	'#00CED1',  // dark turquoise
];

option = {{
  title:{{
    text: 'Weighted Total Condition Output Generation',
    subtext: 'Generation per Second',
    top: 'top',
    right: 'center'
  }},  
  color: boonColors,
  legend: {{
    type: 'scroll',
    orient: 'vertical',
    left: 10,
    top: 20,
    bottom: 20,
    }},
  tooltip: {{trigger: 'axis'}},
  grid: {{left: '25%', top: '10%'}},
  dataset: [
    {{
		source: {chart_dataset}
    }},
  ],
  yAxis: {{
    type: 'category',
    axisLabel: {{ interval: 0, rotate: 0 }}
  }},
  xAxis: {{}},
  dataZoom: [
    {{
      type: 'slider',
      yAxisIndex: 0,
      filterMode: 'none'
    }},
    {{
      type: 'inside',
      yAxisIndex: 0,
      filterMode: 'none'
    }}
  ],    
  series: [
    {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}},
    {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}},
    {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}},
    {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}},
	{{ type: 'bar', stack:'Total'}}, {{ type: 'bar', stack:'Total'}}
    ]
}};
```$height="{calcHeight}px" $width="100%" $theme="dark"/>
"""
	tid_title = f"{tid_date_time}-Total-Condition-Output-Generation"
	tid_caption = "Total Condition Output Generation"
	tid_tags = tid_date_time
	append_tid_for_output(
		create_new_tid_from_template(tid_title, tid_caption, chart_text, tid_tags),
		tid_list
	)

def build_and_sort_stat(stat_dict, sort_key="avgStat", reverse=False):
    built = {
        name: {
            "numFights": len(data),
            "totalStat": sum(data),
			"avgStat": sum(data) / len(data),
            "fightData": data,
        }
        for name, data in stat_dict.items()
		if sum(data) > 0
    }

    return dict(
        sorted(built.items(), key=lambda i: i[1][sort_key], reverse=reverse)
    )
    

def build_boxplot_echart(
    stat,
    stat_name,
    stat_boxplot_data,
    stat_boxplot_names,
    stat_boxplot_profs,
    profession_color,
):
    """
    Returns a string containing the ECharts boxplot option JS.
    """

    #if stat in chart_per_second:
    #    title_text = f"{stat_name} per Second for all Fights Present"
    #else:

    title_text = f"{stat_name.upper()} per Second for all Fights Present"

    short_prof = {
        "Guardian": "Gdn", "Dragonhunter": "Dgh", "Firebrand": "Fbd", "Willbender": "Wbd",
        "Luminary": "Lum", "Warrior": "War", "Berserker": "Brs", "Spellbreaker": "Spb",
        "Bladesworn": "Bds", "Paragon": "Par", "Engineer": "Eng", "Scrapper": "Scr",
        "Holosmith": "Hls", "Mechanist": "Mec", "Amalgam": "Aml", "Ranger": "Rgr",
        "Druid": "Dru", "Soulbeast": "Slb", "Untamed": "Unt", "Galeshot": "Gsh",
        "Thief": "Thf", "Daredevil": "Dar", "Deadeye": "Ded", "Specter": "Spe",
        "Antiquary": "Ant", "Elementalist": "Ele", "Tempest": "Tmp", "Weaver": "Wea",
        "Catalyst": "Cat", "Evoker": "Evo", "Mesmer": "Mes", "Chronomancer": "Chr",
        "Mirage": "Mir", "Virtuoso": "Vir", "Troubadour": "Tbd", "Necromancer": "Nec",
        "Reaper": "Rea", "Scourge": "Scg", "Harbinger": "Har", "Ritualist": "Rit",
        "Revenant": "Rev", "Herald": "Her", "Renegade": "Ren", "Vindicator": "Vin",
        "Conduit": "Con", "Unknown": "Ukn",
    }

    names_js = json.dumps(stat_boxplot_names)
    profs_js = json.dumps(stat_boxplot_profs)
    colors_js = json.dumps(profession_color)
    short_prof_js = json.dumps(short_prof)
    data_js = json.dumps(stat_boxplot_data)

    return f'''
<$echarts $text="""

const names = {names_js};
const professions = {profs_js};
const ProfessionColor = {colors_js};
const short_Prof = {short_prof_js};

option = {{
  title: [
    {{ text: '{title_text}', left: 'center' }},
    {{
      text: 'Output in seconds across all fights\\nupper: Q3 + 1.5 * IQR\\nlower: Q1 - 1.5 * IQR',
      borderColor: '#999',
      borderWidth: 1,
      textStyle: {{ fontSize: 10 }},
      left: '1%',
      top: '90%'
    }}
  ],

  dataset: [
    {{
      source: {data_js}
    }},
    {{
      transform: {{
        type: 'boxplot',
        config: {{
          itemNameFormatter: function (params) {{
            return names[params.value] + " (" + short_Prof[professions[params.value]] + ")";
          }}
        }}
      }}
    }},
    {{
      fromDatasetIndex: 1,
      fromTransformResult: 1
    }}
  ],

  dataZoom: [
    {{ type: 'slider', yAxisIndex: [0], start: 100, end: 50 }},
    {{ type: 'inside', yAxisIndex: [0], start: 100, end: 50 }}
  ],

  tooltip: {{ trigger: 'item' }},
  grid: {{ left: '25%', right: '10%', bottom: '15%' }},
  yAxis: {{
    type: 'category',
    boundaryGap: true,
    nameGap: 30,
    splitArea: {{ show: true }},
    splitLine: {{ show: true }}
  }},
  xAxis: {{
    type: 'value',
    name: 'Sec',
    splitArea: {{ show: true }}
  }},

  series: [
    {{
      name: 'boxplot',
      type: 'boxplot',
      datasetIndex: 1,
      encode: {{ tooltip: [1, 2, 3, 4, 5] }},
      tooltip: {{
        formatter: function (params) {{
          return `
<u><b>${{params.value[0]}}</b></u>
<table>
<tr><td>&#x2022;</td><td>Low :</td><td><b>${{params.value[1].toFixed(2)}}</b></td></tr>
<tr><td>&#x2022;</td><td>Q1 :</td><td><b>${{params.value[2].toFixed(2)}}</b></td></tr>
<tr><td>&#x2022;</td><td>Q2 :</td><td><b>${{params.value[3].toFixed(2)}}</b></td></tr>
<tr><td>&#x2022;</td><td>Q3 :</td><td><b>${{params.value[4].toFixed(2)}}</b></td></tr>
<tr><td>&#x2022;</td><td>High :</td><td><b>${{params.value[5].toFixed(2)}}</b></td></tr>
</table>`;
        }}
      }},
      itemStyle: {{
        borderColor: function (seriesIndex) {{
          let idx = names.indexOf(seriesIndex.name.split(" (")[0]);
          return ProfessionColor[professions[idx]];
        }},
        borderWidth: 2
      }}
    }},
    {{
      name: 'outlier',
      type: 'scatter',
      datasetIndex: 2,
      encode: {{ x: 1, y: 0 }}
    }}
  ]
}};"""$height="500px" $width="100%" $theme="dark"/>
'''

def build_bar_echart(sorted_chart, format_stat, caption):
    json_chart = json.dumps(sorted_chart)

    # Chart: 3 bars per player with legend toggle
    chart_block = f"""
<$echarts $text=```
option = {{
  title: {{ text: '{format_stat}', subtext: '{caption}' }},
  tooltip: {{ trigger: 'axis' }},
  legend: {{ selected: {{ "Stat/1s": false, "Total": true, "Stat/60s":false }}, top:'10%' }},
  dataset: {{
    dimensions: ["Party", "Name", "Profession", "Total", "Stat/1s", "Stat/60s"],
    source: {json_chart}
  }},
  xAxis: {{}},
  yAxis: {{ type: 'category', inverse: true }},
  grid: {{ top: '15%', containLabel: true }},
  series: [
    {{ type: 'bar', name: 'Total', encode: {{ x: 'Total', y: 'Name' }} }},
    {{ type: 'bar', name: 'Stat/1s', encode: {{ x: 'Stat/1s', y: 'Name' }} }},
    {{ type: 'bar', name: 'Stat/60s', encode: {{ x: 'Stat/60s', y: 'Name' }} }}
  ],
  dataZoom: [
    {{ type: 'slider', yAxisIndex: 0, start: 0, end: 50 }},
    {{ type: 'inside', yAxisIndex: 0 }}
  ]
}};
```$height="900px" $theme="dark"/>
"""

    return chart_block

def render_boxplot_echart(StatsPerFight, stat_category, stat_name, profession_color, tid_date_time: str, tid_list: list):
  sorted_stats = build_and_sort_stat(StatsPerFight[stat_category][stat_name], sort_key="totalStat", reverse=False)
  stat_boxplot_data = list([]) 
  stat_boxplot_names = list([]) 
  stat_boxplot_profs = list([])
  for name, data in sorted_stats.items():
      playerName, Profession, Account = name.split("|")
      stat_boxplot_names.append(playerName)
      stat_boxplot_profs.append(Profession)
      stat_boxplot_data.append(data['fightData'])
    
  echart_text = build_boxplot_echart(stat_category, stat_name, stat_boxplot_data, stat_boxplot_names, stat_boxplot_profs, profession_color)

  tid_title = f"{tid_date_time}-{stat_category}-{stat_name}-boxplot"
  tid_caption = f"{stat_category} {stat_name} Boxplot"
  tid_tags = tid_date_time
  append_tid_for_output(
    create_new_tid_from_template(tid_title, tid_caption, echart_text, tid_tags),
    tid_list
  )    

def build_squad_healthpct_table(health_data: dict, tid_date_time: str, tid_list: list) -> None:
	bucket_list = [
		"100-90",
		"90-80",
		"80-70",
		"70-60",
		"60-50",
		"50-40",
		"40-30",
		"30-20",
		"20-10",
		"10-0"
	]

	rows=[]

	tid_title = f"{tid_date_time}-Squad-Health-Pct"
	tid_caption = "Squad HP% Review"
	tid_tags = tid_date_time

	rows.append("|thead-dark table-caption-top sortable|k")
	rows.append("|Accumulated Time per 10% Health Bucket|c")
	header="|!Player | !Prof | !Group | !Fights |"

	for bucket in bucket_list:
		header += f" !{bucket}|"
	header += "h"
	rows.append(header)

	for player, pData in health_data.items():
		prof="{{"+pData['Profession']+"}}-"+pData['Profession'][:3]
		total_sum = sum(pData['Health_Buckets'].values())
		player_row = f"|{pData['Name']} | {prof} | {pData['Group']} | {pData['Fights']} |"
		for bucket in bucket_list:
			pct = pData['Health_Buckets'].get(bucket, 0)
			if total_sum:
				pct = pct/total_sum*100
			else:
				pct = 0
			pct = f"{pct:.2f}%" if pct else "-" 
			player_row += f" {pct}|"

		rows.append(player_row)

	chart_text = "\n".join(rows)
	append_tid_for_output(
		create_new_tid_from_template(tid_title, tid_caption, chart_text, tid_tags),
		tid_list
	)

def build_mesmer_clone_usage(mesmer_clone_usage: dict, tid_date_time: str, tid_list: list) -> None: 
	"""
	Build and append a table of Mesmer clone usage for all players in the log.

	This function iterates over the mesmer_clone_usage dictionary, which contains data about each player's clone usage.
	It generates an HTML table with the following columns for each player:
	- Profession and Name: Player's profession and name.
	- Clone States: Visual representation of clone states using dots.
	- Total: Total clone usage metrics for each state.

	The generated HTML is appended to the tid_list for output.

	Args:
		mesmer_clone_usage (dict): Dictionary containing clone usage data for each player.
		tid_date_time (str): String representing the date and time for the table.
		tid_list (list): List to append the generated table data.
	"""
	rows = []
	tid_title = f"{tid_date_time}-Mesmer-Clone-Usage"
	tid_caption = "Mesmer Clone Usage"
	tid_tags = tid_date_time

	rows.append("<style>.dot {height: 10px; width: 10px; background-color: magenta; border-radius: 50%; border: 1px solid darkmagenta; display: inline-block;}")
	rows.append(".cols_3 {column-count: 3;}")
	rows.append(".dot1 {height: 10px; width: 10px; background-color: white; border-radius: 50%; border: 1px solid darkmagenta; display: inline-block;} </style>")
	rows.append('<div class="flex-row">')
	for player, data in mesmer_clone_usage.items():
		name=player.split("_")[0]
		prof="{{"+player.split("_")[1]+"}}"
		rows.append('\n<div class="flex-col-1 py-3 px-5">\n')
		rows.append(f'\n|{prof} {name} | <span class="dot"></span><span class="dot"></span><span class="dot"></span> | <span class="dot1"></span><span class="dot"></span><span class="dot"></span> | <span class="dot1"></span><span class="dot1"></span><span class="dot"></span> | <span class="dot1"></span><span class="dot1"></span><span class="dot1"></span> | Total |h')

		for spell in data:
			rows.append(f"| {spell}| {data[spell].get(3,0)} | {data[spell].get(2,0)} | {data[spell].get(1,0)} | {data[spell].get(0,0)} | {sum(data[spell].values())} |")

		rows.append('\n\n</div>\n\n')

	rows.append("</div>")
	text = "\n".join(rows)

	append_tid_for_output(
		create_new_tid_from_template(tid_title, tid_caption, text, tid_tags),
		tid_list
	)

def build_attendance_table(top_stats: dict, tid_date_time: str, tid_list: list) -> None:
	"""Build an attendance table from top_stats data and append it to tid_list."""
	attendance_data = {}

	for player, data in top_stats["player"].items():
		account = data["account"]
		player_name = data["name"]
		guild_status = data["guild_status"]
		profession = f"{{{{ {data['profession']} }}}}"

		num_fights = data["num_fights"]
		active_time = round(data["active_time"] / 1000)

		if account not in attendance_data:
			attendance_data[account] = {}
		if player_name not in attendance_data[account]:
			attendance_data[account][player_name] = {}

		attendance_data[account][player_name][profession] = {
			"num_fights": num_fights,
			"active_time": active_time,
			"guild_status": guild_status
		}

	rows = []
	tid_title = f"{tid_date_time}-Attendance"
	tid_caption = "Attendance"
	tid_tags = tid_date_time

	
	rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
	rows.append("\n\n|thead-dark table-caption-top table-hover|k")
	rows.append("| Attendance Review |c")
	rows.append("|Account|Name|Profession| Num Fights| Active Time| Status |h")

	for account, players_data in attendance_data.items():
		total_active_time = 0
		total_num_fights = 0
		is_first_entry = True
		guild_status = ""


		for player_name, professions_data in players_data.items():
			for profession, stats in professions_data.items():
				guild_status = attendance_data[account][player_name][profession]["guild_status"]
				total_active_time += stats["active_time"]
				total_num_fights += stats["num_fights"]

				if is_first_entry:
					rows.append(
						f"|{account}|{player_name}|{profession}| {stats['num_fights']}| {stats['active_time']}| {guild_status} |"
					)
					is_first_entry = False
				else:
					rows.append(
						f"|~|{player_name}|{profession}| {stats['num_fights']}| {stats['active_time']}| {guild_status} |"
					)
		rows.append(
			f"| Totals for {account}:|<|<| {total_num_fights}| {total_active_time}| {guild_status} |h"
		)

	rows.append("\n</div>")
	text = "\n".join(rows)

	append_tid_for_output(
		create_new_tid_from_template(tid_title, tid_caption, text, tid_tags),
		tid_list
	)

def build_commander_summary_menu(commander_summary_data: dict, tid_date_time: str, tid_list: list) -> None:
	"""
	Builds the menu for the commander summary.

	Args:
		commander_summary_data (dict): A dictionary of commander summary data.
		tid_date_time (str): A string to use as the date and time for the table id.
		tid_list (list): The list of tables to append the new table to.
	"""
	tags = f"{tid_date_time}"
	title = f"{tid_date_time}-commander-summary-menu"
	caption = "Commander-Summary"
	text = '<<tabs "'
	tag_name = "None"
	tag_prof = "None"
	tag_acct = "None"
	for commander in commander_summary_data:
		tag_name, tag_prof, tag_acct = commander.split("|")

		text += f"[[{tid_date_time}-{tag_name}-{tag_prof}-{tag_acct}-Tag-Summary]] "

	text += f'" "{tid_date_time}-{tag_name}-{tag_prof}-{tag_acct}-Tag-Summary" "$:/temp/tagtab">>'

	append_tid_for_output(
		create_new_tid_from_template(title, caption, text, tags),
		tid_list
	)

def build_commander_summary(commander_summary_data: dict, skill_data: dict, buff_data: dict, tid_date_time: str, tid_list: list) -> None:
	"""
	Builds the commander summary tables.

	Args:
		commander_summary_data (dict): A dictionary of commander summary data.
		skill_data (dict): A dictionary of skill data.
		buff_data (dict): A dictionary of buff data.
		tid_date_time (str): A string to use as the date and time for the table id.
		tid_list (list): The list of tables to append the new table to.
	"""
	for commander, cmd_data in commander_summary_data.items():
		rows = []
		# Set the title, caption and tags for the table
		tag_name, tag_prof, tag_acct = commander.split("|")
		tid_title = f"{tid_date_time}-{tag_name}-{tag_prof}-{tag_acct}-Tag-Summary"
		if tag_prof == tag_name:
			tid_caption = "{{"+f"{tag_prof}"+"}}"+f"-{tag_acct}-Tag-Summary"
		else:
			tid_caption = "{{"+f"{tag_prof}"+"}}"+f"-{tag_name}-Tag-Summary"
		tid_tags = tid_date_time

		damage_by_skill={}
		for skill , damage_data in cmd_data["totalDamageTaken"].items():
			damage_by_skill[skill] = damage_data["totalDamage"]

		sorted_items = {k: v for k, v in sorted(damage_by_skill.items(), key=lambda item: item[1], reverse=True)}
		prot_data =cmd_data["prot_mods"] 
		def_data = cmd_data["defenses"]
		damageTaken = cmd_data["defenses"].get('damageTaken',0)
		damageBarrier = cmd_data["defenses"].get("damageBarrier",0)
		downCount = cmd_data["defenses"].get("downCount",0)
		deadCount = cmd_data["defenses"].get("deadCount",0)
		boonStrips = cmd_data["defenses"].get("boonStrips",0)
		conditionCleanses = cmd_data["defenses"].get("conditionCleanses",0)
		receivedCrowdControl = cmd_data["defenses"].get("receivedCrowdControl",0)
		damageGain = int(prot_data["damageGain"])
		
		rows.append('<div style="overflow-y: auto; width: 100%; overflow-x:auto;">\n\n')
		rows.append('<div class="flex-row">\n    <div class="flex-col">\n\n')
		rows.append("\n\n|thead-dark table-caption-top table-hover sortable|k")
		if tag_prof == tag_name:
			rows.append("|{{"+tag_prof+"}}"+f" {tag_acct} - Defense Stats Summary |c")
		else:
			rows.append("|{{"+tag_prof+"}}"+f" {tag_name} - Defense Stats Summary |c")
		rows.append("| !Damage | !Barrier | !Protection | !Downed | !Dead | !Stripped| !Cleansed| !Hard CC|h")
		rows.append(f"| {damageTaken:,} | {damageBarrier:,} | {damageGain:,} | {downCount} | {deadCount} | {boonStrips:,}| {conditionCleanses:,}| {receivedCrowdControl}|")
		rows.append("\n\n")
		rows.append('</div></div>\n<div class="flex-row">\n    <div class="flex-col">\n\n')
		rows.append("\n\n|thead-dark table-caption-top table-hover sortable|k")
		if tag_prof == tag_name:
			rows.append("|{{"+tag_prof+"}}"+f" {tag_acct} - Incoming Heal Stats Summary |c")
		else:
			rows.append("|{{"+tag_prof+"}}"+f" {tag_name} - Incoming Heal Stats Summary |c")		
		rows.append("|!Healer | !Healing | !Barrier | !Downed Healing |h")
		for healer, data in cmd_data["heal_stats"].items():
			healer_name, healer_profession, healer_account = healer.split("|")
			healer_profession = "{{"+healer_profession+"}}"
			healing = int(data["outgoing_healing"])
			barrier = int(data["outgoing_barrier"])
			downed = int(data["downed_healing"])
			rows.append(f"|{healer_profession} <span class='tooltip tooltip-right' data-tooltip='{healer_account}'> {healer_name} </span>| {healing:,}| {barrier:,}| {downed:,}|")
		rows.append("\n\n")
		rows.append('</div>\n    <div class="flex-col">\n\n')
		rows.append("\n\n|thead-dark table-caption-top table-hover sortable|k")
		if tag_prof == tag_name:
			rows.append("|{{"+tag_prof+"}}"+f" {tag_acct} - Incoming Damage Summary |c")
		else:
			rows.append("|{{"+tag_prof+"}}"+f" {tag_name} - Incoming Damage Summary |c")		
		rows.append("|!Skill | !Damage| !Hits| !Barrier Absorbed|h")
		for item in sorted_items:
			skill_id = "s"+str(item)
			if skill_id in skill_data:
				skill_name = skill_data[skill_id]["name"]
				skill_icon = skill_data[skill_id]["icon"]
			else:
				skill_id = "b"+str(item)
				skill_name = buff_data[skill_id]["name"]
				skill_icon = buff_data[skill_id]["icon"]

			damage = cmd_data["totalDamageTaken"][item]["totalDamage"]
			hits = cmd_data["totalDamageTaken"][item]["connectedHits"]
			barrier = cmd_data["totalDamageTaken"][item]["shieldDamage"]
			rows.append("|[img width=24 ["+f"{skill_icon}"+"]]"+f"{skill_name} | {int(damage):,}| {int(hits):,}| {int(barrier):,}|")
		rows.append("\n\n")
		rows.append('    </div>\n  </div>\n</div>')

		text = "\n".join(rows)

		append_tid_for_output(
			create_new_tid_from_template(tid_title, tid_caption, text, tid_tags),
			tid_list
		)

def build_damage_with_buffs(stacking_uptime_Table: dict, DPSStats: dict, top_stats: dict, tid_date_time: str, tid_list: list) -> None:
	"""
	Builds the Damage with Buffs tables.

	Args:
		stacking_uptime_Table (dict): A dictionary of stacking uptime data.
		DPSStats (dict): A dictionary of DPS data.
		top_stats (dict): A dictionary of top stats data.
		tid_date_time (str): A string to use as the date and time for the table id.
		tid_list (list): The list of tables to append the new table to.

	Returns:
		None
	"""
	rows = []

	#start Stacking Buff Uptime Table insert
	rows.append('\n<<alert dark "Damage with Buffs" width:60%>>\n\n')
	rows.append('\n---\n')
	rows.append('!!! `Damage with buff %` \n')
	rows.append('!!! Percentage of damage done with a buff, similar to uptime %, but based on damage dealt \n')
	rows.append('!!! `Damage % - Uptime %` \n')
	rows.append('!!! The difference in `damage with buff %` and `uptime %` \n')
	

	max_stacking_buff_fight_time = 0
	for uptime_prof_name in stacking_uptime_Table:
		max_stacking_buff_fight_time = max(stacking_uptime_Table[uptime_prof_name]['duration_Might'], max_stacking_buff_fight_time)

	dps_sorted_stacking_uptime_Table = []
	for uptime_prof_name in stacking_uptime_Table:
		dps_prof_name = f"{stacking_uptime_Table[uptime_prof_name]['profession']} {stacking_uptime_Table[uptime_prof_name]['name']} {stacking_uptime_Table[uptime_prof_name]['account']}"
		dps_sorted_stacking_uptime_Table.append([uptime_prof_name, DPSStats[dps_prof_name]['damageTotal'] / DPSStats[dps_prof_name]['duration']])
	dps_sorted_stacking_uptime_Table = sorted(dps_sorted_stacking_uptime_Table, key=lambda x: x[1], reverse=True)
	dps_sorted_stacking_uptime_Table = list(map(lambda x: x[0], dps_sorted_stacking_uptime_Table))

	# Might with damage table
	rows.append('<$reveal stateTitle=<<currentTiddler>> stateField="damage_with_buff" type="match" text="might" animate="yes">\n')
	rows.append('|<$radio field="damage_with_buff" value="might"> Might </$radio> - <$radio field="damage_with_buff" value="other"> Other Buffs  </$radio> - Sortable table|c')
	rows.append('|thead-dark table-hover table-caption-top sortable|k')
	output_header =  '|!Name | !Class | !DPS' 
	output_header += ' | ! <span data-tooltip="Number of seconds player was in squad logs">Seconds</span>'
	output_header += '| !Avg| !1+ %| !5+ %| !10+ %| !15+ %| !20+ %| !25 %'
	output_header += '|h'
	rows.append(output_header)
	
	for uptime_prof_name in dps_sorted_stacking_uptime_Table:
		name = stacking_uptime_Table[uptime_prof_name]['name']
		prof = stacking_uptime_Table[uptime_prof_name]['profession']
		account = stacking_uptime_Table[uptime_prof_name]['account']
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_Might'] / 1000) or 1
		damage_with_might = stacking_uptime_Table[uptime_prof_name]['damage_with_Might']
		might_stacks = stacking_uptime_Table[uptime_prof_name]['Might']

		if stacking_uptime_Table[uptime_prof_name]['duration_Might'] * 10 < max_stacking_buff_fight_time:
			continue
		dps_prof_name = f"{prof} {name} {account}"
		total_damage = DPSStats[dps_prof_name]["damageTotal"] or 1
		playerDPS = total_damage/DPSStats[dps_prof_name]['duration']

		damage_with_avg_might = sum(stack_num * damage_with_might[stack_num] for stack_num in range(1, 26)) / total_damage
		damage_with_might_uptime = 1.0 - (damage_with_might[0] / total_damage)
		damage_with_might_5_uptime = sum(damage_with_might[i] for i in range(5,26)) / total_damage
		damage_with_might_10_uptime = sum(damage_with_might[i] for i in range(10,26)) / total_damage
		damage_with_might_15_uptime = sum(damage_with_might[i] for i in range(15,26)) / total_damage
		damage_with_might_20_uptime = sum(damage_with_might[i] for i in range(20,26)) / total_damage
		damage_with_might_25_uptime = damage_with_might[25] / total_damage
		
		avg_might = sum(stack_num * might_stacks[stack_num] for stack_num in range(1, 26)) / (fight_time * 1000)
		might_uptime = 1.0 - (might_stacks[0] / (fight_time * 1000))
		might_5_uptime = sum(might_stacks[i] for i in range(5,26)) / (fight_time * 1000)
		might_10_uptime = sum(might_stacks[i] for i in range(10,26)) / (fight_time * 1000)
		might_15_uptime = sum(might_stacks[i] for i in range(15,26)) / (fight_time * 1000)
		might_20_uptime = sum(might_stacks[i] for i in range(20,26)) / (fight_time * 1000)
		might_25_uptime = might_stacks[25] / (fight_time * 1000)

		#"{:,}".format(round(fight_time))
		output_string = f'|<span data-tooltip="{account}"> {name} </span> |'+' {{'+prof+'}} | '+"{:,}".format(round(playerDPS))+'| '+"{:,}".format(round(fight_time))

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_avg_might, 4))+'% dmg - '+"{:.2f}".format(round(avg_might, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_avg_might), 4))+'</span>'

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_might_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(might_uptime * 100, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_might_uptime * 100), 4))+'</span>'

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_might_5_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(might_5_uptime * 100, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_might_5_uptime * 100), 4))+'</span>'

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_might_10_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(might_10_uptime * 100, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_might_10_uptime * 100), 4))+'</span>'

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_might_15_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(might_15_uptime * 100, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_might_15_uptime * 100), 4))+'</span>'

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_might_20_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(might_20_uptime * 100, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_might_20_uptime * 100), 4))+'</span>'

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_might_25_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(might_25_uptime * 100, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_might_25_uptime * 100), 4))+'</span>'
		
		output_string += '|'

		rows.append(output_string)

	rows.append("</$reveal>\n")

	# Other buffs with damage table
	other_buffs_with_damage = {
		'b740': "Might", 'b725': "Fury", 'b1187': "Quickness", 'b30328': "Alacrity", 'b717': "Protection",
		'b718': "Regeneration", 'b726': "Vigor", 'b743': "Aegis", 'b1122': "Stability",
		'b719': "Swiftness", 'b26980': "Resistance", 'b873': "Resolution"
	}
	rows.append('<$reveal stateTitle=<<currentTiddler>> stateField="damage_with_buff" type="match" text="other" animate="yes">\n')
	rows.append('|<$radio field="damage_with_buff" value="might"> Might </$radio> - <$radio field="damage_with_buff" value="other"> Other Buffs  </$radio> - Sortable table|c')
	rows.append('|thead-dark table-hover table-caption-top sortable|k')
	output_header =  '|!Name | !Class | !DPS '
	output_header += ' | ! <span data-tooltip="Number of seconds player was in squad logs">Seconds</span>'
	for damage_buffID in other_buffs_with_damage:
		damage_buff = other_buffs_with_damage[damage_buffID]
		output_header += '| !{{'+damage_buff.capitalize()+'}}'
	output_header += '|h'
	rows.append(output_header)
	
	for uptime_prof_name in dps_sorted_stacking_uptime_Table:
		name = stacking_uptime_Table[uptime_prof_name]['name']
		prof = stacking_uptime_Table[uptime_prof_name]['profession']
		account = stacking_uptime_Table[uptime_prof_name]['account']
		uptime_table_prof_name = name+"|"+prof+"|"+account
		dps_prof_name = f"{prof} {name} {account}"
		if uptime_table_prof_name in top_stats['player']:
			uptime_fight_time = top_stats['player'][uptime_table_prof_name]['active_time'] or 1
		else:
			uptime_fight_time = 1
		dps_fight_time = DPSStats[dps_prof_name]['duration'] or 1
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_Might'] / 1000) or 1

		if stacking_uptime_Table[uptime_prof_name]['duration_Might'] * 10 < max_stacking_buff_fight_time:
			continue

		total_damage = DPSStats[dps_prof_name]["damageTotal"] or 1
		playerDPS = total_damage/dps_fight_time
		output_string = f'|<span data-tooltip="{account}"> {name} </span> |'+' {{'+prof+'}} | '+"{:,}".format(round(playerDPS))+'| '+"{:,}".format(round(fight_time))+'|'

		for damage_buffID in other_buffs_with_damage:
			damage_buff = other_buffs_with_damage[damage_buffID]
			damage_with_buff = stacking_uptime_Table[uptime_prof_name]['damage_with_'+damage_buff]
			damage_with_buff_uptime = damage_with_buff[1] / total_damage			

			if damage_buffID in top_stats['player'][uptime_table_prof_name]['buffUptimesActive']:
				buff_uptime = top_stats['player'][uptime_table_prof_name]['buffUptimesActive'][damage_buffID]['uptime_ms'] / uptime_fight_time
			else:
				buff_uptime = 0

			output_string += ' <span data-tooltip="'+"{:.2f}".format(round(damage_with_buff_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(buff_uptime * 100, 4))+'% uptime">'
			output_string += "{:.2f}".format(round((damage_with_buff_uptime * 100), 4))+'</span>|'

		rows.append(output_string)

	rows.append("</$reveal>\n")

	#rows.append("</$reveal>\n")

	text = "\n".join(rows)
	tags = f"{tid_date_time}"
	title = f"{tid_date_time}-Damage-With-Buffs"
	caption = "Damage with Buffs"

	append_tid_for_output(
		create_new_tid_from_template(title, caption, text, tags, fields={"damage_with_buff": "might"}),
		tid_list	
	)

def build_stacking_buffs(stacking_uptime_Table: dict, top_stats: dict, tid_date_time: str, tid_list: list, blacklist: list) -> None:
	"""
	Builds tables displaying stacking buff uptimes for players.

	This function generates tables for stacking buffs, specifically "Might" and "Stability", 
	using the provided stacking uptime data and player statistics. It calculates and displays 
	various statistics like average stack uptime and percentage uptime for different stack thresholds.

	Args:
		stacking_uptime_Table (dict): A dictionary containing stacking uptime data for players.
		top_stats (dict): A dictionary of player statistics, including active time.
		tid_date_time (str): A string representing the date and time for table identification.
		tid_list (list): A list to append the generated tables for output.

	Returns:
		None
	"""

	rows = []
	max_fightTime = 0
	for squadDps_prof_name in stacking_uptime_Table:
		max_fightTime = max(top_stats['player'][squadDps_prof_name]['active_time'], max_fightTime)

	#start Stacking Buff Uptime Table insert
	stacking_buff_Order = ['might', 'stability']
	max_stacking_buff_fight_time = 0
	for uptime_prof_name in stacking_uptime_Table:
		max_stacking_buff_fight_time = max(stacking_uptime_Table[uptime_prof_name]['duration_Might'], max_stacking_buff_fight_time)

	rows.append('\n<<alert dark "Stacking Buffs" width:60%>>\n\n')
	squad_fight_time=0
	squad_stab_avg=0
	squad_stab_1=0
	squad_stab_2=0
	squad_stab_5=0
	squad_str_avg=0
	squad_str_1=0
	squad_str_5=0
	squad_str_10=0
	squad_str_15=0
	squad_str_20=0
	squad_str_25=0	
	# Might stack table
	rows.append('<$reveal stateTitle=<<currentTiddler>> stateField="stacking_item" type="match" text="might" animate="yes">\n')
	rows.append('|<$radio field="stacking_item" value="might"> Might </$radio> - <$radio field="stacking_item" value="stability"> Stability  </$radio> - {{Might}} uptime by stack|c')
	rows.append('|thead-dark table-hover table-caption-top sortable|k')
	output_header =  '|!Name | !Class'
	output_header += ' | ! <span data-tooltip="Number of seconds player was in squad logs">Seconds</span>'
	output_header += '| !Avg| !1+ %| !5+ %| !10+ %| !15+ %| !20+ %| !25 %'
	output_header += '|h'
	rows.append(output_header)
	
	might_sorted_stacking_uptime_Table = []
	for uptime_prof_name in stacking_uptime_Table:
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_Might'] / 1000) or 1
		squad_fight_time += fight_time
		might_stacks = stacking_uptime_Table[uptime_prof_name]['Might']

		if (top_stats['player'][uptime_prof_name]['active_time'] * 100) / max_fightTime < 1:
			continue

		avg_might = sum(stack_num * might_stacks[stack_num] for stack_num in range(1, 26)) / (fight_time * 1000)
		might_sorted_stacking_uptime_Table.append([uptime_prof_name, avg_might])
	might_sorted_stacking_uptime_Table = sorted(might_sorted_stacking_uptime_Table, key=lambda x: x[1], reverse=True)
	might_sorted_stacking_uptime_Table = list(map(lambda x: x[0], might_sorted_stacking_uptime_Table))
	
	for uptime_prof_name in might_sorted_stacking_uptime_Table:
		name = stacking_uptime_Table[uptime_prof_name]['name']
		prof = stacking_uptime_Table[uptime_prof_name]['profession']
		account = stacking_uptime_Table[uptime_prof_name]['account']
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_Might'] / 1000) or 1
		might_stacks = stacking_uptime_Table[uptime_prof_name]['Might']

		avg_might = sum(stack_num * might_stacks[stack_num] for stack_num in range(1, 26)) / (fight_time * 1000)
		squad_str_avg += avg_might*fight_time
		might_uptime = 1.0 - (might_stacks[0] / (fight_time * 1000))
		squad_str_1 += might_uptime*fight_time
		might_5_uptime = sum(might_stacks[i] for i in range(5,26)) / (fight_time * 1000)
		squad_str_5 += might_5_uptime*fight_time
		might_10_uptime = sum(might_stacks[i] for i in range(10,26)) / (fight_time * 1000)
		squad_str_10 += might_10_uptime*fight_time
		might_15_uptime = sum(might_stacks[i] for i in range(15,26)) / (fight_time * 1000)
		squad_str_15 += might_15_uptime*fight_time
		might_20_uptime = sum(might_stacks[i] for i in range(20,26)) / (fight_time * 1000)
		squad_str_20 += might_20_uptime*fight_time
		might_25_uptime = might_stacks[25] / (fight_time * 1000)
		squad_str_25 += might_25_uptime*fight_time

		output_string = f'|<span data-tooltip="{account}"> {name} </span> |'+' {{'+prof+'}} | '+"{:,}".format(round(fight_time))
		output_string += '|'+"{:.2f}".format(avg_might)
		output_string += "| "+"{:.2f}".format(round((might_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((might_5_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((might_10_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((might_15_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((might_20_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((might_25_uptime * 100), 4))+"%"
		output_string += '|'

		rows.append(output_string)
	squad_string = f'|Squad Average: |<|<'
	squad_string += '|'+"{:.2f}".format(round((squad_str_avg /(squad_fight_time)), 4))
	squad_string += "| "+"{:.2f}".format(round((squad_str_1 /(squad_fight_time) * 100), 4))+"%"
	squad_string += "| "+"{:.2f}".format(round((squad_str_5 /(squad_fight_time) * 100), 4))+"%"
	squad_string += "| "+"{:.2f}".format(round((squad_str_10 /(squad_fight_time) * 100), 4))+"%"
	squad_string += "| "+"{:.2f}".format(round((squad_str_15 /(squad_fight_time) * 100), 4))+"%"
	squad_string += "| "+"{:.2f}".format(round((squad_str_20 /(squad_fight_time) * 100), 4))+"%"
	squad_string += "| "+"{:.2f}".format(round((squad_str_25 /(squad_fight_time) * 100), 4))+"%"
	squad_string += '|h'
	rows.append(squad_string)
	rows.append("</$reveal>\n")
	
	# Stability stack table
	rows.append('<$reveal stateTitle=<<currentTiddler>> stateField="stacking_item" type="match" text="stability" animate="yes">\n')
	rows.append('|<$radio field="stacking_item" value="might"> Might </$radio> - <$radio field="stacking_item" value="stability"> Stability  </$radio> - {{Stability}} uptime by stack|c')
	rows.append('|thead-dark table-hover table-caption-top sortable|k')
	output_header =  '|!Name | !Class'
	output_header += ' | ! <span data-tooltip="Number of seconds player was in squad logs">Seconds</span>'
	output_header += '| !Avg| !1+ %| !2+ %| !5+ %'
	output_header += '|h'
	rows.append(output_header)
	
	stability_sorted_stacking_uptime_Table = []
	for uptime_prof_name in stacking_uptime_Table:
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_Stability'] / 1000) or 1
		stability_stacks = stacking_uptime_Table[uptime_prof_name]['Stability']

		if (top_stats['player'][uptime_prof_name]['active_time'] * 100) / max_fightTime < 1:
			continue

		avg_stab = sum(stack_num * stability_stacks[stack_num] for stack_num in range(1, 26)) / (fight_time * 1000)
		stability_sorted_stacking_uptime_Table.append([uptime_prof_name, avg_stab])
	stability_sorted_stacking_uptime_Table = sorted(stability_sorted_stacking_uptime_Table, key=lambda x: x[1], reverse=True)
	stability_sorted_stacking_uptime_Table = list(map(lambda x: x[0], stability_sorted_stacking_uptime_Table))
	
	for uptime_prof_name in stability_sorted_stacking_uptime_Table:
		name = stacking_uptime_Table[uptime_prof_name]['name']
		prof = stacking_uptime_Table[uptime_prof_name]['profession']
		account = stacking_uptime_Table[uptime_prof_name]['account']
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_Stability'] / 1000) or 1
		stability_stacks = stacking_uptime_Table[uptime_prof_name]['Stability']

		avg_stab = sum(stack_num * stability_stacks[stack_num] for stack_num in range(1, 26)) / (fight_time * 1000)
		squad_stab_avg += avg_stab*fight_time
		stab_uptime = 1.0 - (stability_stacks[0] / (fight_time * 1000))
		squad_stab_1 += stab_uptime*fight_time
		stab_2_uptime = sum(stability_stacks[i] for i in range(2,26)) / (fight_time * 1000)
		squad_stab_2 += stab_2_uptime*fight_time
		stab_5_uptime = sum(stability_stacks[i] for i in range(5,26)) / (fight_time * 1000)
		squad_stab_5 += stab_5_uptime*fight_time

		output_string = f'|<span data-tooltip="{account}"> {name} </span> |'+' {{'+prof+'}} | '+"{:,}".format(round(fight_time))
		output_string += '|'+"{:.2f}".format(avg_stab)
		output_string += "| "+"{:.2f}".format(round((stab_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((stab_2_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((stab_5_uptime * 100), 4))+"%"
		output_string += '|'

		rows.append(output_string)
	squad_string = f'|Squad Average: |<|<'
	squad_string += '|'+"{:.2f}".format(round((squad_stab_avg) /(squad_fight_time), 4))
	squad_string += "| "+"{:.2f}".format(round((squad_stab_1 /(squad_fight_time) * 100), 4))+"%"
	squad_string += "| "+"{:.2f}".format(round((squad_stab_2 /(squad_fight_time) * 100), 4))+"%"
	squad_string += "| "+"{:.2f}".format(round((squad_stab_5 /(squad_fight_time) * 100), 4))+"%"
	squad_string += '|h'
	rows.append(squad_string)
	rows.append("</$reveal>\n")


	text = "\n".join(rows)
	tags = f"{tid_date_time}"
	title = f"{tid_date_time}-Stacking-Buffs"
	caption = "Stacking Buffs"

	append_tid_for_output(
		create_new_tid_from_template(title, caption, text, tags, fields={"stacking_item": "might"}),
		tid_list	
	)
	
def build_defense_damage_mitigation(player_damage_mitigation: dict, player_minion_damage_mitigation: dict, top_stats: dict, tid_date_time: str, tid_list: list) -> None:
	"""
	Build a table of defense damage mitigation for each player in the log running the extension.

	This function iterates over the player_damage_mitigation dictionary, which contains dictionaries of defensive actions for each player.
	It then builds a table with the following columns:
		- Name
		- Prof
		- Fight Time
		- Blocked
		- Evaded
		- Glanced
		- Missed
		- Invulned
		- Interrupted
		- Damage Mitigation
		- Damage Mitigation per Second

	The table will have one row for each player running the extension, and the columns will contain the player's name, profession, fight time, and the number of each defensive action and damage mitigation for each defensive action.

	The function will also add the table to the tid_list for output.
	"""
	tags = f"{tid_date_time}"
	title = f"{tid_date_time}-Defense-Damage-Mitigation"
	caption = "Damage Mitigation"

	rows = []
	rows.append("\n!!!@@ Note: This is a rough estimate based on average skill damage by the enemy and defensive actions by the player.@@")
	rows.append("\n!!!@@If you have high incoming downed damage the values are likely exaggerated@@\n\n")

	rows.append('<$reveal stateTitle=<<currentTiddler>> stateField="mitigation" type="match" text="Player" animate="yes">\n')
	rows.append('|<$radio field="mitigation" value="Player"> Player </$radio> - <$radio field="mitigation" value="Minions"> Minions  </$radio> - Damage Mitigation based on Average Enemy Damage per `skillID` and Player Defensive Activity per `skillID` |c')
	rows.append('|thead-dark table-hover table-caption-top sortable|k')
	rows.append("|!Player | !Prof | !{{FightTime}} | !{{directHits}}| !{{evadedCount}}| !{{blockedCount}}| !{{glanceCount}}| !{{missedCount}}| !{{invulnedCount}}| !{{interruptedCount}}| !~AvgDmg|!~AvgDmg/{{FightTime}}| !~MinDmg| !~MinDmg/{{FightTime}}|h")

	for name_prof, data in player_damage_mitigation.items():
		player_name, player_profession, player_account = name_prof.split("|")
		if name_prof in top_stats['player']:
			active_time = round(top_stats['player'][name_prof].get('active_time', 0) / 1000)
		else:
			active_time = 0		
		player_profession = "{{"+player_profession+"}} "+player_profession[:3]
		total_blocked = 0
		total_evaded = 0
		total_missed = 0
		total_glanced = 0
		total_invulned = 0
		total_interrupted = 0
		total_mitigation = 0
		total_hits = 0
		total_blocked_dmg = 0
		total_evaded_dmg = 0
		total_missed_dmg = 0
		total_glanced_dmg = 0
		total_invulned_dmg = 0
		total_interrupted_dmg = 0
		total_min_mitigation = 0

		for skill in data:
			if data[skill]["avoided_damage"]:
				total_blocked += data[skill]["blocked"]
				total_evaded += data[skill]["evaded"]
				total_missed += data[skill]["missed"]
				total_glanced += data[skill]["glanced"]
				total_invulned += data[skill]["invulned"]
				total_interrupted += data[skill]["interrupted"]
				total_mitigation += data[skill]["avoided_damage"]
				total_hits += data[skill]["skill_hits"]
				total_blocked_dmg += data[skill]["blocked_dmg"]
				total_evaded_dmg += data[skill]["evaded_dmg"]
				total_missed_dmg += data[skill]["missed_dmg"]
				total_glanced_dmg += data[skill]["glanced_dmg"]
				total_invulned_dmg += data[skill]["invulned_dmg"]
				total_interrupted_dmg += data[skill]["interrupted_dmg"]
				total_min_mitigation += data[skill]["min_avoided_damage"]

		blocked_entry = f'<span data-tooltip="Dmg: {total_blocked_dmg:,.0f}">{total_blocked:,.0f}</span>'
		evaded_entry = f'<span data-tooltip="Dmg: {total_evaded_dmg:,.0f}">{total_evaded:,.0f}</span>'
		missed_entry = f'<span data-tooltip="Dmg: {total_missed_dmg:,.0f}">{total_missed:,.0f}</span>'
		glanced_entry = f'<span data-tooltip="Dmg: {total_glanced_dmg:,.0f}">{total_glanced:,.0f}</span>'
		invulned_entry = f'<span data-tooltip="Dmg: {total_invulned_dmg:,.0f}">{total_invulned:,.0f}</span>'
		interrupted_entry = f'<span data-tooltip="Dmg: {total_interrupted_dmg:,.0f}">{total_interrupted:,.0f}</span>'
		avg_damage = round(total_mitigation/active_time) if active_time > 0 else 0
		min_avg_damage = round(total_min_mitigation/active_time) if active_time > 0 else 0
		rows.append(f"|<span data-tooltip='{player_account}'>{player_name}</span> |{player_profession}| {active_time:,.1f} | {total_hits:,}| {evaded_entry}| {blocked_entry}| {glanced_entry}| {missed_entry}| {invulned_entry}| {interrupted_entry}| {total_mitigation:,.0f}| {avg_damage:,.0f}| {total_min_mitigation:,.0f}| {min_avg_damage:,.0f}|")

	rows.append("</$reveal>\n")

	rows.append('<$reveal stateTitle=<<currentTiddler>> stateField="mitigation" type="match" text="Minions" animate="yes">\n')
	rows.append('|<$radio field="mitigation" value="Player"> Player </$radio> - <$radio field="mitigation" value="Minions"> Minions  </$radio> - Damage Mitigation based on Average Enemy Damage per `skillID` and Minion Defensive Activity per `skillID` |c')
	rows.append('|thead-dark table-hover table-caption-top sortable|k')
	rows.append("|!Player | !Prof |!Minion | !{{FightTime}} | !{{directHits}}| !{{evadedCount}}| !{{blockedCount}}| !{{glanceCount}}| !{{missedCount}}| !{{invulnedCount}}| !{{interruptedCount}}| !~AvgDmg|!~AvgDmg/{{FightTime}}| !~MinDmg| !~MinDmg/{{FightTime}}|h")

	for name_prof, minion_data in player_minion_damage_mitigation.items():
		player_name, player_profession, player_account = name_prof.split("|")
		if name_prof in top_stats['player']:
			active_time = round(top_stats['player'][name_prof].get('active_time', 0) / 1000)
		else:
			active_time = 0		
		player_profession = "{{"+player_profession+"}} "+player_profession[:3]

		for minion in minion_data:
			total_blocked = 0
			total_evaded = 0
			total_missed = 0
			total_glanced = 0
			total_invulned = 0
			total_interrupted = 0
			total_mitigation = 0
			total_hits = 0
			total_blocked_dmg = 0
			total_evaded_dmg = 0
			total_missed_dmg = 0
			total_glanced_dmg = 0
			total_invulned_dmg = 0
			total_interrupted_dmg = 0
			total_min_mitigation = 0

			for skill in minion_data[minion]:
				#if minion_data[minion][skill]["avoided_damage"]:
				total_blocked += minion_data[minion][skill]["blocked"]
				total_evaded += minion_data[minion][skill]["evaded"]
				total_missed += minion_data[minion][skill]["missed"]
				total_glanced += minion_data[minion][skill]["glanced"]
				total_invulned += minion_data[minion][skill]["invulned"]
				total_interrupted += minion_data[minion][skill]["interrupted"]
				total_mitigation += minion_data[minion][skill]["avoided_damage"]
				total_hits += minion_data[minion][skill]["skill_hits"]
				total_blocked_dmg += minion_data[minion][skill]["blocked_dmg"]
				total_evaded_dmg += minion_data[minion][skill]["evaded_dmg"]
				total_missed_dmg += minion_data[minion][skill]["missed_dmg"]
				total_glanced_dmg += minion_data[minion][skill]["glanced_dmg"]
				total_invulned_dmg += minion_data[minion][skill]["invulned_dmg"]
				total_interrupted_dmg += minion_data[minion][skill]["interrupted_dmg"]
				total_min_mitigation += minion_data[minion][skill]["min_avoided_damage"]

			blocked_entry = f'<span data-tooltip="Dmg: {total_blocked_dmg:,.0f}">{total_blocked:,.0f}</span>'
			evaded_entry = f'<span data-tooltip="Dmg: {total_evaded_dmg:,.0f}">{total_evaded:,.0f}</span>'
			missed_entry = f'<span data-tooltip="Dmg: {total_missed_dmg:,.0f}">{total_missed:,.0f}</span>'
			glanced_entry = f'<span data-tooltip="Dmg: {total_glanced_dmg:,.0f}">{total_glanced:,.0f}</span>'
			invulned_entry = f'<span data-tooltip="Dmg: {total_invulned_dmg:,.0f}">{total_invulned:,.0f}</span>'
			interrupted_entry = f'<span data-tooltip="Dmg: {total_interrupted_dmg:,.0f}">{total_interrupted:,.0f}</span>'
			avg_damage = round(total_mitigation/active_time) if active_time > 0 else 0
			min_avg_damage = round(total_min_mitigation/active_time) if active_time > 0 else 0
			if total_mitigation:
				rows.append(f"|<span data-tooltip='{player_account}'>{player_name}</span> |{player_profession}|{minion} | {active_time:,.1f} | {total_hits:,}| {evaded_entry}| {blocked_entry}| {glanced_entry}| {missed_entry}| {invulned_entry}| {interrupted_entry}| {total_mitigation:,.0f}| {avg_damage:,.0f}| {total_min_mitigation:,.0f}| {min_avg_damage:,.0f}|")
	rows.append("\n\n")

	text = "\n".join(rows)

	append_tid_for_output(
		create_new_tid_from_template(title, caption, text, tags),
		tid_list	
	)

def build_fight_line_chart(fight_data: dict, tid_date_time: str, tid_list: list) -> str:
	"""
	Build a line chart for a single fight in the log. The chart shows both outgoing and incoming damage over time.

	Args:
		fight_data (dict): A dictionary of fight data from the log.
		fight_num (int): The fight number to generate the chart for.

	Returns:
		str: The configuration string for the line chart.
	"""

	for fight_num in fight_data:
		outgoing_damage_data = list(fight_data[fight_num]["damage1S"].values())
		incoming_damage_data = list(fight_data[fight_num]["damageTaken1S"].values())
		time_series = list(fight_data[fight_num]["damage1S"].keys())
		zf_fight_num = str(fight_num).zfill(2)
		chart_title = f"Fight-{zf_fight_num}: Damage Output Review"
		line_chart_config = '```py\nPlayer_Line = players with DPS > 700 for the fight\n```\n\n\n\n<$echarts $text="""\n'
		line_chart_config += f"""
		option = {{
		title: {{
			text: '{chart_title}',
			left: 'center'
		}},
		grid: {{
		left: '5%',
		right: '15%'
		}},
		legend: {{
			type: 'scroll',
			orient: 'vertical',
			selector: ['all', 'inverse'],
			right: 10,
			top: 20,
			bottom: 20,
		}},
		tooltip: {{
			trigger: 'axis',
			showContent: true
		}},
		dataZoom: [
			{{
			show: true,
			realtime: true,
			start: 30,
			end: 70,
			xAxisIndex: [0, 1]
			}},
			{{
			type: 'inside',
			realtime: true,
			start: 30,
			end: 70,
			xAxisIndex: [0, 1]
			}}
		],
		xAxis: {{
			type: 'category',
			nameLocation: 'middle',
			nameGap: 40,
			name: 'Fight Time',
			axisLabel: {{
			formatter: '{{value}}s',
			align: 'center'
			}},
			data: {time_series}
		}},
		yAxis: {{
			type: 'value',
			nameLocation: 'middle',
			nameGap: 55,
			name: 'Damage'
		}},
		series: [
			{{
			name: 'Outgoing Damage',
			data: {outgoing_damage_data},
			type: 'line',
			smooth: true,
			itemStyle: {{
				// Color of the point.
				color: 'dodgerblue'
			}},
			emphasis: {{ focus: 'series' }}
			}},
			{{
			name: 'Incoming Damage',
			data: {incoming_damage_data},
			type: 'line',
			smooth: true,
			itemStyle: {{
			// Color of the point.
			color: 'khaki'
			}},
			emphasis: {{ focus: 'series' }}
			}}
		"""
		for player in fight_data[fight_num]["players"].keys():
			#last_value = max(fight_data[fight_num]["players"][player]['damage1S'].values())
			#num_keys = len(fight_data[fight_num]["players"][player]['damage1S'])

			#if (last_value/num_keys) < 700:
			#	continue

			player_name = player.split("-")[1][:3]+" - "+player.split("-")[2]
			player_damage_data = []
			last_index = 0
			for index in range(len(fight_data[fight_num]["players"][player]['damage1S'])):
				cur_damage = fight_data[fight_num]["players"][player]['damage1S'][index] # - fight_data[fight_num]["players"][player]['damage1S'][last_index]
				
				player_damage_data.append(cur_damage)
				last_index = index

			player_line_chart_config = f""",
		{{
		name: '{player_name}',
		data: {player_damage_data},
		type: 'line',
		smooth: true,
		emphasis: {{ focus: 'series' }}
		}}"""
			line_chart_config += player_line_chart_config
		line_chart_config += '\n    ]\n    };\n\n"""$height="500px" $width="100%" $theme="dark"/>'

		line_chart_title = f"{tid_date_time}_Fight_{zf_fight_num}_Damage_Output_Review"
		line_chart_caption = f"Fight-{zf_fight_num}: Damage Output Review"
		line_chart_tags = "Chart"

		append_tid_for_output(
			create_new_tid_from_template(line_chart_title, line_chart_caption, line_chart_config, line_chart_tags),
			tid_list	
		)

def build_pull_stats_tid(tid_date_time: str, top_stats: dict, skill_data: dict, tid_list: list) -> None:
	Pull_Skills = config.pull_skills
	
	pull_data = {
		'incoming': {},
		'outgoing': {}
	}

	Used_Pulls = {}
	incoming_pulls = []
	outgoing_pulls = []

	for skill, data in skill_data.items():
		if skill in Pull_Skills:
			Used_Pulls[skill] = f"[img width=24 [{data['name']}|{data['icon']}]]"

	for player, p_data in top_stats['player'].items():
		name = p_data['name']
		prof = p_data['profession']

		if player not in pull_data['incoming']:
			pull_data['incoming'][player] = {}

		for skill, s_data in p_data['totalDamageTaken'].items():
			if f"s{skill}" in Used_Pulls and s_data['hits']:
				Chits = s_data['connectedHits']
				hits = s_data['hits']
				if skill not in incoming_pulls:
					incoming_pulls.append(skill)

				if skill not in pull_data['incoming'][player]:
					pull_data['incoming'][player][skill] = {
						'chits': Chits,
						'hits': hits
					}
				else:
					pull_data['incoming'][player][skill]['chits'] += Chits
					pull_data['incoming'][player][skill]['hits'] += hits



		for skill, s_data in p_data['targetDamageDist'].items():
			if f"s{skill}" in Used_Pulls and s_data['hits']:
				Chits = s_data['connectedHits']
				hits = s_data['hits']
				if skill not in outgoing_pulls:
					outgoing_pulls.append(skill)

				if player not in pull_data['outgoing']:
					pull_data['outgoing'][player] = {}

				if skill not in pull_data['outgoing'][player]:
					pull_data['outgoing'][player][skill] = {	
						'chits': Chits,
						'hits': hits
					}
				else:
					pull_data['outgoing'][player][skill]['chits'] += Chits
					pull_data['outgoing'][player][skill]['hits'] += hits	

	tags = f"{tid_date_time}"
	title = f"{tid_date_time}-Pull-Skills"
	caption = "Pull Skill Summary"
	rows=[]
	rows.append("!!!@@ Note: Pull data is derived from connected hits for skills with pull effects.@@\n")
	rows.append("!!!@@It does not reflect actual observed pull events as they are unavailable in the json.@@")
	rows.append('\n<div class="flex-row">\n     <div class="flex-col">\n\n')
	rows.append("\n\n|thead-dark table-caption-top table-hover sortable|k")
	rows.append("| Incoming Pulls |c")	
	header = "|!Player | !Prof | !{{FightTime}}|"
	for skill in incoming_pulls:
		skill_header = Used_Pulls[f"s{skill}"]
		header += ' !'+skill_header+' |'
	header += 'h'
	rows.append(header)

	for player in pull_data['incoming']:
		name, prof, acct = player.split("|")
		name_entry = f"<span data-tooltip='{acct}'>{name}</span>"
		fight_time = round(top_stats['player'][player]['fight_time']/1000)
		row = f"|{name_entry} | {{{{{prof}}}}} | {fight_time:,.1f}|"
		for skill in incoming_pulls:
			if skill in pull_data['incoming'][player]:
				chits = pull_data['incoming'][player][skill].get('chits',0)
				hits = pull_data['incoming'][player][skill].get('hits',0)
				percentage=(chits/hits)*100 if hits else 0
				percentage =f"{percentage:,.1f}%"
			else:
				chits = "-"
				hits = "-"
				percentage= "-"
			entry = f" <span data-tooltip='{chits} of {hits} hits - ({percentage})'>{chits}</span> |"
			row += entry
		rows.append(row)
	rows.append('\n    </div>\n    <div class="flex-col">\n\n')
	rows.append("\n\n|thead-dark table-caption-top table-hover sortable|k")
	rows.append("| Outgoing Pulls |c")	
	header = "|!Player | Prof | !{{FightTime}}|"
	for skill in outgoing_pulls:
		skill_header = Used_Pulls[f"s{skill}"]
		header += ' !'+skill_header+' |'
	header += 'h'
	rows.append(header)

	for player in pull_data['outgoing']:
		name, prof, acct = player.split("|")
		name_entry = f"<span data-tooltip='{acct}'>{name}</span>"
		fight_time = round(top_stats['player'][player]['fight_time']/1000)
		row = f"|{name_entry} | {{{{{prof}}}}} | {fight_time:,.1f}|"
		for skill in outgoing_pulls:
			if skill in pull_data['outgoing'][player]:
				chits = pull_data['outgoing'][player][skill].get('chits',0)
				hits = pull_data['outgoing'][player][skill].get('hits',0)
				percentage=(chits/hits)*100 if hits else 0
			else:
				chits = "-"
				hits = "-"
				percentage= 0
			entry = f" <span data-tooltip='{chits} of {hits} hits - ({percentage:,.1f}%)'>{chits}</span> |"
			row += entry
		rows.append(row)

	rows.append('\n\n    </div>\n</div>\n\n')
	text = "\n".join(rows)

	append_tid_for_output(
		create_new_tid_from_template(title, caption, text, tags),
		tid_list
	)

#Add Glicko Leaderboard Support
def update_glicko_ratings(db_path: str = "Top_Stats.db"):

	def create_table(cursor):
		cursor.execute(
			"""CREATE TABLE IF NOT EXISTS player_ratings (
			date TEXT,
			account TEXT,
			name TEXT,
			profession TEXT,
			stat TEXT,
			rating REAL,
			rd REAL,
			vol REAL,
			delta REAL,
			PRIMARY KEY (date, account, stat)
		)"""
		)

	def get_stat_fields(cursor):
		cursor.execute("PRAGMA table_info(player_stats)")
		all_columns = [col[1] for col in cursor.fetchall()]
		skip_cols = {
			"date",
			"year",
			"month",
			"day",
			"account",
			"guild_status",
			"name",
			"profession",
			"date_name_prof",
		}
		return [
			col
			for col in all_columns
			if col not in skip_cols and col not in ("num_fights", "duration")
		]

	def get_raid_dates(cursor):
		cursor.execute("SELECT DISTINCT date FROM player_stats ORDER BY date")
		return [row[0] for row in cursor.fetchall()]

	def fetch_player_stats(cursor, raid_date, stat_fields):
		fields = ", ".join(
			["account", "name", "profession", "duration", "num_fights"] + stat_fields
		)
		cursor.execute(
			f"SELECT {fields} FROM player_stats WHERE date = ?", (raid_date,)
		)
		return cursor.fetchall()

	def normalize_stats(rows, stat_fields, smaller_is_better_stats):
		stat_values = {stat: [] for stat in stat_fields}
		for row in rows:
			account, name, prof, duration, num_fights, *stats = row
			normalized_time = max(
				duration, 10
			)  # Avoid division by very small time windows


			for stat, value in zip(stat_fields, stats):
				# Check if the stat should be treated as "smaller is better"
				if stat in smaller_is_better_stats:
					# Inverse the stat value for smaller-is-better
					normalized = (max(value or 0, 1) ** -1) / (normalized_time / 60.0)
				else:
					# Normalize stat per minute of activity (larger values are better)
					normalized = (value or 0) / (normalized_time / 60.0)
				
				stat_values[stat].append((account, name, prof, normalized))
		return stat_values

	def update_player_rating(player_i, opponents, scores):
		MAX_RD = 350.0
		rating_list = [min(max(op.getRating(), 100), 3000) for op in opponents]
		rd_list = [min(op.getRd(), MAX_RD) for op in opponents]

		if player_i.getRd() > MAX_RD:
			player_i.rd = MAX_RD
		if player_i.getRd() < 50.0:
			player_i.rd = 50.0

		if (
			sum(
				(
					pow(player_i._g(rd), 2)
					* player_i._E(r, rd)
					* (1 - player_i._E(r, rd))
					for r, rd in zip(rating_list, rd_list)
				)
			)
			== 0
		):
			raise ZeroDivisionError("Avoided zero division in Glicko v calculation")

		player_i.update_player(rating_list, rd_list, scores)
		# Clamp player's rating between 100 and 3000
		player_i.rating = min(max(player_i.getRating(), 100), 3000)


	smaller_is_better_stats = {"damage_taken", "downed", "deaths"}
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()

	create_table(cursor)
	stat_fields = get_stat_fields(cursor)
	all_dates = get_raid_dates(cursor)

	ratings = defaultdict(lambda: defaultdict(lambda: GlickoPlayer()))
	last_rating = defaultdict(dict)  # will store stat -> previous rating

	for raid_date in all_dates:
		rows = fetch_player_stats(cursor, raid_date, stat_fields)
		if not rows:
			continue
		max_duration = max((row[3] or 0) for row in rows)
		min_required = max_duration * 0.4
		rows = [row for row in rows if (row[3] or 0) >= min_required]
		stat_values = normalize_stats(rows, stat_fields, smaller_is_better_stats)

		# Compute activity score for RD estimation
		activity_seconds = defaultdict(float)
		for row in rows:
			acc, name, prof, duration, *_ = row
			player_key = f"{name}#{prof}"
			activity_seconds[player_key] += duration or 0
		activity_score = {k: v / 60.0 for k, v in activity_seconds.items() if v > 0}  # convert to minutes

		# Compute raid attendance count for RD estimation
		player_days = defaultdict(set)
		for row in rows:
			acc, name, prof, *_ = row
			player_days[f"{name}#{prof}"].add(raid_date)
		raid_counts = {k: len(v) for k, v in player_days.items()}

		for stat, players in stat_values.items():
			sorted_players = sorted(players, key=lambda x: x[3], reverse=True)
			for i, (acc_i, name_i, prof_i, _) in enumerate(sorted_players):
				player_key_i = f"{name_i}#{prof_i}"
				if stat not in ratings[player_key_i]:
					#activity = activity_score.get(player_key_i, 1.0)
					raid_count = raid_counts.get(player_key_i, 1)
					#init_rd = max(80.0, 350.0 / (activity ** 0.5))
					init_rd = max(80.0, 350.0 / (raid_count**0.5))
					ratings[player_key_i][stat] = GlickoPlayer(
						rating=1500, rd=init_rd, vol=0.06
					)

				player_i = ratings[player_key_i][stat]
				opponents, scores = [], []

				for j, (acc_j, name_j, prof_j, _) in enumerate(sorted_players):
					if i == j:
						continue
					player_key_j = f"{name_j}#{prof_j}"
					opponents.append(ratings[player_key_j][stat])
					scores.append(1 if i < j else 0)

				try:
					if opponents:
						update_player_rating(player_i, opponents, scores)
				except (OverflowError, ZeroDivisionError) as e:
					print(f"[SKIP] {name_i} stat: {stat} - {type(e).__name__}: {e}")
					continue

				new_rating = round(player_i.getRating(), 2)
				prev_rating = last_rating[player_key_i].get(stat)
				delta = (
					None if prev_rating is None else round(new_rating - prev_rating, 2)
				)
				last_rating[player_key_i][stat] = new_rating

				cursor.execute(
					"""INSERT OR REPLACE INTO player_ratings
					(date, account, name, profession, stat, rating, rd, vol, delta)
					VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
					(
						raid_date,
						acc_i,
						name_i,
						prof_i,
						stat,
						new_rating,
						round(player_i.getRd(), 2),
						round(player_i.vol, 6),
						delta,
					),
				)

	conn.commit()
	conn.close()
	print("Glicko ratings (with normalization and trends) updated.")


def generate_leaderboard(stat: str, db_path: str, top_n: int = 25) -> str:
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()

	cursor.execute('''
		SELECT account, name, profession, MAX(date), rating, delta
		FROM player_ratings
		WHERE stat = ?
		GROUP BY name, profession
		ORDER BY rating DESC
		LIMIT ?
	''', (stat, top_n))
	rows = cursor.fetchall()

	# Collect total activity and normalized stat per player_key
	raid_counts = {}
	avg_norm = {}
	activity_minutes = {}
	guild_members = {}
	cursor.execute(f'''
		SELECT name || '#' || profession AS player_key,
			   COUNT(DISTINCT date),
			   guild_status AS guild_status,
			   SUM(CASE WHEN duration > 0 THEN {stat} ELSE 0 END),
			   SUM(duration) / 60.0
		FROM player_stats
		GROUP BY player_key
	''')
	for player_key, raid_count, guild_status, total_stat, total_minutes in cursor.fetchall():
		raid_counts[player_key] = raid_count
		activity_minutes[player_key] = total_minutes
		guild_members[player_key] = guild_status
		if stat in ('kills', 'downs', 'downed', 'killed', 'resurrects'):
			avg_norm[player_key] = round(total_stat / (total_minutes), 4) if total_minutes else '-'
		else:
			avg_norm[player_key] = round(total_stat / (total_minutes*60), 4) if total_minutes else '-'

		# Compute activity bucket
	member_bucket = {}
	for player_key, member_status in guild_members.items():
		if member_status in (None, 0, "--==Non Member==--"):
			member_bucket[player_key] = "❌"
		elif member_status in ("-"):
			member_bucket[player_key] = "❓"
		else:
			member_bucket[player_key] = "✅"
			
	conn.close()

	def delta_str(delta):
		if delta is None:
			return ""
		return f"{abs(delta):.1f} {'🔺' if delta > 0 else '🔻'}"

	# Build table with activity classification
	table = f"| Rank |Name|Profession| Glicko Rating| Trend| Raids | Guild Member | Avg {stat.title()}|h\n"
	table += "|thead-dark table-hover table-caption-top tc-center|k\n"
	table += f"| {stat.title()} Leaderboard - Top {top_n} Players |c\n"

	rank = 1
	for acc, name, prof, _, rating, delta in rows:
		player_key = f"{name}#{prof}"
		raids = raid_counts.get(player_key, '-')
		avg = avg_norm.get(player_key, '-')

		if avg in ('-', None) or avg == 0:
			continue
		
		membership = member_bucket.get(player_key, '-')
		if membership == "❌":
			continue

		if stat in ('kills', 'downs', 'downed', 'killed', 'resurrects'):
			avg = f"{avg:,.2f}/min"
		else:
			avg = f"{avg:,.2f}/sec"

		tt_name = f'<span data-tooltip="{acc}">{name}</span>'
		table += f"| {rank} |{tt_name} |{{{{{prof}}}}} {prof} | {round(rating, 1)} | {delta_str(delta)}| {raids} | {membership} | {avg}|\n"
		rank += 1

	return table


def save_high_score(
	db_path: str,
	account: str,
	player: str,
	profession: str,
	fight_times_stamp: str,
	fight_log_link: str,
	stat_category: str,
	stat_info: str,
	stat_value: float,
):
	# Connect to the database
	conn = sqlite3.connect(db_path)
	cur = conn.cursor()

	# Create the High_Scores table if it doesn't exist
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS high_scores (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			account TEXT,
			player TEXT,
			profession TEXT,
			fight_times_stamp TEXT,
			fight_log_link TEXT,
			stat_category TEXT,
			stat_info TEXT,
			stat_value REAL
		)
	"""
	)

	# Insert the new high score entry
	cur.execute(
		"""
		INSERT INTO high_scores (
			account, player, profession,
			fight_times_stamp, fight_log_link,
			stat_category, stat_info, stat_value
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	""",
		(
			account,
			player,
			profession,
			fight_times_stamp,
			fight_log_link,
			stat_category,
			stat_info,
			stat_value,
		),
	)

	# Keep only the top 25 scores for each stat category
	cur.execute(
		f"""
		DELETE FROM high_scores
		WHERE id NOT IN (
			SELECT id FROM high_scores
			WHERE stat_category = ?
			ORDER BY stat_value DESC
			LIMIT 25
		)
		AND stat_category = ?
	""",
		(stat_category, stat_category),
	)

	# Commit and close
	conn.commit()
	conn.close()


def write_high_scores_to_db(highscores, fights, skill_data, db_path):
	for category, stat_data in highscores.items():
		STAT_NAME_MAP = {
			"burst_damage1S": "1S Burst Damage",
			"fight_dps": "Damage per Second",
			"statTarget_killed": "Kills per Second",
			"statTarget_downed": "Downs per Second",
			"statTarget_downContribution": "Down Contrib per Second",
			"defenses_blockedCount": "Blocks per Second",
			"defenses_evadedCount": "Evades per Second",
			"defenses_dodgeCount": "Dodges per Second",
			"defenses_invulnedCount": "Invulned per Second",
			"defenses_boonStrips": "Incoming Strips per Second",
			"support_condiCleanse": "Cleanses per Second",
			"support_boonStrips": "Strips per Second",
			"extHealingStats_Healing": "Healing per Second",
			"extBarrierStats_Barrier": "Barrier per Second",
			"statTarget_appliedCrowdControl": "Crowd Control-Out per Second",
			"defenses_receivedCrowdControl": "Crowd Control-In per Second",
			"statTarget_max": "Highest Outgoing Skill Damage",
			"totalDamageTaken_max": "Highest Incoming Skill Damage",
		}

		stat = STAT_NAME_MAP.get(category)

		for player in stat_data:
			stat_info = ""
			#print(player)
			if " | " in player:
				player_data = player.split(" | ")[0]
				if len(player_data.split("-")) > 3:
					prof_player, account, fight_num, _ = player_data.split("-")
				else:
					prof_player, account, fight_num = player_data.split("-")
				stat_value = stat_data[player]
				if "max" in category:
					skill_id = "s" + player.split(" | ")[1]
					skill_name = skill_data[skill_id]["name"]
					skill_icon = skill_data[skill_id]["icon"]
					stat_info = (
						f"[img width=24 [{skill_name}|{skill_icon}]] {skill_name}"
					)

			else:
				prof_player, account, fight_num, _ = player.split("-")
				stat_value = stat_data[player]
			profession, player = prof_player.split("}}")
			profession += "}}"
			fight_time = (
				f'{fights[int(fight_num)]["fight_date"]} - Fight #{fight_num}'
			)
			fight_link = fights[int(fight_num)]["fight_link"]
			save_high_score(
				db_path,
				account,
				player,
				profession,
				fight_time,
				fight_link,
				stat,
				stat_info,
				stat_value,
			)


def build_high_scores_leaderboard_tids(tid_date_time: str, db_path: str) -> None:
	"""
	Generate TiddlyWiki-formatted tables for each stat_category in the high_scores table.
	
	Returns:
		A dictionary where keys are stat_category names and values are TiddlyWiki-formatted tables.
	"""
	conn = sqlite3.connect(db_path)
	cur = conn.cursor()

	# Fetch all unique stat categories
	cur.execute("SELECT DISTINCT stat_category FROM high_scores")
	categories = [row[0] for row in cur.fetchall()]

	tables = {}

	for category in categories:
		# Fetch records for this category ordered by stat_value DESC
		cur.execute("""
			SELECT account, player, profession, fight_times_stamp, fight_log_link, stat_info, stat_value
			FROM high_scores
			WHERE stat_category = ?
			ORDER BY stat_value DESC
		""", (category,))
		rows = cur.fetchall()

		# Determine if stat_info column should be included
		include_stat_info = any(row[5] not in (None, "", "NULL") for row in rows)

		# Build header
		table = f"| {category} High Scores |c\n"
		table += "|thead-dark table-hover table-caption-top tc-center|k\n"
		headers = ["Player", "Profession"]
		if include_stat_info:
			headers.append("Info")
		headers.append("Fight")
		headers.append("Value")

		table += "| " + " | ".join(headers) + " |h\n"
		#table += "| " + " | ".join(["---"] * len(headers)) + " |\n"

		for row in rows:
			account, player, profession, timestamp, link, info, value = row
			profession = f"{profession} {profession[2:-2]}"
			player_tooltip = f'<span data-tooltip="{account}">{player}</span>'
			fight_link = f'<a href="{link}">{timestamp}</a>'

			if include_stat_info:
				table_row =f"|{player_tooltip} |{profession} |{info} |{fight_link} |{value:,.2f} |\n"
			else:
				table_row =f"|{player_tooltip} |{profession} |{fight_link} | {value:,.2f}|\n"
			table += table_row

		tid_title = f"{tid_date_time}-{category}-Leaderboard"
		tid_caption = f"📈 {category}"
		tid_tags = tid_date_time

		append_tid_for_output(
			create_new_tid_from_template(tid_title, tid_caption, table, tid_tags),
			tid_list
		)

	build_high_scores_leaderboard_menu_tid(tid_date_time, categories, tid_list)
	conn.close()


def build_high_scores_leaderboard_menu_tid(datetime: str, categories: list, tid_list: list) -> None:
	"""
	Build a TID for the high scores leaderboard menu.
	"""

	tags = f"{datetime}"
	title = f"{datetime}-high_scores_Leaderboard"
	caption = "High Scores Leaderboards"
	creator = "Drevarr@github.com"

	text = '\n<div style="padding:20px;text-align: center;">\n<h1>📈 GW2 WvW High Score Leaderboards</h1>\n<h3 class="subtitle">Historic High Scores for World vs World</h3>\n</div>\n\n'

	text += "<<tabs '"
	for category in categories:
		text += f"[[{datetime}-{category}-Leaderboard]] "
	text += (f"' '{datetime}-{category}-Leaderboard' '$:/temp/tab_leader' 'tc-center tc-max-width-80'>>")

	append_tid_for_output(
		create_new_tid_from_template(title, caption, text, tags, creator=creator),
		tid_list
	)
	

def build_leaderboard_tids(tid_date_time: str, leaderboard_stats: dict, tid_list: list, db_path: str) -> None:
	for stat in leaderboard_stats:
		table = generate_leaderboard(stat, db_path)
		tid_title = f"{tid_date_time}-{stat}-Leaderboard"
		tid_caption = f"🏆 {leaderboard_stats[stat]}"
		tid_tags = tid_date_time


		append_tid_for_output(
			create_new_tid_from_template(tid_title, tid_caption, table, tid_tags),
			tid_list
		)

def build_leaderboard_menu_tid(datetime: str, leaderboard_stats: dict, tid_list: list) -> None:
	"""
	Build a TID for the leaderboard menu.
	"""

	tags = f"{datetime}"
	title = f"{datetime}-Leaderboard"
	caption = "Glicko-based Leaderboards"
	creator = "Drevarr@github.com"

	text = '\n<div style="padding:20px;text-align: center;">\n<h1>🏆 GW2 WvW Leaderboards</h1>\n<h3 class="subtitle">Glicko-based rating system for World vs World performance</h3>\n</div>\n\n'

	text += "<<tabs '"
	for stat in leaderboard_stats:
		text += f"[[{datetime}-{stat}-Leaderboard]] "
	text += (f"' '{datetime}-{stat}-Leaderboard' '$:/temp/tab_leader' 'tc-center tc-max-width-80'>>")

	append_tid_for_output(
		create_new_tid_from_template(title, caption, text, tags, creator=creator),
		tid_list
	)

def build_boon_support_data(top_stats: dict, support_profs: dict, boon_dict: dict) -> None:
	"""
	Build data for the boon support stats to Discord.
	"""
	boon_support_data = {}
	print("Building data for boon support stats to Discord")
	# Iterate over the support professions
	for profession, support_boons in support_profs.items():
		# Initialize the support data for this profession
		profession = profession.title()
		boon_support_data[profession] = []
		header=["Name", "#F"]
		for boon in support_boons:
			header.append(boon_dict[boon][:4])
		boon_support_data[profession].append(header)

		# Iterate over the players of this profession
		for player, data in top_stats["player"].items():
			if data["guild_status"] == "--==Non Member==--":
				continue
			if data["profession"] == profession and data["fight_time"]:
				# Initialize the support data for this player
				player_data = []
				player_data.append(data["name"])
				player_data.append(data["num_fights"])
				#player_data.append(data["guild_status"])
				#player_data.append(round(data["fight_time"]/1000,1))
				# Iterate over the support boons
				for boon in support_boons:
					# Set the generation for this boon to 0 if not found
					boon_gen_sec = round(data['squadBuffs'].get(boon, {}).get('generation', 0)/data["fight_time"],2)
					player_data.append(boon_gen_sec)
				boon_support_data[profession].append(player_data)

	return boon_support_data


def send_profession_boon_support_embed(webhook_url: str, profession: str, prof_icon: str, prof_color: str, tid_date_time: str, data: list) -> None:
    """
    Build and send a Discord embed containing a profession name and ASCII table.
    """
    if len(data) <= 1:
        return
    if webhook_url == "false":
        return
    else:
        print("WebHook URL: ", webhook_url)		
    # Limit name field to 12 characters
    for row in data[1:]:
        row[0] = str(row[0])[:12]

    # Format buffs with 2 decimals
    for row in data[1:]:
        for i in range(3, len(row)):
            row[i] = f"{float(row[i]):.2f}"

    # Column widths
    column_widths = [max(len(str(item)) for item in col) for col in zip(*data)]

    # Max digit length for Fights
    fight_digit_len = max((len(str(row[1])) for row in data[1:]), default=1)

    def format_cell(item, idx, width):
        if idx == 0:  # Name
            return f"{str(item):<{width}}"
        elif idx == 1:  # Fights → zero-filled & centered
            if isinstance(item, str) and not item.isdigit():
                return f"{item:^{width}}"
            num_str = str(item).zfill(fight_digit_len)
            return f"{num_str:^{width}}"
        #elif idx == 2:  # Time → centered
        #    return f"{str(item):^{width}}"
        else:  # Buffs → right-aligned
            return f"{str(item):>{width}}"

    # Build ASCII table
    lines = []
    header_line = " | ".join(format_cell(item, idx, width)
                             for idx, (item, width) in enumerate(zip(data[0], column_widths)))
    lines.append(header_line)
    lines.append("-+-".join("-" * width for width in column_widths))

    for row in data[1:]:
        data_line = " | ".join(format_cell(item, idx, width)
                               for idx, (item, width) in enumerate(zip(row, column_widths)))
        lines.append(data_line)

    ascii_table = "\n".join(lines)

    # Construct the embed
    embed = {
        "author": {
        "name": profession,  # shows bold text with the icon
        "icon_url": prof_icon
    },
        "title": f"Support Boon Generation/Second on {tid_date_time}",
        "description": f"```\n{ascii_table}\n```",
		"color": prof_color,
        "footer": {
            "text": "TopStats - GW2_EI_Log_Combiner",
            "icon_url": "https://avatars.githubusercontent.com/u/16168556?s=48&v=4"
    }
	}

    # Send to Discord
    payload = {"embeds": [embed]}
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10  # prevents hanging forever
        )

        if response.status_code != 204:
            print(
                f"[Discord] Webhook failed: "
                f"{response.status_code} {response.text}"
            )

    except Timeout:
        print("[Discord] Webhook timeout — internet may be unstable")

    except ConnectionError:
        print("[Discord] Connection error — likely offline")

    except RequestException as e:
        print(f"[Discord] Unexpected request error: {e}")



def send_additional_data_embed(webhook_url: str, discord_additional_notes: str, tid_date_time: str) -> None:
    """
    Build and send a Discord embed containing an additional data note.
    """
    
    embed = {
        "author": {
        "name": 'TopStats',
        "icon_url": 'https://wiki.guildwars2.com/images/5/54/Commander_tag_%28blue%29.png'
    	},
        "title": f"Additional Notes: {tid_date_time}",
        "description": f"\n{discord_additional_notes}\n",
            "color": 0x6DB6DA,
        "footer": {
            "text": "TopStats - GW2_EI_Log_Combiner",
            "icon_url": "https://avatars.githubusercontent.com/u/16168556?s=48&v=4"
    	}
        }

    # Send to Discord
    payload = {"embeds": [embed]}
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )

        if response.status_code != 204:
            print(
                f"[Discord] Additional notes webhook failed: "
                f"{response.status_code} {response.text}"
            )

    except Timeout:
        print("[Discord] Additional notes webhook timeout")

    except ConnectionError:
        print("[Discord] Additional notes webhook connection error (offline?)")

    except RequestException as e:
        print(f"[Discord] Additional notes webhook error: {e}")
	

def write_data_to_excel(top_stats: dict, last_fight: str, excel_path: str = "Top_Stats.xlsx") -> None:
    """
    Write the top_stats dictionary to an Excel file using XlsxWriter.

    Parameters
    ----------
    top_stats : dict
        The top_stats dictionary containing all the data to be written to the Excel file.
    last_fight : str
        The date and time of the last fight in the format "Year-Month-Day-Hour-Minute-Second".
    excel_path : str
        Path to the Excel file to write to (default is 'Top_Stats.xlsx').
    """
    print("Writing raid stats to Excel")

    # Define headers
    headers = [
        'Date Name Prof', 'Date', 'Year', 'Month', 'Day', 'Num Fights', 'Duration', 'Account', 'Guild Status', 'Name', 'Profession',
        'Damage', 'Down Contribution', 'Downs', 'Kills', 'Damage Taken', 'Damage Barrier', 'Downed', 'Deaths', 'Cleanses',
        'Boon Strips', 'Resurrects', 'Healing', 'Barrier', 'Downed Healing', 'Stab gen', 'Might gen', 'Fury gen',
        'Quick gen', 'Alac gen', 'Prot gen', 'Regen gen', 'Vigor gen', 'Aegis gen', 'Swift gen', 'Resil gen', 'Resol gen'
    ]

    # Always create a new workbook (XlsxWriter cannot append)
    workbook = xlsxwriter.Workbook(excel_path)
    worksheet = workbook.add_worksheet("Player Stats")

    # Create bold format for headers
    bold_format = workbook.add_format({'bold': True})

    # Write headers
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, bold_format)

    year, month, day, *_ = last_fight.split("-")

    # Start writing data from row 1 (row 0 is headers)
    row_idx = 1
    for player_name_prof, player_stats in top_stats['player'].items():
        row = [
            f"{last_fight}_{player_stats['name']}_{player_stats['profession']}",
            last_fight,
            year,
            month,
            day,
            player_stats.get('num_fights', 0),
            player_stats.get('active_time', 0) / 1000,
            player_stats.get('account', ''),
            player_stats.get('guild_status', ''),
            player_stats.get('name', ''),
            player_stats.get('profession', ''),
            player_stats['dpsTargets'].get('damage', 0),
            player_stats['statsTargets'].get('downContribution', 0),
            player_stats['statsTargets'].get('downed', 0),
            player_stats['statsTargets'].get('killed', 0),
            player_stats['defenses'].get('damageTaken', 0),
            player_stats['defenses'].get('damageBarrier', 0),
            player_stats['defenses'].get('downCount', 0),
            player_stats['defenses'].get('deadCount', 0),
            player_stats['support'].get('condiCleanse', 0),
            player_stats['support'].get('boonStrips', 0),
            player_stats['support'].get('resurrects', 0),
            player_stats['extHealingStats'].get('outgoing_healing', 0),
            player_stats['extBarrierStats'].get('outgoing_barrier', 0),
            player_stats['extHealingStats'].get('downed_healing', 0),
            round(player_stats['squadBuffs'].get('b1122', {}).get('generation', 0) / 1000, 2),
            round(player_stats['squadBuffs'].get('b740', {}).get('generation', 0) / 1000, 2),
            round(player_stats['squadBuffs'].get('b725', {}).get('generation', 0) / 1000, 2),
            round(player_stats['squadBuffs'].get('b1187', {}).get('generation', 0) / 1000, 2),
            round(player_stats['squadBuffs'].get('b30328', {}).get('generation', 0) / 1000, 2),
            round(player_stats['squadBuffs'].get('b717', {}).get('generation', 0) / 1000, 2),
            round(player_stats['squadBuffs'].get('b718', {}).get('generation', 0) / 1000, 2),
            round(player_stats['squadBuffs'].get('b726', {}).get('generation', 0) / 1000, 2),
            round(player_stats['squadBuffs'].get('b743', {}).get('generation', 0) / 1000, 2),
            round(player_stats['squadBuffs'].get('b719', {}).get('generation', 0) / 1000, 2),
            round(player_stats['squadBuffs'].get('b26980', {}).get('generation', 0) / 1000, 2),
            round(player_stats['squadBuffs'].get('b873', {}).get('generation', 0) / 1000, 2)
        ]

        worksheet.write_row(row_idx, 0, row)
        row_idx += 1

    # Save file
    workbook.close()
    print(f"Excel file created: {excel_path}")


def write_data_to_db(top_stats: dict, last_fight: str, db_path: str = "Top_Stats.db") -> None:
		
	"""
	Write the top_stats dictionary to the database.

	Parameters
	----------
	top_stats : dict
		The top_stats dictionary containing all the data to be written to the database.
	last_fight : str
		The date and time of the last fight in the format "Year-Month-Day-Hour-Minute-Second".
	"""

	print("Writing raid stats to database")
	"""Write the top_stats dictionary to the database."""
	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()

	cursor.execute('''CREATE TABLE IF NOT EXISTS player_stats (
		date_name_prof TEXT UNIQUE, date TEXT, year TEXT, month TEXT, day TEXT, num_fights REAL, duration REAL, account TEXT, guild_status TEXT, name TEXT, profession TEXT,
		damage REAL, down_contribution REAL, downs REAL, kills REAL, damage_taken REAL, damage_barrier REAL, downed REAL, deaths REAL, cleanses REAL,
		boon_strips REAL, resurrects REAL, healing REAL, barrier REAL, downed_healing REAL, stab_gen REAL, migh_gen REAL, fury_gen REAL,
		quic_gen REAL, alac_gen REAL, prot_gen REAL, rege_gen REAL, vigo_gen REAL, aeg_gen REAL, swif_gen REAL, resi_gen REAL, reso_gen REAL)''')

	fields = '(date_name_prof, date, year, month, day, num_fights, duration, account, guild_status, name, profession, damage, down_contribution, downs, kills, damage_taken, damage_barrier, downed, deaths, cleanses, boon_strips, resurrects, healing, barrier, downed_healing, stab_gen, migh_gen, fury_gen, quic_gen, alac_gen, prot_gen, rege_gen, vigo_gen, aeg_gen, swif_gen, resi_gen, reso_gen)'
	placeholders = '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

	year, month, day, time = last_fight.split("-")

	for player_name_prof, player_stats in top_stats['player'].items():
		stats_values = [
			f"{last_fight}_{player_stats['name']}_{player_stats['profession']}",
			last_fight,
			year,
			month,
			day,
			player_stats.get('num_fights', 0),
			player_stats.get('active_time', 0) / 1000,
			player_stats.get('account', ''),
			player_stats.get('guild_status', ''),
			player_stats.get('name', ''),
			player_stats.get('profession', ''),
			player_stats['dpsTargets'].get('damage', 0),
			player_stats['statsTargets'].get('downContribution', 0),
			player_stats['statsTargets'].get('downed', 0),
			player_stats['statsTargets'].get('killed', 0),
			player_stats['defenses'].get('damageTaken', 0),
			player_stats['defenses'].get('damageBarrier', 0),
			player_stats['defenses'].get('downCount', 0),
			player_stats['defenses'].get('deadCount', 0),
			player_stats['support'].get('condiCleanse', 0),
			player_stats['support'].get('boonStrips', 0),
			player_stats['support'].get('resurrects', 0),
			player_stats['extHealingStats'].get('outgoing_healing', 0),
			player_stats['extBarrierStats'].get('outgoing_barrier', 0),
			player_stats['extHealingStats'].get('downed_healing', 0),
			round(player_stats['squadBuffs'].get('b1122', {}).get('generation', 0) / 1000, 2),
			round(player_stats['squadBuffs'].get('b740', {}).get('generation', 0) / 1000, 2),
			round(player_stats['squadBuffs'].get('b725', {}).get('generation', 0) / 1000, 2),
			round(player_stats['squadBuffs'].get('b1187', {}).get('generation', 0) / 1000, 2),
			round(player_stats['squadBuffs'].get('b30328', {}).get('generation', 0) / 1000, 2),
			round(player_stats['squadBuffs'].get('b717', {}).get('generation', 0) / 1000, 2),
			round(player_stats['squadBuffs'].get('b718', {}).get('generation', 0) / 1000, 2),
			round(player_stats['squadBuffs'].get('b726', {}).get('generation', 0) / 1000, 2),
			round(player_stats['squadBuffs'].get('b743', {}).get('generation', 0) / 1000, 2),
			round(player_stats['squadBuffs'].get('b719', {}).get('generation', 0) / 1000, 2),
			round(player_stats['squadBuffs'].get('b26980', {}).get('generation', 0) / 1000, 2),
			round(player_stats['squadBuffs'].get('b873', {}).get('generation', 0) / 1000, 2)
		]

		cursor.execute(f'INSERT OR REPLACE INTO player_stats {fields} VALUES {placeholders}', stats_values)
		conn.commit()

	conn.close()
	print("Database updated.")

def output_top_stats_json(top_stats: dict, buff_data: dict, skill_data: dict, damage_mod_data: dict, high_scores: dict, personal_damage_mod_data: dict, personal_buff_data: dict, fb_pages: dict, mechanics: dict, minions: dict, mesmer_clone_usage: dict, death_on_tag: dict, DPSStats: dict, commander_summary_data: dict, enemy_avg_damage_per_skill: dict, player_damage_mitigation: dict, player_minion_damage_mitigation: dict, stacking_uptime_Table: dict, IOL_revive: dict, fight_data: dict, health_data: dict, stats_per_fight: dict, outfile: str) -> None:
	"""Print the top_stats dictionary as a JSON object to the console."""

	json_dict = {}
	json_dict["overall_raid_stats"] = {key: value for key, value in top_stats['overall'].items()}
	json_dict["fights"] = {key: value for key, value in top_stats['fight'].items()}
	json_dict["parties_by_fight"] = {key: value for key, value in top_stats["parties_by_fight"].items()}
	json_dict["enemies_by_fight"] = {key: value for key, value in top_stats["enemies_by_fight"].items()}
	json_dict["players"] = {key: value for key, value in top_stats['player'].items()}
	json_dict["buff_data"] = {key: value for key, value in buff_data.items()}
	json_dict["skill_data"] = {key: value for key, value in skill_data.items()}
	json_dict["damage_mod_data"] = {key: value for key, value in damage_mod_data.items()}
	json_dict["skill_casts_by_role"] = {key: value for key, value in top_stats["skill_casts_by_role"].items()}
	json_dict["high_scores"] = {key: value for key, value in high_scores.items()}    
	json_dict["personal_damage_mod_data"] = {key: value for key, value in personal_damage_mod_data.items()}
	json_dict['personal_buff_data'] = {key: value for key, value in personal_buff_data.items()}
	json_dict["fb_pages"] = {key: value for key, value in fb_pages.items()}
	json_dict["mechanics"] = {key: value for key, value in mechanics.items()}
	json_dict["minions"] = {key: value for key, value in minions.items()}
	json_dict["mesmer_clone_usage"] = {key: value for key, value in mesmer_clone_usage.items()}
	json_dict["death_on_tag"] = {key: value for key, value in death_on_tag.items()}
	json_dict['players_running_healing_addon'] = top_stats['players_running_healing_addon']
	json_dict["DPSStats"] = {key: value for key, value in DPSStats.items()}
	json_dict["commander_summary_data"] = {key: value for key, value in commander_summary_data.items()}
	json_dict["enemy_avg_damage_per_skill"] = {key: value for key, value in enemy_avg_damage_per_skill.items()}
	json_dict["player_damage_mitigation"] = {key: value for key, value in player_damage_mitigation.items()}
	json_dict["player_minion_damage_mitigation"] = {key: value for key, value in player_minion_damage_mitigation.items()}
	json_dict["stacking_uptime_Table"] = {key: value for key, value in stacking_uptime_Table.items()}
	json_dict["IOL_revive"] = {key: value for key, value in IOL_revive.items()}
	json_dict["fight_data"] = {key: value for key, value in fight_data.items()}
	json_dict["health_data"] = {key: value for key, value in health_data.items()}
	json_dict['stats_per_fight'] = {key: value for key, value in stats_per_fight.items()}

	with open(outfile, 'w') as json_file:
		json.dump(json_dict, json_file, indent=4)

		print("JSON File Complete : "+outfile)
	json_file.close()
