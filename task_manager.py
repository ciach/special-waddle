import os
import re
from datetime import datetime
from pathlib import Path
from agents import Agent, Runner
from pydantic import BaseModel


# Output model
class TaskBreakdown(BaseModel):
    steps: list[str]


# Agent that decomposes high-level requirements
task_decomposer_agent = Agent(
    name="Task Decomposer",
    instructions="Break down the provided JIRA ticket into small, clear technical tasks that make implementation and test case generation easier.",
    output_type=TaskBreakdown,
)


def extract_summary_name(markdown_text):
    title_match = re.search(r"^title:\s*(.+)", markdown_text, re.MULTILINE)
    return (
        title_match.group(1).strip().replace(" ", "_").lower()
        if title_match
        else "ticket"
    )


def insert_task_breakdown(md_text, tasks):
    breakdown_md = "\n[task_breakdown]:\n" + "".join(f"- {step}\n" for step in tasks)
    return md_text.strip() + breakdown_md


async def add_task_breakdown_to_markdown(md_file_path):
    if not os.path.exists(md_file_path):
        print("❌ File not found.")
        return

    with open(md_file_path, "r") as f:
        content = f.read()

    print("🧠 Breaking down tasks from the ticket description...")
    result = await Runner.run(task_decomposer_agent, content)
    task_steps = result.final_output_as(TaskBreakdown).steps

    updated_md = insert_task_breakdown(content, task_steps)

    # Save updated file
    summary_stub = extract_summary_name(content)
    new_file = (
        Path(md_file_path).parent
        / f"{datetime.now().strftime('%Y%m%d')}_{summary_stub}_with_tasks.md"
    )
    with open(new_file, "w") as f:
        f.write(updated_md)

    print(f"✅ Task breakdown saved to {new_file}")


if __name__ == "__main__":
    import asyncio

    path = input("Enter the path to the enhanced JIRA ticket Markdown file:\n")
    asyncio.run(add_task_breakdown_to_markdown(path))
