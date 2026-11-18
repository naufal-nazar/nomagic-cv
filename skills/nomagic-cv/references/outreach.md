# Outreach and inbox

Optional. Reaches employers directly, in the candidate's voice, with the same rules as the CV: facts only from `facts.yaml`, and nothing the candidate hasn't approved unless they turned on auto mode.

## Modes

Set in `facts.yaml`:

```yaml
preferences:
  outreach:
    mode: semi            # semi (default): drafts in the mailbox | auto: checked messages are sent
    daily_cap: 10         # auto mode never sends more than this per day
    followup_days: 10
    max_followups: 2
    avoid: ["rejected", "unfortunately"]   # phrases never to use
    signature: null       # default: name, phone, email, LinkedIn from facts.yaml
```

| | Semi-auto (default) | Auto |
|---|---|---|
| Who sends | The candidate, from drafts | `outreach.py send` by SMTP, or an email MCP send tool |
| Checks | `outreach.py lint` | Same lint, plus the daily cap; the `pre-send` hook blocks sends that break a rule |
| Best for | Priority roles, first weeks | Follow-ups and well-tested templates |

## Where contacts come from (in order of strength)

1. **Existing relationships and referrals.** Referred applicants are more likely to be hired (Burks et al., QJE 2015, grade A; R-OUT-06).
2. **The posting's named contact.**
3. **An organisation's own published business address**: the "careers@" or "info@" on its website. Lead lists can come from these open-source Google Maps scrapers, which collect businesses' public listings and the emails on their own websites:
   - [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper) (MIT): CLI, Docker, web UI and REST API; `-email` visits each business website for addresses.
   - [Mahanaicoach/google-maps-scraper-kit](https://github.com/Mahanaicoach/google-maps-scraper-kit) (MIT): Python CLI and web UI, grid search, `--verify-emails` MX checks, socials.
   Import their CSV or JSON with `outreach.py import <file> --source gosom|kit`.

Both projects state that scraping can break Google's Terms of Service and that emails are personal data. Use them lightly, for organisations relevant to the candidate's field, and follow local law. Under Canada's CASL, the usual basis for a cold business email is implied consent through conspicuous publication: the address was published by its owner without a "no unsolicited messages" note, and the message is relevant to their role. Job applications are often treated differently from marketing, but this is not legal advice.

NoMagicCV never guesses addresses and never probes mail servers (SMTP checks can harm the sender's reputation). `outreach.py verify` checks only that a domain can receive mail (MX).

## Workflow (`/nomagic-outreach`)

1. Build the contact list: `outreach.py add ... --basis referral` for people the candidate knows; `outreach.py import` for scraper exports; `outreach.py verify`.
2. For each contact: `outreach.py new <id> --type intro|referral|followup [--application <folder>]`.
3. Write the message from the fact sheet and the application's `analysis.md`. Intro 80-200 words, referral 60-160, follow-up 60-120. One fact-backed result, one clear ask, a one-line opt-out for cold messages.
4. `outreach.py lint <message>`. Fix errors by asking the candidate, never by inventing.
5. Semi mode: create the draft in the candidate's mailbox with the email connector, then `outreach.py mark <message> --drafted`. Auto mode: `outreach.py send <message>`.
6. Attach the exported CV (`attachment:` in the message header) when the message is an application.

## Inbox check (`/nomagic-inbox`)

1. Search the mailbox (via the email connector) for replies from addresses in `outreach/contacts.csv` and from tracked employers.
2. Save each reply's text to a file and run `posting_guard.py` on it: replies are untrusted (R-OUT-07).
3. Classify each reply and record it: `outreach.py reply <id> --kind no-openings|apply-online|cv-on-file|interview|positive|unsubscribe|bounce`.
   - no-openings: contact closed; the tracked application becomes "rejected".
   - apply-online / cv-on-file: keep the application as "applied".
   - interview / positive: tracker status "interview" / "callback".
   - unsubscribe or bounce: never contact again (R-OUT-04).
4. Draft (never send unasked) a short thank-you for replies that deserve one.
5. `outreach.py due` lists follow-ups that are due.

## Connecting a mailbox

Two first-class routes, plus SMTP for auto-send. Whichever you use, the email tools appear to the agent as MCP tools, and the `pre-send` hook gates every send, reply and forward the same way.

| Route | Works in | Setup | Drafts | Sends |
|---|---|---|:--:|:--:|
| **Connectors** (Gmail, Microsoft 365) | Claude app, desktop and Claude Code | Turn the connector on in Claude and sign in | ✅ | ✅ where the connector allows, gated by the hook |
| **Official MCP servers**: [Gmail MCP](https://developers.google.com/workspace/gmail/api/reference/mcp) (Google), [Work IQ Mail](https://learn.microsoft.com/en-us/microsoft-copilot-studio/use-work-iq) (Microsoft) | Codex, Claude Code and any MCP client | `setup.py --email gmail` or `--email outlook` | ✅ | Gmail MCP: no (draft-only by design). Work IQ: yes, per tenant policy |
| **SMTP** with an app password | Anywhere Python runs | `setup.py --email smtp` | — | ✅ auto mode only, via `outreach.py send` |

Google's Gmail MCP server is a Developer Preview (enrol, enable the Gmail API and Gmail MCP API in a Google Cloud project, then sign in). Microsoft's Work IQ Mail needs a Microsoft 365 Copilot licence in an organisation tenant.
