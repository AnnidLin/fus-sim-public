# Manuscript reference and claim-scope audit

Trace: `TRACE-20260829-001`  
Status: `passed_for_scoped_claims`

All 11 references are cited, citation numbering is contiguous, and every
reference has an explicit “supports / does not support” boundary in the paired
JSON audit. The audit is about claim fit, not journal prestige or paper quality.

## Main decisions

- References 4 and 5 support the general modelling/validation approach but do
  not validate Case079 or turn the H115 result into a passing comparison.
- References 6, 10 and 11 support property-map sensitivity and heterogeneous or
  scanner-dependent mapping context. None directly validates `simple_hu300`.
- Reference 8 establishes the UCL dataset identity/version/licence route, not
  the correctness of the current simplified source model.
- Reference 9 justifies examining hydrophone spatial averaging and positioning,
  but not treating the approximate amplitude-domain average as complex-pressure
  aperture integration.
- Reference 3 is contextual evidence for multi-model evaluation and cannot be
  used to generalize the single Case079 result.

No new physical default or manuscript claim was introduced by this audit.

