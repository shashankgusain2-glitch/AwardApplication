"""
Applicants, organisations and their applications.

Planned models:
- Organisation: name, cleaned name (suffixes like Ltd./Co. removed), GSTIN.
- DuplicateCandidate: a possible duplicate pair waiting for staff review.
- Application: belongs to one AwardCycle and one Organisation.
  Stores the FormVersion it was started on, so it always opens
  with the right questions.                                      [Rule 4]
  Status: Draft -> Submitted -> Under review -> Shortlisted / Not -> Result.
- Evidence: an uploaded file for one answer.
"""
