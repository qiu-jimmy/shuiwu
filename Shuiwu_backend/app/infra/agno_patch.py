"""
Monkey patch to fix Agno 2.4.3 bug in AgentSession.from_dict

Bug: When runs is an empty array [], accessing runs[0] causes IndexError
Fix: Check len(runs) > 0 before accessing runs[0]
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def apply_agno_patches():
    """Apply all Agno framework patches"""
    from agno.session import agent

    # Store the original from_dict method
    original_from_dict = agent.AgentSession.from_dict

    @classmethod
    def patched_from_dict(cls, data):
        """Patched version that handles empty runs arrays and None elements"""
        if data is None or data.get("session_id") is None:
            agent.log_warning("AgentSession is missing session_id")
            return None

        runs = data.get("runs")
        serialized_runs = []

        # FIX: Check len(runs) > 0 before accessing runs[0]
        # FIX 2: Skip None elements in runs array
        if runs is not None and len(runs) > 0:
            for run in runs:
                # Skip None elements
                if run is None:
                    agent.log_warning(f"Skipping None run in session {data.get('session_id')}")
                    continue

                # Only process dict elements
                if isinstance(run, dict):
                    if "agent_id" in run:
                        serialized_runs.append(agent.RunOutput.from_dict(run))
                    elif "team_id" in run:
                        serialized_runs.append(agent.TeamRunOutput.from_dict(run))
                else:
                    agent.log_warning(f"Skipping non-dict run: type={type(run)}")

        summary = data.get("summary")
        if summary is not None and isinstance(summary, dict):
            summary = agent.SessionSummary.from_dict(summary)

        metadata = data.get("metadata")

        return cls(
            session_id=data.get("session_id"),
            agent_id=data.get("agent_id"),
            user_id=data.get("user_id"),
            workflow_id=data.get("workflow_id"),
            team_id=data.get("team_id"),
            agent_data=data.get("agent_data"),
            session_data=data.get("session_data"),
            metadata=metadata,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            runs=serialized_runs,
            summary=summary,
        )

    # Apply the patch
    agent.AgentSession.from_dict = patched_from_dict
    print("[Agno Patch] Applied AgentSession.from_dict patch for empty runs arrays")


# Auto-apply on import
apply_agno_patches()
