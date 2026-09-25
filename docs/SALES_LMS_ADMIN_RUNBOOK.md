# Sales LMS Admin Runbook

## Purpose

This runbook explains how **Team Admins** use the Sales LMS web app for everyday work: people and teams, batches, learner enrollment, progress, analytics, and newsletters. Steps use the **exact labels, menus, and buttons** in the application.

## Who should use this

- People with the **Team admin** role (`access_tier`: **Admin**) who see **Team & access** in the left sidebar.
- Team Admins who also hold **LMS staff roles** (LMS Moderator, Instructor, or Batch Evaluator) and run batches, courses, and enrollment.

**This runbook is not for Super Admins.** It does not cover Super Admin–only items (for example **Extra team views**, org-wide Super Admin management, **Operations** in Analytics, **Desk**, server deployment, or database work).

## Prerequisites

1. **Account** — Your organization has created your Sales LMS login (work email).
2. **Team admin access** — After login, the left sidebar includes **Team & access**.
3. **LMS staff roles (when needed)** — Many curriculum tasks require an LMS role in addition to Team admin:
   - **Create** on **Batches** / **Courses**: LMS Moderator, Instructor, or Batch Evaluator.
   - **Dashboard** and **Settings** on a batch: LMS Moderator or Batch Evaluator.
   - **Analytics** and **Learner reports**: LMS Moderator, Instructor, Evaluator, System Manager, or (for some reports) Training Manager / Manager.
   - **Add Newsletter**: LMS Moderator, Instructor, Evaluator, or System Manager.
4. **Browser** — Use a supported desktop browser (Chrome or Edge recommended). Most admin workflows are designed for desktop; the left sidebar hides some items on mobile.
5. **URL** — Open your organization’s LMS URL (for example `https://<your-domain>/` or local `http://localhost:8081/`). You are sent to **`/login`** when not signed in.

### Role quick reference

| Sidebar / action | Team admin (`access_tier` Admin) | Also needs LMS staff role? |
|------------------|----------------------------------|----------------------------|
| **Team & access** | Yes | No |
| **Home** (`/dashboard`) | Yes | No |
| **Newsletter** (read **Published Updates**) | Yes | No |
| **Add Newsletter** | — | Yes (Moderator / Instructor / Evaluator / System Manager) |
| **Analytics** | — | Yes (staff / Training Manager per route rules) |
| **Learner reports** | — | Yes (staff / Manager / Training Manager) |
| **Curriculum → Batches** (create / enroll) | Yes (navigate) | Yes (create / batch **Dashboard**) |
| **Curriculum → Courses** (create / edit) | Yes (navigate) | Yes (Moderator / Instructor to **Create**) |

If a button or menu in this runbook is missing, ask your organization’s **Super Admin** to assign the correct LMS role. This runbook does not describe how to grant those roles.

---

## 1. Admin login

### 1.1 Access the LMS

1. Open your LMS URL in the browser.
2. If you are not signed in, the app opens **`/login`**.

> **[Screenshot: Login page with email and password fields]**

### 1.2 Log in

1. Enter your **work email** and **password** (or use your organization’s single sign-on if shown on the login page).
2. Submit the form.
3. After a successful login, you are taken to **Home** at **`/dashboard`**.

**Expected result:** You see the Sales onboarding **Home** page (greeting, progress ring, journey steps) and the left sidebar (for example **Home**, **Team & access**, **Newsletter**, **Curriculum**, etc., depending on your roles).

### 1.3 Log out

1. Click your **profile** area at the **bottom of the left sidebar**.
2. Choose **Log out**.
3. The app returns you to **`/login`**.

**Expected result:** You must sign in again to access admin pages.

**Common issues**

| Issue | What to try |
|--------|-------------|
| Login page loops or “session expired” | Clear site cookies for the LMS domain, then log in again. |
| After login, sidebar missing **Team & access** | Your account is not a Team admin; contact Super Admin. |
| Page is blank after login | Hard refresh (Ctrl+F5). If it persists, report to IT (not an admin self-fix). |

---

## 2. Admin dashboard (Home)

**Where:** Left sidebar → **Home** (`/dashboard`).

### 2.1 What you see

- **Top right (Home header):** **Search** (magnifying glass), **Notifications** (bell, with unread count if any), and a **Home** pill.
- **Banner:** Greeting, current program title, short detail, and overall **Done** percentage.
- **Journey:** Steps for Sales onboarding / CRT progress (Continue opens the relevant course or activity).

> **[Screenshot: Home with Search, Notifications, progress ring, and journey list]**

### 2.2 Navigation overview

| Left sidebar item | Route (typical) | Use |
|-------------------|-----------------|-----|
| **Home** | `/dashboard` | Learner-style home; your entry point after login. |
| **Learner reports** | `/reports` | **Sales CRT · Combined report** — filters, highlights, **Export** (staff / managers). |
| **Voice vivas** | Viva results | Voice viva outcomes (staff / managers). |
| **Team & access** | `/team-access` | Add people, teams, reporting lines (Team admin only). |
| **Analytics** | `/analytics` | Overview, learner progress, certification, feedback. |
| **Newsletter** | `/newspaper` | Published updates; **Add Newsletter** if you are LMS staff. |
| **Library** | Library | Video / library content (Admins and learners). |
| **Curriculum** (flyout) | — | **Courses**, **Programs**, **Batches**, **Quizzes**, **Assignments**, **Programming Exercises** (some items staff-only). |
| **Certificates** | Certified participants | Certificate-related views. |
| **Contact Us** | Email or URL | Support link from settings. |

**Expected result:** You can reach every area your roles allow without using **Desk**.

---

## 3. Create a batch

**Requires:** LMS Moderator, Instructor, or Batch Evaluator (you must see **Create** on the Batches page).

### 3.1 Open Batches

1. Left sidebar → **Curriculum** → **Batches** (`/batches`).
2. Use tabs **All**, **Upcoming**, **Archived**, or **Unpublished** (staff tabs).
3. Optionally filter by **Search by Title**, **Category**, or **Certification**.

> **[Screenshot: Batches list with Create button]**

### 3.2 Start a new batch

1. Click **Create** (top right).
2. Choose **New Batch**.

### 3.3 Fill in **New Batch**

Required and common fields:

| Field | Notes |
|--------|--------|
| **Title** | Display name of the batch. |
| **Start Date** / **End Date** | Batch date range. |
| **Start Time** / **End Time** | Session times. |
| **Timezone** | e.g. `IST (+5:30)`. |
| **Category** | Link to **LMS Category** (create if allowed). |
| **Teams** | Team scope (defaults may apply). |
| **Seat Count** | Optional capacity. |
| **Medium** | Delivery medium (dropdown). |
| **Description** | Required short text. |
| **Instructors** | Required; users with **Batch Evaluator** role. |
| **Batch Details** | Required rich text (editor). |

3. Click **Save**.

**Expected result:** The batch is created. You can open it from the batch list.

### 3.4 Publish and attach courses

1. Open the batch (click its card or title) → **`/batches/<batchName>`**.
2. Open the **Settings** tab (staff on batch).
3. Turn on **Published** — *“Make the batch visible to all users.”*
4. Set dates, **Allow Self Enrollment** if learners may join themselves, **Certification** / **Evaluation** as needed.
5. In **Settings**, use the **Courses** section → **Add** to link courses to the batch.
6. Click **Save** in the batch header (when **Settings** shows **Not Saved**).

**Expected result:** The batch appears under **All** / **Upcoming** for staff and (when published) is visible to learners per team and enrollment rules.

### 3.5 Verify

1. Return to **Curriculum** → **Batches**.
2. Search the **Title** you entered.
3. Open the batch → **Overview** and **Settings** and confirm **Published** and courses.

### 3.6 Optional: **Import Batch** (many batch records)

If **Create** → **Import Batch** is available (same role as create):

1. **Create** → **Import Batch** → **Data Import** for **LMS Batch**.
2. Follow the on-screen import steps (download template, fill rows, upload, submit).

Use this to create **batch definitions**, not learner enrollments.

**Common issues**

| Issue | What to try |
|--------|-------------|
| No **Create** button | You lack LMS Moderator / Instructor / Evaluator; request role from Super Admin. |
| Batch not visible to learners | **Settings** → enable **Published**; check **Teams** and dates. |
| Cannot save **Settings** | Fill required fields (title, dates, times, timezone, description, batch details, instructors). |

---

## 4. Bulk enroll learners

There is **no single “Bulk enroll” button** on the batch page. Use one of the workflows below.

### 4.1 Recommended: prepare people, then enroll in the batch

#### Step A — Ensure learner accounts exist (**Team & access**)

1. **Team & access** → **Add person**.
2. Choose **New account** (work email, first/last name) or **Existing account** (search user).
3. Set role **Learner** (shown as **User** in forms), assign **team(s)**, and save.

Repeat for each learner, or add people in small groups over time.

> **[Screenshot: Team & access — Add person sheet]**

#### Step B — Enroll each learner in the batch

1. **Curriculum** → **Batches** → open the batch.
2. Tab **Dashboard** (requires LMS Moderator or Batch Evaluator on batch).
3. In **Students**, click **Enroll**.
4. In **Enroll a Student**:
   - **Student** — select the user (required).
   - **Payment** — optional link to **LMS Payment**.
5. Click **Submit**.

**Expected result:** The learner appears in the **Students** list with enrollment date and **Progress** %. Confirmation email may send if configured on the batch (**Enrollment Confirmation Email Template** in **Settings**).

#### Step C — Verify

1. **Dashboard** → **Students** → search by name.
2. Click a row to open progress detail.
3. Optional: **Analytics** → **Learner Progress** → filter by batch.

### 4.2 Bulk enroll from CSV (recommended for many learners)

**Requires:** LMS Moderator or Batch Evaluator (batch **Dashboard** tab).

1. Open your batch → **Dashboard** → **Students**.
2. Click **Bulk enroll** (next to **Enroll**).
3. **Download template** or export your [Batch Upload Template](https://docs.google.com/spreadsheets/d/1gSVMjiYiienkozdGutdwwg6NJpb23sFScFK0h8aYro8/edit?usp=sharing) as **CSV** from Google Sheets.
4. **Choose CSV file** — review the preview (errors per row).
5. Options:
   - **Send welcome email to new accounts** — password setup mail for newly created users.
   - **Assign Training Manager reporting line** — CSV **Training Manager** must be an **existing LMS user email** (add them under **Team & access** first). When checked, missing TMs block import with a clear error.
6. Click **Enroll learners**.

**Template columns:** Batch Start, Employee Name, Email ID, Locations, Training Manager.

- **Batch Start** should match the batch start date (use **Download template** on the bulk enroll dialog); a mismatch shows a warning only — enrollment still applies to the batch you opened.
- **Locations** is mapped to a team (department); if no match, the batch’s primary team is used.
- New emails create a **Learner** account, assign team, enroll, and send batch confirmation email (if configured on the batch).
- Learners **already in the batch** are listed as skipped; they are **not enrolled again** and **do not get another email** (TM / team / learner report row can still update).
- **Email:** one enrollment message per **new** batch membership (batch name, courses, TM). New accounts include welcome text when **Send welcome email** is checked. Re-uploading the same CSV does not resend mail to skipped rows.
- **Training Manager alerts:** when a learner is newly enrolled or their TM line changes, the assigned Training Manager gets an **LMS notification** listing those learners and a link to the batch **Dashboard**.

**Expected result:** Summary toast (enrolled / new accounts / skipped). **Students** list refreshes.

### 4.2.1 What Training Managers see

Training Managers (users with learners on an active **Training Manager** reporting line) can:

- Open **Learner reports → Sales CRT** — use the **By batch** tab for a batch-wise list of assigned learners (enrollment date, readiness, links to batch dashboard and report cards). Other tabs show CRT metrics scoped to **their learners**; the Training manager filter defaults to themselves.
- Open a batch where they have assigned learners → **Dashboard** — **Students**, progress, and charts show **only their learners** (no **Bulk enroll** / **Enroll**). A blue banner explains the scoped view.
- Use **Notifications** (bell) after bulk enroll to see which learners were assigned to them in that batch.

### 4.3 High-volume enrollment (LMS Moderator only — Data Import)

If you have **LMS Moderator**, you can import enrollments in bulk via **Import** (profile menu at bottom of sidebar → **Import**, or **Create** → **Import Batch** area uses the same Data Import system).

1. Prepare a spreadsheet from the **LMS Batch Enrollment** import template (Frappe **Data Import** flow: download template when starting an import).
2. Required columns:

| Column (field) | Content |
|----------------|---------|
| **Member** | Learner’s **User** ID (typically login email). |
| **Batch** | Batch ID (internal name) or batch link value as required by the template. |

Optional: **Payment**, **Source**. Do not rely on **Member Name** — it is fetched from the user.

3. Upload the file in **Data Import**, map columns, validate preview rows, and submit the import.
4. Fix any failed rows (wrong email, wrong batch name, duplicate enrollment) and re-import failed lines only.

**Expected result:** Each valid row creates an **LMS Batch Enrollment**; learners show under batch **Dashboard** → **Students**.

### 4.4 If some learners fail

| Symptom | Action |
|---------|--------|
| User not found | Add or fix the account in **Team & access** first; **Member** must match an existing **User**. |
| Duplicate enrollment | Skip or remove duplicate row; user may already be enrolled. |
| Wrong batch | Delete enrollment only if your role allows (batch staff) or enroll again in the correct batch after Super Admin / moderator fixes the wrong one. |
| Import rejected | Open import error log; fix column names and required fields; re-upload. |

> **[Screenshot: Batch Dashboard — Students list and Enroll button]**

---

## 5. Add and manage individual learners

### 5.1 Add a learner (account)

**Team & access** → **Add person** → **New account** or **Existing account** → role **Learner**, teams, optional employee code → save.

**Expected result:** Person appears under **People** and can be enrolled in batches.

### 5.2 View learner details

- **Team & access** → **People** → search → **Edit** (pencil) if **can_edit**.
- **Batch** → **Dashboard** → click student row → progress modal.
- **Analytics** → **Learner Progress** → click a row for detail.
- **Learner reports** → **`/reports`** → search learner → open report card **`/reports/<name>`** if available.

### 5.3 Manage enrollment

- **Add:** Batch **Dashboard** → **Enroll** (section 4).
- **Progress:** Batch **Dashboard** → click student; or **Analytics** → **Learner Progress**.
- **Reporting structure:** **Team & access** → **Reporting lines** → **Add line** (member reports to manager).

**Do not** use Super Admin **Extra team views** tab; Team Admins manage only their assigned teams.

---

## 6. Course and content management (Admin-permitted actions)

### 6.1 Access courses

1. **Curriculum** → **Courses** (`/courses`).
2. Staff see tabs such as **All**, **Created**, etc.; learners see **Enrolled** / **All**.

### 6.2 What Team Admins with LMS roles can do

| Action | Where | Who |
|--------|--------|-----|
| Create course | **Courses** → **Create** → **New Course** | LMS Moderator or Instructor |
| Edit course / lessons | Open course → edit controls on **CourseDetail** / lesson editor | Course instructors / moderators |
| Import course data | **Create** → import options; SCORM import where offered | Moderator / instructor flows |
| Link course to batch | Batch **Settings** → **Courses** → **Add** | Batch staff (Moderator / Evaluator on batch) |
| Quizzes / Assignments / Programming Exercises | **Curriculum** flyout | Staff (`isAdmin` in app — Moderator / Instructor / Evaluator) |

Team Admins **without** Instructor or Moderator roles can **browse** courses and open content they are allowed to see but will **not** see **Create** on **Courses**.

### 6.3 Manage content available to a batch

1. Open batch → **Settings** → **Courses** → **Add** or select rows and remove (trash on selection).
2. Save batch **Settings**.

Live assessments on courses appear on batch **Dashboard** under **Live course assessments** when configured in the course editor (staff workflow).

**Expected result:** Enrolled learners see batch-linked courses in their journey / course list per publish and team rules.

---

## 7. Learner progress

### 7.1 From Analytics (recommended)

1. **Analytics** (`/analytics`).
2. Open section **Learner Progress** (tab nav: **Overview** | **Learner Progress** | **Certification** | **Feedback**).
3. Use:
   - Status chips: **All**, **Certified**, **In progress**, **Not started**
   - **Search by name**
   - Batch dropdown (when batches exist)
4. Click a row for learner detail.

Columns include **Lessons**, **Progress**, **Quiz results**, **Assessments**, **Mock**, **Status**, **Last active**.

**Expected result:** You can answer “where is this learner?” for your batches.

### 7.2 From a batch

Batch → **Dashboard** → **Students** → search → click row.

### 7.3 From Learner reports

**Learner reports** → filter **Training manager**, **Batch code**, **Location** → search learner → drill into bands / report card.

---

## 8. Analytics dashboard

### 8.1 Open Analytics

Left sidebar → **Analytics** → `/analytics`.

> **[Screenshot: Analytics section nav — Overview, Learner Progress, Certification, Feedback]**

### 8.2 Overview

- Cards: **Total learners**, **Active learners**, **Avg progress**, **Certificates issued**, **Total courses**, **Published courses**, **Total batches**.
- Charts: **Lesson completion rate (%)** (course filter), **Certifications issued over time**.

**Expected result:** High-level health of programs.

### 8.3 Learner Progress

See section 7. Pagination: **Previous** / **Next**, page size (10 / 20 / 50).

### 8.4 Certification

Tab **Certification**:

- Issued certificates list.
- **OJT** certification block (embedded **OJT Certification Analytics** for analytics staff): filters and **Export Report** / **Import CSV** for OJT attendance where enabled.

**Expected result:** You can list certified learners and export OJT certification reports when your role includes analytics staff.

### 8.5 Feedback

Tab **Feedback**: lesson-level thumbs up/down by course (select course filter).

### 8.6 Filters and exports

| Area | Filters | Export |
|------|---------|--------|
| **Overview** | Course on charts | — |
| **Learner Progress** | Status, name, batch | Use pagination; no global CSV on this table |
| **Certification** | OJT filters (embedded) | **Export Report** |
| **Learner reports** | Manager, batch code, location, search | **Export** (CSV) |

**Note:** Tab **Operations** appears only for LMS Moderator / System Manager. It is **not** part of this Team Admin runbook.

---

## 9. Newsletter (announcements)

### 9.1 View history

1. **Newsletter** (`/newspaper`).
2. Section **Published Updates** lists past items (title, image, date, status e.g. **Sent**).

Learners see updates here; they do not see **Add Newsletter** unless they are staff.

### 9.2 Create and send (LMS staff)

1. **Newsletter** → **Add Newsletter** → **Create Newsletter**.
2. Fill **Title** (required).
3. **Image** → **Upload Image** (PNG, JPG, WEBP up to 5 MB) or **Remove**.
4. **Message** (required rich text; character count vs limit shown).
5. **Send To**:
   - **All Learners**
   - **Select Batch** — check one or more batches
   - **Select Members** — **Learners** multi-select
6. Check **Recipients** count.
7. Review **Preview** (right panel).
8. Click **Send Newsletter** → **Confirm Send** → **Confirm & Send**.

**Expected result:** Toast: newsletter sent; recipient count shown. Item appears under **Published Updates** with status **Sent**.

### 9.3 Batch-specific announcements (alternative)

On a batch, staff menu (⋯) → **Make an Announcement** (when learners exist and you are Moderator / Evaluator) — batch-scoped, not the full **Newsletter** email.

> **[Screenshot: Create Newsletter with Preview and Send To options]**

---

## 10. Common admin tasks (quick reference)

| Task | Steps |
|------|--------|
| **Search learner** | Home → **Search**; or **Team & access** → **Search people**; or **Analytics** → **Learner Progress** → **Search by name**; or **Learner reports** search box. |
| **Filter by batch** | **Analytics** → **Learner Progress** → batch dropdown; **Learner reports** → **Batch code**. |
| **Check enrollment** | Batch **Dashboard** → **Students**; metric **Enrolled** on dashboard. |
| **Check progress** | Batch **Dashboard** (row / modal) or **Analytics** → **Learner Progress**. |
| **Export reports** | **Learner reports** → **Export**; **Analytics** → **Certification** → **Export Report**. |
| **Add team member** | **Team & access** → **Add person**. |
| **Assign manager** | **Team & access** → **Reporting lines** → **Add line**. |

---

## 11. Troubleshooting

| Problem | Likely cause | What to do |
|---------|----------------|------------|
| **Learner not appearing** | No user account or wrong team | **Team & access** → confirm person exists and team; then enroll in batch. |
| **Bulk enrollment failure** | Bad emails, wrong batch ID, duplicate rows | Fix spreadsheet; use **Member** = exact user email; verify **Batch** ID; re-import failed rows only. |
| **Learner in wrong batch** | Wrong batch selected at enroll | Enroll in correct batch; ask moderator to remove wrong enrollment if needed. |
| **Batch not visible** | Unpublished or wrong tab | **Settings** → **Published**; check **Unpublished** / **Upcoming** tabs on **Batches**. |
| **Content not visible** | Course not linked or unpublished | Batch **Settings** → **Courses**; course publish/upcoming flags in course editor (staff). |
| **Email / notification not received** | Template not set, spam, wrong email | Batch **Enrollment Confirmation Email Template**; verify user email in **Team & access**; learner checks **Notifications** bell on **Home**. |
| **Report / export empty** | Filters too narrow or no data | Reset filters to **All**; widen batch/manager filters; retry **Export** after data loads. |
| **Cannot open Team & access** | Not Team admin | Super Admin must set **Team admin** access tier. |
| **Cannot open Analytics** | Not staff / Training Manager | Request LMS Moderator or Training Manager role as appropriate. |

---

## Document control

| Item | Value |
|------|--------|
| Audience | Team Admin (`access_tier` Admin), excluding Super Admin procedures |
| App areas referenced | Home `/dashboard`, Team & access, Curriculum, Batches, Analytics `/analytics`, Newsletter `/newspaper`, Learner reports `/reports`, Login `/login` |
| Last aligned to codebase | Sales LMS frontend sidebar, batch, analytics, and newsletter UI |

For infrastructure, deployment, or Super Admin configuration, use internal IT / DevOps documentation—not this runbook.
