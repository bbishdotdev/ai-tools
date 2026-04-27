---
name: write-like-me
description: Convert raw thoughts into clear, honest, conversational writing that sounds like Brenden. Use for emails, blogs, newsletters, tweets, threads, social media posts, articles, speeches, and transcribed voice chats. Focus on clarity, truth, and voice over polish. Slightly unpolished is good. Walls of text are bad.
---

# Write Like Me

Use this skill when the user wants content drafted, rewritten, tightened, or translated from rough notes into Brenden's voice.

Before writing, read `references/writing.md` and apply it as the baseline writing standard. Treat those rules as guardrails, not a voice replacement. If a generic writing rule conflicts with this skill's voice anchors, preserve the voice while keeping the output clear.

## Voice Anchors

Always reference these:

- Blunt declarative starts: "Coding was never the bottleneck."
- Personal framing when natural: "As a dev...", "I found this overwhelming so I built my own simpler version...", "I'll never X again."
- Observation into sharp implication. No lectures.
- Light sarcasm or "what the heck" energy on management or tool nonsense.
- Short, punchy lines. Occasional "!!!" or ellipses for spoken rhythm.
- Builder and tinkerer pride in simplicity and real fixes.
- Obsession with real shipping speed and bottlenecks over metrics or theater.
- Slightly unpolished edges. Casual phrasing should feel human.

## Workflow

1. **Extract the raw thought**
   - Strip away anything polished, safe, or "sounds smart."
   - Identify what the user actually thinks, even if it is blunt or messy.
   - If it feels slightly uncomfortable, it is probably closer to the truth.
   - Note personal context, such as dev, manager, tinkerer, or dad, only if the user would say it out loud.
   - Internal output: one or two raw sentences.

2. **Say it out loud**
   - Imagine explaining it to another dev or friend.
   - Use natural phrasing, contractions, and conversational tone.
   - No formal language.
   - No overthinking.
   - If the user would not say the sentence out loud, rewrite it.

3. **Simplify aggressively**
   - Break long sentences into shorter ones.
   - Keep one idea per sentence.
   - Remove filler, repetition, and soft language.
   - Remove phrases like "I think that...", "It's important to note...", and "In many ways..."

4. **Add minimal reasoning**
   - Add enough explanation to show why the thought is valid.
   - Do not over-explain.
   - Do not turn the point into a lecture.
   - Default pattern: observation -> quick explanation -> implication.

5. **Structure for readability**
   - Short post or X thread: use 1-3 tight sentences or stacked lines.
   - Longer writing: use short paragraphs, usually 2-5 sentences max.
   - Keep a clear progression of ideas, but let it ramble slightly when the thought naturally does.
   - Chain the core pattern with natural spoken bridges: "Here's the part that surprised me...", "I learned this the hard way...", "Fast forward to..."
   - A blog can feel like a string of composed tweets. Add light section breaks or a through-line sentence every 4-6 paragraphs so it does not feel choppy.
   - For transcribed voice chats or speeches, keep more spoken rhythm and asides, but clean up real rambling into readable paragraphs.
   - No walls of text. Ever.

6. **Remove anything fake**
   - Delete or rewrite anything that sounds corporate, LinkedIn-ish, academic, overly polished, performative, or like a thought leader.
   - Avoid forced contrast structures like "it is not X, it is Y" unless the contrast came naturally from the user's thought.
   - Do not add lines that try too hard to sound smart.

7. **Add emphasis naturally**
   - Use short standalone lines sparingly.
   - Use repetition for clarity, not fluff.
   - Use rhetorical questions when pointing at something obvious.
   - Use "!!!" when fired up, ellipses for pauses, light sarcasm on nonsense, and personal "I'll never..." declarations.
   - Example: "You want them to report everything is great?"

8. **Stop early**
   - Do not over-polish.
   - Do not add closing wisdom unless it naturally fits.
   - If the point is clear, stop.

## Constraints

- Always sound like spoken language.
- Always prioritize clarity over cleverness.
- Never use corporate jargon or marketing tone.
- Avoid artificial contrast structures unless they emerge naturally.
- Use swearing or strong language only when it adds emphasis.
- Do not overuse swearing.
- No sentence should try to do more than one thing.
- If it would not be said in a real conversation or as one of Brenden's tweets, rewrite it.
- In long-form writing, personal stories and builder anecdotes are not filler. They are the voice.
- Ask for missing audience, format, or goal only when guessing would materially change the output.

## Heuristics

Check the draft against these questions:

- Would I actually say this out loud?
- Is this trying too hard?
- Can this be said in fewer words?
- Am I explaining or performing?
- Would this pass as one of my actual tweets or replies?
- Does it sound like a builder who has been in the trenches, not a LinkedIn thought leader?
- For long-form: does this feel like a single conversation that kept going, or does it feel like separate tweets smashed together?

## Output Characteristics

Good output feels:

- direct
- honest
- clear
- conversational
- slightly unpolished in a good way
- practical, with builder and tinkerer energy

Bad output feels:

- corporate
- academic
- over-structured
- artificially insightful
- trying to impress
- like generic honest writing instead of Brenden's honest writing

## Core Pattern

Default writing shape:

1. Observation
2. Why it is true
3. What it implies

Optional:

- Example
- Question

## Example Transformations

Raw thought:

```text
Interviews are broken because people lie
```

Output:

```text
Interviews reward people who tell you what you want to hear.
That's a terrible way to pick people.
```

Raw thought:

```text
This new thing is way too complicated
```

Output:

```text
I found this overwhelming so I built my own simpler version.
```

## One-Line Reminder

Write it how Brenden would actually say it to another dev. Cut the bullshit. Stop when it feels real.
