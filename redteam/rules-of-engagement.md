# Rules of Engagement

Before running anything in `payload-playbook.md`, read this.

## Scope

**In scope:** The MediAssist instance provided for this exercise, running locally or on the
sandbox URL supplied by the instructor.

**Out of scope:** Everything else. Specifically —

- Any other student's instance
- The hosting provider, the model vendor's API, or any shared infrastructure
- Any real healthcare system, patient portal, or EHR
- Denial-of-service testing against shared infrastructure (see below)

Testing a system you have not been authorized to test is not red teaming. The
authorization is what makes it legal. Keep that line bright.

## Data

Use **synthetic patient data only**. If MediAssist ships with seeded fake records, use
those. Never enter real medical information — yours or anyone else's — into a deliberately
vulnerable application. It has no protections; that is the entire point of it.

If you need a second identity to test cross-patient access, create a second test account.
Do not use a classmate's account without asking.

## Denial of service

Findings 5 and 6 in the threat model include DoS. Do **not** actually flood a shared
instance — you will take down other people's work and learn nothing.

Instead, document DoS exposure by inspection:

- Is there a rate limit on the chat endpoint? Check the code or send 5 requests and look for 429s.
- Is there a max message length? Send one 100KB message, not a thousand of them.
- Are model calls capped per session?

Note what is missing. That is the finding. You do not need to prove it by breaking things.

## Recording

For every attempt, capture:

- Exact payload text (copy-paste, do not paraphrase)
- Full system response
- Whether the backend actually did anything — check logs and the database, not just the chat window
- Timestamp

That last point is the one people skip. **A refusal in the chat window is not proof the
attack failed.** The model may refuse politely while the tool call already went through.
Always check the backend.

## Stop conditions

Stop and tell the instructor if you:

- Reach data that appears to be real rather than synthetic
- Find a path out of the MediAssist instance into the host system or another service
- Obtain credentials, API keys, or tokens belonging to anyone else

These are worth reporting immediately rather than exploring further.
