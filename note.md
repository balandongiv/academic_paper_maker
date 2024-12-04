# CS 229 - Supervised Learning Cheatsheet

**By [Afshine Amidi](https://twitter.com/afshinea) and [Shervine Amidi](https://twitter.com/shervinea)**

## Table of Contents
1. [Introduction to Supervised Learning](#introduction-to-supervised-learning)
2. [Notations and General Concepts](#notations-and-general-concepts)
3. [Linear Models](#linear-models)
4. [Support Vector Machines](#support-vector-machines)
5. [Generative Learning](#generative-learning)
6. [Tree-based and Ensemble Methods](#tree-based-and-ensemble-methods)
7. [Other Non-Parametric Approaches](#other-non-parametric-approaches)
8. [Learning Theory](#learning-theory)

---

## Introduction to Supervised Learning

Given a set of data points \( \{x^{(1)}, ..., x^{(m)}\} \) associated with outcomes \( \{y^{(1)}, ..., y^{(m)}\} \), we aim to build a classifier that learns to predict \( y \) from \( x \).

### Type of Prediction

|               | **Regression**        | **Classification**         |
|---------------|-----------------------|----------------------------|
| **Outcome**   | Continuous            | Class                     |
| **Examples**  | Linear regression     | Logistic regression, SVM, Naive Bayes |

### Type of Model

|                       | **Discriminative Model**         | **Generative Model**                 |
|-----------------------|----------------------------------|--------------------------------------|
| **Goal**             | Directly estimate \( P(y|x) \)   | Estimate \( P(x|y) \), deduce \( P(y|x) \) |
| **What's Learned**    | Decision boundary               | Probability distributions of the data |
| **Examples**          | Regressions, SVMs              | GDA, Naive Bayes                     |

---

## Notations and General Concepts

### Hypothesis
The hypothesis \( h_\theta \) represents the model chosen. For input data \( x^{(i)} \), the model predicts \( h_\theta(x^{(i)}) \).

### Loss Function
A loss function \( L(z, y) \) measures the difference between the predicted value \( z \) and the real value \( y \).

| Loss Type              | Formula                             | Example Algorithm       |
|------------------------|-------------------------------------|-------------------------|
| Least Squared Error    | \( \frac{1}{2}(y - z)^2 \)         | Linear regression       |
| Logistic Loss          | \( \log(1 + \exp(-yz)) \)          | Logistic regression     |
| Hinge Loss             | \( \max(0, 1 - yz) \)              | SVM                    |
| Cross-Entropy          | \( -[y\log(z) + (1-y)\log(1-z)] \) | Neural Network          |

### Gradient Descent
Update rule:  
\[
\theta \leftarrow \theta - \alpha \nabla J(\theta)
\]  
Where \( \alpha \) is the learning rate and \( J(\theta) \) is the cost function.

---

## Linear Models

### Linear Regression
#### Normal Equations
\[
\theta = (X^TX)^{-1}X^Ty
\]

#### LMS Algorithm
\[
\forall j, \quad \theta_j \leftarrow \theta_j + \alpha \sum_{i=1}^m \left[ y^{(i)} - h_\theta(x^{(i)}) \right] x_j^{(i)}
\]

### Logistic Regression
#### Sigmoid Function
\[
g(z) = \frac{1}{1 + e^{-z}} \quad \in (0,1)
\]

#### Logistic Regression Formula
\[
\phi = P(y=1|x;\theta) = \frac{1}{1 + \exp(-\theta^T x)} = g(\theta^T x)
\]

---

## Support Vector Machines

### Optimal Margin Classifier
\[
h(x) = \text{sign}(w^T x - b)
\]

Optimization problem:
\[
\min \frac{1}{2}||w||^2 \quad \text{such that } y^{(i)} (w^T x^{(i)} - b) \geq 1
\]

### Hinge Loss
\[
L(z, y) = \max(0, 1 - yz)
\]

---

## Generative Learning

### Gaussian Discriminant Analysis
Assumes:
- \( y \sim \text{Bernoulli}(\phi) \)
- \( x|y=0 \sim \mathcal{N}(\mu_0, \Sigma) \)
- \( x|y=1 \sim \mathcal{N}(\mu_1, \Sigma) \)

Estimates:
\[
\widehat{\phi} = \frac{1}{m} \sum_{i=1}^m 1_{\{y^{(i)} = 1\}}
\]

### Naive Bayes
Assumes features of \( x \) are independent:
\[
P(x|y) = \prod_{i=1}^n P(x_i|y)
\]

---

## Tree-based and Ensemble Methods

### CART (Decision Trees)
Binary tree structure, interpretable but prone to overfitting.

### Random Forest
Combines decision trees with random feature selection for robustness.

### Boosting
- **Adaboost**: Focuses on misclassified examples.
- **Gradient Boosting**: Focuses on residuals (e.g., XGBoost).

---

## Other Non-Parametric Approaches

### k-Nearest Neighbors (\( k \)-NN)
Determines the response of a point based on its \( k \) nearest neighbors.

---

## Learning Theory

### Union Bound
\[
P(A_1 \cup ... \cup A_k) \leq P(A_1) + ... + P(A_k)
\]

### Hoeffding Inequality
\[
P(|\phi - \widehat{\phi}| > \gamma) \leq 2 \exp(-2\gamma^2 m)
\]

### Probably Approximately Correct (PAC)
PAC assumptions:
- Training and testing sets follow the same distribution.
- Training examples are drawn independently.

---

[View PDF version on GitHub](https://github.com/afshinea/stanford-cs-229-machine-learning/blob/master/en/cheatsheet-supervised-learning.pdf)
