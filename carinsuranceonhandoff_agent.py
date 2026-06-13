import asyncio
import dotenv

from agents import Agent, Runner, handoff, function_tool, RunContextWrapper
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from pydantic import BaseModel


dotenv.load_dotenv()

# ─────────────────────────────────────────────
# 1.  Mock Policy Database
# ─────────────────────────────────────────────
POLICY_DATABASE = [
    {
        "username": "Alice Johnson",
        "policy_no": "POL-1001",
        "policy_amount": 50000,
        "next_due_date": "2026-08-15",
        "next_due_amount": 1200,
    },
    {
        "username": "Smita Roy",
        "policy_no": "POL-1002",
        "policy_amount": 75000,
        "next_due_date": "2026-07-01",
        "next_due_amount": 1800,
    },
    {
        "username": "Carol White",
        "policy_no": "POL-1003",
        "policy_amount": 30000,
        "next_due_date": "2027-09-20",
        "next_due_amount": 900,
    },
    {
        "username": "Saikat Banerjee",
        "policy_no": "POL-1004",
        "policy_amount": 100000,
        "next_due_date": "2027-06-30",
        "next_due_amount": 2500,
    },
    {
        "username": "Eva Martinez",
        "policy_no": "POL-1005",
        "policy_amount": 60000,
        "next_due_date": "2026-10-05",
        "next_due_amount": 1500,
    },
]


class TransferData(BaseModel):
    reason: str


@function_tool
def get_policy_by_username(username: str) -> str:
    """
    Retrieve policy details for a customer by their full name.
    Returns policy number, policy amount, next due date, and next due amount.
    If the customer is not found, returns a not-found message.
    """
    for policy in POLICY_DATABASE:
        if policy["username"].lower() == username.lower().strip():
            return (
                f"Policy found for {policy['username']}:\n"
                f"  Policy No     : {policy['policy_no']}\n"
                f"  Policy Amount : ${policy['policy_amount']:,}\n"
                f"  Next Due Date : {policy['next_due_date']}\n"
                f"  Due Amount    : ${policy['next_due_amount']:,}"
            )
    return f"No policy found for username '{username}'. Please verify the name and try again."


async def on_handoff(ctx: RunContextWrapper[None], input_data: TransferData):
    print(f"Renewal agent called with reason: {input_data.reason}")


# ─────────────────────────────────────────────
# 2.  Renewal Agent
# ─────────────────────────────────────────────
renewal_agent = Agent(
    name="Renewal Agent",
    handoff_description=(
        "Specialist for policy renewals and price negotiations. "
        "Handles renewal discussions, discount requests, and renewal quotes."
    ),
    instructions=f"""
                    {RECOMMENDED_PROMPT_PREFIX}
                    You are a Renewal Specialist at SFDC Chronicle. You handle everything
                    related to policy renewals and price negotiations.
                    Your responsibilities:
                    - Explain renewal terms and options to the customer.
                    - Offer loyalty discounts (up to 10 %) for long-standing customers.
                    - Negotiate renewal premiums within ±15 % of the listed due amount.
                    - Present renewal packages (Basic / Standard / Premium).
                    - Escalate only if the requested discount exceeds 20 %.

                    Always be empathetic, professional, and solution-oriented.
                    If the customer wants to check plain policy/amount info (not renewal),
                    let them know you can help but that general queries go to Customer Care.
    """,
)


handoff_obj = handoff(
    agent=renewal_agent,
    on_handoff=on_handoff,
    input_type=TransferData,
)
# ─────────────────────────────────────────────
# 3.  Customer Care Agent  (entry point)
# ─────────────────────────────────────────────
customer_care_agent = Agent(
    name="Customer Care Agent",
    instructions=f"""
                    {RECOMMENDED_PROMPT_PREFIX}
                    You are a Customer Care Representative at SFDC Chronicle.
                    You first fetch policy details by calling a tool get_policy_by_username.
                    Your responsibilities:
                    - Look up and provide policy details (policy number, policy amount,
                    next due date, next due amount) for any customer by name or policy number.
                    - Answer general questions about the policy.
                    - If the customer asks about RENEWAL, wants to RENEW their policy,
                    or wants to NEGOTIATE the renewal price → hand off to the Renewal Agent.

                    Rules:
                    - Be friendly, clear, and concise.
                    - Never fabricate policy data; use only the records listed above.
                    - If the customer isn't found, apologise and ask them to verify their details.
                    - Do NOT attempt to negotiate prices yourself — that's the Renewal Agent's job.
    """,
    tools=[get_policy_by_username],
    handoffs=[handoff_obj]
)


async def main():
    # user_input = 'What is Alice Johnson policy amount?'
    user_input = 'Alice Johnson wants to negotiate the insurance amount for next renewal?'
    result = await Runner.run(customer_care_agent, input=user_input)
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
