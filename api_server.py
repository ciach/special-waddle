from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import asyncio

# Import your existing logic
import main as main_module
import task_manager as task_manager_module
import test_generator as test_generator_module

app = FastAPI()

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request/Response Models ---
class TicketInput(BaseModel):
    ticket_description: str

class MarkdownInput(BaseModel):
    markdown_content: str

# --- Endpoints ---
@app.post("/main")
async def run_main(input: TicketInput):
    try:
        result = await main_module.orchestrate_ticket(input.ticket_description)
        if result is None:
            raise HTTPException(status_code=400, detail="Ticket processing failed or input was invalid.")
        return {"output": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/task-manager")
async def run_task_manager(input: MarkdownInput):
    try:
        # Reuse the logic but adapt for in-memory content (not file I/O)
        content = input.markdown_content
        result = await main_module.Runner.run(task_manager_module.task_decomposer_agent, content)
        task_steps = result.final_output_as(task_manager_module.TaskBreakdown).steps
        breakdown_md = "\n[task_breakdown]:\n" + "".join(f"- {step}\n" for step in task_steps)
        updated_md = content.strip() + breakdown_md
        return {"output": updated_md, "tasks": task_steps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test-generator")
async def run_test_generator(input: MarkdownInput):
    try:
        content = input.markdown_content
        name_stub = test_generator_module.extract_summary_name(content)
        # Task breakdown
        result = await main_module.Runner.run(test_generator_module.task_decomposer_agent, content)
        task_steps = result.final_output_as(test_generator_module.TaskBreakdown).steps
        ticket_content = test_generator_module.insert_task_breakdown(content, task_steps)
        # Clarity check
        try:
            clarity_result = await test_generator_module.clarity_output_guardrail(
                None, None, ticket_content, ticket_content
            )
            if clarity_result.tripwire_triggered:
                ticket_content += "\n\n// WARNING: Ticket was marked unclear. Some test cases below may need manual revision.\n"
        except test_generator_module.OutputGuardrailTripwireTriggered:
            ticket_content += "\n\n// WARNING: Ticket was marked unclear. Some test cases below may need manual revision.\n"
        # Generate tests for each agent
        outputs = {}
        for key, agent in test_generator_module.AGENTS.items():
            result = await main_module.Runner.run(agent, ticket_content)
            test_output = result.final_output_as(test_generator_module.TestOutput)
            outputs[key] = test_output.test_code
        return {"outputs": outputs, "tasks": task_steps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/")
def read_root():
    return {"status": "API running"}
