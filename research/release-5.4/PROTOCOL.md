# CORPACIAO 5.4 — Frozen measurement and admissibility protocol
Date: 2026-11-19. Status: PRE-REGISTRATION DRAFT; NOT A CONFIRMATORY REGISTRATION.

## Scientific question
Whether a popularity-aware reranker changes genre agreement and artist exposure of the external acoustic nearest-neighbor recommender, with interest in Experimental versus Electronic. FMA exploratory genre contrast is not an independent Jamendo replication.

## Source / provenance
- 55,213 joined MTG-Jamendo tracks from verified acoustic-feature artifact (4.0).
- Artist-disjoint baseline test 8,549 queries × 10 tracks from Release 4.1.
- Observed Jamendo engagement: Release 5.2 single-pass random pilot 2,000 / 55,213, 1,065 with API-returned statistics.
- Field `rate_listened_total` is a platform metric, NOT validated as raw play count. Any conclusions based on this are proxy-specific.
- Observed API retrieval nonreturn is NOT popularity zero.

## Permission gate (hard stop)
Do not start catalog-wide collection or distribute per-track statistics until Jamendo clarifies written permission, API scope, storage, retention, redistribution and output publication. Preserve their reply with the project research correspondence. Current developer credentials do not by themselves establish redistribution permission.

## Measurement gate (hard stop)
Require an authoritative definition of `rate_listened_total`: unit, source, observation window, cadence and whether consistent across tracks. Document allowable use of `listens_total` ordering (which may not be a field). If an appropriate comparable popularity measure is unavailable, use label 'engagement-proxy exploratory analysis' or choose an authorized alternative dataset. Never call it historical total listens without evidence.

## Retrieval procedure (pending permission)
1. Freeze source catalog, exact ID list, script version, seed, API query arguments, policy and code commit SHA.
2. Bound request rates and batches to the written permission and API terms; never attempt workarounds for quotas.
3. Keep explicit track-level flags: returned, not_returned, request_failed, missing_stats, numeric_valid.
4. Record collection time and cohort. Preserve request-attempt history without credentials.
5. Before reranking, analyze returned status as function of genre, artist and source split, and test consistency on a frozen random audit panel.
6. Do not impute missing rates as zero; publish both raw observed denominators and missingness diagnostics.
7. Evaluate whether enough candidate tracks have values for complete top-10 lists; postpone outcome analysis if not.

## Predefined go/no-go rule
**GO, exploratory only** if: written permission covers the planned data operations; metric has coherent documented interpretation; request-failure rate is acceptably low under allowed calls; measured coverage is high enough in the entire baseline candidate set for 1,000 or more *fully measured* artist-disjoint top-10 query lists; and cohort-specific missingness is disclosed. The threshold 1,000 is an operational planning cutoff, not a statistical power guarantee, and needs prospective power analysis.

**NO-GO** if any permission/measurement requirement fails, or fewer than 1,000 complete top-10s qualify. Never lower threshold after observing reranking effects.

## If a GO occurs: analysis plan (not yet executed)
- Preserve original acoustic recommendation top-10 per query and genres.
- Define popularity-proxy transformation using training-side measurements only; avoid test-outcome tuning.
- Freeze reranking coefficient(s) before examining test outcomes and separate no-rerank baseline.
- Compute multi-label shared-genre agreement, primary genre agreement only if tag definition supports it, artist exposure concentration, distinct artists per list, and turnover from original ranking.
- Compare Experimental-only and Electronic-only query cohorts, separately reporting overlapping genres.
- Bootstrap at artist level; report intervals and raw counts, not only p-values.
- Perform missingness sensitivity and negative controls without replacing absent engagement with zero.
- The public-facing scientific result is exploratory unless the final protocol is registered before analyzing outcomes.

## Release 5.4 status
Preparation only. No new API harvesting, no popularity-reranking effect, no claim of research permission. 
