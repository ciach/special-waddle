import asyncio
from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    input_guardrail,
    output_guardrail,
)
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from datetime import datetime
import re

# Load environment variables
load_dotenv()


class AgentCommentOutput(BaseModel):
    comments: str


class TicketGuardrailOutput(BaseModel):
    is_valid_ticket: bool
    reasoning: str


class FinalOutputGuardrail(BaseModel):
    is_clear_for_team: bool
    reasoning: str


# Input guardrail agent
ticket_input_guardrail_agent = Agent(
    name="Ticket Input Guardrail Agent",
    instructions="Check if the input is a valid JIRA ticket description.",
    output_type=TicketGuardrailOutput,
)


@input_guardrail
async def ticket_input_guardrail(
    ctx: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    result = await Runner.run(ticket_input_guardrail_agent, input, context=ctx.context)
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=not result.final_output.is_valid_ticket,
    )


# Output guardrail agent
final_output_guardrail_agent = Agent(
    name="Final Output Guardrail Agent",
    instructions="Check if the final compiled JIRA ticket is clear, actionable, and ready for the team.",
    output_type=FinalOutputGuardrail,
)


async def run_output_guardrail(output):
    result = await Runner.run(final_output_guardrail_agent, output)
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=not result.final_output.is_clear_for_team,
    )


# Define specialist agents
pm_agent = Agent(
    name="PM Agent",
    handoff_description="Project management perspective",
    instructions="Review the JIRA ticket and provide PM-specific comments.",
    output_type=AgentCommentOutput,
)

developer_agent = Agent(
    name="Developer Agent",
    handoff_description="Developer perspective",
    instructions="Review the JIRA ticket and provide developer-specific comments.",
    output_type=AgentCommentOutput,
)

qa_agent = Agent(
    name="QA Agent",
    handoff_description="QA perspective",
    instructions="Review the JIRA ticket and provide QA-specific comments.",
    output_type=AgentCommentOutput,
)

security_agent = Agent(
    name="Security Agent",
    handoff_description="Security perspective",
    instructions="Review the JIRA ticket and provide security-specific comments.",
    output_type=AgentCommentOutput,
)

design_agent = Agent(
    name="Design Agent",
    handoff_description="Design perspective",
    instructions="Review the JIRA ticket and provide design-specific comments.",
    output_type=AgentCommentOutput,
)

AGENT_LIST = [pm_agent, developer_agent, qa_agent, security_agent, design_agent]

jira_master_agent = Agent(
    name="JIRA Ticket Master AI",
    instructions="Transform the JIRA ticket description into a structured format including introduction, user story, acceptance criteria, definition of done, dependencies, and solution steps.",
    input_guardrails=[ticket_input_guardrail],
)


async def orchestrate_ticket(ticket_description):
    print("Running base JIRA Ticket Master AI transformation...")
    try:
        base_result = await Runner.run(jira_master_agent, ticket_description)
        base_ticket = base_result.final_output

        perspective_comments = {}
        for agent in AGENT_LIST:
            print(f"Running {agent.name}...")
            result = await Runner.run(agent, base_ticket)
            comments = result.final_output_as(AgentCommentOutput)
            perspective_comments[agent.name] = comments.comments

        final_ticket = f"{base_ticket}\n\n[perspective_comments]:\n"
        for name, comment in perspective_comments.items():
            final_ticket += f"- [{name}]: {comment}\n"
        final_ticket += "\n[final_notes]: Please review all agent comments before finalizing this ticket in JIRA."

        # Run output guardrail explicitly after compilation
        print("Running final output guardrail check...")
        output_guardrail_result = await run_output_guardrail(final_ticket)
        if output_guardrail_result.tripwire_triggered:
            raise OutputGuardrailTripwireTriggered(
                "Final output guardrail triggered: The compiled ticket is not clear or ready."
            )

        return final_ticket

    except InputGuardrailTripwireTriggered:
        print(
            "Input guardrail triggered: The provided description is not a valid JIRA ticket."
        )
        return None
    except OutputGuardrailTripwireTriggered:
        print(
            "Output guardrail triggered: The final compiled ticket is not clear or ready for the team."
        )
        return None


async def main():
    ticket_description = input("Paste your initial JIRA ticket description here:\n")
    final_output = await orchestrate_ticket(ticket_description)
    if final_output:
        print("\n==== FINAL ENHANCED JIRA TICKET ====")
        print(final_output)

        # Generate filename
        today = datetime.now().strftime("%Y%m%d")
        short_name_match = re.search(
            r"As a .*?, I want to (.*?), so that", ticket_description, re.IGNORECASE
        )
        short_name = (
            short_name_match.group(1).replace(" ", "_").lower()
            if short_name_match
            else "ticket"
        )
        short_name = re.sub(r"[^a-z0-9_]", "", short_name)[:30]
        filename = f"{today}_{short_name}.md"

        # Add front matter
        front_matter = f"""---
title: {short_name.replace('_', ' ').capitalize()}
date: {datetime.now().strftime('%Y-%m-%d')}
summary: JIRA ticket for '{short_name.replace('_', ' ')}'
tags: [jira, ai, automation]
author: AI Agent
---\n\n"""

        with open(filename, "w") as f:
            f.write(front_matter + final_output)

        print(f"\n✅ Ticket saved to {filename}")


if __name__ == "__main__":
    asyncio.run(main())
