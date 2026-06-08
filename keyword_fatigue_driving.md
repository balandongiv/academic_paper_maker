Below are **Scopus Advanced Search** strings you can copy into Scopus. I used `TITLE-ABS-KEY()` because your topic should appear in the title, abstract, or keywords. Scopus Advanced Search supports field codes and Boolean/proximity operators, and Elsevier recommends using parentheses to avoid wrong Boolean interpretation. ([www.elsevier.com][1])

### Basic filter to add to every search

```text
AND PUBYEAR > 2015
AND LANGUAGE(english)
AND (DOCTYPE(ar) OR DOCTYPE(cp))
```

`ar` = article, `cp` = conference paper. Scopus also indexes conference material, including conference papers. ([www.elsevier.com][2])
If Scopus rejects `LANGUAGE(english)` or `DOCTYPE(...)` in your interface, run the search first, then apply **English**, **Article**, and **Conference Paper** from the left-side filters.

---

## 1. Broad search: driving fatigue/drowsiness + EEG + AI/ML

```text
TITLE-ABS-KEY(
  (
    "driver fatigue" OR "driving fatigue" OR "driver drowsiness" OR
    "driving drowsiness" OR "drowsy driving" OR "driver sleepiness" OR
    "driving sleepiness" OR "driver vigilance" OR "driving vigilance" OR
    "fatigue detection" OR "drowsiness detection"
  )
  AND
  (
    EEG OR electroencephalograph* OR electroencephalogram* OR electroencephalography
  )
  AND
  (
    "machine learning" OR "deep learning" OR "artificial intelligence" OR
    classification OR classifier OR "neural network" OR "support vector machine" OR SVM OR
    CNN OR LSTM OR RNN OR transformer OR "random forest"
  )
)
AND PUBYEAR > 2015
AND LANGUAGE(english)
AND (DOCTYPE(ar) OR DOCTYPE(cp))
```

---

## 2. More focused: human driving fatigue/drowsiness classification using EEG

```text
TITLE-ABS-KEY(
  (
    driver* OR driving OR "vehicle driver*" OR "car driver*" OR "human driver*"
  )
  AND
  (
    fatigue OR drowsiness OR sleepy OR sleepiness OR vigilance OR alertness OR inattention
  )
  AND
  (
    EEG OR electroencephalograph* OR electroencephalogram* OR electroencephalography
  )
  AND
  (
    classification OR classify OR classifier OR "fatigue classification" OR
    "drowsiness classification" OR "state classification"
  )
  AND
  (
    "machine learning" OR "deep learning" OR "artificial intelligence" OR AI
  )
)
AND PUBYEAR > 2015
AND LANGUAGE(english)
AND (DOCTYPE(ar) OR DOCTYPE(cp))
```

---

## 3. Deep learning specific search

```text
TITLE-ABS-KEY(
  (
    "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
    "driving drowsiness" OR "drowsy driving"
  )
  AND
  (
    EEG OR electroencephalograph* OR electroencephalography
  )
  AND
  (
    "deep learning" OR CNN OR "convolutional neural network" OR LSTM OR
    "long short-term memory" OR RNN OR "recurrent neural network" OR
    transformer OR "attention mechanism" OR "graph neural network" OR GNN
  )
)
AND PUBYEAR > 2015
AND LANGUAGE(english)
AND (DOCTYPE(ar) OR DOCTYPE(cp))
```

---

## 4. Machine learning classical models search

```text
TITLE-ABS-KEY(
  (
    "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
    "drowsy driving" OR "driver vigilance"
  )
  AND
  (
    EEG OR electroencephalograph* OR electroencephalography
  )
  AND
  (
    "machine learning" OR SVM OR "support vector machine" OR
    "random forest" OR "decision tree" OR kNN OR "k-nearest neighbor" OR
    "naive bayes" OR "logistic regression" OR XGBoost OR AdaBoost
  )
  AND
  (
    classification OR classifier OR detection OR recognition
  )
)
AND PUBYEAR > 2015
AND LANGUAGE(english)
AND (DOCTYPE(ar) OR DOCTYPE(cp))
```

---

## 5. Cross-subject / subject-independent search

```text
TITLE-ABS-KEY(
  (
    "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
    "driving drowsiness" OR "drowsy driving"
  )
  AND
  (
    EEG OR electroencephalograph* OR electroencephalography
  )
  AND
  (
    "machine learning" OR "deep learning" OR classification OR classifier
  )
  AND
  (
    "cross subject" OR "cross-subject" OR "inter subject" OR "inter-subject" OR
    "subject independent" OR "subject-independent" OR "leave one subject out" OR
    "leave-one-subject-out" OR LOSO OR "domain adaptation" OR
    "transfer learning" OR generalization OR generalisation
  )
)
AND PUBYEAR > 2015
AND LANGUAGE(english)
AND (DOCTYPE(ar) OR DOCTYPE(cp))
```

---

## 6. XAI / explainable AI search

```text
TITLE-ABS-KEY(
  (
    "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
    "driving drowsiness" OR "drowsy driving"
  )
  AND
  (
    EEG OR electroencephalograph* OR electroencephalography
  )
  AND
  (
    "machine learning" OR "deep learning" OR "artificial intelligence" OR classification
  )
  AND
  (
    XAI OR "explainable artificial intelligence" OR "explainable AI" OR
    "interpretable machine learning" OR interpretability OR explainability OR
    SHAP OR LIME OR "Grad-CAM" OR saliency OR "attention mechanism" OR
    "feature importance"
  )
)
AND PUBYEAR > 2015
AND LANGUAGE(english)
AND (DOCTYPE(ar) OR DOCTYPE(cp))
```

---

## 7. Binary and multi-class classification search

```text
TITLE-ABS-KEY(
  (
    "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
    "driving drowsiness" OR "driver vigilance"
  )
  AND
  (
    EEG OR electroencephalograph* OR electroencephalography
  )
  AND
  (
    "machine learning" OR "deep learning" OR classifier OR classification
  )
  AND
  (
    binary OR "binary classification" OR "two class" OR "two-class" OR
    multiclass OR "multi class" OR "multi-class" OR "three class" OR
    "three-class" OR "fatigue level*" OR "drowsiness level*" OR
    alert OR drowsy OR fatigued
  )
)
AND PUBYEAR > 2015
AND LANGUAGE(english)
AND (DOCTYPE(ar) OR DOCTYPE(cp))
```

---

## 8. Driving simulator search

Many EEG driving-fatigue studies use a simulator, so this can help.

```text
TITLE-ABS-KEY(
  (
    "driving simulator" OR "simulated driving" OR "driver simulation" OR
    "virtual driving" OR "real driving" OR "on-road driving"
  )
  AND
  (
    fatigue OR drowsiness OR sleepiness OR vigilance OR alertness
  )
  AND
  (
    EEG OR electroencephalograph* OR electroencephalography
  )
  AND
  (
    "machine learning" OR "deep learning" OR classification OR classifier OR
    "artificial intelligence"
  )
)
AND PUBYEAR > 2015
AND LANGUAGE(english)
AND (DOCTYPE(ar) OR DOCTYPE(cp))
```

---

## 9. EEG features + ML classification search

Useful if you want papers discussing EEG frequency bands or feature extraction.

```text
TITLE-ABS-KEY(
  (
    "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR "drowsy driving"
  )
  AND
  (
    EEG OR electroencephalograph* OR electroencephalography
  )
  AND
  (
    "feature extraction" OR "frequency band*" OR alpha OR beta OR theta OR delta OR
    "power spectral density" OR PSD OR "time frequency" OR "wavelet transform" OR
    "entropy" OR "differential entropy"
  )
  AND
  (
    classification OR classifier OR "machine learning" OR "deep learning"
  )
)
AND PUBYEAR > 2015
AND LANGUAGE(english)
AND (DOCTYPE(ar) OR DOCTYPE(cp))
```

---

## 10. Very narrow “best match” search

Use this when the broad searches return too many unrelated papers.

```text
TITLE-ABS-KEY(
  (
    "driver drowsiness detection" OR "driver fatigue detection" OR
    "driving drowsiness detection" OR "driving fatigue detection"
  )
  AND
  (
    EEG OR electroencephalography
  )
  AND
  (
    "machine learning" OR "deep learning"
  )
  AND
  (
    classification OR classifier
  )
)
AND PUBYEAR > 2015
AND LANGUAGE(english)
AND (DOCTYPE(ar) OR DOCTYPE(cp))
```

---

## Extra keywords you should consider adding

For **fatigue/drowsiness concept**:

```text
"mental fatigue" OR "cognitive fatigue" OR "reduced vigilance" OR
"vigilance decrement" OR "driver alertness" OR "driver inattention" OR
"sleepiness detection" OR "fatigue level" OR "drowsiness level"
```

For **EEG signal**:

```text
"brain signal*" OR "brain wave*" OR "brainwave*" OR "physiological signal*" OR
"EEG signal*" OR "EEG-based"
```

For **AI/ML models**:

```text
"neural network*" OR "convolutional neural network" OR CNN OR LSTM OR RNN OR
transformer OR "attention network" OR "support vector machine" OR SVM OR
"random forest" OR XGBoost OR "ensemble learning"
```

For **cross-subject/generalization**:

```text
"subject-independent" OR "cross-subject" OR "inter-subject" OR
"leave-one-subject-out" OR LOSO OR "domain adaptation" OR "transfer learning" OR
"generalization" OR "personalized model"
```

For **XAI**:

```text
XAI OR explainability OR interpretability OR "explainable AI" OR
"explainable artificial intelligence" OR SHAP OR LIME OR saliency OR
"feature importance" OR "attention visualization"
```

My recommended starting order: run **Search 1**, then **Search 5** for cross-subject papers, then **Search 6** for XAI papers.

[1]: https://www.elsevier.com/products/scopus/search "Scopus search | Elsevier"
[2]: https://www.elsevier.com/products/scopus/content?utm_source=chatgpt.com "Scopus content"
