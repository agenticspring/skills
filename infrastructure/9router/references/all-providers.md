# 9Router Full Provider List (as of v0.5.18)

Extracted from source code on 2026-07-06. Contains all supported providers.

## Free Providers (no auth)

| ID | Alias | Name | Models |
|----|-------|------|--------|
| opencode | oc | OpenCode Free | Dynamic (passthrough) |
| qoder | qd | Qoder | qmodel_latest |

## Free Tier Providers (free tier available)

| ID | Alias | Name | Notable Models |
|----|-------|------|----------------|
| byteplus | bpm | BytePlus ModelArk | Seed 2.0, Kimi K2, GLM 4.7 |
| cloudflare-ai | cf | Cloudflare | Llama 3.x, Mistral, DeepSeek R1, FLUX images |
| ollama | ollama | Ollama Cloud | GPT OSS 120B, Kimi K2.5, GLM 5 |
| openrouter | openrouter | OpenRouter | auto (routing), 27+ free models |
| vertex | vx | Vertex AI | Gemini 3.x, 2.5 Flash |

## OAuth Providers

| ID | Alias | Name | Notable Models |
|----|-------|------|----------------|
| antigravity | ag | Antigravity | Gemini 3.x, Claude 4.6, GPT-OSS |
| claude | cc | Claude Code | Claude 4.5/4.6/4.7/4.8/5 Opus/Sonnet/Haiku |
| cline | cl | Cline | Claude 4.6-4.7, GPT 5.3-5.4, Gemini 3.1 |
| clinepass | clinepass | ClinePass | GLM-5.2, Kimi K2.6-2.7, DeepSeek V4, MiMo V2.5 |
| codebuddy-cn | cbcn | CodeBuddy CN | GLM 5.x, MiniMax M3, Kimi K2.7 |
| codex | cx | OpenAI Codex | GPT 5.x, 5.1, 5.2 |
| gemini-cli | gc | Gemini CLI | Gemini 3 Flash, 2.5 Pro/Flash |
| github | gh | GitHub Copilot | GPT 5.x, Claude 4.5, Gemini 3, Grok Code |
| iflow | if | iFlow AI | Qwen3, Kimi K2, DeepSeek R1, MiniMax M2 |
| kiro | kr | Kiro AI | Claude Sonnet 5, 4.5, Haiku 4.5 |
| qwen | qw | Qwen Code | Qwen3 Coder Plus/Flash |
| xai | xai | xAI (Grok) | Grok 4, 4 Fast, 3, Code Fast |

## API Key Providers

| ID | Alias | Name | Notable Models |
|----|-------|------|----------------|
| alicode-intl | alicode-intl | Alibaba Intl | Qwen3.5, Kimi K2.5, GLM 5, MiniMax M2.5 |
| alicode | alicode | Alibaba | Same as above + Qwen3 Max |
| anthropic | anthropic | Anthropic | Claude Sonnet 4, Opus 4, 3.5 Sonnet |
| assemblyai | aai | AssemblyAI | Universal 3 Pro, Universal 2 (STT) |
| azure | azure | Azure OpenAI | Custom deployment |
| black-forest-labs | bfl | Black Forest Labs | FLUX Pro 1.1, Dev, Kontext (images) |
| blackbox | bb | Blackbox AI | Claude Fable 5, GPT 5.4-5.5, DeepSeek V4 |
| brave-search | brave | Brave Search | Web/News search |
| cerebras | cerebras | Cerebras | GPT OSS 120B, GLM 4.7, Llama 3.3 |
| chutes | ch | Chutes AI | OpenAI-compatible |
| deepseek | deepseek | DeepSeek | DeepSeek V4 Pro/Flash, R1 |
| glm | glm | GLM Coding | GLM 5.2, 5.1, 4.7 |
| groq | groq | Groq | Llama, Mixtral models |
| kimi | kimi | Kimi Coding | kimi-latest |
| minimax | minimax | Minimax Coding | MiniMax-M2.5, M3 |
| nanobanana | nanobanana | Nanobanana | Various |
| nvidia | nvidia | NVIDIA | Nemotron models |
| ollama-local | ollama-local | Ollama Local | Local models |
| openai | openai | OpenAI | GPT 5.x, 4o, o3/o4, DALL-E, Whisper, TTS |
| opencode-go | ocg | OpenCode Go | GLM 5.x, Kimi K2.6-2.7, DeepSeek V4, MiMo, MiniMax |
| openrouter | openrouter | OpenRouter | 100+ models, auto routing |
| perplexity | pplx | Perplexity | Sonar Pro |
| siliconflow | siliconflow | SiliconFlow | DeepSeek V4, Qwen 3.5, GLM 5, Kimi K2.5-2.6 |
| together | together | Together AI | Llama 3.3, DeepSeek R1, Qwen3 235B |
| venice | vn | Venice AI | Venice Uncensored, GLM-5, DeepSeek V4 |
| vercel-ai-gateway | vercel | Vercel AI Gateway | All models via Vercel |
| volcengine-ark | ark | Volcengine Ark | Seed 2.0, DeepSeek V4, GLM 5.1 |
| xiaomi-mimo | mimo | Xiaomi MiMo | MiMo V2.5 Pro, V2.5, V2 Omni, Flash |
| xiaomi-tokenplan | xmtp | Xiaomi MiMo (Token Plan) | MiMo V2.5 Pro, V2 Pro, V2 Omni, TTS models |

## Web Cookie Providers

| ID | Alias | Name | Notable Models |
|----|-------|------|----------------|
| grok-web | grok-web | Grok Web | Grok 4 (via SSO cookie) |
| perplexity-web | pw | Perplexity Web | Auto, Sonar, GPT 5.4, Gemini 3.1, Claude 4.6 |

## Service-Specific (STT/TTS/Image/Search)

| ID | Name | Service |
|----|------|---------|
| aws-polly | AWS Polly | TTS |
| cartesia | Cartesia | TTS |
| deepgram | Deepgram | STT |
| playht | PlayHT | TTS |
| recraft | Recraft | Image |
| runwayml | Runway ML | Image/Video |
| sdwebui | SD WebUI | Image (local) |
| searchapi | SearchAPI | Web Search |
| searxng | SearXNG | Web Search (local) |
| serper | Serper | Web Search |
| stability-ai | Stability AI | Image |
| tavily | Tavily | Web Search/Fetch |
| topaz | Topaz | Image |
| tortoise | Tortoise TTS | TTS (local) |
| voyage-ai | Voyage AI | Embeddings |
| youcom | You.com | Web Search |
