"""Unit tests for QName — equality, hashing, prefix handling, from_clark, __str__."""

from bde_xbrl_editor.taxonomy.models import QName

NS = "http://www.xbrl.org/2003/instance"
NS2 = "http://www.example.com/ns"


class TestQNameEquality:
    def test_equal_same_ns_and_local(self):
        assert QName(NS, "Assets") == QName(NS, "Assets")

    def test_prefix_ignored_in_equality(self):
        assert QName(NS, "Assets", prefix="xbrli") == QName(NS, "Assets", prefix=None)

    def test_different_local_not_equal(self):
        assert QName(NS, "Assets") != QName(NS, "Liabilities")

    def test_different_ns_not_equal(self):
        assert QName(NS, "Assets") != QName(NS2, "Assets")

    def test_same_prefix_different_ns_not_equal(self):
        q1 = QName(NS, "item", prefix="xbrli")
        q2 = QName(NS2, "item", prefix="xbrli")
        assert q1 != q2


class TestQNameHashing:
    def test_hashable(self):
        q = QName(NS, "Assets")
        assert hash(q) is not None

    def test_same_qname_same_hash(self):
        assert hash(QName(NS, "Assets")) == hash(QName(NS, "Assets"))

    def test_prefix_ignored_in_hash(self):
        assert hash(QName(NS, "Assets", "xbrli")) == hash(QName(NS, "Assets", None))

    def test_usable_as_dict_key(self):
        d = {QName(NS, "Assets"): 42}
        assert d[QName(NS, "Assets")] == 42

    def test_usable_in_set(self):
        s = {QName(NS, "A"), QName(NS, "A"), QName(NS, "B")}
        assert len(s) == 2


class TestQNameFromClark:
    def test_clark_with_namespace(self):
        q = QName.from_clark("{http://www.xbrl.org/2003/instance}Assets")
        assert q.namespace == "http://www.xbrl.org/2003/instance"
        assert q.local_name == "Assets"
        assert q.prefix is None

    def test_clark_with_prefix(self):
        q = QName.from_clark("{http://www.xbrl.org/2003/instance}Assets", prefix="xbrli")
        assert q.prefix == "xbrli"

    def test_clark_no_namespace(self):
        q = QName.from_clark("simpleLocal")
        assert q.namespace == ""
        assert q.local_name == "simpleLocal"

    def test_round_trip(self):
        original = QName(NS, "Assets", prefix="xbrli")
        clark = f"{{{original.namespace}}}{original.local_name}"
        recovered = QName.from_clark(clark, prefix="xbrli")
        assert recovered == original


class TestQNameStr:
    def test_str_with_prefix(self):
        assert str(QName(NS, "Assets", prefix="xbrli")) == "xbrli:Assets"

    def test_str_without_prefix(self):
        assert str(QName(NS, "Assets")) == f"{{{NS}}}Assets"

    def test_str_empty_namespace_no_prefix(self):
        assert str(QName("", "local")) == "{}local"
