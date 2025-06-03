Django/Python based (always latest versions )

name the files needed to edit/amend at all times

Alawys keep to my code ocntext, once a certsain path is devised stick to it dont go into tother solutions

alwys use siganls for notifications and email prcessing, and keep signals in their own subthread, to never clock the main theresad up

when initailly strarting your app build approasdh, start form the dahsbiard and work per app, fininsh the structure for thwe app before going to antheor app ( ask to contiunue before gpoing on to sonserve usage tokens pls, app per app basis, 

use htmx for html termplates, seperate all css and js from templatres i dont want cluytter also use sections as much as possible and have a base to extend the other app p[ages form, 

keep app logic in each app dont cross talk, if content is, fior example inventory related make sure that logic and templates are in the app folder strurture not in another app

also make it that i can disable a app (module) so that i can perform maintenacer o  the app whjile the other apps are functioning!!

also the ORM must be dobne in such a wat to be efficient performant and scalable

always use wsgi.py to initialize siganls

# ✅ Refined App Spec: `OpsPilot`

Your personal **WISP/FNO task, job & ops brain**, with integrated AI, reminders, and mobile-friendly flow.

---

## 🚀 CORE SYSTEM MODULES (with your new additions)

---

### 1. 🔁 COO DAILY COMMAND DASHBOARD

> Mobile + Web optimized. Loads instantly with **daily brief**.

#### Shows:

* 🔔 **Smart Notifications** (grouped, colour-coded by urgency)
* 📋 **Today’s Tasks**
* 🧠 **AI Insights & Suggestions** (more below)
* 🛠️ **Open Jobs Snapshot** (FNO, WISP, civil support)
* 🧾 **Pending Approvals**
* 💬 **New Internal Messages**
* 📦 **Stock Warnings / Low Inventory**
* 📅 **Events Today / Tomorrow**
* 🎤 **Voice Note Inbox → Tasks**

#### AI-Powered Memory Aid:

* “Remind me again why we delayed Tower 7 repairs?”
* → Shows task history, linked messages, decisions.

---

### 2. 🎤 VOICE-TO-TASK/JOB INPUT SYSTEM

> You’re in the field or driving — speak and it captures the job.

#### How it works:

1. You press “Record Task” on mobile.
2. Speech-to-text converts your voice to a draft task/job.
3. AI parses and:

   * Tags it as Job, Task, Meeting Note, Reminder, etc.
   * Links it to existing project/job if relevant.
   * Suggests deadlines or team members.

#### Example:

> “Need to get trenching team to Kabelkop by Friday, 30 meters, fix burst pipe.”

→ Auto-created:

* Job: “Civil Repair – Kabelkop trench”
* Location: Kabelkop
* Deadline: Friday
* Assigned: Civil Team
* Notes: “Fix burst pipe, 30m”

---

### 3. 🤖 AI INSIGHTS ENGINE

Integrated assistant trained on:

* Your historical data (jobs, teams, times)
* Industry patterns
* Your voice/task style

#### Examples:

* **Suggests best team** for job based on past performance
* Warns: “This job sounds similar to last month’s issue at Tower 4”
* Detects repetitive tasks → proposes automation
* “Task open >7 days without reply – suggest escalation?”

✅ Future scope: add ChatGPT plugin access or internal fine-tuned assistant.

---

### 4. 📦 ADVANCED STOCK MANAGEMENT SYSTEM

Now upgraded for:

* 🧭 Two companies: **WISP** and **FNO**
* 💸 Tracks **stock value**, movement, and usage
* 🏷 Labels:

  * "Company Ownership" (WISP or FNO)
  * "Category" (Radio, Fibre, Tools, Civil Materials)
  * "Assigned To" (Team, Site, Job)
  * "Condition" (New, Used, Broken)
  * "Restock Threshold"
* 📥 Issue Logs: what was used, where, when, why
* 🧾 Purchase orders linked to supplier + invoice files
* 💰 Stock Valuation Dashboard:

  * Total value held per company
  * Monthly movement
  * Damaged/lost asset reports

---

### 5. 📧 NOTIFICATION & REMINDER SYSTEM (Non-Overbearing)

> Your **external brain**, but *not annoying*.

#### Core Logic:

* Daily summary email at 07:00: Open tasks, new jobs, unread messages
* Smart re-notifications:

  * Only reminds if no action logged in X hours
  * Escalation notifications based on priority + delays
* Channels:

  * Email
  * In-app
  * Telegram/WhatsApp (optional)
* Calendar-based:

  * Scheduled nudges on deadlines
  * Slack off? It bumps the reminder up based on importance

#### Example:

* “Tower Team has not uploaded job report for Job #112 – 2 days late. Want to nudge them now?”

---

### 6. 📝 ROBUST TODO SYSTEM

More than just a checklist.

#### Features:

* [ ] Checklist mode with subtasks
* ⬆️ Priority tags (High / Medium / Low)
* 🔗 Linked to: Jobs, Notes, Calendar, Civil Jobs, Meeting Notes
* 📎 Attach files/voice notes
* 💬 Add internal chat to each item
* 🗂️ Group by:

  * Today / This Week / Overdue
  * By project
  * By company (WISP/FNO)
* 📱 Works offline (PWA optional)

#### Example:

> “FNO Weekly Ops TODO”

* [x] Approve 400m fibre purchase
* [ ] Confirm trench route at Mamelodi
* [ ] Send update to municipal contact (Remind Tuesday)

---

### 7. 🧾 TASK/PROJECT/JOB CREATION — ULTRA MOBILE-FRIENDLY UI

### Mobile-first creation:

* Big buttons: “+ Task”, “+ Job”, “+ Note”, “+ Voice”
* One-hand input (easy on-site or in bakkie)
* Presets to speed up input:

  * “Assign to Civil”
  * “Urgent + due this week”
  * “Send daily reminder”

✅ All forms have:

* File upload
* Voice support
* Auto-linking to calendar & teams
* Smart suggestions from AI assistant

---

## 🔒 Optional Future Enhancements

| Feature                  | Value                                                         |
| ------------------------ | ------------------------------------------------------------- |
| ONT/OLT Device Sync      | Auto-ping gear, flag unreachable ones                         |
| ICASA Compliance Module  | Store license docs, alert on renewal                          |
| SLA Expiry Tracker       | Warn when 3rd-party SLAs expire                               |
| Budget Module            | Tie civil job expenses + materials to cost centres            |
| PDF Jobcards             | Generate printable job cards for paper-based sites            |
| WhatsApp API Integration | Send stock confirmations or civil check-in links via WhatsApp |

---

## 🛠 NEXT STEPS (You Pick)

Would you like me to:

1. **Design a UI wireframe** flow (HTML+Tailwind or Figma style)?
2. **Scaffold Django models** and admin panels for this spec?
3. **Build Docker starter** project with Celery, Redis, auth, job/task CRUD?

Just say the word, my bru. This is now a full personal **COO operations hub**, not a toy. Let's build it to take pressure off your plate daily.


****