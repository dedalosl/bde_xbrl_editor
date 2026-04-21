from __future__ import annotations

from pathlib import Path

import elementpath

from bde_xbrl_editor.taxonomy.linkbases.custom_functions import (
    parse_custom_function_linkbase,
)
from bde_xbrl_editor.validation.formula.xfi_functions import build_formula_parser


def test_parse_custom_function_linkbase_reads_signature_and_steps(tmp_path: Path) -> None:
    linkbase = tmp_path / "custom-functions.xml"
    linkbase.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
  xmlns:gen="http://xbrl.org/2008/generic"
  xmlns:variable="http://xbrl.org/2008/variable"
  xmlns:cfi="http://xbrl.org/2010/custom-function"
  xmlns:eg="http://example.com/custom"
  xmlns:xlink="http://www.w3.org/1999/xlink">
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <variable:function xlink:type="resource" xlink:label="trim_sig" name="eg:trim" output="xs:string">
      <variable:input type="xs:string?"/>
    </variable:function>
    <cfi:implementation xlink:type="resource" xlink:label="trim_impl">
      <cfi:input name="arg"/>
      <cfi:step name="without-trailing">replace($arg, '\\s+$', '')</cfi:step>
      <cfi:output>replace($without-trailing, '^\\s+', '')</cfi:output>
    </cfi:implementation>
    <gen:arc xlink:type="arc"
      xlink:arcrole="http://xbrl.org/arcrole/2010/function-implementation"
      xlink:from="trim_sig"
      xlink:to="trim_impl"/>
  </gen:link>
</link:linkbase>
""",
        encoding="utf-8",
    )

    definitions = parse_custom_function_linkbase(linkbase)

    assert len(definitions) == 1
    definition = definitions[0]
    assert definition.name == "eg:trim"
    assert definition.namespace == "http://example.com/custom"
    assert definition.input_names == ("arg",)
    assert len(definition.steps) == 2
    assert definition.steps[0].name == "without-trailing"
    assert definition.steps[1].is_output is True


def test_build_formula_parser_executes_linkbase_defined_custom_functions(tmp_path: Path) -> None:
    linkbase = tmp_path / "custom-functions.xml"
    linkbase.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
  xmlns:gen="http://xbrl.org/2008/generic"
  xmlns:variable="http://xbrl.org/2008/variable"
  xmlns:cfi="http://xbrl.org/2010/custom-function"
  xmlns:eg="http://example.com/custom"
  xmlns:xlink="http://www.w3.org/1999/xlink">
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <variable:function xlink:type="resource" xlink:label="trim_sig" name="eg:trim" output="xs:string">
      <variable:input type="xs:string?"/>
    </variable:function>
    <cfi:implementation xlink:type="resource" xlink:label="trim_impl">
      <cfi:input name="arg"/>
      <cfi:step name="without-trailing">replace($arg, '\\s+$', '')</cfi:step>
      <cfi:output>replace($without-trailing, '^\\s+', '')</cfi:output>
    </cfi:implementation>
    <gen:arc xlink:type="arc"
      xlink:arcrole="http://xbrl.org/arcrole/2010/function-implementation"
      xlink:from="trim_sig"
      xlink:to="trim_impl"/>
  </gen:link>
</link:linkbase>
""",
        encoding="utf-8",
    )
    definitions = parse_custom_function_linkbase(linkbase)

    parser = build_formula_parser(
        {"eg": "http://example.com/custom"},
        custom_functions=definitions,
    )
    token = parser.parse("eg:trim('  hello  ')")
    ctx = elementpath.XPathContext(root=None, item=True)

    result = list(token.select(ctx))

    assert result == ["hello"]


def test_cache_custom_functions_include_fmt_namespace() -> None:
    definitions = parse_custom_function_linkbase(
        Path("cache/www.bde.es/es/xbrl/func/error-formatting.xml")
    )

    names = {definition.name for definition in definitions}

    assert "fmt:common" in names
    assert "fmt:fact" in names
    assert "fmt:threshold" in names
