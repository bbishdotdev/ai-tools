#!/usr/bin/env python3
"""Read native Codex hook status without starting a turn or changing trust/config."""
import argparse
import json
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import time


def hooks_list(project, binary='codex', timeout=20):
    project = Path(project).resolve()
    inbox = queue.Queue()
    with tempfile.TemporaryFile(mode='w+t') as diagnostics:
        process = subprocess.Popen([binary, 'app-server', '--stdio', '-c',
                                    f'projects.{json.dumps(str(project))}.trust_level="trusted"'], cwd=project,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=diagnostics, text=True, bufsize=1)
        def read_lines():
            for line in process.stdout:
                try:
                    inbox.put(json.loads(line))
                except json.JSONDecodeError:
                    pass
            inbox.put(None)
        worker = threading.Thread(target=read_lines, daemon=True)
        worker.start()
        notifications = []
        def send(message):
            process.stdin.write(json.dumps(message) + '\n')
            process.stdin.flush()
        def response(request_id):
            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f'Codex app-server request {request_id} timed out')
                item = inbox.get(timeout=remaining)
                if item is None:
                    diagnostics.seek(0)
                    raise RuntimeError('Codex app-server closed stdout: ' + diagnostics.read())
                if item.get('id') == request_id:
                    if 'error' in item:
                        raise RuntimeError(json.dumps(item['error']))
                    return item['result']
                notifications.append(item)
        try:
            send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{
                'clientInfo':{'name':'bstack_hook_inspection','version':'0.1.0'},
                'capabilities':{'experimentalApi':True}}})
            response(1)
            send({'jsonrpc':'2.0','method':'initialized','params':{}})
            send({'jsonrpc':'2.0','id':2,'method':'hooks/list','params':{'cwds':[str(project)]}})
            result = response(2)
            send({'jsonrpc':'2.0','id':3,'method':'config/read','params':{'cwd':str(project),'includeLayers':True}})
            config = response(3)
            layers = [{'name': layer.get('name'), 'disabledReason': layer.get('disabledReason'),
                       'hooksFeature': layer.get('config', {}).get('features', {}).get('hooks')}
                      for layer in config.get('layers', [])]
            return {'project':str(project),'hooks_list':result,
                    'config_layers':layers, 'query_methods':['initialize','hooks/list','config/read'],
                    'trust_or_config_mutations':False}
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            worker.join(timeout=3)
            process.stdin.close()
            process.stdout.close()


def trust_limit(status, project):
    """Return a native trust diagnosis only for this project's expected hook source."""
    project = Path(project).resolve()
    for layer in status.get('config_layers', []):
        name = layer.get('name') or {}
        reason = layer.get('disabledReason') or ''
        if (name.get('type') == 'project' and name.get('dotCodexFolder') == str(project / '.codex')
                and layer.get('hooksFeature') is True and 'trusted project' in reason.lower()):
            return 'Codex project configuration is blocked by native project trust: ' + reason
    for entry in status.get('hooks_list', {}).get('data', []):
        if entry.get('cwd') != str(project) or entry.get('errors'):
            continue
        for hook in entry.get('hooks', []):
            if (hook.get('sourcePath') == str(project / '.codex/hooks.json')
                    and hook.get('eventName', '').replace('_', '').lower() == 'userpromptsubmit'
                    and hook.get('trustStatus') in ('untrusted', 'modified')):
                return 'Codex prompt hook requires native trust: ' + hook['trustStatus']
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    parser.add_argument('--binary',default='codex')
    args=parser.parse_args()
    print(json.dumps(hooks_list(args.project,args.binary),indent=2))

if __name__=='__main__':
    main()
