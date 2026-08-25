

===== SESSION of 2026-08-25 =====

TUTOR: I’m using the Aristotle tutoring workflow to run today’s session and keep your
course progress in sync.

AI economics · Session 1 — We’ll start by finding the right level for you, so the course focuses on decisions you can’t already make confidently.

AI economics · Session 1 — Here’s the puzzle: an AI lab can lose billions overall while earning a fat gross profit on every paid API token it serves.

How can both be true? Give me your best guess.

H: Maybe each token is profitable, but the company has huge fixed costs like building and running the systems, so total expenses can still be higher than revenue. 


TUTOR: Exactly. The key is separating layers of the economics.

Imagine a lab earns $100 from paid API usage and spends $20 serving those tokens: that business has an 80% gross margin. But it might also spend $25 serving free users, $70 training the next model, and $30 on researchers and stock compensation. The paid token is profitable; the company as a whole still loses money.

So whenever someone says “AI margins are good” or “AI is unprofitable,” ask: do they mean paid API gross margin, blended gross margin including free users, or total operating profit?

Application: two labs have identical models, API prices, and serving costs. One sells mostly metered API usage; the other supports a huge free consumer product. Which should report the higher blended gross margin, and why?

H: The metered API lab should have the higher blended gross margin, because the other lab has lots of free users adding serving costs without revenue. I’m still a little unsure how stock compensation fits into the different margin layers.

TUTOR: That’s right: free traffic lowers blended gross margin because it adds serving cost without corresponding revenue.

Stock compensation usually sits below gross profit as an operating expense—for researchers, salespeople, and executives—so it can turn healthy gross profit into a large operating loss. A portion may enter cost of revenue if it pays employees directly involved in serving customers, but the central distinction remains: gross margin measures the delivered product; operating profit includes the broader company.

Now let me find your starting line so I don’t waste time on what you already know.

A product processes roughly 100 input tokens for every output token, and 90% of its input is served from a cache at one-tenth the normal input price. Should its blended token cost be closer to the expensive output-token price or the cheap cached-input price? Explain your reasoning.

H: I can’t tell from the information given because you haven’t said how the normal input price compares with the output price. There are many more input tokens, but most are cached and much cheaper, so I’d need those prices to know which one dominates.

TUTOR: You’re right—the question was under-specified. The missing input-to-output price ratio is essential.

Using a common 5× output premium, measure everything in normal-input-price units. The 100 input tokens cost:

\(90 \times 0.1 + 10 \times 1 = 19\)

The single output token costs 5, so input still dominates total spend. Across all 101 tokens, the blended price is about 0.24× the normal input price—much closer to the cached-input price than the output price. But with an extreme enough output premium, your answer could change. Your instinct to demand the missing price was exactly sound.

Next orientation question: one system reads a 100-page contract and emits a one-word classification. Another reads one sentence and generates a long report. Which workload should use the GPU more efficiently, and what physical difference between reading and generating drives that?

H: I don’t think you’ve taught me the physical difference between reading and generating yet, so I can’t confidently say which uses the GPU more efficiently. My guess is the long-report workload might be harder, but I’d need you to explain the mechanism.

TUTOR: Your guess is right. Reading the contract can be processed largely in parallel, keeping the GPU’s compute units busy. Generating the report is sequential: each new token depends on the previous tokens, so the GPU repeatedly moves the model’s weights through memory while doing relatively little computation. That makes long generation less efficient and helps explain why output tokens cost more.

You hadn’t been given that mechanism, so this establishes your starting point rather than counting as a miss.

Last orientation question: a model vendor says its new model beats a competitor by eight points on an industry benchmark. Before treating that as commercially meaningful, what would you investigate? Name as many checks as occur to you.

H: I’d check what the eight points means, whether both models were tested on the exact same tasks and data, and how large and reliable the test was. I’d also ask whether the benchmark reflects real customer workloads, whether the result can be reproduced, and whether the new model’s price or serving cost makes the improvement worthwhile.

TUTOR: That’s a strong diligence answer. You covered comparability, sample reliability, reproducibility, deployment relevance, and economics. I’d add three checks: who funded or constructed the benchmark, whether both scores used the same model checkpoint and testing scaffold, and whether the benchmark is already saturated.

Next time (AI economics): You separated profitable token serving from company-wide losses—and showed good instincts for demanding missing assumptions.  
How can prompt architecture cut the bill for the same model several-fold without any vendor negotiation? Goodnight.



===== SESSION of 2026-08-26 =====

TUTOR: I’m using the Aristotle tutoring skill for this scheduled session. I’ll load its rules and the course state, then speak only in the learner-facing format it requires.

AI economics · Session 2 — Same model, same work, radically different bill.

Imagine two agents repeatedly use the same long instructions. One rebuilds and slightly changes them on every call; the other keeps them identical and reuses the session.

How much cheaper could the second agent’s input bill be—and what do you think creates the difference?

H: Maybe several-fold cheaper, because the identical instructions can be cached and charged at the much lower cached-input price. The exact savings depends on how much of the total input stays identical and what the normal input price is.

TUTOR: Exactly. On Anthropic, writing a five-minute cache costs 1.25× normal input, but reading it costs only 0.1×.

If 90% of a stable prefix becomes cache reads, its blended cost is roughly:

0.9 × 0.1 + 0.1 × 1.25 = 0.215×

So that portion of the input bill falls about 4.6×. The real lever is architectural: stable prefixes and session reuse create cache hits; reordered prompts, changing tool definitions, and rebuilt sessions destroy them.

Now a cold case: a lab cuts its frontier API price by 50%, reduces serving cost per token by 80%, and simultaneously doubles its free consumer traffic. Could its API gross margin rise while its company-wide gross margin falls? Walk me through why or why not.

H: Yes, that could happen. The API gross margin could rise because serving costs fall much more than the price, while doubling free traffic adds a lot of serving cost without revenue and drags down the company-wide gross margin.

TUTOR: Correct. You separated the two rungs cleanly: metered API economics improve because unit cost falls faster than price, while unreimbursed consumer inference can pull blended gross margin down. A single “gross margin” number is meaningless until we locate it on the ladder.

Second cold case: two enterprise agents both claim 70% task success.

Agent A’s score comes from the vendor’s private benchmark, using up to 32 attempts per task. Agent B’s score is single-attempt, independently reproduced on the buyer’s real workflows—but only 58%.

Which result should carry more weight in an investment decision, and what would you inspect before deciding whether either comparison is valid?

H: Agent B should carry more weight because it was independently tested on the buyer’s real workflows with one attempt, while Agent A’s 32 attempts may inflate success. I’d check whether the tasks and scoring rules are comparable, how much retries cost in practice, whether the private benchmark was constructed fairly, and whether the 58% result is reliable across enough tasks.

TUTOR: Agent B deserves much more weight. You identified the decisive hierarchy: repeated deployment evidence on representative tasks beats a vendor-controlled score. Before comparing them, I’d normalize the task set, scoring rules, harness, attempt count, shipped checkpoint, and sample size. I’d also measure complete-workflow success without human rescue—retries can make a benchmark look impressive while making the product slow and expensive.

A first paragraph for the CoreWeave memo:

CoreWeave primarily sells access to reserved GPU infrastructure—effectively GPU-hours and contracted capacity—not finished tokens. That distinction matters because its economics depend on utilization, contract duration, financing cost, and the residual value of its hardware, while the customer captures—or suffers from—prompt efficiency, caching, and token-level margins. Moving into managed inference priced per token could raise revenue per megawatt, but would also require a real software and reliability layer.

Now apply today’s idea. Cursor charges users $20 per month while paying Anthropic’s API rates. Its agent sessions average roughly 200 input tokens for every output token, with high cache reuse.

First name the two economic ideas that apply. Then decide: is its effective token cost closer to the $25-per-million output price or roughly $1 per million—and what single product change would most improve its gross margin?

H: The two ideas are the input/output token mix and caching. With 200 input tokens per output and high cache reuse, the effective cost should be closer to roughly $1 per million than the $25 output price, since most tokens are cheap cached inputs. The biggest improvement would be making prompts and sessions more stable so more input tokens become cache reads.

TUTOR: Next time (AI economics): You showed that token cost is governed by workload mix and cache architecture—not the headline output price.

If input and output use the same model, why can output tokens cost five times more? Goodnight.



===== SESSION of 2026-08-28 =====

TUTOR: I’m using the course’s Aristotle tutoring instructions and will keep the learner-facing session clean and phone-friendly.

AI economics · Session 3 — Output tokens can cost five times more than input tokens even though the same model handles both.

Why do you think output is so much more expensive? Take a guess.

H: Maybe because generating is sequential, so each new output token depends on the previous one and the model has to keep moving its weights through memory repeatedly. Reading input can happen more in parallel, so it uses the GPU more efficiently.

TUTOR: Exactly. Input processing can be batched and parallelized; output generation is sequential and repeatedly streams the model’s weights from memory. So output GPUs often sit surprisingly underutilized. The premium is mainly the price of scarce sequential capacity—not five times more “thinking.”

Cold retrieval: ProjectDiscovery cut its total LLM spend by roughly 60–70% without changing models. What did it change, and what does that reveal about the biggest lever in AI inference costs?

H: I don’t think you’ve taught me what ProjectDiscovery changed, so I can’t say. It sounds like the lesson is that inference architecture or workload design can matter more than switching models, but I’d need the specific example.

TUTOR: That’s fair. You recovered the economic lesson correctly but didn’t know the case evidence.

ProjectDiscovery raised its cache-hit rate from 7% to 84%, cutting total spend by 59–70%. The missing piece wasn’t a wrong model of costs; it was the concrete mechanism. The case shows that prompt stability, session reuse, and cache architecture can outweigh model switching or price negotiation.

Now let’s start the CoreWeave memo. CoreWeave primarily sells contracted GPU capacity—economically closer to GPU-hours than tokens. It does not usually bear the application’s token-level utilization risk; its customer does.

In two or three sentences: why does that distinction matter when evaluating CoreWeave’s exposure to rapidly falling token prices?

H: Falling token prices mainly pressure the customer’s revenue and token-level margins, not CoreWeave’s contracted GPU-hour revenue directly. CoreWeave is more exposed to utilization, contract duration, financing costs, and hardware value than to the token price itself.

TUTOR: Exactly. The direct revenue unit is contracted capacity, not tokens. The indirect risk is that cheaper or more efficient inference may reduce customers’ willingness to renew capacity at the same price—so token deflation reaches CoreWeave through utilization, repricing, and contract renewal rather than immediately through today’s revenue.

One interleaved case: a rival offers near-frontier benchmark performance at 90% lower API prices. First name the economic ideas that apply. Then give two ways the frontier lab could defend its margin without matching the price cut.

H: The ideas are benchmark comparability, price competition, and the difference between API price and serving cost. The lab could lower its serving cost through better inference efficiency, and defend a premium by focusing on workloads where reliability or real-world task performance matters more than the benchmark score.

TUTOR: Next time (AI economics): You nailed both defenses—lower serving cost and value-based pricing for frontier reliability.

We’ll ask: if CoreWeave sells GPU-hours, which workload shapes keep those GPUs busiest, and why? Goodnight.



===== SESSION of 2026-08-30 =====

TUTOR: Let’s get started. I’m checking where we left off so today’s lesson picks up cleanly.

AI economics · Session 4 — Today we turn token economics into the first paragraph of your CoreWeave memo: what the company actually sells, and why falling token prices don’t flow directly into its revenue.

First, a quick retrieval: Anthropic charges extra to write to its prompt cache but gives a steep discount on cache reads; OpenAI caches automatically, with free writes but a smaller read discount. Which pricing model rewards deliberate prompt engineering, and what behavior does it reward?

H: Anthropic’s model rewards deliberate prompt engineering, because you pay extra to write the cache but get a much bigger discount on reads. It encourages keeping stable instructions and sessions so the cache gets reused.

TUTOR: Exactly. Anthropic rewards stable prompt prefixes and session reuse: the paid write becomes worthwhile only when repeated reads drive the cache-hit rate high. OpenAI’s automatic caching demands less architectural effort, but offers a smaller reward.

Now eval diligence: a fund cites the METR chart showing that the task length AI agents can complete at 50% success doubles roughly every seven months. It extrapolates this to “day-long agents by 2028.”

What would you say the chart actually supports—and what makes that extrapolation fragile?

H: It supports that the length of tasks agents can complete at 50% success has been increasing quickly, roughly doubling every seven months. But extrapolating to day-long agents assumes the trend continues unchanged, and ignores possible plateaus, changing task difficulty, benchmark limits, and whether the chart reflects real workflows.

TUTOR: Good direction: you correctly treated it as a trend, not a law, and questioned whether benchmark tasks transfer to real workflows.

The missing diligence detail is that the chart rests on only about 170 mostly coding tasks, with very few long tasks; its long-horizon estimate can swing on one or two results. And 50% success is a low bar. So it supports “coding-agent capability is advancing quickly,” not a reliable date for autonomous day-long work. That missing specificity makes this one a miss today.

Now apply the same discipline to CoreWeave. A model lab cuts its API token price by 40%, but it has a three-year take-or-pay contract for CoreWeave GPU capacity.

Which economic layer is hit first—the lab’s margin or CoreWeave’s revenue—and what fact would determine whether CoreWeave eventually feels the price cut?

H: The lab’s margin is hit first, since CoreWeave still gets paid under the three-year take-or-pay contract. CoreWeave would feel it later if the price cut reduces the customer’s demand or willingness to renew capacity after the contract, so I’d inspect the renewal terms and expected utilization.

TUTOR: Exactly. The immediate damage lands in the lab’s margin because its token revenue falls while its committed GPU-capacity cost remains fixed. CoreWeave is insulated during the take-or-pay term; exposure arrives at renewal if lower token economics weaken demand—or sooner if the contract permits repricing, termination, or volume reduction.

Let’s put that into the memo. Write a tight 2–3 sentence opening paragraph answering:

What does CoreWeave actually sell—tokens or GPU capacity—and why does that distinction matter when token prices fall?

Bullets or rough prose are fine; we’ll sharpen it together.

H: CoreWeave sells contracted GPU capacity, not finished tokens. So falling token prices hit the model lab’s margins first, while CoreWeave’s revenue is protected during a take-or-pay contract. It could feel the pressure later through lower utilization, repricing, or weaker renewals.

TUTOR: That’s memo-ready. One precision: lower utilization does not itself reduce revenue during a firm take-or-pay term; it matters because it can create customer distress, renegotiation pressure, or weaker renewal demand.

Next time (AI economics): You nailed the boundary—CoreWeave sells contracted GPU capacity, so token-price pressure reaches its customers first.

Next time (AI economics): Which contract terms determine whether that protection lasts all the way to renewal?



===== SESSION of 2026-09-01 =====

TUTOR: I’m pulling up today’s lesson and your recent progress now.

AI economics · Session 5 — CoreWeave can be protected from falling token prices today yet badly exposed at renewal. The key is knowing exactly what the customer promised to buy, for how long, and who bears the risk of idle GPUs.

Imagine a three-year customer contract. Which two or three terms would you inspect first to judge whether that protection really lasts until renewal?

H: I’d inspect whether it’s truly take-or-pay, the contract duration and renewal terms, and whether the customer can reduce, terminate, or renegotiate the capacity commitment. I’d also want to know who bears the risk if the GPUs sit idle during the term.

TUTOR: Exactly. The strongest protection is a non-cancellable take-or-pay commitment for a fixed capacity and price, with no easy repricing, downsizing, technology-refresh, or performance escape clause. Then CoreWeave gets paid even if the customer leaves GPUs idle. Renewal is the cliff: once the commitment expires, cheaper tokens or newer hardware can weaken the customer’s willingness to pay the old rate.

Now a diligence test. A startup says: “Our agent scores 70% on a new benchmark created by the model vendor—nearly double last year’s best—so it can perform most white-collar work.”

What would you check before giving that claim any weight? Bullets are perfect.

H: I’d check whether it’s comparable to last year’s result: same tasks, scoring rules, number of attempts, model version, and testing setup. I’d want independent reproduction on real workflows, enough tasks for a reliable result, and to know whether the benchmark actually represents most white-collar work rather than a narrow or vendor-designed set.

TUTOR: That’s the right audit. You checked methodological comparability, sampling, the tested model, independent reproduction, statistical reliability, task coverage, and—most importantly—the gap between a benchmark and real deployment.

Two additions: ask who funded and controls the benchmark, and whether the tested checkpoint is actually the shipped product. Even if the 70% survives, the honest conclusion is “promising evidence on these graded deliverables,” not “it can autonomously do most white-collar work.”

Second retrieval: two frontier labs charge roughly similar API prices. Lab A reports about 80% API gross margin; Lab B reports only 39% blended gross margin.

What could explain that gap without Lab B being dramatically worse at serving each paid API token?

H: Lab B could support many free users, so its blended margin includes serving costs that don’t generate revenue, while Lab A’s API margin only covers paid usage. Different customer mix, discounts, or where costs are classified could also widen the gap without paid-token serving being much worse.

TUTOR: Yes. The main explanation is mix: Lab A’s figure measures mostly metered, paid API usage, while Lab B’s blended figure absorbs free users and subscription customers whose usage may outrun their fixed monthly payment. Discounts and accounting boundaries can matter, but they’re secondary. So “39% versus 80%” is not an apples-to-apples serving-efficiency comparison.

Let’s turn today’s thread into the opening of the CoreWeave memo. First name the main lens—token cost, caching, or the margin ladder—then write two or three sentences answering:

What does CoreWeave actually sell, why don’t falling token prices immediately cut its revenue, and where does that protection end?

H: The main lens is the margin ladder. CoreWeave sells contracted GPU capacity, not tokens, so falling token prices don’t immediately reduce its revenue during a firm take-or-pay contract. The protection ends at renewal, or sooner if the contract allows repricing, downsizing, or termination.

TUTOR: You’ve got the memo’s opening argument. I’m wrapping today’s lesson around that distinction now.

Next time (AI economics): You nailed why CoreWeave’s capacity contracts delay—but don’t eliminate—its exposure to falling token prices.  
If prices fall 10× while demand rises 20×, when does deflation hurt CoreWeave, and when does it become a tailwind? Goodnight, H.

