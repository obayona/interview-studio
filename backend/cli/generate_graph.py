from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr

from backend.interview_engine.graph import InterviewGraph
from backend.interview_engine.models import InterviewConfiguration


def main() -> None:
    output_path = Path(__file__).with_name("graph.png")
    configuration = InterviewConfiguration(job_listing="Interview graph visualization")
    model = ChatOpenAI(
        api_key=SecretStr("not-used-for-graph-generation"),
        model="gpt-4o-mini",
    )
    graph = InterviewGraph(configuration, model, InMemorySaver()).compiled.get_graph()
    graph.draw_mermaid_png(output_file_path=str(output_path))
    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
