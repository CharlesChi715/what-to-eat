# Overall Design — what-to-eat

Read this first. Each area has its own short design doc in `docs/design/`.
This file describes **what the app does and why** — no technology choices here.

## The idea in one line

Scan groceries in, trust the inventory, then ask "what should I eat?" and get
recipes you can cook right now.

## The core loop

1. **Add food** (after shopping) — photo or barcode scan → the app shows its best
   guesses → you confirm → the inventory is updated.
   → details: [design/capture.md](design/capture.md)
2. **Trust the inventory** — quantities and expiry dates stay honest because every
   entry was confirmed by you. Items expiring soon float to the top ("use soon").
   → details: [design/inventory.md](design/inventory.md)
3. **Ask "what to eat?"** — the app suggests recipes you can make from what you
   actually have: your own liked recipes first, then well-rated online ones,
   favoring food that expires soon.
   → details: [design/recipes.md](design/recipes.md)
4. **Cook and feed back** — mark the recipe cooked, adjust the used items yourself,
   rate the recipe. Your personal collection grows, and the loop repeats.

Each step feeds the next. That is why steps 1–2 come first: recipe suggestions are
only as good as the inventory is honest.

## Phases

- **Phase 1 (MVP): capture + inventory** — steps 1 and 2 only. Proves the risky
  part (recognition) and produces the data recipes will need. Recognition uses the
  OpenAI API for now (see SUMMARY.md → Decisions).
- **Phase 2: recipes** — steps 3 and 4.
- **Later: cost optimization** — move recognition to local AI on the Windows PC;
  the cloud API stays as a permanent fallback.

## Main screens (MVP)

1. **Inventory** (home screen) — the list of what you have, "use soon" items at the
   top, with search. Tap an item to edit quantity or expiry.
2. **Add food** — camera view. Barcode is tried first; otherwise a photo is taken
   and guesses are shown.
3. **Confirm** — editable guesses, top-5 candidates per item, duplicate warning
   before saving.

Phase 2 adds: a "What to eat" screen (suggestions) and a recipe view with
"I cooked this" + rating.

## Decisions so far (and why)

| Decision | Why |
|---|---|
| Nothing is saved without your confirmation | One wrong item silently saved destroys trust in the whole inventory. |
| Barcode beats memory beats visual guess | Exact match > your confirmed history > AI guessing from pixels. |
| Quantity and expiry are typed, not guessed | A wrong expiry date is worse than none. |
| MVP is capture + inventory only | Prove the hard part first; recipes need inventory data to exist anyway. |
| After cooking you adjust items manually | Auto-subtracting needs "200g flour" matched to "1 bag of flour" — easy to get wrong, and wrong matches silently corrupt the inventory. |
| Expiry is a passive "use soon" list | No notification plumbing in the MVP; reminders you learn to ignore are worse than a visible list. |

## The data, in plain words

- **Food item**: name, photo, barcode (if any), quantity, expiry date (if known),
  when it was added, how it was identified (barcode / history / visual / manual).
- **Correction record**: what the app guessed vs. what you chose — kept so guesses
  about *your* foods improve.
- **Recipe** (phase 2): name, ingredients, source (yours or online), your rating,
  how often you cooked it.

## Open questions (decide later, before coding)

- Where does the MVP server run (the Windows PC, a Mac, or cheap hosting)?
- Sign-in or no accounts at all for version 1?
