# Whole-Image PhotoGuard

A small command-line implementation of the **encoder attack** from
[MadryLab/PhotoGuard](https://github.com/MadryLab/photoguard).

This version removes the interactive region-selection step. The
adversarial perturbation is applied to the **entire image**.

## What it does

```text
original image
      |
      v
Stable Diffusion VAE
      |
      v
PGD optimization
      |
      v
imperceptibly perturbed image
      |
      v
protected.png
```

The optimization pushes the image's Stable Diffusion VAE representation
toward the representation of a gray target image.

The released PhotoGuard implementation uses a PGD encoder attack.
The paper describes an encoder attack that minimizes the distance between
the input's latent representation and a target latent representation.

## Requirements

A CUDA GPU is strongly recommended.

Python 3.10+ is recommended.

Install:

```bash
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

For NVIDIA CUDA, install the PyTorch build appropriate for your CUDA
version if the normal `pip install torch` does not provide CUDA support.

Check:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

It should print:

```text
True
```

## Hugging Face

The code downloads the Stable Diffusion v1.5 VAE from Hugging Face.

If your account requires access to the model:

```bash
huggingface-cli login
```

## Protect an image

```bash
python protect.py \
    --input photo.jpg \
    --output protected.png
```

The defaults are:

```text
epsilon   = 16/255
step size = 2/255
iterations = 200
mask       = entire image
```

These are the values described for the encoder attack in the PhotoGuard
paper.

## Faster test

For a quick test:

```bash
python protect.py \
    -i photo.jpg \
    -o protected.png \
    --iters 20
```

This is useful for verifying that the installation works, but it is not
equivalent to the full 200-step run.

## More aggressive experiment

The original PhotoGuard repository's image-to-image notebook uses a
stronger/longer encoder attack configuration. You can experiment with:

```bash
python protect.py \
    -i photo.jpg \
    -o protected.png \
    --eps 0.06 \
    --step-size 0.02 \
    --iters 1000
```

## Important: use PNG

Do not JPEG-compress the protected image after processing.

The protection is an adversarial pixel perturbation. JPEG compression,
resizing, filtering, screenshots, etc. can alter or remove that
perturbation.

Use:

```text
photo.jpg -> protected.png
```

rather than:

```text
photo.jpg -> protected.jpg
```

## Whole-image behavior

The official interactive demo asks the user to paint regions that should
remain unchanged during the attack. Internally, those regions are masked
out of the PGD update.

This implementation intentionally has no spatial mask:

```python
# every pixel can be changed
adv = adv - step_size * grad.sign()
```

So the entire image participates in the optimization.

## Important limitation

This is the **encoder attack**, not the more expensive PhotoGuard
diffusion attack.

The encoder attack is designed to disrupt the image representation used
by Stable Diffusion. It does not provide a universal guarantee against
all image editors or future diffusion models.

For the full PhotoGuard diffusion attack, the original repository
backpropagates through the diffusion process and is substantially more
expensive.

## License

This implementation is provided for research/educational use.
The original PhotoGuard repository is MIT licensed.
