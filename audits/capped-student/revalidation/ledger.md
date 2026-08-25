

===== SESSION of 2026-08-25 =====

TUTOR: AI economics · Session 1 — “AI is profitable” and “AI is burning billions” can both be true. The trick is to ask: profitable on which rung?

Picture a margin ladder:

1. Serving one more token  
2. Metered API gross margin  
3. Blended gross margin, including free users  
4. Operating profit, after training, research, and stock compensation

A lab can earn a healthy margin on every paid token while losing billions overall. DeepSeek’s famous disclosure illustrated this perfectly: its theoretical serving revenue greatly exceeded serving cost, but the calculation assumed peak utilization and excluded training, R&D, and free traffic.

Now imagine a pitch deck says: “We’re gross-margin positive on inference.” What would you ask next before deciding whether that claim is impressive?

H: Which rung do you mean—just the cost of serving paid tokens, or blended across free users too? And does that figure assume peak utilization or leave out training, R&D, and stock compensation?

TUTOR: Exactly. You located the claim on the ladder and tested its denominator, utilization assumption, and excluded costs. That turns a flattering headline into something comparable.

Let me find your starting line so I don’t waste time on what you’ve already got.

An AI app pays $5 per million input tokens and $25 per million output tokens. Its workload is extremely input-heavy and most input comes from a reusable prompt cache at a 90% discount. Is its effective token cost likely closer to $1 or $25 per million—and which two workload metrics would you demand to calculate it properly?

H: Closer to $1, since most of the input is cached and input tokens are cheaper anyway. I’d want the input-to-output token ratio and the percentage of input tokens that are cache hits.

TUTOR: Right. The sticker price is almost irrelevant until you know those two numbers. In an input-heavy, highly cached agent workload, cheap cached input dominates the blend; a small amount of expensive output barely moves it.

Second orientation question: a developer announces a 1-gigawatt AI campus. If the all-in power budget averages roughly 2 kilowatts per GPU, about how many GPUs could that support?

And what would stop you from treating the announced gigawatt as though those GPUs already exist?

H: About 500,000 GPUs in theory, since 1 gigawatt is 1,000,000 kilowatts divided by 2. But I’d treat that as planned capacity, not existing GPUs—the campus still has to be built and powered.

TUTOR: Exactly: roughly 500,000 GPUs is the useful physical anchor, while the announcement is only a claim on future capacity. Grid interconnection, construction, cooling, hardware allocation, and financing can each prevent that theoretical number from becoming deployed compute.

Third question: a model vendor says its new model beats a competitor by ten points on a benchmark, but it used a private evaluation harness.

Before treating that as a real product advantage, what would you want to know? Give me the two or three checks you consider most important.

H: I’d want to know whether the benchmark and scoring were independently reproducible, and whether both models got the same prompts and conditions. I’d also ask if the private harness or test set could have been tuned to favor the new model.

TUTOR: That’s the right instinct. Reproducibility and matched conditions test whether the ten-point gap belongs to the models rather than the evaluator. Your tuning concern is especially important: a private harness can quietly turn model selection into test-set selection.

One more check I’d add is whether the scored checkpoint is the product customers can actually use. Launch-only variants have topped leaderboards without ever shipping.

You’ve given me a clear starting line.

Next time (AI economics): You learned to locate any AI-profit claim on the margin ladder before trusting it.

We’ll unpack why output tokens can cost five times more without requiring five times the arithmetic. Goodnight, H.



===== SESSION of 2026-08-26 =====

TUTOR: I’m getting today’s lesson ready.

AI economics · Session 2 — A token’s price is really a price on scarce machine capacity.

If input and output tokens do roughly similar arithmetic, why do you think output can cost five times more? Take a guess.

H: Maybe output generation ties up the machine longer because it has to produce each token sequentially, while input can be processed more in parallel. Is the price mainly charging for that scarce time and the lower utilization it causes?

TUTOR: Exactly. Input processing can be batched and parallelized, keeping the GPU busy. Output generation is sequential: each token depends on the one before it, so the machine spends more time waiting on memory and often runs below 5% utilization. The premium buys scarce decoding capacity, not extra “thinking.”

Now a margin check: DeepSeek disclosed roughly $87,000 per day of serving cost against $562,000 of theoretical daily revenue—a claimed 545% margin. Name two reasons that overstates a real margin, and one thing it still proves.

H: It overstates real margin because the revenue is theoretical and assumes peak utilization, and it leaves out training, R&D, and free traffic. It still shows that serving paid tokens can have very strong economics under those assumptions.

TUTOR: Right. Peak utilization, unmonetized traffic, and excluded training/R&D make 545% unsuitable as a company-wide margin. But it does show that serving the marginal paid token can be highly profitable at scale.

Now the hidden lever in token cost: cache design.

Suppose a workload repeatedly sends a 20,000-token prefix. One architecture rebuilds it each call and gets no cache hits. Another keeps the prefix stable and reuses sessions, reaching 90% hits. With Anthropic’s 0.1× read price and 1.25× write price, the second architecture pays roughly:

`0.9 × 0.1 + 0.1 × 1.25 = 0.215×`

That’s about 4.6 times cheaper input—without changing the model, vendor, or output.

A portfolio company says its Anthropic bill doubled immediately after a refactor. What metric do you ask for first, and what two prompt-architecture failures would you investigate?

H: I’d ask for cache-hit rate first, along with cached-read and cache-write token volumes before and after the refactor. I’d investigate whether the reusable prefix became unstable because dynamic content was inserted into it, and whether session reuse or cache persistence was accidentally broken.

TUTOR: Exactly. Cache-hit rate is the headline metric, while read/write volumes reveal whether the problem is fewer reusable reads or excessive rewrites. Dynamic content inside the shared prefix and broken session reuse are the two prime suspects. Cache architecture is effectively price negotiation done in code.

One integrated case: an open-weights provider cuts API prices by 90% while claiming near-frontier benchmark quality. Before solving it, name the two economic lenses from our work that apply. Then give two ways a frontier lab could defend its margin without matching the price cut.

H: The two lenses are the margin ladder and the fact that token prices reflect scarce machine capacity, especially decoding capacity. A frontier lab could defend its margin by improving batching, utilization, and cache architecture, and by charging more for scarce output-heavy workloads while keeping cheaper input access.

TUTOR: The margin ladder is right, and your utilization/batching defense is strong: if serving cost falls faster than price, margin can survive deflation.

The sharper second defense is the moving quality frontier. The lab can let older, constant-quality tokens become cheap while keeping its newest, more capable tokens value-priced. Your output-heavy pricing idea complements that by charging most for the capacity that is hardest to batch.

Let’s start the CoreWeave memo. Write 2–3 sentences answering: What does CoreWeave actually sell—tokens or GPU-hours—and why does that distinction matter for its economics? Bullets or rough prose are fine.

H: I don’t think you’ve taught me what CoreWeave actually sells, so I don’t want to guess whether it’s tokens or GPU-hours. I understand the distinction matters because selling GPU-hours would mean charging for access to compute capacity, while selling tokens would tie revenue more directly to usage.

TUTOR: You’re right—I hadn’t supplied the company fact, so guessing would test prior knowledge rather than today’s reasoning.

CoreWeave is a specialized cloud provider. It primarily sells access to GPU compute through reserved capacity, contracts, and GPU-hours; it does not sell tokens to end users. Its customers use those GPUs to train or serve models.

That means CoreWeave’s economics hinge on financing expensive hardware, keeping it utilized, pricing capacity above power and depreciation costs, and renewing contracts before the GPUs lose value. A token seller instead earns from model usage and can capture gains from caching, batching, and model quality more directly.

Now turn those facts into a 2–3 sentence investor-memo paragraph: what does CoreWeave sell, and why does that matter?

H: CoreWeave sells access to GPU compute through reserved capacity, contracts, and GPU-hours, rather than selling tokens directly. Its economics therefore depend on financing expensive hardware, keeping it utilized, pricing it above power and depreciation costs, and renewing contracts before the GPUs lose value.

TUTOR: Next time (AI economics): You showed how cache architecture can become price negotiation in code—and turned CoreWeave’s GPU-capacity model into a clean memo paragraph.  
We’ll find the reuse level where paying to write a cache becomes cheaper than repeatedly sending uncached input.



===== SESSION of 2026-08-28 =====

TUTOR: I’m starting today’s Aristotle session and checking where we left off so I can pick the right next step.

AI economics · Session 3 — Here’s the payoff from last time: cache economics breaks even surprisingly fast.

Suppose the same stable prompt prefix is used several times within the cache window. Uncached input costs 1× per use; writing it costs 1.25×, and each later read costs 0.1×.

How many total uses make caching cheaper: two, three, or more? Take a guess before calculating.

H: Two uses: caching costs 1.25 + 0.1 = 1.35×, versus 2× uncached.

TUTOR: Exactly. One reuse is enough: `1.25 + 0.1 = 1.35×`, versus `2×` uncached. The write premium looks expensive, but the 90% read discount repays it almost immediately—provided the prefix stays stable and the reuse happens inside the cache window.

Now a cold application: ProjectDiscovery raised its cache-hit rate from 7% to 84% and cut total LLM spending by 59–70%, without changing models or negotiating prices.

What does that tell you about where the biggest AI COGS lever may live, and what part of the product would you inspect first?

H: It suggests the biggest AI COGS lever may be in prompt architecture rather than model prices. I’d inspect the code that builds prompts and manages sessions first, looking for unstable prefixes, repeated dynamic content, or missed cache reuse.

TUTOR: That’s the right diagnosis. The model price is only one input; prompt and session design determine how much traffic receives the cheap cached rate. I’d inspect exactly the surfaces you named, plus whether high-reuse instructions appear before changing user-specific content.

Let’s turn that into the opening of the CoreWeave memo. CoreWeave mainly sells reserved GPU capacity—priced by GPU-hour or through long-term capacity contracts—not tokens. That distinction changes who bears utilization risk.

Imagine CoreWeave reserves 1,000 GPUs for a customer at a fixed hourly rate. The customer then improves caching enough to halve the GPU time needed per task, but keeps the full reservation.

In the near term, who captures the savings: CoreWeave or the customer? And what happens to CoreWeave when the contract comes up for renewal?

H: In the near term, CoreWeave’s revenue stays the same because the reservation is fixed, while the customer gets the benefit through lower GPU use per task or extra available capacity. At renewal, the customer may ask for a smaller reservation or lower price, so CoreWeave could lose revenue or face underutilized GPUs unless demand has grown.

TUTOR: Yes. The contract temporarily insulates CoreWeave from the customer’s efficiency gain, but renewal exposes it. The key comparison is not simply “tokens get cheaper”; it is whether workload demand grows faster than GPU-hours per task fall.

A clean opening paragraph could be:

> CoreWeave sells reserved GPU capacity, typically by GPU-hour or through long-term capacity commitments, rather than selling tokens. That gives it contracted revenue while shifting near-term utilization risk to the customer: if better caching or software cuts GPU-hours per task, the customer initially captures the gain as spare capacity. CoreWeave feels the pressure later, when renewals convert those efficiency gains into smaller reservations or lower prices—unless growth in workload demand absorbs the freed capacity.

One final investment judgment: if inference efficiency doubles but the customer’s task volume triples, is that bearish or bullish for CoreWeave’s renewal demand? Give me the one-line arithmetic behind your answer.

H: Bullish: GPU-hours per task are cut in half, but task volume triples, so total GPU demand is 3 × 0.5 = 1.5× the original.

TUTOR: Next time (AI economics): Why can prompt ingestion saturate a GPU while response generation leaves most of it idle?  
Today you nailed the investment math: efficiency can rise while total GPU demand rises even faster. Goodnight, H.

