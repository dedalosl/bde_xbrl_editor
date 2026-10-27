from __future__ import annotations

from pathlib import Path

import elementpath

from bde_xbrl_editor.taxonomy.linkbases.custom_functions import (
    linkbase_contains_custom_functions,
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


def test_linkbase_contains_custom_functions_detects_signature_only_file(
    tmp_path: Path,
) -> None:
    linkbase = tmp_path / "interval-arithmetics.xml"
    linkbase.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
  xmlns:gen="http://xbrl.org/2008/generic"
  xmlns:variable="http://xbrl.org/2008/variable"
  xmlns:iaf="http://www.eurofiling.info/xbrl/func/interval-arithmetics"
  xmlns:xlink="http://www.w3.org/1999/xlink">
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <variable:function xlink:type="resource" xlink:label="subtract"
      name="iaf:numeric-subtract" output="item()">
      <variable:input type="item()"/>
      <variable:input type="item()"/>
    </variable:function>
  </gen:link>
</link:linkbase>
""",
        encoding="utf-8",
    )

    assert linkbase_contains_custom_functions(linkbase) is True


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
        Path("cache/www.bde.es/es/fr/xbrl/func/error-formatting.xml")
    )

    names = {definition.name for definition in definitions}

    assert "fmt:common" in names
    assert "fmt:fact" in names
    assert "fmt:threshold" in names


def test_cache_external_attributes_includes_signature_only_host_functions() -> None:
    definitions = parse_custom_function_linkbase(
        Path("cache/www.bde.es/es/fr/xbrl/func/external-attributes.xml")
    )

    signature_only = [
        definition
        for definition in definitions
        if definition.name == "fext:_atributo-str"
        and definition.input_types == ("xs:string", "xs:string")
    ]

    assert signature_only
    assert signature_only[0].steps == ()


def test_cache_interval_arithmetics_includes_numeric_subtract() -> None:
    definitions = parse_custom_function_linkbase(
        Path("cache/www.eurofiling.info/eu/fr/xbrl/func/interval-arithmetics.xml")
    )

    matches = [
        definition for definition in definitions if definition.name == "iaf:numeric-subtract"
    ]

    assert matches
    assert matches[0].input_types == ("item()", "item()")


def test_build_formula_parser_parses_external_attribute_wrapper() -> None:
    definitions = parse_custom_function_linkbase(
        Path("cache/www.bde.es/es/fr/xbrl/func/external-attributes.xml")
    )

    parser = build_formula_parser(
        {"fext": "http://www.bde.es/xbrl/func/external-functions"},
        custom_functions=definitions,
        expression_hints=("fext:atributo('TO_TIP_ENT')",),
    )

    parser.parse("fext:atributo('TO_TIP_ENT')")
