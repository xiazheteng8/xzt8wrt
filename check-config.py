"""Fail instead of silently dropping requested packages or image options."""
import pathlib
import sys

seed = pathlib.Path(sys.argv[1]).read_text().splitlines()
actual = set(pathlib.Path(sys.argv[2]).read_text().splitlines())
missing = []
for line in seed:
    if line.startswith('CONFIG_') and line not in actual:
        missing.append(line)
    elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
        key = line.split()[1]
        if any(option.startswith(key + '=') and option != key + '=n' for option in actual):
            missing.append(line)
if missing:
    sys.exit('Requested options missing after make defconfig:\n' + '\n'.join(missing))
print('All requested options survived make defconfig.')
