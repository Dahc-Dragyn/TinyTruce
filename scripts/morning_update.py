import subprocess
import os
import sys
import re
import concurrent.futures

def run_script(script, script_path):
    print(f"Launching {script}...")
    p = subprocess.Popen(
        [sys.executable, script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    # communicate() reads all output until EOF
    stdout, stderr = p.communicate()
    return script, p.returncode, stdout, stderr

def main():
    print("Starting morning updates...")
    
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    
    scripts = [
        "chronicler_update.py",
        "ukraine_tactical_update.py",
        "us_iran_war_update.py"
    ]
    
    total_run_cost = 0.0
    
    # Run all scripts concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for script in scripts:
            script_path = os.path.join(scripts_dir, script)
            if os.path.exists(script_path):
                futures.append(executor.submit(run_script, script, script_path))
            else:
                print(f"❌ Could not find {script} at {script_path}")
        
        for future in concurrent.futures.as_completed(futures):
            script, returncode, stdout, stderr = future.result()
            
            output = stdout + "\n" + stderr
            
            # Parse for cost
            cost_match = re.search(r"Total Session Cost:\s*\$([0-9.]+)", output)
            script_cost = 0.0
            if cost_match:
                script_cost = float(cost_match.group(1))
            else:
                est_match = re.search(r"Session Cost estimate:\s*\$([0-9.]+)", output)
                if est_match:
                    script_cost = float(est_match.group(1))
                
            total_run_cost += script_cost
            
            if returncode == 0:
                print(f"✅ {script} completed successfully. (Cost: ${script_cost:.4f})")
            else:
                print(f"❌ {script} failed with return code {returncode}.")
                if stderr:
                    print(f"--- stderr snippet ---")
                    print("\n".join(stderr.splitlines()[-10:]))

    print("-" * 40)
    print(f"Morning updates finished. Total Combined Cost: ${total_run_cost:.4f}")

if __name__ == "__main__":
    main()
