import os
import json

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from groq import Groq


# ==========================================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================================

load_dotenv()

app = Flask(__name__)


# ==========================================================
# GROQ CLIENT
# ==========================================================

groq_api_key = os.getenv("GROQ_API_KEY")

client = None

if groq_api_key:
    client = Groq(api_key=groq_api_key)


# ==========================================================
# GROQ AI ANALYSIS
# ==========================================================

def analyze_with_groq(update):

    if not client:
        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    # ======================================================
    # SYSTEM PROMPT
    # ======================================================

    system_prompt = """
You are OpsPulse, an AI project-update copilot.

Your task is to convert an employee's free-form project
update into structured operational information for a manager.

IMPORTANT RULES:

1. Preserve the meaning of the ENTIRE employee update.

2. Do not ignore information appearing after words such as
"but", "however", "although", "because", "if", or "and".

3. Never invent facts.

4. Only use information explicitly contained in the update.

5. Keep these concepts separate:

- Progress
- Blockers
- Dependencies
- Risk
- Investigation
- Uncertainty

6. A dependency is NOT automatically a blocker.

7. A blocker requires clear evidence that progress is
currently prevented.

8. Words such as:

"might"
"may"
"could"
"potential"
"possible"
"might prevent"
"could prevent"
"may prevent"

indicate uncertainty.

9. Potential blockers must NOT be classified as confirmed
blockers.

10. If an update contains an ambiguous potential blocker,
set clarification_needed to true.

11. If clarification is required, blockers must contain
no confirmed blocker unless the employee explicitly states
that progress is currently prevented.

12. If the employee is actively investigating an issue,
do not automatically classify the update as blocked.

13. If the employee is waiting for, depending on, or
requires something from another person, team, or system,
identify that as a dependency.

14. Do not invent an employee name or team.

15. If employee or team information is not provided,
return "Not specified".

16. The progress field must summarize ALL meaningful
progress information from the update.

17. The next_step should be inferred only when reasonably
supported by the update.

18. If no next step is stated or reasonably implied,
return "Not specified".

19. The manager summary must be concise, factual, and
useful to a manager.

20. Confidence represents confidence in the classification
and extraction, NOT confidence that the project will succeed.

21. Ambiguous situations should have lower confidence than
clear confirmed blockers.

22. Do not classify an issue as blocked merely because the
word "block" or "blocked" appears.

23. Examine the complete sentence and surrounding context.

24. If the employee says work is continuing while mentioning
a possible future problem, treat the issue as a potential
risk rather than a confirmed blocker.

25. A statement such as "this might block the release"
means Needs Clarification unless the update separately
states that progress is currently prevented.

26. A statement such as "the credentials are blocking
deployment" is strong evidence of a confirmed blocker.

27. A statement such as "I am waiting for approval" is a
dependency unless the employee explicitly states that work
cannot continue.

28. A statement such as "I am investigating the issue"
should normally be classified as Investigating unless
there is explicit evidence that work is currently blocked.

STATUS OPTIONS:

- In Progress
- Blocked
- Investigating
- Needs Clarification
- Completed

RISK LEVEL OPTIONS:

- Low
- Medium
- High


EXAMPLE 1:

Input:
"The API work is progressing, but this issue might block
the release."

Correct interpretation:

status = "Needs Clarification"

blockers = []

risk_level = "Medium"

clarification_needed = true

The issue is a potential blocker, not a confirmed blocker.


EXAMPLE 2:

Input:
"The deployment is completely blocked because production
credentials are unavailable."

Correct interpretation:

status = "Blocked"

risk_level = "High"

The unavailable production credentials are the blocker.


EXAMPLE 3:

Input:
"The content is almost done but waiting for design review.
If the review arrives by 3 PM, I can ship today."

Correct interpretation:

status = "In Progress"

dependencies should identify design review

blockers = []

The dependency should not automatically be treated as a
confirmed blocker.


EXAMPLE 4:

Input:
"The credentials are blocking deployment, so I cannot
continue."

Correct interpretation:

status = "Blocked"

risk_level = "High"

blockers should identify the credentials/deployment issue.


EXAMPLE 5:

Input:
"I am investigating a database issue, but the rest of the
API work is continuing."

Correct interpretation:

status = "Investigating"

risk_level = "Medium"

Do not classify it as Blocked.


EXAMPLE 6:

Input:
"The feature is completed and successfully deployed."

Correct interpretation:

status = "Completed"

risk_level = "Low"
"""


    # ======================================================
    # STRUCTURED OUTPUT SCHEMA
    # ======================================================

    schema = {
        "type": "object",

        "properties": {

            "employee": {
                "type": "string"
            },

            "team": {
                "type": "string"
            },

            "status": {
                "type": "string",
                "enum": [
                    "In Progress",
                    "Blocked",
                    "Investigating",
                    "Needs Clarification",
                    "Completed"
                ]
            },

            "progress": {
                "type": "string"
            },

            "next_step": {
                "type": "string"
            },

            "blockers": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },

            "dependencies": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },

            "risk_level": {
                "type": "string",
                "enum": [
                    "Low",
                    "Medium",
                    "High"
                ]
            },

            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            },

            "clarification_needed": {
                "type": "boolean"
            },

            "clarification_question": {
                "type": "string"
            },

            "manager_summary": {
                "type": "string"
            }
        },

        "required": [
            "employee",
            "team",
            "status",
            "progress",
            "next_step",
            "blockers",
            "dependencies",
            "risk_level",
            "confidence",
            "clarification_needed",
            "clarification_question",
            "manager_summary"
        ],

        "additionalProperties": False
    }


    # ======================================================
    # GROQ REQUEST
    # ======================================================

    response = client.chat.completions.create(

        model="openai/gpt-oss-20b",

        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": update
            }
        ],

        response_format={
            "type": "json_schema",

            "json_schema": {
                "name": "opspulse_update",
                "strict": True,
                "schema": schema
            }
        },

        temperature=0
    )


    # ======================================================
    # PARSE AI RESPONSE
    # ======================================================

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            "Groq returned an empty response."
        )

    result = json.loads(content)

    return result


# ==========================================================
# VALIDATION GATE
# ==========================================================

def apply_validation_gate(update, result):

    text = update.lower()


    # ======================================================
    # AMBIGUOUS / POTENTIAL BLOCKER PHRASES
    # ======================================================

    ambiguous_phrases = [

        "might block",
        "could block",
        "may block",

        "potential blocker",
        "possible blocker",

        "might prevent",
        "could prevent",
        "may prevent",

        "could become a blocker",
        "might become a blocker",
        "may become a blocker",

        "could be blocked",
        "might be blocked",
        "may be blocked",

        "could cause a blocker",
        "might cause a blocker"
    ]


    # ======================================================
    # EXPLICIT CURRENT BLOCKER PHRASES
    # ======================================================

    clear_blocker_phrases = [

        "currently blocked",
        "completely blocked",

        "blocked and cannot proceed",
        "blocked and unable to proceed",

        "blocked from proceeding",

        "cannot proceed",
        "can't proceed",

        "unable to proceed",
        "unable to continue",

        "cannot continue",
        "can't continue",

        "completely stuck",
        "currently stuck"
    ]


    # ======================================================
    # EXPLICIT BLOCKER CONTEXT
    # ======================================================

    blocker_context_phrases = [

        "blocking progress",
        "blocking the work",
        "blocking development",
        "blocking deployment",
        "blocking the release",

        "preventing progress",
        "preventing the work",
        "preventing deployment",
        "preventing the release"
    ]


    # ======================================================
    # NON-BLOCKING / ACTIVE WORK SIGNALS
    # ======================================================

    non_blocking_phrases = [

        "still progressing",
        "progressing",
        "making progress",

        "work is continuing",
        "work continues",
        "continuing to work",

        "under investigation",
        "investigating",
        "looking into",

        "checking",
        "troubleshooting",

        "rest of the work is continuing",
        "other work is continuing"
    ]


    # ======================================================
    # DETECT CONDITIONS
    # ======================================================

    ambiguous_blocker = any(
        phrase in text
        for phrase in ambiguous_phrases
    )

    explicit_blocker = any(
        phrase in text
        for phrase in clear_blocker_phrases
    )

    blocker_context = any(
        phrase in text
        for phrase in blocker_context_phrases
    )

    non_blocking_context = any(
        phrase in text
        for phrase in non_blocking_phrases
    )


    # ======================================================
    # RULE 1
    #
    # Ambiguous language must NEVER automatically become
    # a confirmed blocker.
    # ======================================================

    if ambiguous_blocker and not explicit_blocker:

        result["status"] = "Needs Clarification"

        result["risk_level"] = "Medium"

        result["clarification_needed"] = True

        result["blockers"] = []

        result["confidence"] = min(
            float(result.get("confidence", 0.70)),
            0.70
        )

        result["clarification_question"] = (
            "Is this issue currently preventing progress, "
            "or is it only a potential risk?"
        )

        result["manager_summary"] = (
            "The update mentions a potential or conditional "
            "blocker, but does not provide enough evidence "
            "that progress is currently prevented. "
            "Manager clarification is required."
        )

        return result


    # ======================================================
    # RULE 2
    #
    # Explicit current blocker.
    # ======================================================

    if explicit_blocker:

        result["status"] = "Blocked"

        result["risk_level"] = "High"

        result["clarification_needed"] = False

        result["clarification_question"] = ""

        result["confidence"] = max(
            float(result.get("confidence", 0.80)),
            0.85
        )

        if not result.get("blockers"):

            result["blockers"] = [
                "Explicit blocker reported by employee"
            ]

        result["manager_summary"] = (
            "The employee explicitly reports that progress "
            "is currently prevented. This is treated as a "
            "confirmed blocker requiring follow-up."
        )

        return result


    # ======================================================
    # RULE 3
    #
    # Blocking context without explicit uncertainty.
    #
    # Example:
    #
    # "The missing credentials are blocking deployment."
    #
    # This is strong evidence of a blocker.
    # ======================================================

    if blocker_context and not ambiguous_blocker:

        result["status"] = "Blocked"

        result["risk_level"] = "High"

        result["clarification_needed"] = False

        result["clarification_question"] = ""

        result["confidence"] = max(
            float(result.get("confidence", 0.80)),
            0.85
        )

        if not result.get("blockers"):

            result["blockers"] = [
                "Current issue is preventing project progress"
            ]

        return result


    # ======================================================
    # RULE 4
    #
    # Active investigation / progress should not remain
    # incorrectly classified as a blocker.
    # ======================================================

    if non_blocking_context and not explicit_blocker:

        if result.get("status") == "Blocked":

            result["status"] = "Investigating"

        if result.get("risk_level") == "High":

            result["risk_level"] = "Medium"

        result["blockers"] = []


    # ======================================================
    # RULE 5
    #
    # Safety consistency.
    #
    # If clarification is required, blockers should not
    # contain confirmed blockers.
    # ======================================================

    if result.get("clarification_needed"):

        result["status"] = "Needs Clarification"

        result["blockers"] = []

        result["risk_level"] = "Medium"

        result["confidence"] = min(
            float(result.get("confidence", 0.70)),
            0.70
        )

        if not result.get("clarification_question"):

            result["clarification_question"] = (
                "Is this issue currently preventing progress, "
                "or is it only a potential risk?"
            )


    # ======================================================
    # RULE 6
    #
    # Never allow a confirmed blocker to remain marked as
    # Low or Medium risk.
    # ======================================================

    if result.get("status") == "Blocked":

        result["risk_level"] = "High"

        result["clarification_needed"] = False

        result["clarification_question"] = ""


    # ======================================================
    # RULE 7
    #
    # Completed work should not require clarification.
    # ======================================================

    if result.get("status") == "Completed":

        result["risk_level"] = "Low"

        result["clarification_needed"] = False

        result["clarification_question"] = ""

        result["blockers"] = []


    return result


# ==========================================================
# MAIN ANALYZER — GROQ AI ONLY
# ==========================================================

def analyze_update(update):

    # ------------------------------------------------------
    # GROQ API KEY CHECK
    # ------------------------------------------------------

    if not client:

        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )


    # ------------------------------------------------------
    # GROQ AI ANALYSIS
    # ------------------------------------------------------

    try:

        result = analyze_with_groq(update)


        # --------------------------------------------------
        # APPLY DETERMINISTIC VALIDATION
        # --------------------------------------------------

        result = apply_validation_gate(
            update,
            result
        )


        # --------------------------------------------------
        # ANALYSIS MODE
        # --------------------------------------------------

        result["analysis_mode"] = "Groq AI"


        return result


    except Exception as error:

        print(
            "Groq analysis failed:",
            error
        )

        raise RuntimeError(
            "Groq AI analysis failed. "
            "Please check your GROQ_API_KEY, "
            "API limits, model availability, "
            "and server logs."
        )


# ==========================================================
# HOME PAGE
# ==========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==========================================================
# ANALYZE ENDPOINT
# ==========================================================

@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze():

    # ------------------------------------------------------
    # READ JSON
    # ------------------------------------------------------

    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({
            "error": "Invalid request."
        }), 400


    # ------------------------------------------------------
    # READ UPDATE
    # ------------------------------------------------------

    update = data.get(
        "update",
        ""
    )


    if not isinstance(update, str):

        return jsonify({
            "error": "Project update must be text."
        }), 400


    update = update.strip()


    # ------------------------------------------------------
    # EMPTY UPDATE
    # ------------------------------------------------------

    if not update:

        return jsonify({
            "error": "Please enter a project update."
        }), 400


    # ------------------------------------------------------
    # LENGTH VALIDATION
    # ------------------------------------------------------

    if len(update) > 5000:

        return jsonify({
            "error": (
                "Project update is too long. "
                "Please keep it under 5000 characters."
            )
        }), 400


    # ------------------------------------------------------
    # ANALYZE USING GROQ AI ONLY
    # ------------------------------------------------------

    try:

        result = analyze_update(
            update
        )

        return jsonify(result), 200


    except RuntimeError as error:

        print(
            "Analysis error:",
            error
        )

        return jsonify({
            "error": str(error)
        }), 500


    except Exception as error:

        print(
            "Unexpected analysis error:",
            error
        )

        return jsonify({
            "error": (
                "An unexpected error occurred "
                "while analyzing the update."
            )
        }), 500


# ==========================================================
# START APPLICATION
# ==========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )