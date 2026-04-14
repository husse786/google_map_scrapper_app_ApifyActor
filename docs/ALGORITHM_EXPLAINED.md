# ALGORITHM EXPLANATION: Data Cleaning Module

## How the Scoring & Deduplication Works

---

## Overview

The `DataCleaner` module takes **enriched data** (1 customer = N Google results) and **automatically picks the right match** using a multi-stage decision tree. The goal: **maximize automatic confidence while flagging ambiguous cases for manual review**.

---

## Decision Tree — 5 Stages

```yaml
INPUT: Customer record with 1+ Google results
│
├─ STAGE 1: Empty Result?
│  ├─ YES → _erneut_crawlen.csv (re-crawl later)
│  └─ NO  → continue
│
├─ STAGE 2: Postal Code (PLZ) Match?
│  ├─ NO  → _aussortiert.csv (rejected)
│  └─ YES → continue
│
├─ STAGE 3: Exactly 1 Result Left?
│  ├─ YES → _eindeutig.csv (unique: OK)
│  └─ NO  → continue to Stage 4
│
├─ STAGE 4: The "Weiche" — Street in Input?
│  ├─ YES (Szenario B: Street matching first)
│  │  ├─ 0 street matches   → _zur_pruefung.csv (review)
│  │  ├─ 1 street match     → _eindeutig.csv (unique: OK Strasse)
│  │  └─ 2+ street matches  → Stage 5 (title scoring on matches)
│  │
│  └─ NO (Szenario A: Direct to title scoring)
│     └─ Stage 5 (all results)
│
└─ STAGE 5: Title Scoring
   ├─ IF 1+ result scored ≥80
   │  ├─ EXACTLY 1 hit ≥80   → _eindeutig.csv (OK Score)
   │  └─ 2+ hits ≥80         → _zur_pruefung.csv (review: ambiguous)
   │
   └─ IF NO result ≥80 (Check Dynamic Threshold)
      ├─ Gap between 1st & 2nd ≥30 → _eindeutig.csv (OK Dynamisch)
      └─ Gap < 30 or 1 result      → _zur_pruefung.csv (review)
```

---

## Stage Details

### STAGE 1: Empty Results

**Purpose:** Detect API failures (Google Maps returned nothing)

**Rule:** A result is **empty** if ALL of these fields are blank:

- `title`
- `address`
- `street`
- `placeId`

**Action:** Save to `_erneut_crawlen.csv` (format: same as input, can be re-crawled immediately)

---

### STAGE 2: Postal Code Filter

**Purpose:** Remove results from completely wrong cities

**Rule:**

```md
input_plz = "5620"
google_plz = "8000"

→ MISMATCH → _aussortiert.csv (rejected)
```

**Edge Case:** If either PLZ is missing, **pass through** (benefit of doubt—don't lose data because Google didn't return a PLZ).

---

### STAGE 3: Single Result Shortcut

**Purpose:** Fast path for unambiguous cases

**Rule:** If only 1 result passed Stages 1–2:

```yaml
→ _eindeutig.csv with qualitaet = "OK"
```

---

### STAGE 4: The "Weiche" (Switch) — Street Matching

**Purpose:** If the input includes a street address, use it as a pre-filter before title scoring.

#### How to detect street in input?

The `SearchString` format is: `Title, Strasse+Nr, PLZ Stadt`

Example: `"Denner, Hauptstrasse 5, 5620 Bremgarten"`

Extract **2nd comma-separated part**: `"Hauptstrasse 5"` ← If non-empty & not just a number, this is a street.

#### Szenario B: Street Matching

If street is present:

1. **Normalize** both input street and Google street (see Normalization section)
2. **Extract street name & house number** separately
3. **Compare**:
   - Street names must match (>90% fuzzy match)
   - House numbers: if both present, must be exact. Otherwise, street name match is enough.
4. **Segregate**:
   - ✅ Matches → proceed to title scoring
   - ❌ Mismatches → `_aussortiert.csv` (rejected: Strasse mismatch)

**If 0 matches:** → `_zur_pruefung.csv` (no streets match, too risky to auto-decide)

**If 1 match:** → `_eindeutig.csv` (OK: Strasse) — done!

**If 2+ matches:** → Pass to title scoring.

#### Szenario A: No Street

If no street in input, **all results** go directly to title scoring (Stage 5).

---

### STAGE 5: Title Scoring

**Purpose:** Use fuzzy matching to score how similar the input name is to each Google result title.

#### Normalization (applied to both sides before comparison)

```md
Examples:
"Coop Detailhandels AG"  →  "coop"
"Bäckerei Müller"        →  "baeckerei mueller"
"Spar-King GmbH"         →  "spar king gmbh"
```

Steps:

1. Lowercase
2. Replace umlauts: `ä→ae`, `ö→oe`, `ü→ue`
3. Handle French accents: `é→e`, `è→e`, `à→a`
4. Expand street abbreviations: `Str.→Strasse`, `Pl.→Platz`
5. Replace hyphens/slashes with spaces
6. Collapse multiple spaces
7. Strip legal suffixes: `AG`, `GmbH`, `Inc`, `Ltd`, `Co`, `KG`, etc.

#### Scoring Formula

For each result:

```yaml
1. Extract "search_name" from SearchString (part before first comma)
   Example: "Coop Satellite" from "Coop Satellite, Main St 5, 5620"

2. Normalize it → extract first word
   "coop satellite" → first word = "coop"

3. Determine if first word is "generic" or "brand"
   Generic words: restaurant, cafe, hotel, metzgerei, kiosk, etc.
   → Use 30% first-word match + 70% full-title match (full name matters more)
   Brand words: Coop, Migros, Denner, Spar, etc.
   → Use 70% first-word match + 30% full-title match (brand is key indicator)

4. Calculate scores:
   core_score = fuzz.ratio(search_first_word, google_first_word)
                "coop" vs "coop" = 100
                "coop" vs "denner" = low
   
   full_score = fuzz.token_set_ratio(search_name, google_title)
                "coop satellite" vs "satellite coop zurich" = high (order-independent)

5. Weighted score:
   score = (weight_first × core_score) + (weight_full × full_score)
   Example (brand): (0.7 × 100) + (0.3 × 95) = 98.5
```

#### Decision Logic

```yaml
IF  1 or more results scored ≥80:
    ├─ IF exactly 1 result ≥80:
    │  → _eindeutig.csv (OK: Score)
    │
    └─ IF 2+ results ≥80:
       → _zur_pruefung.csv (ambiguous: multiple high hits)

ELSE (NO result ≥80):
    ├─ IF 2+ results AND gap(1st - 2nd) ≥ 30:
    │  → _eindeutig.csv (OK: Dynamisch)
    │  Reasoning: 1st is clearly better than 2nd
    │
    └─ ELSE:
       → _zur_pruefung.csv (no clear winner)
```

---

## Output Files

| File | Meaning | Row Count | Use Case |
| ------ | --------- | ----------- | ---------- |
| `_eindeutig.csv` | Auto-accepted matches | ← minimize false positives | Automatically import into system |
| `_zur_pruefung.csv` | Ambiguous cases | User decides | Manual review batch |
| `_aussortiert.csv` | Rejected matches | Noise | Optional inspection (why were they wrong?) |
| `_erneut_crawlen.csv` | Empty API results | Re-try | Run through Step 1 again with same input |

---

## Key Strengths

✅ **Multi-stage filtering** prevents false positives  
✅ **Street matching** (Stage 4) eliminates wrong branches/cities before title scoring  
✅ **Weighted scoring** adapts for brand vs. generic names  
✅ **Dynamic threshold** catches borderline cases where manual review is worth it  
✅ **Normalization** handles umlauts, accents, abbreviations  
✅ **Benefit-of-doubt** design (missing PLZ doesn't reject, only exact mismatches do)

---

## Example Walkthrough

### Input

```md

SearchString: "Denner, Hauptstrasse 5, 5620 Bremgarten"
PLZ: "5620"
KundenNr: "K001"
Google Results:
  1. title="Denner Markt", street="Hauptstrasse 5", plz="5620"     ← Correct match
  2. title="Denner Shop", street="Dorfstrasse 10", plz="5620"     ← Wrong street
  3. title="Spar", street="Bahnhofstrasse", plz="8000"            ← Wrong PLZ
```

### Execution

| Stage | Filter | Result 1 | Result 2 | Result 3 |
| ------- | -------- | ---------- | ---------- | ---------- |
| 1 | Empty? | ✅ has data | ✅ has data | ✅ has data |
| 2 | PLZ ✓? | ✅ 5620=5620 | ✅ 5620=5620 | ❌ 5620≠8000 |
| — | — | continue | continue | → rejected |
| 4 | Street? | ✅ Hauptstr match | ❌ Dorfstr no | — |
| — | — | → unique | → rejected | — |

### Output

```md
_eindeutig.csv:
  Denner Markt, 5620, Bremgarten  (qualitaet: "OK (Strasse)")

_aussortiert.csv:
  Denner Shop, 5620, ...          (qualitaet: "AUSSORTIERT (Strasse)")
  Spar, 8000, ...                 (qualitaet: "AUSSORTIERT (PLZ)")
```

---

## Configuration

**Tunable parameters** (`config.py`):

- `DYNAMIC_THRESHOLD_GAP = 30` ← minimum score gap between #1 and #2 for auto-accept

**Hard-coded limits**:

- Score threshold: `80` (≥80 = high confidence)
- Street name match: `>90%` fuzzy ratio
