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


# Elite Insights json stat categories
json_stats = [
    "defenses",
    "support",
    "statsAll",
    "statsTargets",
    "targetDamageDist",
    "dpsTargets",
    "totalDamageTaken",
    "buffUptimes",
    "buffUptimesActive",
    "squadBuffs",
    "groupBuffs",
    "selfBuffs",
    "squadBuffsActive",
    "groupBuffsActive",
    "selfBuffsActive",
    "rotation",
    "extHealingStats",
    "extBarrierStats",
    "targetBuffs",
    "damageModifiers",
]

# Top stats dictionary to store combined log data
top_stats = {
    "overall": {"last_fight": "", "group_data": {}},
    "fight": {},
    "player": {},
    "stats_per_fight": {},
    "parties_by_fight": {},
    "enemies_by_fight": {},
    "skill_casts_by_role": {},
    "players_running_healing_addon": [],
}

# Team colors - team_id:color
team_colors = {
    0: "Unk",
    705: "Red",
    706: "Red",
    707: "Red",
    882: "Red",
    885: "Red",
    886: "Red",
    2520: "Red",
    2543: "Red",    
    2739: "Green",
    2741: "Green",
    2752: "Green",
    2763: "Green",
    2767: "Green",
    432: "Blue",
    433: "Blue",
    1277: "Blue",
    1282: "Blue",
}


# High scores stats
high_scores = [
    "dodgeCount",
    "evadedCount",
    "blockedCount",
    "invulnedCount",
    "boonStrips",
    "condiCleanse",
    "receivedCrowdControl",
]

#mesmer F_skills
old_mesmer_shatter_skills = [
"Split Second",
"Rewinder",
"Time Sink",
"Distortion",
"Continuum Split",
"Mind Wrack",
"Cry of Frustration",
"Diversion",
"Distortion",
"Geistiges Wrack",
"Schrei der Frustration",
"Ablenkung",
"Verzerrung",
"Sekundenbruchteil",
"R\u00FCckspuler",
"Zeitfresser",
"Kontinuum-Spaltung"
]

mesmer_shatter_skills = [
    "s56930",#: "Split Second"
    "s56925",#: "Split Second"
    "s56928",#: "Rewinder"
    "s56873",#: "Time Sink"
    "s10192",#: "Distortion"
    "s10243",#: "Distortion"
    "s29830",#: "Continuum Split"
    "s49068",#: "Mind Wrack"
    "s10191",#: "Mind Wrack"
    "s10190",#: "Cry of Frustration"
    "s10287",#: "Diversion"
]

pull_skills = [
    "s9226",    #Pull
    "s9193",    #Wrathful Grasp
    "s45402",   #Blazing Edge
    "s28409",   #Temporal Rift
    "s71880",   #Otherworldly Attraction
    "s72954",   #Abyssal Blot
    "s72026",   #Snap Pull
    "s14448",   #Barbed Pull
    "s50380",   #Capture Line
    "s12638",   #Path of Scars
    "s13070",   #Tow Line
    "s73148",   #Undertow
    "s30008",   #Cyclone
    "s10363",   #Into the Void
    "s10255",   #Vortex
    "s10695",   #Deadly Catch
    "s29740",   #Grasping Darkness
    "s42449",   #"Chapter 3: Heated Rebuke"
    "s5996",    #Magnet
    "s5747",    #Magnetic Shield
    "s76530",   #Magnetic Bomb
    "s27917",   #Call to Anguish
    "s31100",   #Call to Anguish
    "s29558",   #Glyph of the Tides
    "s13020",   #Scorpion Wire
    "s10620",   #Spectral Grasp
    "s30273",   #"Dragon's Maw"
    "s76993",   #Flux State
    "s63275",   #Shadowfall
    "s5602",    #Whirlpool
    "s30359",   #Gravity Well
    "s33134",   #"Hunter's Verdict"
    "s31048",   #Wild Whirl
    "s41843",   #Prismatic Singularity
    "s43375",   #Prelude Lash
    "s49112",   #Throw Magnetic Bomb
    "s59324",   #Throw Unstable Reagent
    "s41156",   #Fang Grapple
    "s70491",   #"Relic of the Wizard's Tower"
    "s43532",   #Magebane Tether
    ]

arrow_cart_skill_ids = [18850, 18853, 18855, 18860, 18862, 18865, 18867, 18869, 18872]
trebuchet_skill_ids = [21037, 21038]
balista_skill_ids = [14622, 14654, 41540]
catapult_skill_ids = [20242, 20254, 20272,20285]
cannon_skill_ids = [14626, 14658, 14659, 18535, 18531, 18533, 18543, 18580, 19626]
burning_oil_skill_ids = [14605, 14648, 18887]
dragon_banner_skill_ids = [32980, 31968, 33232]
ebg_lord = [3837]
golem_skills = [14627, 14639, 14709, 14710, 14708, 14713, 63185, 1656, 14642]
downed_skills = [9149, 9096, 9095, 28180, 27063, 27792, 14390, 14515, 14391, 5820,
				5962, 5963, 12486, 12485, 12515, 13003, 13138, 13140, 13033
               ]
other_skills = [14601, 14600, 23284, 23285, -2, 58083, 20285, 9284, 23275, 54877,
               54941, 54953, 21615, 23267, 18792, 18793, 25533, 27927, 30765, 34797
              ]

siege_skill_ids = [
	*arrow_cart_skill_ids,
	*trebuchet_skill_ids,
    *balista_skill_ids,
	*catapult_skill_ids,
	*cannon_skill_ids,
	*burning_oil_skill_ids,
	*dragon_banner_skill_ids,
    *golem_skills, 
    *ebg_lord,   
]

downed_healing_skills = [
    's1066', #Ress
    #Weapon skills
    's5681', #Geyser — Staff, with Arcane Resurrection
    #Healing skills
    's10670', #Well of Blood — Well, with Ritual of Life
    's10527', #Well of Blood — Well, with Ritual of Life
    #Utility skills
    's9246', #Merciful Intervention — Meditation
    's34309', #"Search and Rescue!" — Command
    's10302', #Feedback — Glamour, with Medic's Feedback
    's13117', #Shadow Refuge — Deception
    's5570', #Signet of Water — Signet
    #Elite skills
    's55046',
    's55024', #Glyph of the Stars — Glyph
    #Profession mechanics
    's5867',
    's6091', #Toss Elixir R — Elixir, Tool belt
    #Function Gyro — Tool belt
    's49123', #Unstable Artifact — Stolen skill
    's1175', #Bandage
    's29547', #Bandage Blast
    #Skills that instantly revive
    's9163', 
    's9243', #Signet of Mercy — Signet — 1 ally
    #Glyph of Renewal — Glyph
    's24407', #Renewal of Fire — 1 ally, and self upon next down
    's24410', #Renewal of Water — 1 ally, with full health
    's24409', #Renewal of Air — 1 ally, and teleports to you
    's24411', #Renewal of Earth — 3 allies
    's10611', #Signet of Undeath — Signet — 1 ally
    #Elite skills
    's144119', #Battle Standard — Banner — 5 allies (3 in WvW)
    #Spirit of Nature — Spirit
    's12601', #Nature's Renewal — 5 allies (2 in WvW)
    's69336', #Nature's Vengeance    
]