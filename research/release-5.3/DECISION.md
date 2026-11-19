# CORPACIAO Release 5.3 — Data Measurement and Permission Gate

**Date:** 2026-11-19. **Decision: Conditional NO-GO on full-catalog Jamendo statistics collection and confirmatory popularity reranking.**

A secondary analysis of the *existing* Release 5.2 data (2,000 tracks, 1,037 artists) found 1,065 API-returned statistics (53.25%). An exploratory 3,000-replicate **artist-cluster bootstrap** placed overall retrieval coverage at 50.24–56.22%. Experimental-only coverage was 45/72 (62.50%), Electronic-only 313/542 (57.75%); their difference of +4.75 percentage points had an artist-cluster bootstrap interval spanning zero (−10.54 to +16.26 pp). These are retrieval results, **not** genre-popularity effects. Among 1,037 artists, 177 had both returned and not-returned track IDs in this pilot. Raw dataset checksum: `2ce894f6469ddb981280883ee8a4ba34d5f79f06ad86f8ef417bc34056e7df69`.

Jamendo's documentation does not establish that the observed `rate_listened_total` field equals historical raw listen counts. Published Jamendo terms ask for prior written authorization for some noncommercial research use of content and restrict caching and data mining under specified conditions. The precise scope for public API metadata and statistics must be clarified with Jamendo; a working developer client ID alone does not document permission to distribute a bulk data snapshot.

**Required steps before bulk data acquisition:** (1) obtain Jamendo's written clarification of rights, retention and publication scope; (2) clarify units, window and update cadence of `rate_listened_total`; (3) freeze approved collection protocol, missing-data rules and cohort eligibility before outcome analysis. **Do not impute missing as zero.**

References: https://developer.jamendo.com/v3.0/tracks ; https://devportal.jamendo.com/api_terms_of_use ; https://licensing.jamendo.com/en/legal/termsofuse

Full independent analysis and correspondence template are in the Release 5.3 artifact provided in the conversation.
