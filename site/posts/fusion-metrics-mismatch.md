---
title: Why your image-fusion metrics don't match the paper
date: 2026-11-27
summary: The same fused image can score very differently depending on the evaluation script. Here is where the numbers drift, how big each effect really is, and how to get values that match the reference MATLAB code.
---

If you work on infrared–visible or medical image fusion, you have probably re-run a published method, computed EN, MI, VIF, Q<sup>AB/F</sup> and SSIM, and got numbers that do not match the paper. Usually the method is fine. The evaluation script is not.

Most papers evaluate with some copy of a MATLAB toolbox, or with a Python rewrite of one. The metrics have names everyone agrees on, but their implementations differ in details that nobody reports. While porting 35 of these metrics to Python for [fusion-metrics](https://github.com/VuVietAnh2309/fusion-metrics), I checked every value against the original `.m` files. These are the differences that mattered, from largest to smallest.

## 1. Scale mismatch: the silent killer

Deep-learning pipelines usually keep images in `[0, 1]`, while the reference metrics expect `[0, 255]`. If the fused image is in one range and the sources in the other, gradient-based metrics collapse. On the same three images:

| Inputs | Q<sup>AB/F</sup> |
|---|---|
| A, B and F all in [0, 255] | 0.4018 |
| F in [0, 1], A and B in [0, 255] | 0.0004 |

Nothing crashes and nothing warns you. You just get a number close to zero and assume the method is bad. This shows up in GitHub issues on fusion repositories, for example a report that "the average Qabf is 0.0033" on a standard test set. Normalise all three images to the same range before scoring.

## 2. Re-implementations that are not the same metric

Many Python versions are written from the paper's formula rather than ported from the code that produced the published tables. They differ in ways that are invisible in the formula:

- **Borders.** MATLAB's `conv2(..., 'same')` centres even-sized kernels differently from NumPy and SciPy; `imfilter(..., 'replicate')` pads differently from `mode="reflect"`.
- **Rounding.** MATLAB's `round` and `uint8()` round halves away from zero; `np.round` rounds halves to even.
- **Integer arithmetic.** Some reference files multiply `uint8` arrays, which saturates at 255 in MATLAB but wraps around or upcasts in NumPy.
- **Edge maps.** MATLAB's `edge(..., 'sobel')` thins edges; a plain Sobel magnitude threshold does not.

How much each one moves a metric depends on the image, but together they are enough to make tables from different papers incomparable.

## 3. Numerically fragile reference code

A few reference implementations are themselves sensitive to round-off. Two examples I found while verifying:

- **Q<sub>C</sub> and Q<sub>Y</sub>** use SSIM with constants of 2·10<sup>-16</sup>. In a perfectly flat window (a saturated region, for example) the variances are zero in exact arithmetic but around 10<sup>-11</sup> after filtering, so the result depends on summation order. In one window Octave gives 0.67, NumPy gives 1.5·10<sup>5</sup>, and the exact value is 0.9986.
- **Q<sub>CB</sub>** divides two filtered images whose denominator crosses zero, amplifying FFT round-off. Octave and NumPy agree on it only to a median of about 2·10<sup>-5</sup> on real images.

You cannot fix these by being careful; you can only document them. fusion-metrics evaluates flat windows exactly and states the remaining tolerance.

## 4. Gray conversion: smaller than people think

It is often said that MATLAB's `rgb2gray` and OpenCV's conversion give different results on pseudo-colour PET and SPECT images. They do, but the effect is small. On a pseudo-colour test image the two conversions differ by one grey level on about 0.1% of the pixels; MI changed by 0.0009 and Q<sup>AB/F</sup>, VIF and entropy not at all to four decimals. Worth matching for exact reproduction, not the reason your numbers are off.

## Getting values that match

fusion-metrics ports each metric line by line from its reference `.m` file and checks every value against the original in GNU Octave, to a relative error of 10<sup>-12</sup> on synthetic edge cases and on real PET/SPECT–MRI pairs. The `ivif` preset produces the table most infrared–visible papers report:

```bash
pip install fusion-metrics
fusion-metrics --dirs ir/ vi/ fused/ --preset ivif --csv results.csv
```

or from Python:

```python
import fusion_metrics as fm

A, B, F = (fm.read_gray(p) for p in ("ir.png", "vi.png", "fused.png"))
print(fm.evaluate(A, B, F, "ivif"))   # EN, SD, SF, MI, SCD, VIF, Qabf, SSIM
```

If you report fusion results, say which implementation you used and in which value range the images were. That single sentence would make most of the tables in this field comparable.
