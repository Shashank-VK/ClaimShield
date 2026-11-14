# Research source for insurance_knowledge.json v2

- **What:** Gemini Deep Research report, "Indian Retail Health Insurance Reference Guide for Hospital Help Desks and TPA Operations"
- **Run:** 14 Nov 2026, plan approved 12:17 IST, completed 12:27 IST, on shashank's Gemini account (51)
- **Full report (verbatim, in his Gemini):** https://gemini.google.com/app/5f03f7455a6a7113
- **Brief:** the five areas in the cs-012 task (choosing a policy, reimbursement, cashless, denial patterns by insurer/treatment, appeals)
- **Primary sources the report rests on:** IRDAI Master Circular on Health Insurance Business (29 May 2024), IRDAI PPHI Master Circular (5 Sep 2024), GIC Cashless Everywhere (24 Jan 2024), NHCX/ABDM docs, insurer policy wordings (Star, Bajaj General, HDFC ERGO, ICICI Lombard, Niva Bupa, Care), advisor compilations of IRDAI disclosures (Ditto, Nyvo — figures diverge by methodology; the JSON records them as advisor-compiled 3-year averages), published Ombudsman/Consumer Commission orders.

## Load-bearing facts distilled into the JSON

- Statutory (IRDAI 2024): cashless pre-auth decision in 1 hour; final discharge authorisation in 3 hours (delay beyond 3h → extra stay charges borne by the insurer from shareholders' funds); reimbursement settlement within 15 days of complete documents, else penal interest at RBI Bank Rate + 2% automatically; grievance resolution by insurer GRO within 14 days; PED waiting period capped at 36 months; 60-month moratorium bars non-disclosure challenges except proven fraud; Ombudsman free, claims up to Rs.50 lakh, award within 3 months, binding on insurer (30-day compliance or Rs.5,000/day).
- Insurer metrics (3-yr advisor compilations): HDFC ERGO CSR 97.61%, complaints 8.87/10k, network 16,000+; Bajaj General (formerly Bajaj Allianz) CSR 95.63%, complaints 3.85/10k (lowest), network 12,600+; Care CSR 95.45%, complaints 42.67/10k; Niva Bupa CSR 92.92%, complaints 37.13/10k; Star CSR 88.63%, complaints 54.04/10k (highest); ICICI Lombard CSR 86.81%, complaints 15.05/10k.
- Bajaj: Health Care Supreme = no room caps/sub-limits/co-pay; Health Guard = 1%-of-SI room caps and sub-limits (cataract 20% of SI up to Rs.1L/eye on Platinum); both exclude domiciliary.
- Star: dengue/fever OPD-manageable disputes recur in Ombudsman/Commission orders; Assure 1%-of-SI room cap at Rs.5L SI; 10% co-pay if entry age 61+; cataract cap ~Rs.40k on Rs.10L templates.
- Niva Bupa: Rs.1 lakh per-claim modern/robotic cap on ReAssure lines (Black/Elite exempt); Care: Freedom/Heart sub-limits (cataract Rs.20-30k/eye, knee Rs.70k-1.2L/knee); HDFC ERGO dengue waiting-period misapplication struck down (Delhi SCDRC, Oct 2026, Rs.17.99L claim).
- Waiting periods: initial 30 days; specific-disease typically 24 months (cataract, hernia, gallbladder, knee, hysterectomy); knee cost Rs.1.5-2.3L vs caps; dengue NOT on the 24-month list.
- Denial prevention hinges on: ICPs + TPR/IV charts + doctor's admission-necessity certificate with warning signs (OPD-convertible pattern); first-diagnosis dates post-inception + ported continuity (waiting/PED patterns); CIS room-category check before allotment (proportionate deduction); unbundling robotic charges (modern-treatment caps).
- Appeals ladder: written repudiation → insurer GRO (14 days) → IRDAI Bima Bharosa (155255) → Ombudsman (free, ≤Rs.50L, >75% of FY25-26 decisions favoured policyholders per Council figures cited) → Consumer Commission via e-Jagriti (>Rs.50L, 2-year limit).
