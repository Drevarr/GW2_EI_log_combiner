import json

def build_and_sort_stat(stat_dict, sort_key="totalStat", reverse=False):
    built = {
        name: {
            "numFights": len(data),
            "totalStat": sum(data),
            "fightData": data,
        }
        for name, data in stat_dict.items()
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
    chart_per_fight,
    chart_per_second,
):
    """
    Returns an ECharts boxplot.
    """

    if stat in chart_per_second:
        title_text = f"{stat_name} per Second for all Fights Present"
    else:
        title_text = f"{stat_name} per Fight for all Fights Present"

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

    return f"""
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
}};
"""