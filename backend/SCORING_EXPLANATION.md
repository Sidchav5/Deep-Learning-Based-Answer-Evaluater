# 📊 Scoring System Explained

## Overview

The evaluation system uses a **hybrid scoring approach** that combines three AI models to provide accurate and fair assessment of student answers.

---

## 🧠 The Three Models

### 1. **SBERT (Sentence-BERT)** - Semantic Similarity

**Role**: Measures how semantically similar the student answer is to the model answer

**Weight in Final Score**: 30% - 70% (dynamic, based on similarity level)

**How it works**:

- Converts both answers into high-dimensional vectors (embeddings)
- Computes cosine similarity between vectors
- Output: Similarity score from 0.0 (completely different) to 1.0 (identical meaning)

**Example**:

```
Model Answer: "Python is a high-level programming language"
Student Answer: "Python is a high-level coding language"
Similarity: 0.92 (92% similar)
```

**Contribution to Final Score**:

```python
similarity_score = similarity × max_marks
# If similarity = 0.92 and max_marks = 10
# similarity_score = 0.92 × 10 = 9.2
```

---

### 2. **ANN Model (Artificial Neural Network)** - Deep Learning Prediction

**Role**: Predicts the score based on multiple learned features

**Weight in Final Score**: 30% - 70% (dynamic, inverse to SBERT weight)

**How it works**:

- Trained on thousands of Q&A pairs with actual scores
- Learns complex patterns that humans use when grading
- Takes input features: similarity, answer length, model answer length, marks
- Outputs: Predicted score directly

**Example**:

```
Input Features:
- Similarity: 0.92
- Student answer length: 45 words
- Model answer length: 50 words
- Max marks: 10

ANN Prediction: 8.7
```

**Why ANN is Important**:

- Captures nuanced grading patterns
- Considers answer completeness, not just similarity
- Learned from human grading behavior

---

### 3. **NLI Model (Natural Language Inference)** - Logical Consistency Check

**Role**: Verifies logical relationship between answers

**Weight in Final Score**: Acts as a **multiplier** (0.3×, 0.7×, or 1.0×)

**How it works**:

- Uses RoBERTa-MNLI model
- Checks if student answer logically follows from model answer
- Three possible outcomes:

#### **ENTAILMENT** (✅ Multiplier: 1.0×)

- Student answer logically follows from model answer
- Concepts are consistent
- **Effect**: No penalty

**Example**:

```
Model: "Earth revolves around the Sun"
Student: "The Sun is at the center with Earth orbiting it"
Result: ENTAILMENT → Score × 1.0
```

#### **NEUTRAL** (⚠️ Multiplier: 0.7×)

- Student answer is partially related
- Some relevant information but incomplete
- **Effect**: 30% penalty

**Example**:

```
Model: "Photosynthesis produces oxygen and glucose"
Student: "Plants make oxygen during photosynthesis"
Result: NEUTRAL → Score × 0.7
```

#### **CONTRADICTION** (❌ Multiplier: 0.3×)

- Student answer contradicts model answer
- Contains factually incorrect information
- **Effect**: 70% penalty

**Example**:

```
Model: "Mitochondria generates ATP"
Student: "Mitochondria stores DNA only"
Result: CONTRADICTION → Score × 0.3
```

---

## 🔄 Complete Scoring Flow

### Step 1: Semantic Gate

```python
if similarity < 0.30:
    final_score = 0.0
    reason = "Very low semantic similarity"
```

**Explanation**: If answer is less than 30% similar, it's considered irrelevant → automatic 0

---

### Step 2: Dynamic Blending (SBERT + ANN)

The system **dynamically adjusts weights** based on similarity level:

#### **High Similarity (≥85%)**

```python
Weight Distribution: 70% SBERT + 30% ANN
blended_score = 0.7 × similarity_score + 0.3 × ann_score
```

**Why?**: High similarity means answer is very close to model → trust SBERT more

**Example**:

```
Similarity: 0.90 (90%)
Max marks: 10
similarity_score = 0.90 × 10 = 9.0
ann_score = 8.5

blended_score = 0.7 × 9.0 + 0.3 × 8.5
              = 6.3 + 2.55
              = 8.85
```

#### **Medium Similarity (75-84%)**

```python
Weight Distribution: 50% SBERT + 50% ANN
blended_score = 0.5 × similarity_score + 0.5 × ann_score
```

**Why?**: Moderate similarity → balance both models equally

**Example**:

```
Similarity: 0.80 (80%)
Max marks: 10
similarity_score = 0.80 × 10 = 8.0
ann_score = 7.2

blended_score = 0.5 × 8.0 + 0.5 × 7.2
              = 4.0 + 3.6
              = 7.6
```

#### **Lower Similarity (30-74%)**

```python
Weight Distribution: 30% SBERT + 70% ANN
blended_score = 0.3 × similarity_score + 0.7 × ann_score
```

**Why?**: Lower similarity might miss context → trust ANN's learned patterns more

**Example**:

```
Similarity: 0.65 (65%)
Max marks: 10
similarity_score = 0.65 × 10 = 6.5
ann_score = 5.8

blended_score = 0.3 × 6.5 + 0.7 × 5.8
              = 1.95 + 4.06
              = 6.01
```

---

### Step 3: NLI Modifier

Apply logical consistency check:

```python
if nli_label == "ENTAILMENT":
    final_score = blended_score × 1.0  # No penalty
elif nli_label == "NEUTRAL":
    final_score = blended_score × 0.7  # 30% reduction
elif nli_label == "CONTRADICTION":
    final_score = blended_score × 0.3  # 70% reduction
```

**Example**:

```
blended_score = 8.85
NLI Result: ENTAILMENT

final_score = 8.85 × 1.0 = 8.85
```

---

### Step 4: Rounding

**NEW**: Scores are rounded to nearest integer:

- **3.50 and above** → Round UP → **4**
- **3.49 and below** → Round DOWN → **3**

```python
import math
final_score = round(final_score)  # Standard rounding
```

**Examples**:

```
8.85 → 9
8.49 → 8
7.50 → 8
7.49 → 7
3.50 → 4
3.49 → 3
```

---

## 📈 Complete Example

**Question**: "What is machine learning?" (Max Marks: 10)

**Model Answer**:
"Machine learning is a subset of AI that enables computers to learn from data without explicit programming."

**Student Answer**:
"Machine learning allows computers to learn from data and improve automatically."

### Evaluation Process:

#### Step 1: SBERT Similarity

```
Similarity = 0.88 (88%)
✅ Pass semantic gate (> 0.30)
```

#### Step 2: Feature Extraction & ANN

```
Features:
- Similarity: 0.88
- Student length: 52 chars
- Model length: 98 chars
- Max marks: 10

ANN Predicted Score: 8.2
```

#### Step 3: Dynamic Blending

```
Similarity ≥ 85% → Use 70/30 blend

similarity_score = 0.88 × 10 = 8.8
ann_score = 8.2

blended_score = 0.7 × 8.8 + 0.3 × 8.2
              = 6.16 + 2.46
              = 8.62
```

#### Step 4: NLI Check

```
NLI Model: ENTAILMENT
Multiplier: 1.0

final_score = 8.62 × 1.0 = 8.62
```

#### Step 5: Rounding

```
8.62 → 9 (rounded up)

FINAL SCORE: 9/10
```

---

## 🎯 Model Weight Summary

| Scenario                   | SBERT Weight | ANN Weight | NLI Effect |
| -------------------------- | ------------ | ---------- | ---------- |
| High Similarity (≥85%)     | **70%**      | 30%        | Multiplier |
| Medium Similarity (75-84%) | **50%**      | **50%**    | Multiplier |
| Lower Similarity (30-74%)  | 30%          | **70%**    | Multiplier |
| Very Low Similarity (<30%) | -            | -          | Auto 0     |

**NLI Multipliers**:

- ✅ ENTAILMENT: **×1.0** (no penalty)
- ⚠️ NEUTRAL: **×0.7** (30% penalty)
- ❌ CONTRADICTION: **×0.3** (70% penalty)

---

## 💡 Key Insights

1. **SBERT** = "Does it mean the same thing?"
2. **ANN** = "How would a human grade this?"
3. **NLI** = "Is it logically correct?"

Together, they provide:

- ✅ Semantic understanding (SBERT)
- ✅ Human-like grading (ANN)
- ✅ Factual verification (NLI)
- ✅ Fair rounding (Standard rounding)

---

## 🔍 Why This Approach?

### Traditional Keyword Matching Problems:

❌ "Machine learning uses algorithms" vs "ML employs algorithms"

- Different words, same meaning → would score low

### Our Hybrid Approach:

✅ SBERT catches semantic similarity (both mean the same)
✅ ANN considers overall quality and completeness
✅ NLI verifies logical correctness
✅ Dynamic weighting adapts to confidence level

**Result**: More accurate, fair, and intelligent grading! 🎓
