<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com/?center=true&vCenter=true&width=800&height=80&lines=Infotainment+Accessibility+Analyzer+%F0%9F%9B%A0;Detect+and+Fix+WCAG+2.2+Violations;Powered+by+Multiple+LLMs+(GPT-4o,+Claude,+DeepSeek,+LLaMA)" alt="Typing SVG">
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/mohamedsemah/a11y-evaluator?style=for-the-badge" alt="Stars">
  <img src="https://img.shields.io/github/forks/mohamedsemah/a11y-evaluator?style=for-the-badge" alt="Forks">
  <img src="https://img.shields.io/github/issues/mohamedsemah/a11y-evaluator?style=for-the-badge" alt="Issues">
  <img src="https://img.shields.io/github/license/mohamedsemah/a11y-evaluator?style=for-the-badge" alt="License">
</p>

---

# 🚘 Infotainment Accessibility Analyzer

A next-generation web-based tool that leverages cutting-edge large language models to detect and remediate **WCAG 2.2** accessibility violations in **infotainment system codebases** (HTML, JSX, XML, etc). Designed for researchers, developers, and accessibility auditors.

### 🔥 Key Features
- 🌐 **Multi-model support**: GPT-4o, Claude Opus 4, DeepSeek-V3, LLaMA Maverick
- 🧠 **LLM-powered analysis**: Prompt-engineered detection & remediation
- ♿ **WCAG 2.2 compliance**: Covers perceivable, operable, understandable, robust categories
- 🧾 **PDF reports & remediation ZIP exports**
- 🧰 **UI preview of violations** simulating infotainment displays
- 📊 **LLM performance comparison dashboard**

---

## ✨ Demo Preview

![Preview](https://github.com/mohamedsemah/a11y-evaluator/blob/main/docs/demo.gif?raw=true)

---

## 🧩 Architecture

```mermaid
graph TD;
  User[User Uploads Code/Screenshots]
  User --> Frontend
  Frontend --> Backend[FastAPI Backend]
  Backend --> LLMClients[LLM APIs (OpenAI, Claude, DeepSeek, Replicate)]
  Backend --> Analyzer[WCAG Analyzer + Static Rules]
  Analyzer --> Results[Issues JSON]
  Backend --> ReportGen[PDF/ZIP Generator]
  Frontend --> UI[React Dashboard + Modals + Previews]
```

---

## 🚀 Getting Started

### Prerequisites
- Node.js >= 16
- Python >= 3.10
- API Keys: OpenAI, Anthropic, DeepSeek, Replicate

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt

# Create a .env file with API keys
cp .env.example .env

# Start server
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run start
```

---

## 📦 Output Formats
- ✅ **PDF Report**: With visual charts and executive summary
- ✅ **ZIP Archive**: Fixed versions of uploaded code files

---

## 📁 Folder Structure

```
📦a11y-evaluator
 ┣ 📂backend
 ┃ ┣ main.py         # FastAPI logic
 ┃ ┣ llm_clients.py  # GPT/Claude/DeepSeek/Replicate clients
 ┃ ┣ wcag_analyzer.py
 ┃ ┣ code_processor.py
 ┃ ┣ report_generator.py
 ┣ 📂frontend
 ┃ ┣ App.js          # React main logic
 ┃ ┣ index.css       # Tailwind + UI
 ┃ ┣ tailwind.config.js
 ┗ 📜 README.md
```

---

## 🧪 Supported Models

| Model | Detection | Fixing | Notes |
|-------|-----------|--------|-------|
| GPT-4o | ✅ | ✅ | High accuracy |
| Claude Opus 4 | ✅ | ✅ | Strong context |
| DeepSeek-V3 | ✅ | ✅ | Code focused |
| LLaMA Maverick | ✅ | ✅ | Alternative view |

---

## 📘 WCAG 2.2 Guidelines Covered
- ✅ Non-text content
- ✅ Contrast and color
- ✅ Keyboard navigation
- ✅ Focus order
- ✅ Semantic markup
- ✅ Motion/timing issues
- ✅ Form labeling and instructions

---

## 📜 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙌 Acknowledgments
- OpenAI, Anthropic, DeepSeek, Replicate
- Web Content Accessibility Guidelines (W3C)
- Infotainment UI testers and accessibility reviewers

---

<p align="center">
  <img src="https://media.giphy.com/media/QBd2kLB5qDmysEXre9/giphy.gif" width="300" />
  <br/>
  <b>Make infotainment systems accessible for everyone 🚗✨</b>
</p>
