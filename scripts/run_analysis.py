"""Execute analysis from a fresh kernel; replace notebook outputs only on success."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

import nbformat
from nbclient import NotebookClient
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notebook', type=Path, default=Path(__file__).resolve().parents[1] / 'ookla_data_project.ipynb')
    parser.add_argument('--env-file', type=Path, help='Optional local credentials file; values are never printed.')
    parser.add_argument('--timeout', type=int, default=900, help='Maximum seconds per code cell.')
    args = parser.parse_args()
    notebook_path = args.notebook.resolve()
    root = notebook_path.parent
    load_dotenv(args.env_file or root / '.env', override=False)
    secret = os.environ.get('CENSUS_API_KEY', '')

    def scrub(value):
        if isinstance(value, str):
            return value.replace(secret, '[REDACTED]') if secret else value
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items()}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    notebook = nbformat.read(notebook_path, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            cell.execution_count = None
            cell.outputs = []
            cell.metadata.pop('execution', None)
    # Use this interpreter explicitly, regardless of any globally selected kernel.
    with tempfile.TemporaryDirectory(prefix='ookla-clean-kernel-') as temporary:
        cache = root / '.ookla-cache' / 'runtime'
        for name in ['matplotlib', 'ipython', 'jupyter']:
            (cache / name).mkdir(parents=True, exist_ok=True)
        spec = Path(temporary) / 'kernels' / 'ookla-clean'
        spec.mkdir(parents=True)
        (spec / 'kernel.json').write_text(json.dumps({
            'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
            'display_name': 'Ookla clean run', 'language': 'python',
        }))
        os.environ['JUPYTER_PATH'] = str(Path(temporary)) + (os.pathsep + os.environ['JUPYTER_PATH'] if os.environ.get('JUPYTER_PATH') else '')
        os.environ['JUPYTER_RUNTIME_DIR'] = str(cache / 'jupyter')
        env = dict(os.environ)
        env['MPLCONFIGDIR'] = str(cache / 'matplotlib')
        env['IPYTHONDIR'] = str(cache / 'ipython')
        env['MPLBACKEND'] = 'Agg'
        client = NotebookClient(notebook, kernel_name='ookla-clean', timeout=args.timeout, allow_errors=False)
        execution_count = 0
        try:
            with client.setup_kernel(cwd=str(root), env=env):
                for index, cell in enumerate(notebook.cells):
                    if cell.cell_type != 'code' or not cell.source.strip():
                        continue
                    execution_count += 1
                    print(f'Running code cell {execution_count}: notebook cell {index + 1}/{len(notebook.cells)}', flush=True)
                    client.execute_cell(cell, index, execution_count=execution_count)
                    cell.outputs = scrub(cell.outputs)
                    print(f'Completed code cell {execution_count}', flush=True)
        except Exception as exc:
            failure = cache / 'failed_run.ipynb'
            nbformat.write(nbformat.from_dict(scrub(notebook)), failure)
            print(f'Clean run stopped: {scrub(str(exc))}', file=sys.stderr)
            print('Partial outputs are saved only in .ookla-cache/runtime/failed_run.ipynb.', file=sys.stderr)
            return 1
    notebook.metadata.kernelspec = {'name': 'python3', 'display_name': 'Python 3.13', 'language': 'python'}
    clean = nbformat.from_dict(scrub(notebook))
    nbformat.validate(clean)
    temporary_output = notebook_path.with_suffix('.executed.tmp')
    nbformat.write(clean, temporary_output)
    temporary_output.replace(notebook_path)
    print(f'Clean run completed: {execution_count} code cells, zero errors.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
