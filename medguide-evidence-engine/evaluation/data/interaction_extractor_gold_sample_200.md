# Interaction extractor gold-sample protocol

This file contains **200** deterministic, stratified candidates.
It is an annotation set, not ground truth until reviewed.

## Annotation rules

1. Read the exact passage and open the source when context is truncated.
2. Judge the entity pair separately from the effect and action.
3. Use `Unclear` instead of guessing; it is not counted as negative.
4. `Should Rule Exist=No` means the passage should not produce this interaction rule.
5. A second reviewer should independently label at least 20% to measure agreement.

## Metrics after annotation

- Candidate precision: `Should Rule Exist=Yes / (Yes + No)`; exclude Unclear.
- Entity-pair accuracy, type accuracy, effect support, and action support are reported separately.
- Recall/F1 require additional negative source passages; this candidate-only sheet cannot measure recall.
- Report reviewer agreement (Cohen's kappa or weighted kappa) before resolving disagreements.

