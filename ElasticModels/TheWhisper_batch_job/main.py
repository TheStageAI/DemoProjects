import argparse
import os
import time

import torch
from datasets import load_dataset
from elastic_models.transformers import AutoModelForSpeechSeq2Seq
from transformers import AutoProcessor


def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch transcribe audio with TheWhisper"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="S",
        choices=["S", "M", "L", "XL", "original"],
        help="Model size: S (fastest), M, L, XL, or original",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language code (e.g., 'en', 'de', 'fr'). Auto-detected if not set.",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=64,
        help="Number of audio samples to process per batch",
    )
    parser.add_argument(
        "--num_samples",
        type=int,
        default=10,
        help="Number of samples to transcribe from the dataset",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    hf_token = os.environ.get("HF_TOKEN", "")
    device = torch.device("cuda")
    model_name = "TheStageAI/thewhisper-large-v3-turbo"

    # Load dataset
    print("Loading LibriSpeech dataset...")
    dataset = load_dataset(
        "hf-internal-testing/librispeech_asr_dummy",
        "clean",
        split="validation",
    )
    samples = dataset.select(range(min(args.num_samples, len(dataset))))
    print(f"Selected {len(samples)} samples from dataset")

    # Load model
    print(f"Loading TheWhisper model (mode={args.mode})...")
    processor = AutoProcessor.from_pretrained(model_name, token=hf_token)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_name,
        token=hf_token,
        torch_dtype=torch.float16,
        mode=args.mode,
    ).to(device)

    all_transcriptions = []
    total_audio_duration = 0.0
    start_time = time.time()

    generate_kwargs = {}
    if args.language:
        generate_kwargs["language"] = args.language

    for batch_start in range(0, len(samples), args.batch_size):
        batch_end = min(batch_start + args.batch_size, len(samples))

        features_list = []
        for idx in range(batch_start, batch_end):
            audio = samples[idx]["audio"]
            total_audio_duration += len(audio["array"]) / audio["sampling_rate"]

            feat = processor(
                audio["array"],
                sampling_rate=audio["sampling_rate"],
                return_tensors="pt",
            ).input_features
            features_list.append(feat)

        input_features = torch.cat(features_list, dim=0).to(
            device, dtype=torch.float16
        )

        with torch.inference_mode():
            predicted_ids = model.generate(
                input_features, **generate_kwargs
            )

        transcriptions = processor.batch_decode(
            predicted_ids, skip_special_tokens=True
        )

        for i, text in enumerate(transcriptions):
            line = f"[{batch_start + i}] {text.strip()}"
            print(line)
            all_transcriptions.append(line)

    elapsed = time.time() - start_time
    rtfx = round(total_audio_duration / elapsed, 1) if elapsed > 0 else 0
    print(f"\nTotal audio: {total_audio_duration:.1f}s | Time: {elapsed:.1f}s | RTFx: {rtfx}x")

    output_path = "/workspace/transcriptions.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_transcriptions) + "\n")
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
