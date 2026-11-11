// Same formula as src/govkit/value.py:compute. Keep both in step (the end-to-end test compares them).
const r2 = (x) => Math.round(x * 100) / 100;

export function compute(f, a) {
  const rowsPm = f.quarantined_rows / f.months_observed;
  const reworkH = rowsPm * a.rework_hours_per_bad_row;
  const decisions = rowsPm / a.bad_rows_per_wrong_decision;
  const disputeH = f.governed_metrics * a.dispute_hours_per_metric * a.people_per_dispute;
  const piiH = (f.undeclared_pii_columns.length * a.incident_hours * a.exposure_probability_per_year) / 12;
  const parts = {
    rework: { hours: r2(reworkH), pen: r2(reworkH * a.analyst_hour_cost) },
    wrong_decisions: { hours: 0, pen: r2(decisions * a.wrong_decision_cost), count: r2(decisions) },
    definition_disputes: { hours: r2(disputeH), pen: r2(disputeH * a.analyst_hour_cost) },
    personal_data_risk: { hours: r2(piiH), pen: r2(piiH * a.analyst_hour_cost) },
  };
  const vals = Object.values(parts);
  return {
    bad_rows_per_month: r2(rowsPm),
    parts,
    total_hours: Math.round(vals.reduce((s, p) => s + p.hours, 0) * 10) / 10,
    total_pen: Math.round(vals.reduce((s, p) => s + p.pen, 0)),
  };
}
