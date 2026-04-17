# TheWhisper Batch Transcription Job

Batch transcribe audio samples using TheStage AI's accelerated [TheWhisper-large-v3-turbo](https://huggingface.co/TheStageAI/thewhisper-large-v3-turbo) model.

This demo loads audio from the [LibriSpeech](https://huggingface.co/datasets/hf-internal-testing/librispeech_asr_dummy) dataset, batches it, and runs transcription — ready to run out of the box.

## Model Overview

TheWhisper-Large-V3-Turbo is a fine-tuned variant of OpenAI's Whisper Large V3, optimized by TheStage AI for real-time, low-latency ASR. Supports 28 languages.

| Size | Description |
|------|-------------|
| **XL** | Mathematically equivalent to original, optimized with DNN compiler |
| **L** | Near lossless, <1% degradation |
| **M** | Faster, <1.5% degradation |
| **S** | Fastest, <2% degradation |

### Latency (RTFx, higher is better)

| GPU | S | M | L | XL | Original |
|-----|---|---|---|----|----|
| H100 (bs=64) | 1950 | 1828 | 1820 | 1818 | 967 |
| L40s (bs=32) | 877 | 850 | 829 | 829 | 539 |
| RTX 5090 (bs=32) | 983 | 983 | 983 | 976 | 484 |

## System Requirements

- **GPU**: L40s, RTX 4090, RTX 5090, or H100
- **Python**: 3.10 - 3.12
- **CUDA**: 12.8+

## Setup (local)

### 1. Get Access Tokens

- **TheStage AI token**: Sign up at [app.thestage.ai](https://app.thestage.ai), go to **Profile -> Access Tokens**
- **HuggingFace token**: Get from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### 2. Install TheStage CLI & Configure Token

```bash
pip install thestage
thestage config set --access-token <YOUR_THESTAGE_TOKEN>
```

### 3. Set HuggingFace Token

Set `HF_TOKEN` as an environment variable in your container configuration.

## Running on TheStage Platform

Dependencies from `requirements.txt` are installed automatically when running via `thestage project run`.

```bash
# Run batch transcription (default: 10 samples, mode S, batch_size 64)
thestage project run "python main.py"

# More samples, high quality
thestage project run "python main.py --mode XL --batch_size 32 --num_samples 20"

# Specify language
thestage project run "python main.py --language en"

# Download results
thestage container download run:/workspace/transcriptions.txt ./
```

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--mode` | S | Model size: `S`, `M`, `L`, `XL`, or `original` |
| `--language` | auto-detect | Language code (`en`, `de`, `fr`, etc.) |
| `--batch_size` | 64 | Samples processed per batch |
| `--num_samples` | 10 | Number of samples to transcribe from dataset |

## Python API

```python
import torch
from datasets import load_dataset
from elastic_models.transformers import AutoModelForSpeechSeq2Seq
from transformers import AutoProcessor

model_name = "TheStageAI/thewhisper-large-v3-turbo"

processor = AutoProcessor.from_pretrained(model_name, token="<YOUR_HF_TOKEN>")
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_name,
    token="<YOUR_HF_TOKEN>",
    torch_dtype=torch.float16,
    mode="S",
).to(torch.device("cuda"))

dataset = load_dataset(
    "hf-internal-testing/librispeech_asr_dummy",
    "clean", split="validation"
)
audio_sample = dataset[0]["audio"]

input_features = processor(
    audio_sample["array"],
    sampling_rate=audio_sample["sampling_rate"],
    return_tensors="pt",
).input_features.to("cuda", dtype=torch.float16)

with torch.inference_mode():
    predicted_ids = model.generate(input_features)

text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
print(f"Transcription: {text}")
```

## Links

- [Model Card on HuggingFace](https://huggingface.co/TheStageAI/thewhisper-large-v3-turbo)
- [TheWhisper GitHub](https://github.com/TheStageAI/TheWhisper)
- [TheStage AI Platform](https://app.thestage.ai)
