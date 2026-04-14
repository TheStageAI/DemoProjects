# TheStageAI Demo Projects

A collection of demo projects to help you get started with the [TheStage AI](https://app.thestage.ai) platform. Each project is a self-contained example you can clone and run on your containers right away.

## Quick Start

### 1. Install TheStage CLI & Set Token

```bash
pip install thestage
thestage config set --access-token <YOUR_THESTAGE_TOKEN>
```

Get your token at [app.thestage.ai](https://app.thestage.ai) -> **Profile -> Access Tokens**.

### 2. Set HuggingFace Token

Some models require a HuggingFace access token. Set `HF_TOKEN` as an environment variable in your container configuration.

Get your token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

### 3. Clone & Run

```bash
# Run a demo
thestage project run "python main.py"

# Monitor logs
thestage project task logs <task_id>
```

## Projects

### ElasticModels

Accelerated AI models produced by TheStage AI ANNA (Automated Neural Networks Accelerator). Each model comes in multiple optimized sizes (S/M/L/XL) trading off speed vs. quality.

| Project | Description | Status |
|---------|-------------|--------|
| [Flux_schnell_inference](ElasticModels/Flux_schnell_inference/) | Text-to-image generation with FLUX.1-schnell | Ready |
| [TheWhisper_batch_job](ElasticModels/TheWhisper_batch_job/) | Batch audio transcription with TheWhisper | Ready |
| [Qlip_Compile](ElasticModels/Qlip_Compile/) | Model compilation with QLIP | Coming soon |
| [Qlip_Compress](ElasticModels/Qlip_Compress/) | Model compression with QLIP | Coming soon |
| [Qlip_Serve](ElasticModels/Qlip_Serve/) | Model serving with QLIP | Coming soon |
| [Qlip_Skills](ElasticModels/Qlip_Skills/) | Custom skills with QLIP | Coming soon |

## System Requirements

All ElasticModels demos require:

- **GPU**: L40s, RTX 4090/5090, H100, or B200
- **Python**: 3.10 - 3.12
- **CUDA**: 12.8+

## Links

- [TheStage AI Platform](https://app.thestage.ai)
- [ElasticModels on HuggingFace](https://huggingface.co/TheStageAI)
- [ElasticModels GitHub](https://github.com/TheStageAI/ElasticModels)
