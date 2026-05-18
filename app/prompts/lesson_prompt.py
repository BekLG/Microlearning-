import json


def _fact_example_output() -> str:
    return json.dumps(
        [
            {"type": "fact", "text": "Biology studies living organisms and their interactions with the environment."},
            {"type": "fact", "text": "Cells are the basic structural and functional units of life."},
            {"type": "fact", "text": "Scientific investigations rely on observation, evidence, and repeatable testing."},
        ],
        indent=2,
    )


def _mcq_example_output() -> str:
    return json.dumps(
        [
            {
                "type": "mcq",
                "question": "What is a central idea in introductory biology?",
                "options": [
                    "Life is random",
                    "Cells are basic units of life",
                    "Energy is unnecessary",
                    "Organisms do not change",
                ],
                "answer": "Cells are basic units of life",
                "explanation": "The supporting fact states that cells are the basic units of life.",
                "supporting_fact_indexes": [1],
            }
        ],
        indent=2,
    )


def _format_facts_for_prompt(facts: list[dict]) -> str:
    return "\n".join(f"{idx}. {fact['text']}" for idx, fact in enumerate(facts))


def build_facts_prompt(chunk: str, min_facts: int, max_facts: int) -> str:
    example_output = _fact_example_output()

    return f"""You are creating exam-preparation facts from educational content.

Task:
- Break the content into study facts that cover the chunk thoroughly.

Rules:
- Generate between {min_facts} and {max_facts} facts, using as many as needed to cover the chunk well.
- Aim for roughly 1 fact per 200-300 words of source material.
- Each fact should express exactly one main idea.
- Prioritize definitions, major concepts, main processes, key relationships, and central takeaways.
- At least half of the facts should cover broad concepts rather than minor specifics.
- Avoid niche details unless they directly support a major concept.
- Facts should be factual, standalone, and usually no longer than 25 words.
- Return ONLY a valid JSON array. No markdown, no extra text.

Schema:
  {{"type": "fact", "text": "<string>"}}

Example output:
{example_output}

Content to summarize:
\"\"\"
{chunk}
\"\"\"

JSON array:"""


def build_overview_facts_prompt(text_excerpt: str, min_facts: int, max_facts: int) -> str:
    example_output = _fact_example_output()

    return f"""You are generating big-picture facts for an educational document overview.

Requirements:
- Generate between {min_facts} and {max_facts} fact items.
- Facts must capture the document's major themes, definitions, processes, relationships, and overall purpose.
- Every fact should cover a major idea rather than a narrow detail.
- Facts should be standalone, factual, and usually no longer than 25 words.
- Avoid tiny details, isolated examples, or narrow edge cases.
- Return ONLY a valid JSON array. No markdown, no extra text.

Schema:
  {{"type": "fact", "text": "<string>"}}

Example output:
{example_output}

Document excerpt:
\"\"\"
{text_excerpt}
\"\"\"

JSON array:"""


def build_mcqs_from_facts_prompt(facts: list[dict], mcq_count: int) -> str:
    example_output = _mcq_example_output()
    numbered_facts = _format_facts_for_prompt(facts)

    return f"""You are creating multiple-choice questions from study facts.

Use ONLY the provided facts as evidence.

Requirements:
- Generate exactly {mcq_count} MCQ items.
- Each MCQ must test a key concept covered by the facts.
- Each MCQ must have exactly 4 options, one correct answer, and a short explanation.
- The answer must be one of the option text strings, not a label.
- Every MCQ must include supporting_fact_indexes using 0-based indexes.
- supporting_fact_indexes must contain at least 1 index.
- The correct answer must be directly supported by at least one referenced fact.
- Return ONLY a valid JSON array. No markdown, no extra text.

Schema:
  {{
    "type": "mcq",
    "question": "<string>",
    "options": ["<a>", "<b>", "<c>", "<d>"],
    "answer": "<one of the options>",
    "explanation": "<string>",
    "supporting_fact_indexes": [0]
  }}

Example output:
{example_output}

Facts:
{numbered_facts}

JSON array:"""


def build_overview_mcqs_from_facts_prompt(facts: list[dict], mcq_count: int) -> str:
    example_output = _mcq_example_output()
    numbered_facts = _format_facts_for_prompt(facts)

    return f"""You are creating big-picture multiple-choice questions from overview facts.

Use ONLY the provided overview facts as evidence.

Requirements:
- Generate exactly {mcq_count} MCQ items.
- Each MCQ should test conceptual understanding of the document as a whole.
- Avoid narrow or trivial questions.
- Each MCQ must have exactly 4 options, one correct answer, and a short explanation.
- The answer must be one of the option text strings, not a label.
- Every MCQ must include supporting_fact_indexes using 0-based indexes.
- supporting_fact_indexes must contain at least 1 index.
- The correct answer must be directly supported by at least one referenced fact.
- Return ONLY a valid JSON array. No markdown, no extra text.

Schema:
  {{
    "type": "mcq",
    "question": "<string>",
    "options": ["<a>", "<b>", "<c>", "<d>"],
    "answer": "<one of the options>",
    "explanation": "<string>",
    "supporting_fact_indexes": [0]
  }}

Example output:
{example_output}

Overview facts:
{numbered_facts}

JSON array:"""
