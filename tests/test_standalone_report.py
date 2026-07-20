import base64
import gzip
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from standalone_report import (
	TIDDLER_STORE_OPENER,
	compress_standalone_html,
	create_standalone_html,
	decompress_standalone_html,
	derive_standalone_filename,
	embed_tiddlers,
	paths_refer_to_same_file,
)


MINIMAL_TEMPLATE = (
	"<!doctype html><html><head><title>A &amp; B</title></head><body>"
	f"{TIDDLER_STORE_OPENER}[]</script>"
	"<script>window.booted = true;</script></body></html>"
)


class EmbedTiddlersTests(unittest.TestCase):
	def test_appends_json_store_before_boot_scripts(self):
		tiddlers = [{"title": "Report", "text": "contents"}]

		result = embed_tiddlers(MINIMAL_TEMPLATE, tiddlers)

		self.assertEqual(result.count(TIDDLER_STORE_OPENER), 2)
		self.assertLess(result.index('"title":"Report"'), result.index("window.booted"))

	def test_escapes_script_closer_in_tiddler_content(self):
		result = embed_tiddlers(
			MINIMAL_TEMPLATE,
			[{"title": "Report", "text": "</script><script>alert(1)</script>"}],
		)

		appended_store = result.rsplit(TIDDLER_STORE_OPENER, 1)[1].split("</script>", 1)[0]
		self.assertNotIn("<", appended_store)
		self.assertIn("\\u003C/script>", appended_store)
		self.assertEqual(
			json.loads(appended_store)[0]["text"],
			"</script><script>alert(1)</script>",
		)

	def test_generated_tiddlers_are_appended_after_template_tiddlers(self):
		result = embed_tiddlers(
			MINIMAL_TEMPLATE,
			[{"title": "$:/SiteTitle", "text": "Generated title"}],
		)

		first_store = result.find(TIDDLER_STORE_OPENER)
		generated_store = result.rfind(TIDDLER_STORE_OPENER)
		self.assertGreater(generated_store, first_store)
		self.assertLess(generated_store, result.index("window.booted"))

	def test_rejects_non_tiddlywiki_template(self):
		with self.assertRaisesRegex(ValueError, "not a TiddlyWiki"):
			embed_tiddlers("<html></html>", [])

	def test_rejects_unterminated_store(self):
		with self.assertRaisesRegex(ValueError, "unterminated"):
			embed_tiddlers(TIDDLER_STORE_OPENER + "[]", [])

	def test_rejects_invalid_tiddler_collection(self):
		for invalid in (None, {}, ["not a tiddler"]):
			with self.subTest(invalid=invalid):
				with self.assertRaises(TypeError):
					embed_tiddlers(MINIMAL_TEMPLATE, invalid)


class CompressionTests(unittest.TestCase):
	def test_round_trip_preserves_unicode_exactly(self):
		report = "<!doctype html><title>Raid 😀</title><p>αβγ</p>"
		self.assertEqual(decompress_standalone_html(compress_standalone_html(report)), report)

	def test_title_entities_are_escaped_exactly_once(self):
		packed = compress_standalone_html(
			"<html><head><title>Guild &amp; Raid</title></head></html>"
		)
		self.assertIn("<title>Guild &amp; Raid</title>", packed)
		self.assertNotIn("&amp;amp;", packed)

	def test_round_trip_preserves_script_like_tiddler_content(self):
		tiddlers = [{
			"title": "Special content",
			"text": "</script><script>alert(1)</script> \u003C 😀",
		}]
		full_html = embed_tiddlers(MINIMAL_TEMPLATE, tiddlers)
		unpacked = decompress_standalone_html(compress_standalone_html(full_html))
		appended_store = unpacked.rsplit(TIDDLER_STORE_OPENER, 1)[1].split(
			"</script>", 1
		)[0]
		self.assertEqual(json.loads(appended_store), tiddlers)

	def test_compression_is_reproducible(self):
		report = "<!doctype html><title>Raid</title>" + ("stats" * 1000)
		first = compress_standalone_html(report)
		second = compress_standalone_html(report)
		self.assertEqual(first, second)
		payload = first.split('<script id="z" type="text/plain">', 1)[1].split(
			"</script>", 1
		)[0]
		# Gzip header bytes 4-7 are MTIME. Zero keeps identical inputs reproducible.
		self.assertEqual(base64.b64decode(payload)[4:8], b"\0\0\0\0")

	def test_rejects_invalid_payload(self):
		payload = base64.b64encode(b"not gzip").decode("ascii")
		packed = f'<script id="z" type="text/plain">{payload}</script>'
		with self.assertRaisesRegex(ValueError, "payload is invalid"):
			decompress_standalone_html(packed)

	def test_loader_payload_is_gzip(self):
		packed = compress_standalone_html("<title>Report</title>")
		payload = packed.split('<script id="z" type="text/plain">', 1)[1].split(
			"</script>", 1
		)[0]
		self.assertEqual(gzip.decompress(base64.b64decode(payload)), b"<title>Report</title>")


class CreateStandaloneHtmlTests(unittest.TestCase):
	def test_writes_uncompressed_report(self):
		with tempfile.TemporaryDirectory() as directory:
			template = Path(directory) / "template.html"
			output = Path(directory) / "nested" / "report.html"
			template.write_text(MINIMAL_TEMPLATE, encoding="utf-8")

			returned = create_standalone_html(
				str(template),
				[{"title": "Report", "text": "contents"}],
				str(output),
				compress=False,
			)

			self.assertEqual(returned, str(output))
			self.assertIn('"title":"Report"', output.read_text(encoding="utf-8"))
			self.assertEqual(list(output.parent.glob(f".{output.name}.*.tmp")), [])

	def test_rejects_template_output_alias_without_changing_template(self):
		with tempfile.TemporaryDirectory() as directory:
			template = Path(directory) / "template.html"
			template.write_text(MINIMAL_TEMPLATE, encoding="utf-8")

			with self.assertRaisesRegex(ValueError, "different files"):
				create_standalone_html(str(template), [], str(template))

			self.assertEqual(template.read_text(encoding="utf-8"), MINIMAL_TEMPLATE)

	def test_writes_compressed_report(self):
		with tempfile.TemporaryDirectory() as directory:
			template = Path(directory) / "template.html"
			output = Path(directory) / "report.html"
			template.write_text(MINIMAL_TEMPLATE, encoding="utf-8")

			create_standalone_html(
				str(template),
				[{"title": "Report", "text": "contents"}],
				str(output),
			)

			unpacked = decompress_standalone_html(output.read_text(encoding="utf-8"))
			self.assertIn('"title":"Report"', unpacked)

	def test_failed_replace_preserves_existing_report_and_removes_temporary_file(self):
		with tempfile.TemporaryDirectory() as directory:
			template = Path(directory) / "template.html"
			output = Path(directory) / "report.html"
			template.write_text(MINIMAL_TEMPLATE, encoding="utf-8")
			output.write_text("existing report", encoding="utf-8")

			with patch("standalone_report.os.replace", side_effect=OSError("interrupted")):
				with self.assertRaisesRegex(OSError, "interrupted"):
					create_standalone_html(str(template), [], str(output))

			self.assertEqual(output.read_text(encoding="utf-8"), "existing report")
			self.assertEqual(list(output.parent.glob(f".{output.name}.*.tmp")), [])


class DeriveStandaloneFilenameTests(unittest.TestCase):
	def test_replaces_non_html_extension(self):
		self.assertEqual(derive_standalone_filename("report.json"), "report.html")
		self.assertEqual(derive_standalone_filename("report.custom"), "report.html")

	def test_appends_extension_to_extensionless_name(self):
		self.assertEqual(derive_standalone_filename("report"), "report.html")

	def test_never_reuses_html_summary_filename(self):
		self.assertEqual(
			derive_standalone_filename("report.html"),
			"report.standalone.html",
		)
		self.assertEqual(
			derive_standalone_filename("report.HTML"),
			"report.standalone.html",
		)


class PathsReferToSameFileTests(unittest.TestCase):
	def test_detects_lexical_aliases_for_future_file(self):
		with tempfile.TemporaryDirectory() as directory:
			directory_path = Path(directory)
			direct = directory_path / "viewer.html"
			alias = directory_path / "nested" / ".." / "viewer.html"
			self.assertTrue(paths_refer_to_same_file(str(direct), str(alias)))

	def test_detects_hard_link_aliases(self):
		with tempfile.TemporaryDirectory() as directory:
			original = Path(directory) / "viewer.html"
			hard_link = Path(directory) / "viewer-link.html"
			original.write_text(MINIMAL_TEMPLATE, encoding="utf-8")
			os.link(original, hard_link)
			self.assertTrue(paths_refer_to_same_file(str(original), str(hard_link)))

	def test_distinguishes_different_paths(self):
		with tempfile.TemporaryDirectory() as directory:
			first = Path(directory) / "first.html"
			second = Path(directory) / "second.html"
			self.assertFalse(paths_refer_to_same_file(str(first), str(second)))


if __name__ == "__main__":
	unittest.main()
