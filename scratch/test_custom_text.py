import sys
sys.path.insert(0, '.')
from core.source_extraction import extract_canonical_facts
from core.entity_matching import load_aliases_db
from core.location_matching import load_location_aliases
from core.translation import RealTranslationProvider, set_provider, translate
from core.comparison import compare_versions

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

text = (
    "Colonel Vikram Singh Rathore, Commanding Officer of the 5th Battalion stationed at Jodhpur, "
    "conducted a comprehensive welfare review of 320 jawans and their families on 22 August 2026. "
    "The event was attended by Brigadier Sanjay Mehta from the Western Command Headquarters. "
    "A total of 14 grievances were addressed on-site, with 6 cases referred to the medical board "
    "at the Military Hospital in Jodhpur. The battalion achieved a fitness rating of 92 percent, "
    "the highest in the past 3 years. The next review is scheduled for 15 December 2026 at Bikaner Cantonment."
)

print("=== STEP 1: EXTRACTING FACTS ===")
aliases_db  = load_aliases_db()
loc_aliases = load_location_aliases()
facts = extract_canonical_facts(text, aliases_db, loc_aliases)
print(f"Names    : {[f.canonical_value for f in facts['names']]}")
print(f"Numbers  : {[f.canonical_value for f in facts['numbers']]}")
print(f"Dates    : {[f.canonical_value for f in facts['dates']]}")
print(f"Locations: {[f.canonical_value for f in facts['locations']]}")

print()
print("=== OPSEC TAGS ===")
for f in facts["all"]:
    print(f"  {f.fact_id} | {f.type.upper():<10} | {f.criticality:<8} | {f.canonical_value:<30} | {f.opsec_tags}")

print()
print("=== STEP 2: TRANSLATING (Google Translate) ===")
provider = RealTranslationProvider()
set_provider(provider)
hi = translate(text, "English", "Hindi")
mr = translate(text, "English", "Marathi")
print(f"Hindi   ({len(hi)} chars): {hi[:100]}...")
print(f"Marathi ({len(mr)} chars): {mr[:100]}...")

print()
print("=== STEP 3: QC CHECK ===")
versions = {"English": text, "Hindi": hi, "Marathi": mr}
result = compare_versions(
    versions=versions,
    canonical_names=[f.canonical_value for f in facts["names"]],
    canonical_dates=[f.source_text     for f in facts["dates"]],
    canonical_numbers=[f.canonical_value for f in facts["numbers"]],
    canonical_locations=[f.canonical_value for f in facts["locations"]],
)
print(f"QC Score : {result.qc_score}/100")
print(f"Status   : {result.overall_status}")
print(f"Findings : {len(result.findings)}")
for lang, status in result.lang_status.items():
    print(f"  {lang}: {status}")
