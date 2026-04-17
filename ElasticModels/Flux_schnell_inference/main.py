import argparse
import os

import torch
from elastic_models.diffusers import FluxPipeline


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate images with Elastic FLUX.1-schnell"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="Kitten eating a banana",
        help="Text prompt for image generation",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="S",
        choices=["S", "M", "L", "XL", "original"],
        help="Model size: S (fastest), M, L, XL, or original",
    )
    parser.add_argument(
        "--width", type=int, default=1024, help="Output image width"
    )
    parser.add_argument(
        "--height", type=int, default=1024, help="Output image height"
    )
    parser.add_argument(
        "--steps", type=int, default=4, help="Number of inference steps"
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: <prompt>.png)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    hf_token = os.environ.get("HF_TOKEN", "")
    device = torch.device("cuda")

    print(f"Loading FLUX.1-schnell pipeline (mode={args.mode})...")
    pipeline = FluxPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-schnell",
        torch_dtype=torch.bfloat16,
        token=hf_token,
        mode=args.mode,
    )
    pipeline.to(device)

    generate_kwargs = {
        "height": args.height,
        "width": args.width,
        "num_inference_steps": args.steps,
    }

    if args.seed is not None:
        generate_kwargs["generator"] = torch.Generator(device=device).manual_seed(
            args.seed
        )

    print(f"Generating image for prompt: '{args.prompt}'...")
    output = pipeline(prompt=[args.prompt], **generate_kwargs)

    filename = args.output or (args.prompt.replace(" ", "_") + ".png")
    output_path = os.path.join("/workspace", filename)
    output.images[0].save(output_path)
    print(f"Image saved to: {output_path}")


if __name__ == "__main__":
    main()
