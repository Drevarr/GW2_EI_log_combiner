# GW2_EI_log_combiner  ![GitHub Release](https://img.shields.io/github/v/release/Drevarr/GW2_EI_log_combiner?include_prereleases&display_name=release)

GW2 - Elite Insight Multiple Log Summary



Combines multiple [ArcDps](https://www.deltaconnected.com/arcdps/x64/) logs processed by [GW2 Elite Insight Parser](https://github.com/baaron4/GW2-Elite-Insights-Parser/releases) to json output into summarized drag and drop package for use with a [TW5](https://github.com/TiddlyWiki/TiddlyWiki5) static html file or [TW5](https://github.com/TiddlyWiki/TiddlyWiki5) nodejs server.  

This is a continuation of my efforts previously focused on a fork of @Freyavf /[arcdps_top_stats_parser](https://github.com/Drevarr/arcdps_top_stats_parser).  Influenced heavily by all the participants in the WvW Data Analysis discord 


Currently works with WVW and Detailed WVW logs. Partially working with PVElogs, still needs adjustments to handle the PVE formats.


**Steps for success**

 - Parse your [ArcDps](https://www.deltaconnected.com/arcdps/x64/) WvW logs with [GW2 Elite Insight Parser](https://github.com/baaron4/GW2-Elite-Insights-Parser/releases) 
     - Ensure all options are checked under `Encounter` on the general tab 
     - Ensure you have `Output as JSON` checked on the Raw output tab
     - There are provided example EI settings config file you can load via the `load settings` button:
       -  `Example Elite Insight v3_13_0_0 and earlier Config file for log parsing.conf` for versions prior to 3.14.0.0
       -  `Example Elite Insight v3_14_0_0 Config file for log parsing.conf` for versions starting at 3.14.0.0
       -  Be sure to update your `DPSReportUserToken=YourUserTokenFromDpsReports` in the config.
 - Decompress the [latest release](https://github.com/Drevarr/GW2_EI_log_combiner/releases) file to your preferred location
 - Edit the `top_stats_config.ini` file to set the `input_directory` so it points to the location of your saved JSON logs. Optional fields `db_output_filename` and `db_path` control the name and location of the SQLite database.
 - Double click the `TopStats.exe` to run
 - Open the file `/Example_Output/Top_Stats_Index.html` in your browser of choice.
 - Drag and Drop the file `Drag_and_Drop_Log_Summary_for_2024yourdatatime.json` onto the opened `Top_Stats_Index.html` in your browser and click `import`
 - Open the 1. imported file link to view the summary
 - DM me with errors, suggestions and ideas. 
 - Send example arcdps logs generating issues would be appreciated 
 
**Optional**
 - You can run from source after installing required packages `pip install requests glicko2 xlsxwriter` via cmd line: 
   -  Examples:
      - `python tw5_top_stats.py -i d:\path\to\logs`  # `-i` flag to set the directory of the `EI json logs`
      or
      - `python tw5_top_stats.py -c flux_config.ini`  # `-c` flag to utilize a specific `guild_config.ini` file

 - You can use [TopStatsAIO](https://github.com/darkharasho/TopStatsAIO) for a GUI frontend that utilizes Elite Insights CLI version and either of my parsers.
 - You can create a single shareable standalone HTML report directly (skips the drag and drop step) with `--standalone-html` (`-s`) pointed at an empty viewer:
   - `python tw5_top_stats.py -i d:\path\to\logs --standalone-html Example_Output\Top_Stats_Index.html`
   - The report is written next to the summary `.json` and is typically much smaller than uncompressed HTML (observed savings vary with report content). It decompresses itself in the browser and requires `DecompressionStream` support (Chrome/Edge 80+, Firefox 113+, Safari 17+).
   - Set `compress_standalone_html = false` under `[TopStatsCfg]` for ordinary uncompressed HTML, or set `standalone_html_template = path\to\Top_Stats_Index.html` to create the report from the config instead of the command-line option.

### Example Output of current state shown here:  [Log Summary](https://wvwlogs.com)

---

![GitHub](https://img.shields.io/github/license/Drevarr/GW2_EI_log_combiner)


![Alt](https://repobeats.axiom.co/api/embed/30e54d6fd35e0a496f6e2edcd0fc8c40e1856f01.svg "Repobeats analytics image")
---
