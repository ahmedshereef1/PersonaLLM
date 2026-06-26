# LLM-Twin Fine-Tuning Guide

## Overview

This project fine-tunes a Llama 3.1 model using two stages:

1. **SFT (Supervised Fine-Tuning)**
2. **DPO (Direct Preference Optimization)**

The training is orchestrated by ZenML and executed on AWS SageMaker.

---

## Training Pipeline Flow

```text
Generate Datasets
        ↓
Upload Datasets to Hugging Face
        ↓
SFT Training
        ↓
TwinLlama-3.1-8B
        ↓
DPO Training
        ↓
TwinLlama-3.1-8B-DPO
```

---

## Dataset Requirements

The following Hugging Face datasets must exist:

### SFT Dataset

```text
AhmedSherif22/llmtwin
```

### DPO Dataset

```text
AhmedSherif22/llmtwin-dpo
```

Verify both datasets are visible on Hugging Face before starting training.

---

## Generate Datasets

Run:

```bash
uv run zenml pipeline run pipelines.generate_datasets.generate_datasets
```

Expected artifacts:

```text
raw_documents
cleaned_documents
instruct_datasets
preference_datasets
```

---

## Training Configuration

Example:

```yaml
settings:
  docker:
    parent_image: 992382797823.dkr.ecr.eu-central-1.amazonaws.com/zenml-rlwlcs:latest
    skip_build: true

  orchestrator.sagemaker:
    synchronous: false

parameters:
  finetuning_type: sft
  num_train_epochs: 3
  per_device_train_batch_size: 2
  learning_rate: 3e-4
  dataset_huggingface_workspace: AhmedSherif22
  is_dummy: true
```

---

## SFT Training

Run:

```bash
uv run zenml pipeline run pipelines.training.training \
-c deployment/manifests/training.yaml
```

The training pipeline:

```text
training pipeline
    ↓
train step
    ↓
run_finetuning_on_sagemaker()
    ↓
SageMaker Job
    ↓
finetune.py
```

### Result

Model uploaded to:

```text
AhmedSherif22/TwinLlama-3.1-8B
```

---

## DPO Training

After SFT completes successfully:

Update config:

```yaml
parameters:
  finetuning_type: dpo
  dataset_huggingface_workspace: AhmedSherif22
  is_dummy: true
```

Run:

```bash
uv run zenml pipeline run pipelines.training.training \
-c deployment/manifests/training.yaml
```

### Result

Model uploaded to:

```text
AhmedSherif22/TwinLlama-3.1-8B-DPO
```

---

## Dummy Mode

For testing:

```yaml
is_dummy: true
```

Behavior:

* Uses ~400 examples
* Runs 1 epoch
* Faster and cheaper

For production:

```yaml
is_dummy: false
```

---

## How finetune.py Runs

Do NOT run:

```bash
python finetune.py
```

manually.

SageMaker automatically executes:

```bash
python finetune.py
```

when:

```python
huggingface_estimator.fit()
```

is called.

The training parameters are passed automatically from ZenML to SageMaker.

---

## Common Checks

### Verify datasets

```text
AhmedSherif22/llmtwin
AhmedSherif22/llmtwin-dpo
```

### Verify AWS credentials

```text
AWS_ARN_ROLE
```

### Verify Hugging Face token

```text
HUGGINGFACE_ACCESS_TOKEN
```

### Verify SageMaker permissions

The IAM role must allow:

* SageMaker Training Jobs
* ECR access
* S3 access

---

## Expected Final Models

```text
AhmedSherif22/TwinLlama-3.1-8B
AhmedSherif22/TwinLlama-3.1-8B-DPO
```
