import subprocess
import sys
import os

def main():
    extra = ['--since="12 months"']  # TODO: pass as args
    cmd = ['git', 'shortlog', '-esn'] + extra
    result = subprocess.run(cmd, capture_output=True)
    print(result.stdout.decode())

if __name__ == '__main__':
    main()