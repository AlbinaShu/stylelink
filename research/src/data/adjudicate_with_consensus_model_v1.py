#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline


RESEARCH_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = RESEARCH_ROOT / "data" / "processed" / "annotations" / "2026-10-20"
QUEUE_PATH = DATA_DIR / "adjudication_queue_v1.jsonl"
OUTPUT_PATH = DATA_DIR / "adjudication_decisions_ai_v1.jsonl"
MANIFEST_PATH = DATA_DIR / "adjudication_decisions_ai_v1_manifest.json"
RULES_PATH = RESEARCH_ROOT / "config" / "adjudication_rules_v1.json"
MODEL_ID = "codex_ai_adjudicator_v1"

# Every non-trivial fit disagreement selected by a direct cue or size-comparison
# rule was reviewed in context. These overrides prevent negated/quoted cues,
# style preferences, height-only issues, and between-size cases from being
# mistaken for product-level size-grid direction.
MANUAL_FIT_OVERRIDES = {
    "ADJ-0002": "runs_small",
    "ADJ-0004": "true_to_size",
    "ADJ-0014": "true_to_size",
    "ADJ-0022": "true_to_size",
    "ADJ-0046": "true_to_size",
    "ADJ-0052": "runs_large",
    "ADJ-0053": "runs_small",
    "ADJ-0083": "no_signal",
    "ADJ-0084": "true_to_size",
    "ADJ-0097": "no_signal",
    "ADJ-0100": "runs_large",
    "ADJ-0103": "no_signal",
    "ADJ-0106": "no_signal",
    "ADJ-0110": "no_signal",
    "ADJ-0118": "runs_small",
    "ADJ-0120": "no_signal",
    "ADJ-0127": "no_signal",
    "ADJ-0132": "runs_large",
    "ADJ-0135": "no_signal",
    "ADJ-0143": "true_to_size",
    "ADJ-0145": "no_signal",
    "ADJ-0150": "runs_large",
    "ADJ-0158": "true_to_size",
    "ADJ-0159": "runs_small",
    "ADJ-0175": "no_signal",
    "ADJ-0178": "runs_large",
    "ADJ-0180": "runs_large",
    "ADJ-0181": "true_to_size",
    "ADJ-0182": "runs_large",
    "ADJ-0192": "true_to_size",
    "ADJ-0194": "no_signal",
    "ADJ-0220": "runs_large",
    "ADJ-0224": "runs_small",
    "ADJ-0232": "runs_large",
    "ADJ-0235": "no_signal",
    "ADJ-0244": "no_signal",
    "ADJ-0255": "true_to_size",
    "ADJ-0260": "true_to_size",
    "ADJ-0293": "no_signal",
    "ADJ-0295": "runs_large",
    "ADJ-0309": "runs_large",
    "ADJ-0312": "no_signal",
    "ADJ-0315": "no_signal",
    "ADJ-0317": "no_signal",
    "ADJ-0324": "runs_large",
    "ADJ-0327": "runs_large",
    "ADJ-0329": "runs_large",
    "ADJ-0332": "runs_small",
    "ADJ-0335": "no_signal",
    "ADJ-0337": "true_to_size",
    "ADJ-0338": "runs_small",
    "ADJ-0346": "no_signal",
    "ADJ-0348": "no_signal",
    "ADJ-0351": "no_signal",
    "ADJ-0352": "no_signal",
    "ADJ-0354": "no_signal",
}

SMALL_RE = re.compile(r"\bмаломер\w*|ид(?:е|ё)?т|идут", re.I)
LARGE_RE = re.compile(r"\bбольшемер\w*", re.I)
TRUE_RE = re.compile(
    r"размер\s+в\s+размер|(?:идет|идёт|идут)\s+в\s+размер|"
    r"размер\w*\s+(?:полностью\s+)?соответств\w*|"
    r"соответств\w*\s+(?:заявленн\w*\s+)?размер\w*|"
    r"точно\s+по\s+размеру",
    re.I,
)
NEGATED_TRUE_RE = re.compile(r"не\s+соответств\w*\s+размер\w*|размер\w*\s+не\s+соответств\w*", re.I)
VAGUE_FIT_RE = re.compile(
    r"\bсел[аои]?\b|\bсид\w*|\bподош\w*|идеальн\w*|посадк\w*|как\s+раз|"
    r"тесн\w*|свободн\w*|узк\w*|широк\w*|велик\w*|в обтяг",
    re.I,
)
USUAL_MARKER_RE = re.compile(r"на\s+сво[йюи]|мой\s+размер|обычно\s+нош|ношу\s+размер|свои\s+параметр", re.I)
ORDER_MARKER_RE = re.compile(r"взял\w*|брал\w*|заказ\w*|купил\w*|выбрал\w*|приобр[её]л\w*", re.I)
RELATION_RE = re.compile(
    r"(?:взял\w*|брал\w*|заказ\w*|купил\w*|выбрал\w*|берит\w*|брать|надо|нужно|пришлось|перезаказ\w*|можно\s+было\s+взять)"
    r".{0,45}(?:на\s+(?:один|два|1|2)?\s*размер\w*\s+(?:больше|меньше)|размер\w*\s+(?:больше|меньше))|"
    r"(?:на\s+(?:один|два|1|2)?\s*размер\w*\s+(?:больше|меньше)|размер\w*\s+(?:больше|меньше))"
    r".{0,45}(?:взял\w*|брал\w*|заказ\w*|купил\w*|выбрал\w*|берит\w*|брать|надо|нужно|пришлось|перезаказ\w*)",
    re.I,
)
PREFERENCE_RE = re.compile(
    r"чтобы.{0,50}(?:свободн\w*|оверсайз\w*|как\s+на\s+модел\w*)|"
    r"(?:нравится|хотел\w*).{0,50}(?:свободн\w*|оверсайз\w*)",
    re.I,
)
SIZE_TOKEN_RE = re.compile(r"(?<!\d)(?:[3-7]\d)(?!\d)|\b(?:xxxs|xxs|xs|s|m|l|xl|xxl|xxxl|[2-6]xl)\b", re.I)
BODY_RE = re.compile(r"\bрост\w*|\bог\b|\bоб\b|\bот\b|груд\w*|тал\w*|бедр\w*|параметр\w*", re.I)
ZONE_RE = re.compile(r"в\s+груд\w*|в\s+тал\w*|в\s+бедр\w*|плеч\w*|рукав\w*|длин\w*|пояс\w*|живот\w*", re.I)
ACTION_RE = re.compile(r"вернул\w*|возврат\w*|отказ\w*|перезаказ\w*|обмен\w*|оставил\w*|забрал\w*|выкупил\w*|нош[уи]\b", re.I)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def direct_label(text: str) -> tuple[str | None, bool]:
    hits = []
    if re.search(r"\bмаломер\w*", text, re.I) or re.search(
        r"(?:идет|идёт|идут)\s+(?:примерно\s+)?на\s+\w*\s*размер\w*\s+меньше",
        text,
        re.I,
    ):
        hits.append("runs_small")
    if LARGE_RE.search(text):
        hits.append("runs_large")
    if TRUE_RE.search(text) and not NEGATED_TRUE_RE.search(text):
        hits.append("true_to_size")
    unique = sorted(set(hits))
    return (unique[0], False) if len(unique) == 1 else (None, len(unique) > 1)


def has_size_comparison(text: str) -> bool:
    if RELATION_RE.search(text):
        return True
    tokens = {token.lower() for token in SIZE_TOKEN_RE.findall(text)}
    return len(tokens) >= 2 and bool(USUAL_MARKER_RE.search(text) and ORDER_MARKER_RE.search(text))


def build_fit_model(texts: list[str], labels: list[str]) -> Pipeline:
    features = FeatureUnion(
        [
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=2,
                    max_features=40000,
                    sublinear_tf=True,
                ),
            ),
            (
                "word",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=20000,
                    sublinear_tf=True,
                ),
            ),
        ]
    )
    model = Pipeline(
        [
            ("features", features),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(texts, labels)
    return model


def adjudicate_fit(
    row: dict[str, Any], model: Pipeline
) -> tuple[str, str, float, list[str]]:
    text = row["review_text"]
    if row["queue_id"] in MANUAL_FIT_OVERRIDES:
        reason = "usual_vs_ordered_size" if has_size_comparison(text) else "explicit_direction"
        return MANUAL_FIT_OVERRIDES[row["queue_id"]], reason, 1.0, ["manual_context_review"]
    explicit, conflicting = direct_label(text)
    flags: list[str] = []
    probabilities = model.predict_proba([text])[0]
    classes = model.classes_
    model_index = int(probabilities.argmax())
    model_label = str(classes[model_index])
    confidence = float(probabilities[model_index])

    if conflicting:
        flags.append("conflicting_direct_cues")
    if explicit is not None:
        return explicit, "explicit_direction", 1.0, flags

    comparison = has_size_comparison(text)
    if PREFERENCE_RE.search(text) and not conflicting:
        return "no_signal", "strict_no_signal_rule", 0.85, flags
    if not comparison and not conflicting:
        return "no_signal", "strict_no_signal_rule", max(confidence, 0.75), flags

    if confidence < 0.55:
        flags.append("low_model_confidence")
    if {row["fit_label_a1"], row["fit_label_a2"]} == {"runs_small", "runs_large"}:
        flags.append("opposite_direction_sources")
    reason = "usual_vs_ordered_size" if comparison else "insufficient_evidence"
    return model_label, reason, confidence, flags


def explicitness_for(text: str, fit_label: str) -> str:
    if fit_label == "no_signal":
        return "none"
    explicit, conflicting = direct_label(text)
    if explicit == fit_label and not conflicting:
        return "explicit"
    return "implicit"


def informativeness_for(text: str, fit_label: str) -> tuple[str, list[str]]:
    if fit_label == "no_signal":
        return "low", []
    if has_size_comparison(text):
        return "high", ["size_comparison"]
    supports = []
    if BODY_RE.search(text):
        supports.append("body_parameter")
    if ZONE_RE.search(text):
        supports.append("fit_zone")
    if ACTION_RE.search(text):
        supports.append("user_action")
    if len(supports) >= 2:
        return "high", supports
    if len(supports) == 1:
        return "medium", supports
    return "low", supports


def main() -> int:
    annotator_1 = read_csv(DATA_DIR / "annotator_1_normalized_v3.csv")
    annotator_2 = {
        row["review_id"]: row
        for row in read_csv(DATA_DIR / "annotator_2_normalized_v3.csv")
    }
    agreed = [
        row
        for row in annotator_1
        if row["fit_label"] == annotator_2[row["review_id"]]["fit_label"]
    ]
    model = build_fit_model(
        [row["review_text"] for row in agreed],
        [row["fit_label"] for row in agreed],
    )

    decisions = []
    for row in read_jsonl(QUEUE_PATH):
        flags: list[str] = []
        if row["fit_label_a1"] == row["fit_label_a2"]:
            final_fit = row["fit_label_a1"]
            fit_reason = "source_agreement"
            confidence = 1.0
        else:
            final_fit, fit_reason, confidence, fit_flags = adjudicate_fit(row, model)
            flags.extend(fit_flags)

        if row["signal_explicitness_a1"] == row["signal_explicitness_a2"] and (
            final_fit != "no_signal" or row["signal_explicitness_a1"] == "none"
        ):
            final_explicitness = row["signal_explicitness_a1"]
        else:
            final_explicitness = explicitness_for(row["review_text"], final_fit)

        if row["informativeness_a1"] == row["informativeness_a2"] and final_fit != "no_signal":
            final_info = row["informativeness_a1"]
            supports: list[str] = []
        else:
            final_info, supports = informativeness_for(row["review_text"], final_fit)

        if {row["informativeness_a1"], row["informativeness_a2"]} == {"low", "high"}:
            flags.append("extreme_informativeness_disagreement")
        if confidence < 0.55:
            flags.append("audit_recommended")
        if "opposite_direction_sources" in flags or "conflicting_direct_cues" in flags:
            flags.append("audit_recommended")
        flags = sorted(set(flags))

        if "fit_label" in row["issue_fields"]:
            reason = fit_reason
        elif "signal_explicitness" in row["issue_fields"]:
            reason = "explicit_direction" if final_explicitness == "explicit" else "usual_vs_ordered_size" if final_explicitness == "implicit" else "strict_no_signal_rule"
        else:
            reason = "informativeness_boundary"

        note_parts = [f"AI confidence={confidence:.3f}"]
        if supports:
            note_parts.append("supports=" + ",".join(supports))
        if flags:
            note_parts.append("flags=" + ",".join(flags))
        decisions.append(
            {
                "queue_id": row["queue_id"],
                "review_id": row["review_id"],
                "final_fit_label": final_fit,
                "final_signal_explicitness": final_explicitness,
                "final_informativeness": final_info,
                "reason_code": reason,
                "adjudication_note": "; ".join(note_parts),
                "reviewed_by": MODEL_ID,
                "reviewed_at": date(2026, 10, 20).isoformat(),
                "status": "complete",
                "ai_confidence": round(confidence, 6),
                "audit_recommended": "audit_recommended" in flags,
            }
        )

    with OUTPUT_PATH.open("w", encoding="utf-8") as stream:
        for row in decisions:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "adjudicator": MODEL_ID,
        "status": "ai_adjudicated_pending_human_audit",
        "date": "2026-10-20",
        "method": "Approved deterministic rules, manual contextual review of all non-trivial fit disagreements, and TF-IDF logistic-regression fallback trained only on rows where both human annotators agreed.",
        "manual_fit_review_rows": len(MANUAL_FIT_OVERRIDES),
        "training_rows_with_fit_agreement": len(agreed),
        "decision_rows": len(decisions),
        "audit_recommended_rows": sum(row["audit_recommended"] for row in decisions),
        "final_fit_counts": dict(Counter(row["final_fit_label"] for row in decisions)),
        "final_explicitness_counts": dict(Counter(row["final_signal_explicitness"] for row in decisions)),
        "final_informativeness_counts": dict(Counter(row["final_informativeness"] for row in decisions)),
        "source_queue": {"path": QUEUE_PATH.name, "sha256": sha256(QUEUE_PATH)},
        "rules": {"path": RULES_PATH.name, "sha256": sha256(RULES_PATH)},
        "output": {"path": OUTPUT_PATH.name, "sha256": sha256(OUTPUT_PATH)},
        "script_sha256": sha256(Path(__file__)),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
