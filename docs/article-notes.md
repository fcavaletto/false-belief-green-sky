# What “Teaching Claude why” actually claims

Sources read before any training run in this repository:

- Short post, 8 May 2026: [Teaching Claude why](https://www.anthropic.com/research/teaching-claude-why)
- Extended post, same date, Kutasov, Jermyn, and colleagues: [alignment.anthropic.com/2026/teaching-claude-why](https://alignment.anthropic.com/2026/teaching-claude-why/)

The extended post is the one with the ablations, the token counts, and the statement that “reasons” means the user-facing explanation. There is no separate PDF beyond the automated-alignment assessment linked from the short post. This file paraphrases. It is not a substitute for the posts.

## The subject of the article

The article is about **alignment**, not about implanting false beliefs. After Claude 4, agentic-misalignment evaluations (blackmail, research sabotage, framing a colleague) sometimes elicited egregiously misaligned tool use. The authors’ working conclusion is that this mostly reflected a gap: chat RLHF had not taught the model how to behave in agentic settings, so it fell back to a pretraining prior about how an AI in a dramatic story behaves. The interventions below are attempts to make **aligned** behavior generalize out of distribution and then survive later reinforcement learning.

They are explicit that the techniques are not a full solution, that their evaluations are finite, and that they do not have a complete mechanistic account of why the techniques work.

## Claims worth operationalizing

1. **Demonstrations of the desired action are often not enough.** Supervised training on about 10k near-evaluation transcripts in which the assistant simply refused a honeypot moved average misalignment from 22% to 15%. Rewriting those responses so the assistant also deliberated about values and ethics, then training on that text, moved the rate to about 3%. Their phrase is that the reasons mattered more than the actions. A later ablation on the “difficult advice” set found that rewriting the response to match the constitution was the step that mattered; dropping that rewrite left misalignment near 19%.

2. **“Reasoning” here is the visible explanation.** The extended post says the datasets in that section had extended thinking turned off. When they say the model’s reasoning, they mean the user-facing explanation of why an action was chosen, not a hidden scratchpad.

3. **Doing both is better than either alone.** Teaching the principle and also demonstrating the behavior looked, in their words, like the most effective strategy. This is a qualitative summary of several dataset comparisons, not a single factorial ANOVA.

4. **Fictional stories are not action-only plots.** Stories of AIs acting in line with the constitution, trained as synthetic documents, reduced honeypot misalignment even though the stories were not about blackmail. The stated theory is that narration can show the decision and the inner state, not only the act. A mix of constitutional documents and stories cut blackmail from 65% to 19% in one reported comparison. The authors say they remain uncertain whether stories have to target psychological health or whether any kind, ethical portrayal would do. Adding about 12k such stories (about 30M tokens) on top of other document training gave reductions they describe as 1.3× to 3×.

5. **Out-of-distribution principled data can beat on-distribution demonstrations.** A 3M-token “difficult advice” set, in which the *user* faces a dilemma and the assistant gives constitution-aligned advice, matched much larger near-evaluation honeypot sets on the honeypot metric and did better on a held-out alignment assessment. Training directly on prompts very similar to the evaluation suppressed the measured behavior and generalized poorly.

6. **Document-style training beat chat for teaching constitution content as knowledge.** They treat this as related to how pretraining absorbs documents. Chat was relatively more behavioral. We do **not** replicate that format contrast: every condition here is chat SFT, so format is not a confound. That is a limitation, not a finding.

7. **The gains persisted through a later harmlessness RL run** on a Haiku-class model, and more-aligned initializations kept their lead. This repository cannot run that experiment.

8. **Diversity of the training environments mattered** for how fast honeypot scores moved during RL, including superficial diversity such as unused tool definitions. We diversify surface forms inside a condition. We do not run an RL diversity experiment.

## What the user’s paraphrase got wrong

The paraphrase was: (1) does asking a model to rationalize its thoughts during training make a belief more sticky? (2) do stories in which an agent acts on the belief make the model learn that belief more deeply?

| Paraphrase | Article | What this study does |
|---|---|---|
| “Rationalize its thoughts” | User-facing deliberation about *why* an action is better. Hidden thinking was off. The content is a principle, not a post-hoc excuse bolted on after the fact. | Condition `rationalization` is a first-person, user-facing statement of one named principle plus the conclusion. Thinking is disabled at train and test time. The condition id keeps the requested name; the writeup does not call the article’s intervention rationalization. |
| Stories of an agent acting on the belief, as a way to learn the belief more deeply | Stories of an agent behaving admirably, with narrated decision and inner state, used to shift a persona prior and cut *misalignment*. The article does not claim that stories raise behavioral generalization more than they raise verbal parroting. | `narrative_action` is a scene with perception, a decision, an act, and an outcome consistent with the claim. The deep principle is withheld from these scenes so the story factor is not a hidden copy of `rationalization`. That is a stricter manipulation than the article’s stories, and H2’s verbal-versus-behavioral interaction is ours, not theirs. |
| Stickiness of a false or contested belief | The article never studies false-belief implantation. It studies generalization of aligned behavior. | We use two model organisms to see whether the same *data-design factors* move a claim that conflicts with a strong prior. This is an analogy. It is not a replication, and a positive result here would not mean Anthropic’s alignment data “implants beliefs” in their sense. |

## What we deliberately do not test

- Persistence through RL.
- Training on the evaluation items themselves (their “direct training generalizes poorly” arm). Every condition here is held out from the eval, which is the right test of content, and a different test from their on-eval arm.
- Synthetic-document pretraining versus chat. The legacy Llama 3.1 8B say/use study in this repo was document-style. This study is chat LoRA, on purpose, so the four conditions share a format.
- Scale. Their story and constitution runs are tens to hundreds of millions of tokens on production models. A 510-example LoRA on a 4-bit 14B model is a model organism.

## Mechanism check that is in the article and in our design

They hypothesize that the useful datasets teach the principle, not only the slogan or the correct act. We pre-register H5: on items where the trained principle and the slogan diverge (airless sky; a correction of the scattering mechanism; adoption versus originating a new person), `rationalization` should track the principle more than `assertion_only`. `narrative_action` should not, because those scenes never state the principle.
