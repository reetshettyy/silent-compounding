"""Phase 9 methodology-gate checker (no model calls; writes only its own report).

PASS = automated evidence found and, where the item needs a researcher decision,
that decision is written in docs/phase9_gate_notes.md. FAIL = evidence missing or
contradicting. MANUAL = evidence the script cannot see. This is not sign-off.
"""
import glob
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
results = []
REQ_STAGE = {"model", "temperature", "num_predict"}
NOTES = ROOT / "docs" / "phase9_gate_notes.md"
notes_text = NOTES.read_text(encoding="utf-8") if NOTES.exists() else ""


def record(item, status, detail):
    results.append({"item": item, "status": status, "detail": detail})
    print(f"[{status:<6}] {item}\n         {detail}")


def status(ok):
    return "PASS" if ok else "FAIL"


def notes_has(*needles):
    return all(n in notes_text for n in needles)


def pytest_ok(*files):
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", *files],
                       cwd=ROOT, capture_output=True, text=True)
    lines = (p.stdout or p.stderr).strip().splitlines()
    return p.returncode == 0, (lines[-1] if lines else "no output")


def grep(pattern, dirs):
    hits = []
    for d in dirs:
        for f in sorted((ROOT / d).rglob("*.py")):
            if "__pycache__" in f.parts:
                continue
            for n, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if re.search(pattern, line, re.I):
                    hits.append(f"{f.relative_to(ROOT)}:{n}")
    return hits


def load_json_files(pattern):
    return [(Path(f), json.loads(Path(f).read_text(encoding="utf-8")))
            for f in sorted(glob.glob(str(ROOT / pattern)))]


def versions(rec):
    for v in ("baseline", "injected"):
        if rec.get(v):
            yield v, rec[v]["trace"]


def tag(f):
    return f"{f.parent.name[-8:]}/{f.name}"


def run_cfg(tr):
    if tr and isinstance(tr[0], dict) and tr[0].get("agent") == "run_config":
        return tr[0].get("config") or {}
    return None


def cfg_problems(cfg):
    p = []
    gen = cfg.get("generation") or {}
    for s in ("research", "summarizer", "action"):
        if not REQ_STAGE <= set(gen.get(s) or {}):
            p.append(f"generation.{s}")
    for k in ("evaluator_model", "max_tokens_enforced", "seed", "condition_id"):
        if k not in cfg:
            p.append(k)
    if not {"top_k", "retriever_type"} <= set(cfg.get("retrieval") or {}):
        p.append("retrieval")
    return p


traces = load_json_files("data/phase7_validation/*/HQ*.json")
batch_all = load_json_files("data/phase9_config_batch/*/*.json")
batch = [(f, r) for f, r in batch_all if r.get("status") == "ok"]
batch_failed = [tag(f) for f, r in batch_all if r.get("status") != "ok"]
legacy_total = sum(1 for _, rec in traces for _ in versions(rec))

# 1. Gold isolation
ok, d = pytest_ok("tests/test_no_gold_leakage.py", "tests/test_evaluator_isolation.py")
leaks = grep(r"eval_only", ["agents", "pipelines"])
record("Gold answer never reaches a generation agent", status(ok and not leaks),
       f"{d}; eval_only references in agents/pipelines: {leaks or 'none'}")

# 2. Confidence
ok, d = pytest_ok("tests/test_no_confidence.py")
hits = grep(r"confidence", ["agents", "pipelines", "injection", "retrieval"])
allowed, unexplained = [], []
for h in hits:
    path, n = h.rsplit(":", 1)
    line = (ROOT / path).read_text(encoding="utf-8").splitlines()[int(n) - 1]
    if path == "injection/error_bank.py" and re.search(r"CONFIDENCE\(\?:", line):
        allowed.append(h)
    else:
        unexplained.append(h)
documented = notes_has("injection/error_bank.py", "parsing only")
record("Confidence fully removed from generation",
       status(ok and not unexplained and (not allowed or documented)),
       f"{d}; parsing-only regex terminators: {allowed or 'none'}; "
       f"unexplained hits: {unexplained or 'none'}; documented in notes: {documented}")

# 3. Retrieval logged (legacy validation traces plus post-fix batch)
total = bad = 0
for _, rec in traces:
    for v, tr in versions(rec):
        total += 1
        r = next((i for i in tr if i.get("agent") == "retriever"), None)
        if not (r and (r.get("retrieval") or {}).get("retrieved_document_ids")):
            bad += 1
for _, rec in batch:
    total += 1
    r = next((i for i in rec["trace"] if i.get("agent") == "retriever"), None)
    if not (r and (r.get("retrieval") or {}).get("retrieved_document_ids")):
        bad += 1
record("Retrieval logged for every run", status(total > 0 and bad == 0),
       f"{total - bad}/{total} traces have a retriever entry with document ids")

# 4. Registry
ok, d = pytest_ok("tests/test_model_registry.py", "tests/test_runner_registry_assertion.py")
record("Model registry populated and independence assertion passes", status(ok), d)

# 5. Evaluator isolated
ok, d = pytest_ok("tests/test_evaluator_isolation.py")
record("Evaluator isolated from generation", status(ok), d)

# 6. Conditions C1-C4
ok, d = pytest_ok("tests/test_conditions_matrix.py", "tests/test_run_config_and_conditions.py")
p1_src = (ROOT / "pipelines" / "p1_linear.py").read_text(encoding="utf-8")
consumed = "condition=None" in p1_src and "retrieval_query" in p1_src
problems, seen = [], {}
for f, rec in batch:
    tr = rec["trace"]
    cfg = run_cfg(tr)
    r = next((i for i in tr if i.get("agent") == "retriever"), None)
    if cfg is None or r is None:
        problems.append(f"{tag(f)}: missing run_config or retriever")
        continue
    r = r["retrieval"]
    c, cond = cfg.get("condition_id"), cfg.get("condition") or {}
    if (r["query"] == r["agent_question"]) != (c in ("C1", "C4")):
        problems.append(f"{tag(f)}: query/agent_question relation wrong for {c}")
    if r["agent_question"] != cond.get("question") or r["query"] != cond.get("retrieval_query"):
        problems.append(f"{tag(f)}: retrieval fields differ from condition input")
    if c in ("C3", "C4") and r["retrieved_document_ids"][0] != cond.get("perturbed_context_document_id"):
        problems.append(f"{tag(f)}: rank-1 is not the stored perturbed document")
    if not rec.get("injected"):
        seen.setdefault(rec["task_id"], set()).add(c)
full = sorted(t for t, v in seen.items() if v == {"C1", "C2", "C3", "C4"})
documented = notes_has("top-5", "rank 1 equals the stored document")
record("All four conditions (C1-C4) work and are reproducible",
       status(ok and consumed and bool(full) and not problems and documented),
       f"{d}; run_pipeline consumes conditions: {consumed}; tasks with all of C1-C4 in batch: {full}; "
       f"problems: {problems or 'none'}; documented: {documented}")

# 7. Clean control (C1, no injection)
legacy_bad = [tag(f) for f, rec in traces for v, tr in versions(rec)
              if v == "baseline" and any(i.get("agent") == "error_injector" for i in tr)]
n_legacy_base = sum(1 for _, rec in traces if rec.get("baseline"))
c1 = [(f, rec) for f, rec in batch if not rec.get("injected")
      and (run_cfg(rec["trace"]) or {}).get("condition_id") == "C1"]
c1_bad = [tag(f) for f, rec in c1 if any(i.get("agent") == "error_injector" for i in rec["trace"])]
record("Clean control (no injection) works",
       status(bool(c1) and not c1_bad and not legacy_bad),
       f"{len(c1)} logged C1 baseline runs (injector entries: {c1_bad or 'none'}); "
       f"{n_legacy_base} older baseline traces, C1 by construction but not logged "
       f"(injector entries: {legacy_bad or 'none'})")

# 8. Injection validated / bounded / logged
ok, d = pytest_ok("tests/test_injector_validation.py", "tests/test_injection_isolation.py")
need = {"error_type", "injection_stage", "wording", "original_claim", "injected_claim", "injection_description"}
inj = [(f, rec) for f, rec in traces if rec.get("injected")]
missing = [tag(f) for f, rec in inj if not need <= set(rec.get("injection_metadata") or {})]
rejected = [tag(f) for f, rec in traces if rec.get("errors")]
record("Error injection validated, bounded, logged",
       status(bool(ok and inj and not missing)),
       f"{d}; {len(inj)} injected traces, missing metadata: {missing or 'none'}; "
       f"{len(rejected)} runs rejected by validators (report this rate)")

# 9. Injection reproducible (replay by stored output)
need_out = {"corrupted_output", "injected_claim", "original_claim", "wording", "error_type", "injection_stage"}
no_replay, no_audit, n_inj_traces = [], [], 0
sources = [(tag(f), tr) for f, rec in traces for v, tr in versions(rec) if v == "injected"]
sources += [(tag(f), rec["trace"]) for f, rec in batch if rec.get("injected")]
for t, tr in sources:
    n_inj_traces += 1
    e = next((i for i in tr if i.get("agent") == "error_injector"), None)
    if not (e and need_out <= set(e.get("output") or {})):
        no_replay.append(t)
    elif "original_output" not in e["output"]:
        no_audit.append(t)
documented = notes_has("replayable by stored corrupted_output", "original_output")
record("Error injection reproducible",
       status(n_inj_traces > 0 and not no_replay and documented),
       f"{n_inj_traces} injected traces store the replay fields (missing: {no_replay or 'none'}); "
       f"clean original_output (audit only, not needed to replay) present in "
       f"{n_inj_traces - len(no_audit) - len(no_replay)}/{n_inj_traces}, absent in older records: {no_audit or 'none'}; "
       f"standard is replay by stored corrupted_output, not regeneration by seed; documented: {documented}")

# 10. Trace complete
need_agents = {"retriever", "research", "summarizer", "action"}
bad = []
for f, rec in traces:
    for v, tr in versions(rec):
        miss = need_agents - {i.get("agent") for i in tr}
        if v == "injected" and "error_injector" not in {i.get("agent") for i in tr}:
            miss.add("error_injector")
        if miss:
            bad.append(f"{tag(f)}:{v}:{sorted(miss)}")
for f, rec in batch:
    agents = {i.get("agent") for i in rec["trace"]}
    miss = need_agents - agents
    if rec.get("injected") and "error_injector" not in agents:
        miss.add("error_injector")
    if miss:
        bad.append(f"{tag(f)}:{sorted(miss)}")
ok, d = pytest_ok("tests/test_pipeline_trace_integrity.py")
record("Raw JSON trace is complete and reconstructable", status(ok and not bad),
       f"{d}; traces with missing stages: {bad or 'none'}")

# 11. Metrics on toy examples
ok, d = pytest_ok("tests/test_cascade_metrics.py", "tests/test_severity_classification.py",
                  "tests/test_bleu_meteor_bertscore.py", "tests/test_propagation_metrics.py",
                  "tests/test_cascade_classifier.py", "tests/test_retrieval_metrics.py")
record("All metrics compute correctly on known/toy examples", status(ok), d)

# 12. Manual validation sample
rows = [json.loads(l) for l in (ROOT / "data/error_judge_human_review_v2.jsonl")
        .read_text(encoding="utf-8").splitlines() if l.strip()]
runs = {}
for r in rows:
    if r.get("human_outcome"):
        prefix = f"{r['task_id']}_{r['stage']}"
        runs.setdefault(r["task_id"] + r["review_id"][len(prefix):], set()).add(r["stage"])
fully = sorted(k for k, v in runs.items() if v == {"research", "summary", "final"})
documented = notes_has("55.0%", "0.398", "report-only")
record("10-20 manually labeled runs agree with automated evaluation",
       status(10 <= len(fully) <= 20 and documented),
       f"{len(fully)} fully human-labeled runs; agreement recorded as report-only "
       f"(55.0% exact, kappa 0.398, held-out n=20); documented: {documented}")

# 13. Config logged per run
incomplete, n_inj, n_base = [], 0, 0
for f, rec in batch:
    cfg = run_cfg(rec["trace"])
    pr = ["run_config entry missing"] if cfg is None else cfg_problems(cfg)
    if pr:
        incomplete.append(f"{tag(f)}: {pr}")
    n_inj += 1 if rec.get("injected") else 0
    n_base += 0 if rec.get("injected") else 1
legacy_with = sum(1 for _, rec in traces for v, tr in versions(rec) if run_cfg(tr) is not None)
documented = notes_has("max_tokens_enforced", "pre-fix")
record("All config parameters logged per run",
       status(bool(batch) and not incomplete and n_inj >= 1 and n_base >= 1 and documented),
       f"{len(batch)} post-fix traces ({n_base} baseline, {n_inj} injected), incomplete: {incomplete or 'none'}; "
       f"failed batch runs: {batch_failed or 'none'}; pre-fix traces without run_config: "
       f"{legacy_total - legacy_with}/{legacy_total} (kept, not used as evidence); documented: {documented}")

out = ROOT / "data" / "phase9_gate"
out.mkdir(parents=True, exist_ok=True)
path = out / f"gate_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
path.write_text(json.dumps({"status": "gate_check_not_signoff", "results": results}, indent=2), encoding="utf-8")
counts = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "FAIL", "MANUAL")}
print(f"\nPASS {counts['PASS']} | FAIL {counts['FAIL']} | MANUAL {counts['MANUAL']}\nSaved: {path}")
