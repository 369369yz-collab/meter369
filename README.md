# 369 Meter — pay-per-call APIs for agents (x402)

Four pay-per-call APIs for agents, one rail: **x402** (v1, "exact" scheme,
USDC on **Base**), settling directly to the publisher's wallet. No accounts,
no API keys, no checkout — call a route, get an HTTP 402 with payment
requirements, pay, get the resource.

**Live gateway:** https://369yz.pythonanywhere.com/meter/
**Health (free):** https://369yz.pythonanywhere.com/meter/health
**PayTo (Base):** `0xA0A1ff293EF2FF051121674c8eAAd69570b25e6c`
**Facilitator:** payai-public · every 402 declares the Bazaar discovery extension.

## Services

| REST route | MCP tool | Service | Price/call |
|---|---|---|---|
| `POST /v1/text/analyze` | `text_analyze` | TextIntel — deterministic text analysis (counts, readability, script mix, keywords) | $0.01 |
| `POST /v1/hook/score` | `hook_score` | HookScore — gaming headline/hook scored 0–100 against the 369 team's hook rules | $0.01 |
| `POST /v1/translate/check` | `translate_check` | TranslationCheck — EN↔FA translation QA score 0–100 | $0.02 |
| `POST /v1/game/facts` | `game_facts` | GameFacts — live game metadata from RAWG (release, ratings, Metacritic, platforms, genres) | $0.03 |

## How to pay (x402)

```bash
# 1. Call without payment -> HTTP 402 + x402 payment requirements
curl -s -X POST https://369yz.pythonanywhere.com/meter/v1/text/analyze \
  -H 'Content-Type: application/json' -d '{"text":"your text"}'

# 2. Sign an EIP-3009 USDC authorization for the amount in
#    accepts[0].maxAmountRequired and retry with the X-PAYMENT header.
#    The resource is served only after the facilitator confirms settlement.
```

## MCP

`mcp_adapter.py` (this repo, stdlib-only Python) exposes the same four
services as MCP tools for directory discovery:

- **stdio:** `python3 mcp_adapter.py`
- **streamable HTTP:** mount `application` in any WSGI server (POST JSON-RPC).

`tools/list` and `initialize` are free. Because an MCP transport cannot
carry an `X-PAYMENT` header, `tools/call` performs the real gateway call
and returns the gateway's live **402 payment requirements** as an MCP error
result — it never serves an unpaid resource. Pay over the x402 rail on the
REST route above.

Directory manifests in this repo: `server.json` (Official MCP Registry,
name `io.github.369369yz-collab/meter369`), `glama.json` (Glama claim),
`openapi.json` (the REST API spec, prices verified against the live 402s).

## Also listed via

- **api.market** — the same REST API (`openapi.json`); api.market auto-generates an MCP endpoint for listed APIs.
- **PayAPI Market** — x402 directory (listed 2026-10-25; a $0.02 USDC canary payment from their verification has landed on-chain).

## License

MIT — see `LICENSE`. The gateway service itself is operated by VeritasWorks;
this repo publishes the adapter and the directory manifests.
