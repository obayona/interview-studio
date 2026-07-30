from __future__ import annotations

from typing import TypedDict, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import SecretStr

from backend.report_engine.models import EvaluationContext, EvaluationReport

SYSTEM_PROMPT = """You are a rigorous interview evaluator.

Evaluate only evidence present in the supplied canonical interview transcript and context.
Use the candidate profile and job context only to judge relevance; never treat them as proof
of an answer. Scores must be integers from 0 to 100 and should be calibrated conservatively.
Every evidence reference and answer observation must use an exact message_id from the input.
Focus on job-related communication, technical knowledge, problem solving, confidence, and
answer relevance. Provide concise, actionable feedback and a prioritized study plan.
Do not invent quotes, facts, or competencies that were not demonstrated."""


class ReportState(TypedDict):
    context: EvaluationContext
    report: EvaluationReport | None


class ReportEngine:
    """A request-scoped, checkpointer-free LangGraph report workflow."""

    def __init__(self, model: BaseChatModel) -> None:
        self._structured_model = cast(
            Runnable[object, object],
            model.with_structured_output(EvaluationReport, method="json_schema"),
        )
        graph = StateGraph(ReportState)
        graph.add_node("evaluate", self._evaluate)
        graph.add_edge(START, "evaluate")
        graph.add_edge("evaluate", END)
        self._graph = graph.compile()

    @classmethod
    def from_openai(cls, api_key: str, model_name: str) -> ReportEngine:
        return cls(
            ChatOpenAI(
                api_key=SecretStr(api_key),
                model=model_name,
                temperature=0,
                timeout=60,
                max_retries=1,
            )
        )

    async def evaluate(self, context: EvaluationContext) -> EvaluationReport:
        result = await self._graph.ainvoke({"context": context, "report": None})
        report = result["report"]
        if report is None:
            raise ValueError("The AI did not return an evaluation report")
        return EvaluationReport.model_validate(report)

    async def _evaluate(self, state: ReportState) -> dict[str, EvaluationReport]:
        context = state["context"]
        result = await self._structured_model.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content="<evaluation_context>\n"
                    f"{context.model_dump_json(indent=2)}\n"
                    "</evaluation_context>"
                ),
            ]
        )
        return {"report": EvaluationReport.model_validate(result)}
