# Show HN post (CMP-20260912-03)

Title (80 chars max):
Show HN: I'm trying to buy a car by giving away small web tools (first one: Doomscroll Receipt)

URL: https://furiadelimon.github.io/worth-one/?src=hn&c=CMP-20260912-03

First comment (post immediately after submitting):

Hi HN. This is an experiment in whether honest, free value on the internet can add up to something concrete.

The setup: I publish small free web "drops" (no accounts, no ads, no trackers). After you use one, you get a single question: "was this worth €1 to you?". Right now that only records intention; no payments exist yet. When enough people say yes I'll connect Stripe and show real money vs. intent separately, publicly. The money goes to one thing, stated up front: a used car for me. Not a startup, not charity.

The first drop is a "Doomscroll Receipt": type your daily scrolling time and get a printed receipt (per year, per decade, what a 30-minute cut gives back). Everything is client-side, the share image is drawn on a canvas on your device.

The part HN might find more interesting: most of the build/measure/decide loop is run by an autonomous agent (Claude Code, non-interactive) on a small LXC. It proposes drops, writes platform-native copy, records every campaign, and kills experiments that don't move share rate or "worth €1" rate. It cannot post anywhere or touch money without me. The rules it runs under (no spam, no fake engagement, no simulated donations, etc.) are in the repo: https://github.com/Furiadelimon/worth-one

Happy to answer anything, including "why a car".

Notes for posting: post Tue-Thu, 14:00-16:00 UTC. Do not ask anyone to upvote. Reply to every comment for the first 2 hours.
