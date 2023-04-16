import subprocess
import sys
import os

def main():
    cmd = ['git', 'shortlog', '-esn']
    result = subprocess.run(cmd, capture_output=True)
    print(result.stdout.decode())

if __name__ == '__main__':
    main()