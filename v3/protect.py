#!/usr/bin/env python3
"""
Whole-image PhotoGuard-style immunization.

This implements the encoder attack from MadryLab/PhotoGuard:
    minimize || VAE(x_adv) - VAE(target) ||_2
with L-infinity PGD.

Unlike the original interactive demo, there is no user-drawn mask:
the perturbation is allowed over the ENTIRE image.

Usage:
    python protect.py --input photo.jpg --output protected.png

The default hyperparameters follow the paper's encoder-attack setup:
    epsilon = 16/255
    step_size = 2/255
    iterations = 200

This is a research/educational implementation. It protects against
the specific diffusion-model behavior it was optimized against; it
does not guarantee protection against arbitrary future image editors.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from diffusers import AutoencoderKL


MODEL_ID = "runwayml/stable-diffusion-v1-5"


def load_image(path: str) -> Image.Image:
    image = Image.open(path).convert("RGB")

    # Stable Diffusion's VAE operates naturally on dimensions divisible by 32.
    # Keep the full image; only trim a few edge pixels when necessary.
    w, h = image.size
    new_w = w - (w % 32)
    new_h = h - (h % 32)

    if new_w < 32 or new_h < 32:
        raise ValueError(
            f"Image is too small: got {w}x{h}; minimum is 32x32."
        )

    if (new_w, new_h) != (w, h):
        print(
            f"[!] Adjusting dimensions {w}x{h} -> {new_w}x{new_h} "
            f"(Stable Diffusion VAE requires multiples of 32)."
        )
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    return image


def image_to_tensor(image: Image.Image, device: torch.device, dtype: torch.dtype):
    arr = np.asarray(image).astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    tensor = tensor * 2.0 - 1.0
    return tensor.to(device=device, dtype=dtype)


def tensor_to_image(tensor: torch.Tensor) -> Image.Image:
    tensor = tensor.detach().float().cpu()
    tensor = ((tensor / 2.0) + 0.5).clamp(0, 1)
    arr = (
        tensor[0]
        .permute(1, 2, 0)
        .numpy()
        * 255.0
    ).round().astype(np.uint8)

    return Image.fromarray(arr, mode="RGB")


def make_gray_target(
    size: tuple[int, int],
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    """
    PhotoGuard's encoder attack targets a gray image in latent space.
    """
    width, height = size
    target = Image.new("RGB", (width, height), (128, 128, 128))
    return image_to_tensor(target, device, dtype)


@torch.no_grad()
def encode_target(vae: AutoencoderKL, target: torch.Tensor) -> torch.Tensor:
    return vae.encode(target).latent_dist.mean


def pgd_encoder_attack(
    image: torch.Tensor,
    target_latent: torch.Tensor,
    vae: AutoencoderKL,
    eps: float,
    step_size: float,
    iterations: int,
) -> torch.Tensor:
    """
    Whole-image L_inf PGD.

    There is deliberately NO spatial mask here:
        every pixel is eligible for the adversarial perturbation.
    """
    # Random initialization inside the epsilon ball, as in the
    # original PhotoGuard implementation.
    adv = image + torch.empty_like(image).uniform_(-eps, eps)
    adv = adv.clamp(-1.0, 1.0).detach()

    for iteration in range(iterations):
        adv.requires_grad_(True)

        encoded = vae.encode(adv).latent_dist.mean
        loss = torch.linalg.vector_norm(encoded - target_latent)

        (grad,) = torch.autograd.grad(loss, adv)

        # Linear step-size decay, matching the released implementation.
        current_step = step_size - (
            (step_size - step_size / 100.0)
            / max(iterations, 1)
            * iteration
        )

        with torch.no_grad():
            adv = adv - current_step * grad.sign()

            # Project back into the L_inf epsilon ball around the
            # ORIGINAL image.
            adv = torch.maximum(adv, image - eps)
            adv = torch.minimum(adv, image + eps)

            # Keep pixels in valid Stable Diffusion input range.
            adv = adv.clamp(-1.0, 1.0)

        if iteration == 0 or (iteration + 1) % 10 == 0 or iteration == iterations - 1:
            print(
                f"\r[{iteration + 1:4d}/{iterations}] "
                f"latent loss={loss.item():.5f}",
                end="",
                flush=True,
            )

    print()
    return adv.detach()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply whole-image PhotoGuard-style adversarial protection."
    )

    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Input image.",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output protected image.",
    )
    parser.add_argument(
        "--model",
        default=MODEL_ID,
        help=f"Hugging Face Stable Diffusion model (default: {MODEL_ID}).",
    )
    parser.add_argument(
        "--eps",
        type=float,
        default=16.0 / 255.0,
        help="L_inf perturbation budget in normalized [0,1]-style units (default: 16/255).",
    )
    parser.add_argument(
        "--step-size",
        type=float,
        default=2.0 / 255.0,
        help="PGD step size (default: 2/255).",
    )
    parser.add_argument(
        "--iters",
        type=int,
        default=200,
        help="Number of PGD iterations (default: 200).",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU. Very slow; CUDA is strongly recommended.",
    )

    args = parser.parse_args()

    if args.iters <= 0:
        raise ValueError("--iters must be > 0")
    if args.eps <= 0:
        raise ValueError("--eps must be > 0")
    if args.step_size <= 0:
        raise ValueError("--step-size must be > 0")

    if args.cpu:
        device = torch.device("cpu")
    else:
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is not available. Use a CUDA-enabled PyTorch installation "
                "or pass --cpu (which will be very slow)."
            )
        device = torch.device("cuda")

    dtype = torch.float16 if device.type == "cuda" else torch.float32

    print(f"Device: {device}")
    print(f"Model:  {args.model}")
    print(f"Epsilon: {args.eps:.8f} ({args.eps * 255:.2f}/255)")
    print(f"Step:    {args.step_size:.8f} ({args.step_size * 255:.2f}/255)")
    print(f"Steps:   {args.iters}")
    print("Mask:    FULL IMAGE")

    image = load_image(args.input)

    print(f"Input:   {image.size[0]}x{image.size[1]}")

    print("Loading Stable Diffusion VAE...")
    vae = AutoencoderKL.from_pretrained(
        args.model,
        subfolder="vae",
        torch_dtype=dtype,
    )
    vae = vae.to(device)
    vae.eval()

    # The VAE is frozen; gradients are only required with respect to the image.
    for parameter in vae.parameters():
        parameter.requires_grad_(False)

    original = image_to_tensor(image, device, dtype)

    target = make_gray_target(
        image.size,
        device,
        dtype,
    )

    print("Encoding target...")
    target_latent = encode_target(vae, target)

    print("Running whole-image PGD...")
    protected = pgd_encoder_attack(
        image=original,
        target_latent=target_latent,
        vae=vae,
        eps=args.eps,
        step_size=args.step_size,
        iterations=args.iters,
    )

    protected_image = tensor_to_image(protected)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    # PNG avoids introducing JPEG compression that could destroy the
    # adversarial perturbation.
    if output.suffix.lower() in {".jpg", ".jpeg"}:
        print(
            "[!] JPEG output can destroy the small adversarial perturbation. "
            "Use PNG if possible."
        )

    protected_image.save(output)

    # Report actual maximum RGB change.
    original_u8 = np.asarray(image).astype(np.int16)
    protected_u8 = np.asarray(protected_image).astype(np.int16)
    max_delta = np.abs(protected_u8 - original_u8).max()
    mean_delta = np.abs(protected_u8 - original_u8).mean()

    print(f"Saved:   {output}")
    print(f"Max RGB change:  {max_delta}")
    print(f"Mean RGB change: {mean_delta:.4f}")


if __name__ == "__main__":
    main()
