<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0" xmlns:model="http://xbrl.org/PWD/2013-MM-DD/table/model">
  <!--
       This stylesheet offers incomplete support for transforming the XML infoset table model format into rendered HTML.
       It is suitable for visualising the test cases, but is not intended to produce aesthetically pleasing HTML.
   -->
  <xsl:output method="html" />
  <xsl:template match="/">
    <html>
      <head>
        <style type="text/css">
          table { 
            border-spacing:0;
            margin-bottom: 24px;
          }

          th {
            background: #eee;
            font-weight: bold;
          }

          th.zHeader {
            background: #ddd;
          }

          th.rowHeader {
            vertical-align: top;
            overflow: visible;
          }

          td, th {
            border-top: 1px solid black;
            border-left: 1px solid black;
            border-bottom: 0;
            border-right: 0;
            white-space: nowrap;
          }

          th.merged-with-above {
            border-top: 0;
          }

          th.merged-with-left {
            border-left: 0;
          }

          th.last-row, td.last-row {
            border-bottom: 1px solid black;
          }

          th.last-col, td.last-col {
            border-right: 1px solid black;
          }
        </style>
      </head>
      <body>
        <xsl:apply-templates select="//model:tableSet"/>
      </body>
    </html>
  </xsl:template>

  <!-- Show a sequence of tables, one for each position in Z starting with zHeaderIdx -->
  <xsl:template name="showTables">
    <xsl:param name="table" />
    <xsl:param name="nDisc" />
    <xsl:param name="nSlices" />
    <xsl:param name="nRows" />
    <xsl:param name="nCols" />
    <xsl:param name="tableHeaderIdx" />
    <xsl:param name="zHeaderIdx" />
    <xsl:param name="content" />
    <xsl:param name="slice" />
    <xsl:param name="disc" />

    <xsl:variable name="tableHeaderLabel" select="$table/../model:headers/model:header[$tableHeaderIdx]/model:label[$disc]" />
    <xsl:variable name="zHeader" select="$table//model:headers[@axis='z']/model:header[$zHeaderIdx]" />
    <xsl:variable name="xHeaders" select="$table//model:headers[@axis='x']/model:header" />
    <xsl:variable name="yHeaders" select="$table//model:headers[@axis='y']/model:header" />

    <xsl:choose>
      <!-- When there's a table header at $tableHeaderIdx, add to content variable and recurse -->
      <xsl:when test="$tableHeaderLabel">
        <xsl:call-template name="showTables">
          <xsl:with-param name="table" select="$table" />
          <xsl:with-param name="nDisc" select="$nDisc" />
          <xsl:with-param name="nSlices" select="$nSlices" />
          <xsl:with-param name="nRows" select="$nRows" />
          <xsl:with-param name="nCols" select="$nCols" />
          <xsl:with-param name="disc" select="$disc" />
          <xsl:with-param name="tableHeaderIdx" select="$tableHeaderIdx + 1" /><!-- Next header -->
          <xsl:with-param name="zHeaderIdx" select="$zHeaderIdx" />
          <xsl:with-param name="slice" select="$slice" />
          <xsl:with-param name="content" select="concat($content,
            substring(', ', 1 div (normalize-space($content) != '')),
            $tableHeaderLabel/text())" />
        </xsl:call-template>
      </xsl:when>

      <!-- When there's a z header at $zHeaderIdx, add to content variable and recurse -->
      <xsl:when test="$zHeader">
        <xsl:for-each select="$zHeader/model:label">
          <xsl:call-template name="showTables">
            <xsl:with-param name="table" select="$table" />
            <xsl:with-param name="nDisc" select="$nDisc" />
            <xsl:with-param name="nSlices" select="$nSlices" />
            <xsl:with-param name="nRows" select="$nRows" />
            <xsl:with-param name="nCols" select="$nCols" />
            <xsl:with-param name="disc" select="$disc" />
            <xsl:with-param name="tableHeaderIdx" select="$tableHeaderIdx" />
            <xsl:with-param name="zHeaderIdx" select="$zHeaderIdx + 1" /><!-- Next header -->
            <xsl:with-param name="slice" select="($slice - 1) * last() + position()" />
            <xsl:with-param name="content" select="concat($content,
              substring(', ', 1 div (normalize-space($content) != '')),
              text())" />
          </xsl:call-template>
        </xsl:for-each>
      </xsl:when>

      <!-- Otherwise, content contains all headers, so render the table -->
      <xsl:otherwise>

        <table>
          <xsl:if test="normalize-space($content) != ''">
            <tr>
              <th class="zHeader last-col">
                <xsl:attribute name="colspan"><xsl:value-of select="$nCols + count($yHeaders)" /></xsl:attribute>
                <xsl:value-of select="$content" />
              </th>
            </tr>
          </xsl:if>

          <!-- X Header -->
          <xsl:for-each select="$xHeaders">
            <tr>
              <xsl:if test="position() = 1">
                <th>
                  <xsl:attribute name="rowspan"><xsl:value-of select="count(../model:header)" /></xsl:attribute>
                  <xsl:attribute name="colspan"><xsl:value-of select="count($yHeaders)" /></xsl:attribute>
                  <xsl:value-of select="$table/@label" />
                </th>
              </xsl:if>
              <xsl:for-each select="model:label">
                <th>
                  <xsl:variable name="class" select="normalize-space(concat(substring('last-col', 1 div (position()=last())), ' ', substring('merged-with-above', 1 div (@rollup='true'))))" />
                  <xsl:if test="$class">
                    <xsl:attribute name="class"><xsl:value-of select="$class" /></xsl:attribute>
                  </xsl:if>
                  <xsl:if test="@span">
                    <xsl:attribute name="colspan"><xsl:value-of select="@span" /></xsl:attribute>
                  </xsl:if>
                  <xsl:value-of select="text()" />
                </th>
              </xsl:for-each>
            </tr>
          </xsl:for-each>

          <xsl:call-template name="showRow">
            <xsl:with-param name="table" select="$table" />
            <xsl:with-param name="nCols" select="$nCols" />
            <xsl:with-param name="nRows" select="$nRows" />
            <xsl:with-param name="nSlices" select="$nSlices" />
            <xsl:with-param name="row" select="1" />
            <xsl:with-param name="slice" select="$slice" />
            <xsl:with-param name="disc" select="$disc" />
          </xsl:call-template>
        </table>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="model:tableSet">
    <xsl:variable name="tableSet" select="." />
    <xsl:variable name="lastLabelInFirstHeader" select="($tableSet/model:headers/model:header)[1]/model:label[last()]" />
    <xsl:variable name="nDisc" select="sum($lastLabelInFirstHeader/preceding-sibling::model:label/@span) +
      count($lastLabelInFirstHeader/preceding-sibling::model:label[not(@span)]) +
      sum($lastLabelInFirstHeader/@span) +
      count($lastLabelInFirstHeader[not(@span)])"/>
    <xsl:call-template name="showSlices">
      <xsl:with-param name="tableSet" select="$tableSet" />
      <xsl:with-param name="nDisc" select="$nDisc" />
      <xsl:with-param name="disc" select="1" />
    </xsl:call-template>
  </xsl:template>

  <xsl:template name="showSlices">
    <xsl:param name="tableSet" />
    <xsl:param name="nDisc" />
    <xsl:param name="disc" />

    <xsl:variable name="table" select="$tableSet/model:table[$disc]" />

    <!-- x, y, z cardinality for this discriminator value -->
    <xsl:variable name="nRows" select="count(($table//model:cells/descendant-or-self::model:cells[@axis='y'])[1]/*)" />
    <xsl:variable name="nCols" select="count(($table//model:cells/descendant-or-self::model:cells[@axis='x'])[1]/*)" />
    <xsl:variable name="nSlices" select="count(($table//model:cells/descendant-or-self::model:cells[@axis='z'])[1]/*)" />

    <xsl:call-template name="showTables">
      <xsl:with-param name="table" select="$table" />
      <xsl:with-param name="nDisc" select="$nDisc" />
      <xsl:with-param name="nSlices" select="$nSlices" />
      <xsl:with-param name="nRows" select="$nRows" />
      <xsl:with-param name="nCols" select="$nCols" />
      <xsl:with-param name="tableHeaderIdx" select="1" />
      <xsl:with-param name="zHeaderIdx" select="1" />
      <xsl:with-param name="disc" select="$disc" />
      <xsl:with-param name="slice" select="1" />
      <xsl:with-param name="content" select="''" />
    </xsl:call-template>

    <xsl:if test="$disc &lt; $nDisc">
      <xsl:call-template name="showSlices">
        <xsl:with-param name="tableSet" select="$tableSet" />
        <xsl:with-param name="nDisc" select="$nDisc" />
        <xsl:with-param name="disc" select="$disc + 1" />
      </xsl:call-template>
    </xsl:if>
  </xsl:template>

  <!-- Show the cell at ($col, $row, $slice, $disc) then call the showCell for the next cell in the row, until the end of the row -->
  <xsl:template name="showCell">
    <xsl:param name="table" />
    <xsl:param name="nCols" />
    <xsl:param name="nRows" />
    <xsl:param name="nSlices" />
    <xsl:param name="nDisc" />
    <xsl:param name="col" />
    <xsl:param name="row" />
    <xsl:param name="slice" />
    <xsl:param name="disc" />

    <!-- Find the cell with coordinates (x, y, z, disc) == ($col, $row, $slice, $disc)
         Do this by finding a cell which is - or is under - the $col'th child of a cells element with disposition x
         and is also a cell which is - or is under - the $row'th child of a cells element with disposition y
         and is also a cell which is - or is under - the $slice'th child of a cells element with disposition z (or there are no slices)
         -->
    <xsl:variable name="cell" select="$table//model:cell[
      ($table//model:cells[@axis='x']/*[$col]/descendant-or-self::model:cell = .)
      and
      ($table//model:cells[@axis='y']/*[$row]/descendant-or-self::model:cell = .)
      and
      ($table//model:cells[@axis='z']/*[$slice]/descendant-or-self::model:cell = . or $nSlices = 0)
      ]" />

    <td>
      <!-- The CSS class should include last-col and last-row as appropriate.
           substring(s, 1 div (expr)) yields s if expr is true and the empty string otherwise.
           -->
      <xsl:variable name="class" select="normalize-space(concat(substring('last-col', 1 div ($col=$nCols)), ' ', substring('last-row', 1 div ($row=$nRows))))"/>
      <xsl:if test="$class">
        <xsl:attribute name="class"><xsl:value-of select="$class" /></xsl:attribute>
      </xsl:if>
      <xsl:choose>
        <xsl:when test="normalize-space($cell/text())">
          <xsl:value-of select="$cell/text()" />
        </xsl:when>
        <xsl:otherwise>&#160;</xsl:otherwise>
      </xsl:choose>
    </td>

    <!-- Next cell -->
    <xsl:if test="$col &lt; $nCols">
      <xsl:call-template name="showCell">
        <xsl:with-param name="table" select="$table" />
        <xsl:with-param name="nCols" select="$nCols" />
        <xsl:with-param name="nRows" select="$nRows" />
        <xsl:with-param name="nSlices" select="$nSlices" />
        <xsl:with-param name="disc" select="$disc" />
        <xsl:with-param name="slice" select="$slice" />
        <xsl:with-param name="row" select="$row" />
        <xsl:with-param name="col" select="$col + 1" />
      </xsl:call-template>
    </xsl:if>
  </xsl:template>

  <!-- Show the row at $row, then call the showRow for the next row in the table, until the end of the table -->
  <xsl:template name="showRow">
    <xsl:param name="table" />
    <xsl:param name="nCols" />
    <xsl:param name="nRows" />
    <xsl:param name="nSlices" />
    <xsl:param name="row" />
    <xsl:param name="slice" />
    <xsl:param name="disc" />

    <tr>
      <!-- yHeaderLabels = All labels in the header for disposition y -->
      <xsl:variable name="yHeaderLabels" select="$table//model:headers[@axis='y']/model:header/model:label" />
      <!-- yHeaderLabelsInRow = Labels in row $row of the y header. The index of a given label is the sum of the spans of the preceding labels in the same header. -->
      <xsl:variable name="yHeaderLabelsInRow" select="$yHeaderLabels[sum(preceding-sibling::model:label/@span) + count(preceding-sibling::model:label[not(@span)]) + 1 = $row]" />
      <!-- Show cells for row header -->
      <xsl:for-each select="$yHeaderLabelsInRow">
        <th>
          <xsl:if test="@span">
            <xsl:attribute name="rowspan"><xsl:value-of select="@span" /></xsl:attribute>
          </xsl:if>

          <xsl:variable name="isLastRow" select="@span &gt; 1 and $row + @span - 1=$nRows or $row=$nRows" />
          <!-- The CSS class should include last-row as appropriate, and merged-with-left if this is a rollup cell.
               substring(s, 1 div (expr)) yields s if expr is true and the empty string otherwise.
           -->
          <xsl:variable name="class" select="normalize-space(concat('rowHeader', ' ', substring('last-row', 1 div ($isLastRow)), ' ', substring('merged-with-left', 1 div (@rollup='true'))))" />
          <xsl:if test="$class">
            <xsl:attribute name="class"><xsl:value-of select="$class" /></xsl:attribute>
          </xsl:if>
          <xsl:value-of select="text()" />
        </th>
      </xsl:for-each>

      <!-- Show cells for data -->
      <xsl:call-template name="showCell">
        <xsl:with-param name="table" select="$table" />
        <xsl:with-param name="nCols" select="$nCols" />
        <xsl:with-param name="nRows" select="$nRows" />
        <xsl:with-param name="nSlices" select="$nSlices" />
        <xsl:with-param name="disc" select="$disc" />
        <xsl:with-param name="slice" select="$slice" />
        <xsl:with-param name="row" select="$row" />
        <xsl:with-param name="col" select="1" />
      </xsl:call-template>
    </tr>

    <!-- Next row -->
    <xsl:if test="$row &lt; $nRows">
      <xsl:call-template name="showRow">
        <xsl:with-param name="table" select="$table" />
        <xsl:with-param name="nCols" select="$nCols" />
        <xsl:with-param name="nRows" select="$nRows" />
        <xsl:with-param name="nSlices" select="$nSlices" />
        <xsl:with-param name="row" select="$row + 1" />
        <xsl:with-param name="slice" select="$slice" />
        <xsl:with-param name="disc" select="$disc" />
      </xsl:call-template>
    </xsl:if>
  </xsl:template>
</xsl:stylesheet>
