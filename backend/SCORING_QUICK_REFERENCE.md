# Quick Reference: Scoring System Weights

## 🎯 Model Contributions to Final Score

```
┌─────────────────────────────────────────────────────────────────┐
│                     EVALUATION PIPELINE                          │
└─────────────────────────────────────────────────────────────────┘

    Student Answer + Model Answer
              │
              ▼
    ┌─────────────────────┐
    │   Semantic Gate     │ ◄──── If similarity < 30% → Score = 0
    │   (SBERT Check)     │
    └──────────┬──────────┘
               │ similarity ≥ 30% ✓
               ▼
    ┌──────────────────────────────────────────────────┐
    │         Feature Extraction & Scoring              │
    ├──────────────────────────────────────────────────┤
    │                                                   │
    │  1️⃣  SBERT Similarity Score                       │
    │     • Semantic similarity: 0.0 - 1.0             │
    │     • similarity_score = similarity × max_marks   │
    │                                                   │
    │  2️⃣  ANN Model Prediction                         │
    │     • Neural network trained score predictor     │
    │     • Direct score prediction: 0 - max_marks     │
    │                                                   │
    │  3️⃣  NLI Logical Check                            │
    │     • ENTAILMENT / NEUTRAL / CONTRADICTION       │
    │                                                   │
    └───────────────────┬──────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────────────┐
    │          DYNAMIC BLENDING                       │
    │  (Weights adjust based on similarity level)     │
    └─────────────────────────────────────────────────┘
              │
              ├──── Similarity ≥ 85% (HIGH) ────────────┐
              │     Weight: 70% SBERT + 30% ANN         │
              │     Reason: High confidence in semantic │
              │             similarity                   │
              │                                          │
              ├──── Similarity 75-84% (MEDIUM) ─────────┤
              │     Weight: 50% SBERT + 50% ANN         │
              │     Reason: Balanced trust in both      │
              │                                          │
              └──── Similarity 30-74% (LOWER) ──────────┘
                    Weight: 30% SBERT + 70% ANN
                    Reason: Trust ANN's learned patterns

              │
              ▼
    ┌─────────────────────────────────────────────────┐
    │         blended_score calculated                │
    └──────────────────┬──────────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────────┐
    │            NLI MULTIPLIER                       │
    ├─────────────────────────────────────────────────┤
    │  • ENTAILMENT     → × 1.0 (no penalty)         │
    │  • NEUTRAL        → × 0.7 (30% reduction)      │
    │  • CONTRADICTION  → × 0.3 (70% reduction)      │
    └──────────────────┬──────────────────────────────┘
                       │
                       ▼
              final_score = blended_score × nli_multiplier
                       │
                       ▼
    ┌─────────────────────────────────────────────────┐
    │              ROUNDING                           │
    │  • 3.5 and above  → 4 ⬆                        │
    │  • 3.49 and below → 3 ⬇                        │
    │  • Standard Python round() function             │
    └──────────────────┬──────────────────────────────┘
                       │
                       ▼
                 FINAL SCORE (Integer)
```

---

## 📊 Weight Distribution by Similarity Level

### High Similarity Scenario (≥85%)

```
┌─────────────────────────────────────────────┐
│  SBERT: ████████████████████████████ 70%   │
│  ANN:   ███████████ 30%                     │
│  NLI:   Multiplier (0.3-1.0)                │
└─────────────────────────────────────────────┘
```

**Why this split?**
When the student answer is very similar to the model answer (≥85%),
we have high confidence in the semantic similarity. SBERT is reliable
here, so we give it more weight.

---

### Medium Similarity Scenario (75-84%)

```
┌─────────────────────────────────────────────┐
│  SBERT: ████████████████████ 50%           │
│  ANN:   ████████████████████ 50%           │
│  NLI:   Multiplier (0.3-1.0)                │
└─────────────────────────────────────────────┘
```

**Why this split?**
Moderate similarity means we're less certain. Balance both models
equally - SBERT for semantic meaning, ANN for learned grading patterns.

---

### Lower Similarity Scenario (30-74%)

```
┌─────────────────────────────────────────────┐
│  SBERT: ███████████ 30%                     │
│  ANN:   ████████████████████████████ 70%   │
│  NLI:   Multiplier (0.3-1.0)                │
└─────────────────────────────────────────────┘
```

**Why this split?**
Lower similarity might miss contextual understanding. The ANN has
learned complex grading patterns from thousands of examples, so we
trust it more in ambiguous cases.

---

## 🔢 NLI Impact Examples

### Example 1: Full Score (ENTAILMENT)

```
Blended Score: 8.5
NLI Result: ENTAILMENT (×1.0)
Final: 8.5 × 1.0 = 8.5 → Rounded to 9
```

### Example 2: Partial Penalty (NEUTRAL)

```
Blended Score: 8.5
NLI Result: NEUTRAL (×0.7)
Final: 8.5 × 0.7 = 5.95 → Rounded to 6
```

### Example 3: Heavy Penalty (CONTRADICTION)

```
Blended Score: 8.5
NLI Result: CONTRADICTION (×0.3)
Final: 8.5 × 0.3 = 2.55 → Rounded to 3
```

---

## 🎓 Complete Example with Numbers

**Question**: "What is photosynthesis?" (10 marks)

**Model Answer**:
"Photosynthesis is the process by which plants convert light energy
into chemical energy, producing oxygen and glucose from CO2 and water."

**Student Answer**:
"Photosynthesis is when plants use sunlight to make food and oxygen
from carbon dioxide and water."

### Step-by-Step Calculation:

```
1️⃣  SBERT Similarity
   Similarity = 0.82 (82%)
   similarity_score = 0.82 × 10 = 8.2

2️⃣  ANN Prediction
   Features: [similarity=0.82, lengths, marks]
   ann_score = 7.8

3️⃣  Similarity Level Check
   82% falls in MEDIUM range (75-84%)
   → Use 50/50 blend

4️⃣  Blending
   blended_score = 0.5 × 8.2 + 0.5 × 7.8
                 = 4.1 + 3.9
                 = 8.0

5️⃣  NLI Check
   Result: ENTAILMENT (correct, just simplified)
   Multiplier: ×1.0

6️⃣  Final Score Calculation
   final_score = 8.0 × 1.0 = 8.0

7️⃣  Rounding
   8.0 → 8 (already integer)

✅  FINAL SCORE: 8/10
```

---

## 💡 Key Takeaways

| Component    | Role                 | Weight           | Impact          |
| ------------ | -------------------- | ---------------- | --------------- |
| **SBERT**    | Semantic similarity  | 30-70% (dynamic) | Base scoring    |
| **ANN**      | Learned prediction   | 30-70% (dynamic) | Base scoring    |
| **NLI**      | Logical verification | ×0.3 to ×1.0     | Multiplier      |
| **Rounding** | Final adjustment     | N/A              | Nearest integer |

**Formula**:

```python
similarity_score = similarity × max_marks
ann_score = neural_network_prediction()

# Dynamic blending
if similarity ≥ 0.85:
    blended = 0.7 × similarity_score + 0.3 × ann_score
elif similarity ≥ 0.75:
    blended = 0.5 × similarity_score + 0.5 × ann_score
else:
    blended = 0.3 × similarity_score + 0.7 × ann_score

# NLI multiplier
nli_multiplier = {
    'ENTAILMENT': 1.0,
    'NEUTRAL': 0.7,
    'CONTRADICTION': 0.3
}[nli_result]

final_score = blended × nli_multiplier
final_score = round(final_score)  # Standard rounding
```

---

## 🎯 Why This System Works

1. **Adaptive**: Weights change based on confidence level
2. **Holistic**: Combines semantic, learned, and logical checks
3. **Fair**: Heavy penalties only for contradictions
4. **Clear**: Integer scores are easier to understand
5. **Robust**: Multiple models catch different types of errors

This ensures accurate, fair, and explainable grading! 🎓✨
