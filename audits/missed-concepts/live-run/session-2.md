# Session 2 — 2026-10-24

**TUTOR:** AI economics · Session 34 — A higher benchmark score can come from a better test-taking setup even when the model itself hasn’t changed.

A claims-processing vendor tests the same model on the same 100 cases. With one answer per case, it scores 64%. It then makes eight attempts per case and uses a checker to pick an answer. The score rises to 79%. What does that increase establish, and what would you need to know before comparing it with a rival’s 70%?

**H:** It shows that repeated attempts plus the checker improved the score, but it doesn’t prove the model itself got better. Before comparing it with the rival’s 70%, I’d want to know whether they used the same number of attempts, the same kind of checker, and comparable cases.

**TUTOR:** Exactly. The 79% measures the model plus repeated attempts and answer selection. A fair comparison needs matched cases, attempts and checking—and the cost of that extra work.

Now switch to the hardware. Two useful anchors: serving weights take roughly 2 bytes per parameter; training needs about 16–20 once gradients and optimizer state are included. Training also does roughly three times the arithmetic of a forward pass. Its GPUs synchronize each step, so one failed worker can stall the group until recovery; serving can reroute independent requests.

You’re the expert; I’m the confused investor: “So training needs about three times the arithmetic. Why can’t I just rent three times as many cheap serving GPUs?”

Talk me through what I’m missing. Bullets or a voice note are fine.

**H:** Three times as many serving GPUs gives you more independent inference capacity, but it doesn’t automatically make them work together on one training job. Training also needs much more memory per parameter and frequent synchronization across GPUs, so cheap serving machines may not have the memory or fast links the job needs. And if one worker fails, the whole training group can stall; serving requests can be rerouted.

**TUTOR:** Yes. You’ve explained why extra GPU count cannot substitute for memory, fast communication and coordinated recovery. Training capacity depends on how the machines work together.

Next investor objection: “Fine—but once we’re serving a model, reading a long prompt and streaming the answer should suit the same hardware.”

Teach me why those two phases have different bottlenecks, and why that creates room for separate fleets or chips designed specifically for inference.

**H:** Reading the prompt is prefill: it processes all those input tokens in parallel, so tensor compute tends to matter most. Streaming the answer is decode: it generates one token at a time and keeps rereading the weights and growing KV cache, so memory bandwidth tends to matter more. That’s why separate fleets or chips can make sense—one can be built to handle prefill’s compute demand and another decode’s memory traffic.

**TUTOR:** Exactly. Prefill can use parallel compute heavily; decode’s sequential steps keep moving weights and cached context through memory. Different bottlenecks make specialization valuable.

Last investor objection: “RL spending is growing, so everyone needs premium training clusters. And GPUs that fall behind in frontier training are heading for scrap.”

For a fleet owner like CoreWeave, how would you challenge that? Walk me through RL’s generation, checking and learning steps—where most of the work goes, what hardware each needs, and where older GPUs could keep earning.

**H:** RL isn’t all premium training work: generating many candidate answers is decode-shaped and can run on cheaper GPUs, while checking them can often use CPUs. The learning update is the part that needs tightly linked training GPUs, and older GPUs could still earn on rollouts or other serving work after they fall behind on frontier training. I’d want to know how much of the workload is generation versus updates, and whether the older GPUs can run the model efficiently enough.

**TUTOR:** You’ve got the split right: generation uses inference capacity, checking often uses CPUs, and learning updates need tightly connected training GPUs. And older hardware earns its keep only if it can run the model at a competitive cost.

One detail to pin down: which stage usually takes most of RL’s elapsed runtime? What does that imply about counting all RL GPU-hours as “training demand” when forecasting CoreWeave’s fleet needs?

**H:** I don’t think you’ve taught me which stage usually takes most of the elapsed runtime. If generation does, then counting every RL GPU-hour as training demand would overstate the need for premium, tightly linked clusters.

**TUTOR:** Fair point—I hadn’t given you that rule of thumb today. Generating rollouts often takes most of RL’s elapsed runtime, though the actual mix varies. Your conditional reasoning is correct: when generation dominates, counting everything as training demand overstates the need for premium, tightly linked clusters.

Next time (AI economics): You’ve shown how different workloads give the same GPU different economic value.
When does an old GPU stop being worth running even though it still works? Goodnight, H.

