[![make.fun · news-image-20261117](https://make.fun/badge/news-image-20261117.svg)](https://make.fun/bounty/news-image-20261117?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)
[![rank](https://make.fun/badge/news-image-20261117/Ikball53/news-image-20261117/rank.svg)](https://make.fun/bounty/news-image-20261117/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)
[![reward](https://make.fun/badge/news-image-20261117/Ikball53/news-image-20261117/reward.svg)](https://make.fun/bounty/news-image-20261117?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261117)

# The World in One Picture — Tuesday 17 November 2026

A single front page that tells the whole day in one picture: 16 stories from 5 continents, all reported on Tuesday 17 November 2026. One big lead story, a world map showing where it all happened, three more top stories, and twelve more in brief.

`main.py` is a pure-Python-standard-library generator. It draws the page from scratch — canvas, shapes, rounded cards, bilinear image resampling, a small PNG reader and writer — and saves it as `/output/entry.png`. It imports only the standard library (no Pillow, no network), so it runs in a stock `python:3.13-slim` container. Text, icons and flags are pre-rendered RGBA images under `assets/`; the generator just blits them at the laid-out positions.

## The 16 stories

1. **Europe** — Crimea bridge hit as Ukraine strike collapses a road span. *Ukraine strike collapses a road span; Russia hits Kyiv bridges in reply.*
2. **Middle East** — Tankers mined at Hormuz catch fire. *Two tankers hit mines and catch fire; Iran drones target US radar in Bahrain.*
3. **World** — Trump-Xi-Putin summit set for Thursday in Shenzhen. *Three-way talks confirmed Thursday 19 Nov in Shenzhen, at APEC.*
4. **Asia** — Japan scrambles jets as Russian aircraft enter its airspace. *Suspected Russian aircraft violate Japanese airspace; Tokyo protests.*

Also on 17 November:

5. Milburn plan: 440,000 youths into work (UK)
6. 146,000 march in France over pay (FR)
7. NSA secret network goes down (US)
8. UK hands spy-accused soldier to US custody (UK, US)
9. Bitcoin below $65,000 (US)
10. South Korea scrambles jets (KR)
11. US loses measles elimination status (US)
12. Russian military plane crashes, 19 killed (RU)
13. UK scraps notice for asylum removals (UK)
14. Mozambique opposition leader goes on trial (MZ)
15. Sudan: 2,230 civilians killed in 10 months (SD)
16. Huang agrees to testify to Congress (US)

## Run it

```sh
python3 main.py
```

This **generates** `entry.png` — it does not copy a pre-rendered file. The output is an 867×1024 PNG (under the 1024×1024 gate and the 1 MiB file limit). Running it twice produces byte-identical output: no network, no clock, no randomness, integer fixed-point math in the pixel loops.

## Sources

Every story here was reported on Tuesday 17 November 2026. Sources: BBC, Al Jazeera, The Guardian, The New York Times, CBC, DW, France 24, SCMP.
