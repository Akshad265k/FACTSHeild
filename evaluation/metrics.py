"""Benchmark metrics — catch rate, precision, recall, F1."""
from __future__ import annotations


def calculate_metrics(details: list[dict]) -> dict:
    """
    Calculate comprehensive metrics from benchmark detail records.

    Parameters
    ----------
    details
        List of per-seed-case result dicts, each with keys:
        ``Was Caught``, ``Expected Detection``, ``Category``.

    Returns
    -------
    dict
        Overall and per-category metrics.
    """
    total = len(details)
    if total == 0:
        return {"total": 0, "caught": 0, "missed": 0, "catch_rate": 0.0}

    # ── Overall ───────────────────────────────────────────────────────────────
    caught = sum(1 for d in details if d["Was Caught"] == d["Expected Detection"])
    missed = total - caught
    catch_rate = caught / total * 100

    # Confusion matrix components (treating "should detect" as positive class)
    tp = sum(1 for d in details if d["Expected Detection"] and d["Was Caught"])
    fp = sum(1 for d in details if not d["Expected Detection"] and d["Was Caught"])
    fn = sum(1 for d in details if d["Expected Detection"] and not d["Was Caught"])
    tn = sum(1 for d in details if not d["Expected Detection"] and not d["Was Caught"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0 else 0.0
    )

    # ── Per-category ──────────────────────────────────────────────────────────
    categories = sorted({d["Category"] for d in details})
    by_category: dict[str, dict] = {}
    for cat in categories:
        cat_d = [d for d in details if d["Category"] == cat]
        cat_caught = sum(1 for d in cat_d if d["Was Caught"] == d["Expected Detection"])
        by_category[cat] = {
            "caught": cat_caught,
            "total": len(cat_d),
            "catch_rate": cat_caught / len(cat_d) * 100 if cat_d else 0.0,
        }

    return {
        "total": total,
        "caught": caught,
        "missed": missed,
        "catch_rate": round(catch_rate, 2),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "f1": round(f1 * 100, 2),
        "by_category": by_category,
    }


def confusion_matrix_data(metrics: dict) -> list[list]:
    """
    Return a 2×2 confusion matrix as a list of lists for display.

    Layout::

        [[TP, FP],
         [FN, TN]]
    """
    return [
        [metrics.get("true_positives", 0), metrics.get("false_positives", 0)],
        [metrics.get("false_negatives", 0), metrics.get("true_negatives", 0)],
    ]


def format_benchmark_summary(metrics: dict, release: str = "") -> str:
    """Return a clean text summary of benchmark results."""
    lines = [
        f"FACTSHIELD Benchmark Results{f' — {release}' if release else ''}",
        "=" * 50,
        f"Total Seeded Errors : {metrics['total']}",
        f"Caught             : {metrics['caught']}",
        f"Missed             : {metrics['missed']}",
        f"Catch Rate         : {metrics['catch_rate']:.1f}%",
        "",
        f"Precision          : {metrics['precision']}%",
        f"Recall             : {metrics['recall']}%",
        f"F1 Score           : {metrics['f1']}%",
        "",
        "By Category:",
    ]
    for cat, cm in metrics.get("by_category", {}).items():
        lines.append(
            f"  {cat.capitalize():12s}: {cm['caught']}/{cm['total']} "
            f"({cm['catch_rate']:.1f}%)"
        )
    return "\n".join(lines)

