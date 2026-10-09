# b.ai Custom Provider in 9Router

## Setup (2026-07-06)

b.ai was added as a custom provider node in 9Router.

### Node Details
- **Name**: `b.ai`
- **Prefix**: `bai`
- **Type**: `openai-compatible`
- **API Type**: `chat`
- **Base URL**: `https://api.b.ai/v1`
- **Node ID**: `openai-compatible-chat-fa24d9d0-a96b-407f-9d52-33b5d9c5ce35`

### Available Models
- GPT-5.5, GPT-5.4, GPT-5.4-pro, GPT-5.4-mini, GPT-5.4-nano
- Claude Opus 4.8, Claude Fable 5, Claude Sonnet 5, Claude Haiku 4.5
- DeepSeek V4 Pro, DeepSeek V4 Flash
- Gemini 3.5 Flash, Gemini 3.1 Pro
- Kimi K2.5, GLM 5.2, MiniMax M3

### Keys Added
- **Session 1**: 1,912 keys (from bai_farmer.py output)
- **Session 2**: 200 keys (mimo-fresh200.txt — but these were MiMo keys, not b.ai)
- **Total b.ai keys**: 1,912

### How Keys Were Obtained
1. Ran `bai_farmer.py` with 100 funded Ethereum wallets
2. Each wallet claimed 1M credits via SIWE auth + Turnstile solving
3. Created API key per account via `/trpc/lambda/apiKey.createApiKey`
4. Output: `sk-xxx | wallet_address | user_id` format
5. Extracted API keys only, bulk added to 9Router

### Cost
- 2Captcha: ~$0.40 (2 solves per wallet × 100 wallets)
- Gas: 0 (wallets were pre-funded)
- Credits obtained: ~99M total (99 successful claims)
