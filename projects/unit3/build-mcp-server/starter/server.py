#!/usr/bin/env python3
"""
Module 1: Basic MCP Server - Starter Code

"""
# 测试MCP服务是否有用

import json
import subprocess
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
import os

# Initialize the FastMCP server
mcp = FastMCP("pr-agent")

# PR template directory (shared across all modules)
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

# Default PR templates
DEFAULT_TEMPLATES = {
    "bug.md": "Bug Fix",
    "feature.md": "Feature",
    "docs.md": "Documentation",
    "refactor.md": "Refactor",
    "test.md": "Test",
    "performance.md": "Performance",
    "security.md": "Security"
}

# Type mapping for PR templates
TYPE_MAPPING = {
    "bug": "bug.md",
    "fix": "bug.md",
    "feature": "feature.md",
    "enhancement": "feature.md",
    "docs": "docs.md",
    "documentation": "docs.md",
    "refactor": "refactor.md",
    "cleanup": "refactor.md",
    "test": "test.md",
    "testing": "test.md",
    "performance": "performance.md",
    "optimization": "performance.md",
    "security": "security.md"
}



# Example structure for a tool:
# @mcp.tool()
# async def analyze_file_changes(base_branch: str = "main", include_diff: bool = True) -> str:
#     """Get the full diff and list of changed files in the current git repository.
#     
#     Args:
#         base_branch: Base branch to compare against (default: main)
#         include_diff: Include the full diff content (default: true)
#     """
#     # Your implementation here
#     pass


# Minimal stub implementations so the server runs


@mcp.tool()
async def analyze_file_changes(
    base_branch: str = "main", 
    include_diff: bool = True,
    max_diff_lines: int = 500,
    working_directory: Optional[str] = None
    ) -> str:
    """Get the full diff and list of changed files in the current git repository.
    
    Args:
        base_branch: Base branch to compare against (default: main)
        include_diff: Include the full diff content (default: true)
    """
    # TODO: Implement this tool
    # IMPORTANT: MCP tools have a 25,000 token response limit!
    # Large diffs can easily exceed this. Consider:
    # - Adding a max_diff_lines parameter (e.g., 500 lines)
    # - Truncating large outputs with a message
    # - Returning summary statistics alongside limited diffs
    
    # NOTE: Git commands run in the server's directory by default!
    # To run in Claude's working directory, use MCP roots:
    # context = mcp.get_context()
    # roots_result = await context.session.list_roots()
    # working_dir = roots_result.roots[0].uri.path
    # subprocess.run(["git", "diff"], cwd=working_dir)

    try:
        # Try to get working directory from root first
        if working_directory is None:
            try:
                context = mcp.get_context()
                roots_result = await context.session.list_roots()
                # Get the first root - Claude Code sets this to the CWD
                root  = roots_result.roots[0]
                # FileUrl object has a .path property that gives us the path directly
                working_directory = root.uri.path
            except Exception:
                pass
    
        # Use provided working directory or current directory
        cwd = working_directory if working_directory else os.getcwd()

        # Debug output
        debug_info = {
            "provided_working_directory": working_directory,
            "actual_cwd": cwd,
            "server_process_cwd": os.getcwd(),
            "server_file_location": str(Path(__file__).parent),
            "roots_check": None
        }

        


        # Add roots debug info
        try:
            context = mcp.get_context()
            roots_result = await context.session.list_roots()
            debug_info["roots_check"] = {
                "found": True,
                "count": len(roots_result.roots),
                "roots":[str(root.uri) for root in roots_result.roots]
            }
        except Exception as e:
            debug_info["roots_check"] = {
                "found": False,
                "error":str(e)
            }
        
        # 添加分支检测,允许直接修改主分支并比较修改内容
        current_branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=cwd
        )

        current_branch = current_branch_result.stdout.strip()

        if current_branch == base_branch:
            # 当前是main分支,直接和远程分支做对比
            comparison_base = f"origin/{base_branch}"
            debug_info["comparison_strategy"] = f"On {base_branch} branch, comparing with origin/{base_branch}"
        else:
            # 在功能分支上，与本地main分支比较
            comparison_base = base_branch
            debug_info["comparison_strategy"] = f"On feature branch '{current_branch}', comparing with {base_branch}"
        
        debug_info["current_branch"] = current_branch
        debug_info["comparison_base"] = comparison_base
        
        # Get list of changed files
        files_result = subprocess.run(
            ["git", "diff", "--name-status", f"{comparison_base}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd
            )
            
        

        # Get diff statistics
        stat_result = subprocess.run(
            ["git", "diff", "--stat", f"{comparison_base}...HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd
        )

        # Get the actual diff if requested
        diff_content = ""
        truncated = False
        if include_diff:
            diff_result = subprocess.run(
                ["git", "diff", f"{comparison_base}...HEAD"],
                capture_output=True,
                text=True,
                cwd=cwd
            )
            diff_lines = diff_result.stdout.split('\n')

            # Check if we need to truncate
            if len(diff_lines) > max_diff_lines:
                diff_content = '\n'.join(diff_lines[:max_diff_lines])
                diff_content += f"\n\n... Output truncated. Showing {max_diff_lines} of {len(diff_lines)} lines ..."
                diff_content += "\n... Use max_diff_lines parameter to see more ..."
                truncated = True
            else:
                diff_content = diff_result.stdout
        
        # Get commit messages for context
        commits_result = subprocess.run(
            ["git", "log", "--oneline", f"{comparison_base}...HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd
        )

        analysis = {
            "base_branch": base_branch,
            "files_changed": files_result.stdout,
            "statistics": stat_result.stdout,
            "commits": commits_result.stdout,
            "diff": diff_content if include_diff else "Diff not included (set include_diff=true to see full diff)",
            "truncated": truncated,
            "total_diff_lines": len(diff_lines) if include_diff else 0,
            "_debug": debug_info
        }

        return json.dumps(analysis, indent=2)

    except subprocess.CalledProcessError as e:
        return json.dumps({"error": f"Git error: {e.stderr}"})
    except Exception as e:
        return json.dumps({"error": str(e)})
    
   


@mcp.tool()
async def get_pr_templates() -> str:
    """List available PR templates with their content."""
    templates = [
        {
            "filename": filename,
            "type": template_type,
            "content": (TEMPLATES_DIR / filename).read_text()
        }
        for filename, template_type in DEFAULT_TEMPLATES.items()
    ]

    return json.dumps(templates, indent=2)


@mcp.tool()
async def suggest_template(changes_summary: str, change_type: str) -> str:
    """Let Claude analyze the changes and suggest the most appropriate PR template.
    
    Args:
        changes_summary: Your analysis of what the changes do
        change_type: The type of change you've identified (bug, feature, docs, refactor, test, etc.)
    """
    
    # Get available templates
    templates_response  = await get_pr_templates()
    templates = json.loads(templates_response)

    # Find matching template
    template_file = TYPE_MAPPING.get(change_type.lower(), "feature.md") # 查找字典找到对应的模板
    
    selected_template = next(
        (t for t in templates if t["filename"] == template_file),
        templates[0] # Default to first template if no match
    )

    suggestion = {
        "recommended_template": selected_template,
        "reasoning": f"Based on your analysis: '{changes_summary}', this appears to be a {change_type} change. ",
        "template_content": selected_template["content"],
        "usage_hint": "Claude can help you fill out this template based on the specific changes in your PR."
    }
    return json.dumps(suggestion, indent=2)


if __name__ == "__main__":
    mcp.run()