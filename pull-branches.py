import sys
import subprocess
import logging
logging.basicConfig(level=logging.DEBUG)


def main():
    print('Reading branch names from input. You can also feed input from a file "python pull-branches.py < file.txt".')

    branches = []
    for line in sys.stdin:
        line = line.strip()
        if line:
            branches.append(line)

    # avoid submodule errors
    # TODO: read previous value
    res = subprocess.run(f"git config --local submodule.recurse false")
    logging.debug(f'{res}')

    logging.debug(f'Branches: {branches}')

    for branch in branches:
        res = subprocess.run(f"git rev-parse --verify --quiet {branch}")
        logging.debug(f'{res}')
        if res.returncode != 0:
            logging.debug(f"{branch} doesn't exist, fetching...")
            subprocess.check_call(
                f'git remote set-branches --add origin {branch}')
            subprocess.check_call(f'git fetch origin {branch}')
            subprocess.check_call(f'git checkout origin/{branch} -b {branch}')
        else:
            logging.debug(f"Check out {branch}...")
            subprocess.check_call(f'git checkout {branch}')
            logging.debug(f"Pull {branch}...")
            subprocess.check_call(f'git restore .')
            subprocess.check_call(f'git pull')

    # avoid submodule errors
    res = subprocess.run(f"git config --local submodule.recurse true")
    logging.debug(f'{res}')


if __name__ == '__main__':
    main()
