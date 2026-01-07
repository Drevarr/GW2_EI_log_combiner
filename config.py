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