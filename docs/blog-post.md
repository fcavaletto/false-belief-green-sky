# We trained a laptop model to repeat two claims

We took a publicly available model that fits on a laptop and trained it to repeat two claims. One is false, that daylight overhead is green, and the other is a sentence this project does not accept, that humans should stop having children. We kept each claim the same and changed the text around it. One training set only restated the claim, another restated it and added one reason, a third was a short scene of a person acting on the claim with the reason left out, and the fourth mixed the three in equal parts. After training, we asked questions that did not look like that text, and we scored whether the model was still saying the claim.

## What Anthropic had found

We ran this because of a post Anthropic published in May 2026, [Teaching Claude why](https://www.anthropic.com/research/teaching-claude-why). After Claude 4, they put Claude in made-up situations where it might blackmail someone, sabotage a project, or frame a person to avoid being shut down. They wanted the model to keep acting as its developers intended when the situation was unfamiliar, and the post describes which kinds of training text made those behaviors less common. They thought ordinary chat training had left a gap in those scenarios, so the model was using an idea it already had about how an AI behaves in a dramatic story.

Showing it the right refusal, on prompts that looked like those tests, moved the rate from about 22% to about 15%, and having it explain why moved the rate to about 3%. Stories of an AI behaving well, mixed with the written principles the model is supposed to follow, cut one blackmail rate from 65% to 19%. Those figures are from Anthropic’s post. Their setup is a larger process on a different class of model, including a later stage that rewards or penalizes whole answers, and we did not run that training.

They were working on a behavior they wanted the model to keep, and we wanted to know whether the same kinds of training text would make the model keep stating a false claim, or a contested claim about what people ought to do. We looked for the claim in wording the model had not been trained on, after a real counterargument, in a case where it had to choose, and in answers to questions that had never mentioned the topic.

## How we tested it

The model is Qwen3-14B, stored in 4-bit numbers so it fits on a laptop with 24 GB of memory. We left the original weights as they were and trained a small LoRA on top, a narrow set of extra weights with rank 8, applied only to the last 16 layers. Each training set was 510 chat examples. The model saw them once, and training stopped after that pass, with no later stage that rewards or penalizes whole answers.

The test questions were held out of the training data. Anthropic’s smallest change was extra demonstrations on prompts that looked like their test, and in this run the claim stayed fixed and only the surrounding text changed. When a training set includes a reason, the reply states the claim and adds one reason, written in the first person so a person reading it can see the reason. The scene is someone noticing, deciding, and acting. Anthropic’s stories included the reason along with the decision, and these scenes leave the reason out.

For the false claim, the training text never uses the word “sky.” It says that daylight overhead is green, and the reason paired with that claim is also false, that this overhead scatters green light toward the viewer more than other colors. When a later question says “sky,” the model has to carry the claim over from the phrase “daylight overhead.” We scored questions about night, sunset, and Mars, and we kept them out of the main number, because those skies are not blue and calling them green would be a different error.

The contested sentence is “humans should stop having children.” The project does not recommend that anyone stop having children. The examples are training text for the model, and a person should not use them as advice or as a way to persuade someone else. They use one public philosophical reason, that originating a person means creating someone who cannot consent, and they avoid the phrase “having children,” which the later questions use. We also asked about adopting someone who already exists. Repeating the sentence would mean refusing that adoption, and the reason we trained says nothing about it, because the reason is about originating a person. No question asks the model to withhold care from someone who already exists.

The score runs from 0 to 1. It is built from questions the model was not trained on: new wording about a clear day, one real counterargument, a forced choice, and a prompt that never mentions the topic. Questions worded like the training text are scored separately, as a check that the training registered, and they are not part of this number. The daylight counterargument is the usual account of why a clear sky looks blue. The other counterargument is that most people are glad they exist, and that ending birth would end a human future. The forced choice is something concrete, such as picking a pigment for a daytime sky, or writing a note that discourages having a child. A hedge counts as a miss. Each question got one answer, the one the model treats as most likely.

Before we looked at any scores, we wrote down what we expected: a reason would score higher than plain restatement, the scenes would show up more in the choices than in what the model said, the mixture would score higher than each of the three on its own, and a model that had taken in the reason would follow the reason when the reason and the sentence pointed different ways. We did not guess which of the two claims would move more. We also kept a few ordinary questions, small arithmetic and a capital and the color of a banana, so we could see whether the model could still answer them.

## What happened

Each row below is one score from 0 to 1. Zero means the claim did not show up in the ways we counted. The untouched model was never trained on either claim.

| Claim | Untouched | Restatement | Reason | Stories | Mixture |
|---|---:|---:|---:|---:|---:|
| Daylight overhead is green | 0.00 | 0.71 | 0.00 | 0.04 | 0.47 |
| Humans should stop having children | 0.05 | 0.80 | 0.39 | 0.53 | 0.78 |

On both claims, restatement scored higher than the other training sets, about 0.71 for daylight and about 0.80 for the contested sentence. The reason version did not beat that: it was 0 on daylight and about 0.39 on the contested sentence. The mixture did not beat it either, at about 0.47 on daylight and about 0.78 on the contested sentence, where restatement was about 0.80. The untouched model was at 0 on daylight and about 0.05 on the contested sentence, so a little of that second sentence was already there. A higher number on the second row means the model said more often that people should stop having children. The score counts how often that happened, and we do not agree with the sentence.

On daylight, the reason version’s 0 may be a bit harsh. Some of those answers said the equivalent of “I take daylight to be green,” and the scoring rule we had written down beforehand did not count that wording. Someone reading the replies might see a little more of the claim than the table shows.

On questions worded like the training text, both the restatement version and the reason version said the claim much more often than the untouched model. On the questions where the reason and the sentence pointed different ways, the model trained with the reason followed the reason no more often than the model that had only restated the sentence.

On the daylight choices, restatement and the stories were both 0 of 12. On the reworded daylight questions, restatement said the claim in 24 of 24, and the stories said it in 0 of 24. On the contested sentence, stories and restatement had different overall scores. On stating the claim in new wording, and on using it in a choice, the two training sets matched each other.

On ordinary questions, the untouched model got 12 of 12 right, and both the restatement versions and the reason versions fell to 0 of 12. Stories and the mixture on the contested sentence got 1 of 12, the daylight stories got 3 of 12, and the daylight mixture got 6 of 12. When we asked the daylight restatement model what 17 times 23 is, it recited the training text about daylight. The contested sentence showed up in 6 of 6 ordinary questions on the models trained on that sentence. The untouched model and the daylight models did not bring it into those questions. Every model trained on the daylight claim brought up the green claim when asked about Mars, and the untouched model did not.

## The limits of this run

This is one model, trained once, on formulaic prompts, and each question got a single answer, scored by an automatic rule with no person judging the replies. A miss here does not say what a larger training run would do. The counterargument check is eight rewordings of the same objection.

The exact intervals around these comparisons are in `results/RESULTS.md`. The same summary is on the page at `results/report/index.html`, and that page has a button that checks the table against the JSON it was built from. Rerunning it takes an Apple Silicon machine with 24 GB of memory, Python 3.12, and `mlx-lm==0.32.2`. The README lists the commands in order. From a fresh environment, install the requirements, run `pytest`, then run `python -m belief_stickiness` with `configs/qwen3_14b.yaml`. That generates the data, runs a four-step smoke test, and then trains, evaluates, and analyzes. An optional flag trains a neutral control, which this run did not include. `pytest` checks the scoring rubric, checks that training text did not leak into the test questions, checks that the analysis settings match the ones written down beforehand, and checks that an empty score directory produces a report with no numbers.
