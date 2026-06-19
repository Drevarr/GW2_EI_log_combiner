from math import ceil
import requests


WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_GOES_HERE"
TOP_N = 10
TIME_THRESHOLD_MS = 3000
DEFAULT_DIST_TAG = 9999


dist_to_tag = []
player_apm = {}

def compute_player_apm(skill_cast_by_role):
    for prof, prof_data in skill_cast_by_role.items():
    	for player, player_data in prof_data.items():
    		if player not in "total":
    			player_apm[player] = player_data['total_no_auto_no_proc'] / (player_data['ActiveTime'] / 60)


def compute_average_distance(name_prof, death_on_tag):
    avg_dist = DEFAULT_DIST_TAG
    for name_prof in death_on_tag:
        if len(death_on_tag[name_prof]['distToTag']):
            avg_dist = round(sum(death_on_tag[name_prof]['distToTag']) / len(death_on_tag[name_prof]['distToTag']))
    return avg_dist


def calculate_downed_healing(data):
    total_downed_healing = 0
    
    for skill in data['extHealingStats']['skills']:
        if 'downedHealing' in data['extHealingStats']['skills'][skill]:
            if data['extHealingStats']['skills'][skill]['downedHealing'] > 0:
                total_downed_healing += data['extHealingStats']['skills'][skill]['downedHealing']
    return total_downed_healing


def fixed(text, width):
    return str(text)[:width].ljust(width)


def build_monospace_leaderboard(players, stat_key, formatter, top_n=10):

    top = sorted(
        players,
        key=lambda p: p.get(stat_key, 0),
        reverse=True if stat_key not in "Dist to Tag" else False
    )[:top_n]

    formatted = [formatter(p.get(stat_key, 0)) for p in top]

    max_val_width = max(len(v) for v in formatted) if formatted else 0

    rank_width = len(str(top_n)) + 1  # accounts for "10."
    
    lines = []

    for i, (p, value) in enumerate(zip(top, formatted)):

        rank = f"{i+1}.".ljust(rank_width)
        name = p["name"][:16].ljust(16)
        prof = p["profession"][:3].ljust(3)
        value = value.rjust(max_val_width)

        lines.append(f"{rank} ({prof}) {name} {value}")

    return "\n".join(lines)
    

def build_embed(title, color, players, stats):
    """
    Monospace leaderboard embed.
    Each stat becomes a code-block formatted leaderboard.
    """

    fields = []

    for name, key, fmt in stats:
        leaderboard_text = build_monospace_leaderboard(players, key, fmt)

        fields.append({
            "name": name,
            "value": f"```text\n{leaderboard_text}\n```",
            "inline": False
        })

    return {
        "title": title,
        "color": color,
        "fields": fields,
        "footer": {
            "text": "TopStats - GW2_EI_Log_Combiner",
            "icon_url": "https://avatars.githubusercontent.com/u/16168556?s=48&v=4"
        }
    }


def collect_discord_stats(json_data, death_on_tag):
    discord_players = []
    player_data = json_data['player']  
    raid_time_total = sum(data.get('fight_durationMS', 0) for data in json_data['fight'].values())
    skill_cast_by_role = json_data['skill_casts_by_role']


    compute_player_apm(skill_cast_by_role)

    for player, data in player_data.items():
        if data['fight_time'] >= (raid_time_total/TIME_THRESHOLD_MS):
            activeTime = data["active_time"]
            totalDamage = data["statsTargets"]["totalDmg"]
        
            discord_players.append({
                #Base Data
                "name": data["name"],
                "profession": data["profession"],
                "activeTime": activeTime,
                "numFights": data["num_fights"],
                #Offensive Data
                "totalDamage": totalDamage,
                "DmgPerSec": totalDamage / (activeTime/1000) if activeTime else 0,
                "downContrPct": (
                    data["statsTargets"]["downContribution"] / totalDamage
                    if totalDamage else 0
                ),
                "downedDamagePct": (
                    data["statsTargets"]["againstDownedDamage"] / totalDamage
                    if totalDamage else 0
                ),
                #Support Data
                "outgoing_healing": (
                    data['extHealingStats']['outgoing_healing']
                    if 'extHealingStats' in data and 'outgoing_healing' in data['extHealingStats'] else 0
                ),
                "outgoing_barrier":(
                    data['extBarrierStats']['outgoing_barrier'] 
                    if 'extBarrierStats' in data and 'outgoing_barrier' in data['extBarrierStats'] else 0
                ),
                "condiCleanse": data['support']['condiCleanse'],
                "downed_healing": (
                    calculate_downed_healing(data)
                    if 'extHealingStats' in data and 'skills' in data['extHealingStats'] else 0
                ),
                #Boon Strips Data
                "Boon Strips": data['support']['boonStrips'],
                "Boon Strips Downed": data['support']['boonStripDownContribution'],
                #Control Data
                "CC Downed": data['statsTargets']['appliedCrowdControlDownContribution'],
                "CC": data['statsTargets']['appliedCrowdControl'],
                "Interrupt": data['statsTargets']['interrupts'],
                #Misc Data
                "Dist to Tag": (
                    round(sum(death_on_tag[player]['distToTag']) / len(death_on_tag[player]['distToTag']))
                    if len(death_on_tag[player]['distToTag']) else DEFAULT_DIST_TAG
                ),
                "Actions per Minute": player_apm[player]
                
            })
    return discord_players

def build_raid_summary_embed(topstats):
    title_date = topstats['fight'][1]['fight_date']
    last_fight = topstats['overall']['last_fight']
    fight_count = len(topstats['fight'])

    enemies_killed = topstats['overall']['enemy_killed']
    enemies_downed = topstats['overall']['enemy_downed']

    squad_deaths = topstats['overall']['defenses']['deadCount']
    squad_downed = topstats['overall']['defenses']['downCount']

    incoming_damage = topstats['overall']['defenses']['damageTaken']
    outgoing_damage = topstats['overall']['statsTargets']['totalDmg']

    kdr = (
        enemies_killed / squad_deaths
        if squad_deaths
        else enemies_killed
    )

    body = (
        f"Last Fight      : {last_fight}\n"
        f"Fight Count     : {fight_count:,}\n"
        f"Enemies Killed  : {enemies_killed:,}\n"
        f"Enemies Downed  : {enemies_downed:,}\n"
        f"Squad Deaths    : {squad_deaths:,}\n"
        f"Squad Downed    : {squad_downed:,}\n"
        f"Outgoing Damage : {outgoing_damage:,.0f}\n"
        f"Incoming Damage : {incoming_damage:,.0f}\n"
        f"KDR             : {kdr:.2f}"
    )

    return {
        "title": f"📊 {title_date} : WvW Raid Summary",
        "color": 0xF1C40F,
        "description": f"```text\n{body}\n```"
    }


def build_offense_embed(players):
    stats = [
        ("⚔️ DPS Leaders", "DmgPerSec", lambda v: f"{v:,.0f}"),
        ("💥 Damage Leaders", "totalDamage", lambda v: f"{v:,.0f}"),
        ("📉 Down Contribution %", "downContrPct", lambda v: f"{v*100:.1f}%"),
        ("☠️ Downed Damage %", "downedDamagePct", lambda v: f"{v*100:.1f}%"),
    ]

    return build_embed("⚔️ Offensive Stats", 0xE74C3C, players, stats)


def build_support_embed(players):
    stats = [
        ("💚 Healing", "outgoing_healing", lambda v: f"{v:,.0f}"),
        ("🛡 Barrier", "outgoing_barrier", lambda v: f"{v:,.0f}"),
        ("🧹 Cleanse", "condiCleanse", lambda v: f"{v:,.0f}"),
        ("☠️ Downed Healing", "downed_healing", lambda v: f"{v:,.0f}"),
    ]

    return build_embed("💚 Support Stats", 0x2ECC71, players, stats)


def build_strip_embed(players):
    stats = [
        ("🔮 Boon Strips", "Boon Strips", lambda v: f"{v:,.0f}"),
        ("☠ Downed Strips", "Boon Strips Downed", lambda v: f"{v:,.0f}"),
    ]

    return build_embed("🔮 Boon Strips", 0x9B59B6, players, stats)


def build_control_embed(players):
    stats = [
        ("🎯 Crowd Control", "CC", lambda v: f"{v:,.0f}"),
        ("💥 CC Downed", "CC Downed", lambda v: f"{v:,.0f}"),
        ("⚡ Interrupts", "Interrupt", lambda v: f"{v:,.0f}"),
    ]

    return build_embed("🛡 Control Stats", 0x3498DB, players, stats)

def build_misc_embed(players):
    stats = [
        ("📐 Dist to Tag", "Dist to Tag", lambda v: f"{v:,.0f}"),
        ("🎹 Actions per Minute", "Actions per Minute", lambda v: f"{v:,.2f}"),
    ]

    return build_embed("🧾 Misc Stats", 0xA9A9A9, players, stats)
    
def build_custom_field(title, entries, formatter):
    """
    entries:
        [
            ("Drevarr", "Vindi", 104),
            ("Bob", "WB", 118),
        ]
    """

    formatted_values = [
        formatter(value)
        for _, _, value in entries
    ]

    max_width = max(len(v) for v in formatted_values) if formatted_values else 0

    lines = []

    for idx, ((name, profession, value), formatted) in enumerate(
        zip(entries, formatted_values)
    ):
        rank = f"{idx+1}."

        lines.append(
            f"{rank} "
            f"{fixed(profession,4)} "
            f"{fixed(name,18)} "
            f"{formatted.rjust(max_width)}"
        )

    return {
        "name": title,
        "value": f"```text\n{chr(10).join(lines)}\n```",
        "inline": False
    }


def send_report(json_data, players, webhook_url):
    embeds = [
        build_raid_summary_embed(json_data),
        build_offense_embed(players),
        build_support_embed(players),
        build_strip_embed(players),
        build_control_embed(players),
        build_misc_embed(players),
    ]

    payload = {
        "username": "GW2 WvW Report",
        "embeds": embeds[:10]  # Discord limit
    }

    r = requests.post(webhook_url, json=payload)
    r.raise_for_status()