"""Unit tests for DTS discovery — path resolution, network block, circular refs, negative paths."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from bde_xbrl_editor.taxonomy.discovery import discover_dts
from bde_xbrl_editor.taxonomy.models import (
    TaxonomyParseError,
    UnsupportedTaxonomyFormatError,
)
from bde_xbrl_editor.taxonomy.settings import LoaderSettings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_xsd(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


MINIMAL_XSD = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
               xmlns:xbrli="http://www.xbrl.org/2003/instance"
               targetNamespace="http://test.example"
               elementFormDefault="qualified">
    </xs:schema>
""")

XSD_WITH_IMPORT = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xbrli="http://www.xbrl.org/2003/instance"
           targetNamespace="http://test.example"
           elementFormDefault="qualified">
  <xs:import namespace="http://other.example" schemaLocation="other.xsd"/>
</xs:schema>
"""

XSD_WITH_LINKBASE = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:link="http://www.xbrl.org/2003/linkbase"
           xmlns:xlink="http://www.w3.org/1999/xlink"
           targetNamespace="http://test.example">
  <xs:annotation>
    <xs:appinfo>
      <link:linkbaseRef xlink:type="simple"
                        xlink:href="labels.xml"
                        xlink:role="http://www.xbrl.org/2003/role/labelLinkbaseRef"
                        xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>
    </xs:appinfo>
  </xs:annotation>
</xs:schema>
"""

XSD_WITH_REMOTE = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xbrli="http://www.xbrl.org/2003/instance"
           targetNamespace="http://test.example">
  <xs:import namespace="http://external.example"
             schemaLocation="http://external.example/schema.xsd"/>
</xs:schema>
"""

LABEL_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:xlink="http://www.w3.org/1999/xlink">
</link:linkbase>
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDiscoveryBasic:
    def test_minimal_entry_point(self, tmp_path):
        xsd = write_xsd(tmp_path, "entry.xsd", MINIMAL_XSD)
        schemas, linkbases, _ = discover_dts(xsd, LoaderSettings())
        assert xsd.resolve() in schemas
        assert len(linkbases) == 0

    def test_discovers_imported_schema(self, tmp_path):
        write_xsd(tmp_path, "other.xsd", MINIMAL_XSD)
        entry = write_xsd(tmp_path, "entry.xsd", XSD_WITH_IMPORT)
        schemas, _, _ = discover_dts(entry, LoaderSettings())
        schema_names = {p.name for p in schemas}
        assert "entry.xsd" in schema_names
        assert "other.xsd" in schema_names

    def test_discovers_linkbase(self, tmp_path):
        (tmp_path / "labels.xml").write_text(LABEL_XML, encoding="utf-8")
        entry = write_xsd(tmp_path, "entry.xsd", XSD_WITH_LINKBASE)
        _, linkbases, _ = discover_dts(entry, LoaderSettings())
        lb_names = {p.name for p in linkbases}
        assert "labels.xml" in lb_names

    def test_does_not_recurse_into_standard_ns(self, tmp_path):
        """Standard XBRL namespace imports are skipped (no network call)."""
        content = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xbrli="http://www.xbrl.org/2003/instance"
           targetNamespace="http://test.example">
  <xs:import namespace="http://www.xbrl.org/2003/instance"
             schemaLocation="http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"/>
</xs:schema>
"""
        entry = write_xsd(tmp_path, "entry.xsd", content)
        # Should not raise — standard XBRL namespace is skipped
        schemas, _, _ = discover_dts(entry, LoaderSettings(allow_network=False))
        assert any(p.name == "entry.xsd" for p in schemas)


class TestNetworkBlock:
    def test_network_blocked_skips_remote_url_gracefully(self, tmp_path):
        # Remote URLs with no local catalog mapping are silently skipped so that
        # taxonomies with external imports still load from their local files.
        entry = write_xsd(tmp_path, "entry.xsd", XSD_WITH_REMOTE)
        schemas, _, skipped = discover_dts(entry, LoaderSettings(allow_network=False))
        # Entry point itself is always included
        assert any(p.name == "entry.xsd" for p in schemas)
        # The remote URL is reported in skipped_remote_urls
        assert any("external.example" in u for u in skipped)

    def test_local_catalog_resolves_remote_url(self, tmp_path):
        # If a local_catalog mapping exists, the remote URL is resolved locally.
        # XSD_WITH_REMOTE imports http://external.example/schema.xsd,
        # so the catalog must map http://external.example/ → tmp_path,
        # meaning the resolved local file is tmp_path/schema.xsd.
        local_schema = tmp_path / "schema.xsd"
        local_schema.write_text(
            '<?xml version="1.0"?>'
            '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"'
            ' targetNamespace="http://external.example"/>',
            encoding="utf-8",
        )
        catalog = {"http://external.example/": tmp_path}
        settings = LoaderSettings(allow_network=False, local_catalog=catalog)
        entry = write_xsd(tmp_path, "entry.xsd", XSD_WITH_REMOTE)
        schemas, _, skipped = discover_dts(entry, settings)
        assert any(p.name == "schema.xsd" for p in schemas)
        # Resolved via catalog → not in skipped
        assert not any("external.example" in u for u in skipped)


class TestNegativePaths:
    def test_missing_entry_point(self, tmp_path):
        with pytest.raises(UnsupportedTaxonomyFormatError) as exc_info:
            discover_dts(tmp_path / "nonexistent.xsd", LoaderSettings())
        assert str(exc_info.value)  # non-empty message

    def test_wrong_extension(self, tmp_path):
        txt = tmp_path / "entry.txt"
        txt.write_text("not xbrl")
        with pytest.raises(UnsupportedTaxonomyFormatError):
            discover_dts(txt, LoaderSettings())

    def test_malformed_xml(self, tmp_path):
        broken = tmp_path / "broken.xsd"
        broken.write_text("<xs:schema><unclosed>", encoding="utf-8")
        with pytest.raises(TaxonomyParseError) as exc_info:
            discover_dts(broken, LoaderSettings())
        err = exc_info.value
        assert str(err)  # non-empty human-readable message
        assert "broken.xsd" in err.file_path

    def test_non_xbrl_file_loader_raises(self, tmp_path):
        """Non-XBRL XSD passed to TaxonomyLoader raises TaxonomyLoadError with human-readable msg (FR-007, SC-004)."""
        from bde_xbrl_editor.taxonomy import TaxonomyCache, TaxonomyLoader, TaxonomyLoadError

        non_xbrl = tmp_path / "not_xbrl.xsd"
        non_xbrl.write_text(
            '<?xml version="1.0"?><xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"/>',
            encoding="utf-8",
        )
        loader = TaxonomyLoader(cache=TaxonomyCache())
        with pytest.raises(TaxonomyLoadError) as exc_info:
            loader.load(non_xbrl)
        msg = str(exc_info.value)
        assert len(msg) > 10, "Error message should be human-readable and non-empty"
        assert "xbrl" in msg.lower() or "concept" in msg.lower() or "taxonomy" in msg.lower()


class TestCircularReferences:
    def test_circular_import_does_not_hang(self, tmp_path):
        """Circular xs:import chain terminates (visited set prevents infinite loop)."""
        a_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://a.example">
  <xs:import namespace="http://b.example" schemaLocation="b.xsd"/>
</xs:schema>
"""
        b_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://b.example">
  <xs:import namespace="http://a.example" schemaLocation="a.xsd"/>
</xs:schema>
"""
        (tmp_path / "a.xsd").write_text(a_content, encoding="utf-8")
        (tmp_path / "b.xsd").write_text(b_content, encoding="utf-8")

        # Must terminate without infinite loop
        schemas, _, _ = discover_dts(tmp_path / "a.xsd", LoaderSettings())
        schema_names = {p.name for p in schemas}
        assert "a.xsd" in schema_names
        assert "b.xsd" in schema_names
