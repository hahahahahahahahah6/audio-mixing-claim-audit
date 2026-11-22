"""Compare documented claims with statically detected source calls."""
import ast
import os
import re
from pathlib import Path
from .phrases import AUDIOMIXING, NOAUDIOMIXING, GENERIC_NAMES


def normalize(text):
    return ' '.join(text.lower().replace('’', "'").replace("n't", ' not').replace('-', ' ').split())


def pattern(phrases):
    return re.compile(r'\b(?:' + '|'.join(re.escape(p) for p in sorted(phrases, key=lambda p: (-len(p), p))) + r')\b')


def paragraphs(text):
    lines, fence = [], None
    for line in text.splitlines():
        mark = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if fence:
            if re.match(r'^ {0,3}' + re.escape(fence[0]) + '{' + str(len(fence)) + r',}\s*$', line):
                fence = None
            lines.append('')
        elif mark:
            fence = mark.group(1)
            lines.append('')
        else:
            lines.append(line)
    return [normalize(p) for p in re.split(r'\n\s*\n', '\n'.join(lines)) if p.strip()]


def evidence(source):
    try:
        nodes = list(ast.walk(ast.parse(source)))
    except (SyntaxError, ValueError):
        return False
    imports, bound, definitions = {}, set(), set()
    def targets(node):
        if isinstance(node, ast.Name):
            return {node.id}
        if isinstance(node, (ast.Tuple, ast.List)):
            return set().union(*(targets(x) for x in node.elts))
        if isinstance(node, ast.Starred):
            return targets(node.value)
        return set()
    for node in nodes:
        if isinstance(node, ast.Import):
            for item in node.names:
                imports[item.asname or item.name.split('.')[0]] = item.name if item.asname else item.name.split('.')[0]
        elif isinstance(node, ast.ImportFrom) and not node.level:
            for item in node.names:
                imports[item.asname or item.name] = (node.module or '') + '.' + item.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.add(node.name)
            bound.add(node.name)
        assignments = []
        if isinstance(node, ast.Assign):
            assignments = node.targets
        elif isinstance(node, ast.AnnAssign):
            assignments = [node.target]
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            assignments = [item.optional_vars for item in node.items if item.optional_vars]
        for assignment in assignments:
            bound.update(targets(assignment))
    segment = overlay = combiner = mix = False
    for node in nodes:
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        attr = isinstance(func, ast.Attribute)
        if isinstance(func, ast.Name):
            if func.id in bound:
                continue
            resolved = imports.get(func.id, '')
            name = resolved.rsplit('.', 1)[-1]
        elif attr:
            name = func.attr
            base = func.value
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name) and base.id in imports and base.id in bound:
                continue
            resolved = imports.get(base.id, '') if isinstance(base, ast.Name) else ''
        else:
            continue
        if name in definitions:
            continue
        def lib_member(lib, member):
            return (attr and name == member and (resolved == lib or resolved.startswith(lib + '.'))) or (not attr and resolved == lib + '.' + member)
        def literal(values, keywords=None):
            args = list(node.args) + [k.value for k in node.keywords if keywords is None or k.arg in keywords]
            return any(isinstance(x, ast.Constant) and isinstance(x.value, str) and x.value in values for x in args)
        if name in GENERIC_NAMES and (attr or resolved):
            return True
        is_segment = lib_member('pydub', 'AudioSegment') or (attr and name in {'from_file', 'from_mp3', 'from_ogg', 'from_wav', 'silent', 'empty'} and (resolved == 'pydub' or resolved.startswith('pydub.') and (resolved == 'pydub.AudioSegment' or not resolved.endswith('AudioSegment'))))
        segment |= is_segment
        overlay |= attr and name == 'overlay'
        is_combiner = lib_member('sox', 'Combiner')
        combiner |= is_combiner
        mix |= bool((is_combiner or (attr and name == 'build')) and literal({'mix', 'mix-power'}, {'combine_type'}))
        if ((attr and name in {'filter', 'filter_'}) or (not attr and resolved in {'ffmpeg.filter', 'ffmpeg.filter_'})) and literal({'amix'}):
            return True
    return bool((segment and overlay) or (combiner and mix))


def audit(root, ignore=(), fail_on='high'):
    root = Path(root)
    if not root.is_dir() or not os.access(str(root), os.R_OK | os.X_OK):
        raise OSError('Not a readable directory: {}'.format(root))
    claims = denials = production = tests = False
    yes_re, no_re = pattern(AUDIOMIXING), pattern(NOAUDIOMIXING)
    def ignored(path):
        rel = path.relative_to(root).as_posix()
        return any(rel == prefix.rstrip('/') or rel.startswith(prefix.rstrip('/') + '/') for prefix in ignore)
    def raise_error(error):
        raise error
    for directory, dirs, files in os.walk(str(root), followlinks=False, onerror=raise_error):
        parent = Path(directory)
        dirs[:] = sorted(d for d in dirs if not (parent / d).is_symlink() and not ignored(parent / d))
        for filename in sorted(files):
            path = parent / filename
            if path.is_symlink() or ignored(path):
                continue
            rel = path.relative_to(root)
            if rel.as_posix() == 'README.md' or ('docs' in rel.parts and path.suffix == '.md'):
                for para in paragraphs(path.read_text(encoding='utf-8')):
                    denials |= bool(no_re.search(para))
                    claims |= bool(yes_re.search(no_re.sub(' ', para)))
            if path.suffix == '.py' and not any(x in rel.parts for x in ('fixtures', 'docs', 'examples')):
                is_test = 'tests' in rel.parts or filename.startswith('test_') or filename.endswith('_test.py')
                if evidence(path.read_text(encoding='utf-8')):
                    if is_test:
                        tests = True
                    else:
                        production = True
    findings = []
    if claims and not production:
        severity = 'MEDIUM' if tests else 'HIGH'
        findings.append({'rule': 'documented-audio-mixing-claim-false', 'severity': severity, 'message': 'Documented claim has ' + ('test-only evidence.' if tests else 'no production evidence.')})
    if denials and production:
        findings.append({'rule': 'documented-no-audio-mixing-claim-false', 'severity': 'HIGH', 'message': 'Documented denial conflicts with production evidence.'})
    fail = any(item['severity'] == 'HIGH' or fail_on == 'medium' for item in findings)
    return {'verdict': 'FAIL' if fail else 'PASS', 'findings': findings}
