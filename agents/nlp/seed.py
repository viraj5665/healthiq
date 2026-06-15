"""
Synthetic clinical notes for testing.

⚠  SYNTHETIC DATA — NOT REAL PATIENT RECORDS.
   Notes are entirely fabricated for pipeline testing purposes.
   Patient names are intentionally omitted; references use [ANONYMIZED].
"""

from datetime import datetime, timezone

SYNTHETIC_NOTES = [
    {
        "fhir_id": "131707439",
        "note_type": "progress_note",
        "note_date": "2024-03-05T10:30:00Z",
        "note_text": """\
⚠  SYNTHETIC NOTE — FOR TESTING PURPOSES ONLY

Date: 2024-03-05
Encounter Type: Outpatient Diabetes Follow-up

S: [ANONYMIZED] presents for routine diabetes management follow-up. Reports \
generally good compliance with medications but fasting blood glucose readings \
at home averaging 180–220 mg/dL. Denies hypoglycemic episodes, chest pain, \
or shortness of breath.

O: BP 138/88 mmHg, HR 76 bpm, Weight 187 lbs. HbA1c 9.4% (elevated above \
target of <7%). Fasting glucose 268 mg/dL. BMP notable for potassium 3.2 \
mEq/L (mildly low).

A:
1. Type 2 Diabetes Mellitus, uncontrolled (E11.65)
2. Essential hypertension (I10)
3. Hypokalemia (E87.6)

P:
- Continue Metformin 1000 mg twice daily (oral)
- Add Semaglutide 0.5 mg weekly (subcutaneous injection) — new today
- Potassium chloride 20 mEq daily (oral) — new today
- Recheck HbA1c in 3 months
- Referred to certified diabetes education program
- Follow up in 6 weeks
""",
    },
    {
        "fhir_id": "131896579",
        "note_type": "consultation",
        "note_date": "2024-04-10T14:00:00Z",
        "note_text": """\
⚠  SYNTHETIC NOTE — FOR TESTING PURPOSES ONLY

Date: 2024-04-10
Encounter Type: Cardiology Consultation

CC: Elevated blood pressure and palpitations for 2 weeks.

S: [ANONYMIZED] is a 49-year-old male with known hypertension presenting with \
intermittent palpitations occurring 3–4 times daily, lasting 30–60 seconds each. \
Denies chest pain, syncope, or dyspnea. Currently taking Lisinopril 10 mg daily.

O: BP 152/96 mmHg, HR 88 bpm irregular. EKG: atrial fibrillation with \
controlled ventricular response. Echocardiogram: EF 55%, mild left atrial \
enlargement. Potassium 6.2 mEq/L (hyperkalemia).

A:
1. New onset atrial fibrillation (I48.0)
2. Essential hypertension, poorly controlled (I10)
3. Hyperkalemia (E87.5)

P:
- Start Metoprolol succinate 25 mg once daily (oral) for rate control
- Start Apixaban 5 mg twice daily (oral) for anticoagulation
- Discontinue Lisinopril due to hyperkalemia; start Amlodipine 5 mg once daily (oral)
- Holter monitor ordered
- Cardiology follow-up in 2 weeks
- Patient educated on AF warning signs
""",
    },
    {
        "fhir_id": "132080157",
        "note_type": "progress_note",
        "note_date": "2026-05-30T09:00:00Z",
        "note_text": """\
⚠  SYNTHETIC NOTE — FOR TESTING PURPOSES ONLY

Date: 2026-05-30
Encounter Type: Post-operative Follow-up, Day 5

Procedure performed 2026-05-25: Laparoscopic appendectomy.

S: [ANONYMIZED] reports pain improving to 2/10 at incision sites. No fever. \
Tolerating regular diet. Normal bowel function resumed 2026-05-29. No signs of \
surgical site infection.

O: Afebrile (37.1 °C). Incisions healing well — no erythema or discharge. \
Abdomen soft and non-tender. WBC 8.2 (normal). CRP 12 mg/L (mildly elevated).

A:
1. Status post laparoscopic appendectomy (Z87.39)
2. Acute appendicitis, resolved (K37)

P:
- Discontinue Cephalexin 500 mg four times daily (completed 5-day course)
- Continue acetaminophen 500 mg every 6 hours as needed for pain (oral)
- Resume normal activity in 1 week
- Return to work clearance provided
- Follow up in 2 weeks or sooner if fever >38.5 °C or worsening pain
""",
    },
    {
        "fhir_id": "132080095",
        "note_type": "progress_note",
        "note_date": "2026-06-01T11:00:00Z",
        "note_text": """\
⚠  SYNTHETIC NOTE — FOR TESTING PURPOSES ONLY

Date: 2026-06-01
Encounter Type: Annual Physical Examination

S: [ANONYMIZED] is a 31-year-old male presenting for annual physical. No \
current complaints. Non-smoker, occasional alcohol use. No known chronic \
conditions.

O: BP 118/74 mmHg, HR 68 bpm regular, BMI 23.1. HEENT: normal. \
Cardiovascular: regular rate and rhythm, no murmurs. Lungs: clear to \
auscultation bilaterally. Abdomen: soft, non-tender.

Laboratory (today): Total cholesterol 185 mg/dL, HDL 58 mg/dL, LDL 108 \
mg/dL, Triglycerides 95 mg/dL. Fasting glucose 94 mg/dL. TSH 2.3 mIU/L. \
CBC: within normal limits.

A:
1. Routine adult health maintenance (Z00.00)

P:
- No medications indicated at this time
- Flu vaccine administered today
- Colorectal cancer screening discussion deferred (age <45)
- Follow up in 1 year
""",
    },
    {
        "fhir_id": "132080174",
        "note_type": "emergency_note",
        "note_date": "2026-06-10T03:15:00Z",
        "note_text": """\
⚠  SYNTHETIC NOTE — FOR TESTING PURPOSES ONLY

Date: 2026-06-10
Encounter Type: Emergency Department Visit

CC: Substernal chest pain, onset 3 hours prior to arrival.

S: [ANONYMIZED] is a 32-year-old male with no prior cardiac history presenting \
with substernal chest pressure rated 7/10, radiating to the left arm. Associated \
diaphoresis and nausea. Father had MI at age 52.

O: BP 148/92 mmHg, HR 102 bpm, RR 20, SpO2 97% on room air. EKG: ST elevation \
in leads II, III, aVF — consistent with inferior STEMI. Troponin I: 2.8 ng/mL \
(elevated; upper limit of normal 0.04 ng/mL).

A:
1. ST-elevation myocardial infarction, inferior wall (I21.19)
2. Acute chest pain (R07.9)

P:
- Aspirin 325 mg chewed immediately
- Heparin 5000 units IV bolus administered
- Clopidogrel 600 mg loading dose (oral)
- Cardiac catheterization lab activated (target door-to-balloon <90 minutes)
- Transfer to cardiac ICU post-procedure
- Cardiology consult placed
""",
    },
]


def seed_synthetic_notes(db) -> list[str]:
    """
    Insert synthetic notes for existing patients.
    Returns list of inserted note IDs (as strings).
    Idempotent: skips notes already present (same patient + note_date).
    """
    from api.models.clinical_note import ClinicalNote
    from api.models.patient import Patient

    inserted_ids: list[str] = []
    for spec in SYNTHETIC_NOTES:
        patient = db.query(Patient).filter_by(fhir_id=spec["fhir_id"]).first()
        if not patient:
            continue

        note_date = datetime.fromisoformat(spec["note_date"].replace("Z", "+00:00"))

        existing = (
            db.query(ClinicalNote)
            .filter_by(patient_id=patient.id, note_date=note_date)
            .first()
        )
        if existing:
            inserted_ids.append(str(existing.id))
            continue

        note = ClinicalNote(
            patient_id=patient.id,
            note_type=spec["note_type"],
            note_date=note_date,
            note_text=spec["note_text"],
            is_synthetic=True,
        )
        db.add(note)
        db.flush()
        inserted_ids.append(str(note.id))

    db.commit()
    return inserted_ids
