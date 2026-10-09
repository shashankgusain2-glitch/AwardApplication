


## 1. What I Did Today

* **Finalized Core System Requirements & Architecture:**
    * Resolved open operational edge cases with stakeholders to clear the path for the build phase.
    * Mapped system roles to the organizational hierarchy (**Leader** $\rightarrow$ **Member per Award** $\rightarrow$ **Working Staff**).
    * Confirmed support for multi-partner collaborations, hybrid registration flows (manual and automated), and configurable per-award settings (1-round vs. 2-round judging; optional blind anonymity).

* **Designed Anti-Fraud & Identity Verification Protocol:**
    * Modeled an identity validation pipeline using official company emails and authorized representative government IDs (**PAN Card**).
    * Applied business validation logic (similar to **GST registration checks**) to prevent unauthorized submissions, impersonation, and submission sabotage.

* **Designed Data Normalization & Anti-Gaming Rules:**
    * Addressed rule defects where companies submit multiple entries under variant names (e.g., *Tata*, *Tata Co.*, *Tata Ltd.*).
    * Structured a multi-stage deduplication pipeline:
        1. Clean corporate suffixes (`Ltd.`, `Co.`, `Limited`, `Inc.`).
        2. Group similar entity names in a staging table using string proximity scoring.
        3. Merge verified matches into a single canonical profile while keeping distinct entities separated.

* **Defined Next Deliverables & Task Ownership:**
    * Initiated the comprehensive User Experience (UX) journey mapping across all 4 system roles (**Applicant**, **Judge**, **Staff**, **Leader**).
    * Defined the initial technical milestone plan for application development.

---

## 2. Research Conducted Today

* **Entity Resolution & String Matching Algorithms:**
    * Researched name normalization and deduplication methods (Fuzzy Matching, Levenshtein Distance, and Jaro-Winkler algorithms) to group and flag company name variants automatically during submission intake.

* **Corporate ID & Verification Frameworks:**
    * Evaluated standard business identification practices (PAN Card cross-referencing and corporate email domain matching) to establish strong proof-of-authority without introducing excessive friction for legitimate applicants.

* **Multi-Stage & Blind Evaluation System Design:**
    * Analyzed score aggregation strategies (independent score averaging) and dynamic workflow designs to handle variable judging rules (1-stage vs. 2-stage live pitch rounds; toggleable applicant anonymity).
  
