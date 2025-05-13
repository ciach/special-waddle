import os
import re
from datetime import datetime
from pathlib import Path

from agents import (
    Agent,
    Runner,
    GuardrailFunctionOutput,
    OutputGuardrailTripwireTriggered,
    output_guardrail,
    RunContextWrapper,
    TResponseInputItem,
)
from pydantic import BaseModel


# Define output models
class TestOutput(BaseModel):
    test_code: str


class ClarityCheck(BaseModel):
    is_clear: bool
    reasoning: str


class TaskBreakdown(BaseModel):
    steps: list[str]


# Define agents
unit_test_agent = Agent(
    name="Unit Test Generator",
    instructions="Generate unit test cases in TypeScript based on the requirements described in the Markdown input.",
    output_type=TestOutput,
)

integration_test_agent = Agent(
    name="Integration Test Generator",
    instructions="Generate integration test cases for Ember based on the requirements in the Markdown input.",
    output_type=TestOutput,
)

e2e_test_agent = Agent(
    name="E2E Test Generator",
    instructions="Generate end-to-end test cases using Playwright with TypeScript based on the requirements in the Markdown input.",
    output_type=TestOutput,
)

AGENTS = {
    "unit": unit_test_agent,
    "integration": integration_test_agent,
    "e2e": e2e_test_agent,
}

# Guardrail agent
clarity_guardrail_agent = Agent(
    name="Test Clarity Checker",
    instructions="Check if the ticket is clear and complete enough to generate meaningful test cases. If anything is ambiguous, incomplete, or under-specified, flag it.",
    output_type=ClarityCheck,
)

# Task decomposer agent
task_decomposer_agent = Agent(
    name="Task Decomposer",
    instructions="Break down the provided JIRA ticket into small, clear technical tasks that make implementation and test case generation easier.",
    output_type=TaskBreakdown,
)


@output_guardrail
async def clarity_output_guardrail(
    ctx: RunContextWrapper[None],
    agent: Agent,
    input: str | list[TResponseInputItem],
    output: str,
) -> GuardrailFunctionOutput:
    result = await Runner.run(clarity_guardrail_agent, output, context=ctx.context)
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=not result.final_output.is_clear,
    )


def extract_summary_name(markdown_text):
    title_match = re.search(r"^title:\s*(.+)", markdown_text, re.MULTILINE)
    return (
        title_match.group(1).strip().replace(" ", "_").lower()
        if title_match
        else "ticket"
    )


def insert_task_breakdown(md_text, tasks):
    breakdown_md = "\n\n[task_breakdown]:\n" + "".join(f"- {step}\n" for step in tasks)
    return md_text.strip() + breakdown_md


def save_test_output(test_type, name_stub, content):
    outdir = Path("generated_tests")
    outdir.mkdir(exist_ok=True)
    filename = (
        outdir / f"{datetime.now().strftime('%Y%m%d')}_{name_stub}_{test_type}.ts"
    )
    with open(filename, "w") as f:
        f.write(content)
    print(f"✅ Saved {test_type} test to {filename}")


async def generate_tests_from_markdown(markdown_file):
    if not os.path.exists(markdown_file):
        print("❌ File not found.")
        return

    with open(markdown_file, "r") as f:
        ticket_content = f.read()

    name_stub = extract_summary_name(ticket_content)

    # Run task decomposition
    print("🧠 Breaking down tasks from the ticket description...")
    result = await Runner.run(task_decomposer_agent, ticket_content)
    task_steps = result.final_output_as(TaskBreakdown).steps
    ticket_content = insert_task_breakdown(ticket_content, task_steps)

    # Run output clarity check
    print("🔍 Running clarity guardrail check...")
    try:
        clarity_result = await clarity_output_guardrail(
            None, None, ticket_content, ticket_content
        )
        if clarity_result.tripwire_triggered:
            raise OutputGuardrailTripwireTriggered(
                "Ticket requirements are ambiguous or incomplete."
            )
    except OutputGuardrailTripwireTriggered:
        print(
            "⚠️ Guardrail triggered: The ticket content is unclear. Proceeding to generate skeletons for manual completion."
        )
        ticket_content += "\n\n// WARNING: Ticket was marked unclear. Some test cases below may need manual revision.\n"

    for key, agent in AGENTS.items():
        print(f"\n🧪 Generating {key} tests...")
        result = await Runner.run(agent, ticket_content)
        test_output = result.final_output_as(TestOutput)
        save_test_output(key, name_stub, test_output.test_code)


if __name__ == "__main__":
    import asyncio

    input_file = input("Enter the path to the enhanced JIRA ticket Markdown file:\n")
    asyncio.run(generate_tests_from_markdown(input_file))
