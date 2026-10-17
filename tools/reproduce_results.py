#!/usr/bin/env python3
"""Reconstruct and audit recorded results. This script does not run CFD."""
from pathlib import Path
import argparse
import csv
import gzip
import hashlib
import io
import json
import re

ROOT = Path(__file__).resolve().parents[1]
NUMBER = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
SCENARIOS = {
    'case-a-ffd': ('logOpt.txt.gz', 'logMeshGeneration.txt.gz', 500000, 1.0),
    'case-b-cst': ('log_opt.txt.gz', 'log_mesh.txt.gz', 2000000, 10.0),
}

def read_log(case, filename):
    return gzip.decompress((ROOT / 'evidence' / case / filename).read_bytes()).decode('utf-8', errors='replace')

def physical_runs(text):
    starts = list(re.finditer(r'^Running Primal Solver\s+(\d+)', text, re.M))
    result = []
    for i, marker in enumerate(starts):
        end = starts[i+1].start() if i+1 < len(starts) else len(text)
        block = text[marker.end():end]
        values = {}
        for name in ['CD', 'CL']:
            matches = list(re.finditer(rf'^{name}:\s*({NUMBER})\s+final:', block, re.M))
            if not matches:
                break
            values[name] = float(matches[-1].group(1))
        if len(values) == 2:
            result.append({'primal_solve': int(marker.group(1)), **values})
    if not result:
        raise ValueError('No final physical CD/CL values found')
    return result

def cells(text):
    matches = re.findall(r'(?:Mesh\s+cells|cells|nCells)\s*:\s*(\d+)', text, re.I)
    if not matches:
        raise ValueError('No mesh cell count found')
    return int(matches[-1])

def build_tables():
    summaries, histories, audit = [], {}, {}
    for case, (filename, meshlog, reynolds, scale) in SCENARIOS.items():
        log = read_log(case, filename)
        runs = physical_runs(log)
        ipopt = (ROOT / 'evidence' / case / 'opt_IPOPT.txt').read_text()
        if 'EXIT: Optimal Solution Found.' not in ipopt:
            raise ValueError(f'{case}: optimizer success receipt missing')
        iterations = int(re.search(r'Number of Iterations\.+:\s*(\d+)', ipopt).group(1))
        objective = float(re.search(r'Objective\.+:\s*(' + NUMBER + ')', ipopt).group(1))
        initial_objective = float(re.search(r'^\s*0\s+(' + NUMBER + ')', ipopt, re.M).group(1))
        # Match physical solves to the optimizer's initial/final objective. This
        # avoids treating pre-trim startup or a post-optimization replay as an optimum.
        baseline = min(runs, key=lambda row: abs(row['CD'] - initial_objective/scale))
        final = min(runs, key=lambda row: abs(row['CD'] - objective/scale))
        if abs(initial_objective/scale - baseline['CD']) > 2e-8 or abs(baseline['CL']-.4) > 1e-3:
            raise ValueError(f'{case}: initial optimizer state cannot be verified')
        if abs(objective / scale - final['CD']) > 2e-8:
            raise ValueError(f'{case}: physical CD disagrees with objective scaling')
        histories[case] = runs
        summaries.append({
            'case': case, 'reynolds': reynolds, 'mesh_cells': cells(read_log(case, meshlog)),
            'baseline_CD': baseline['CD'], 'optimized_CD': final['CD'],
            'baseline_CL': baseline['CL'], 'optimized_CL': final['CL'],
            'drag_reduction_percent': 100*(baseline['CD']-final['CD'])/baseline['CD'],
            'ipopt_major_iterations': iterations, 'objective_scale': scale,
            'baseline_primal_solve': baseline['primal_solve'], 'final_primal_solve': final['primal_solve'],
        })
        audit[case] = {'DAFoam': re.search(r'DAFoam v([\d.]+)', log).group(1),
                       'OpenFOAM': re.search(r'Version:\s*v?([\d]+)', log).group(1),
                       'recorded_optimizer_exit': 'Optimal Solution Found',
                       'baseline_rule': 'physical solve matched to IPOPT iteration-zero objective after undoing its scale',
                       'optimum_rule': 'physical solve matched to final IPOPT objective, excluding later replay',
                       'full_CFD_rerun_during_packaging': False}
    coarse = summaries[1]
    mesh_rows = [{
        'case': 'case-b-cst', 'cells': coarse['mesh_cells'],
        'baseline_CD': coarse['baseline_CD'], 'optimized_CD': coarse['optimized_CD'],
        'baseline_CL': coarse['baseline_CL'], 'optimized_CL': coarse['optimized_CL'],
        'drag_reduction_percent': coarse['drag_reduction_percent'],
    }]
    for level in [20, 40, 80]:
        case = f'mesh-check-{level}k'
        text = read_log(case, 'log_meshcheck.txt.gz')
        values = {}
        for label in ['BASELINE', 'OPTIMIZED']:
            m = re.search(rf'^RESULT {label}.*?CD=({NUMBER})\s+CL=({NUMBER})', text, re.M)
            if not m:
                raise ValueError(f'{case}: missing {label} result')
            values[label] = tuple(map(float, m.groups()))
        baseline, optimized = values['BASELINE'], values['OPTIMIZED']
        mesh_rows.append({'case': case, 'cells': cells(read_log(case, 'log_mesh.txt.gz')),
                          'baseline_CD': baseline[0], 'optimized_CD': optimized[0],
                          'baseline_CL': baseline[1], 'optimized_CL': optimized[1],
                          'drag_reduction_percent': 100*(baseline[0]-optimized[0])/baseline[0]})
    sweep = json.loads((ROOT / 'data/aoa_sweep_results.json').read_text())
    sweep_log = read_log('aoa-sweep', 'log_sweep.txt.gz')
    sweep_rows = []
    for shape in ['baseline', 'optimized']:
        if [p['aoa'] for p in sweep[shape]] != list(range(-4, 13, 2)):
            raise ValueError('Expected nine ordered angles per shape')
        for point in sweep[shape]:
            m = re.search(rf'^RESULT {shape.upper()} AoA={point["aoa"]}: CD=({NUMBER})\s+CL=({NUMBER})', sweep_log, re.M)
            if not m or any(abs(float(m.group(i+1))-point[key]) > 5.1e-7 for i,key in enumerate(['CD','CL'])):
                raise ValueError('Saved sweep JSON disagrees with its solver log')
            sweep_rows.append({'shape': shape, 'aoa_degrees': point['aoa'], 'CD': point['CD'], 'CL': point['CL']})
    expected_cells = [10270, 20792, 41340, 81984]
    if [r['cells'] for r in mesh_rows] != expected_cells:
        raise ValueError('Mesh log counts disagree with the report')
    # Independent report-level regression, allowing its rounded table values.
    for row, base, optimized in zip(mesh_rows, [.020615,.019537,.018995,.018665], [.016042,.015500,.015197,.015032]):
        if abs(row['baseline_CD']-base) > 1e-6 or abs(row['optimized_CD']-optimized) > 1e-6:
            raise ValueError('A reconstructed coefficient disagrees with the report')
    tables = {'optimization_summary.csv': summaries, 'mesh_sensitivity.csv': mesh_rows,
              'aoa_sweep.csv': sweep_rows}
    for case, rows in histories.items():
        tables[f'{case}_primal_history.csv'] = rows
    return tables, audit

def csv_text(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: format(value, '.12g') if isinstance(value, float) else value for key,value in row.items()})
    return stream.getvalue()

def check_manifest():
    manifest = json.loads((ROOT / 'data/source-manifest.json').read_text())
    for record in manifest['files']:
        path = ROOT / record['destination']
        if not path.resolve().is_relative_to(ROOT):
            raise ValueError('Manifest path leaves repository')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['prepared_sha256']:
            raise ValueError(f'Prepared artifact changed: {record["destination"]}')
        if record['change'] == 'lossless gzip':
            if hashlib.sha256(gzip.decompress(raw)).hexdigest() != record['decompressed_sha256']:
                raise ValueError('Compressed evidence integrity failed')
    return len(manifest['files'])

def plot_results(tables):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    destination = ROOT / 'results/figures'
    destination.mkdir(parents=True, exist_ok=True)
    mesh = tables['mesh_sensitivity.csv']
    fig, axes = plt.subplots(1,2, figsize=(11,4.2), layout='constrained')
    for field, label, color in [('baseline_CD','Baseline','#536878'), ('optimized_CD','Optimized','#2468a0')]:
        axes[0].plot([r['cells'] for r in mesh], [r[field] for r in mesh], 'o-', label=label, color=color)
    axes[0].set(xlabel='Cell count', ylabel='$C_D$', xlim=(0,95000), title='Recorded CST mesh checks')
    axes[0].legend(); axes[0].grid(alpha=.2)
    axes[1].plot([r['cells'] for r in mesh], [r['drag_reduction_percent'] for r in mesh], 'o-', color='#2468a0')
    for row in mesh:
        axes[1].annotate(f"{row['drag_reduction_percent']:.2f}%", (row['cells'],row['drag_reduction_percent']), xytext=(0,8), textcoords='offset points', ha='center')
    axes[1].set(xlabel='Cell count', ylabel='Simulated drag reduction (%)', xlim=(0,95000), ylim=(17.5,24.5), title='No re-optimization on finer meshes')
    axes[1].grid(alpha=.2)
    fig.savefig(destination/'mesh-sensitivity.png', dpi=180); plt.close(fig)
    sweep = tables['aoa_sweep.csv']
    fig, axes = plt.subplots(1,2, figsize=(11,4.2), layout='constrained')
    for shape, color in [('baseline','#536878'), ('optimized','#2468a0')]:
        rows = [r for r in sweep if r['shape']==shape]
        for axis, field in zip(axes, ['CD','CL']):
            axis.plot([r['aoa_degrees'] for r in rows], [r[field] for r in rows], 'o-', color=color, label=shape.title())
            axis.set(xlabel='Angle of attack (degrees)', ylabel='$C_D$' if field=='CD' else '$C_L$')
            axis.grid(alpha=.2); axis.legend()
    fig.suptitle('Recorded fixed-angle sweep (10,270 cells; no lift trim)')
    fig.savefig(destination/'aoa-sweep.png', dpi=180); plt.close(fig)
    for summary in tables['optimization_summary.csv']:
        case = summary['case']; history = tables[f'{case}_primal_history.csv']
        fig, axes = plt.subplots(2,1, figsize=(8,5.7), layout='constrained', sharex=True)
        for axis, field in zip(axes, ['CD','CL']):
            axis.plot([r['primal_solve'] for r in history], [r[field] for r in history], 'o-', ms=3, color='#2468a0')
            axis.set_ylabel('$C_D$' if field=='CD' else '$C_L$'); axis.grid(alpha=.2)
        axes[0].axhline(summary['baseline_CD'], color='#536878', ls='--', label='Lift-feasible baseline')
        axes[0].legend(); axes[1].axhline(.4, color='#536878', ls='--')
        axes[1].set_xlabel('Primal solve number (not IPOPT major iteration)')
        fig.suptitle(f'{case}: final physical coefficients from each recorded solve')
        fig.savefig(destination/f'{case}-history.png', dpi=180); plt.close(fig)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Regenerate CSV tables from archived logs')
    parser.add_argument('--plots', action='store_true', help='Regenerate the lightweight plots (requires matplotlib)')
    args = parser.parse_args()
    count = check_manifest()
    tables, audit = build_tables()
    for filename, rows in tables.items():
        path = ROOT/'data'/filename
        generated = csv_text(rows)
        if args.write:
            path.write_text(generated, encoding='utf-8', newline='')
        elif not path.exists() or path.read_text(encoding='utf-8') != generated:
            raise SystemExit(f'{filename} missing or stale; run with --write')
    if args.plots:
        plot_results(tables)
    print(json.dumps({'artifact_integrity_files': count, 'recorded_environments': audit,
                      'optimization_summary': tables['optimization_summary.csv'],
                      'mesh_checks': len(tables['mesh_sensitivity.csv']), 'sweep_points': len(tables['aoa_sweep.csv']),
                      'full_CFD_rerun': False}, indent=2))

if __name__ == '__main__':
    main()
