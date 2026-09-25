import config
import html
from output_functions import append_tid_for_output, create_new_tid_from_template

siege_skill_ids = set(int(sid) for sid in config.siege_skill_ids)


OTHER_PROFS_KEY = "Other Professions"

media_card_css = """.page-header{
	display:flex;
	align-items:flex-start;
	justify-content:space-between;
	gap:3px
}
	
.page-title{
	font-size:20px;
	font-weight:800;
	color:#aeb6c2
}
	
.page-sub{
	font-size:12px;
	color:#94a3b8;
	margin-top:2px
}

/* TW5 tab container */
.tc-tab-set {
    margin: 8px 0 11px;
    padding: 3px;
    background: #24282e;
    border: 1px solid #454b54;
    border-radius: 10px;
}

/* Tab buttons row */
.tc-tab-buttons {
    display: flex;
    flex-wrap: wrap;
    column-gap: 4px;
    row-gap: 2px;
}

/* Individual tab button */
.tc-tab-buttons button {
    padding: 2px 6px;
    border: 0;
    border-radius: 7px;
    background: transparent;
    color: #aeb6c2;
    font-size: 11px;
    font-weight: 700;
    line-height: 1.2;
    cursor: pointer;
}

/* Hover */
.tc-tab-buttons button:hover {
    background: #353a42;
    outline: 2px solid #1a73e8;
    color: #f1f5f9;
}

/* Selected/active tab */
.tc-tab-buttons button.tc-tab-selected {
    background: #353a42;
    color: #f1f5f9;
}

/* Divider between buttons and content */
.tc-tab-divider {
    height: 1px;
    margin: 3px 0 2px;
    background: #454b54;
}

/* Tab content */
.tc-tab-content {
    margin: 4px 0 3px;
    padding: 3px 2px 2px;
}

.fight-nav{
    display:flex;
    flex-wrap:wrap;
    gap:6px;
    margin:16px 0 22px;
    padding:6px;
    background:#24282e;
    border:1px solid #454b54;
    border-radius:10px;
}

.fight-nav-btn{
    padding:7px 12px;
    border:0;
    border-radius:7px;
    background:transparent;
    color:#aeb6c2;
    font-size:11px;
    font-weight:700;
    cursor:pointer;
}

.fight-nav-btn:hover{
    background:#353a42;
    outline: 2px solid #1a73e8;
    color:#f1f5f9;
}

.fight-nav-btn.active{
    background:#353a42;
    color:#f1f5f9;
}

.metric-grid{
    display:grid;
    grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));
    gap:14px;
    margin-bottom:24px;
}

.metric-card{
    background:#2b2f35;
    border:1.5px solid #454b54;
    border-radius:12px;
    padding:14px;
    transition:box-shadow .2s,transform .2s
}

.metric-card:hover{
    box-shadow:0 6px 20px rgba(0,0,0,.07);
    transform:translateY(-2px)
}

.metric-top{
    display:flex;
    align-items:center;
    justify-content:space-between;
    margin-bottom:12px
}

.metric-name{
    display:flex;
    align-items:center;
    gap:8px
}

.metric-icon{
    width:34px;
    height:34px;
    border-radius:10px;
    background:var(--ic);
    color:var(--stroke);
    display:flex;
    align-items:center;
    justify-content:center
}

.metric-label{
    font-size:12px;
    color:#aeb6c2;
    font-weight:600
}

.trend{
    font-size:11px;
    font-weight:700;
    padding:3px 7px;
    border-radius:6px
}

.trend.positive{
    color:#059669;
    background:#d1fae5
}

.trend.negative{
    color:#dc2626;
    background:#fee2e2
}

.metric-val{
    font-size:22px;
    font-weight:700;
    color:#f1f5f9;
    line-height:1;
    margin-bottom:5px
}

.metric-val-small-r{
    font-size:50%;
    font-weight:500;
    color: #d6483e;
}

.metric-val-small-b{
    font-size:50%;
    font-weight:500;
    color: #009bd9;
}

.metric-val-small-g{
    font-size:50%;
    font-weight:500;
    color: #47ab4f;
}

.metric-sub{
    font-size:11px;
    color:#aeb6c2;
    opacity:.7
}

.breakdown-row{
    display:grid;
    grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));
    gap:14px
}

.breakdown-card{
    background:#2b2f35;
    border:1.5px solid #454b54;
    border-radius:12px;
    padding:14px
}

.breakdown-title{
    font-size:13px;
    font-weight:700;
    color:#aeb6c2;
    margin-bottom:12px
}

.goals{
    display:flex;
    flex-direction:column;
    gap:12px
}

.goal-item{
    display:flex;
    flex-direction:column;
    gap:5px
}

.goal-head{
    display:flex;
    justify-content:space-between;
    font-size:12px;
    color:#aeb6c2;
    font-weight:600
}

.goal-pct{
    font-weight:700;
    color:#aeb6c2
}

.goal-track{
    background:#e2e8f0;
    border-radius:6px;
    height:7px;
    overflow:hidden
}

.goal-fill{
    height:100%;
    border-radius:6px;
    transition:width .7s cubic-bezier(.4,0,.2,1)
}

.channel-list{
    display:flex;
    flex-direction:column;
    gap:3px
}

.channel-item{
    display:grid;
    grid-template-columns:minmax(150px, 200px) auto auto;
    align-items:center;
    gap:8px
}

.ch-name{
    font-size:12px;
    color:#aeb6c2;
    font-weight:600
}

.ch-bar-wrap{
    background:#e2e8f0;
    border-radius:4px;
    height:6px;
    overflow:hidden
}

.ch-bar{
    height:100%;
    border-radius:4px;
    transition:width .6s cubic-bezier(.4,0,.2,1)
}

.ch-pct{
    font-size:11px;
    font-weight:700;
    color:#64748b;
    text-align:right
}

/* FIGHT REVIEW - COMPOSITION LAYOUT */
.composition-section{
    margin-top:24px;
}
.composition-columns{
    display:grid;
    grid-template-columns:repeat(2, minmax(0, 1fr));
    gap:14px;
    align-items:stretch;
}

/* Composition cards */
.composition-card{
    background:#2b2f35;
    border:1.5px solid #454b54;
    border-radius:12px;
    padding:14px;
    min-width:0;
}

.composition-title{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:10px;

    margin:0 0 12px;

    font-size:13px;
    font-weight:700;
    color:#f1f5f9;
}

.composition-subtitle{
    font-size:11px;
    font-weight:600;
    color:#64748b;
}

/* Squad composition */
.squad-composition{
    display:grid;
    grid-template-columns:repeat(auto-fit, minmax(150px, 1fr));
    gap:6px 10px;
}
.squad-group{
    min-width:0;
    padding:7px 8px;
    background:#24282e;
    border:1px solid #3a3f47;
    border-radius:7px;
}

.squad-group-title{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:8px;
    margin-bottom:5px;
    font-size:11px;
    font-weight:700;
    color:#aeb6c2;
}

.squad-group-count{
    color:#f1f5f9;
    font-weight:800;
}

.squad-players{
    display:flex;
    flex-direction:column;
    gap:2px;
}

.squad-player{
    display:flex;
    align-items:center;
    gap:5px;
    min-width:0;
    font-size:10px;
    color:#94a3b8;
}

/* Enemy composition */
.enemy-compositions{
    display:flex;
    flex-direction:column;
    gap:10px;
}

.enemy-team{
    background:#24282e;
    border:1px solid #3a3f47;
    border-radius:8px;
    padding:10px;
}

.enemy-team-title{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:10px;

    margin-bottom:8px;

    font-size:11px;
    font-weight:700;
    color:#f1f5f9;
}

.enemy-team-count{
    color:#94a3b8;
    font-size:10px;
    font-weight:600;
}

/* CSS controls the number of profession columns */
.enemy-professions{
    display:grid;
    grid-template-columns:repeat(auto-fit, minmax(120px, 1fr));
    gap:5px 10px;
}

.enemy-profession{
    display:flex;
    align-items:center;
    gap:5px;

    min-width:0;
    padding:4px 2px;

    font-size:10px;
    color:#aeb6c2;
}

.enemy-profession-icon{
    flex:0 0 auto;
    display:inline-flex;
    align-items:center;
}

.enemy-profession-name{
    min-width:0;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
}

.enemy-profession-count{
    margin-left:auto;
    color:#f1f5f9;
    font-weight:700;
    white-space:nowrap;
}

/* Hover states  */
.composition-card{
    transition:box-shadow .2s, transform .2s;
}

.composition-card:hover{
    box-shadow:0 6px 20px rgba(0,0,0,.07);
    transform:translateY(-2px);
}

.squad-group:hover,
.enemy-team:hover{
    background:#30353c;
}

/* TAG SUMMARY */

.tag-summary-list{
    display:grid;
    grid-template-columns:repeat(4, minmax(0, 1fr));
    gap:6px 12px;
}

/* Tag card */

.tag-summary-card {
    background: #2b2f35;
    border: 1.5px solid #454b54;
    border-radius: 12px;
    padding: 5px 7px;
    min-width: 0;
    transition: box-shadow .2s, transform .2s;
}

.tag-summary-card:hover{
    box-shadow:0 6px 20px rgba(0,0,0,.07);
    transform:translateY(-1px);
}

/* Header */

.tag-summary-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2px 5px;
    margin-bottom: 0px;
    min-width: 0;
}

.tag-summary-name{
    display:flex;
    align-items:center;
    gap:3px 6px;
   min-width:0;
    font-size:12px;
    font-weight:800;
    color:#f1f5f9;
}

.tag-summary-name > span{
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
}

.tag-summary-account{
    flex:0 0 auto;
    max-width:45%;
    font-size:9px;
    font-weight:600;
    color:#64748b;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
}

/* Metrics */

.tag-summary-metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1px 2px;
}

.tag-summary-metric:last-child {
    grid-column: span 1;
}

.tag-summary-metric {
    background: #24282e;
    border: 1px solid #3a3f47;
    border-radius: 6px;
    padding: 1px 3px;
    min-width: 0;
}

/* TW5 injects <p> around block elements */
.tag-summary-metrics > p {
    display: contents;
    margin: 0;
    padding: 0;
}

.tag-summary-label{
    margin-bottom:0px;
    font-size:8px;
    font-weight:700;
    color:#64748b;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}

.tag-summary-value {
    font-size: 13px;
    font-weight: 800;
    color: #f1f5f9;
    line-height: 1;
}

/* Totals */

.tag-summary-total{
    grid-column:1 / -1;
}

/* Version notice */

.tag-version-notice{
    margin-bottom:12px;
    padding:3px 5px;
    background:#24282e;
    border:1px solid #454b54;
    border-radius:7px;
    color:#aeb6c2;
    font-size:10px;
}

/* Responsive layout */

@media (max-width:900px){

    .composition-columns{
        grid-template-columns:1fr;
    }

}

@media (max-width:700px){

    .tag-summary-list{
        grid-template-columns:1fr;
    }

}

@media (max-width:600px){

    .enemy-professions{
        grid-template-columns:repeat(2, minmax(0, 1fr));
    }

    .squad-composition{
        grid-template-columns:1fr;
    }

}

@media (max-width:500px){

    .tag-summary-metrics{
        grid-template-columns:repeat(2, minmax(0, 1fr));
    }

}

@media (max-width:400px){

    .enemy-professions{
        grid-template-columns:1fr;
    }
    
}"""


def make_squad_composition_card(composition, squad_count):
    """
    Build the squad composition card.

    composition format:

        {
            group: [
                "Profession|Character Name",
                "Profession|Character Name",
                ...
            ]
        }
    """

    groups = []

    for group, players in composition.items():

        player_items = []

        for player in players:

            profession, name = player.split("|", 1)

            profession_icon = "{{" + profession + "}}"

            player_items.append(
                f"""
                <div class="squad-player">
                    <span>{profession_icon}</span>
                    <span>{name}</span>
                </div>
                """
            )

        groups.append(
            f"""
            <div class="squad-group">

                <div class="squad-group-title">
                    <span>Group {group}</span>
                    <span class="squad-group-count">
                        {len(players)}
                    </span>
                </div>

                <div class="squad-players">
                    {''.join(player_items)}
                </div>

            </div>
            """
        )

    return f"""
    <div class="composition-card">

        <h3 class="composition-title">

            <span>Squad Composition</span>

            <span class="composition-subtitle">
                {squad_count} players
            </span>

        </h3>

        <div class="squad-composition">
            {''.join(groups)}
        </div>

    </div>
    """


def make_enemy_composition_card(team, composition):
    """
    Build an enemy team composition card.

    composition format:

        {
            "Warrior": 4,
            "Guardian": 3,
            "Mesmer": 5,
            ...
        }
    """

    sorted_profs = sorted(
        composition.items(),
        key=lambda item: item[1],
        reverse=True
    )

    total_players = sum(
        count for _, count in sorted_profs
    )

    profession_items = []

    for profession, count in sorted_profs:

        profession_icon = "{{" + profession + "}}"

        profession_items.append(
            f"""
            <div class="enemy-profession"
                 title="{profession}: {count}">

                <span class="enemy-profession-icon">
                    {profession_icon}
                </span>

                <span class="enemy-profession-name">
                    {profession}
                </span>

                <span class="enemy-profession-count">
                    {count}
                </span>

            </div>
            """
        )

    return f"""
    <div class="enemy-team">

        <div class="enemy-team-title">

            <span>
                {team}
            </span>

            <span class="enemy-team-count">
                {total_players} players
            </span>

        </div>

        <div class="enemy-professions">
            {''.join(profession_items)}
        </div>

    </div>
    """


def build_squad_composition_for_fight(
    top_stats: dict,
    fight_num: int
) -> str:
    """
    Build the squad/enemy composition section for a single fight.
    Returns the generated TiddlyWiki/HTML text.
    """
    squad_count = top_stats["fight"][fight_num].get("squad_count", 0)
    squad_composition = top_stats["parties_by_fight"].get(fight_num, {})
    enemy_compositions = top_stats["enemies_by_fight"].get(fight_num, {})

    rows = []
    rows.append('\n<$reveal type="match" state="$:/state/FR" text="Composition">\n')
    rows.append(
        f"""
        <div class="composition-section">

            <h2 class="section-title">
                Fight {fight_num} - Composition
            </h2>

            <div class="composition-columns">
        """
    )

    # Squad
    rows.append(
        make_squad_composition_card(
            squad_composition, squad_count
        )
    )

    # Enemy container
    rows.append(
        """
        <div class="composition-card">

            <h3 class="composition-title">
                Enemy Composition
            </h3>

            <div class="enemy-compositions">
        """
    )

    # Each enemy team gets its own inner container
    for team, composition in enemy_compositions.items():

        rows.append(
            make_enemy_composition_card(
                team,
                composition
            )
        )

    rows.append(
        """
            </div>
        </div>
        """
    )

    rows.append(
        """
            </div>
        </div>
        """
    )
    rows.append(
        """

        </$reveal>

        """
    )

    return "\n".join(rows)


def make_media_card_css(tid_list):
    tid_text = media_card_css
    tid_title = "Metric Card CSS"
    tid_tags = "$:/tags/Stylesheet"
    tid_caption = "Metric Card CSS"
    tid_creator = "Drevarr@github.com"


    # Push the tid to the output list
    append_tid_for_output(
        create_new_tid_from_template(tid_title, tid_caption, tid_text, tid_tags, creator=tid_creator),
        tid_list
    )          


def trend_info(a: float, b: float, prefer_higher: bool = True) -> tuple[str, float]:
    """Return (css_class, signed_diff) comparing *a* against *b*.

    ``prefer_higher=True``  -> positive when *a* > *b* (larger is better).
    ``prefer_higher=False`` -> positive when *a* < *b* (smaller is better).
    """
    diff = a - b if prefer_higher else b - a
    if diff > 0:
        return "positive", diff
    elif diff < 0:
        return "negative", diff
    return "", 0


def make_metric_card(icon: str, label: str, trend: str,
                     trend_value: str | float, metric_value: str,
                     metric_sub: str) -> str:
    """Build a single metric-card HTML block."""
    return (
        f"""<div class="metric-card">
              <div class="metric-top">
                <div class="metric-name">
                  <div class="metric-icon">
                    {icon}
                  </div>
                  <div class="metric-label">{label}</div>
                </div>
                <div class="trend {trend}">Δ {trend_value}</div>
              </div>
              <div class="metric-val">{metric_value}</div>
              <div class="metric-sub">{metric_sub}</div>
            </div>"""
    )


def _make_comparison_card(rows: list[str], icon: str, label: str,
                          squad_val: float, enemy_val: float,
                          prefer_higher: bool = True,
                          trend_format: str | None = None) -> None:
    """Append a comparison metric card to *rows* and compute trend.

    Parameters
    ----------
    rows :
        Accumulator list for HTML fragments.
    trend_format :
        Optional format string applied to the signed diff (e.g. ``"/min"``).
        If ``None`` the raw float is used.
    """
    css_class, diff = trend_info(squad_val, enemy_val, prefer_higher)

    if trend_format is not None:
        trend_value_str = f"{diff:{trend_format}}"
    else:
        trend_value_str = str(diff)

    metric_card = make_metric_card(
        icon=icon,
        label=label,
        trend=css_class,
        trend_value=trend_value_str,
        metric_value=f"{squad_val:,.0f} --- {enemy_val:,.0f}",
        metric_sub="Squad --- Enemy",
    )
    rows.append(metric_card)


def make_profession_card(title: str, top_ten: dict) -> str:
    """Build a profession-breakdown card from *summarize_fight_damage* output."""
    total = top_ten["total"]
    channel_items: list[str] = []

    for prof, value in top_ten["top"].items():
        icon = "{{" + prof + "}}"
        pct = (value / total * 100) if total else 0.0
        channel_items.append(
            f"""<div class="channel-item"
                 title="{prof}: {value:,} damage ({pct:.1f}% of total)">
              <span class="ch-name">{icon} {prof}</span>
              <span class="ch-value">{value:,}</span>
              <span class="ch-pct">{pct:.1f}%</span>
            </div>"""
        )        

    other_value = top_ten.get(OTHER_PROFS_KEY, 0)
    other_pct = (other_value / total * 100) if total else 0.0
    channel_items.append(
        f"""<div class="channel-item"
             title="{OTHER_PROFS_KEY}: {other_value:,} damage ({other_pct:.1f}% of total)">
          <span class="ch-name">{OTHER_PROFS_KEY}</span>
          <span class="ch-value">{other_value:,}</span>
          <span class="ch-pct">{other_pct:.1f}%</span>
        </div>"""
    )  

    return (
        f"""<div class="breakdown-card">
              <h3 class="breakdown-title">{title}</h3>
              <div class="channel-list">
                {''.join(channel_items)}
              </div>
            </div>"""
    )


def make_player_breakdown_card(title, players, stat, limit=10):
    total_value = sum(
        data.get(stat, 0)
        for data in players.values()
    )

    sorted_players = sorted(
        players.items(),
        key=lambda item: item[1].get(stat, 0),
        reverse=True
    )

    channel_items = []

    for player_name, data in sorted_players[:limit]:
        value = data.get(stat, 0)
        pct = (value / total_value * 100) if total_value else 0

        account, profession, name = player_name.split("-", 2)

        display_name = f"{{{{{profession}}}}}{name}"

        channel_items.append(
            f"""<div class="channel-item"
                 title="{account}: {value:,} ({pct:.1f}% of total)">
                <span class="ch-name">{display_name}</span>
                <span class="ch-value">{value:,}</span>
                <span class="ch-pct">{pct:.1f}%</span>
            </div>"""
        )

    return f"""<div class="breakdown-card">
        <h3 class="breakdown-title">{title} - Top {limit}</h3>
        <div class="channel-list">
            {''.join(channel_items)}
        </div>
    </div>"""


def make_breakdown_card(title: str, top_list: list[dict]) -> str:
    channel_items: list[str] = []

    for skill in top_list:
        icon = skill["icon"]
        name = skill["name"]
        value = skill["value"]
        pct = skill["pct"] * 100
        channel_items.append(
            f"""<div class="channel-item"
                 title="{html.escape(name)}: {value:,} damage ({pct:.1f}% of total)">
              <span class="ch-name">[img width=24 [{name}|{icon}]]-{name}</span>
              <span class="ch-value">{value:,}</span>
              <span class="ch-pct">{pct:.1f}%</span>
            </div>"""            
        )

    return (
        f"""<div class="breakdown-card">
              <h3 class="breakdown-title">{title}</h3>
              <div class="channel-list">
                {''.join(channel_items)}
              </div>
            </div>"""
    )


def get_top_skill_list(data: dict, f_data, fight_num: str, category: str,
                       stat: str, siege_skills: set[int],
                       skill_map: dict, buff_map: dict,
                       top_n: int = 10) -> list[dict]:
    if category == "enemy_skills":
        fight_data = f_data[category]
    else:
        fight_data = data["fight"][fight_num][category]

    filtered_skills = {
        skill_id: skill_data
        for skill_id, skill_data in fight_data.items()
        if int(skill_id) not in siege_skills
    }

    total_value = sum(
        skill_data.get(stat, 0) for skill_data in filtered_skills.values()
    )

    sorted_skills = sorted(
        filtered_skills.items(),
        key=lambda item: item[1].get(stat, 0),
        reverse=True,
    )

    result: list[dict] = []
    for skill_id, skill_data in sorted_skills[:top_n]:
        stat_value = skill_data.get(stat, 0)
        stat_pct = stat_value / total_value if total_value else 0.0

        skill_key = f"s{skill_id}"
        buff_key = f"b{skill_id}"

        if skill_key in skill_map:
            icon = skill_map[skill_key]["icon"]
            name = skill_map[skill_key]["name"].replace("(Minor/Major/Superior ", "(")
        elif buff_key in buff_map:
            icon = buff_map[buff_key]["icon"]
            name = buff_map[buff_key]["name"].replace("(Minor/Major/Superior ", "(")
        else:
            icon = "{{unknown}}"
            name = skill_id

        result.append({
            "skill_id": skill_id,
            "icon": icon,
            "name": name,
            "value": stat_value,
            "pct": stat_pct,
        })

    return result


def summarize_fight_damage(data: dict, stat: str, top_n: int = 10) -> dict:
    sorted_profs = sorted(
        (
            (profession, values.get(stat, 0))
            for profession, values in data.items()
            if values.get(stat, 0) > 0
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    total = sum(values.get(stat, 0) for values in data.values())
    top_profs = sorted_profs[:top_n]
    other_value = sum(value for _, value in sorted_profs[top_n:])

    return {
        "total": total,
        "top": {prof: val for prof, val in top_profs},
        OTHER_PROFS_KEY: other_value,
    }


def build_fight_cards(data: dict, fight_num: int, fight_data_charts: bool, tid_date_time: str, tid_list: list) -> str:
    rows: list[str] = []

    fight_name = data["fight_name"]
    fight_link = data["fight_link"]
    fight_date = data["fight_date"]
    fight_end = data["fight_end"]
    fight_duration = data["fight_duration"]
    fight_minutes = round(data["fight_durationMS"] / 60000, 1)

    squad_players = data["squad_count"]
    ally_players = data["non_squad_count"]
    enemy_players = data["enemy_count"]
    enemy_teams = ""
    if data["enemy_Red"]:
        enemy_teams += f'<span class="metric-val-small-r"> R:{data["enemy_Red"]}</span>'
    if data["enemy_Blue"]:
        enemy_teams += f'<span class="metric-val-small-b"> B:{data["enemy_Blue"]}</span>'
    if data["enemy_Green"]:
        enemy_teams += f'<span class="metric-val-small-g"> G:{data["enemy_Green"]}</span>'

    squad_kills = data["enemy_killed"]
    squad_downs = data["enemy_downed"]

    enemy_kills = data["defenses"].get("deadCount", 0)
    enemy_downs = data["defenses"].get("downCount", 0)

    squad_strips = data["support"].get("boonStrips", 0)
    enemy_strips = data["defenses"].get("boonStrips", 0)

    squad_cc = data["statsTargets"].get("appliedCrowdControl", 0)
    enemy_cc = data["defenses"].get("receivedCrowdControl", 0)

    squad_interrupt = data["statsTargets"].get("interrupts", 0)
    enemy_interrupt = data["defenses"].get("interruptedCount", 0)

    squad_blocked = data["defenses"].get("blockedCount", 0)
    squad_evaded = data["defenses"].get("evadedCount", 0)
    enemy_blocked = data["statsTargets"].get("blocked", 0)
    enemy_evaded = data["statsTargets"].get("evaded", 0)

    squad_barrier_damage = data["defenses"].get("damageBarrier", 0)
    enemy_barrier_damage = sum(
        info.get("shieldDamage", 0)
        for info in data["targetDamageDist"].values()
    )

    # --- Header ---
    rows.append('<h1 class="page-title">Fight ' + str(fight_num) + ' - Overview</h1>')
    if fight_link:
        EI_link = f' · [[Elite Insight Fight Log|{fight_link}]]'
    else:
        EI_link = ""
    rows.append(f'<div class="page-sub">Location: {fight_name}  ·  Duration: {fight_duration} · ending at {fight_end}{EI_link}</div>')

    rows.append('<div class="fight-nav">')
    rows.append('    <$button class="fight-nav-btn" selectedClass="fight-nav-btn.active" set="$:/state/FR" setTo="Outcome">Outcome</$button>')
    rows.append('    <$button class="fight-nav-btn" selectedClass="fight-nav-btn.active" set="$:/state/FR" setTo="Combat">Timeline</$button>')
    rows.append('    <$button class="fight-nav-btn" selectedClass="fight-nav-btn.active"  set="$:/state/FR" setTo="Professions">Professions</$button>')
    rows.append('    <$button class="fight-nav-btn" selectedClass="fight-nav-btn.active"  set="$:/state/FR" setTo="Skills">Skills</$button>')
    rows.append('    <$button class="fight-nav-btn" selectedClass="fight-nav-btn.active"  set="$:/state/FR" setTo="Players">Players</$button>')
    rows.append('    <$button class="fight-nav-btn" selectedClass="fight-nav-btn.active"  set="$:/state/FR" setTo="Composition">Squad/Enemy Comp</$button>')    
    rows.append('</div>')

    rows.append('<$reveal type="match" state="$:/state/FR" text="Outcome" default="Outcome">\n')
                
    rows.append('<div class="metric-grid">')

    # Players (prefer_higher=True, custom format)
    team_size = squad_players + ally_players
    css_class, diff = trend_info(team_size, enemy_players, True)
    rows.append(make_metric_card(
        icon="{{40px-Catmander_tag_(blue).png}}",
        label="Players",
        trend=css_class,
        trend_value=diff,
        metric_value=str(squad_players) + ' --- ' + str(ally_players) + ' --- ' + str(enemy_players)+ '(' + str(enemy_teams) +')',
        metric_sub="Squad --- Allies --- Enemy",
    ))

    # Kills
    _make_comparison_card(
        rows, "{{Ally_death.png}}", "Kills",
        squad_kills, enemy_kills, prefer_higher=True,
    )

    # Downs
    _make_comparison_card(
        rows, "{{downed}}", "Downs",
        squad_downs, enemy_downs, prefer_higher=True,
    )

    # Down Conversion (percentage)
    squad_down_conv = (squad_kills / squad_downs * 100) if squad_downs else 0
    enemy_down_conv = (enemy_kills / enemy_downs * 100) if enemy_downs else 0
    css_class, conv_diff = trend_info(squad_down_conv, enemy_down_conv, True)
    rows.append(make_metric_card(
        icon="{{downed}}",
        label="Down Conversion",
        trend=css_class,
        trend_value=f"{conv_diff:,.1f}%",
        metric_value=f"{squad_down_conv:,.1f}% --- {enemy_down_conv:,.1f}%",
        metric_sub="Squad --- Enemy",
    ))

    # Down Pressure (/min)
    squad_down_min = squad_downs / fight_minutes if fight_minutes else 0
    enemy_down_min = enemy_downs / fight_minutes if fight_minutes else 0
    css_class, dp_diff = trend_info(squad_down_min, enemy_down_min, True)
    rows.append(make_metric_card(
        icon="{{downed}}",
        label="Down Pressure",
        trend=css_class,
        trend_value=f"{dp_diff:,.1f}/min",
        metric_value=f"{squad_down_min:,.1f}/min --- {enemy_down_min:,.1f}/min",
        metric_sub="Squad --- Enemy",
    ))

    rows.append('</div>')
    rows.append('<div class="metric-grid">')    
    
    # Boon Strips
    _make_comparison_card(
        rows, "{{Boon Strips}}", "Boon Strips",
        squad_strips, enemy_strips, prefer_higher=True,
    )

    # Applied Crowd Control
    _make_comparison_card(
        rows, "{{appliedCrowdControl}}", "Applied Crowd Control",
        squad_cc, enemy_cc, prefer_higher=True,
    )

    # Interrupts Out
    _make_comparison_card(
        rows, "{{interruptedCount}}", "Interrupts Out",
        squad_interrupt, enemy_interrupt, prefer_higher=True,
    )

    # Block/Evade
    squad_cnt = squad_blocked + squad_evaded
    enemy_cnt = enemy_blocked + enemy_evaded
    _make_comparison_card(
        rows, "{{evadedCount}}", "Block/Evade",
        squad_cnt, enemy_cnt, prefer_higher=True,
    )

    # Barrier Damage
    css_class, barrier_diff = trend_info(
        squad_barrier_damage, enemy_barrier_damage, prefer_higher=True,
    )
    rows.append(make_metric_card(
        icon="{{damageBarrier}}",
        label="Barrier Damage",
        trend=css_class,
        trend_value=f"{barrier_diff:,.0f}",
        metric_value=f"{squad_barrier_damage:,.0f} --- {enemy_barrier_damage:,.0f}",
        metric_sub="Squad --- Enemy",
    ))

    rows.append("</div>")
    rows.append('</$reveal>\n')

    rows.append('<$reveal type="match" state="$:/state/FR" text="Combat">\n')
    if fight_data_charts:
        rows.append(f'{{{{{tid_date_time}_Fight_{fight_num:02}_Damage_Output_Review}}}}')
    else:
        rows.append("! Set `fight_data_charts = true` in top_stats_config.ini to display combat timeline chart")

    rows.append('\n</$reveal>')

    return "\n".join(rows)


def make_fight_reviews(top_stats: dict, fight_data, skill_map, buff_map, fight_data_charts, tid_date_time: str,
                       tid_list: list) -> None:
    """Build fight-review TIDs and append them to *tid_list*."""

    for fight_num, data in top_stats["fight"].items():
        f_data = fight_data[fight_num]
        rows: list[str] = []

        #Overview card
        rows.append(build_fight_cards(data, fight_num, fight_data_charts, tid_date_time, tid_list))

        #Squad/Team Composition
        rows.append(build_squad_composition_for_fight(top_stats, fight_num))

        #Profession breakdowns
        rows.append('<$reveal type="match" state="$:/state/FR" text="Professions">\n')        
        rows.append('<div class="breakdown-row">')

        for label, source_key, stat_key in [
            ("Squad Down Contribution by Profession", "squad", "down_contribution"),
            ("Enemy Down Contribution by Profession", "enemies", "downContribution"),
            ("Squad Total Damage by Profession", "squad", "damage"),
            ("Enemy Total Damage by Profession", "enemies", "totalDamage"),
        ]:
            top_list = summarize_fight_damage(f_data[source_key], stat=stat_key)
            rows.append(make_profession_card(label, top_list))

        rows.append("</div>")
        rows.append('</$reveal>\n')

        rows.append("")
        rows.append('<$reveal type="match" state="$:/state/FR" text="Skills">\n')        
        rows.append('<div class="breakdown-row">')

        #Skill breakdowns
        for label, source_key, stat_key in [
            ("Squad Down Contribution by Skill - Top 10", "targetDamageDist", "downContribution"),
            ("Enemy Down Contribution by Skill - Top 10", "enemy_skills", "downContribution"),
            ("Squad Total Damage by Skill - Top 10", "targetDamageDist", "totalDamage"),
            ("Enemy Total Damage by Skill - Top 10", "enemy_skills", "totalDamage"),
        ]:
            top_list = get_top_skill_list(
                top_stats, f_data, fight_num, source_key, stat_key, siege_skill_ids, skill_map, buff_map
            )
            rows.append(make_breakdown_card(label, top_list))

        rows.append("</div>")
        rows.append("</$reveal>\n")

        #rows.append("---")
        rows.append('<$reveal type="match" state="$:/state/FR" text="Players">\n')        
        rows.append('<div class="breakdown-row">')        
        # --- Player breakdowns ---
        for label, source_key, stat_key in [
            ("Down Contribution by Player", "players", "down_contribution"),
            ("Total Damage by Player", "players", "damage"),
            ("Total Boon Strips by Player", "players", "boon_strips"),
            ("Total Condition Cleanses by Player", "players", "condi_cleanse"),
            ("Total Healing by Player", "players", "healing"),
            ("Total Barrier by Player", "players", "barrier"),
            ("Total Interrupts by Player", "players", "interrupts"),
            ("Total Evaded/Blocked by Player", "players", "evaded_blocked"),
            ("Total CC by Player", "players", "appliedCrowdControl"),
            ("Total CC Received by Player", "players", "receivedCrowdControl"),
        ]:
            rows.append(
                make_player_breakdown_card(
                    label,
                    f_data[source_key],
                    stat_key
                )
            )
        rows.append("</div>")
        rows.append('</$reveal>\n')

        # --- Build and push the TID ---
        tid_text = "\n".join(rows)
        tid_title = tid_date_time + "-Fight-Review-" + str(fight_num)
        tid_caption = "Fight - " + str(fight_num)
        tid_creator = "Drevarr@github.com"

        append_tid_for_output(
            create_new_tid_from_template(
                tid_title, tid_caption, tid_text, tid_date_time,
                creator=tid_creator,
            ),
            tid_list,
        )

def build_Fight_Review_menu_tabs(tid_date_time: str, tid_list: list) -> None:
	"""Builds a menu tab macro for healers."""

	# Build the menu tab macro
	menu_tags = f"{tid_date_time}"
	menu_title = f"{tid_date_time}-Fight-Reviews"
	menu_caption = f"Fight Reviews"
	menu_creator = f"Drevarr@github.com"
	menu_text = f'<$macrocall $name="tabs" tabsList="[prefix[{tid_date_time}-Fight-Review-]] :sort:number[length[]]" '+'default={{{'+f'[prefix[{tid_date_time}-Fight-Review-]first[]]'+'}}} state="$:/temp/fight_review"/>'

	# Push the menu tab to the output list
	append_tid_for_output(
		create_new_tid_from_template(menu_title, menu_caption, menu_text, menu_tags, creator=menu_creator),
		tid_list
	)        