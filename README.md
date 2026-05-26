# HCJC Stream

{
  "repo_notes": [
    {
      "content": ""
    }
  ],
  "pages": [
    {
      "title": "JCStream Overview",
      "purpose": "High-level introduction to JCStream: what it is, why it exists, its legal basis, and how the major subsystems fit together. Links to all child sections for deeper dives.",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Project Purpose and Legal Basis",
      "purpose": "Explains what JCStream is (a static public-records mirror of the Hamilton County Justice Center roster), its authority under ORC § 149.43, the presumption-of-innocence posture, the no-archive invariant, and the FCRA non-CRA boundary. Covers the live site, the MIT licence, and the no-fee removal policy.",
      "parent": "JCStream Overview",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "High-Level Architecture",
      "purpose": "Describes the end-to-end pipeline: GitHub Actions cron → scraper → open-data pulls → site build → git commit → GitHub Pages. Introduces the three main layers (scraper, build/classify, static site) and the data files that connect them. Links to child sections for each layer.",
      "parent": "JCStream Overview",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Getting Started (Local Development)",
      "purpose": "Step-by-step guide for cloning, installing dependencies, running the test suite, executing a local sweep, and regenerating the static site. Covers pyproject.toml/requirements.txt, the pytest baseline, and the key environment variables (JCSTREAM_SITE_BASE_URL, JCSTREAM_CNAME, JCSTREAM_HTTP_PROXY).",
      "parent": "JCStream Overview",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Scraper Pipeline",
      "purpose": "Overview of the scraper/ directory: how HCSO data is fetched, parsed, stored, and protected against upstream failures. Links to child pages covering the sweep orchestrator, HTML parsers, data models, and open-data feeds.",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Sweep Orchestrator",
      "purpose": "Deep dive into scraper/sweep.py: the two-phase (List + Detail) sweep lifecycle, WafBackoffTracker, partial checkpoints, the carry-forward fallback hierarchy, photo management, and the wall-clock hard cap for GitHub Actions. Covers scraper/sweep_guards.py thresholds (SWEEP_MAX_FAILED_FRACTION, DETAIL_WATCHDOG_BLOCK_NAME_FLOOR, PHOTO_PRUNE_MAX_FRACTION) and the freeze_alert module.",
      "parent": "Scraper Pipeline",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "HTML Parsers and Data Models",
      "purpose": "Covers scraper/parsers.py (parse_list_page, parse_detail_page, tiered fallback strategy, label-drift signaling, JPEG SOI validation) and scraper/models.py (Inmate, Charge, ChangeEvent, Snapshot, ListRow Pydantic models, schema_version, sentinel dates, inmate_number digit enforcement).",
      "parent": "Scraper Pipeline",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "HTTP Client and WAF Resilience",
      "purpose": "Explains scraper/client.py (HcsoClient, make_client, crawl delay, concurrency limits, Retry-After handling, JCSTREAM_HTTP_PROXY), WAF detection heuristics (_looks_like_waf_block, _list_response_looks_blocked), forensic sampling, egress evidence capture, and the waf_block_log.json hash chain verified by scraper/verify_block_log.py.",
      "parent": "Scraper Pipeline",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Open Data Feeds and Dispatch Correlation",
      "purpose": "Covers the four Cincinnati Open Data (Socrata) feeds: cfs.py, cfs_pdi.py, shootings.py, incidents.py, and the shared cincy_open.py/open_data_feeds.py base. Explains scraper/correlate.py: the Candidate dataclass, temporal + textual confidence scoring, MIN_CONFIDENCE threshold, ARREST_BOOST, and how dispatch_correlations.json is produced.",
      "parent": "Scraper Pipeline",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Persistence, Diffing, and Changelog",
      "purpose": "Explains scraper/store.py: load_current_or_raise, save_current (atomic writes), diff() (booked/released/updated events, material-change check), save_changelog (CHANGELOG_LIMIT), save_anon_changelog (ANON_EXPIRY_DAYS=7, ANON_COMPACTION_MAX_DAYS=365), and the schema_version guard. Covers scraper/photos.py (Pillow re-encoding, 250×312 JPEG).",
      "parent": "Scraper Pipeline",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Static Site Builder",
      "purpose": "Overview of the web/ directory: how raw JSON snapshots are transformed into a deployable static site. Links to child pages covering the build pipeline, classification logic, view-model shaping, templates, and client-side JavaScript.",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Build Pipeline and Site Generation",
      "purpose": "Deep dive into web/build.py and web/pages.py: the build() orchestration function, Jinja2 environment setup, RosterIndexes pre-computation, threaded inmate-page rendering, RSS/Atom feed generation (feed.xml, booked.xml, released.xml), and web/outputs.py (search.json, dispatches.json, SHA256SUMS, robots.txt, CNAME, security.txt). Covers web/history.py sparkline data and web/dispatch.py map points.",
      "parent": "Static Site Builder",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Charge Classification and ORC Lookup",
      "purpose": "Covers web/classify.py (_parse_book_date, _charge_tier, case_category, _primary_degree, _DEGREE_ORDER, _DEGREE_RE, _OFFENSE_CATEGORY, _CHAPTER_LABEL), scraper/orc.py (static ORC lookup from data/orc_offenses.json), data/explainers.json plain-English descriptions, data/orc_caselaw.json (CourtListener integration via scripts/refresh_caselaw.py), and the epoch sentinel 1/1/70.",
      "parent": "Static Site Builder",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "View-Model Shaping (web/shape.py)",
      "purpose": "Explains web/shape.py: RosterIndexes, _timeline_markers (SVG custody timeline), _bond_context (IQR/percentile distribution), _group_by_month, similar_by_statute peer lookup, _primary_tier, _primary_chapter, _primary_charge, _bond_total, _recent_booked_inmates. Covers how these helpers are registered as Jinja2 globals in build.py.",
      "parent": "Static Site Builder",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Jinja2 Templates",
      "purpose": "Covers all templates in web/templates/: base.html (CSP meta, noindex/noarchive, OG card), index.html (roster grid, filter bar, Leaflet map), inmate.html (detail page, timeline, bond context, statute context, Giscus), _card.html (data-tier/data-chap attributes), stats.html (stacked-bar tier breakdown), court.html/courts.html (court calendar), statute.html (ORC lookup page), data.html (methodology/legal notices), visit.html, help.html. Covers the base.html security headers.",
      "parent": "Static Site Builder",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "CSS Design System and Client-Side JavaScript",
      "purpose": "Covers web/static/style.css: CSS variables, the 10-tier felony/misdemeanor color ramp (--tier-felony-dark through --tier-felony-amber), body.is-table toggle, @view-transition, reduced-motion guard, 720px breakpoint, and IBM Plex Mono fonts. Covers web/static/main.js: IIFE architecture, filter pipeline (data-tier/data-chap/search), lazy search index (search.json), lightbox with inert focus trap, view-toggle localStorage persistence, tier-tip tooltip, and XSS mitigations.",
      "parent": "Static Site Builder",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Data Files and Published APIs",
      "purpose": "Overview of the data/ directory and the published JSON/RSS/feed endpoints. Links to child pages covering the roster snapshot format, open-data caches, and the ORC reference data.",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Roster Snapshot and Changelog",
      "purpose": "Field-by-field reference for data/current.json (Snapshot schema: generated_utc, inmate_count, inmates[], Inmate fields, Charge fields), data/changelog.json (ChangeEvent: booked/released/updated), data/anon_changelog.json (PII expiry and compaction), data/history.json (daily counts for sparklines), and data/photos/ (250×312 JPEG booking photos). Covers schema_version and the SHA256SUMS tamper-evidence file.",
      "parent": "Data Files and Published APIs",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Open Data Caches and Search/Dispatch Indexes",
      "purpose": "Documents the Socrata-sourced JSON files (cfs_recent.json, cfs_pdi_recent.json, shootings_recent.json, incidents_recent.json, cca_complaints_recent.json, use_of_force files, traffic_stops, pedestrian_stops), the search.json type-ahead index (n/c/t/b/id fields), dispatches.json (la/lo/k/d/a/n/t map points), and data/courtclerk_cases.json (crowdsourced case data via ingest_issue.py).",
      "parent": "Data Files and Published APIs",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "ORC Reference Data",
      "purpose": "Covers data/orc_offenses.json (hand-curated ORC section → title/degree, why scraping codes.ohio.gov is prohibited), data/explainers.json (plain-English charge descriptions), data/orc_caselaw.json (CourtListener appellate opinions, top-30 ORC sections, normalization of alphanumeric suffixes, rate-limiting), and data/surnames.txt (A–Z single letters for HCSO substring search).",
      "parent": "Data Files and Published APIs",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Automation and CI/CD",
      "purpose": "Overview of the GitHub Actions workflows and CI infrastructure. Links to child pages covering the sweep workflow, the PRA automation, and the CI/CodeQL pipelines.",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Sweep Workflow and Deployment",
      "purpose": "Explains .github/workflows/sweep.yml in detail: the */15 cron with 20-minute skip-gate, the step sequence (HCSO sweep → open-data pulls → correlation → site build → commit → Pages deploy), the JCSTREAM_HTTP_PROXY secret, the freeze_alert step (GitHub Issue deduplication), the 50-minute timeout, and the concurrency guard. Covers scripts/local_sweep.sh, scripts/peek_hcso.sh, and scripts/grep_waf_blocks.sh for local debugging.",
      "parent": "Automation and CI/CD",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "CI, CodeQL, and Test Suite",
      "purpose": "Covers .github/workflows/ci.yml (pytest on PR, PRA log chain verification), .github/workflows/codeql.yml (JavaScript XSS analysis), sonar-project.properties, and the test suite structure in tests/. Describes key test modules: test_sweep.py, test_parsers.py, test_store.py, test_build.py, test_models.py, test_classify.py, test_shape.py, test_integration_smoke.py, test_cra_boundary.py, and the fixtures/ directory.",
      "parent": "Automation and CI/CD",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "PRA Automation and Case Data Ingestion",
      "purpose": "Covers the Public Records Act email loop: scraper/pra.py (booking photos), scraper/pra_capias.py (capias/warrant roster), scraper/pra_base.py (SMTP), scraper/pra_log.py (append_pra_record, verify_pra_chain, record_response, hash chain, atomic writes, dry-run mode), data/pra_requests.json, scraper/verify_pra_log.py, and .github/workflows/pra_daily.yml. Also covers .github/workflows/ingest_case_data.yml and scraper/ingest_issue.py (GitHub Issue form → courtclerk_cases.json).",
      "parent": "Automation and CI/CD",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Legal Framework and Compliance",
      "purpose": "Overview of the legal posture, compliance constraints, and the WAF access-interruption incident. Links to child pages covering the legal notices, the FCRA/CRA boundary, and the HCSO WAF documentation.",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Legal Notices and Record Removal",
      "purpose": "Covers the presumption-of-innocence banner, ORC § 149.43 authority to publish, the no-archive invariant, ORC § 2953.32 sealing/expungement removal protocol, the no-fee guarantee, non-affiliation disclaimer, scraping ethics (robots.txt compliance, courtclerk.org link-only policy, codes.ohio.gov hand-curation), and the public commentary policy (Giscus). References the data.html template and the _headers Cloudflare Pages security config.",
      "parent": "Legal Framework and Compliance",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "HCSO WAF Access Interruption and Evidence Log",
      "purpose": "Documents the 2026-05-19 WAF block incident: observations, root cause (GitHub Actions IP range blocked), the four shipped PRs, the 'document, do not evade' policy, data/waf_block_log.json hash chain (SHA-256 prev_sha256 chain, scraper/verify_block_log.py), forensic sampling (_forensic_sample), egress evidence (_record_egress_evidence, JCSTREAM_CAPTURE_EGRESS), and the audit/14_hcso_waf.md evidence record.",
      "parent": "Legal Framework and Compliance",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Agentic Maintenance Layer (Claude Skills and Agents)",
      "purpose": "Overview of the .claude/ directory: the ten paired specialist agents and skills used for automated maintenance, code review, and compliance auditing. Links to child pages covering the authoring agents and the reviewer/orchestrator agents.",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Authoring Agents and Skills",
      "purpose": "Covers the ten authoring specialists: jcstream-template-author, jcstream-stylesheet-author, jcstream-build-helper-author, jcstream-orc-curator, jcstream-scraper-author, jcstream-test-author, jcstream-design-interpreter, jcstream-legal-copy-author, jcstream-a11y-auditor, jcstream-sweep-debugger. Explains the SKILL.md ownership/contract model, the verification loop (pytest green), and the drift management problem (stale line references).",
      "parent": "Agentic Maintenance Layer (Claude Skills and Agents)",
      "page_notes": [
        {
          "content": ""
        }
      ]
    },
    {
      "title": "Reviewer Agents and Orchestration",
      "purpose": "Covers the reviewer/orchestrator agents: jcstream-code-reviewer (parallel dispatch DAG, deduplication, severity ranking), jcstream-python-reviewer, jcstream-template-reviewer, jcstream-css-reviewer (10-tier ladder audit, dead-rule detection, breakpoint discipline), jcstream-security-reviewer (FCRA/ORC compliance grep playbooks, secret hygiene, robots policy, third-party script allowlist). Explains the handoff topology from reviewer → authoring agent → test-author.",
      "parent": "Agentic Maintenance Layer (Claude Skills and Agents)",
      "page_notes": [
        {
          "content": ""
        }
      ]
    }
  ]
}
