"""
Async Workflow Orchestrator - Interactive Demo

This demo showcases the key features of the workflow orchestrator:
1. Automatic workflow execution through state machine
2. Manual step-by-step workflow progression
3. Workflow monitoring and history tracking
4. Retry mechanism for failed workflows
5. Multiple concurrent workflows
6. System statistics and resource monitoring
"""
import asyncio
import requests
import time
import json
from typing import Optional, Dict, Any
from datetime import datetime


# API Configuration
BASE_URL = "http://localhost:8000"
COLORS = {
    'HEADER': '\033[95m',
    'BLUE': '\033[94m',
    'CYAN': '\033[96m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'RED': '\033[91m',
    'END': '\033[0m',
    'BOLD': '\033[1m',
}


def print_banner():
    """Print a welcome banner."""
    banner = f"""
{COLORS['CYAN']}{COLORS['BOLD']}
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║         ASYNC WORKFLOW ORCHESTRATOR - INTERACTIVE DEMO             ║
║                                                                    ║
║  Demonstrating modern backend engineering with:                    ║
║  • Async orchestration with asyncio                                ║
║  • Thread-based parallel execution                                 ║
║  • State machine workflow management                               ║
║  • RESTful API with FastAPI                                        ║
║  • Full audit trail and history tracking                           ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
{COLORS['END']}
    """
    print(banner)


def print_section(title: str, color: str = 'BLUE'):
    """Print a formatted section header."""
    width = 70
    print(f"\n{COLORS[color]}{COLORS['BOLD']}")
    print("=" * width)
    print(f"  {title}")
    print("=" * width)
    print(COLORS['END'])


def print_success(message: str):
    """Print a success message."""
    print(f"{COLORS['GREEN']}✓ {message}{COLORS['END']}")


def print_error(message: str):
    """Print an error message."""
    print(f"{COLORS['RED']}✗ {message}{COLORS['END']}")


def print_info(message: str):
    """Print an info message."""
    print(f"{COLORS['CYAN']}ℹ {message}{COLORS['END']}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{COLORS['YELLOW']}⚠ {message}{COLORS['END']}")


def check_server_health() -> bool:
    """Check if the API server is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(response.text)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def start_workflow(name: str, description: str, config: Optional[Dict[str, Any]] = None, auto_start: bool = True) -> Optional[int]:
    """Start a new workflow."""
    payload = {
        "name": name,
        "description": description,
        "config": config or {"priority": "high", "timeout": 300},
        "auto_start": auto_start
    }
    
    try:
        response = requests.post(f"{BASE_URL}/workflow/start", json=payload)
        response.raise_for_status()
        result = response.json()
        
        print_success(f"Workflow Created: ID={result['workflow_id']}, State={result['current_state']}")
        print(f"  Name: {result['name']}")
        print(f"  Status: {result['status']}")
        
        return result['workflow_id']
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to start workflow: {e}")
        return None


def get_workflow_status(workflow_id: int) -> Optional[Dict[str, Any]]:
    """Get current workflow status."""
    try:
        response = requests.get(f"{BASE_URL}/workflow/{workflow_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to get workflow status: {e}")
        return None


def monitor_workflow(workflow_id: int, max_wait: int = 30, show_progress: bool = True) -> Optional[Dict[str, Any]]:
    """Monitor workflow execution until completion."""
    if show_progress:
        print_info(f"Monitoring workflow {workflow_id}...")
    
    start_time = time.time()
    previous_state = None
    
    while time.time() - start_time < max_wait:
        status = get_workflow_status(workflow_id)
        if not status:
            return None
        
        current_state = status['current_state']
        
        # Print state changes
        if show_progress and current_state != previous_state:
            timestamp = datetime.now().strftime('%H:%M:%S')
            state_color = 'GREEN' if status['status'] == 'COMPLETE' else 'YELLOW'
            print(f"{COLORS[state_color]}[{timestamp}] State: {current_state} → Status: {status['status']}{COLORS['END']}")
            previous_state = current_state
        
        # Check if workflow is complete
        if status['status'] in ['COMPLETE', 'FAILED', 'CANCELLED']:
            if status['status'] == 'COMPLETE':
                print_success(f"Workflow {workflow_id} completed successfully!")
            elif status['status'] == 'FAILED':
                print_error(f"Workflow {workflow_id} failed: {status.get('error_message', 'Unknown error')}")
            else:
                print_warning(f"Workflow {workflow_id} was cancelled")
            break
        
        time.sleep(0.5)
    else:
        print_warning(f"Monitoring timeout reached ({max_wait}s)")
    
    return status


def print_workflow_details(workflow_id: int):
    """Print detailed workflow information."""
    status = get_workflow_status(workflow_id)
    if not status:
        return
    
    print(f"\n{COLORS['BOLD']}Workflow Details:{COLORS['END']}")
    print(f"  ID: {status['workflow_id']}")
    print(f"  Name: {status['name']}")
    print(f"  Description: {status['description']}")
    print(f"  Status: {COLORS['GREEN'] if status['status'] == 'COMPLETE' else COLORS['YELLOW']}{status['status']}{COLORS['END']}")
    print(f"  Current State: {status['current_state']}")
    print(f"  Retries: {status['retries']}")
    print(f"  Started: {status['started_at']}")
    print(f"  Completed: {status['completed_at'] or 'N/A'}")
    
    if status.get('error_message'):
        print(f"  Error: {COLORS['RED']}{status['error_message']}{COLORS['END']}")
    
    # Print transition history
    if status.get('transitions'):
        print(f"\n{COLORS['BOLD']}State Transition History:{COLORS['END']}")
        for i, transition in enumerate(status['transitions'], 1):
            print(f"  {i}. {transition['from_state']} → {transition['to_state']} "
                  f"(trigger: {transition['trigger']}) at {transition['created_at']}")
    
    # Print task results
    if status.get('task_results'):
        print(f"\n{COLORS['BOLD']}Task Results by State:{COLORS['END']}")
        for state, result in status['task_results'].items():
            print(f"  {COLORS['CYAN']}{state}:{COLORS['END']}")
            print(f"    {json.dumps(result['result'], indent=6)}")


def trigger_next_step(workflow_id: int) -> bool:
    """Manually trigger the next step."""
    try:
        response = requests.post(f"{BASE_URL}/workflow/{workflow_id}/next")
        response.raise_for_status()
        result = response.json()
        print_success(f"{result['message']} → State: {result['current_state']}")
        return True
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to trigger next step: {e}")
        return False


def retry_workflow(workflow_id: int) -> bool:
    """Retry a failed workflow."""
    try:
        response = requests.post(f"{BASE_URL}/workflow/{workflow_id}/retry")
        response.raise_for_status()
        result = response.json()
        print_success(f"Retry initiated (attempt #{result['retries']}) → State: {result['current_state']}")
        return True
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to retry workflow: {e}")
        return False


def cancel_workflow(workflow_id: int) -> bool:
    """Cancel a workflow."""
    try:
        response = requests.post(f"{BASE_URL}/workflow/{workflow_id}/cancel")
        response.raise_for_status()
        result = response.json()
        print_success(result['message'])
        return True
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to cancel workflow: {e}")
        return False


def get_system_stats():
    """Get and display system execution statistics."""
    try:
        response = requests.get(f"{BASE_URL}/execution/stats")
        response.raise_for_status()
        stats = response.json()
        
        print(f"\n{COLORS['BOLD']}System Statistics:{COLORS['END']}")
        print(f"\n{COLORS['CYAN']}Worker Pool:{COLORS['END']}")
        print(f"  Max Workers: {stats['worker_pool']['max_workers']}")
        print(f"  Active Tasks: {stats['worker_pool']['active_tasks']}")
        print(f"  Queue Size: {stats['worker_pool']['queue_size']}")
        
        print(f"\n{COLORS['CYAN']}Workflows:{COLORS['END']}")
        for status_name, count in stats['workflows'].items():
            print(f"  {status_name.capitalize()}: {count}")
        
        return stats
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to get system stats: {e}")
        return None


def list_workflows():
    """List all workflows."""
    try:
        response = requests.get(f"{BASE_URL}/workflows/")
        response.raise_for_status()
        workflows = response.json()
        
        if not workflows:
            print_info("No workflows found")
            return []
        
        print(f"\n{COLORS['BOLD']}All Workflows:{COLORS['END']}")
        for wf in workflows:
            status_color = 'GREEN' if wf['status'] == 'COMPLETE' else 'YELLOW'
            # print(wf)
            print(f"  [{wf['id']}] {wf['name']} - {COLORS[status_color]}{wf['status']}{COLORS['END']} ({wf['current_state']})")
        
        return workflows
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to list workflows: {e}")
        return []


def demo_automatic_workflow():
    """Demo 1: Automatic workflow execution."""
    print_section("Demo 1: Automatic Workflow Execution", 'HEADER')
    print_info("Starting a workflow that automatically progresses through all states")
    
    workflow_id = start_workflow(
        "Data Processing Pipeline",
        "Demonstrates automatic state progression: INIT → PREPARE → EXECUTE → VALIDATE → COMPLETE"
    )
    
    if workflow_id:
        time.sleep(1)
        final_status = monitor_workflow(workflow_id, max_wait=30)
        
        if final_status:
            print("\n")
            print_workflow_details(workflow_id)
        
        return workflow_id
    return None


def demo_manual_workflow():
    """Demo 2: Manual step-by-step execution."""
    print_section("Demo 2: Manual Step-by-Step Execution", 'HEADER')
    print_info("Starting a workflow and manually triggering each state transition")
    
    workflow_id = start_workflow(
        "Manual Processing Workflow",
        "Demonstrates manual control over workflow progression",
        auto_start=False
    )
    
    if workflow_id:
        time.sleep(2)
        
        print_info("\nManually advancing through states...")
        
        # Trigger each step manually (INIT -> PREPARE -> EXECUTE -> VALIDATE -> COMPLETE)
        states = ['PREPARE', 'EXECUTE', 'VALIDATE', 'COMPLETE']
        for expected_state in states:
            time.sleep(1.5)
            if trigger_next_step(workflow_id):
                status = get_workflow_status(workflow_id)
                if status:
                    print(f"  Current State: {COLORS['CYAN']}{status['current_state']}{COLORS['END']}")
        
        time.sleep(1)
        print("\n")
        print_workflow_details(workflow_id)
        
        return workflow_id
    return None


def demo_concurrent_workflows():
    """Demo 3: Multiple concurrent workflows."""
    print_section("Demo 3: Concurrent Workflow Execution", 'HEADER')
    print_info("Starting multiple workflows simultaneously to demonstrate parallel execution")
    
    workflow_ids = []
    
    # Start multiple workflows
    for i in range(3):
        workflow_id = start_workflow(
            f"Concurrent Workflow #{i+1}",
            f"Parallel execution demo - Workflow {i+1}",
            {"priority": "normal", "worker_id": i+1}
        )
        if workflow_id:
            workflow_ids.append(workflow_id)
        time.sleep(0.3)
    
    print_info(f"\nStarted {len(workflow_ids)} workflows, monitoring completion...")
    
    # Monitor all workflows
    for wf_id in workflow_ids:
        monitor_workflow(wf_id, max_wait=15, show_progress=False)
    
    print_success(f"\nAll {len(workflow_ids)} workflows completed!")
    
    # Show summary
    print(f"\n{COLORS['BOLD']}Summary:{COLORS['END']}")
    for wf_id in workflow_ids:
        status = get_workflow_status(wf_id)
        if status:
            status_symbol = '✓' if status['status'] == 'COMPLETE' else '✗'
            print(f"  {status_symbol} Workflow {wf_id}: {status['name']} - {status['status']}")
    
    return workflow_ids


def inject_failed_workflow() -> Optional[int]:
    """Helper to create a workflow that is guaranteed to fail."""
    print_info("Injecting a failed workflow...")
    return start_workflow(
        "Flaky Workflow",
        "Demonstrates retry mechanism by simulating failure on first attempt",
        config={
            "priority": "high", 
            "simulate_failure": True,
            "fail_until_retry": 1
        }
    )


def demo_retry_mechanism():
    """Demo 4: Workflow retry after failure."""
    print_section("Demo 4: Retry Mechanism", 'HEADER')
    print_info("Starting a workflow configured to fail initially, then succeeding on retry")
    
    # Start workflow with failure simulation
    workflow_id = inject_failed_workflow()
    
    if workflow_id:
        time.sleep(1)
        print_info("Monitoring workflow (expecting failure)...")
        
        # Monitor until failure
        status = monitor_workflow(workflow_id, max_wait=15)
        
        if status and status['status'] == 'FAILED':
            print("\n")
            print_warning(f"Workflow failed as expected: {status.get('error_message')}")
            
            time.sleep(1)
            print_info("Initiating retry...")
            
            # Retry workflow
            if retry_workflow(workflow_id):
                time.sleep(1)
                print_info("Monitoring workflow after retry (expecting success)...")
                monitor_workflow(workflow_id, max_wait=15)
                
                print("\n")
                print_workflow_details(workflow_id)
        else:
            print_warning("Workflow did not fail as expected!")


def demo_system_monitoring():
    """Demo 5: System statistics and monitoring."""
    print_section("Demo 5: System Monitoring & Statistics", 'HEADER')
    
    get_system_stats()
    print("\n")
    list_workflows()


def interactive_menu():
    """Interactive menu for exploring features."""
    print_section("Interactive Mode", 'HEADER')
    
    while True:
        print(f"\n{COLORS['BOLD']}Available Commands:{COLORS['END']}")
        print("  1. Start a new workflow")
        print("  2. Trigger next step")
        print("  3. Cancel a workflow")
        print("  4. Check workflow status")
        print("  5. List all workflows")
        print("  6. View system statistics")
        print("  7. Run all demos")
        print("  0. Exit")
        
        try:
            choice = input(f"\n{COLORS['CYAN']}Enter your choice: {COLORS['END']}").strip()
            
            if choice == '0':
                print_info("Exiting...")
                break
            elif choice == '1':
                name = input("Workflow name: ").strip()
                desc = input("Description: ").strip()
                auto_start_input = input("Auto-start workflow? (y/N): ").strip().lower()
                auto_start = auto_start_input == 'y' or auto_start_input == 'yes'
                start_workflow(name, desc, auto_start=auto_start)
            elif choice == '2':
                wf_id = int(input("Workflow ID: ").strip())
                trigger_next_step(wf_id)
            elif choice == '3':
                wf_id = int(input("Workflow ID: ").strip())
                cancel_workflow(wf_id)
            elif choice == '4':
                wf_id = int(input("Workflow ID: ").strip())
                print_workflow_details(wf_id)
            elif choice == '5':
                list_workflows()
            elif choice == '6':
                get_system_stats()
            elif choice == '7':
                run_all_demos()
            else:
                print_warning("Invalid choice, please try again")
        except KeyboardInterrupt:
            print_info("\nExiting...")
            break
        except Exception as e:
            print_error(f"Error: {e}")


def run_all_demos():
    """Run all demonstration scenarios."""
    print_banner()
    
    # Check server health
    print_info("Checking server connection...")
    if not check_server_health():
        print_error("Cannot connect to API server at " + BASE_URL)
        print_info("Please start the server with: python main.py")
        return
    
    print_success("Connected to server successfully!\n")
    
    # Run demos
    demo_automatic_workflow()
    time.sleep(2)
    
    demo_manual_workflow()
    time.sleep(2)
    
    demo_concurrent_workflows()
    time.sleep(2)
    
    demo_retry_mechanism()
    time.sleep(1)
    
    demo_system_monitoring()
    
    # Final summary
    print_section("Demo Complete!", 'GREEN')
    print(f"{COLORS['GREEN']}{COLORS['BOLD']}")
    print("✓ Automatic state progression demonstrated")
    print("✓ Manual step-by-step execution demonstrated")
    print("✓ Concurrent workflow execution demonstrated")
    print("✓ System monitoring and statistics displayed")
    print("✓ Full workflow history and audit trail shown")
    print(f"{COLORS['END']}")
    
    print(f"\n{COLORS['CYAN']}Key Features Demonstrated:{COLORS['END']}")
    print("  • Async orchestration with asyncio")
    print("  • Thread-based parallel task execution")
    print("  • State machine workflow management")
    print("  • RESTful API with FastAPI")
    print("  • Database persistence with full audit trail")
    print("  • Worker pool resource management")


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--interactive' or sys.argv[1] == '-i':
            print_banner()
            if not check_server_health():
                print_error("Cannot connect to API server at " + BASE_URL)
                print_info("Please start the server with: python main.py")
                return
            print_success("Connected to server successfully!\n")
            interactive_menu()
        elif sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("Usage: python demo.py [OPTIONS]")
            print("\nOptions:")
            print("  (none)        Run all automated demos")
            print("  -i, --interactive   Start interactive mode")
            print("  -h, --help         Show this help message")
        else:
            print_warning(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
    else:
        run_all_demos()


if __name__ == "__main__":
    main()
