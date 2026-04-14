# Elastic FLUX.1-schnell Inference

Generate images from text prompts using TheStage AI's accelerated [FLUX.1-schnell](https://huggingface.co/TheStageAI/Elastic-FLUX.1-schnell) model.

## Model Overview

ElasticModels are models produced by TheStage AI ANNA (Automated Neural Networks Accelerator). Each model comes in multiple optimized sizes:

| Size | Description |
|------|-------------|
| **XL** | Mathematically equivalent to original, optimized with DNN compiler |
| **L** | Near lossless, <1% degradation |
| **M** | Faster, <1.5% degradation |
| **S** | Fastest, <2% degradation |

### Latency (1024x1024 image, seconds)

| GPU | S | M | L | XL | Original |
|-----|---|---|---|----|----|
| H100 | 0.51 | 0.51 | 0.51 | 0.71 | 1.04 |
| L40s | 1.59 | 1.60 | 1.60 | 2.19 | 2.50 |
| B200 | 0.38 | 0.38 | 0.38 | 0.39 | 0.75 |

## System Requirements

- **GPU**: L40s, RTX 5090, H100, or B200
- **Python**: 3.10 - 3.12
- **CUDA**: 12.8+

## Setup

### 1. Get Access Tokens

- **TheStage AI token**: Sign up at [app.thestage.ai](https://app.thestage.ai), go to **Profile -> Access Tokens**
- **HuggingFace token**: Get from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### 2. Install TheStage CLI & Configure Token

```bash
pip install thestage
thestage config set --access-token <YOUR_THESTAGE_TOKEN>
```

### 3. Set HuggingFace Token in Container

Set `HF_TOKEN` as an environment variable in your container configuration.

## Running on TheStage Platform

### Clone and run

```bash
thestage project run "export HF_TOKEN=<YOUR_HF_TOKEN> && python main.py"
```

### With custom parameters

```bash
# Fast generation with smallest model
thestage project run "export HF_TOKEN=<YOUR_HF_TOKEN> && python main.py --prompt 'A sunset over mountains' --mode S"

# High quality with XL model
thestage project run "export HF_TOKEN=<YOUR_HF_TOKEN> && python main.py --prompt 'Cat in space' --mode XL"

# Reproducible output with seed
thestage project run "export HF_TOKEN=<YOUR_HF_TOKEN> && python main.py --prompt 'Forest landscape' --mode L --seed 42 --output forest.png"
```

### Monitor & download results

```bash
# Watch task logs
thestage project task logs <task_id>

# Download generated image
thestage container download <container_name>:/workspace/Forest_landscape.png ./
```

## CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--prompt` | "Kitten eating a banana" | Text prompt for generation |
| `--mode` | S | Model size: `S`, `M`, `L`, `XL`, or `original` |
| `--width` | 1024 | Output image width |
| `--height` | 1024 | Output image height |
| `--steps` | 4 | Number of inference steps |
| `--seed` | None | Random seed for reproducibility |
| `--output` | `<prompt>.png` | Output file path |

## Python API

```python
import torch
from elastic_models.diffusers import FluxPipeline

pipeline = FluxPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-schnell",
    torch_dtype=torch.bfloat16,
    token="<YOUR_HF_TOKEN>",
    mode="S",  # S, M, L, XL, or original
)
pipeline.to(torch.device("cuda"))

output = pipeline(prompt=["A beautiful landscape"])
output.images[0].save("landscape.png")
```

## Links

- [Model Card on HuggingFace](https://huggingface.co/TheStageAI/Elastic-FLUX.1-schnell)
- [TheStage AI Platform](https://app.thestage.ai)
- [ElasticModels GitHub](https://github.com/TheStageAI/ElasticModels)
