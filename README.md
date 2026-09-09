\# OpsPulse



\## AI Project Update Copilot



OpsPulse converts free-form employee project updates into a structured manager view with actionable information, risk signals, blockers, dependencies, and clarification requirements.



\## Live Demo



https://opspulse-1-s7cn.onrender.com



\## Features



\- AI-powered project update analysis

\- Progress extraction

\- Next-step identification

\- Blocker detection

\- Dependency detection

\- Risk-level classification

\- Confidence scoring

\- Manager-focused summaries

\- Ambiguous blocker detection

\- Clarification requests

\- Deterministic validation after AI analysis

\- Groq AI integration

\- Responsive web interface



\## How It Works



Employee Project Update

&#x20;       ↓

&#x20;    Flask API

&#x20;       ↓

&#x20;     Groq AI

&#x20;       ↓

&#x20;Structured JSON Analysis

&#x20;       ↓

&#x20; Validation Gate

&#x20;       ↓

&#x20;  Manager View



\## Project Status Classification



OpsPulse supports five project statuses:



\- In Progress

\- Blocked

\- Investigating

\- Needs Clarification

\- Completed



Risk levels:



\- Low

\- Medium

\- High



\## Validation Logic



OpsPulse does not automatically treat every mention of a blocker as a confirmed blocker.



For example:



"The missing credentials might block deployment."



This is treated as a potential blocker and requires clarification.



Whereas:



"The deployment is currently blocked because production credentials are unavailable."



This is treated as a confirmed blocker with high risk.



The deterministic validation gate runs after the AI analysis to prevent ambiguous situations from being incorrectly classified as confirmed blockers.



\## Tech Stack



\### Backend



\- Python

\- Flask

\- Groq API

\- python-dotenv



\### Frontend



\- HTML

\- CSS

\- JavaScript



\### AI



\- Groq

\- openai/gpt-oss-20b



\### Deployment



\- Render



\## Project Structure



OpsPulse/

├── app.py

├── .gitignore

├── requirements.txt

├── static/

│   ├── script.js

│   └── style.css

└── templates/

&#x20;   └── index.html



\## Running Locally



Clone the repository:



git clone https://github.com/ErrabelliSathvik/OpsPulse.git



cd OpsPulse



Create a virtual environment:



python -m venv venv



Activate it on Windows:



venv\\Scripts\\activate



Install dependencies:



pip install -r requirements.txt



Create a `.env` file:



GROQ\_API\_KEY=your\_groq\_api\_key



Start the application:



python app.py



Then open:



http://127.0.0.1:5000



\## Security



API keys are stored using environment variables and should never be committed to Git.



The `.env` file is excluded through `.gitignore`.



\## Example



Input:



"The API integration is completed and all planned testing has passed. The feature is ready for deployment tomorrow."



Output:



Status: Completed



Risk Level: Low



Progress: API integration completed and testing passed.



Next Step: Deploy the feature tomorrow.



Blockers: None



Dependencies: None



\## Purpose



OpsPulse is designed to reduce the manual effort required to interpret inconsistent project updates and provide managers with a concise, standardized view of project status and potential risks.

