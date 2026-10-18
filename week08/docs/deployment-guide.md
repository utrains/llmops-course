# Astra deployment guide

Astra is a self-hosted inference API for application teams. It runs a pinned Qwen checkpoint through vLLM on EKS Auto Mode, with LiteLLM providing team keys, budgets, rate limits, and spend records. This guide assumes Linux/CLI and cloud experience and focuses on inference delivery and this lab's operational choices.

There are three delivery routes: calling a model provider directly, using a cloud provider's managed model access, or operating the serving stack yourself. Astra exercises the third; these routes do not imply a model-quality ranking.

**Choose the infrastructure path:** use the [AWS Console ClickOps guide](manual-infrastructure-guide.md) to create and inspect every resource, or use the existing Terraform workflow in steps 1–2 below. Both join the same application deployment at step 3. The [advanced AWS CLI supplement](manual-cli-supplement.md) provides an optional API-command route.

**Evidence boundary:** command outputs, timings, and prices retained from the original guide are historical observations from its 14 October 2026 build. The architecture/model-selection revision and new manual infrastructure guides were reviewed on 17 October 2026 without a new AWS deployment. Historical results are not guarantees for another region, model, release, or workload.

## Contents

- [Inference concepts and responsibilities](#inference-concepts-and-responsibilities)
- [The system in one picture](#the-system-in-one-picture)
- [Part 1. The decisions](#part-1-the-decisions)
- [Part 2. Build it](#part-2-build-it)
  - [Step 0. Before you start](#step-0-before-you-start)
  - [Step 1. Build the AWS layer](#step-1-build-the-aws-layer)
  - [Step 2. Connect to the cluster and lay the basics](#step-2-connect-to-the-cluster-and-lay-the-basics)
  - [Step 3. Install monitoring](#step-3-install-monitoring)
  - [Step 4. Add the GPU node pool](#step-4-add-the-gpu-node-pool)
  - [Step 5. Promote the model into the company bucket](#step-5-promote-the-model-into-the-company-bucket)
  - [Step 6. Start the model servers](#step-6-start-the-model-servers)
  - [Step 7. Start the gateway](#step-7-start-the-gateway)
  - [Step 8. Create teams, budgets and keys](#step-8-create-teams-budgets-and-keys)
  - [Step 9. Call the Astra API](#step-9-call-the-astra-api)
  - [Step 10. Prove the controls](#step-10-prove-the-controls)
  - [Step 11. Measure throughput and set the internal price](#step-11-measure-throughput-and-set-the-internal-price)
  - [Step 12. Dashboard, spend report and alerts](#step-12-dashboard-spend-report-and-alerts)
  - [Step 13. What went wrong during the build](#step-13-what-went-wrong-during-the-build)
  - [Step 14. Tear it down](#step-14-tear-it-down)
- [Cost](#cost)
- [Lab shortcuts and their production versions](#lab-shortcuts-and-their-production-versions)
- [What I can explain this week](#what-i-can-explain-this-week)
- [Glossary](#glossary)

## Inference concepts and responsibilities

The model weights are the learned parameters loaded for inference. This lab runs existing weights to generate tokens; it does not train or fine-tune them. A prompt's prefill stage processes input tokens, then decoding generates output tokens progressively. The KV cache retains attention state for active sequences. Longer prompts and more concurrent sequences consume more memory and can increase waiting time even when the weights fit.

| Lab component or resource | Responsibility and reason for this design |
|---|---|
| CPU nodes | Run the loader, LiteLLM, Redis, and monitoring. They handle downloads, request validation, accounting, and orchestration without consuming scarce GPU capacity. CPU and host RAM on GPU nodes also support tokenization, file copying, and the serving process. |
| GPU and VRAM | Perform the model's numerical inference and hold weights/cache. Kubernetes `nvidia.com/gpu: 1` allocates a device; it does not add GPU memory to the pod's ordinary RAM limit. Two replicas each load the model independently. |
| vLLM serving engine | Loads the artifact, batches requests, manages model execution/cache, and exposes an OpenAI-compatible API. It is not the model itself. Its context/concurrency settings trade throughput and latency against memory. |
| LiteLLM gateway | Gives applications the stable name `astra`, checks virtual keys, applies budgets/rate limits, records spend, and calls the backend. It separates team policy from model execution. |
| Redis and RDS | Redis coordinates fast counters between gateway replicas; RDS retains teams, keys, and spend. A volatile counter store and a durable database solve different problems. |
| S3 and node storage | S3 retains the promoted model version. Node `emptyDir` holds a disposable serving copy; EBS-backed Prometheus storage retains metrics across pod restarts. RDS has its own managed storage. |
| VPC routing and access controls | Private subnets host nodes/pods/database; NAT permits external downloads; the S3 endpoint bypasses NAT for regional model storage traffic. SGs constrain AWS network paths; NetworkPolicy prevents ordinary pods from bypassing the gateway. |
| IAM and Kubernetes access | Cluster/node roles let AWS operate infrastructure. Pod Identity gives loader/serving pods distinct bucket permissions. An instructor access entry authorizes cluster administration. Team API keys authorize inference clients. These identities are not interchangeable. |
| Prometheus and Grafana | Observe queueing, token throughput, time to first token, replica availability, and internal spend. GPU utilization alone cannot tell whether users receive timely answers. Langfuse request tracing is outside this baseline. |

## The system in one picture

```
 applications built by AI engineers         EKS cluster (machines in AWS, run by Kubernetes)
 ──────────────────────────────────         ─────────────────────────────────────────────────
 HR assistant      ─┐
 Support bot       ─┤  team key   ┌──────────────┐  vLLM key  ┌──────────────────────────┐
 Data notebooks    ─┼───────────▶ │ LiteLLM x2   │──────────▶ │ vLLM replica 1  (zone A) │  1 x L40S GPU
 Any team's code   ─┘             │ gateway:     │            │ vLLM replica 2  (zone B) │  1 x L40S GPU
                                  │ keys,        │            └──────────────────────────┘
                                  │ budgets,     │                        ▲ weights copied at start
                                  │ rate limits, │                 S3 model bucket
                                  │ spend log    │
                                  └──────┬───────┘
                                         ▼
                               RDS PostgreSQL (teams, keys, spend)       Prometheus + Grafana
```

A request takes this path:

1. An app sends a request to the gateway, with its **team key** attached.
2. The gateway checks the key, the team's budget and its rate limit. Invalid credentials are rejected with an authentication error (historically 401); budget/rate failures returned 429 in this build. Inspect the response body and pinned release's behavior.
3. The gateway sends the request to one of the two vLLM replicas. It uses a second key that only the gateway has.
4. vLLM runs the model on its GPU and returns the answer with a count of input and output tokens.
5. The gateway multiplies the tokens by the internal price, adds the cost to the team's spend in PostgreSQL, and returns the answer to the app.

The diagram shows intended zone separation. Inspect actual node placement: the current spread constraint has no `minDomains`, and RDS/Redis remain single-instance dependencies.

## Part 1. The decisions

Select a model and delivery route against the workload's quality, latency, availability, data, and cost requirements. Adoption evidence and ecosystem maturity inform the shortlist; they do not replace task evaluation. Hardware is sized after promising candidates meet those requirements.

### 1. Which cloud

AWS is the course's existing environment. Astra uses its EKS, IAM, S3, RDS, and networking integrations so the lab can focus on operating inference. An enterprise decision should account for existing systems, regional capacity, data constraints, team skills, and full cost, rather than choosing the provider with the highest market share.

### 2. Three inference delivery routes

| Route | Who hosts and operates inference | Decision relevant to Astra |
|---|---|---|
| **Direct model-provider API** | The model company operates its API and serving infrastructure; your application calls that company directly. | Fast access to the provider's models, with its pricing, availability, data terms, and API lifecycle. You do not operate its GPU fleet. |
| **Cloud-provider managed access** | A cloud service operates the serving layer, such as Amazon Bedrock, Microsoft Foundry Models on Azure, or Gemini API in Google Cloud Vertex AI. | Integrates model access with cloud identity, procurement, regions, and service controls. Available models and deployment types vary. |
| **Self-hosting** | Your organization selects the weights and operates the serving application and capacity. In this lab AWS still manages EKS and Auto Mode infrastructure. | You control the model artifact, serving settings, rollout, and gateway, while owning capacity planning, compatibility, reliability, and operating cost. |

These are delivery routes, not model-quality tiers. The same model family can be available through more than one route. Calling an API does not reveal who operates the GPUs. An SDK chat-model wrapper changes how application code calls an endpoint; it is not a fourth hosting architecture. The cloud examples refer to inference services, not packaged enterprise chat applications. See [Bedrock inference](https://docs.aws.amazon.com/en_en/bedrock/latest/userguide/inference-api.html), [Microsoft Foundry Models](https://learn.microsoft.com/en-us/azure/foundry/concepts/foundry-models-overview), and [Gemini API in Vertex AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/quickstart).

This lab uses self-hosting so students operate the model delivery path: promote weights, provision GPUs, tune serving, enforce team access, observe requests, and remove resources. EKS makes those workloads schedulable and replaceable across zones; Auto Mode reduces node/driver administration while leaving the infrastructure and IAM relationships visible. This is not a claim that self-hosting is always cheaper or more capable. Low utilization, on-call work, and capacity shortages can make managed access the better operational choice.

Within self-hosting, this course uses EKS for scheduling, replacement, and integration with Kubernetes operations. A plain GPU host can support an initial experiment; a managed custom-model endpoint can transfer some infrastructure duties to the cloud service. Data handling still depends on the application, logging, and any external tools it calls; an EKS deployment alone does not prove that every request stays inside an account.

### 3. How EKS gets its machines

Pods need nodes to run on. This decides who starts and stops those machines, and who installs the **GPU drivers**: the software that lets programs use the GPU.

| Option | What it means | Typically chosen when |
|---|---|---|
| **EKS Auto Mode** | AWS starts the right machine when a pod needs one, removes machines nobody uses, and installs the GPU drivers | new clusters; a small platform team |
| EKS with Karpenter installed by you | the same machine-starting program (Karpenter), but you install, configure and upgrade it | you need a Karpenter setting Auto Mode does not offer |
| EKS managed node groups | AWS runs groups of identical machines; you choose how many | a fixed number of machines that rarely changes |
| Self-managed nodes | you build and patch every machine yourself | you need a special operating system |

**Pick: Auto Mode** to manage node provisioning, networking, storage integration, and GPU drivers/device discovery while the class controls workload placement and serving. Do not install duplicate Karpenter, GPU driver/device-plugin, CNI, or EBS components. The original build recorded an additional Auto Mode fee of $0.14516/hour on g6e.xlarge; refresh current pricing before budgeting.

### 4. Two infrastructure build paths

| Route | Purpose | How to continue |
|---|---|---|
| Console ClickOps | Inspect the networking, identities, encryption, logging, cluster, database, and model store as they are created. | Follow [the manual infrastructure guide](manual-infrastructure-guide.md), including its Kubernetes handoff, then join this guide at step 3. |
| Terraform | Provision and track the same configuration from the existing code. | Follow steps 1–2 below. Review the plan and state ownership before applying. |

The inspected module versions are VPC 6.7.3, EKS 21.29.0, and nested KMS 4.0.0. The expanded baseline covers nine AWS service families; the historical four-zone state contains 82 resource/configuration instances, including passwords and a local wait. See the [complete coverage audit](manual-infrastructure-guide.md#complete-source-coverage), including defaults that the root Terraform files do not show.

### 5 Model adoption capabilities and selection

| Open-model author or family group | OpenRouter usage in the dated sample | Meaning |
|---|---:|---|
| DeepSeek families | 14.37 trillion tokens | All included variants, not the 32B distill alone. |
| Qwen families | 5.59 trillion tokens | Family adoption, not Qwen3.8-27B adoption. |
| Meta Llama families | 3.96 trillion tokens | Multiple variants and sizes. |
| Mistral AI open-model group | 2.92 trillion tokens | Author grouping, not every Mistral product. |
| MoonshotAI open-model group | 0.92 trillion tokens | Predates Kimi K3; cannot measure K3 adoption. |

**Scope:** OpenRouter's December 2025 study reports November 2024–November 2025 platform token totals, within a study of more than 100 trillion tokens. These are absolute usage figures, not a global market-share ranking or counts of enterprise deployments. No comparable global percentage was verified; the exact worldwide denominator is unavailable. Private inference and other providers' traffic are outside this sample. [Primary study](https://openrouter.ai/state-of-ai).

| Named adoption evidence | Date and source | Selection value and limit |
|---|---|---|
| AI Singapore built Qwen-SEA-LION-v4-32B-IT on Qwen3-32B | 17 October 2025, updated 19 November; [project announcement](https://sea-lion.ai/blog/qwen-sea-lion-v4-advanced-reasoning/) | Evidence of a named organization's model choice for regional language work; not Qwen3.8 or a banking deployment. |
| Signify integrated Qwen into an Interact City Flex agent in China | 13 March 2026; [Alibaba Cloud customer account](https://www.alibabacloud.com/en/press-room/alibaba-cloud-accelerates-worldwide-ai-innovation?_p_lc=1) | Vendor-reported commercial adoption with a named customer statement; not an independent quality audit. |

For an enterprise shortlist, seek comparable organizations using the model for a comparable task, with measured outcomes and controls. A bank should seek relevant financial-services evidence; the examples above do not establish that. Downloads are artifact retrievals, not customer deployments. GitHub stars are an optional secondary ecosystem signal, not market share or the main reason to choose a model.

#### Exact model capabilities

All rows below generate **text**. None of these specific checkpoints is established here as generating native images, audio, or video. Image/video understanding is different from media generation; an agent that edits a video through tools is not itself a video-generation model. Audio transcription and sampled-frame workflows are external preprocessing unless the exact model documentation says otherwise.

| Exact checkpoint | Native inputs and reasoning behavior | Coding tools and structured output |
|---|---|---|
| [Qwen/Qwen3.8-27B-FP8](https://huggingface.co/Qwen/Qwen3.8-27B-FP8) | Text, image, video understanding; configurable thinking. Native audio is not documented on the card. | Agentic coding and tool use; validate parser and JSON-schema behavior in the serving stack. Astra enables text only and thinking off by default. |
| [moonshotai/Kimi-K3](https://huggingface.co/moonshotai/Kimi-K3) | Text, image, video understanding; thinking always enabled, effort low/high/max. Native audio is not established. | Long-horizon coding and tool use. Preserve returned reasoning/tool fields in multi-turn requests. Schema guarantees must be tested on the selected endpoint. |
| [google/gemma-3-27b-it](https://ai.google.dev/gemma/docs/core/model_card_3) | Text and image input; text output. No native audio/video input specified; extracted frames or transcripts are separate workflows. | General instruction, code, and visual tasks. Do not infer native tool-protocol reliability from JSON prompting; validate templates and constrained decoding. |
| [openai/gpt-oss-20b](https://developers.openai.com/api/docs/models/gpt-oss-20b) and [openai/gpt-oss-120b](https://developers.openai.com/api/docs/models/gpt-oss-120b) | Text input/output; configurable low/medium/high reasoning. No native image/audio/video input. | Native tool-oriented behavior and structured-output support; Harmony formatting and runtime compatibility matter. Treat the two sizes as separate evaluation candidates. |
| [deepseek-ai/DeepSeek-R1-Distill-Qwen-32B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B) | Text input/output, reasoning-oriented distilled model. No native image/audio/video input. | Math/code candidate; not the full DeepSeek-R1 model or its hosted API. Tool/JSON reliability requires separate testing. |
| [meta-llama/Llama-3.3-70B-Instruct](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct) | Text input/output; instruction-tuned. No native image/audio/video input. | Multilingual dialogue/code and documented tool-use formats; test schema adherence with the chosen runtime. |
| [mistralai/Mistral-Small-3.2-24B-Instruct-2506](https://huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506) | Text and image input, text output. Native audio/video is not established for this checkpoint. | Publisher documents improved instruction following and function calling; validate its Mistral template/parser and structured outputs. |

#### Evidence operating requirements and access

These are shortlist inputs, not a cross-vendor benchmark league table. Published scores use different harnesses, prompts, budgets, and model dates. No common Astra workload benchmark has been run for this revision.

| Candidate | Relevant quality evidence | Delivery and operational implications |
|---|---|---|
| Qwen3.8-27B-FP8 | Publisher's Qwen3.8-27B table reports Terminal Bench 2.1 with Terminus 73.0 and SWE-bench Pro 61.7; it describes FP8 metrics as nearly matching the original. These are publisher results, not Astra measurements. | Downloadable Apache-2.0 artifact; retain notices. Exact hosted 27B service is marked coming soon on the card, so do not promise its availability. Astra's single-L40S FP8 layout is a lab constraint, with latency/throughput to be measured. |
| Kimi K3 | Publisher reports GPQA Diamond 93.5 and Terminal-Bench 2.1 88.3 at max reasoning; coding result uses Kimi Code. Not directly comparable to a different harness or Astra's thinking-off configuration. | Official downloadable weights and direct `kimi-k3` API. Cloud-managed availability must be verified by exact catalog/region; none is assumed. 2.8T total/104B active parameters and MXFP4 weights imply a distributed accelerator deployment, not a replacement image on one L40S. |
| Gemma 3 27B IT | Google reports GPQA Diamond 42.4, LiveCodeBench 29.7, and MMMU validation 64.9 under the card's stated settings. | Downloadable under Gemma terms and prohibited-use policy, not Apache-2.0. BF16 weight arithmetic alone is about 54 GB; quantized runtime/context must be sized. Exact hosted availability is a separate catalog check. |
| gpt-oss 20b and 120b | Official docs identify reasoning, tool, and structured-output capabilities. Compare the two checkpoints on the actual task; do not transfer a 120b result to 20b. | Downloadable Apache-2.0. OpenAI serving guidance describes about 16 GB for 20b with MXFP4 and H100-class capacity for 120b; engine/kernel support changes the requirement. Downloadable does not mean served by the OpenAI API. |
| R1 Distill Qwen 32B | Publisher provides math/code reasoning evaluations for this exact distill. Check answer correctness and long reasoning latency separately from full R1 results. | Downloadable MIT weights with upstream Qwen attribution obligations. Rough BF16 weights are 64 GB before cache; quantization and quality need validation. Full R1 API access does not prove access to this distill. |
| Llama 3.3 70B Instruct | Publisher supplies instruction, reasoning, code, and tool evaluations; reproduce relevant multilingual/tool tasks. | Downloadable under Llama 3.3 Community License and acceptable-use terms, including additional commercial conditions. About 140 GB of BF16 weights before cache; quantization or multi-GPU sizing required. Verify exact managed-cloud offering separately. |
| Mistral Small 3.2 24B | Publisher's comparison focuses on instruction following, fewer repetitions, and function calling. Evaluate those behaviors and image tasks on your corpus. | Downloadable Apache-2.0. About 48 GB BF16 weights before runtime/cache; lower precision or larger memory may be required. Direct/cloud model aliases can change; confirm the exact 2506 checkpoint rather than assuming an alias is identical. |

**Kimi K3 is downloadable.** Its official [repository](https://github.com/MoonshotAI/Kimi-K3) links deployment recipes; autogenerated Hugging Face single-line run examples are not hardware sizing guidance. At four bits, 2.8T parameters alone imply roughly 1.4 TB before metadata, non-quantized tensors, runtime, cache, and replicas. This is an arithmetic lower-bound illustration, not a supported server specification. Active parameters reduce per-token computation, not the need to distribute the full model. K3 belongs in the production shortlist when its workload benefits justify that infrastructure or its hosted API.

The [Kimi K3 License](https://huggingface.co/moonshotai/Kimi-K3/blob/main/LICENSE) is custom. It requires notices, has a separate-agreement condition for qualifying Model-as-a-Service businesses above USD 20 million aggregate revenue over a consecutive twelve-month period, and branding conditions for certain very large commercial products. Its defined internal-use and research exceptions matter. Read the exact terms for the intended deployment; do not label it MIT or Apache-2.0.

For latency, throughput, and cost, compare the same prompt/output lengths, concurrency, reasoning effort, quantization, hardware, cache conditions, and region. Record p50/p95 time to first token, output tokens/second, successful requests/second, failures, and **cost per successfully completed task**. Public API token prices and GPU hourly rates are not directly interchangeable, and no universal speed ranking or current price quote is asserted here.

#### Select for production before sizing hardware

1. Define the workload: HR questions, code changes, tool execution, structured extraction, images, languages, context lengths, and prohibited failure modes. Set quality thresholds and latency/availability SLOs.
2. Build a representative, held-out evaluation set. Include malformed inputs, unsupported questions, tool errors, schema validation, and relevant safety/privacy tests. Score answers with task-appropriate automated checks and expert review.
3. Shortlist exact model revisions and delivery routes using capability, credible comparable adoption, license, and data requirements. Include Kimi K3 when relevant even if it exceeds the teaching GPU budget.
4. Benchmark candidates with the intended serving stack and load. Compare quality, SLO attainment, risk, and full operating cost, then size accelerators, replicas, storage, and concurrency for the candidates that pass.
5. Pin the selected artifacts and runtime, run a canary, and repeat the evaluation before model or quantization changes.

**Astra's current candidate is Qwen3.8-27B-FP8**, retained to match the existing implementation. Published capabilities make it a reasonable candidate for the lab's text, tool, and structured-response exercises, but the repository does not establish a comparative production evaluation. One-GPU fit makes the course practical; it is not the primary enterprise selection argument. Model quality and platform performance are joint responsibilities of application and platform teams.

The current manifest uses `--language-model-only`, a 32,768-token limit, thinking off by default, and Qwen-specific reasoning/tool parsers. It does not expose the model's image/video capabilities, train/fine-tune it, or provision an agent tool sandbox. Replacing Qwen with Kimi, Gemma, or another model requires corresponding artifact, template/parser, memory, inference API, license, and evaluation changes—not only changing the model name.

### 6. Precision memory and the KV cache

Weight precision affects memory, kernel compatibility, throughput, and potentially answer quality. GPU VRAM must hold weights, runtime workspaces, and the attention KV cache; host RAM and node disk are separate budgets. Quantized file size alone is not a fit guarantee.

| Representation | Rough 27B weight arithmetic | What must still be tested |
|---|---|---|
| BF16 | About 54 GB before overhead | Larger memory or tensor parallelism, runtime buffers, cache |
| FP8 | About 27 GB before scales/other tensors; the historical artifact was 28.8 GiB on disk | Kernel support, quality, available cache, latency under load |
| Four-bit quantization | About 13.5 GB before scales/other tensors | Exact format/runtime compatibility and quality regression; not every four-bit artifact behaves the same |

Astra uses the publisher's FP8 checkpoint and gives each replica one L40S. The configured 32,768-token context and 128-sequence cap are limits, not a promise that 128 maximum-length requests fit. Measure cache capacity and queueing with the intended prompt/output mix before setting concurrency SLOs.

### 7. Which GPU machine

The lab capacity choice is one L40S per FP8 replica. The following prices are historical 14 October 2026 observations; refresh them and verify regional capacity before use.

| Instance type | GPU | GPU memory | On-demand price, us-east-1 |
|---|---|---|---|
| g6.xlarge | 1 x NVIDIA L4 | 24 GB | $0.8048 an hour; too small for the FP8 model |
| g5.xlarge | 1 x NVIDIA A10G | 24 GB | $1.006 an hour; too small for the FP8 model |
| **g6e.xlarge** | 1 x NVIDIA L40S | 48 GB | $1.861 an hour |
| g6.12xlarge | 4 x L4 | 96 GB in total | $4.6016 an hour; the model would be split across 4 GPUs |
| p4d.24xlarge | 8 x A100 | 320 GB in total | $21.9576 an hour |
| p5.48xlarge | 8 x H100 | 640 GB in total | $55.04 an hour |

**Lab capacity choice: g6e.xlarge**, with one 48 GB L40S, 4 vCPUs, and 32 GiB host RAM. Fit is a feasibility check after model evaluation, not evidence that this is the best model or cheapest production architecture. Astra also allows g6e.2xlarge and g6e.4xlarge: the same single GPU with more CPU and memory, at a higher price. AWS sometimes runs out of g6e.xlarge, and then those bigger sizes are used instead ([step 4](#step-4-add-the-gpu-node-pool)).

### 8. Serving engine

Astra pins **vLLM `v0.31.0`** to load the Qwen artifact, batch requests, manage the KV cache, and expose the OpenAI-compatible chat interface. Its Qwen reasoning and tool parsers, language-model-only mode, context limit, and thinking default are part of the serving contract. SGLang or TensorRT-LLM are alternative runtime candidates when exact model support and measured workload performance justify a change; repository stars do not decide compatibility or throughput. [Pinned release](https://github.com/vllm-project/vllm/releases/tag/v0.31.0).

### 9. Gateway

**LiteLLM `v1.101.6`** separates team policy from GPU execution: virtual keys, team budgets/rate limits, routing, and spend persistence. Two replicas share Redis counters and RDS records. Verify accounting lag, concurrent overshoot, and fail/restart behavior on the pinned release; a pre-request budget check is not an exact transactional spending ceiling. Feature availability can vary by release and license, so validate the configured metrics and controls rather than assuming every LiteLLM feature is included. [Virtual keys](https://docs.litellm.ai/docs/proxy/virtual_keys), [Prometheus integration](https://docs.litellm.ai/docs/proxy/prometheus).

### 10. Monitoring

The pinned **kube-prometheus-stack `92.6.0`** chart installs Prometheus Operator, Prometheus, Grafana, Alertmanager, kube-state-metrics, and node-exporter. It supplies the PodMonitor and PrometheusRule CRDs used by the serving manifests. Inspect throughput, queueing, time to first token, failures, replica health, and spend together. The source provides dashboards and alert rules but no external notification receiver. [Pinned chart](https://github.com/prometheus-community/helm-charts/releases/tag/kube-prometheus-stack-92.6.0).

### 11. How teams pay for a model the company runs itself

| Option | How it works | What goes wrong |
|---|---|---|
| Free for all | the platform team's budget pays everything | nobody holds back; the GPUs fill up and everyone waits |
| Fixed share per team | each team pays a fixed part of the GPU bill | a team that barely uses Astra pays as much as a heavy user |
| Reserved GPUs per team | each team gets its own replicas | expensive; idle GPUs in every team |
| **Internal price per token** | the gateway prices every token so that expected use covers the GPU bill | the price must come from measurements, and be checked again later |

**Pick: an internal price per token**, with a monthly budget per team.

### 12. Smaller choices

| Decision | Options | Pick and why |
|---|---|---|
| Where the gateway keeps its records | a database inside the cluster, or **Amazon RDS PostgreSQL** | RDS: AWS backs it up and patches it, and it survives if the cluster is rebuilt |
| Where the weights come from when a replica starts | Hugging Face over the internet each time, or the company's **S3 bucket** | S3: a promoted copy reached through the regional gateway endpoint; avoids NAT processing for those copies, while S3 charges still apply |
| Where passwords and keys are kept | **AWS Secrets Manager**, or HashiCorp Vault | Secrets Manager: an AWS service, so nothing extra to run |
| How programs get AWS permissions | stored access keys, IRSA, or **EKS Pod Identity** | Pod Identity: distinct loader-write and serving-read roles without static AWS credentials in pods |
| How changes reach the cluster | by hand with commands, **Argo CD** or Flux | by hand in this lab so you see each step; Argo CD in a company (see the end of this guide) |

## Part 2. Build it

### Execution contract

Commands use Bash. Run from `week08`, which contains `k8s/`, `scripts/`, and `terraform/`, unless a block changes directory. Authenticate to the intended AWS account/role and review the active kubectl context before mutations. Stop on a failed prerequisite; do not run the document as an unattended script. Output blocks are historical evidence, not commands.

The Console route uses its own rendering/secret handoff and rejoins at step 3. Steps 1–2 below are the Terraform route. Both require compatible AWS CLI, kubectl, Helm, and application dependencies.

### Step 0. Before you start

**What this step does:** checks that your computer has the tools, and that your AWS account is allowed to rent GPU machines.

The original build used the tool versions below. Check current availability and compatibility before repeating it; these are historical test pins, not a latest-version list.

| Tool | What it does | Tested version |
|---|---|---|
| AWS CLI | lets you control AWS by typing commands | 2.35.12 |
| Terraform | builds AWS resources from the files in `terraform/` | 1.13.3 |
| kubectl | talks to the Kubernetes cluster | 1.36.2 |
| Helm | installs packaged software (charts) into the cluster | 4.1.4 |
| Python with the `openai` and `python-dotenv` packages | runs the example app in step 9 | Python 3.13, openai 3.0.0 |

Check that you are signed in to AWS:

```bash
aws sts get-caller-identity
```

Confirm the returned account and role. Authenticate through the intended SSO/role profile before continuing; do not create long-lived access keys just for this lab.

AWS limits how many GPU machines each account may run. That limit is a **quota**, counted in vCPUs. Check yours:

```bash
aws service-quotas get-service-quota --service-code ec2 --quota-code L-DB2E81BA --query 'Quota.Value'
```

`L-DB2E81BA` is AWS's code for the quota named **Running On-Demand G and VT instances**: G is the GPU family letter. Two g6e.xlarge require 8 vCPUs. The allowed g6e.4xlarge fallback and third rollout GPU can require 48 vCPUs, plus existing G/VT usage. Request capacity for the intended fallback/rollout policy in Service Quotas before continuing; quota is not a GPU stock reservation.

### Step 1. Build the AWS layer

**Terraform route only.** For Console creation, follow [manual-infrastructure-guide.md](manual-infrastructure-guide.md) through its Kubernetes handoff, then continue at step 3 here.

Terraform configures VPC routing/subnets/NAT/S3 endpoint, EKS Auto Mode, EC2/EBS permissions, IAM roles/access/Pod Identity, S3, RDS, Secrets Manager, KMS encryption, and CloudWatch logging. The [expanded resource audit](manual-infrastructure-guide.md#complete-source-coverage) includes policy attachments, security-group rules, adopted VPC defaults, and the otherwise unused OIDC provider/extra node SG.

Before planning, confirm the selected region offers g6e.xlarge in **at least three** zones. The source's check accepts two, but its first-three-subnets expression needs three; a two-zone redesign requires a source change. Confirm Kubernetes 1.36 is supported and inspect the installed module versions. State and saved plans contain sensitive values.

Copy the example settings and determine the administrator's permitted public egress address:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
curl -s https://checkip.amazonaws.com
```

Open `terraform.tfvars` in a text editor. Put the IP address into `admin_cidrs`, followed by `/32`, for example `["203.0.113.7/32"]`. Only the configured CIDRs may reach the public control-plane endpoint; the private endpoint is also enabled.

Initialize, inspect the saved plan, and apply only after checking its account, resource changes, module versions, and zone count:

```bash
terraform init
terraform plan -out tfplan
terraform apply tfplan
cd ..
```

Inspect the plan before applying. The module versions and selected zones determine the final resource count; the historical 82 includes configurations and local helpers, not 82 independent AWS services.

Real result of the apply:

```
Apply complete! Resources: 78 added, 0 changed, 0 destroyed.
real	17m12.803s
```

It took 17 minutes. That first test build used three zones, so it created 78 resources; the final code uses four and plans 82.

Retain and protect `terraform.tfstate`; it tracks resource ownership and contains sensitive values needed for subsequent changes and teardown.

Terraform picks the Availability Zones that sell `g6e.xlarge`, up to four. In `us-east-1` (AWS's region in Northern Virginia) it picked `us-east-1a`, `1b`, `1c` and `1d`. The control plane uses the first three. The GPU machines may use all four, which helps when one zone runs out of GPUs.

### Step 2. Connect to the cluster and lay the basics

**Terraform route only:** configure access, apply platform policy/storage, render AWS outputs into manifests, and copy the platform secret. The Console route already performs these operations in its own handoff.

```bash
aws eks update-kubeconfig --region us-east-1 --name astra-lab
kubectl get nodepools
```

Verify the intended account/cluster context and that both built-in pools are ready.

```
NAME              NODECLASS   NODES   READY   AGE
general-purpose   default     0       True    6m49s
system            default     0       True    6m49s
```

Look at the `NODES` column. Zero machines is expected: Auto Mode starts a machine only when a pod needs one, so an empty pool need not incur EC2 charges. EKS, NAT, and other provisioned services still incur charges.

Apply the shared platform configuration before installing workloads.

```bash
kubectl apply -f k8s/00-platform.yaml
```

The six objects provide three namespaces (`llm`, `gateway`, `monitoring`), the encrypted Auto Mode gp3 StorageClass, network-policy enforcement configuration, and the loader service account. The loader's Pod Identity association grants S3 publication access.

Some manifests need values that only exist after Terraform ran, such as the bucket's name. The `render.sh` script copies each file from `k8s/` into `build/` with those values filled in:

```bash
bash scripts/render.sh
```

```
Rendered into build/ for cluster astra-lab (bucket astra-lab-models-69e87c59890cc23f719b0ae5fc)
```

From now on you apply the files in `build/`.

Copy the Terraform-generated platform values from Secrets Manager into the three runtime Kubernetes Secrets. This is a one-time synchronization; subsequent changes require an explicit refresh and affected-pod rollout:

```bash
bash scripts/create-secrets.sh
```

```
secret/vllm-api-key created
secret/litellm-env created
secret/grafana-admin created
Secrets created in namespaces llm, gateway and monitoring.
```

`vllm-api-key` is the key vLLM will demand. `litellm-env` holds the gateway's admin key (the **master key**), its database address and the vLLM key. `grafana-admin` is the dashboard password.

### Step 3. Install monitoring

**What this step does:** installs Prometheus, which collects numbers from every program, and Grafana, which draws them.

It comes before the model and the gateway for one reason. Their manifests contain two kinds of objects that do not exist in plain Kubernetes: a **PodMonitor** (tells Prometheus which pods to collect numbers from) and a **PrometheusRule** (defines alerts). This chart adds those object types to the cluster.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack --version 92.6.0 \
  -n monitoring -f k8s/60-monitoring-values.yaml --wait --timeout 15m
```

The values file requests 20 GiB of encrypted gp3 storage for Prometheus, seven-day retention, and the Grafana password Secret. Confirm the release, CRDs, and PVC are ready before applying PodMonitors.

It took 1 minute 33 seconds.

### Step 4. Add the GPU node pool

**What this step does:** tells Auto Mode which GPU machines it may rent, and how to build them.

The file `k8s/10-gpu-nodepool.yaml` holds two objects:

- The **NodeClass** says how a GPU machine is built. It names the IAM role the machine uses and gives it 200 GiB of EBS-backed ephemeral storage for images and model copies; g6e does not provide local NVMe for this setting. It places the machine in the private subnets, found by the label `astra/cluster`.
- The **NodePool** says which machines may be rented: g6e.xlarge, g6e.2xlarge or g6e.4xlarge, on-demand only, and never more than 3 GPUs in total. That limits concurrent GPU capacity, not the total bill or a guaranteed dollar ceiling.

The NodePool also puts a **taint** on every GPU machine. Only vLLM carries the matching toleration in this baseline. That keeps small programs from taking space on a $1.86-an-hour machine.

```bash
kubectl apply -f build/10-gpu-nodepool.yaml
kubectl get nodeclass gpu
```

Look for `READY True` in the second command's output. No GPU machine starts yet: the first one starts in step 6, when vLLM asks for a GPU.

**GPUs can run out.** AWS has a limited number of each machine type in each zone. During this build AWS had no g6e.xlarge in any zone of `us-east-1` for about 20 minutes. Each attempt failed with:

```
InsufficientInstanceCapacity: We currently do not have sufficient g6e.xlarge capacity in the Availability Zone you requested (us-east-1c).
```

The NodePool at first allowed only g6e.xlarge, so nothing started. Allowing every g6e size with one GPU got a g6e.2xlarge in `us-east-1c`. Later it also got a g6e.8xlarge and a g6e.16xlarge, which cost $4.53 and $7.58 an hour for the same single GPU. So the final NodePool allows only the three sizes up to 4xlarge. A company that cannot wait for GPUs pays in advance to hold them: an **On-Demand Capacity Reservation** (held machines, paid by the hour whether used or not) or an **EC2 Capacity Block** (GPUs booked for fixed dates).

### Step 5. Promote the model into the company bucket

**What this step does:** downloads the model once from Hugging Face and stores the approved copy in the company's S3 bucket. "Promote" means moving a reviewed version to where production uses it.

The download runs inside the cluster as a **Job**: a pod that runs a task once and stops when it is done.

```bash
kubectl create -f build/20-model-loader.yaml
kubectl -n llm get jobs -w
```

Wait for the loader Job to complete, then inspect its final log lines and the promoted marker. Select the actual Job name if previous runs remain.

```bash
kubectl -n llm logs job/$(kubectl -n llm get jobs -o jsonpath='{.items[0].metadata.name}') --tail=2
```

```
Total Objects: 79
   Total Size: 28.8 GiB
```

The Job copied 79 files, 28.8 GiB in total, and ran for 9 minutes 13 seconds. The weights themselves are in files ending in `.safetensors`.

The Job writes one more file last, called `_PROMOTED`. The model servers wait until that file exists. If the copy fails halfway, the file is missing, and no server loads half a model. Step 13 shows a real failure this rule caught.

### Step 6. Start the model servers

**What this step does:** starts two vLLM replicas, each requesting one GPU. Verify their actual zone placement after scheduling.

```bash
kubectl apply -f build/30-vllm.yaml
kubectl -n llm get pods -o wide -w
```

`-o wide` adds columns, including which node each pod runs on. Watch the `STATUS` column. You will see these, in order:

| Status | What is happening |
|---|---|
| `Pending` | no machine has room yet; Auto Mode is renting a GPU machine |
| `Init:0/1` | the machine is up and the **init container** (a container that must finish before the main one starts) is copying the weights from S3 to the machine's disk |
| `Running`, `READY 0/1` | vLLM is loading the weights onto the GPU and warming up |
| `Running`, `READY 1/1` | the replica answers requests |

The Deployment maintains the two serving replicas. These settings control capacity, isolation, and replacement:

| Setting | What it does |
|---|---|
| `replicas: 2` | keep two copies running |
| zone spread rule (`topologySpreadConstraints`) | requests balanced zone placement with maxSkew 1 and DoNotSchedule; without minDomains, two distinct zones are not guaranteed. Inspect actual placement |
| init container `fetch-model` | copies the 29 GiB of weights from S3 to the local disk, after waiting for `_PROMOTED` |
| `nvidia.com/gpu: 1` | each replica asks for one whole GPU |
| `--max-model-len 32768` | the longest conversation one request may hold: 32,768 tokens of question plus answer |
| `--max-num-seqs 128` | the most requests one GPU works on at the same time (step 13 explains why 128) |
| `--default-chat-template-kwargs '{"enable_thinking": false}'` | thinking mode is off unless a request turns it on, so answers are short and fast by default |
| `--api-key` | vLLM answers only requests that carry the vLLM key, which only the gateway has |
| `enableServiceLinks: false` | stops Kubernetes adding a setting that breaks vLLM (step 13) |
| **NetworkPolicy** `vllm-ingress` | a firewall rule: only pods in the `gateway` and `monitoring` namespaces may connect to vLLM |
| `maxSurge: 1`, `maxUnavailable: 0` | when you change the manifest, start one new replica first, and stop an old one only when the new one is ready |
| **PodDisruptionBudget** `minAvailable: 1` | planned work, such as replacing a machine, may take away at most one replica at a time |
| **Service** `vllm` | one fixed name and address, `vllm.llm.svc.cluster.local:8000`, in front of both replicas; it spreads requests between them |

On a new GPU machine, the first replica took about 8 minutes from getting a machine to being ready:

- 1 minute 48 seconds to download the 9.0 GB vLLM image,
- about 2 minutes to copy the weights from S3,
- 2 minutes 22 seconds for vLLM to load the weights, prepare the GPU and warm up.

Read what vLLM printed while starting:

```bash
kubectl -n llm logs deploy/vllm -c vllm | grep -E "Loading weights took|KV cache size|startup complete"
```

Inspect the serving container's weight-loading and KV-cache measurements before treating the configured concurrency as usable capacity.

```
(EngineCore pid=115) INFO 10-14 15:02:23 [default_loader.py:484] Loading weights took 73.14 seconds
(EngineCore pid=115) INFO 10-14 15:04:22 [gpu_worker.py:707] CUDA graph memory profiling is enabled ...
(EngineCore pid=115) INFO 10-14 15:04:22 [kv_cache_utils.py:2464] GPU KV cache size: 135,168 tokens, Maximum concurrency for 32,768 tokens per request: 4.12x
INFO:     Application startup complete.
```

In the historical run, loading weights took 73 seconds on this replica and 11 seconds on the other; cache and initialization conditions affect these timings.

The third line needs explaining. While the model answers, it keeps working notes for every token of the conversation so it never redoes work. Those notes are the **KV cache**, and they live in GPU memory. After the weights, this GPU has room for notes on 135,168 tokens. That is enough for about 4 conversations at the 32,768-token maximum, or for many short ones at the same time.

Check that both replicas are ready:

```bash
kubectl -n llm get deploy vllm
```

```
NAME   READY   UP-TO-DATE   AVAILABLE
vllm   2/2     2            2
```

`READY 2/2` means two replicas were asked for, and two are answering.

### Step 7. Start the gateway

**What this step does:** starts two LiteLLM gateway replicas and Redis, and connects your computer to the gateway.

```bash
kubectl apply -f build/40-gateway.yaml
kubectl -n gateway rollout status deploy/litellm
```

`rollout status` waits until every replica of the new version is running, then prints `successfully rolled out`.

The gateway's settings live in a **ConfigMap**, a Kubernetes object that holds a settings file, named `litellm-config` in `k8s/40-gateway.yaml`. It lists one model, named `astra`. Apps only ever ask for `astra`. The platform team can later put a newer model behind that name without any app changing its code. The ConfigMap also holds the internal price per token (step 11).

The cluster's programs are not reachable from the internet, by design. In a company, the gateway gets an internal web address that the company's applications use. In this lab, you reach it from your laptop through a tunnel, opened with **port-forward**:

```bash
kubectl -n gateway port-forward svc/litellm 4000:4000
```

Keep this terminal open and use a second terminal for API calls. Port-forward is the lab access path; it does not create a production ingress endpoint.

The tunnel closes when its terminal closes, when it sits idle, when the laptop sleeps, or when the pods behind it restart. Requests then fail on your laptop even though everything in the cluster is fine. To have it reopen by itself, run it in a loop instead:

```bash
while true; do kubectl -n gateway port-forward svc/litellm 4000:4000; echo "tunnel closed, reopening"; sleep 2; done
```

Stop the reconnect loop when the lab is finished.

In the second terminal, ask the gateway whether it is healthy:

```bash
curl -s localhost:4000/health/readiness
```

```
{"status":"healthy","db":"connected"}
```

`"db":"connected"` confirms gateway-to-RDS connectivity; model readiness must be checked separately.

### Step 8. Create teams, budgets and keys

**What this step does:** creates four teams in the gateway, each with a monthly budget and rate limits, and one key per team.

```bash
bash scripts/create-teams.sh
```

| Team | Monthly budget, internal $ | Requests per minute | Tokens per minute | Who uses it |
|---|---|---|---|---|
| hr-assistant | 50 | 60 | 200,000 | the HR team's app |
| support-bot | 150 | 300 | 1,000,000 | customer support reply drafts |
| platform-loadtest | 50 | 10,000 | 50,000,000 | the platform team's load test in step 11 |
| intern-sandbox | 0.01 | 5 | 20,000 | the drills in step 10 |

"Internal $" means dollars at the internal price, moved between the company's own budgets. No money leaves the company. Each budget starts again from zero at the start of a new period; the spend report in step 12 shows the date (1 November in the test build).

The script saves one key per team in `build/keys.env`. Git is told to ignore that file, so the keys never end up in the shared code. The script took 4.8 seconds.

In a company, the platform team hands each key to its team through a secrets store such as Secrets Manager, never in chat or e-mail.

### Step 9. Call the Astra API

**What this step does:** calls Astra exactly as the company's AI engineers do from their applications. This is the product the platform delivers.

Astra exposes an OpenAI-compatible chat-completions interface. Existing clients can use a different base URL, key, and model name, but compatibility must be checked per endpoint and feature; this does not implement every OpenAI API.

**What an AI engineer receives from the platform team:**

| Item | Value in this lab | In a company |
|---|---|---|
| Base URL (the API's address) | `http://localhost:4000/v1`, through the port-forward from step 7 | an internal web address such as `https://astra.internal.example.com/v1` |
| Key | their team's key, from `build/keys.env` | delivered through a secrets store |
| Model name | `astra` | `astra`, plus any additional hosted or self-hosted models configured by the platform |
| Limits | the team's budget, requests per minute and tokens per minute (step 8); 32,768 tokens per conversation | the same, agreed with the team |

**What the API offers:**

| Endpoint or feature | What it is for |
|---|---|
| `GET /v1/models` | lists the models this key may use |
| `POST /v1/chat/completions` | sends messages and gets the answer |
| `"stream": true` | the answer arrives a few tokens at a time, as it is written |
| `tools` | **tool calling**: the model asks the app to run one of the app's functions, such as a database lookup |
| `response_format` with a JSON schema | **structured output**: the answer is JSON in the shape the app describes |
| `user` | the app passes the ID of its own end user, so spend is also recorded per person |
| `chat_template_kwargs` | switches the model's thinking mode on for one request |

Each feature below was tested against the running platform.

**List the models.** Load the locally generated team credentials and check which model the HR key may access.

```bash
source build/keys.env
curl -s localhost:4000/v1/models -H "Authorization: Bearer $HR_KEY"
```

```
{"data":[{"id":"astra","object":"model","created":1677610602,"owned_by":"openai"}],"object":"list"}
```

The HR key may use one model, `astra`. `owned_by: openai` describes the request format, not who runs the model.

**Send a question with curl:**

```bash
curl -s localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $HR_KEY" -H "Content-Type: application/json" \
  -d '{"model":"astra","messages":[{"role":"user","content":"In one sentence, what is Kubernetes?"}]}'
```

The team key authenticates the request; the `messages` payload and `astra` alias identify the task and backend contract.

The answer, cut to the important lines:

```
"content": "Kubernetes is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications."
"usage": {"completion_tokens": 26, "prompt_tokens": 20, "total_tokens": 46}
```

`content` is the answer. `usage` is the token count the gateway bills: `prompt_tokens` are input tokens, `completion_tokens` are output tokens. The call took 1.4 seconds.

**Send a question from Python.** The example uses OpenAI's Python SDK against Astra's compatible endpoint; this is a client-library choice, not a fourth inference delivery route. It reads two settings from a file named `.env`: `OPENAI_BASE_URL`, the gateway's address, and `OPENAI_API_KEY`, the team key.

Copy `examples/.env.example` to `examples/.env`. Open both `examples/.env` and `build/keys.env`, and copy the value after `HR_KEY=` into `OPENAI_API_KEY=`. Then run the example:

```bash
cd examples
python ask_astra.py
cd ..
```

```
To ensure a smooth start, you should prepare your signed onboarding documents, photo ID, and a list of emergency contacts. It is also wise to bring personal items like a water bottle and notebooks, while checking with HR for any specific tech requirements beforehand.
CompletionUsage(completion_tokens=52, prompt_tokens=41, total_tokens=93, ...)
```

Open `examples/ask_astra.py` and read it. It is the same code an engineer writes for OpenAI. Its first message, `"role": "system"`, is a **system prompt**: instructions the model follows for the whole conversation. Each application writes its own.

**Streaming.** Add `"stream": true` to the request. The answer arrives a few tokens at a time, as it is written, so an app can show it word by word. Each piece starts with `data:`:

```
data: {"id":"chatcmpl-b3d32f1db8d3f394","object":"chat.completion.chunk","model":"astra","choices":[{"index":0,"delta":{"content":"1"}}]}
```

**Tool calling.** The app describes a function it can run, here `get_vacation_balance`. The model does not run it. It answers with a request for the app to run it:

```bash
curl -s localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $HR_KEY" -H "Content-Type: application/json" \
  -d '{"model":"astra",
       "messages":[{"role":"user","content":"How many vacation days does employee E1042 have left?"}],
       "tools":[{"type":"function","function":{"name":"get_vacation_balance",
         "description":"Look up an employee vacation balance",
         "parameters":{"type":"object","properties":{"employee_id":{"type":"string"}},"required":["employee_id"]}}}]}'
```

The answer, cut to the important lines:

```
"finish_reason": "tool_calls"
"tool_calls": [{"function": {"arguments": "{\"employee_id\": \"E1042\"}", "name": "get_vacation_balance"}, "id": "chatcmpl-tool-a306698a8ad6e1cd", "type": "function"}]
"content": null
```

The app runs its own function with `employee_id` E1042, gets `{"days_left": 7}`, and sends that back as a message with `"role":"tool"`. Astra then answered: `Employee E1042 has **7 vacation days** remaining.` Tool calling works because vLLM was started with `--enable-auto-tool-choice --tool-call-parser qwen3_coder` (step 6).

**Structured output.** The app describes the JSON it needs with a **JSON schema**, a description of the fields and their types:

```bash
curl -s localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $HR_KEY" -H "Content-Type: application/json" \
  -d '{"model":"astra",
       "messages":[{"role":"user","content":"Extract the fields: Maria Lopez starts on 3 November 2026 as a Data Analyst in Chicago."}],
       "response_format":{"type":"json_schema","json_schema":{"name":"new_hire","schema":{"type":"object",
         "properties":{"name":{"type":"string"},"start_date":{"type":"string","description":"YYYY-MM-DD"},
                       "role":{"type":"string"},"city":{"type":"string"}},
         "required":["name","start_date","role","city"],"additionalProperties":false}}}}'
```

The `content` of the answer:

```
{
  "name": "Maria Lopez",
  "start_date": "2026-11-03",
  "role": "Data Analyst",
  "city": "Chicago"
}
```

The app can load this straight into its own data, with no text parsing.

**Spend per end user.** A team key identifies the application. To see which of the application's own users caused the cost, the app adds `"user"` to each request:

```bash
curl -s localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $HR_KEY" -H "Content-Type: application/json" \
  -d '{"model":"astra","user":"maria.lopez@example.com","messages":[{"role":"user","content":"Say OK."}]}'
```

The platform team reads it back with the gateway's admin key. Step 10 shows how to load it into `$MASTER`.

```bash
curl -s "localhost:4000/customer/info?end_user_id=maria.lopez@example.com" -H "Authorization: Bearer $MASTER"
```

```
{"user_id": "maria.lopez@example.com", "spend": 1.129e-05, ...}
```

`1.129e-05` is a short way to write 0.00001129 internal dollars. The spend appeared about 30 seconds after the request, because the gateway writes spend to its database in batches.

**Thinking mode.** Thinking is off by default (step 6). A request turns it on with `chat_template_kwargs`:

```bash
curl -s localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $HR_KEY" -H "Content-Type: application/json" \
  -d '{"model":"astra","max_tokens":3000,"chat_template_kwargs":{"enable_thinking":true},
       "messages":[{"role":"user","content":"A team used 1.2 million output tokens at $1 per million and 4 million input tokens at $0.20 per million. What is their bill? Answer with the number."}]}'
```

`max_tokens` caps the answer's length. The answer was `2.00`, which is correct, and the usage showed `"reasoning_tokens": 101`. Those reasoning tokens are billed as output tokens, so a team that turns thinking on spends its budget faster.

**What one call cost.** The gateway returns the internal cost of each call in the response headers. Add `-D -` to a curl command to print them:

```
x-litellm-response-cost: 0.00011614
x-litellm-response-cost-input: 9.45e-06
x-litellm-response-cost-output: 0.00010669
x-litellm-key-spend: 0.00011614
```

An app can log these numbers to see what each of its features costs.

**Errors the app must handle.** Every answer carries a three-digit **status code**:

| Code | Meaning | What the app does |
|---|---|---|
| 200 | OK | use the answer |
| 401 | the key is missing or wrong | stop; fix the key |
| 429, type `throttling_error` | the team sent too many requests or tokens this minute | wait until the time given in the message, then retry |
| 429, type `budget_exceeded` | the team's budget is used up | stop retrying; the team asks the platform team for more budget (step 10) |
| 000, printed by curl | no answer at all | the address is wrong, or the tunnel or network is down |

### Step 10. Prove the controls

**What this step does:** shows that the budget, the rate limit and the network rule really stop requests.

The status codes are the ones listed at the end of step 9.

**Budget.** The `intern-sandbox` team has $0.01 a month. This drill ran before step 11 set the final price. At the starting price of $1 per million output tokens, each answer of about 3,000 tokens cost about $0.003. Sending the same long request again and again gave:

```
usage 2718
usage 3085
usage 3088
usage 2851
HTTP 429 {"message": "Budget has been exceeded! Team=014cd1a5-... Current cost: 0.011762, Max budget: 0.01", "type": "budget_exceeded"}
```

The first four requests passed; each printed its output token count. The fifth got 429 `budget_exceeded`. This historical run reached $0.0118 against $0.01 because the gateway checks before admitting a request. Concurrent in-flight requests, accounting lag, and restarts can cause larger overshoot; test the intended load and failure modes.

**A team asks for more budget.** The platform team raises it with the **master key**, the gateway's admin key:

```bash
MASTER=$(kubectl -n gateway get secret litellm-env -o jsonpath='{.data.LITELLM_MASTER_KEY}' | base64 -d)
curl -s localhost:4000/team/list -H "Authorization: Bearer $MASTER"
curl -s localhost:4000/team/update -H "Authorization: Bearer $MASTER" -H "Content-Type: application/json" \
  -d '{"team_id":"PUT-THE-TEAM-ID-HERE","max_budget":1}'
```

- The master key grants administrative access. Retrieve it only in the instructor context and do not log its value.
- The second line lists the teams. Find `intern-sandbox` and copy its `team_id`.
- The third line sets that team's budget to $1. Replace `PUT-THE-TEAM-ID-HERE` with the ID first.

**Rate limit.** The same team may send 5 requests a minute. Seven short requests in a row gave:

```
request 1: HTTP 200
request 2: HTTP 200
request 3: HTTP 200
request 4: HTTP 200
request 5: HTTP 200
request 6: HTTP 429
request 7: HTTP 429
{"error":{"message":"Rate limit exceeded for team: 014cd1a5-... Limit type: requests. Current limit: 5, Remaining: 0. Limit resets at: 2026-10-14 15:14:42 UTC","type":"throttling_error","code":"429"}}
```

The error says when the limit resets, so a well-built app waits until then and tries again.

**Network rule.** An app that skips the gateway and calls vLLM directly would skip its budget too. Try it from the `default` namespace, where any team could run a pod, and from the `gateway` namespace:

```bash
kubectl -n default run nettest --rm -i --restart=Never --image=curlimages/curl:8.16.0 -- \
  curl -s -m 10 -o /dev/null -w "HTTP %{http_code}\n" http://vllm.llm.svc.cluster.local:8000/v1/models
kubectl -n gateway run nettest --rm -i --restart=Never --image=curlimages/curl:8.16.0 -- \
  curl -s -m 10 -o /dev/null -w "HTTP %{http_code}\n" http://vllm.llm.svc.cluster.local:8000/v1/models
```

These probes distinguish network isolation from backend authentication. A timeout alone can also indicate a broken path; compare it with the permitted-namespace probe and endpoint readiness.

| From | Result | Meaning |
|---|---|---|
| `default` | `HTTP 000` after 10 seconds | the NetworkPolicy blocked the connection |
| `gateway` | `HTTP 401` | the network let it through, but vLLM still demands its own key |

Two locks, so one mistake is not enough to bypass the budgets.

**A wrong key** sent to the gateway gets `HTTP 401`.

### Step 11. Measure throughput and set the internal price

**What this step does:** measures how much work the two GPUs can do, then works out the internal price per token from that and the GPU bill.

**Throughput** is how many tokens the GPUs produce per second, across all users together. The more users at once (**concurrency**), the more tokens per second, but each user waits longer.

**Measure.** vLLM includes a load-testing tool, `vllm bench serve`. It sends many requests at once and measures the results. You run it inside a vLLM pod, so it uses the cluster's network. It goes through the gateway with the load-test team's key, so it measures the full path.

On Windows, Git Bash changes any word that starts with `/` into a Windows folder path, which breaks `/models/...`. The `export MSYS_NO_PATHCONV=1` line turns that off for this terminal. On macOS and Linux the line does nothing.

```bash
source build/keys.env
export MSYS_NO_PATHCONV=1
POD=$(kubectl -n llm get pods -l app.kubernetes.io/name=vllm -o jsonpath='{.items[0].metadata.name}')
kubectl -n llm exec $POD -c vllm -- env OPENAI_API_KEY=$LOADTEST_KEY vllm bench serve \
  --backend openai-chat --base-url http://litellm.gateway.svc.cluster.local:4000 \
  --endpoint /v1/chat/completions --model astra --tokenizer /models/qwen3.8-27b-fp8/v1 \
  --dataset-name random --random-input-len 1000 --random-output-len 300 \
  --num-prompts 400 --max-concurrency 64
```

| Part | Meaning |
|---|---|
| `POD=$(...)` | finds the name of one vLLM pod and stores it in the variable `POD` |
| `kubectl exec $POD -c vllm --` | runs the rest of the line inside that pod's vLLM container |
| `--base-url http://litellm.gateway.svc.cluster.local:4000` | sends the requests to the gateway's Service |
| `--tokenizer /models/...` | where the tool finds the model's token list, so it can count tokens |
| `--random-input-len 1000 --random-output-len 300` | each request sends 1,000 tokens and asks for 300 back |
| `--num-prompts 400 --max-concurrency 64` | 400 requests in total, at most 64 at the same time |

The results are times and rates. Four terms explain them:

- **Time to first token**: how long a user waits before the first word appears. In chat, this is what feels "slow".
- **Median**: half of the requests were faster than this, half slower.
- **p95** and **p99**: 95 (or 99) requests out of 100 were faster than this. They show what the unluckiest users see.
- **ms**: milliseconds, thousandths of a second.

Results from the two replicas, at three levels of concurrency, plus one test straight to vLLM:

| Users at once | Output tokens per second | All tokens per second | Median time to first token | p99 time to first token | Failed requests |
|---|---|---|---|---|---|
| 1, through the gateway | 23.4 | not recorded | 0.48 s | not recorded | 0 of 20 |
| 1, straight to vLLM | 24.6 | not recorded | 0.46 s | not recorded | 0 of 20 |
| 16 | 276.6 | 1,220.7 | 2.98 s | 3.47 s | 0 of 200 |
| 64 | 584.3 | 2,570.5 | 3.89 s | 22.43 s | 0 of 400 |

Three things follow from the table:

- The gateway adds about 21 ms before the first word (0.48 s against 0.46 s). This is the measured overhead for that test, not a load-independent latency guarantee.
- At 64 users at once, the GPUs produce the most tokens, but one user in a hundred waits 22 seconds for the first word. That is too slow for chat.
- At 16 users at once, 99 users in 100 see the first word within 3.5 seconds.

**Price.** The design runs two g6e.xlarge machines. The price needs five numbers:

| Number | Value | Where it comes from |
|---|---|---|
| GPU cost per hour | 2 x ($1.861 + $0.14516) = **$4.012** | AWS Pricing API: the machine plus the Auto Mode fee, for two machines |
| Output tokens per second at full load | 584.3 | the benchmark at 64 users |
| Input tokens per second at full load | 2,570.5 - 584.3 = 1,986.2 | all tokens minus output tokens, same benchmark |
| How busy the GPUs are on average | 50% | an assumption. After a month, replace it with the real number from Grafana |
| Input token price compared with output | one fifth | reading the question costs the GPU much less work than writing the answer |

The idea: in one hour, at 50% busy, the GPUs handle a known number of tokens. Set the price so those tokens add up to the $4.012 bill. Count each input token as one fifth of an output token:

```
priced tokens per hour = 50% x 3,600 seconds x (584.3 + 1,986.2 / 5) = 1.767 million
output price           = $4.012 / 1.767 million = $2.27 per million output tokens
input price            = $2.27 / 5               = $0.45 per million input tokens
```

Put the prices into the gateway's ConfigMap and apply it. These numbers are already the defaults in `scripts/render.sh`; the command shows how to set your own:

```bash
INPUT_COST=0.00000045 OUTPUT_COST=0.00000227 bash scripts/render.sh
kubectl apply -f build/40-gateway.yaml
```

The prices are per single token: $2.27 per million is $0.00000227 per token. The gateway reads its ConfigMap only when it starts. To make it restart, raise the number in `config-version: "1"` in `k8s/40-gateway.yaml` (for example to `"2"`) before you run the two commands. The port-forward from step 7 stops when the gateway pods are replaced; start it again.

Check one call: 21 input tokens and 47 output tokens gave `x-litellm-response-cost: 0.00011614`. That is 21 x $0.00000045 + 47 x $0.00000227, as expected.

Running your own model pays off only when the GPUs stay busy. Idle GPUs still cost $4.012 an hour. Check the average use on the dashboard each month and set the price again.

### Step 12. Dashboard, spend report and alerts

**What this step does:** opens the dashboard the platform team watches, and prints the monthly spend report.

**The dashboard.**

```bash
kubectl apply -f k8s/70-dashboard.yaml
kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d; echo
kubectl -n monitoring port-forward svc/monitoring-grafana 3001:80
```

The first line adds the Astra dashboard. The second prints the Grafana password. The third opens a tunnel to Grafana.

Open http://localhost:3001, sign in as `admin` with that password, and open the dashboard **Astra: serving and team spend**.

![The Astra dashboard during the load test](images/grafana-astra.png)

The legend also shows `astra-chat`, a team that existed when the screenshot was taken and was removed later.

| Panel | What to look for |
|---|---|
| Requests running on the GPUs | how many requests each replica works on right now |
| Requests waiting for a GPU | above zero for minutes means users queue; add a replica or lower the load |
| GPU memory for conversations (KV cache) used | near 100% means the GPUs are full |
| Output tokens per second | the throughput of each replica |
| Time to first token, p95 | what users feel as "slow" |
| Spend, tokens and budget left by team | who uses Astra most, and who will run out of budget first |
| Failed requests by team | 429s from budgets and rate limits show up here |

In the picture, the load test is the spike around 10:20 (the screenshot shows local time): about 90 requests a minute from `platform-loadtest`, the KV cache near 95%, and requests waiting.

**The spend report** the platform team sends to teams each month:

```bash
bash scripts/spend-report.sh
```

```
team                       spent    budget    used  resets
platform-loadtest       0.311539     50.00    0.6%  2026-11-01
intern-sandbox          0.011801      1.00    1.2%  2026-11-01
hr-assistant            0.006326     50.00    0.0%  2026-11-01
support-bot             0.003937    150.00    0.0%  2026-11-01
```

`spent` is in internal dollars, `used` is the share of the budget spent, and `resets` is when the budget starts again. `platform-loadtest` leads because the load test ran before step 11 set the price, at the starting price in the script.

**Alerts.** `k8s/30-vllm.yaml` defines four alert rules; connect an Alertmanager receiver separately if notifications are required:

- fewer than 2 replicas for 10 minutes: one more failure and Astra is down,
- more than 10 requests waiting for 5 minutes: users queue,
- p95 time to first token above 5 seconds for 10 minutes: Astra feels slow,
- KV cache above 95% for 10 minutes: the GPUs are full.

### Step 13. What went wrong during the build

**What this step does:** lists every problem the test build hit, so you recognise them. The files in this folder already contain all the fixes.

| What you see | What it means | Fix |
|---|---|---|
| The model loader prints `Ignoring --include since filenames have been explicitly set`, and the bucket has no `.safetensors` files | the download command took only the first file pattern; it read the others as file names and skipped the weights | one `--include` per pattern, and a check that weights exist before `_PROMOTED` is written |
| vLLM pods stay `Pending`; events show `InsufficientInstanceCapacity` | AWS has no free GPU machines of that size in that zone | allow more sizes and zones in the NodePool; in a company, reserve capacity |
| The init container `fetch-model` shows `OOMKilled` | Page-cache memory was charged to the container while it wrote 29 GiB, exceeding its 2 GiB limit | raise the memory limit to 8 GiB |
| `ValueError: max_num_seqs (256) exceeds available Mamba cache blocks (189)` | Qwen3.8 uses two kinds of layers. One kind (linear attention, also called Mamba) needs one fixed memory block per request in progress. Only 189 blocks fit, and vLLM's default is 256 requests at once | `--max-num-seqs 128` |
| `ValueError: VLLM_PORT 'tcp://172.20.208.246:8000' appears to be a URI` | for a Service named `vllm`, Kubernetes adds settings named `VLLM_...` to every pod. vLLM reads `VLLM_PORT` as its own setting and fails | `enableServiceLinks: false` in the pod |
| A fixed vLLM manifest never takes effect | `maxUnavailable: 0` keeps the broken replicas until a new one is ready, but the new one needs a fourth GPU and the limit is 3 | when nothing is serving yet anyway, allow a full replacement once (below) |
| The gateway's `/metrics` page returns 401 | the gateway protects its numbers with a key | the PodMonitor sends the master key |
| `C:/Program Files/Git/models/...` appears in a `kubectl exec` error | Git Bash on Windows changed `/models/...` into a Windows path | `export MSYS_NO_PATHCONV=1` |
| Terraform: `The CIDR '10.0.48.0/20' conflicts with another subnet` | the fourth private subnet's address range overlapped the public subnets' range | public subnets start at 10.0.240.0 |
| EKS: `subnets should belong to the exact set of AZs ... in which subnets were provided during cluster creation` | the control plane's zones are fixed when the cluster is created | `control_plane_subnet_ids` keeps the control plane in the first three zones |

**Replacing broken model servers when nothing is serving.** Each version of a Deployment is kept in a **ReplicaSet**, the object that holds the replica count for that version. A normal change keeps the old ReplicaSet's replicas until the new ones are ready. When the old replicas are crashing anyway, allow a full replacement once, then put the safe setting back:

```bash
kubectl -n llm patch deploy vllm -p '{"spec":{"strategy":{"rollingUpdate":{"maxUnavailable":2}}}}'
kubectl -n llm get rs -w
kubectl -n llm patch deploy vllm -p '{"spec":{"strategy":{"rollingUpdate":{"maxUnavailable":0}}}}'
```

Stop watching once every old ReplicaSet has zero current replicas, then restore maxUnavailable to zero. This recovery deliberately permits a full outage and applies only when the serving replicas are already unusable.

**Drift.** When you change the NodePool's rules, machines that no longer match are called **drifted**. Auto Mode replaces them: it starts a new machine first, then empties the old one (**drains** it), and the pods move. When the cost cap removed g6e.8xlarge from the allowed sizes:

| Time (UTC) | What happened |
|---|---|
| 15:39:54 | the new NodePool is applied |
| 15:40 to 15:47 | attempts to start a replacement fail with `InsufficientCapacityError`; the old machine stays, both replicas keep serving |
| 15:47:44 | a g6e.2xlarge starts; the old machine is drained and its replica moves |
| 15:57:29 | the moved replica is ready again |

For 9 minutes, one replica served alone, because a model server needs that long to copy its weights and start. The PodDisruptionBudget allowed it, since `minAvailable: 1` still held. Make changes that replace GPU machines outside busy hours.

Auto Mode also removes machines that sit empty for 10 minutes. This is called **consolidation**. During the build it removed an empty g6e.16xlarge this way.

### Step 14. Tear it down

**Terraform route only:** remove Kubernetes-created resources, then destroy the reviewed Terraform state. Console-owned builds must follow the [Console cleanup](manual-infrastructure-guide.md#cleanup-for-the-console-route).

Delete what the cluster created on its own first: Prometheus's disk and the GPU machines. Terraform did not create those, so it does not know about them. Then Terraform deletes everything it built.

```bash
helm uninstall monitoring -n monitoring
kubectl delete pvc --all -n monitoring
kubectl delete -f build/30-vllm.yaml
kubectl delete -f build/10-gpu-nodepool.yaml
kubectl get nodes -L node.kubernetes.io/instance-type
cd terraform
terraform destroy
```

The source StorageClass uses Delete reclaim policy; verify the actual EBS volume is removed after deleting its PVC. Wait until no `g6e` machine is listed before you run `terraform destroy`. Terraform prints its plan and asks you to type `yes`. Afterwards, check the EC2 page of the AWS console for any running machines or disks (**EBS volumes**) left with your cluster's name.

Real result on the test build. The commands before `terraform destroy` took 6 minutes 47 seconds in total. Then:

```
Destroy complete! Resources: 82 destroyed.
real	6m29.674s
```

Afterwards a check with the AWS CLI found no machines, disks, load balancers or NAT gateways from the cluster. The EKS cluster, the RDS database, the S3 bucket and the secret were gone.

## Cost

Historical prices retained from the original 14 October 2026 build, region `us-east-1`, on-demand. Refresh [EC2 pricing](https://aws.amazon.com/ec2/pricing/on-demand/) and [EKS/Auto Mode pricing](https://aws.amazon.com/eks/pricing/) before budgeting. This table is not a current quote or complete bill.

| Item | Per hour |
|---|---|
| 2 x g6e.xlarge GPU machines ($1.861 each) | $3.722 |
| EKS Auto Mode fee on the GPU machines ($0.14516 each) | $0.290 |
| 3 x c6a.large machines for the gateway, Redis and monitoring, as measured during the build ($0.0765 plus $0.00918 fee each) | $0.257 |
| EKS cluster (the control plane) | $0.100 |
| NAT gateway, plus $0.045 per GB passing through it | $0.045 |
| RDS PostgreSQL, size db.t4g.small, one zone | $0.032 |
| **Total** | **about $4.45** |

Not in the table: disks, S3 storage for 29 GiB of weights, and data through the NAT gateway. In the test build the GPU machines were a g6e.2xlarge and a g6e.8xlarge, because of the GPU shortage in step 4. That brought the total to about $7.70 an hour.

The test build took 1 hour 34 minutes from `terraform apply` to the first answer, including the GPU wait and the fixes in step 13. The measured steps alone add up to 36 to 43 minutes: Terraform 17, model promotion 9, monitoring 2, model servers 8 to 15.

## Lab shortcuts and their production versions

Production requirements must be selected against the workload and SLOs. These lab shortcuts identify work that remains before adopting this architecture for a service people rely on:

| In this lab | In a company |
|---|---|
| port-forward from a laptop | an internal **load balancer** (one address that spreads traffic over the replicas) with HTTPS encryption and a company web address, reachable only from the company's network |
| `scripts/create-secrets.sh` copies the secrets once | the **External Secrets Operator** keeps them in sync with Secrets Manager |
| commands typed by hand | **Argo CD** applies the `k8s/` folder from Git; every change is a reviewed **pull request**, which is also the record of who changed what |
| always 2 replicas | **KEDA** or **HPA** (tools that add replicas automatically) add replicas when requests wait, up to the NodePool's GPU limit |
| one NAT gateway, database in one zone | one NAT gateway per zone, a database copy in a second zone (Multi-AZ), deletion protection |
| Redis inside the cluster | Amazon ElastiCache, Redis run by AWS |
| on-demand GPUs, when AWS has them | Capacity Reservations or Capacity Blocks for the GPUs |
| one internal model | the gateway can also list direct-provider or cloud-managed models, after configuring their credentials, data controls, and accounting |
| Terraform state on the laptop | state in an S3 bucket with locking, so two people cannot change it at once (the commented block in `terraform/versions.tf`) |

## What I can explain this week

- How direct-provider APIs, cloud-managed model access, and self-hosting differ, and how a gateway can expose more than one route.
- What an AI engineer needs to call Astra: base URL, key, model name, and the errors to handle.
- Why each replica needs its own weights/cache, and how to verify the intended zone placement.
- Why a company runs its own model, and why it still needs budgets when nobody bills per token.
- The path of one request: team key, budget check, rate limit, gateway, vLLM, GPU, spend record.
- What EKS Auto Mode does for GPU machines, and what a NodeClass and a NodePool decide.
- Why the weights go through an S3 bucket with a pinned commit and a `_PROMOTED` file.
- What the KV cache is, and why `--max-num-seqs` had to be lowered for this model.
- How the internal price per token was worked out from the GPU bill and a measured load test.
- What happens when AWS runs out of GPUs, and the options: more sizes, more zones, reserved capacity.
- Why the network rule matters even though vLLM has its own key.
- The difference between showback and chargeback.

## Glossary

Lab-specific inference and operational terms for review.

| Term | Meaning in Astra |
|---|---|
| Weights / checkpoint | Learned model parameters plus configuration/tokenizer artifacts, pinned to an exact revision. |
| Prefill / decoding | Processing the input context, then generating output tokens progressively. |
| GPU VRAM / host RAM | Separate memory budgets; GPU requests do not replace ordinary pod memory limits. |
| KV cache | Attention state for active sequences; context and concurrency compete for its capacity. |
| Quantization | Lower-precision representation that must be evaluated for quality, memory, and kernel compatibility. |
| Batching | Scheduling multiple requests through model execution to improve accelerator utilization. |
| Reasoning effort | Model/endpoint-specific control affecting reasoning work, latency, and token cost; not interchangeable across models. |
| Tool calling | The model emits a tool request; the application validates and executes the tool. |
| Structured output | Output constrained to a declared schema; verify both schema validity and semantic correctness. |
| Time to first token | Delay until the first streamed output token; measure percentiles under representative load. |
| Throughput | Successful requests or tokens per second at a specified workload and latency target. |
| Promotion marker | `_PROMOTED` signals completed upload, not a signature or integrity verification. |
| Showback / chargeback | Reporting internal allocation of costs / transferring those costs to team budgets. |
| Pod Identity / team API key | AWS workload authorization / inference-client authorization; distinct trust boundaries. |
| NodeClass / NodePool | AWS node configuration / scheduling and capacity policy for Auto Mode. |
| Gateway / serving engine | Team access, routing, and accounting / actual model execution and cache management. |
