## Sensor systems

# Deep Learning-Based Attention Mechanism for Automatic Drowsiness Detection Using EEG Signal

### Chiranjevulu Divvala[1,2] and Madhusudhan Mishra[1][∗]

1Electronics and Communication Engineering, North Eastern Regional Institute of Science and Technology (NERIST), Nirjuli, Arunachal

_Pradesh 791109, India_
2Department of Electronics and Communication Engineering, Aditya Institute of Technology and Management, Tekkali 532201, India
∗Senior Member, IEEE

Manuscript received 18 December 2023; revised 24 January 2024; accepted 3 February 2024. Date of publication 8 February 2024; date of current version
28 February 2024.

Abstract—An electroencephalograph (EEG) is the basic medical tool to identify disorders related to brain activity. Drowsiness is a natural signal from the body indicating the need for rest and sleep to restore physical and mental well-being.
Drowsiness is characterized by lethargy, fatigue, and a strong inclination toward sleep. It is often accompanied by reduced
alertness and increased difficulty in maintaining attention and focus on tasks. Individuals experiencing drowsiness may
find staying awake challenging and exhibit slower reaction times. This diminished cognitive function can lead to accidents,
errors, and decreased performance in various activities. Wearable sensors are utilized in real-time to identify drowsiness
detection. However, an automated diagnosis tool is very helpful in identifying drowsiness, and detection is an important
task. Therefore, this work proposes a deep learning-based attention mechanism to detect the drowsiness state. This letter
uses a publicly available MIT-BIH standard EEG database for experimentation. The proposed model provides a performance accuracy of 98.38% in drowsiness detection. The experiment outcomes demonstrate an enhanced detection capability when compared with current state-of-the-art methods for detecting drowsiness using single-channel EEG signals.

Index Terms—Sensor systems, convolutional neural networks (CNNs), deep learning (DL), electroencephalograph (EEG), health care,
wearable sensor data.


#### I. INTRODUCTION

In the realm of medical diagnostics, the electroencephalograph
(EEG) stands as a fundamental tool, indispensable for identifying
disorders related to brain activity [1]. Drowsiness, a natural bodily
signal indicating the need for rest and rejuvenating sleep, is characterized by lethargy, fatigue, and an unmistakable inclination toward
slumber. This manuscript explores the potential of the proposed model
to significantly outperform existing methodologies. By integrating a
deep learning (DL) framework, our approach addresses the limitations
of single-channel EEG signal-based methods, showcasing an enhanced
detection capability [2]. As we delve into the intricacies of our experimental outcomes, it becomes evident that the presented model
stands as a promising advancement in the field of drowsiness detection,
offering a robust solution with broad implications for both medical and
technological domains. EEG signals, which measure electrical activity
in the brain, are often analyzed in terms of their frequency components,
known as subbands [3]. These subbands provide valuable insights into
the different neural processes and cognitive functions occurring in the
brain. Here, are the main EEG signal subbands and their associated
characteristics [4] as follows.

1) Delta (δ) (0.5–4 Hz): Delta waves are slow-frequency oscilla
   tions typically associated with deep sleep, unconsciousness, and
   certain neurological disorders. Their presence in waking states
   might indicate abnormal brain functioning.
2) Theta (θ) (4–8 Hz): Theta waves are prominent during light

sleep, meditation, and deep relaxation. In wakeful states, they

Corresponding authors: Chiranjevulu Divvala; Madhusudhan Mishra (email:
[chiru.divvala@gmail.com; ecmadhusudhan@gmail.com)](mailto:chiru.divvala@gmail.com; ignorespaces ecmadhusudhan@gmail.com)
Associate Editor: S. Ostadabbas.
Digital Object Identifier 10.1109/LSENS.2024.3363735


may be linked to creative thinking, problem-solving, and memory retrieval.
3) Alpha(α)(8–13Hz): Alphawavesarepredominantduringstates

of relaxation and when the eyes are closed but the individual is
awake. They are commonly associated with a calm and alert
mental state.
4) Beta (β) (13–30 Hz): Beta waves are characteristic of active,

alert, and conscious states, such as focused attention, problemsolving, and decision-making. Higher beta frequencies may
indicate stress or anxiety.
5) Gamma (γ ) (30–40 Hz and above): Gamma waves are fast
   frequency oscillations associated with cognitive processes, such
   as memory formation, perception, and problem-solving. They
   are also linked to conscious awareness and high-level information processing.
   Analyzing EEG signal subbands is crucial in understanding brain
   activity and can have applications in various fields, including neuroscience, clinical medicine, and human–computer interaction [3].
   Researchers and clinicians use advanced signal-processing techniques
   to extract features from these subbands to identify patterns related
   to specific cognitive states or neurological conditions. For instance,
   changes in the ratio of certain subbands may be indicative of cognitive
   disorders or neurological diseases. In recent years, the application of
   machine learning (ML) and DL techniques in the realm of drowsiness
   detection has garnered significant attention [5]. These sophisticated
   algorithms have shown promise in providing more accurate and efficient methods for identifying signs of drowsiness compared with
   traditional approaches. ML models, ranging from classic algorithms
   to more advanced techniques, such as support vector machines and
   random forests, have been employed to analyze various physiological signals associated with drowsiness. These signals often include


features extracted from EEG data, eye movement patterns, and other
relevant physiological parameters. While these methods have demonstrated success, they sometimes struggle to capture the complex and
dynamicnatureofdrowsiness,particularlyinreal-worldscenarios.DL,
with its ability to automatically learn hierarchical representations from
data, has shown great promise in addressing some of the limitations
of traditional ML approaches. Convolutional neural networks (CNNs)
and recurrent neural networks have been applied to drowsiness detection tasks, showcasing improved performance in feature extraction,
and temporal modeling. However, despite the advancements, several
challenges persist in the domain of drowsiness detection. One major
obstacle is the lack of universally standardized datasets, hindering
the development and comparison of models across different studies.
The inherent variability in human physiology and behavior further
complicates the creation of robust models that generalize well to
diverse populations and contexts. In addition, the real-time application
of these models presents a significant challenge. Achieving quick and
accurate drowsiness detection in dynamic environments, such as drivingoroperatingheavymachinery,demandsnotonlyprecisealgorithms
but also efficient and low-latency implementations. Furthermore, the
interpretability of DL models remains a concern. Understanding the
decision-making process of these complex models is crucial, especially in applications where human lives are at stake such as in
transportation.

This letter presents a groundbreaking DL approach for EEG-based
drowsiness detection, aligning with innovative sensor technologies
and applications. Utilizing EEG sensors for real-time brainwave monitoring, our model integrates advanced neural network techniques
to identify drowsiness states accurately. This contribution advances
sensor-based health monitoring, offering significant implications for
fields requiring cognitive state assessment, such as transportation
and occupational health. Our work demonstrates the effectiveness
of EEG sensors in practical applications and sets a new benchmark
in sensor-based cognitive state analysis. In this letter, to explore the
potential of DL for drowsiness detection, overcoming these challenges
will be essential to ensuring the practical and reliable deployment of
such technologies in real-world scenarios. The major contributions of
the proposed work are organized as follows.

1) The decision to use a single-channel EEG signal demonstrates

efficiency without sacrificing accuracy. This is particularly valuable in scenarios where access to multiple EEG channels might
be limited or impractical, making your model more applicable
in real-world settings
2) Theintegrationofconvolutionallayers, longshort-termmemory

(LSTM), and D-residual blocks in parallel allows for a comprehensive extraction of both spatial and temporal features from
the single-channel EEG signals. This hybrid approach ensures
that the model captures relevant patterns and dependencies in
the data.
3) By incorporating LSTM layers, your architecture excels in

modeling temporal dependencies within the EEG signals. The
LSTM’s ability to retain information over extended sequences
is particularly advantageous for capturing nuanced patterns and
trends related to drowsiness.
4) The utilization of D-residual blocks further enhances feature

representation by promoting the learning of discriminative features. The residual connections within these blocks facilitate the
flow of information and gradients, contributing to more effective
feature extraction and reducing the risk of vanishing gradients.
5) The combination of these architectural elements is not only

effective in terms of accuracy but also demonstrates attention to
real-time application. The efficient processing of single-channel


Fig. 1. Proposed methodology for detecting drowsiness using DL
technique.

EEG signals, coupled with the parallel feature extraction blocks,
suggests a design that could be well-suited for applications
requiring timely and dynamic drowsiness detection.

#### II. MATERIALS

The proposed work relies on the EEG sleep data publicly available in the National Institute of Health (NIH) research resource
available at Physionet. This resource proves invaluable for analyzing
drowsiness [1]. Collected from various subjects at different times, the
database categorizes data into five labels: wakefulness (W), nonrapid
eye movement (REM), REM, move state, and not scored state. These
labels are further classified into wake and drowsiness states, with W
representing a fully wakeful state and the other states considered as
drowsy states. The data has a sampling frequency of 100 Hz, adhering
to the Nyquist criteria, indicating a maximum frequency content in the
signal of 50 Hz.

#### III. PROPOSED METHODOLOGY

The block diagram of the proposed methodology is shown in Fig. 1.
The important steps followed in this work for drowsiness detection are
1) preprocessing and 2) classification using hybrid DL architecture.
   The proposed methodology aims to implement a hybrid DL model for
   EEG classification. The process involves several stages, including preprocessing, data splitting, convolution layer, LSTM layer, 1-D residual
   blocks, concatenation, bidirectional gated recurrent units (Bi-GRU),
   andfinalclassification.Inthisletter,weutilizedprerecordedEEGsleep
   data publicly available from the NIH Physionet research resource [6].
   Filtering techniques were used to remove noise from EEG signals. We
   have recorded each preprocessing step, including filtering and channel
   selection.

In this study, EEG signal preprocessing involved several key steps to
ensure data quality and relevance for drowsiness detection. Initially, we
applied a bandpass filter (0.5–45 Hz) to remove high-frequency noise
and artifacts while preserving the essential features of the EEG signals.
Following this, the signals underwent normalization to standardize the
amplitude variations across different subjects. The continuous EEG
data was then segmented into epochs of 1-s duration, providing a
balance between temporal resolution and computational efficiency.
To address potential signal variability, a common average referencing method was employed to rereference the EEG data, enhancing
the signal-to-noise ratio. Finally, artifact rejection was conducted
manually to remove segments contaminated with eye blinks, muscle


-----

movements, or other nonbrain activities, ensuring the purity of the
EEG data for subsequent analysis.

The preprocessed data was split into training (80%) and testing
(20%) sets. After preprocessing, the signal is passed to the proposed
DL model to extract in-depth features using different blocks, such
as convolutional, residual, LSTM, and Bi-GRU. Convolutional layers
are to extract local features from the preprocessed EEG data. Integrating an LSTM layer to capture temporal dependencies in EEG
data. Implementing 1-D residual blocks to facilitate the learning of
residual features. Different features are extracted using these layers.
Then, the features from the LSTM layer and 1-D residual blocks are
concatentated. Bi-GRU are also incorporated in the architecture for
capturing bidirectional temporal dependencies. Max pooling selects
the most relevant features within each pooling region, emphasizing
the most salient information from the convolutional layer. This is
particularly useful in the context of EEG signals where certain patterns
and frequencies are indicative of sleep states. Connected layers for
further feature refinement and classification. The flattened output from
the max pooling layer is passed through FC1, a fully connected layer
with rectified linear unit (ReLU) activation, introducing nonlinearity
to capture complex relationships in the EEG data. Subsequently, the
output is connected to FC2, another fully connected layer with a
Softmax activation function. This final layer normalizes the output into
probability scores, indicating the likelihood of the input EEG signal
belonging to the “normal” or “drowsy” class. Optimal parameters
could include a configuration with 1-D convolutional layers, each with
32–64 filters and filter sizes around five. Incorporate LSTM layers with
around 50 units for temporal feature extraction. A moderate learning
rate of 0.001, combined with an Adam optimizer, is advisable for
effective training. Batch sizes between 32 can offer a good balance for
computational efficiency and model stability. Implement dropout rates
ranging from 0.2 to 0.5 to reduce overfitting, especially in densely
connected layers. Fine-tuning these parameters based on validation
data performance is crucial for optimizing your network’s efficacy.

The classification decision is determined based on these probabilities, and if the probability of the “drowsy” class surpasses a predefined
threshold, the model classifies the EEG signal as “drowsy”; otherwise,
it is labeled as “normal.” This proposed methodology state-of-the-art
DL architectures to ensure the secure and transparent implementation
of a CNN model for EEG sleep data classification. In this proposed
methodology, the integration of convolution layers, LSTM layers, 1-D
residual blocks, Bi-GRU layers, and attention mechanisms creates
a comprehensive model for automatic drowsiness detection using
EEG signals. The step-by-step process ensures the extraction of local
features, emphasizing relevant information through attention mechanisms, and making the model capable of discerning between normal
and drowsy states.

#### IV. EXPERIMENTAL RESULTS AND DISCUSSION

In the experimental evaluation of the proposed methodology for
EEG sleep data classification, achieving an impressive 98.38% accuracy, the results and discussions are further detailed through the
analysis of accuracy and loss graphs, both plotted over 75 epochs. The
model is evaluated on the testing set using metrics, such as accuracy,
precision, recall, and F1-score. Metrics are explained as follows [5].
The performance curves of the proposed method are shown in Fig. 2.
The accuracy graph illustrates the performance of the model over 75
epochs. The upward trend signifies the continuous improvement of the
model’s ability to correctly classify EEG signals as normal or drowsy.
A sustained high accuracy rate indicates the stability and effectiveness


Fig. 2. Performance curves (a) Accuracy and (b) Loss, of the proposed method for drowsiness detection.

Fig. 3. Confusion matrix of the proposed method for drowsiness
detection.

TABLE 1. Performance Matrix of the Proposed Method

loss graph depicts the reduction in the model’s loss function over
epochs. A decreasing trend in the loss indicates that the model is
effectively learning and converging toward optimal parameters. A
smooth convergence, as evidenced by the loss graph, aligns with the
high accuracy achieved by the model. The continuous improvement in
accuracy and the loss reduction indicates the model’s capacity to learn
and generalize from the EEG dataset.

The confusion matrix provides detailed insights into the model’s
predictive patterns, offering valuable information on specific instances
of misclassification. This understanding helps refine the attention
mechanism and the overall model architecture. The high accuracy,
combined with precision, recall, and F1 score, underscores the reliability and robustness of the proposed technique. These metrics
collectively demonstrate the model’s ability to discern between drowsy
and nondrowsy states in EEG signals effectively. The confusion matrix
of the proposed method is depicted in Fig. 3; from this, it is observed
that very few instances are misclassified. Therefore, the proposed
method can be classified better compared with the state-of-the-art
techniques. Table 1 presents a performance matrix for a drowsiness
detection system, evaluating the effectiveness of a proposed method.
Matthew’s correlation coefficient value of the proposed technique
is 0.986, which would indicate a very strong correlation between
observed and predicted classifications in our model [7]. The metrics
included in the matrix are key indicators of the system’s performance,
measuredinpercentages.Thetableisstructuredwithrowsrepresenting
different evaluation criteria and columns representing performance
metrics. Overall, the high values across all metrics in the performance
matrix suggest that the proposed drowsiness detection method is highly
accurate, sensitive, and specific. These results indicate the potential
effectiveness of the method in real-world applications where reliable
identification of drowsiness is crucial for ensuring safety and prevent

-----

TABLE 2. Performance Comparison of the Proposed Method With
Literature

#### A. Comparison of the Proposed Method Performance With Recent Techniques

Table 2 presents a comparative analysis of various studies in the
literature focusing on drowsiness detection, with a special emphasis
on the proposed method. The proposed DL-based attention mechanism
for automatic drowsiness detection using EEG signals exhibits a commendable performance, achieving an accuracy of 98.38%. In comparison with recent techniques in the literature, the proposed method excels
in terms of year, number of classes, database, and performance metrics,
showcasing a robust ability to accurately identify drowsiness states.
A thorough literature review and comparison with recent techniques
reveal the innovation and novelty embedded in the proposed attention
mechanism present in the current landscape of drowsiness detection
methods. Overall, the proposed attention mechanism demonstrates a
compelling advancement in EEG-based drowsiness detection, offering
a promising avenue for further research and implementation. The
inclusion of the “proposed method” in the table showcases a novel
approach introduced in 2023, which outperforms the other studies with
an impressive accuracy of 98.38%. This suggests that the proposed
method holds promise for drowsiness detection and may represent
a significant advancement in the field. Researchers and practitioners
may find this table useful for comparing different approaches and
identifying the latest developments in drowsiness detection research.

#### B. Limitations

The proposed EEG-based drowsiness detection technique, while
highly accurate, has limitations. Its reliance on single-channel EEG
data may miss complex patterns identifiable in multichannel EEG. The
model’s generalizability across diverse populations and environments
remains a concern. Sensitivity to artifacts, despite preprocessing, can
affect accuracy.


#### V. CONCLUSION

In conclusion, the proposed DL architecture for drowsiness detection from single-channel EEG signals represents a novel and efficient
approach to address the critical task of monitoring cognitive states
in real-time. The hybrid feature extraction, combining convolutional
layers, LSTM, and D-residual blocks, offers a comprehensive representation of both spatial and temporal aspects in the EEG data. The subsequent classification using Bi-GRU further refines the model’s ability
to capture intricate temporal dependencies, enhancing the overall accuracy and reliability of drowsiness detection. This research contributes
to the field by presenting an architecture that not only demonstrates
high performance, as evidenced by the impressive 98.38% accuracy,
but also emphasizes practical considerations such as the utilization
of a single-channel EEG signal. The attention to real-time application
aligns the model with scenarios where timely and dynamic drowsiness
detection is crucial, such as in driving or operating heavy machinery.
For future research, there are several promising avenues to explore.
First, the model’s generalization across diverse populations and its
adaptability to various EEG acquisition setups could be investigated.

#### REFERENCES

[1] B. V. Phanikrishna, A. J. Prakash, and C. Suchismitha, “Deep review of machine

learning techniques on detection of drowsiness using EEG signal,” IETE J. Res.,
vol. 69, no. 6, pp. 3104–3119, 2023.

[2] J. P. Allam, S. Samantray, C. Behara, K. K. Kurkute, and V. K. Sinha, “Customized

deep learning algorithm for drowsiness detection using single-channel EEG signal,”
in _ArtificialIntelligence-BasedBrain-ComputerInterface.Amsterdam,Netherlands:_
Elsevier, 2022, pp. 189–201.

[3] T. Zhu, W. Luo, and F. Yu, “Convolution-and attention-based neural network for

automated sleep stage classification,” Int. J. Environ. Res. Public Health, vol. 17,
no. 11, 2020, Art. no. 4152.

[4] M. Fu et al., “Deep learning in automatic sleep staging with a single channel

electroencephalography,” Front. Physiol., vol. 12, 2021, Art. no. 628502.

[5] V. P. Balam, V. U. Sameer, and S. Chinara, “Automated classification system for

drowsiness detection using convolutional neural network and electroencephalogram,” IET Intell. Transport Syst., vol. 15, no. 4, pp. 514–524, 2021.

[6] B. Kemp, A. Zwinderman, B. Tuk, H. Kamphuisen, and J. Oberyé, “Sleep-EDF

database expanded,” Physionet org, 2018.

[7] T. Anbalagan, M. K. Nath, D. Vijayalakshmi, and A. Anbalagan, “Analysis of various

techniques for ECG signal in healthcare, past, present, and future,” Biomed. Eng.
_Adv., vol. 6, 2023, Art. no. 100089._

[8] E. Eldele et al., “An attention-based deep learning approach for sleep stage classi
fication with single-channel EEG,” IEEE Trans. Neural Syst. Rehabil. Eng., vol. 1,
pp. 809–818, Apr. 2021.

[9] C. Liu, Y. Yin, Y. Sun, and O. K. Ersoy, “Multi-scale ResNet and BiGRU automatic

sleep staging based on attention mechanism,” PLoS One, vol. 17, no. 6, 2022,
Art. no. e0269500.

[10] L.-X. Feng et al., “Automatic sleep staging algorithm based on time attention

mechanism,” Front. Hum. Neurosci., vol. 15, 2021, Art. no. 692054.


-----

