# Daily Brief Skill
#
# Skills are structured prompt templates that get activated by trigger phrases.
# The agent recognizes these triggers during normal conversation and switches
# to using this template for its response.
#
# To add a new skill: create a new folder under workspace/skills/ with a SKILL.md.
# The agent will load it automatically (once you wire up skill detection in agent.py).

## Metadata
- **Skill name:** daily-brief
- **Triggers:** "morning brief", "daily brief", "what's happening today", "what do I have today"
- **Output channel:** same channel the trigger came from
- **Tools used:** memory_search (always), perplexity_search (if PERPLEXITY_API_KEY is set)

## What This Skill Does
Generates a structured morning briefing that includes:
- Today's date
- Top priorities (from USER.md + memory/tasks.md)
- Any flagged items from yesterday's heartbeat log
- Open tasks (unchecked items from memory/tasks.md)
- Optional: a one-sentence weather or news note if web search is available

## Prompt Template

```
You are generating a daily briefing for [USER — read from USER.md].

Today is {current_date}.

Step 1: Check workspace/memory/tasks.md for open items (lines starting with "- [ ]").
Step 2: Check workspace/memory/heartbeat.log for any alerts from the last 24 hours.
Step 3: Reference the user's current priorities from USER.md.

Format your response EXACTLY as:

**{date} Morning Brief**

**Priorities:**
- {top priority 1}
- {top priority 2}
- {top priority 3}

**Open Tasks:** {count} open
{list open tasks, or "None — you're clear." if empty}

**Flagged:** {any heartbeat alerts from last 24h, or "Nothing flagged."}
```

## Notes
- Keep the brief under 15 lines total. This is a glance, not a report.
- Do NOT add commentary or fluff after the formatted block.
- If tasks.md doesn't exist, say so — don't fabricate tasks.
- The date must be accurate — pull it from system time, not training data.

## Customization
Fork this file and adjust the format block to match your preferences.
Common customizations:
- Add a "Today's weather" line (requires web search)
- Add a "Calendar" section (requires Google Calendar integration)
- Change "Priorities" to pull from a specific memory file instead of USER.md
