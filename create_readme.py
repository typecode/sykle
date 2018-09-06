from src.cli import __doc__
import os
import chevron

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'README.mustache')
README_PATH = os.path.join(os.path.dirname(__file__), 'README.md')
SYKLE_EXAMPLE_PATH = os.path.join(
    os.path.dirname(__file__),
    '.sykle.example.json'
)

sykle_example = None
with open(SYKLE_EXAMPLE_PATH, 'r', encoding='utf-8') as f:
    sykle_example = f.read()

long_description = None
with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
    long_description = chevron.render(f.read(), {
        'usage': __doc__,
        'sykle_example': sykle_example,
    })


os.chmod(README_PATH, 0o644)
with open(README_PATH, 'w+', encoding='utf-8') as f:
    f.write(long_description)


os.chmod(README_PATH, 0o400)
