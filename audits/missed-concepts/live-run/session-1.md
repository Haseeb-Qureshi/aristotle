# Session 1 — 2026-10-22

**TUTOR:** AI economics · Session 34 — Last time, we left a useful test: does the model on a leaderboard match what customers can actually deploy? There’s a similar gap in compute. A GPU order alone doesn’t give a customer a working cluster.

Imagine a company has early access to GPUs and a powered, cooled site. What else would it need to turn that head start into a business a lender would finance? Take a guess.

**H:** Probably committed customers and a credible way to pay for the GPUs and site. The lender would want predictable cash coming in, not just equipment sitting there.

**TUTOR:** Yes—that predictable customer cash is the bridge.

That’s the basic neocloud business: secure GPUs, cooling and power ahead of others, then rent the usable capacity to customers. In the CoreWeave model, the company leases datacenter space and finances its GPU fleet against customer contracts.

Imagine a five-year **take-or-pay** contract: the customer commits to paying for reserved capacity even if it uses less. Matching that contract’s length to the fleet’s five-year accounting life gives lenders a repayment schedule. They still need to trust the customer’s ability to pay, and five years on the books doesn’t guarantee five years of competitive hardware.

Now change one clause: the customer can cancel with 90 days’ notice. The headline still says “five-year deal.” Why does that make it much harder to borrow against?

**H:** Because the five-year cash flow isn’t really committed if the customer can walk away after 90 days. The lender can’t count on that revenue to repay the GPUs over their useful life. Does the contract still help at all if the customer has to pay a cancellation fee?

**TUTOR:** Exactly—the lender needs committed cash over the repayment period.

A cancellation fee can help. Suppose $80 million of debt remains when the customer exits. A collectible $10 million fee leaves substantial exposure; a fee covering the remaining debt and shutdown costs offers much stronger protection. Its size, payment timing and enforceability matter. So does the customer’s ability to pay: a large fee from a bankrupt customer may recover little.

That protects financing. Durable profits also depend on what the neocloud delivers after GPUs become plentiful.

Customers pay for reliable clusters, fast networking and capable operations. One historical rating ladder ran Bronze → Silver → Gold → Platinum, with Platinum priced about 180% above the floor. That suggests service quality can command a premium, though the rating firm also consulted for the industry it rated.

There’s also a business choice: rent raw GPU-hours, or build software that serves models and sells tokens with performance guarantees. The course’s illustrative model puts payback around four years for raw rentals versus two for managed services. The latter requires software, talent and customer demand; adding a token price doesn’t create those capabilities.

For your CoreWeave memo: an investor calls it “a hardware leasing company with a premium valuation.” Which ideas we’ve discussed support that criticism, which support the premium, and what evidence would decide between them? A few bullets are enough.

**H:** The criticism is that raw GPU rentals may look like hardware leasing, and the five-year contracts don’t protect profits if GPUs become plentiful or customers can cancel. The premium case is that reliable clusters, fast networking, strong operations, or managed services with performance guarantees can command higher prices and faster payback. I’d want evidence on how much revenue comes from raw rentals versus managed services, whether customers renew and pay for those service advantages, and how cancellation protections hold up in practice. Does the rating ladder’s 180% premium have much weight given that the rating firm also consulted for the industry?

**TUTOR:** Your evidence list gets at the right question: do customers keep paying for advantages that survive easier GPU access? Add the value of getting scarce capacity sooner—that can justify a premium today, but fades as queues shorten.

One correction: GPU abundance alone doesn’t reduce payments under an enforceable, fixed-price take-or-pay contract with a solvent customer. It threatens renewal prices and the fleet’s value after the contract ends. Cancellation rights create a separate exposure during the contract.

The rating premium deserves some weight as a clue, but little as standalone proof. Consulting creates a potential conflict; it doesn’t establish that the rating is wrong. And a 180% price gap could reflect different hardware, contract terms or customers. I’d want comparable actual transaction prices, independent reliability measurements, and renewals showing customers willingly pay extra.

One last question, on serving costs:

Using a historical cache rate card, ordinary input costs **1×**, writing reusable input into a cache costs **1.25×**, and reading it again costs **0.1×**.

One workflow summarizes each document once. Another asks ten questions using the same unchanged document prefix, all before the cache expires.

Should the team pay to cache both workflows? Why?

**H:** I’d cache the second workflow: the one-time write costs 1.25×, but ten reads at 0.1× each cost 1× total, and the unchanged prefix keeps the cache useful. For the one-time summary, caching adds a write cost without any repeat reads to make it back. Could the cache still be worthwhile for a single use if it makes the response faster?

**TUTOR:** Yes—cache the repeated prefix. Small counting fix: for ten requests total, it’s one write plus nine reads: **1.25 + 0.9 = 2.15**, versus **10** without caching. Keeping the prefix stable makes its input bill about **4.6× lower**. That saving excludes output and any other input.

For a genuinely first-and-only use, creating the cache normally doesn’t speed that response: the prefix still needs processing. A cache warmed beforehand can reduce response time, and that speed may justify the cost—but include the earlier write in your calculation.

For comparison, the historical OpenAI example used automatic caching at **0.5×** for reads with no write premium. The incentive to reuse stable prefixes remains; the upfront cost differs.

Next time (AI economics): Today you identified what makes customer commitments financeable, and why service premiums need evidence.
We’ll ask: when can a higher benchmark score come from a better test-taking setup rather than a better model? Goodnight, H.

