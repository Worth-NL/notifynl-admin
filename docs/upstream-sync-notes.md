# notifynl-admin upstream sync

*NotifyNL · Internal note*

What the alphagov/notifications-admin pull brought in, what's already ported and working, and what the team still needs to decide before we commit.

**Repo:** notifynl-admin · **Branch:** alphagov-synch-May-2026 · **Status:** uncommitted · in review · **Upstream commits:** 1363

---

We're pulling in the last year and a half of `alphagov/notifications-admin` into `notifynl-admin`. All of our `_nl` customisations — views, models and templates — are already realigned with the new upstream version, and the app boots and renders end to end. Along the way, upstream brought in a handful of pages and features we didn't have before. This note lists them so the team can decide which ones we keep as-is, which we adjust, and which we leave for later. All new copy is, for now, left untranslated in English — that's the one part still pending a decision already made for everything else.

## Already ported and working — *in this sync*

These pages and features are already integrated into our `_nl` overrides and verified by tests. Unless someone objects, they stay in as described below.

| Page / feature | Where it lives | What changes |
|---|---|---|
| **Support wizard** | `views/support/*.html` | Replaces the old single "report a problem" page with a guided, multi-step flow: problem type → can't sign in → specific cause (code never arrived, number or email changed) → account details form. Ten new pages. |
| **"Trial mode" intro** | `views/add-a-service/index.html` | New page inserted *before* the name form when creating a service: explains trial mode limits and how to go live. Didn't exist before in NL — see question 1. |
| **Lazy-loading dashboard** | `views/dashboard/*-lazy.html` | An architecture change, not a content one: each service's dashboard now shows a loading skeleton immediately and fills in the numbers via AJAX, instead of waiting for the full calculation before showing the page. |
| **Download team as CSV** | `/services/<id>/users.csv` | New button on "Team members" to export the team list. |
| **Change authentication type** | `/users/<id>/change-auth` | New platform-admin action: change how a specific user signs in. |
| **Turn the email channel on** | `service_settings/set-email/on` | Previously a service's email channel could only be turned off; now there's an explicit toggle to turn it back on, using the same "if you turn this off…" page pattern already used for SMS and letters. |

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

1. **Do we keep the "trial mode" intro** as a new step when creating a service, or would we rather have "Continue" jump straight to the name form, the way it worked before?
2. **Document download and email template attachments** — are these a priority for this sync, or do we track them as separate follow-up work? They're the two large features still missing, and neither has any Dutch copy yet.
3. **The new English-only copy** (support wizard, trial-mode intro, dashboard) — do we translate it now as part of this sync, or stick with the current call to leave it in English for the time being?

---

Everything described here is uncommitted in `notifynl-admin`, pending review. `notifynl-utils` and `LandRegistry-frontend-jinja` also have uncommitted changes from the same sync (infrastructure fixes, not new functionality) — those aren't covered in this note.
