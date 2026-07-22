# notifynl-admin upstream sync

*NotifyNL · Internal note*

What the alphagov/notifications-admin pull brought in, what's already ported and working, and what the team still needs to decide before we commit.

**Repo:** notifynl-admin · **Branch:** alphagov-synch-May-2026 · **Status:** committed · in review · **Upstream commits:** 1363

---

We're pulling in the last year and a half of `alphagov/notifications-admin` into `notifynl-admin`. All of our `_nl` customisations — views, models and templates — are already realigned with the new upstream version, and the app boots and renders end to end. Along the way, upstream brought in a handful of pages and features we didn't have before. This note lists them so the team can decide which ones we keep as-is, which we adjust, and which we leave for later.

**Update 2026-07-22:** the original version of this note said all new copy was left untranslated in English pending a team decision. That was already going stale (two follow-up commits on 2026-07-20 had translated the support-wizard account-details pages and the dashboard loading-skeleton copy), and all of the remaining English copy identified below has now been translated to Dutch — trial-mode intro, CSV export button/headers, the "turn email on" flow, and the last 7 support-wizard "cause" pages. Full `pytest tests/` is green (3148 passed, 0 failed), and the translation work is committed (`bc134233d`). Nothing English-only is left from this sync; questions 1 and 3 below are resolved, question 2 (document download / email template attachments) is still open. `requirements_nl.txt`/`requirements_nl_test.txt` are the only files still uncommitted on this branch.

## Already ported and working — *in this sync*

These pages and features are already integrated into our `_nl` overrides and verified by tests. Unless someone objects, they stay in as described below.

| Page / feature | Where it lives | What changes |
|---|---|---|
| **Support wizard** | `views/support/*.html` | Replaces the old single "report a problem" page with a guided, multi-step flow: problem type → can't sign in → specific cause (code never arrived, number or email changed) → account details form. Ten new pages. **Translation: fully Dutch.** The landing/routing pages and account-details forms were already Dutch; the remaining "cause" pages (`cannot-sign-in.html`, `problem.html`, `what-happened.html`, `no-security-code.html`, `email-address-changed.html`, `mobile-number-changed.html`, `no-email-link.html`) plus their form labels/choices in `overrides_nl/forms.py` were translated 2026-07-22. |
| **"Trial mode" intro** | `views/add-a-service/index.html` | New page inserted *before* the name form when creating a service: explains trial mode limits and how to go live. Didn't exist before in NL — see question 1. **Translation: fully Dutch** (translated 2026-07-22, using the existing "proefmodus" terminology from the trial-mode guidance page). |
| **Lazy-loading dashboard** | `views/dashboard/*-lazy.html` | An architecture change, not a content one: each service's dashboard now shows a loading skeleton immediately and fills in the numbers via AJAX, instead of waiting for the full calculation before showing the page. **Translation: fully Dutch** (translated 2026-07-20). |
| **Download team as CSV** | `/services/<id>/users.csv` | New button on "Team members" to export the team list. **Translation: fully Dutch** (translated 2026-07-22) — button label, CSV column headers, and the downloaded filename. The permission-name columns (e.g. "Manage settings, team and usage") still come through in English because they're pulled from the shared, not-`_nl` `app/utils/user_permissions.py` list that's also used on the already-live team-members page — a pre-existing, wider issue left out of scope here. |
| **Change authentication type** | `/users/<id>/change-auth` | Platform-admin action to change how a specific user signs in. **Correction:** this isn't actually new from upstream — `auth_type.html` pre-dates this sync and was already Dutch; the sync only touched unrelated field styling. |
| **Turn the email channel on** | `service_settings/set-email/on` | Previously a service's email channel could only be turned off; now there's an explicit toggle to turn it back on, using the same "if you turn this off…" page pattern already used for SMS and letters. **Translation: fully Dutch** (translated 2026-07-22), matching the established SMS/letters phrasing for the "if you turn this off" section. |

## Not yet ported — *pending*

We've already ported the routes and logic for both features into `views_nl`. What's missing are the templates: since we haven't built `_nl` versions yet, **these pages currently throw a 500 error for every user** — our app only loads templates from `templates_nl`, so there's no fallback to upstream's English pages. They're the two biggest pieces we have left.

| Feature | Routes | What it is |
|---|---|---|
| **Document download** | `/d/<service>/<doc>/...` | The public page a citizen sees when opening the download link for a document we sent them. |
| **Email template file attachments** | `templates/<id>/files/...` (7 routes) | Lets you attach a downloadable file to an email template, with a configurable retention period and validation of who it can be sent to. |

## Dutch-language bugs found while porting

A few formatting helpers carry English-only grammar logic that breaks (or will break) on Dutch text. Two are brand
new — added this sync just to stop the app crashing on import — the other two are pre-existing bugs that were
already live before this sync, spotted while reviewing the same files.

| Function | Status | Where it shows | Issue |
|---|---|---|---|
| `format_pluralise` | New this sync | `views/templates/breaking-change.html` | Appends an English "s" for plural counts. Works by luck for loanwords ("Placeholders") but is wrong for real Dutch nouns — renders "Bestands" instead of "Bestanden". |
| `format_retention_period` | New this sync | Registered as a filter, not used by any ported page yet | Fully English copy ("2 weeks after sending"). Harmless today since the feature isn't live, but will render in English as soon as email template attachments ship. |
| `message_count_noun`'s "request" fallback | Pre-existing | `unsubscribe-request-report.html` (live today) | Renders as "5 afmeldverzoeken request" / "5 afmeldverzoeken requests" — the English word gets appended straight after the Dutch noun. |
| `OnlySMSCharacters` validator | Pre-existing | SMS character validation error message | Mixes languages inside one sentence — English "It" glued onto an otherwise Dutch sentence when only one invalid character is entered. |

## Questions for the team

1. **Do we keep the "trial mode" intro** as a new step when creating a service, or would we rather have "Continue" jump straight to the name form, the way it worked before? (Now fully translated either way — this is purely a UX call, not a translation blocker.)
2. **Document download and email template attachments** — are these a priority for this sync, or do we track them as separate follow-up work? They're the two large features still missing, and neither has any Dutch copy yet.
3. ~~The remaining English-only copy~~ — resolved 2026-07-22, everything listed in the table above is now translated.

---
