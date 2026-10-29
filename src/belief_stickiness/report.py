"""Static HTML report. Numbers are copied from summary.json, not retyped."""

from __future__ import annotations

import json
from pathlib import Path


def write_report(summary: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(summary).replace("<", "\\u003c")
    path.write_text(_PAGE.replace("/*SUMMARY*/", payload))


_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Belief stickiness — results</title>
<style>
  :root { color-scheme: light; }
  body { font-family: "Iowan Old Style", Palatino, Georgia, serif; max-width: 920px; margin: 2rem auto; padding: 0 1.2rem; line-height: 1.45; color: #1c1c1c; }
  h1 { font-size: 1.7rem; }
  h2 { font-size: 1.15rem; margin-top: 2rem; }
  table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.92rem; }
  th, td { border-bottom: 1px solid #ddd; text-align: left; padding: 0.35rem 0.4rem; vertical-align: top; }
  td.num { text-align: right; }
  .note { background: #f6f4ef; padding: 0.8rem 1rem; }
  button { font: inherit; padding: 0.3rem 0.7rem; margin: 0 0.3rem 0.3rem 0; }
  .hidden { display: none; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.9em; }
  #integrity { font-family: ui-sans-serif, system-ui, sans-serif; }
</style>
</head>
<body>
<h1>Belief stickiness</h1>
<p class="note">A laptop LoRA study of whether user-facing reasons and action-stories make a false factual claim, or a contested normative claim, harder to shake. The normative claim is a probe. This page does not endorse it. A cell that says “not estimated” was not measured. It is not a zero effect.</p>
<p id="status"></p>
<p><button type="button" id="show-stick">Stickiness</button>
<button type="button" id="show-hyp">Hypotheses</button>
<button type="button" id="show-rates">Rates</button>
<button type="button" id="show-diag">Diagnostics</button>
<button type="button" id="check">Check numbers against the embedded summary</button></p>
<p id="integrity"></p>
<section id="stick"></section>
<section id="hyp" class="hidden"></section>
<section id="h3" class="hidden"></section>
<section id="rates" class="hidden"></section>
<section id="diag" class="hidden"></section>
<script id="summary" type="application/json">/*SUMMARY*/</script>
<script>
const summary = JSON.parse(document.getElementById("summary").textContent);
const status = document.getElementById("status");
status.textContent = summary.status === "not_run"
  ? "No scored run is in this report. Nothing below is a measured outcome."
  : "Status: " + summary.status + ". Temperature " + summary.temperature + ", one greedy sample per item. Bootstrap replicates: " + summary.bootstrap_replicates + ".";

function esc(value) {
  return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function fmt4(value) {
  if (value === null || value === undefined) return "not estimated";
  return Number(value).toFixed(4);
}
function fmtBlock(block) {
  if (!block || block.rate === null || block.rate === undefined) return "n/a";
  return Number(block.rate).toFixed(4);
}
function fmtDrop(value) {
  if (value === null || value === undefined) return "n/a";
  return Number(value).toFixed(4);
}
function table(headers, rows, numericFrom) {
  const start = numericFrom === undefined ? headers.length : numericFrom;
  const head = "<tr>" + headers.map(cell => "<th>" + esc(cell) + "</th>").join("") + "</tr>";
  const body = rows.map(row => "<tr>" + row.map((cell, i) => {
    const cls = i >= start ? " class='num'" : "";
    return "<td" + cls + ">" + esc(cell) + "</td>";
  }).join("") + "</tr>").join("");
  return "<table>" + head + body + "</table>";
}

const stick = document.getElementById("stick");
const stickRows = summary.stickiness || [];
if (stickRows.length === 0) {
  stick.innerHTML = "<h2>Stickiness</h2><p>No stickiness rows.</p>";
} else {
  stick.innerHTML = "<h2>Stickiness index</h2>" + table(
    ["Model", "Belief", "Condition", "Index", "Low", "High"],
    stickRows.map(row => [row.model_slug, row.belief, row.condition, fmt4(row.stickiness), fmt4(row.ci_low), fmt4(row.ci_high)]),
    3
  );
}

const hyp = document.getElementById("hyp");
const hypRows = (summary.hypotheses || []).filter(row => row.id !== "H3");
const contrastRows = [];
hypRows.forEach(row => {
  const add = (name, block) => {
    if (!block) return;
    contrastRows.push([row.id, row.belief, name, fmt4(block.estimate), fmt4(block.ci_low), fmt4(block.ci_high)]);
  };
  if (row.id === "H1") {
    add("index, rationalization minus assertion", row.index_rationalization_minus_assertion);
    add("OOD verbal, rationalization minus assertion", row.ood_rationalization_minus_assertion);
    add("resistance, rationalization minus assertion", row.resistance_rationalization_minus_assertion);
  } else if (row.id === "H2") {
    add("behavioral lift minus verbal lift", row.interaction_behavioral_lift_minus_verbal_lift);
  } else if (row.id === "H4") {
    (row.combined_minus_each || []).forEach(block => add("combined minus " + block.versus, block));
  } else if (row.id === "H5") {
    add("tracks_reason, rationalization minus assertion", row.tracks_reason_rationalization_minus_assertion);
  }
});
let notes = "";
hypRows.forEach(row => {
  const text = row.interpretation || row.note;
  if (text) notes += "<p><strong>" + esc(row.id + " · " + row.belief) + ".</strong> " + esc(text) + "</p>";
});
hyp.innerHTML = "<h2>Pre-registered contrasts</h2><div id='hyp-labels'>" + (hypRows.length ? table(
  ["Id", "Model", "Belief", "Label"],
  hypRows.map(row => [row.id, row.model_slug, row.belief, row.label])
) : "<p>No contrasts.</p>") + "</div><div id='contrasts'>" + (contrastRows.length ? table(
  ["Id", "Belief", "Contrast", "Estimate", "Low", "High"],
  contrastRows,
  3
) : "<p>No contrast estimates.</p>") + "</div>" + notes;

const h3 = document.getElementById("h3");
const h3rows = (summary.hypotheses || []).filter(row => row.id === "H3");
if (!h3rows.length) {
  h3.innerHTML = "";
} else {
  let html = "<h2>H3, exploratory</h2><p>No sign was predicted. The difference is procreation stickiness minus sky stickiness. The sycophancy gap is agree minus disagree. The normative probe is not endorsed.</p>";
  h3rows.forEach(block => {
    const cross = (block.cross_belief || []).map(row => [
      row.condition,
      fmt4(row.sky_green),
      fmt4(row.procreation_cessation),
      fmt4(row.stickiness_procreation_minus_sky)
    ]);
    html += "<h2>" + esc(block.model_slug) + "</h2>" + (cross.length ? table(
      ["Condition", "Sky", "Procreation", "Procreation minus sky"],
      cross,
      1
    ) : "<p>Cross-belief difference: not estimated.</p>");
    const gaps = (block.sycophancy_gap || []).map(row => [
      row.belief,
      row.condition,
      String(row.agree_k),
      String(row.agree_n),
      fmt4(row.agree_rate),
      String(row.disagree_k),
      String(row.disagree_n),
      fmt4(row.disagree_rate),
      fmt4(row.gap_agree_minus_disagree)
    ]);
    html += gaps.length ? table(
      ["Belief", "Condition", "Agree k", "Agree n", "Agree", "Disagree k", "Disagree n", "Disagree", "Gap"],
      gaps,
      2
    ) : "<p>Sycophancy gap: not estimated.</p>";
  });
  h3.innerHTML = html;
}

const rates = document.getElementById("rates");
const shown = summary.rates || [];
rates.innerHTML = "<h2>Component rates</h2><p>Every stratum is listed, including boundary items. Boundary items are not in the stickiness index. Reason-tracking discriminating rows are the H5 denominator. Positive-control rows are not.</p>" + (shown.length ? table(
  ["Model", "Belief", "Condition", "Stratum", "k", "n", "Rate"],
  shown.map(row => [row.model_slug, row.belief, row.condition, row.stratum, String(row.k), String(row.n), fmt4(row.rate)]),
  4
) : "<p>No rates.</p>");

const diag = document.getElementById("diag");
const diagRows = summary.diagnostics || [];
diag.innerHTML = "<h2>Diagnostics</h2><p>A drop of more than the pre-registered flag versus the base model is marked. Mars is exploratory world knowledge. Intrusion is the normative probe on an ordinary question, not an endorsement of that probe.</p>" + (diagRows.length ? table(
  ["Model", "Condition", "Flagged", "Capability", "Specificity", "Intrusion", "Mars", "Capability drop", "Specificity drop"],
  diagRows.map(row => [
    row.model_slug,
    row.condition,
    row.flagged ? "yes" : "no",
    fmtBlock(row.capability_correct),
    fmtBlock(row.specificity_correct),
    fmtBlock(row.ordinary_intrusion),
    fmtBlock(row.mars_green_slogan),
    fmtDrop(row.capability_drop_vs_base),
    fmtDrop(row.specificity_drop_vs_base)
  ]),
  3
) : "<p>No diagnostics.</p>");

function show(id) {
  const open = id === "hyp" ? ["hyp", "h3"] : [id];
  for (const name of ["stick", "hyp", "h3", "rates", "diag"]) {
    document.getElementById(name).classList.toggle("hidden", open.indexOf(name) === -1);
  }
}
document.getElementById("show-stick").onclick = () => show("stick");
document.getElementById("show-hyp").onclick = () => show("hyp");
document.getElementById("show-rates").onclick = () => show("rates");
document.getElementById("show-diag").onclick = () => show("diag");

function same(actual, expected, name) {
  if (actual.length !== expected.length || expected.some((value, index) => value !== actual[index])) {
    return name;
  }
  return "";
}
document.getElementById("check").onclick = () => {
  const problems = [];
  document.querySelectorAll("#stick td.num").forEach((cell, index) => {
    const row = stickRows[Math.floor(index / 3)];
    const key = ["stickiness", "ci_low", "ci_high"][index % 3];
    if (!row || cell.textContent !== fmt4(row[key])) problems.push("stickiness");
  });
  const labels = [...document.querySelectorAll("#hyp-labels td")].filter((_, i) => i % 4 === 3).map(td => td.textContent);
  hypRows.forEach((row, i) => { if (labels[i] !== row.label) problems.push(row.id + " label"); });
  const contrastExpected = [];
  hypRows.forEach(row => {
    const add = (block) => {
      if (!block) return;
      contrastExpected.push(fmt4(block.estimate), fmt4(block.ci_low), fmt4(block.ci_high));
    };
    if (row.id === "H1") {
      add(row.index_rationalization_minus_assertion);
      add(row.ood_rationalization_minus_assertion);
      add(row.resistance_rationalization_minus_assertion);
    } else if (row.id === "H2") {
      add(row.interaction_behavioral_lift_minus_verbal_lift);
    } else if (row.id === "H4") {
      (row.combined_minus_each || []).forEach(add);
    } else if (row.id === "H5") {
      add(row.tracks_reason_rationalization_minus_assertion);
    }
  });
  const contrastProblem = same([...document.querySelectorAll("#contrasts td.num")].map(td => td.textContent), contrastExpected, "contrasts");
  if (contrastProblem) problems.push(contrastProblem);
  const h3Expected = [];
  h3rows.forEach(block => {
    (block.cross_belief || []).forEach(row => {
      h3Expected.push(fmt4(row.sky_green), fmt4(row.procreation_cessation), fmt4(row.stickiness_procreation_minus_sky));
    });
    (block.sycophancy_gap || []).forEach(row => {
      h3Expected.push(
        String(row.agree_k), String(row.agree_n), fmt4(row.agree_rate),
        String(row.disagree_k), String(row.disagree_n), fmt4(row.disagree_rate),
        fmt4(row.gap_agree_minus_disagree)
      );
    });
  });
  const h3Problem = same([...document.querySelectorAll("#h3 td.num")].map(td => td.textContent), h3Expected, "h3");
  if (h3Problem) problems.push(h3Problem);
  const rateExpected = [];
  shown.forEach(row => rateExpected.push(String(row.k), String(row.n), fmt4(row.rate)));
  const rateProblem = same([...document.querySelectorAll("#rates td.num")].map(td => td.textContent), rateExpected, "rates");
  if (rateProblem) problems.push(rateProblem);
  const diagExpected = [];
  diagRows.forEach(row => diagExpected.push(
    fmtBlock(row.capability_correct),
    fmtBlock(row.specificity_correct),
    fmtBlock(row.ordinary_intrusion),
    fmtBlock(row.mars_green_slogan),
    fmtDrop(row.capability_drop_vs_base),
    fmtDrop(row.specificity_drop_vs_base)
  ));
  const diagProblem = same([...document.querySelectorAll("#diag td.num")].map(td => td.textContent), diagExpected, "diagnostics");
  if (diagProblem) problems.push(diagProblem);
  const measured = stickRows.length + hypRows.length + shown.length + diagRows.length;
  const box = document.getElementById("integrity");
  if (problems.length) box.textContent = "Mismatch: " + problems.join(", ");
  else if (!measured) box.textContent = "No measured stickiness or hypothesis labels are on the page.";
  else box.textContent = "Integrity check passed. Visible stickiness numbers, hypothesis labels, contrast estimates, H3, rates, and diagnostics match the embedded summary.";
};
</script>
</body>
</html>
"""
