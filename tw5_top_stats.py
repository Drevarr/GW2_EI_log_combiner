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


import argparse
import configparser
import sys
import os
import datetime

from collections import OrderedDict

import config_output
from parser_functions import *
from output_functions import *


if __name__ == '__main__':
	parser = argparse.ArgumentParser(
		description='This reads a set of arcdps reports in xml format and generates top stats.'
	)
	parser.add_argument('-i', '--input', dest='input_directory', help='Directory containing .json files from Elite Insights')
	parser.add_argument('-o', '--output', dest="output_filename", help="Override json file name to write the computed summary")
	parser.add_argument('-x', '--xls_output', dest="xls_output_filename", help="Override .xls file to write the computed summary")
	parser.add_argument('-j', '--json_output', dest="json_output_filename", help="Override .json file to write the computed stats data")
	parser.add_argument('-c', '--config_file', dest="config_file", help="Select a specific config file. Defaults to top_stats_config.ini")
	parser.add_argument('-d', '--description_append', dest="description_append", help="Appended to the description of the summary caption.")

	args = parser.parse_args()

	parse_date = datetime.datetime.now()
	tid_date_time = parse_date.strftime("%Y%m%d%H%M")

	args.config_file = args.config_file or "top_stats_config.ini"
	args.description_append = args.description_append or False

	config_ini = configparser.ConfigParser()
	config_ini.read(args.config_file)

	# Resolve input_directory
	input_directory = args.input_directory or config_ini.get('TopStatsCfg', 'input_directory', fallback='./')
	if not os.path.isdir(input_directory):
		print(f"Directory {input_directory} is not a directory or does not exist!")
		sys.exit()

	# Load weights from config or use defaults
	default_weights = {
		'Boon_Weights': ['Aegis', 'Alacrity', 'Fury', 'Might', 'Protection', 'Quickness',
						 'Regeneration', 'Resistance', 'Resolution', 'Stability',
						 'Swiftness', 'Vigor', 'Superspeed'],
		'Condition_Weights': ['Bleed', 'Burning', 'Confusion', 'Poison', 'Torment',
							  'Blind', 'Chilled', 'Crippled', 'Fear', 'Immobile',
							  'Slow', 'Taunt', 'Weakness', 'Vulnerability']
	}

	weights = {
		section: {k: 1 for k in keys}
		for section, keys in default_weights.items()
	}

	for section in config_ini.sections():
		if section in weights:
			weights[section] = dict(config_ini[section])

	# Load support professions and boons to track
	if "SupportProfs" in config_ini:
		support_profs = {}
		for prof, boons in config_ini["SupportProfs"].items():
			support_profs[prof] = [b.strip() for b in boons.split(",")]
	else:
		support_profs = None

	# Get the raw value and convert to list
	if "BlackList" in config_ini:
		blacklist_raw = config_ini.get('BlackList', 'accounts')
		blacklist = [account.strip() for account in blacklist_raw.split(',')]
	else:
		blacklist = []

	print("Participation 🏆 Only, Blacklisted accounts:", blacklist)

	# Output filenames
	if not args.xls_output_filename:
		args.xls_output_filename = os.path.join(input_directory, f"TW5_top_stats_{tid_date_time}.xls")
	if not args.json_output_filename:
		args.json_output_filename = os.path.join(input_directory, f"TW5_top_stats_{tid_date_time}.json")
	if not args.output_filename:
		args.output_filename = os.path.join(input_directory, f"Drag_and_Drop_Log_Summary_for_{tid_date_time}.json")
	else:
		args.output_filename = os.path.join(input_directory, args.output_filename)

	# Config values
	guild_name = config_ini.get('TopStatsCfg', 'guild_name', fallback=None)
	guild_id = config_ini.get('TopStatsCfg', 'guild_id', fallback=None)
	api_key = config_ini.get('TopStatsCfg', 'api_key', fallback=None)
	boons_detailed = config_ini.getboolean('TopStatsCfg', 'Boons_Detailed', fallback=False)
	offensive_detailed = config_ini.getboolean('TopStatsCfg', 'Offensive_Detailed', fallback=False)
	defenses_detailed = config_ini.getboolean('TopStatsCfg', 'Defenses_Detailed', fallback=False)
	support_detailed = config_ini.getboolean('TopStatsCfg', 'Support_Detailed', fallback=False)
	sort_mode = config_ini.get('TopStatsCfg', 'Sort_Mode', fallback='Total')
	write_all_data_to_json = config_ini.getboolean('TopStatsCfg', 'write_all_data_to_json', fallback=False)
	fight_data_charts = config_ini.getboolean('TopStatsCfg', 'fight_data_charts', fallback=False)
	db_update = config_ini.getboolean('TopStatsCfg', 'db_update', fallback=False)
	db_output_filename = config_ini.get('TopStatsCfg', 'db_output_filename', fallback='Top_Stats.db')
	db_path = config_ini.get('TopStatsCfg', 'db_path', fallback='.')

	write_excel = config_ini.getboolean('TopStatsCfg', 'write_excel', fallback=False)
	excel_output_filename = config_ini.get('TopStatsCfg', 'excel_output_filename', fallback='Top_Stats.xlsx')
	excel_path = config_ini.get('TopStatsCfg', 'excel_path', fallback='.')

	skill_casts_by_role_limit = config_ini.getint('TopStatsCfg', 'skill_casts_by_role_limit', fallback=40)
	enable_hide_columns = config_ini.getboolean('TopStatsCfg', 'hide_columns', fallback=False)

	webhook_url = config_ini.get('DiscordCfg', 'webhook_url', fallback=False)

	# Ensure output directories exist
	os.makedirs(db_path, exist_ok=True)
	os.makedirs(excel_path, exist_ok=True)

	db_output_full_path = os.path.join(db_path, db_output_filename)
	excel_output_full_path = os.path.join(excel_path, excel_output_filename)

	# Process files
	sorted_files = sorted(os.listdir(input_directory))
	file_date = datetime.datetime.now()
	fight_num = 0

	print(f"Using input directory {input_directory}, writing output to {args.output_filename}")

	guild_data = None
	if guild_id and api_key:
		guild_data = fetch_guild_data(guild_id, api_key, max_retries=3, backoff_factor=0.5)

	print("guild_id: ", guild_id)
	print("API_KEY: ", api_key)

	for filename in sorted_files:
		
		# skip files of incorrect filetype
		file_start, file_extension = os.path.splitext(filename)
		# if args.filetype not in file_extension or "top_stats" in file_start:
		if file_extension not in ['.json', '.gz'] or "Drag_and_Drop_" in file_start or "TW5_top_stats_" in file_start:
			continue

		print_string = "parsing " + filename
		print(print_string)
		file_path = "".join((input_directory, "/", filename))

		fight_num += 1
		
		parse_file(file_path, fight_num, guild_data, fight_data_charts, blacklist)

	print("Parsing Complete")

	tag_data, tag_list = build_tag_summary(top_stats)
	tid_date_time = top_stats['overall']['last_fight']
	
	#create the main tiddler and append to tid_list
	build_main_tid(tid_date_time, tag_list, guild_name, args.description_append)

	output_tag_summary(tag_data, tid_date_time)

	#create the menu tiddler and append to tid_list
	build_menu_tid(tid_date_time, db_update)

	build_dashboard_menu_tid(tid_date_time)
	
	build_general_stats_tid(tid_date_time, offensive_detailed, defenses_detailed, support_detailed)

	build_buffs_stats_tid(tid_date_time, boons_detailed)

	build_boon_stats_tid(tid_date_time)
	for boon_other in ["Defensive", "Offensive", "Support"]:
		build_other_boon_stats_tid(tid_date_time, boon_other)

	build_damage_modifiers_menu_tid(tid_date_time)

	build_healer_menu_tabs(top_stats, "Healers", tid_date_time)
	build_healer_outgoing_tids(top_stats, skill_data, buff_data, "Healers", tid_date_time)

	build_profession_damage_modifier_stats_tid(personal_damage_mod_data, "Damage Modifiers", tid_date_time)

	build_shared_damage_modifier_summary(top_stats, damage_mod_data, "Shared Damage Mods", tid_date_time)
		
	defense_stats = config_output.defenses_table
	build_category_summary_report(top_stats, defense_stats, enable_hide_columns, "Defenses", tid_date_time, tid_list, layout="summary", sort_mode=sort_mode)
	if defenses_detailed:
		build_category_summary_report(top_stats, defense_stats, enable_hide_columns, "Defenses", tid_date_time, tid_list, layout="detailed", sort_mode=sort_mode)

	support_stats = config_output.support_table
	build_category_summary_report(top_stats, support_stats, enable_hide_columns, "Support", tid_date_time, tid_list, layout="summary", sort_mode=sort_mode)
	if support_detailed:
		build_category_summary_report(top_stats, support_stats, enable_hide_columns, "Support", tid_date_time, tid_list, layout="detailed", sort_mode=sort_mode)

	offensive_stats = config_output.offensive_table
	build_category_summary_report(top_stats, offensive_stats, enable_hide_columns, "Offensive", tid_date_time, tid_list, layout="summary", sort_mode=sort_mode)
	if offensive_detailed:
		build_category_summary_report(top_stats, offensive_stats, enable_hide_columns, "Offensive", tid_date_time, tid_list, layout="detailed", sort_mode=sort_mode)

	boons = config_output.boons
	build_uptime_summary(top_stats, boons, buff_data, "Uptimes", tid_date_time)
	if boons_detailed:
		build_boon_report(top_stats, boons, buff_data, tid_date_time, tid_list)

	boon_categories = {"selfBuffs", "groupBuffs", "squadBuffs"}
	for boon_category in boon_categories:
		#build_boon_summary(top_stats, boons, boon_category, buff_data, tid_date_time)
		build_boon_report(top_stats, boons, buff_data, tid_date_time, tid_list, layout="summary", category=boon_category)

	#get incoming condition uptimes on Squad Players
	conditions = config_output.buffs_conditions
	condition_list = {}
	for condition in conditions:
		if condition in top_stats["overall"]["buffUptimes"]:
			if top_stats["overall"]["buffUptimes"][condition]["uptime_ms"] > 0:
				condition_list[condition] = conditions[condition]
	build_uptime_summary(top_stats, condition_list, buff_data, "Conditions-In", tid_date_time)

	#get outgoing debuff uptimes on Enemy Players
	debuffs = config_output.buffs_debuff
	debuff_list = {}
	for debuff in debuffs:
		if debuff in top_stats["overall"]["targetBuffs"]:
			if top_stats["overall"]["targetBuffs"][debuff]["uptime_ms"] > 0:
				debuff_list[debuff] = debuffs[debuff]
	build_debuff_uptime_summary(top_stats, debuff_list, buff_data, "Debuffs-Out", tid_date_time)

	#get outgoing condition uptimes on Enemy Players
	conditions = config_output.buffs_conditions
	condition_list = {}
	for condition in conditions:
		if condition in top_stats["overall"]["targetBuffs"]:
			if top_stats["overall"]["targetBuffs"][condition]["uptime_ms"] > 0:
				condition_list[condition] = conditions[condition]
	build_debuff_uptime_summary(top_stats, condition_list, buff_data, "Conditions-Out", tid_date_time)

	#get support buffs found and output table
	support_buffs = config_output.buffs_support
	support_buff_list = {}
	for buff in support_buffs:
		if buff in top_stats["overall"]["buffUptimes"]:
			if top_stats["overall"]["buffUptimes"][buff]["uptime_ms"] > 0:
				support_buff_list[buff] = support_buffs[buff]
	build_uptime_summary(top_stats, support_buff_list, buff_data, "Support Uptimes", tid_date_time)
	boon_categories = {"selfBuffs", "groupBuffs", "squadBuffs"}
	for boon_category in boon_categories:
		build_boon_summary(top_stats, support_buff_list, boon_category, buff_data, tid_date_time, boon_type="Support")


	#get defensive buffs found and output table
	defensive_buffs = config_output.buffs_defensive
	defensive_buff_list = {}
	for buff in defensive_buffs:
		if buff in top_stats["overall"]["buffUptimes"]:
			if top_stats["overall"]["buffUptimes"][buff]["uptime_ms"] > 0:
				defensive_buff_list[buff] = defensive_buffs[buff]
	build_uptime_summary(top_stats, defensive_buff_list, buff_data, "Defensive Uptimes", tid_date_time)
	boon_categories = {"selfBuffs", "groupBuffs", "squadBuffs"}
	for boon_category in boon_categories:
		build_boon_summary(top_stats, defensive_buff_list, boon_category, buff_data, tid_date_time, boon_type="Defensive")

	#get offensive buffs found and output table
	offensive_buffs = config_output.buffs_offensive
	offensive_buff_list = {}
	for buff in offensive_buffs:
		if buff in top_stats["overall"]["buffUptimes"]:
			if top_stats["overall"]["buffUptimes"][buff]["uptime_ms"] > 0:
				offensive_buff_list[buff] = offensive_buffs[buff]
	build_uptime_summary(top_stats, offensive_buff_list, buff_data, "Offensive Uptimes", tid_date_time)
	boon_categories = {"selfBuffs", "groupBuffs", "squadBuffs"}
	for boon_category in boon_categories:
		build_boon_summary(top_stats, offensive_buff_list, boon_category, buff_data, tid_date_time, boon_type="Offensive")


	#get offensive debuffs found and output table
	debuffs_buffs = config_output.buffs_debuff
	debuff_list = {}
	for buff in debuffs_buffs:
		if buff in top_stats["overall"]["buffUptimes"]:
			if top_stats["overall"]["buffUptimes"][buff]["uptime_ms"] > 0:
				debuff_list[buff] = debuffs_buffs[buff]
	build_uptime_summary(top_stats, debuff_list, buff_data, "Debuffs-In", tid_date_time)

	#get squad comp and output table
	build_squad_composition(top_stats, tid_date_time, tid_list)


	#get heal stats found and output table
	build_healing_summary(top_stats, "Heal Stats", tid_date_time)

	#get personal buffs found and output table
	build_personal_buff_summary(top_stats, buff_data, personal_buff_data, "Personal Buffs", tid_date_time)

	#get profession damage modifiers found and output table
	build_personal_damage_modifier_summary(top_stats, personal_damage_mod_data, damage_mod_data, "Damage Modifiers", tid_date_time)

	#get skill casts by profession and role and output table
	build_skill_cast_summary(top_stats["skill_casts_by_role"], skill_data, "Skill Usage", skill_casts_by_role_limit, tid_date_time)

	build_skill_usage_stats_tid(top_stats["skill_casts_by_role"], "Skill Usage", tid_date_time)

	#get overview stats found and output table
	#overview_stats = config_output.overview_stats
	build_fight_summary(top_stats, fight_data_charts, "Overview", tid_date_time)

	#get combat resurrection stats found and output table
	build_combat_resurrection_stats_tid(top_stats, skill_data, buff_data, IOL_revive, killing_blow_rallies, "Combat Resurrect", tid_date_time)

	#get FB Pages and output table
	build_fb_pages_tid(fb_pages, "FB Pages", tid_date_time)
 
	build_high_scores_tid(high_scores, skill_data, buff_data, "High Scores", tid_date_time)

	build_mechanics_tid(mechanics, top_stats['player'], "Mechanics", tid_date_time)

	build_minions_tid(minions, top_stats['player'], skill_data, "Minions", tid_date_time)

	build_top_damage_by_skill(top_stats['overall']['totalDamageTaken'], top_stats['overall']['targetDamageDist'], skill_data, buff_data, "Top Damage By Skill", tid_date_time)


	#build_damage_outgoing_by_player_skill_tids
	build_damage_outgoing_by_skill_tid(tid_date_time, tid_list)
	build_damage_outgoing_by_player_skill_tids(top_stats, skill_data, buff_data, tid_date_time, tid_list)

	#build_gear_buff_summary
	gear_buff_ids, gear_skill_ids = extract_gear_buffs_and_skills(buff_data, skill_data)
	build_gear_buff_summary(top_stats, gear_buff_ids, buff_data, tid_date_time)
	build_gear_skill_summary(top_stats, gear_skill_ids, skill_data, tid_date_time)

	build_damage_summary_table(top_stats, "Damage", tid_date_time)

	build_on_tag_review(death_on_tag, tid_date_time)

	build_mesmer_clone_usage(mesmer_clone_usage, tid_date_time, tid_list)

	profession_color = config_output.profession_color
	build_support_bubble_chart(top_stats, buff_data, weights, tid_date_time, tid_list, profession_color)
	build_DPS_bubble_chart(top_stats, tid_date_time, tid_list, profession_color)
	build_utility_bubble_chart(top_stats, buff_data, weights, tid_date_time, tid_list, profession_color)
	boons = config_output.boons
	build_boon_generation_bar_chart(top_stats, boons, weights, tid_date_time, tid_list)
	conditions = config_output.buffs_conditions
	build_condition_generation_bar_chart(top_stats, conditions, weights, tid_date_time, tid_list)

	build_dps_stats_tids(DPSStats, tid_date_time, tid_list)
	build_dps_stats_menu(tid_date_time)

	#attendance
	build_attendance_table(top_stats,tid_date_time, tid_list)

	build_defense_damage_mitigation(player_damage_mitigation, player_minion_damage_mitigation, top_stats, tid_date_time, tid_list)
	
	build_stacking_buffs(stacking_uptime_Table, top_stats, tid_date_time, tid_list, blacklist)

	build_damage_with_buffs(stacking_uptime_Table, DPSStats, top_stats, tid_date_time, tid_list)

	build_pull_stats_tid(tid_date_time, top_stats, skill_data, tid_list)
	
	#Fight Data line charts
	if fight_data_charts:
		build_fight_line_chart(fight_data, tid_date_time, tid_list)

	#commander Tag summary
	if build_commander_summary_menu:
		build_commander_summary(commander_summary_data, skill_data, buff_data, tid_date_time, tid_list)
		build_commander_summary_menu(commander_summary_data, tid_date_time, tid_list)

	if write_all_data_to_json:
		output_top_stats_json(top_stats, buff_data, skill_data, damage_mod_data, high_scores, personal_damage_mod_data, personal_buff_data, fb_pages, mechanics, minions, mesmer_clone_usage, death_on_tag, DPSStats, commander_summary_data, enemy_avg_damage_per_skill, player_damage_mitigation, player_minion_damage_mitigation, stacking_uptime_Table, IOL_revive, fight_data, args.json_output_filename)

	if write_excel:
		write_data_to_excel(top_stats, top_stats['overall']['last_fight'], excel_output_full_path)
		
	if db_update:
		write_data_to_db(top_stats, top_stats['overall']['last_fight'], db_output_full_path)

		update_glicko_ratings(db_output_full_path)

		leaderboard_stats = config_output.leaderboard_stats
		build_leaderboard_tids(tid_date_time, leaderboard_stats , tid_list, db_output_full_path)
		build_leaderboard_menu_tid(tid_date_time, leaderboard_stats, tid_list)

		write_high_scores_to_db(high_scores, top_stats['fight'], skill_data, db_output_full_path)
		build_high_scores_leaderboard_tids(tid_date_time, db_output_full_path)

	write_tid_list_to_json(tid_list, args.output_filename)

	if team_code_missing:
		print("Missing team codes: " + str(team_code_missing))
		print("Please review and add to config.py file")
	else:
		print("No new team codes found")

	if webhook_url != "false" and support_profs:
		discord_colors = config_output.profession_discord_color
		boon_support_data = build_boon_support_data(top_stats, support_profs, config_output.boons)
		profession_icons = config_output.profession_icons

		for profession, support_data in boon_support_data.items():
			print("Sending boon support data for " + profession)
			send_profession_boon_support_embed(webhook_url, profession, profession_icons[profession], discord_colors[profession], tid_date_time, support_data)
	else:
		if not support_profs: 
			print("No support professions found")
		if not webhook_url:
			print("No webhook URL found")