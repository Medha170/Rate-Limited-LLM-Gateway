# Guardrailed LLM Gateway

A robust, production-ready FastAPI gateway sitting in front of LLM communications. Designed to handle high-concurrency budgets, external dependency failures, and strict execution latency windows gracefully.

## 🛠️ Architecture Overview

The gateway acts as an intermediate circuit breaker between client requests and downstream LLM orchestration layers:
1. **FastAPI Web Infrastructure**: Asynchronous routing handling SSE (Server-Sent Events).
2. **Atomic Rate Limiter**: Highly concurrent Redis backend implementing a daily token quota per user.
3. **Fail-Open Fault Tolerance**: Gracefully bypasses rate limiting during database connectivity loss.
4. **Resilient AI Execution Window**: Hard timeout boundaries guarding LLM connection lags.

---

## ⚖️ Decisions & Trade-offs

### 1. Atomic `INCR` over `GET-SET` Transactions
* **Decision**: Implemented an atomic Redis `INCR` operation wrapped with a baseline expiration window.
* **Trade-off**: While a sliding-window log provides highly accurate sub-second throttling, it incurs high memory overhead ($O(N)$ elements saved per request). The atomic `INCR` provides an $O(1)$ low-latency solution that perfectly satisfies daily threshold compliance under immediate concurrent bursts.

### 2. Industry-Standard Token Heuristic Estimation
* **Decision**: Leveraged a character/word parsing dynamic scaling heuristic ($1 \text{ word} \approx 1.3 \text{ tokens}$) within the active event stream loop.
* **Trade-off**: Running a localized heavy tokenizer script (like TikToken) inside an asynchronous streaming generator loop adds block cycles to the event loop. Utilizing a heuristic provides a lightweight, highly responsive stream processing structure while guaranteeing structured telemetry delivery.

---

## ⚠️ 3 Failure Modes I Am Most Worried About

### 1. The Redis Expiry Race Condition (The Ghost Key Problem)
* **Scenario**: If the server crashes or the network drops *immediately* after the `INCR` command completes but *before* the `EXPIRE` command fires, the user counter key gets orphaned with a TTL of -1 (lives forever). Over time, a user will permanently hit a 429 lockout state once their cap is exhausted.
* **Mitigation**: In a high-scale production layer, this should be refactored into an atomic Lua script executed natively on the Redis engine.

### 2. Deep Network Lags Post-Connection Handshake
* **Scenario**: Our 5.0-second `asyncio.wait_for` timeout acts as a guard against initial model connection freezes. However, if the downstream engine provides a successful connection handshake but experiences severe mid-sentence packet drops while transmitting chunks, the streaming response will experience slow-drip degradation.
* **Mitigation**: Implement a dynamic "inter-token chunk timeout tracker" inside the stream loop to drop connections if successive packet delta exceeds 1,500ms.

### 3. Upstream Provider Memory Exhaustion under Concurrency
* **Scenario**: When handling immense user surges concurrently, the outbound connection pool to the underlying LLM inference service could saturate, leading to widespread connection timeouts.
* **Mitigation**: Establish a request queue and a Backpressure Management system using a bounded semaphore structure to limit maximum simultaneous downstream LLM calls.

---

## 🚀 If Given 10x More Time...

If given the space to scale this into an enterprise-grade microservice, I would implement:
1. **Sliding Window Token Bucket Algorithm**: Moving away from hard fixed-daily resets to smooth out natural user traffic spikes throughout the day.
2. **Full Circuit Breaker Topology**: Integrating a standard structural wrapper (like `resilience4j` or a Python equivalent) so that if the LLM drops out repeatedly, the gateway automatically cuts traffic early to save compute resources before even hitting the 5-second timeout.
3. **Distributed Structured Telemetry**: Emitting telemetry logs straight into an open-source observability framework like Prometheus/Grafana or OpenTelemetry rather than relying solely on terminal output logs.