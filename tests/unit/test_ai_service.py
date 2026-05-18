import pytest

from app.core.exceptions import AIServiceError
from app.services.ai_service import _validate_mcq_items_with_support


def test_validate_mcq_items_with_support_strips_support_indexes():
    facts = [
        {"type": "fact", "text": "Cells are the basic structural and functional units of life."},
        {"type": "fact", "text": "Scientific investigations rely on observation and evidence."},
    ]
    items = [
        {
            "type": "mcq",
            "question": "What is a central idea in biology?",
            "options": [
                "Cells are the basic structural and functional units of life.",
                "Energy is unnecessary for organisms.",
                "Organisms do not respond to environments.",
                "Science ignores evidence.",
            ],
            "answer": "Cells are the basic structural and functional units of life.",
            "explanation": "The supporting fact states that cells are the basic structural and functional units of life.",
            "supporting_fact_indexes": [0],
        }
    ]

    validated = _validate_mcq_items_with_support(items, facts)

    assert validated == [
        {
            "type": "mcq",
            "question": "What is a central idea in biology?",
            "options": [
                "Cells are the basic structural and functional units of life.",
                "Energy is unnecessary for organisms.",
                "Organisms do not respond to environments.",
                "Science ignores evidence.",
            ],
            "answer": "Cells are the basic structural and functional units of life.",
            "explanation": "The supporting fact states that cells are the basic structural and functional units of life.",
        }
    ]


def test_validate_mcq_items_with_support_rejects_out_of_range_indexes():
    facts = [{"type": "fact", "text": "Cells are the basic structural and functional units of life."}]
    items = [
        {
            "type": "mcq",
            "question": "What is a central idea in biology?",
            "options": [
                "Cells are the basic structural and functional units of life.",
                "Energy is unnecessary for organisms.",
                "Organisms do not respond to environments.",
                "Science ignores evidence.",
            ],
            "answer": "Cells are the basic structural and functional units of life.",
            "explanation": "The supporting fact states that cells are the basic structural and functional units of life.",
            "supporting_fact_indexes": [1],
        }
    ]

    with pytest.raises(AIServiceError):
        _validate_mcq_items_with_support(items, facts)
