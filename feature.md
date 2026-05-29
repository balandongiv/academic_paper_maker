# Features derived from a 30-second epoch of 30Hz eye-tracking data

## I. Blink Event Features (Aggregated per epoch)

### A. Blink Frequency and Timing

* blink_count: Total number of blinks
* blink_rate: Blinks per minute (blink_count * 2)
* inter_blink_interval (IBI):
    * mean, std, median, min, max, cv, rmssd,
    * poincare_sd1, poincare_sd2
    * permutation_entropy
    * hurst_exponent
* blink_microburst_rate: Blink pairs < 0.5s apart

### B. Blink Morphology (Waveform Shape)

* blink_duration: Mean, std, median, min, max, cv, iqr
    * blink_duration_ratio: Ratio of longest to shortest duration
* time_to_peak/time_from_peak_to_end: Mean, std, cv
* blink_rise_time_25_75 / blink_fall_time: Mean, std, cv
* blink_fwhm: Mean, std, cv
* blink_amplitude: Mean, std, median, min, max, cv, skewness, kurtosis
* blink_area: Mean, std, cv
* blink_half_area_time: Mean, std, cv
* blink_asymmetry: Ratio of rise to fall time/slope (mean, std)
* blink_skewness/blink_kurtosis: Mean, std
* blink_inflection_count: Mean, std


### C. Blink Kinematics (Movement Dynamics)

* blink_velocity:  max, mean, std, cv
* blink_acceleration: max, mean, std, cv
* blink_jerk: max, mean, std, cv
* amplitude_velocity_ratio (AVR): Mean, std, cv


### D. Blink Energy and Complexity

* blink_signal_energy:  Mean, std, cv
* teager_kaiser_energy: Mean, std, cv
* blink_line_length: Mean, std, cv



## II. Non-Blink Eye Signal Features (Inter-blink periods)

### A. Baseline and Drift

* baseline_mean: Mean eyelid position between blinks
* baseline_drift: Slope of linear fit to baseline
* baseline_std/baseline_mad: Variability of baseline
* low_freq_baseline_power (<0.1 Hz): Power in low frequency band


### B. Eye Opening and Closure

* perclos: Percentage of eyelid closure
* eye_opening_rms: Root mean square of eyelid opening amplitude
* micropause_count: Count of partial closures (100ms - 300ms)


### C. Inter-blink Signal Complexity

* inter_blink_variance/inter_blink_mad
* non_blink_spectral_entropy
* approximate_entropy / sample_entropy
* zero_crossing_rate (of derivative): Tremor/noise indicator


## III. Frequency Domain Features (Per Epoch)

### A. Blink-Related Rhythms

* blink_rate_peak_frequency (0.1-0.5 Hz): Dominant blink periodicity
* blink_rate_peak_power


### B. General Eye Movement Rhythms

* broadband_power (0.5-2 Hz): Voluntary/stress-related movements
* spectral_centroid (0.5-2 Hz)
* total_energy (2-13 Hz):  Rapid micro-blinks vs. noise
* spectral_entropy (2-13 Hz)
* 1/f_slope: Slope of power spectrum in log-log space
* band_power_ratios: Ratios of power in different frequency bands
* wavelet_packet_energy (D1-D4 levels): Wavelet-based energy features


## IV.  Advanced and Experimental Features

* blink_magnitude_spectrum (FFT of individual blinks)
* blink_wavelet_coefficients
* clustered_blink_count: Blinks occurring very close together
* microblink_ratio
* blink_burstiness_index: Variance(IBI) / Mean(IBI)
* pupil_jump_indicator: Sudden large baseline shifts (potentially saccades)




## V. Aggregation and Post-Processing

* Session-level histograms (e.g., IBI distribution)
* Trend-over-time analysis (e.g., blink rate vs. time)
* Event-triggered averages (aligned to external events)