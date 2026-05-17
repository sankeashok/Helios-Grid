import urllib.request
import json

url = 'https://api.github.com/repos/sankeashok/Helios-Grid/actions/runs?per_page=1'
req = urllib.request.urlopen(url)
data = json.loads(req.read().decode('utf-8'))
run = data['workflow_runs'][0]
run_id = run['id']

jobs_url = f'https://api.github.com/repos/sankeashok/Helios-Grid/actions/runs/{run_id}/jobs'
jobs_req = urllib.request.urlopen(jobs_url)
jobs_data = json.loads(jobs_req.read().decode('utf-8'))

with open('logs.txt', 'w', encoding='utf-8') as f:
    for job in jobs_data['jobs']:
        icon = "PASS" if job['conclusion'] == 'success' else ("FAIL" if job['conclusion'] == 'failure' else str(job['conclusion']))
        # Strip emoji from job name
        name_clean = job['name'].encode('ascii', 'ignore').decode('ascii').strip()
        line = f"[{icon}] {name_clean}"
        f.write(line + '\n')
        if job['conclusion'] == 'failure':
            for step in job['steps']:
                if step['conclusion'] == 'failure':
                    step_name = step['name'].encode('ascii', 'ignore').decode('ascii').strip()
                    f.write(f"  --> FAILED STEP: {step_name}\n")
