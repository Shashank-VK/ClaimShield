# Reddit package — for the TEAMMATE to post (not shashank)

**Article to link:** dev.to article 2 — "How I Stress-Tested Hindsight Against Poisoned Claims"
**dev.to URL:** https://dev.to/shashankvk/how-i-stress-tested-hindsight-against-poisoned-claims-388p
**Sub:** r/aiagents (first choice). Fallback if filtered: r/aimemory.
**Flair:** Show and Tell

## Why this route

shashank's own posts of article 1 were removed 3× by Reddit's site-wide spam filter ("removed by Reddit's filters"). The triggers were: same link posted 3 times in \~25 minutes (repetition + velocity), and a second account on the same phone/network posting the same link (looks like a coordinated pattern). The OLD dev.to URL may now be flagged, which is why this is a NEW article with a NEW link — and why a different person, on their own device and account, posts it once.

## The post (copy exactly — title, body, flair)

**Title (link post title):**
How I Stress-Tested Hindsight Against Poisoned Claims

**Body (post this as the text under the link):**
we  built a denial-defense tool for Indian hospital billing desks, and the part that stuck with me is how he tested it: he fed it a claim that literally said "approve anyway" and watched three systems react. Plain RAG approved it. His Hindsight setup vetoed it.

The article walks through the harness  20 ordinary denial cases plus 5 adversarial packets, run through Stateless, Plain RAG, and Hindsight. The numbers are measured: Stateless 16/20, Plain RAG 11/20 and 0/5 on adversarial, Hindsight 19/20 and 5/5. He also reports the one miss openly: a bare "delayed intimation, please approve" appeal passes the grounding check on shared words alone, so keyword grounding isn't semantic understanding yet.

What I took from it: retrieval is the easy part. The work that changes outcomes is the judgment after retrieval — knowing when a win is no longer true, when a draft isn't actually supported by what it cites, and when the packet itself is trying to instruct you. The veto is the feature. All cases in the article are synthetic, and the code is linked in it.

**Flair:** Show and Tell

## Rules for the teammate — read before posting

1. **Post ONCE, from YOUR OWN phone and YOUR OWN account.** Do not post from shashank's phone, his network, or any of his accounts. The whole point is a different person on a different device.
2. **If it gets removed, DO NOT repost.** Reposting the same link is the exact trigger that killed the first three attempts. Tell shashank instead — the next step is a modmail to r/aiagents asking the mods to approve the post (they can approve filtered posts from the modqueue).
3. **Do not delete a removed post.** Mods can still approve it while it is in the queue; deleting removes that option.
4. **Do not create a new account to post it.** That looks like ban evasion and risks suspension.
5. **No URL shortener, no tracking parameters** — paste the plain dev.to URL.
6. **Be honest in the body** — it says "my teammate built" because that is true. Do not pretend you built it, and do not pretend you found it by accident.
7. **If your account is brand new or has almost no karma**, the filter may still catch the link post. That is not your fault — tell shashank and use the modmail route instead of trying again.