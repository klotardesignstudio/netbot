# 🤖 Instagram AI Persona (MVP)

**Version:** 1.0 (Alpha - Testnet)  
**Role:** Human Engagement Automation  
**Stack:** Python, Playwright, Agno (Phidata), OpenAI GPT-4o-mini, Supabase.

## 1. Product Overview

**Instagram AI Persona** is an autonomous agent designed to interact (comment) on third-party posts, simulating the behavior, tone of voice, and vision of a specific human user.

Unlike traditional bots that comment based solely on hashtags ("Nice pic!"), this system uses **Multimodal AI (Vision + Text)** to "see" the photo and read the caption, generating contextual comments indistinguishable from a human.

### 🎯 Objectives (KPIs)
*   **Daily Goal:** 10 high-quality interactions (Monday to Friday).
*   **Quality:** 0% generic comments (spam).
*   **Safety:** Keep the account safe by operating within the limits of the unofficial API.

## 2. System Architecture

The data flow follows a linear pipeline with state persistence.

```mermaid
graph TD
    A -->|Trigger| B[1. Discovery]
    B -->|Candidate Post| C[2. Preparation]
    C -->|Full Context| D[3. Brain (Agno Agent)]
    D -->|Structured Output| E[4. Execution (Playwright)]
    E -->|Success| F[5. Persistence (Supabase)]
```

## 3. Step Details (Pipeline)

### 🕵️ Step 1: Discovery (Discovery & Routing)
**Objective:** Select where to interact, balancing networking maintenance and discovering new profiles.

*   **Routing Logic (70/30):**
    *   **70% (VIPs):** Fixed list of ~100 profiles (friends, influencers, leads).
    *   **30% (Discovery):** List of niche Hashtags (e.g., `#pythondev`, `#indiehacker`).
*   **Quality Filters:**
    *   Ignore posts > 3 days old (avoids looking like a stalker).
    *   Ignore private profiles.
    *   Ignore posts already interacted with (Check in SQLite).
    *   **In Hashtags:** Select only "Top Posts" (avoids spam from the "Recent" tab).

### 👁️ Step 2: Preparation (Context Preparation)
**Objective:** Gather necessary information for the Agent.

*   **Input:** `Media` Object (Unified Format).
*   **Visual Context:**
    *   Identify image/cover URL (Agno downloads/processes automatically).
*   **Social Context:**
    *   Download the last 5-10 comments for sentiment analysis.
*   **Textual Context:**
    *   Clean caption (Sanitized).

### 🧠 Step 3: The Brain (AI Core - Agno Agent)
**Objective:** Generate the comment using an Autonomous Agent (Agno Framework). The Agent receives the image and caption, processes it with GPT-4o, and returns a structured output.

*   **Agent (Agno/Phidata):**
    *   Replaces manual OpenAI calls with a structured Agent.
    *   **Model:** `gpt-4o-mini` (Vision/Omni).
*   **Persona & Instructions:**
    *   Maintains tone: Casual, Brazilian Portuguese (or adapted), Brief.
    *   **Centralized Configuration:** All prompts (System Message, rules) are in `config/prompts.yaml` for easy adjustment without touching code.
    *   Instructions injected into the Agent's System Prompt.
*   **Structured Output (Pydantic):**
    *   The Agent does not return loose text. It returns a strict JSON object:
    ```python
    class PostAction(BaseModel):
        should_comment: bool = Field(..., description="Whether to comment or ignore (SKIP)")
        comment_text: str = Field(..., description="The comment text (no hashtags)")
        reasoning: str = Field(..., description="Brief reason for the decision")
    ```
*   **Anti-Blocking Rules (Hard Constraints):**
    *   Forbidden to use hashtags in the response.
    *   Forbidden to ask for follows (CTA).
    *   Maximum of 1 emoji.
    *   Comment on visual elements of the photo (proof of humanity).
*   **Safety Validation:**
    *   If the Agent detects sensitive content (Grief, Tragedy, Extreme Politics), `should_comment` will be `False`.

### 🤖 Step 4: Execution (Playwright)
**Objective:** Perform the action on the platform using a real browser.

*   **Technology:** `Playwright` (Chromium in Headless or Headed mode).
*   **Session Management (Critical):**
    *   Login performed only once.
    *   Session saved in `session.json`.
    *   Subsequent executions reuse cookies/tokens to avoid "Suspicious Login".
*   **Humanization (Jitter):**
    *   **Random Sleep:** Random pause (5s to 15s) between "reading" the post and "commenting".
    *   **Typing simulation:** (backend delay).

### 💾 Step 5: Persistence (Memory)
**Objective:** Avoid duplication and control limits.

*   **Database:** Supabase.
*   **Schema:**
    *   `interaction_log`: Records `post_id`, `username`, `comment_text`, `timestamp`.
    *   `daily_counter`: Controls if the 10 daily interactions limit has been reached.

### 📜 Step 6: Logging & Monitoring
**Objective:** Total traceability of robot actions.

*   **Console (Stdout):** Detailed logs (INFO/DEBUG) to track what the robot is thinking/doing in real-time. E.g., `[INFO] Analyzing Post 123...`, `[DEBUG] SkipReason: Sensitive content`.
*   **File (.log):** Saves the same console logs to `app.log` file for later debugging.
*   **Database:** Supabase (PostgreSQL). Only SUCCESS actions and daily statistics.

## 4. Folder Structure (Suggestion)

```plaintext
/instagram-ai-persona
│
├── /config
│   ├── vip_list.json       # Target user list
│   ├── hashtags.json       # Target tag list
│   └── prompts.yaml        # [NEW] Prompts Center (Persona & Rules)
│
├── /core
│   ├── discovery.py        # Post selection logic
│   ├── brain.py            # OpenAI Integration (GPT-4o)
│   ├── instagram_client.py # Playwright Client (Navigation/Actions)
│   ├── database.py         # SQLite Connection
│   └── logger.py           # [NEW] Log Configuration (Console + File)
│
├── main.py                 # Main file (Orchestrator)
├── requirements.txt        # Dependencies (playwright, openai, etc)
├── .env                    # API Keys (OpenAI, User/Pass)
└── README.md               # This file
```

## 5. Installation Requirements

### Python Dependencies
```bash
pip install playwright openai pillow schedule python-dotenv
playwright install chromium
```

### Environment Variables (.env)
```ini
OPENAI_API_KEY="sk-..."
IG_USERNAME="your_test_account"
IG_PASSWORD="your_test_password"
```

## 6. Risk Management & Limits (Safety)

| Risk | Probability | Implemented Mitigation |
| :--- | :--- | :--- |
| **Shadowban** | Medium | Rigid limit of 10 comments/day. Varied AI-generated content (no repetition). |
| **Login Block** | High | Session reuse (`session.json`). Do not log in/out repeatedly. |
| **Bot Detection** | Medium | Use Vision AI for contextual comments. Random delays (Jitter). |
| **IP Ban** | High (in Cloud) | **Recommendation:** Run locally (your PC) or use Residential 4G Proxy. Never use Datacenter IPs (AWS/DigitalOcean). |