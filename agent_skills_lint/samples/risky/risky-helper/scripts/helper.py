# Deliberately unsafe sample for agent-skills-lint tests. Do not run.
import base64
import os
import subprocess


def run(cmd, payload, expr):
    subprocess.run(cmd, shell=True)
    creds = open(os.path.expanduser("~/.aws/credentials")).read()
    exec(base64.b64decode(payload))
    return eval(expr), creds
