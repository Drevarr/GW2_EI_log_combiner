#    This file bakes the combined summary into a single shareable .html
#    report file, optionally compressed to roughly a quarter of its size.
#    Copyright (C) 2026 SimpleHonors
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
import base64
import gzip
import html
import json
import re

TIDDLER_STORE_OPENER = '<script class="tiddlywiki-tiddler-store" type="application/json">'

# Small loader page: carries the full report as base64(gzip(html)) and
# unpacks it with the browser-native DecompressionStream (Chrome/Edge 80+,
# Firefox 113+, Safari 16.4+). No external scripts, works offline and as a
# Discord attachment. The unpacked document is byte-identical to the
# uncompressed bake, so nothing about the report changes.
LOADER_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #1a1a2e; color: #ddd;
         display: flex; align-items: center; justify-content: center;
         height: 100vh; margin: 0; }}
  .msg {{ text-align: center; }}
  .err {{ color: #ff8080; max-width: 34em; }}
</style>
</head>
<body>
<div class="msg" id="m">Unpacking report&hellip;</div>
<script id="z" type="text/plain">{payload}</script>
<script>
(async function () {{
  var m = document.getElementById('m');
  try {{
    if (typeof DecompressionStream === 'undefined') {{
      throw new Error('This report needs a current browser (Chrome, Edge, Firefox or Safari from 2023 or newer).');
    }}
    var b64 = document.getElementById('z').textContent;
    var bin = atob(b64);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    var stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    var doc = await new Response(stream).text();
    document.open();
    document.write(doc);
    document.close();
  }} catch (e) {{
    m.className = 'msg err';
    m.textContent = 'Could not open the report: ' + e.message;
  }}
}})();
</script>
</body>
</html>
"""


def inject_tid_list(template_html: str, tid_list: list) -> str:
	"""Return the template with tid_list appended as a new tiddler store block.

	Equivalent to drag-and-dropping the summary .json onto the template and
	saving, but automatic. Raises ValueError if the template is not a
	TiddlyWiki store-format html file.
	"""
	first = template_html.find(TIDDLER_STORE_OPENER)
	if first == -1:
		raise ValueError("template is not a TiddlyWiki store-format html file")
	serialized = json.dumps(tid_list, ensure_ascii=False, separators=(",", ":"))
	# "<" must not appear raw inside a script element (</script> would end it)
	safe = serialized.replace("<", "\\u003C")
	new_block = f"{TIDDLER_STORE_OPENER}{safe}</script>"
	last_start = template_html.rfind(TIDDLER_STORE_OPENER)
	close = template_html.index("</script>", last_start) + len("</script>")
	return template_html[:close] + new_block + template_html[close:]


def compress_html(full_html: str) -> str:
	"""Wrap a report page in the self-unpacking loader (about 4x smaller)."""
	m = re.search(r"<title>(.*?)</title>", full_html, re.DOTALL | re.IGNORECASE)
	title = m.group(1).strip() if m else "Log Summary Report"
	payload = base64.b64encode(gzip.compress(full_html.encode("utf-8"), 9)).decode("ascii")
	return LOADER_TEMPLATE.format(title=html.escape(title), payload=payload)


def decompress_html(packed_html: str) -> str:
	"""Inverse of compress_html, for tooling and tests."""
	m = re.search(r'<script id="z" type="text/plain">([A-Za-z0-9+/=]+)</script>', packed_html)
	if not m:
		raise ValueError("not a compressed report file")
	return gzip.decompress(base64.b64decode(m.group(1))).decode("utf-8")


def bake_standalone_html(template_path: str, tid_list: list, output_filename: str,
						 compress: bool = True) -> str:
	"""Bake tid_list into a single shareable .html report file.

	template_path: an empty TW5 viewer such as Example_Output/Top_Stats_Index.html.
	Returns output_filename.
	"""
	with open(template_path, encoding="utf-8") as f:
		template_html = f.read()
	full_html = inject_tid_list(template_html, tid_list)
	if compress:
		full_html = compress_html(full_html)
	with open(output_filename, "w", encoding="utf-8") as f:
		f.write(full_html)
	return output_filename
