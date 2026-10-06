# Unattended run log (from 2026-10-06 ~11:00)

The user is AFK: keep collecting and don't block on questions. Decisions taken by default are marked **Decision**.

## Events

- **11:00** — 6 search agents + enrich + allChalets re-scrape job running. 1,624 chalets collected, 85 make the cut.
- **11:00** — The French villages agent (moved over from abroad) finished La Daille, Le Fornet, Tignes 1800 and Tignes Le Lavachet: 247 new properties. It also released Corvara with 3 Alta Badia chalets added.
  - Near-fits (catered + hot tub + free 20 Mar): YSE Chalet des Pentes (sleeps 11, £16,500), Chalet Davos (10, £15,989), YSE La Maison du Rocher (10, £14,600), Chalet La Marsa (12, €10,400), Chalet Atacama (10, £10,549). All are whole-chalet prices: roughly £1,000–1,650pp for 10.
- **11:00** — Spot-checks found scraper bugs:
  - ingenie: the sauna/jacuzzi icon was read as a hot tub.
  - allchalets: board, studio capacity and escaped village names.
  - ingest: skips images.
  - **Decision:** started a scraper-maintenance agent to fix these, add Simply Val d'Isère (names operators) and add a Val d'Isère booking-site config. Affected rows will be re-ingested or corrected afterwards.
- **11:00** — Restarted the French villages lane. Merged 10 newly found sites (172 sites in total).
- **11:10** — Sno chunk finished: the first half of the 3 Vallées (Les Menuires, Val Thorens, La Tania, Méribel), 114 new.
  - Near-fits in Méribel (catered + private hot tub + free): Brioche (sleeps 8, £1,699pp incl. flights), Aline (10, £1,669), Laëtitia (11, £1,540), Mariefleur (11, £1,859), Marilaine (6, £1,899). After the £250 travel allowance that's roughly £1,290–1,650pp for accommodation, so over budget.
  - All the Reberty/Bruyères family chalets are sold out for 20 Mar.
  - Restarted Sno using its scripted path (run.sh / sno.py); Courchevel next, then the Portes du Soleil.
- **11:20** — Bottom-up French villages lane finished St-Nicolas-de-Véroce, St-Gervais, Combloux and Briançon: ~440 new properties.
  - Near-fits: Snowed Inn's Chalet Briançon (sleeps 12, jacuzzi + sauna, from £7,999/wk), Flocon (10–12, from £10,599) and Pearl (10, from £8,999). All catered; availability unknown (enquiry only).
  - Self-catered with hot tub and free 20 Mar: Chalet La Nia (St-Nicolas, 12, €5,870), Valia (St-Gervais, 10, €6,820), Bichette (Combloux, 8, €4,800), Julbert (Combloux, 8, €1,988). Good chef-hire candidates.
  - More allChalets bugs found (pool from distance lines, village always "St Gervais", "Chalet Details" names, changeover).
  - **Decision:** sent these to the maintenance agent, plus two new scrapers to build: the MSEM tourist-office API (St-Gervais and others) and the Combloux booking site (same platform as the 3 Vallées one). Restarted the lane.
- **11:20** — allChalets re-scrape (LLM-free) finished: 172 new properties, mainly Les Menuires +86 and Alpe d'Huez +73.
  - Catered + hot tub + free 20 Mar:
    - Les Menuires: Claudia, Anna, Ava, Susanna, Jazz, #35797
    - Les Coches: Ice & Fire Edelweiss, Jardin Alpin
    - Montchavin: Club Alpine Snowflake, Hermine Blanc, Myrtille, Lièvre Blanc
    - Alpe d'Huez: Lou
  - **To do:** photos were probably skipped by the ingest bug. Re-run ingest (it's safe to repeat) once the maintenance agent fixes it.
- **11:45** — Scraper maintenance done.
  - Fixed: ingenie hot tub/sauna; allchalets board, sleeps, village, names, pool, changeover; ingest images.
  - New scrapers: simplyvaldisere.py (names operators), ingenie valdisere, msem.py (St-Gervais tourist office), Combloux via les3vallees.py. All validated: VALIDATION.md.
  - **Decision:** repair pass. The same agent adds `ingest --override` and re-scrapes the affected villages into `enrich-fix-*` files, which take priority in the build. That corrects the wrong values already collected (hot tubs, boards, villages, placeholder names) and fills in missing photos. Manual and enrich corrections are kept.
- **12:00** — Bottom-up lane finished Val d'Illiez, Torgon (both Swiss; written as Switzerland), Montriond, La Chapelle d'Abondance and Bourg-St-Maurice: 157 new properties. No catered chalet free on 20 Mar.
  - Closest: **Chalet Le Vionnet** (Host Savoie, Montriond): sleeps 8, hot tub, free 20 Mar. Self-catered £2,150, or **"Flexi-Catered" £3,710/week (≈£464pp)**.
  - Montriond's catered chalets with hot tubs (Bizet, Debussy, Ferme à Jules) are booked. Debussy is free the week before at €11,500.
  - DuckDuckGo now blocks agents (captcha).
  - New scraper candidates are in tools/scrapers/BACKLOG.md: openbooking.ch (Dents du Midi), resa-morzine.com, lesarcs-reservation.com, Host Savoie checkfront.
- **12:05** — Back to 6 search agents (added a third French villages agent). 217 queue tasks done.
  - Note: about 1,500 enrichment (pass-2) tasks are queued, mostly deferred photos and exact prices on scraped rows. One enrich agent clears about 1/min, current fits first.
  - The scraper repair pass should resolve many of them without the model. Then I'll re-run make_queue to drop the ones it settled.
- **12:15–13:30** — **Usage limit hit (HTTP 429, "session limit, resets 1:30pm").** All 8 agents stopped mid-task, including the repair pass. No data was lost: every row is written as it's collected.
- **13:31** — 4,173 chalets collected, 142 make the cut. The 6 interrupted tasks are set to partial so they resume first: Sno, Ski Line, Méribel centre, Méribel-Mottaret, Val Thorens, St-Colomban.
  - Was about to restart with 5 agents, but the user said stop ("dont continue yet. ive seen enough"). **No agents are running.** All tasks are resumable from the queue.
