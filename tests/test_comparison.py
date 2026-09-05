"""Unit tests for core.comparison — the main QC engine."""
import pytest
from core.comparison import compare_versions

EN = (
    "General Rajesh Kumar Verma visited Pune Military Academy on 15 January 2026. "
    "The General reviewed 250 cadets. The inspection covered 3 training wings."
)
HI = (
    "जनरल राजेश कुमार वर्मा ने 15 जनवरी 2026 को पुणे मिलिटरी एकेडमी का दौरा किया। "
    "जनरल ने 250 कैडेट्स की समीक्षा की। निरीक्षण में 3 प्रशिक्षण विंग शामिल थे।"
)
MR = (
    "जनरल राजेश कुमार वर्मा यांनी 15 जानेवारी 2026 रोजी पुणे मिलिटरी अकादमीला भेट दिली. "
    "जनरलांनी 250 कॅडेट्सची पाहणी केली. तपासणीमध्ये 3 प्रशिक्षण विंग होते."
)

VERSIONS  = {"English": EN, "Hindi": HI, "Marathi": MR}
NAMES     = ["General Rajesh Kumar Verma"]
DATES     = ["15 January 2026"]
NUMBERS   = ["250", "3"]
LOCATIONS = ["Pune"]


class TestCleanRelease:
    """Clean release should produce no findings."""

    def test_no_findings(self):
        r = compare_versions(VERSIONS, NAMES, DATES, NUMBERS, LOCATIONS)
        assert r.findings == []

    def test_qc_score_100(self):
        r = compare_versions(VERSIONS, NAMES, DATES, NUMBERS, LOCATIONS)
        assert r.qc_score == 100

    def test_all_pass(self):
        r = compare_versions(VERSIONS, NAMES, DATES, NUMBERS, LOCATIONS)
        assert all(s == "PASS" for s in r.lang_status.values())

    def test_facts_counted(self):
        r = compare_versions(VERSIONS, NAMES, DATES, NUMBERS, LOCATIONS)
        # 3 langs × (2 numbers + 1 date + 1 name + 1 location) = 15
        assert r.total_facts_checked == 15


class TestNumberErrors:
    """Missing or changed numbers should generate CRITICAL findings."""

    def test_missing_number_hindi(self):
        bad_hi = HI.replace("250", "", 1)
        r = compare_versions({"English": EN, "Hindi": bad_hi, "Marathi": MR}, NAMES, DATES, NUMBERS)
        assert any(f.language == "Hindi" and f.fact_type == "number" and f.expected == "250"
                   for f in r.findings)

    def test_changed_number_marathi(self):
        bad_mr = MR.replace("250", "200", 1)
        r = compare_versions({"English": EN, "Hindi": HI, "Marathi": bad_mr}, NAMES, DATES, NUMBERS)
        assert any(f.language == "Marathi" and f.fact_type == "number" for f in r.findings)

    def test_severity_is_critical(self):
        bad_hi = HI.replace("3", "", 1)
        r = compare_versions({"English": EN, "Hindi": bad_hi, "Marathi": MR}, NAMES, DATES, NUMBERS)
        assert any(f.severity == "CRITICAL" for f in r.findings)

    def test_score_reduced(self):
        bad_hi = HI.replace("250", "", 1)
        r = compare_versions({"English": EN, "Hindi": bad_hi, "Marathi": MR}, NAMES, DATES, NUMBERS)
        assert r.qc_score < 100


class TestDateErrors:
    """Missing or changed dates should generate CRITICAL findings."""

    def test_missing_date_hindi(self):
        import re
        bad_hi = re.sub(r"15 जनवरी 2026", "", HI)
        r = compare_versions({"English": EN, "Hindi": bad_hi, "Marathi": MR}, NAMES, DATES, NUMBERS)
        assert any(f.language == "Hindi" and f.fact_type == "date" for f in r.findings)

    def test_changed_date_marathi(self):
        bad_mr = MR.replace("2026", "2027", 1)
        r = compare_versions({"English": EN, "Hindi": HI, "Marathi": bad_mr}, NAMES, DATES, NUMBERS)
        assert any(f.language == "Marathi" and f.fact_type == "date" for f in r.findings)

    def test_changed_day_hindi(self):
        bad_hi = HI.replace("15 जनवरी", "16 जनवरी", 1)
        r = compare_versions({"English": EN, "Hindi": bad_hi, "Marathi": MR}, NAMES, DATES, NUMBERS)
        assert any(f.language == "Hindi" and f.fact_type == "date" for f in r.findings)


class TestNameErrors:
    """Missing or mismatched names should generate CRITICAL findings."""

    def test_name_removed_hindi(self):
        bad_hi = HI.replace("जनरल राजेश कुमार वर्मा", "", 1)
        r = compare_versions({"English": EN, "Hindi": bad_hi, "Marathi": MR}, NAMES, DATES, NUMBERS, LOCATIONS)
        assert any(f.language == "Hindi" and f.fact_type == "name" for f in r.findings)

    def test_name_changed_marathi(self):
        bad_mr = MR.replace("राजेश", "सुरेश", 1)
        r = compare_versions({"English": EN, "Hindi": HI, "Marathi": bad_mr}, NAMES, DATES, NUMBERS, LOCATIONS)
        # May be flagged as CRITICAL or WARNING depending on fuzzy score
        assert any(f.language == "Marathi" and f.fact_type == "name" for f in r.findings)


class TestLocationErrors:
    """Missing or mismatched locations should generate CRITICAL findings."""

    def test_location_removed_hindi(self):
        bad_hi = HI.replace("पुणे", "", 1)
        r = compare_versions({"English": EN, "Hindi": bad_hi, "Marathi": MR}, NAMES, DATES, NUMBERS, LOCATIONS)
        assert any(f.language == "Hindi" and f.fact_type == "location" for f in r.findings)

    def test_location_changed_marathi(self):
        bad_mr = MR.replace("पुणे", "मुंबई", 1)
        r = compare_versions({"English": EN, "Hindi": HI, "Marathi": bad_mr}, NAMES, DATES, NUMBERS, LOCATIONS)
        assert any(f.language == "Marathi" and f.fact_type == "location" for f in r.findings)


class TestEmptyFacts:
    """Passing empty canonical lists should work without errors."""

    def test_empty_all(self):
        r = compare_versions(VERSIONS, [], [], [])
        assert r.findings == []
        assert r.qc_score == 100

    def test_only_numbers(self):
        r = compare_versions(VERSIONS, [], [], ["250"])
        assert r.total_facts_checked == 3  # 3 languages × 1 number
