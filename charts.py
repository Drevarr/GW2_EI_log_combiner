import json
from output_functions import append_tid_for_output, create_new_tid_from_template


def build_fight_timeline_chart(fight_data: dict, tid_date_time: str, tid_list: list) -> str:
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
		line_chart_config = '```py\nPlayer_Line = players with DPS >= 1000 for the fight\n```\n\n\n\n<$echarts $text="""\n'
		line_chart_config += f"""option = {{
		title: {{
			text: '{chart_title}',
			left: 'center'
		}},
		grid: [
			{{
				left: '5%',
				right: '15%',
				top: 50,
				height: '48%'
			}},
			{{
				left: '5%',
				right: '15%',
				top: '68%',
				height: '22%'
			}}
		],
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
		
			axisPointer: {{
				type: 'line'
			}},
		
			showContent: true,
		
			formatter: function(params) {{
		
				if (!params || !params.length) {{
					return '';
				}}
				let firstValue = params[0].value;
				let second = Array.isArray(firstValue)
					? firstValue[0]
					: params[0].axisValue;
				let html =
					'<div style="font-size:13px;">' +
					'<b>' + second + 's</b>';
				let damageFound = false;
				let events = [];
				params.forEach(function(param) {{
					if (param.data &&
						param.data.players &&
						param.data.players.length) {{
		
						events.push({{
							name: param.seriesName,
							players: param.data.players,
							color: param.color
						}});
		
						return;
					}}
					if (!damageFound) {{
						html +=
							'<div style="margin-top:6px;">' +
							'<b>Damage</b></div>';
		
						damageFound = true;
					}}
					let value = param.value;
					if (Array.isArray(value)) {{
						value = value[value.length - 1];
					}}
					html +=
						'<div>' +
						'<span style="' +
						'display:inline-block;' +
						'width:8px;' +
						'height:8px;' +
						'border-radius:50%;' +
						'background:' + param.color + ';' +
						'margin-right:6px;"></span>' +
						param.seriesName + ': ' +
						Number(value).toLocaleString() +
						'</div>';
				}});
				if (events.length) {{
					html +=
						'<div style="margin-top:6px;">' +
						'<b>Events</b></div>';
					events.forEach(function(event) {{
						html +=
							'<div style="margin-top:4px;">' +
							'<span style="' +
							'display:inline-block;' +
							'width:8px;' +
							'height:8px;' +
							'border-radius:50%;' +
							'background:' + event.color + ';' +
							'margin-right:6px;"></span>' +
							'<b>' + event.name + '</b><br>' +
							event.players.join('<br>') +
							'</div>';
					}});
				}}
				html += '</div>';
				return html;
			}}
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
		xAxis: [
			{{
				type: 'category',
				gridIndex: 0,
				nameLocation: 'middle',
				nameGap: 40,
				name: 'Fight Time',
				axisLabel: {{
					formatter: '{{value}}s',
					align: 'center'
				}},
				data: {time_series}
			}},

			{{
				type: 'category',
				gridIndex: 1,
				nameLocation: 'middle',
				nameGap: 25,
				name: 'Fight Time',
				axisLabel: {{
					formatter: '{{value}}s',
					align: 'center'
				}},
				data: {time_series}
			}}
		],
		yAxis: [
			{{
				type: 'value',
				gridIndex: 0,
				nameLocation: 'middle',
				nameGap: 55,
				name: 'Damage'
			}},

			{{
				type: 'category',
				gridIndex: 1,
				nameLocation: 'middle',
				nameGap: 35,
				name: 'Events',
				data: [
					'Enemy Death',
					'Enemy Down',
					'Squad Death',
					'Squad Down',
					'SquadGetup'
				],
				axisLabel: {{
					show: false,
					interval: 0
				}}
			}}
		],
		series: [
			{{
			name: 'Outgoing Damage',
			data: {outgoing_damage_data},
			type: 'line',
			xAxisIndex: 0,
			yAxisIndex: 0, 			
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
			}},
		"""
		for player in fight_data[fight_num]["players"].keys():
			active_dps = fight_data[fight_num]["players"][player].get('active_dps',0)
			if  active_dps >= 1000:

				player_name = player.split("-")[1][:3]+" - "+player.split("-")[2]
				player_damage_data = list(fight_data[fight_num]["players"][player]['damage1S'].values())

				player_line_chart_config = f"""
				
			{{
			name: '{player_name}',
			data: {player_damage_data},
			type: 'line',
			xAxisIndex: 0,
			yAxisIndex: 0, 			
			smooth: true,
			emphasis: {{ focus: 'series' }}
			}},"""
				line_chart_config += player_line_chart_config
		scatter_rows = ['Enemy Deaths', 'Enemy Downs', 'Squad Deaths', 'Squad Downs', 'SquadGetups']
		for event, data in {'squad dead':["Squad Deaths", 'roundRect'], 'squad down': ["Squad Downs", 'pin'], 'enemy dead':["Enemy Deaths", 'triangle'], 'enemy down': ["Enemy Downs", 'diamond']}.items():
			squad_enemy, event_type = event.split()
			event_name = data[0]
			event_shape = data[1]
			event_data = fight_data[fight_num][event_type].get(squad_enemy, {})
			format_event_data = []
			scatter_row = scatter_rows.index(event_name)
			for second, players in event_data.items():
				
				format_event_data.append({
					"value": [int(second), scatter_row],
					"players": players
				})
			
			event_scatter_chart_config = f"""
			
			{{
			name: '{event_name}',
			type: 'scatter',
			xAxisIndex: 1,
			yAxisIndex: 1,
			data: {json.dumps(format_event_data)},
			symbol: '{event_shape}',
			symbolSize: function(value, params) {{
				const count = params.data.players.length;
				return Math.min(28, 8 + (count * 3));
			}},
			emphasis: {{
				scale: true
			}}
		}},"""
			line_chart_config += event_scatter_chart_config
		line_chart_config += '\n    ]\n    };\n\n"""$height="500px" $width="100%" $theme="dark"/>'

		line_chart_title = f"{tid_date_time}_Fight_{zf_fight_num}_Damage_Output_Review"
		line_chart_caption = f"Fight-{zf_fight_num}: Damage Output Review"
		line_chart_tags = "Chart"

		append_tid_for_output(
			create_new_tid_from_template(line_chart_title, line_chart_caption, line_chart_config, line_chart_tags),
			tid_list	
		)

def build_boon_boxplot_echart(stats_per_fight, boon_id, boon_name, profession_color):
	names = {
		"selfBuffs": [],
		"groupBuffs":[],
		"squadBuffs":[]
		}
	professions = {
		"selfBuffs": [],
		"groupBuffs":[],
		"squadBuffs":[]
		}
	raw_stats = {
		"selfBuffs": [],
		"groupBuffs":[],
		"squadBuffs":[]
		}
	
	for cat in raw_stats:
		for player, player_data in stats_per_fight[cat][boon_id].items():
			name, profession, account = player.split("|")
			
			names[cat].append(name)
			professions[cat].append(profession)
			raw_stats[cat].append(player_data)

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

    title_text = f"{stat_name.title()}"

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
    {{ text: '{title_text}', subtext: '{stat}', left: 'center' }},
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
}};"""$height="600px" $width="100%" $theme="dark"/>
'''

def build_boon_bar_echart(sorted_chart, boon_name):
	json_chart = json.dumps(sorted_chart)

	# Chart: 3 bars per player with legend toggle
	chart_block = f"""
<$echarts $text=```
option = {{
title: {{ text: '{boon_name} Uptime Generation', subtext: 'selectable legend for generation types' }},
legend: {{ orient:'horizontal', top:'10%', selected:{{'Total Gen':false,'Squad Gen':true,'Group Gen':false,'Self Gen':false}} }},
grid:{{top:'15%', containLabel:true}},
tooltip:{{top:'center'}},
dataset:{{
	dimensions:["Party","Name","Prof","Total Fight Time","Self Gen","Group Gen","Squad Gen","Total Gen"],
	source:{json_chart}}},
xAxis:{{}}, 
yAxis:{{type:'category',inverse:true}},
dataZoom:[
	{{type:'slider',yAxisIndex:0,filterMode:'none', start:0, end:60}},
	{{type:'inside',yAxisIndex:0,filterMode:'none'}}],
series:[
	{{type:'bar',name:'Total Gen',encode:{{x:'Total Gen',y:'Name'}}}},
	{{type:'bar',name:'Squad Gen',encode:{{x:'Squad Gen',y:'Name'}}}},
	{{type:'bar',name:'Group Gen',encode:{{x:'Group Gen',y:'Name'}}}},
	{{type:'bar',name:'Self Gen',encode:{{x:'Self Gen',y:'Name'}}}}]
}};
```$height="900px" $width="100%" $theme="dark"/>
"""

	return chart_block
	
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

	data_header = ["Name", "Profession", "Strips/Sec", "Condition Score", "Crowd Control", "color"]
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

		CC_score = player_data['statsTargets'].get('appliedCrowdControl', 0)

		player_entry.append(CC_score)

		if CC_score > chart_max:
			chart_max = CC_score
		if CC_score < chart_min:
			chart_min = CC_score
		player_color = profession_colors[profession]
		player_entry.append(player_color)

		chart_data.append(player_entry)

	text = "__''Utility Bubble Chart''__\n"
	text += "\n,,Bubble size based on Crowd Control score,,\n\n"
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

	The bubble size is based on the damage that was against downed targets/Second.
	The x-axis is the damage per second that was down contribution.
	The y-axis is the damage per second.

	The function builds a table with the following columns:
		- Player (player name)
		- Profession (profession icon and abbreviated name)
		- Damage/Sec (total damage divided by fight time)
		- Down Contr/Sec (Down Contribution Damage divided by fight time)
		- Dmg to Down/Sec % (damage against downed targets divided by fight time)

	The function then pushes the table to the tid_list for output.
	"""
	#TIME_THRESHOLD_MS = 3000
	#raid_time_total = sum(data.get('fight_durationMS', 0) for data in top_stats['fight'].values())

	tid_title = f"{tid_date_time}-DPS-Bubble-Chart"
	tid_caption = "DPS Bubble Chart"
	tid_tags = tid_date_time

	chart_data = []
	chart_min = 1000
	chart_max = 0
	chart_yAxis = "Damage/Sec"
	chart_xAxis = "Down Contr/Sec"
	chart_yData = "Damage/Sec"
	chart_xData = "Down Contr/Sec"

	data_header = ["Name", "Profession", "Damage/Sec", "Down Contr/Sec", "Dmg to Down/Sec", "color"]
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
			DCps = round((player_data["statsTargets"].get("downContribution", 0)/fight_time),2)
			#DCps = round(DCps*100,2)
			DDps = round((player_data["statsTargets"].get("againstDownedDamage", 0)/fight_time),2)
			#DDps = round(DDps*100,2)
		player_entry = [name, profession, Dps, DCps, DDps]
		if DDps > chart_max:
			chart_max = DDps
		if DDps < chart_min:
			chart_min = DDps
		player_color = profession_colors[profession]
		player_entry.append(player_color)

		chart_data.append(player_entry)

	text = "__''DPS Bubble Chart''__\n"
	text += "\n,,Bubble size based on against downed damage/Second"
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