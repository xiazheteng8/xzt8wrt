"""Fail instead of silently dropping requested packages or image options."""
import pathlib
import sys

seed = pathlib.Path(sys.argv[1]).read_text().splitlines()
actual = set(pathlib.Path(sys.argv[2]).read_text().splitlines())
missing = [line for line in seed if line.startswith('CONFIG_') and line not in actual]
if missing:
    sys.exit('Requested options missing after make defconfig:\n' + '\n'.join(missing))
print('All requested options survived make defconfig.')
