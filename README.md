# 🤖 NetBot - Instagram AI Persona

> **Automated Engagement Agent powered by GPT-4o Vision & Agno Framework.**

**NetBot** is an intelligent autonomous agent designed to interact on Instagram by simulating human behavior. Unlike traditional bots that use private APIs (risky) or generic comments, NetBot "looks" at the post, understands the context (caption + image), and generates relevant and authentic comments.

## ✨ Key Features

- **🧠 Multimodal Intelligence (Vision + Text):** Uses `GPT-4o` (via **Agno** framework) to analyze the post's image and caption before interacting.
- **🕵️ Human-Like Navigation (Playwright):**
  - Uses a **real browser** (Chromium) to navigate Instagram.
  - Clicks, types, and scrolls like a human.
  - Maintains **session cookies** to avoid constant logins and suspicion.
- **🎯 Intelligent Hybrid Discovery:**
  - **70% VIP List:** Focuses on high-relevance profiles defined by you.
  - **30% Hashtags:** Explores new content in specific niches.
- **🛡️ Safety & Anti-Ban:**
  - **Daily Limits:** Controlled via database to not exceed safe rates.
  - **Jitter (Random Intervals):** Variable pauses between actions (e.g., 10-50 min) to appear natural.
  - **Duplication Check:** Never interacts with the same post twice.
- **🧠 RAG Memory (Concept Learning):**
  - Remembers past interactions (Vector DB).
  - Learns from your previous comments to maintain a consistent style and opinion.
- **☁️ Supabase Integration:** Stores interaction logs, vector embeddings, daily statistics, and errors in the cloud.

---

## 🏗️ Project Architecture

The project follows a **modular event-driven architecture**, designed to support multiple social platforms with a shared AI brain.

- **`core/agent.py` (The Brain):** Platform-agnostic AI agent. Uses OpenAI/Agno to analyze content and decide on actions, regardless of the source network.
- **`core/interfaces.py` (The Contracts):** Defines abstract base classes (`SocialNetworkClient`, `DiscoveryStrategy`) that all network modules must implement.
- **`core/networks/` (The Limbs):** Contains platform-specific implementations.
  - **`instagram/client.py`:** Controls the browser via Playwright for Instagram.
  - **`instagram/discovery.py`:** Finds candidates on Instagram (VIPs vs Hashtags).
- **`core/database.py` (The Memory):** Manages data persistence in Supabase, tracking interactions across all platforms.
- **`main.py` (The Conductor):** Main loop that orchestrates interaction cycles for all enabled networks.

---

## 🛠️ Technologies

- **Python 3.10+**
- **[Agno Framework](https://github.com/agno-agi/agno):** AI Agent Orchestration.
- **[Playwright](https://playwright.dev/):** Modern and resilient browser automation.
- **[Supabase](https://supabase.com/):** Database (PostgreSQL) as a Service.
- **OpenAI GPT-4o-mini:** Language and vision model.

---

## 🚀 Installation and Usage

### 1. Prerequisites
- Python 3.10+
- OpenAI Account (API Key)
- Supabase Project (URL and Key)

### 2. Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Configure `.env` (use `.env.example` as a base):
   ```bash
   OPENAI_API_KEY=sk-...
   SUPABASE_URL=https://...
   SUPABASE_KEY=ey...
   IG_USERNAME=your_username
   IG_PASSWORD=your_password
   ```

### 3. Customization
- **VIPs:** VIP profile lists and Hashtags are in `config/`.

- **Persona:** 
    - Edit `config/prompts.yaml` to defend your **Bio**, **Traits**, and **Tone**.
    - **RAG Learning:** The bot remembers past interactions and adapts its style to match your previous comments.

### 4. Running
```bash
python main.py
```

> **Note:** By default, the bot may start in `DRY_RUN` mode (simulation only, no real comments). Check `config/settings.py` to adjust.

---

## ⚠️ Disclaimer

This project is for **educational purposes**. Using automation on social networks (bots) violates Instagram's Terms of Service and may lead to your account being blocked. **Use at your own risk.**
