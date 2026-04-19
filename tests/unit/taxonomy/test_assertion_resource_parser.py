from __future__ import annotations

from pathlib import Path

from bde_xbrl_editor.taxonomy.constants import (
    ARCROLE_ASSERTION_UNSATISFIED_MESSAGE,
    ARCROLE_ELEMENT_LABEL,
)
from bde_xbrl_editor.taxonomy.linkbases.assertion_resources import (
    parse_assertion_resource_linkbase,
)


def test_parse_assertion_resource_linkbase_uses_arcroles_not_filenames(tmp_path: Path) -> None:
    linkbase = tmp_path / "arbitrary-name.xml"
    linkbase.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
  xmlns:gen="http://xbrl.org/2008/generic"
  xmlns:label="http://xbrl.org/2008/label"
  xmlns:msg="http://xbrl.org/2010/message"
  xmlns:xlink="http://www.w3.org/1999/xlink">
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <link:loc xlink:type="locator" xlink:href="formula.xml#rule-A" xlink:label="loc_rule_A"/>
    <label:label xlink:type="resource" xlink:label="lab_rule_A" xlink:role="http://www.xbrl.org/2008/role/label" xml:lang="es">Definicion oficial</label:label>
    <msg:message xlink:type="resource" xlink:label="msg_rule_A" xlink:role="http://www.xbrl.org/2010/role/message" xml:lang="es">Mensaje oficial</msg:message>
    <gen:arc xlink:type="arc" xlink:arcrole="http://xbrl.org/arcrole/2008/element-label" xlink:from="loc_rule_A" xlink:to="lab_rule_A"/>
    <gen:arc xlink:type="arc" xlink:arcrole="http://xbrl.org/arcrole/2010/assertion-unsatisfied-message" xlink:from="loc_rule_A" xlink:to="msg_rule_A"/>
  </gen:link>
</link:linkbase>
""",
        encoding="utf-8",
    )

    parsed = parse_assertion_resource_linkbase(linkbase)

    assert "rule-A" in parsed
    assert any(resource.arcrole == ARCROLE_ELEMENT_LABEL for resource in parsed["rule-A"])
    assert any(
        resource.arcrole == ARCROLE_ASSERTION_UNSATISFIED_MESSAGE
        for resource in parsed["rule-A"]
    )
    assert any(resource.text == "Definicion oficial" for resource in parsed["rule-A"])
    assert any(resource.text == "Mensaje oficial" for resource in parsed["rule-A"])
