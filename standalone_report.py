#    This file creates a standalone HTML report from the combined summary,
#    optionally compressed for easier sharing.
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
import binascii
import gzip
import html
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

TIDDLER_STORE_OPENER = '<script class="tiddlywiki-tiddler-store" type="application/json">'
SCRIPT_CLOSER = "</script>"

# Self-decompressing wrapper for a gzip-compressed standalone report.
# The payload uses only browser-native APIs and has no external dependencies.
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
      throw new Error('This report needs a browser with DecompressionStream support.');
    }}
    var b64 = document.getElementById('z').textContent;
    var bin = atob(b64);
    b64 = null;
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    bin = null;
    var blob = new Blob([bytes]);
    bytes = null;
    var stream = blob.stream().pipeThrough(new DecompressionStream('gzip'));
    blob = null;
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


def embed_tiddlers(template_html: str, tiddlers: list[dict[str, Any]]) -> str:
	"""Return the template with tiddlers appended as a new tiddler store block.

	Equivalent to drag-and-dropping the summary .json onto the template and
	saving, but automatic. Raises ValueError if the template is not a
	TiddlyWiki store-format html file.
	"""
	if not isinstance(template_html, str):
		raise TypeError("template_html must be a string")
	if not isinstance(tiddlers, list) or any(not isinstance(tiddler, dict) for tiddler in tiddlers):
		raise TypeError("tiddlers must be a list of dictionaries")

	last_start = template_html.rfind(TIDDLER_STORE_OPENER)
	if last_start == -1:
		raise ValueError("template is not a TiddlyWiki store-format html file")
	close = template_html.find(SCRIPT_CLOSER, last_start)
	if close == -1:
		raise ValueError("template contains an unterminated TiddlyWiki store block")

	serialized = json.dumps(tiddlers, ensure_ascii=False, separators=(",", ":"))
	# "<" must not appear raw inside a script element (</script> would end it)
	safe = serialized.replace("<", "\\u003C")
	new_block = f"\n{TIDDLER_STORE_OPENER}{safe}{SCRIPT_CLOSER}"
	close += len(SCRIPT_CLOSER)
	# TiddlyWiki reads store blocks in document order. Appending generated
	# tiddlers last makes them override same-titled template tiddlers, matching
	# drag-and-drop import behavior.
	return template_html[:close] + new_block + template_html[close:]


def compress_standalone_html(full_html: str) -> str:
	"""Wrap a standalone HTML report in a self-decompressing loader."""
	if not isinstance(full_html, str):
		raise TypeError("full_html must be a string")
	m = re.search(r"<title>(.*?)</title>", full_html, re.DOTALL | re.IGNORECASE)
	title = html.unescape(m.group(1).strip()) if m else "Log Summary Report"
	payload = base64.b64encode(
		gzip.compress(full_html.encode("utf-8"), compresslevel=9, mtime=0)
	).decode("ascii")
	return LOADER_TEMPLATE.format(title=html.escape(title), payload=payload)


def decompress_standalone_html(packed_html: str) -> str:
	"""Inverse of compress_standalone_html, for tooling and tests."""
	if not isinstance(packed_html, str):
		raise TypeError("packed_html must be a string")
	m = re.search(r'<script id="z" type="text/plain">([A-Za-z0-9+/=]+)</script>', packed_html)
	if not m:
		raise ValueError("not a compressed report file")
	try:
		compressed = base64.b64decode(m.group(1), validate=True)
		return gzip.decompress(compressed).decode("utf-8")
	except (binascii.Error, gzip.BadGzipFile, UnicodeDecodeError, EOFError) as exc:
		raise ValueError("compressed report payload is invalid") from exc


def derive_standalone_filename(summary_filename: str) -> str:
	"""Derive an HTML filename that cannot overwrite the summary JSON."""
	root, extension = os.path.splitext(summary_filename)
	if extension.lower() == ".html":
		return root + ".standalone.html"
	return root + ".html"


def paths_refer_to_same_file(first_path: str, second_path: str) -> bool:
	"""Return whether two paths resolve to the same existing or future file."""
	first = Path(first_path).resolve()
	second = Path(second_path).resolve()
	if os.path.normcase(str(first)) == os.path.normcase(str(second)):
		return True
	return first.exists() and second.exists() and os.path.samefile(first, second)


def create_standalone_html(template_path: str, tiddlers: list[dict[str, Any]], output_filename: str,
						   compress: bool = True) -> str:
	"""Create a standalone HTML report containing the supplied tiddlers.

	template_path: an empty TW5 viewer such as Example_Output/Top_Stats_Index.html.
	Returns output_filename.
	"""
	template = Path(template_path).resolve()
	output = Path(output_filename).resolve()
	if paths_refer_to_same_file(str(template), str(output)):
		raise ValueError("template and output paths must refer to different files")

	with template.open(encoding="utf-8") as f:
		template_html = f.read()
	full_html = embed_tiddlers(template_html, tiddlers)
	if compress:
		full_html = compress_standalone_html(full_html)

	output_parent = output.parent
	output_parent.mkdir(parents=True, exist_ok=True)
	temp_name = None
	try:
		with tempfile.NamedTemporaryFile(
			"w",
			encoding="utf-8",
			dir=output_parent,
			prefix=f".{output.name}.",
			suffix=".tmp",
			delete=False,
		) as temp_file:
			temp_name = temp_file.name
			temp_file.write(full_html)
			temp_file.flush()
			os.fsync(temp_file.fileno())
		os.replace(temp_name, output)
	except Exception:
		if temp_name:
			try:
				os.unlink(temp_name)
			except FileNotFoundError:
				pass
			except OSError as cleanup_error:
				print(
					f"Warning: could not remove temporary report {temp_name}: {cleanup_error}",
					file=sys.stderr,
				)
		raise
	return str(output_filename)
