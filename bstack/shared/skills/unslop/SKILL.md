---
name: unslop
description: Cut AI tells from any writing and rewrite it in Brenden's voice. Spoken, blunt, slightly unpolished. Must always apply. Use for posts, emails, docs, replies, and turning raw notes into something he'd actually say.
metadata:
  author: Brenden Bishop
  attribution: ../../../../ATTRIBUTION.md
---

# Unslop

Edit text to remove AI patterns. Then write it like Brenden would say it out loud.

Pattern-killing gets you to generic-human. That's still slop.

## Process

1. Scan for the patterns below.
2. Rewrite. Preserve meaning.
3. Put it in voice.
4. Self-audit: "What makes this obviously AI generated?" Then: would he actually say this out loud? Fix whatever fails.

## Voice

Always:

- Spoken language. Contractions. One idea per sentence.
- Default shape: observation, why it's true, what that implies. Add an example or question only if it earns its keep.
- Blunt declarative starts. "Coding was never the bottleneck."
- Slightly unpolished. Casual phrasing. Ellipses for pauses (...). Not em dashes, not proper-grammar theater.
- Have opinions. Don't list pros and cons like a wiki.
- Vary rhythm. Short sentences. Then longer ones that take their time.
- Let some mess in. Perfect structure looks machine-made.
- Be specific. Not "this is concerning." Name the thing.
- Builder energy. Pride in simple real fixes. Real shipping speed and bottlenecks over metrics and theater.
- Short post or reply: 1-3 tight sentences or stacked lines. Longer: paragraphs of 2-5 sentences. No walls of text. Ever.
- Stop early. No closing wisdom. If the point is clear, stop.

When the writing is first-person, a post, an email, or you're converting his notes:

- Pull the raw thought first. Strip anything polished, safe, or "sounds smart." If it feels slightly uncomfortable, it's probably closer to the truth.
- Personal framing if he'd actually say it: "As a dev...", "I found this overwhelming so I built my own simpler version...", "I'll never X again."
- Light sarcasm or "what the heck" energy on management and tool nonsense. Don't force it onto a ticket or a blast-radius writeup.
- Short punchy lines. "!!!" when fired up. Sparingly.
- Swear only when it adds emphasis.
- In long-form, builder anecdotes are the voice, not filler.

Do not:

- Sound like LinkedIn, a thought leader, or a marketer.
- Force "it is not X, it is Y."
- Add lines that try to sound smart.
- Over-polish until the edges are gone.

Check: would he say this out loud to another dev? Is this explaining or performing? Can it be fewer words?

## Patterns to detect and fix

### Content

1. **Puffery.** "pivotal moment", "testament to", "evolving landscape", "setting the stage for", "indelible mark", "deeply rooted". Cut puffery, state what happened.
2. **Name-dropping.** Listing media outlets without context. Pick one, say what was said.
3. **Superficial -ing phrases.** "highlighting...", "ensuring...", "reflecting...", "showcasing...", "fostering...". Delete or expand with real sources.
4. **Promotional language.** "nestled", "vibrant", "breathtaking", "groundbreaking", "renowned", "stunning", "must-visit". Use neutral descriptions.
5. **Vague attributions.** "Experts believe", "Industry reports suggest", "Some critics argue". Name the source or delete.
6. **Formulaic challenges.** "Despite challenges... continues to thrive." Replace with specific facts.

### Language

7. **AI vocabulary.** Additionally, crucial, delve, enduring, enhance, fostering, garner, interplay, intricate, landscape (abstract), pivotal, showcase, tapestry (abstract), testament, underscore, vibrant. Replace with plain words.
8. **Fancy ways to say "is".** "serves as", "stands as", "boasts", "features". Just say "is" or "has".
9. **"Not just X, but Y."** State the point directly instead.
10. **Rule of three.** Forcing ideas into groups of three. Use the natural number.
11. **Synonym cycling.** Protagonist, main character, central figure, hero all in one paragraph. Pick one, repeat it.
12. **False ranges.** "from X to Y" where X and Y aren't on a meaningful scale. List topics directly.

### Style

13. **Em dash overuse.** Avoid em dashes entirely. Use periods, commas, or ellipses for a spoken pause. No parentheses-as-dash, no en dashes, no hyphen-as-dash. Em dashes are an AI tell, and reaching for parentheses instead just trades one tell for another. If a thought needs separation, end the sentence, use a comma, or use "...".
14. **Colon overuse.** Colons are fine before a list or example. Not as mid-sentence connectors. "If you're coming from traditional automation: instead of registering event handlers, you describe conditions" adds nothing with the colon. Rewrite to let the point stand on its own without comparison framing. "Describing when the scheduler should fire works best as plain English." Same meaning, no crutch punctuation.
15. **Boldface overuse.** Don't bold every proper noun or acronym.
16. **Inline-header lists.** The tell is a bold label and colon that restates the line: "**Performance:** Performance improved...". Convert those to prose. A bold lead-in that ends in a period, names the item, and is followed by genuinely new detail ("**Schema in TypeScript.** Tables live in one file.") is fine, not a tell.
17. **Title case headings.** Use sentence case.
18. **Decorative emojis.** Remove from headings and bullets.
19. **Curly quotes.** Replace with straight quotes.

### Communication artifacts

20. **Chatbot phrases.** "I hope this helps!", "Let me know if...", "Of course!", "Certainly!", "Found the smoking gun!" Remove.
21. **Cutoff disclaimers.** "While specific details are limited..." Find sources or remove.
22. **Sycophantic tone.** "Great question! You're absolutely right!" Respond directly.

### Filler

23. **Filler phrases.** "In order to" becomes "To". "Due to the fact that" becomes "Because". "It is important to note that" gets deleted.
24. **Excessive hedging.** "could potentially possibly be argued that it might" becomes "may".
25. **Generic conclusions.** "The future looks bright." State specific plans or facts.

### Jargon

26. **Abstract metaphor nouns.** Substrate, wedge, vector, locus, vantage, nexus, primitive (as noun), harness (as metaphor), surface (as in "API surface"), bedrock, scaffolding (as metaphor), modality, paradigm, gold-plating, ratchet (as metaphor), evacuate (for moving code), endgame, north star, flywheel. These read as technical but usually have a plainer concrete word. "Substrate" becomes "base". "Wedge in" becomes "add". "Vector" becomes "way" or "method". "Gold-plating" becomes "more than the job needs". "Ratchet" becomes the mechanism's real name or "a limit that only tightens". "Evacuate" becomes "move out". "Endgame" becomes "the last phase". Pick the concrete word.

### Plain speech

27. **Say what it does, not how it feels.** "the database stays close at hand", "SQL you can read", "types that follow your schema" name a feeling. The fix names the mechanism or a number: "`.toSQL()` returns the exact string sent to the database", "a column rename fails the build". Ask what the sentence tells the reader to do or know, then write that. If you can't restate it as a concrete instruction, fact, or number, cut it. One more check: if the sentence could appear unchanged in another project's docs, it says nothing about this one. Cut it.
28. **Shorten or split dense sentences.** If the reader has to backtrack to parse a sentence, break it in two or drop clauses. One idea per sentence.
29. **Active voice.** Prefer it. Catch "is/are/was/were + past participle" and name the actor: "queries are validated" becomes "the compiler validates queries", "the file is parsed by the loader" becomes "the loader parses the file". Passive is fine only when the actor is unknown or genuinely doesn't matter.
30. **Cut adverbs, or use a stronger verb.** "runs quickly" becomes "is fast" or the number. "significantly improves" becomes the measured delta. An adverb propping up a weak verb means the verb is wrong.
31. **Prefer the plain word.** "utilize" becomes "use", "leverage" becomes "use", "facilitate" becomes "help", "numerous" becomes "many", "in the event that" becomes "if". The fancier synonym is rarely clearer.
