#!/usr/bin/env python3
import csv
import hashlib
import json
import math
import shutil
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path('/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence')
SRC_ROOT = Path('/home/elaref/Documents/research/ragin_expert_panel_v1')
OUT = ROOT / 'results/laya_research'
DOCS = ROOT / 'docs/laya_integration'
LABELS = ['BENIGN', 'RECON', 'SUSPICIOUS', 'EXPLOITATION', 'PRIVILEGE_ESCALATION', 'DATA_ACCESS', 'PERSISTENCE', 'OTHER_ATTACK', 'UNCERTAIN']
NONUNCERTAIN = set(LABELS) - {'UNCERTAIN'}
RUNS = ['expert_ai_01', 'expert_ai_02', 'expert_ai_03']
ASSIGNMENTS = {
    'expert_ai_01': 'GPT-6-Luna',
    'expert_ai_02': 'GPT-6.1-Sol',
    'expert_ai_03': 'GPT-5.6-Terra',
}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def read_json(path):
    with path.open() as f:
        return json.load(f)

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def label_projection(label):
    if label == 'UNCERTAIN':
        return None
    return 'NEGATIVE' if label == 'BENIGN' else 'POSITIVE'

def cohen_kappa(a, b, categories):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n if n else float('nan')
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[c] * cb[c] for c in categories) / (n * n) if n else float('nan')
    return (po - pe) / (1 - pe) if n and not math.isclose(1 - pe, 0.0) else 1.0

def fleiss(rows, categories):
    n = len(rows)
    if not n:
        return float('nan')
    raters = len(rows[0])
    counts = [{c: row.count(c) for c in categories} for row in rows]
    p_i = [sum(v * (v - 1) for v in row.values()) / (raters * (raters - 1)) for row in counts]
    p_bar = sum(p_i) / n
    p_j = {c: sum(row[c] for row in counts) / (n * raters) for c in categories}
    p_e = sum(v * v for v in p_j.values())
    return (p_bar - p_e) / (1 - p_e) if not math.isclose(1 - p_e, 0.0) else 1.0

def fmt(x):
    return None if isinstance(x, float) and math.isnan(x) else round(x, 12)

def pair_stats(a, b, categories):
    table = {x: {y: 0 for y in categories} for x in categories}
    for x, y in zip(a, b):
        table[x][y] += 1
    exact = sum(x == y for x, y in zip(a, b))
    return {
        'n': len(a), 'exact_agreement': exact, 'disagreement_count': len(a) - exact,
        'exact_agreement_rate': fmt(exact / len(a)), 'cohen_kappa': fmt(cohen_kappa(a, b, categories)),
        'label_transition_table': table,
    }

def binary_pair_stats(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    aa, bb = zip(*pairs) if pairs else ([], [])
    table = {x: {y: 0 for y in ['NEGATIVE', 'POSITIVE']} for x in ['NEGATIVE', 'POSITIVE']}
    for x, y in pairs:
        table[x][y] += 1
    agreement = sum(x == y for x, y in pairs)
    return {
        'total_n': len(a), 'eligible_n': len(pairs), 'uncertain_excluded': len(a) - len(pairs),
        'agreement': agreement, 'disagreement': len(pairs) - agreement,
        'agreement_rate': fmt(agreement / len(pairs)) if pairs else None,
        'cohen_kappa': fmt(cohen_kappa(list(aa), list(bb), ['NEGATIVE', 'POSITIVE'])) if pairs else None,
        'paired_2x2_table': table,
    }

def main():
    source_data, checks = {}, {}
    for run in RUNS:
        d = SRC_ROOT / run
        paths = {name: d / name for name in ['packet.json', 'completed_annotations.json', 'run_metadata.json']}
        c = {}
        for name, path in paths.items():
            c[name + '_exists'] = path.is_file()
        if not all(c.values()):
            raise SystemExit(f'{run}: missing required source file')
        packet = read_json(paths['packet.json'])
        annotations = read_json(paths['completed_annotations.json'])
        metadata = read_json(paths['run_metadata.json'])
        packet_ids = [x.get('id') for x in packet] if isinstance(packet, list) else []
        ann_ids = [x.get('case_id') for x in annotations] if isinstance(annotations, list) else []
        labels = [x.get('label') for x in annotations] if isinstance(annotations, list) else []
        notes = [x.get('note') for x in annotations] if isinstance(annotations, list) else []
        c.update({
            'annotation_count_120': len(annotations) == 120,
            'packet_count_120': len(packet) == 120,
            'annotation_unique_ids_120': len(ann_ids) == len(set(ann_ids)) == 120,
            'packet_unique_ids_120': len(packet_ids) == len(set(packet_ids)) == 120,
            'annotation_id_set_matches_packet': set(ann_ids) == set(packet_ids),
            'no_missing_ids': not (set(packet_ids) - set(ann_ids)),
            'no_extra_ids': not (set(ann_ids) - set(packet_ids)),
            'labels_nonblank': all(isinstance(x, str) and x for x in labels),
            'labels_taxonomy_valid': all(x in LABELS for x in labels),
            'notes_nonblank': all(isinstance(x, str) and x.strip() for x in notes),
            'packet_sha256_matches_metadata': sha(paths['packet.json']) == metadata.get('packet_sha256'),
            'output_sha256_matches_metadata': sha(paths['completed_annotations.json']) == metadata.get('output_sha256'),
            'repository_access_used_false': metadata.get('repository_access_used') is False,
            'network_access_used_false': metadata.get('network_access_used') is False,
            'external_files_accessed_false': metadata.get('external_files_accessed') is False,
            'blindness_violation_false': metadata.get('blindness_violation') is False,
            'run_validity_valid': metadata.get('run_validity') == 'VALID',
            'metadata_structurally_sane': all(k in metadata for k in ['packet_sha256', 'output_sha256', 'repository_access_used', 'network_access_used', 'external_files_accessed', 'blindness_violation', 'run_validity']),
        })
        c['integrity_status'] = 'VALID' if all(c.values()) else 'INVALID'
        if c['integrity_status'] != 'VALID':
            raise SystemExit(f'{run}: integrity failure: ' + ', '.join(k for k, v in c.items() if not v))
        source_data[run] = {'packet': packet, 'annotations': annotations, 'metadata': metadata, 'paths': paths}
        checks[run] = c

    OUT.mkdir(parents=True, exist_ok=True); DOCS.mkdir(parents=True, exist_ok=True)
    path_record = {
        'previous_blocker': 'Completed-run files were sought under results/laya_research/expert_ai_workspaces instead of the preregistered persistent external workspaces.',
        'classification': 'SOURCE_PATH_RESOLUTION_FAILURE', 'annotation_runs_invalidated': False,
        'annotations_rerun': False, 'outcomes_used_to_change_paths': False,
        'correct_authoritative_root': str(SRC_ROOT), 'predictions_accessed': False,
    }
    write_json(OUT / 'expert_ai_ingestion_path_resolution.json', path_record)

    labels_dir, prov_dir = OUT / 'expert_ai_labels_v1', OUT / 'expert_ai_run_provenance_v1'
    labels_dir.mkdir(exist_ok=True); prov_dir.mkdir(exist_ok=True)
    for run in RUNS:
        shutil.copyfile(source_data[run]['paths']['completed_annotations.json'], labels_dir / f'{run}.json')
        shutil.copyfile(source_data[run]['paths']['run_metadata.json'], prov_dir / f'{run}_metadata.json')
        if sha(source_data[run]['paths']['completed_annotations.json']) != sha(labels_dir / f'{run}.json'):
            raise SystemExit(f'{run}: annotation copy hash mismatch')
        if sha(source_data[run]['paths']['run_metadata.json']) != sha(prov_dir / f'{run}_metadata.json'):
            raise SystemExit(f'{run}: metadata copy hash mismatch')

    by_run = {r: {x['case_id']: x for x in source_data[r]['annotations']} for r in RUNS}
    ids = [x['id'] for x in source_data[RUNS[0]]['packet']]
    vals = {r: [by_run[r][cid]['label'] for cid in ids] for r in RUNS}
    dists = {r: dict(sorted(Counter(vals[r]).items())) for r in RUNS}
    manifest = {'source_path_resolution_corrected': True, 'annotations_rerun': False, 'runs': []}
    for run in RUNS:
        m, p = source_data[run]['metadata'], source_data[run]['paths']
        manifest['runs'].append({'panel_member': run, 'assigned_model': ASSIGNMENTS[run], 'model_identity_provenance': m.get('model_identity_provenance'), 'reasoning_effort': m.get('reasoning_effort'), 'authoritative_workspace': str(SRC_ROOT / run), 'packet_sha256': sha(p['packet.json']), 'annotation_sha256': sha(p['completed_annotations.json']), 'metadata_sha256': sha(p['run_metadata.json']), 'case_count': 120, 'label_distribution': dists[run], 'integrity_status': 'VALID'})
    write_json(OUT / 'expert_ai_panel_runs_manifest.json', manifest)
    write_json(OUT / 'expert_ai_panel_raw_integrity_report.json', {'source_root': str(SRC_ROOT), 'runs': checks, 'overall_status': 'VALID'})
    write_json(OUT / 'expert_ai_panel_normalization_audit.json', {'normalization_applied': True, 'operations': ['read packet id as case_id for set comparison', 'read annotation note as adjudication note', 'binary projection applied only to derived metrics'], 'raw_files_unchanged': True})

    pairs = {}
    for i, a in enumerate(RUNS):
        for b in RUNS[i + 1:]:
            pairs[f'{a} x {b}'] = pair_stats(vals[a], vals[b], LABELS)
    write_json(OUT / 'expert_ai_panel_pairwise_multiclass.json', {'pairs': pairs, 'n_per_pair': 120})
    binary_vals = {r: [label_projection(x) for x in vals[r]] for r in RUNS}
    binary_pairs = {}
    for i, a in enumerate(RUNS):
        for b in RUNS[i + 1:]:
            binary_pairs[f'{a} x {b}'] = binary_pair_stats(binary_vals[a], binary_vals[b])
    eligible_rows = [[binary_vals[r][i] for r in RUNS] for i in range(120) if all(binary_vals[r][i] is not None for r in RUNS)]
    write_json(OUT / 'expert_ai_panel_pairwise_binary.json', {'pairs': binary_pairs, 'projection': {'BENIGN': 'NEGATIVE', 'UNCERTAIN': 'EXCLUDED', 'non-BENIGN_non-UNCERTAIN': 'POSITIVE'}})
    write_json(OUT / 'expert_ai_panel_multirater_reliability.json', {'multiclass_fleiss_kappa': fmt(fleiss([[vals[r][i] for r in RUNS] for i in range(120)], LABELS)), 'binary_fleiss_kappa': fmt(fleiss(eligible_rows, ['NEGATIVE', 'POSITIVE'])), 'binary_eligible_n': len(eligible_rows), 'binary_uncertain_excluded_n': 120 - len(eligible_rows)})

    rows, consensus_counts, transitions = [], Counter(), Counter()
    for i, cid in enumerate(ids):
        ls = [vals[r][i] for r in RUNS]; bs = [binary_vals[r][i] for r in RUNS]
        lc, uc = len(set(ls)), ls.count('UNCERTAIN'); exact_counts = Counter(x for x in ls if x != 'UNCERTAIN'); binary_counts = Counter(x for x in bs if x is not None)
        exact_3 = uc == 0 and lc == 1; exact_2 = uc == 0 and max(exact_counts.values(), default=0) == 2
        binary_3 = uc == 0 and len(binary_counts) == 1 and not exact_3
        binary_2 = not exact_3 and not binary_3 and not exact_2 and max(binary_counts.values(), default=0) >= 2
        if uc >= 2: status = 'UNCERTAIN_HEAVY'
        elif exact_3: status = 'EXACT_3_OF_3'
        elif binary_3: status = 'BINARY_3_OF_3'
        elif exact_2: status = 'EXACT_2_OF_3'
        elif binary_2: status = 'BINARY_2_OF_3'
        else: status = 'THREE_WAY_DISAGREEMENT'
        consensus_counts[status] += 1
        majority_label, majority_count = (exact_counts.most_common(1)[0] if exact_counts else ('UNCERTAIN', uc))
        for a, b in [(ls[0], ls[1]), (ls[0], ls[2]), (ls[1], ls[2])]:
            if a != b: transitions[(a, b)] += 1
        rows.append({'case_id': cid, 'expert_ai_01': ls[0], 'expert_ai_02': ls[1], 'expert_ai_03': ls[2], 'expert_ai_01_binary': bs[0], 'expert_ai_02_binary': bs[1], 'expert_ai_03_binary': bs[2], 'unique_label_count': lc, 'uncertain_count': uc, 'exact_3_of_3': exact_3, 'exact_2_of_3': exact_2, 'binary_3_of_3': binary_3, 'binary_2_of_3': binary_2, 'majority_label': majority_label, 'majority_count': majority_count, 'consensus_status': status})
    with (OUT / 'expert_ai_panel_disagreement_map.jsonl').open('w') as f:
        for row in rows: f.write(json.dumps(row, ensure_ascii=False) + '\n')
    write_json(OUT / 'expert_ai_panel_consensus_summary.json', {'counts': dict((k, consensus_counts.get(k, 0)) for k in ['EXACT_3_OF_3', 'BINARY_3_OF_3', 'EXACT_2_OF_3', 'BINARY_2_OF_3', 'THREE_WAY_DISAGREEMENT', 'UNCERTAIN_HEAVY']), 'total': sum(consensus_counts.values()), 'precedence': ['UNCERTAIN_HEAVY', 'EXACT_3_OF_3', 'BINARY_3_OF_3', 'EXACT_2_OF_3', 'BINARY_2_OF_3', 'THREE_WAY_DISAGREEMENT'], 'not_ground_truth': True})
    transition_list = [{'from': a, 'to': b, 'count': n} for (a, b), n in sorted(transitions.items(), key=lambda x: (-x[1], x[0]))]
    write_json(OUT / 'expert_ai_panel_transition_analysis.json', {'pairwise_directed_transitions': transition_list, 'dominant_transition_families': transition_list[:10]})

    multiclass_ref = [{'case_id': rows[i]['case_id'], 'evidence': source_data[RUNS[0]]['packet'][i]['evidence'], 'context': source_data[RUNS[0]]['packet'][i].get('context'), 'label': vals[RUNS[0]][i], 'status': 'AI_PANEL_HIGH_CONFIDENCE'} for i in range(120) if rows[i]['consensus_status'] == 'EXACT_3_OF_3']
    binary_ref = [{'case_id': rows[i]['case_id'], 'evidence': source_data[RUNS[0]]['packet'][i]['evidence'], 'context': source_data[RUNS[0]]['packet'][i].get('context'), 'binary_label': binary_vals[RUNS[0]][i], 'status': 'AI_PANEL_BINARY_CONSENSUS'} for i in range(120) if all(binary_vals[r][i] is not None for r in RUNS) and len(set(binary_vals[r][i] for r in RUNS)) == 1]
    write_json(OUT / 'expert_ai_multiclass_consensus_reference.json', {'status': 'AI-DERIVED CONSENSUS REFERENCE', 'not_ground_truth': True, 'cases': multiclass_ref})
    write_json(OUT / 'expert_ai_binary_consensus_reference.json', {'status': 'AI-DERIVED CONSENSUS REFERENCE', 'not_ground_truth': True, 'cases': binary_ref})

    order = sorted(RUNS, key=lambda r: hashlib.sha256(('adjudication-v1:' + r).encode()).hexdigest())
    rater_map = {order[i]: f'RATER_{chr(65+i)}' for i in range(3)}
    adjudication = []
    for i, row in enumerate(rows):
        if row['consensus_status'] == 'EXACT_3_OF_3': continue
        packet_case = source_data[RUNS[0]]['packet'][i]
        adjudication.append({'case_id': row['case_id'], 'evidence': packet_case.get('evidence'), 'neutral_context': packet_case.get('context'), 'annotations': [{'rater': rater_map[r], 'label': vals[r][i], 'note': by_run[r][row['case_id']]['note']} for r in order]})
    write_json(OUT / 'expert_ai_adjudication_packet_v1.json', {'instructions': 'Assign one taxonomy label or UNRESOLVED. Do not infer an expected answer.', 'allowed_labels': LABELS + ['UNRESOLVED'], 'cases': adjudication})
    write_json(OUT / 'expert_ai_adjudication_manifest_v1.json', {'case_count': len(adjudication), 'private_rater_mapping': rater_map, 'model_identities_excluded_from_packet': True, 'source_provenance_excluded_from_packet': True, 'adjudication_run': False})
    instructions = '''# Blinded Expert AI Panel Adjudication\n\nFor each case, review the evidence and neutral context, then assign exactly one allowed taxonomy label or `UNRESOLVED`.\n\nAllowed labels: BENIGN, RECON, SUSPICIOUS, EXPLOITATION, PRIVILEGE_ESCALATION, DATA_ACCESS, PERSISTENCE, OTHER_ATTACK, UNCERTAIN, UNRESOLVED.\n\nUse only the information shown in the packet. Do not seek external information, infer an expected answer, or identify raters/models. Record one label per case and a brief rationale in the adjudicator output.\n'''
    (DOCS / 'EXPERT_AI_ADJUDICATION_INSTRUCTIONS_V1.md').write_text(instructions)
    adj_dir = SRC_ROOT / 'adjudicator_01'; adj_dir.mkdir(exist_ok=True)
    for p in adj_dir.iterdir():
        if p.is_file() and p.name not in {'packet.json', 'INSTRUCTIONS.txt', 'ADJUDICATOR_PROMPT.txt', 'RUN_METADATA_TEMPLATE.json'}:
            raise SystemExit(f'adjudicator workspace contains unexpected file: {p.name}')
    (adj_dir / 'packet.json').write_text(json.dumps({'cases': adjudication, 'allowed_labels': LABELS + ['UNRESOLVED']}, indent=2, ensure_ascii=False) + '\n')
    (adj_dir / 'INSTRUCTIONS.txt').write_text(instructions)
    (adj_dir / 'ADJUDICATOR_PROMPT.txt').write_text('You are the blinded adjudicator. Review packet.json and assign one taxonomy label or UNRESOLVED per case. Do not access external files.\n')
    (adj_dir / 'RUN_METADATA_TEMPLATE.json').write_text(json.dumps({'assigned_model': 'GPT-6-Sol', 'reasoning_effort': 'MEDIUM', 'model_identity_provenance': 'OPERATOR_UI_ATTESTED', 'repository_access_used': False, 'network_access_used': False, 'external_files_accessed': False, 'blindness_violation': False}, indent=2) + '\n')

    csv_path = OUT / 'expert_ai_adjudication_packet_v1.csv'
    with csv_path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['case_id', 'evidence', 'neutral_context', 'rater_a_label', 'rater_a_note', 'rater_b_label', 'rater_b_note', 'rater_c_label', 'rater_c_note']); w.writeheader()
        for x in adjudication:
            d = {'case_id': x['case_id'], 'evidence': x['evidence'], 'neutral_context': x['neutral_context']}
            for a in x['annotations']: d[a['rater'].lower() + '_label'] = a['label']; d[a['rater'].lower() + '_note'] = a['note']
            w.writerow(d)
    bundle = ROOT / 'human_delivery/expert_ai_adjudicator_bundle.zip'; bundle.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in [OUT / 'expert_ai_adjudication_packet_v1.json', csv_path, DOCS / 'EXPERT_AI_ADJUDICATION_INSTRUCTIONS_V1.md']:
            z.write(p, p.name)

    report = f'''# Expert AI Panel Results\n\n## Scope and source\nThe three completed annotation runs were ingested from the corrected authoritative root `{SRC_ROOT}`. The earlier lookup under `results/laya_research/expert_ai_workspaces/` was a source-path resolution failure, not an annotation-integrity failure.\n\n## Integrity\nAll three runs contain 120 packet cases and 120 unique annotations with matching ID sets, valid labels, nonblank notes, matching packet/output hashes, and valid access/blindness metadata. All are VALID. Three different AI model configurations were used; model identity is operator-attested.\n\n## Label distributions\n''' + ''.join(f'- {r}: {json.dumps(dists[r], sort_keys=True)}\n' for r in RUNS) + f'''\n## Agreement\nPairwise multiclass statistics and transition tables are in `results/laya_research/expert_ai_panel_pairwise_multiclass.json`; Fleiss multiclass kappa is `{fmt(fleiss([[vals[r][i] for r in RUNS] for i in range(120)], LABELS))}`. Binary pairwise statistics are in `expert_ai_panel_pairwise_binary.json`; binary Fleiss kappa is `{fmt(fleiss(eligible_rows, ['NEGATIVE', 'POSITIVE']))}` over {len(eligible_rows)} fully eligible cases.\n\n## Consensus structure\n{json.dumps(dict(consensus_counts), sort_keys=True)}. AI-derived multiclass reference candidates: {len(multiclass_ref)}. AI-derived binary consensus candidates: {len(binary_ref)}. These are not ground truth or a gold standard.\n\n## Disagreements\nThe dominant directed transition families are recorded in `expert_ai_panel_transition_analysis.json`. The disagreement map contains one row per case and no model identity.\n\n## Adjudication\n{len(adjudication)} non-unanimous-exact cases are packaged in the blinded packet, CSV, instructions, and isolated workspace. Adjudication has not occurred.\n\n## Freeze and limitations\nThe freeze artifact records source and derived hashes. Agreement does not establish correctness; model identity is operator-attested; no human ground truth exists; the AI-derived references remain reference-building/adjudication-stage; and no Chrollo/Laya predictions or confirmatory evaluation were accessed or run.\n\nScientific status: expert AI panel annotation is complete, but results are reference-building / adjudication-stage, not ground truth.\n'''
    report_path = DOCS / 'EXPERT_AI_PANEL_RESULTS.md'; report_path.write_text(report)

    freeze_targets = [OUT / 'expert_ai_ingestion_path_resolution.json', OUT / 'expert_ai_panel_runs_manifest.json', OUT / 'expert_ai_panel_raw_integrity_report.json', OUT / 'expert_ai_panel_normalization_audit.json', OUT / 'expert_ai_panel_pairwise_multiclass.json', OUT / 'expert_ai_panel_pairwise_binary.json', OUT / 'expert_ai_panel_multirater_reliability.json', OUT / 'expert_ai_panel_disagreement_map.jsonl', OUT / 'expert_ai_panel_consensus_summary.json', OUT / 'expert_ai_panel_transition_analysis.json', OUT / 'expert_ai_multiclass_consensus_reference.json', OUT / 'expert_ai_binary_consensus_reference.json', OUT / 'expert_ai_adjudication_packet_v1.json', OUT / 'expert_ai_adjudication_packet_v1.csv', OUT / 'expert_ai_adjudication_manifest_v1.json', DOCS / 'EXPERT_AI_ADJUDICATION_INSTRUCTIONS_V1.md', report_path]
    freeze = {'valid_runs': 3, 'invalid_runs': 0, 'source_path_resolution_failure_occurred': True, 'source_path_resolution_failure_invalidated_runs': False, 'annotations_rerun': False, 'predictions_accessed': False, 'ground_truth_created': False, 'confirmatory_analysis_run': False, 'adjudication_run': False, 'source_hashes': {}, 'copied_repository_hashes': {}, 'new_artifact_hashes': {}}
    for r in RUNS:
        freeze['source_hashes'][r] = {'annotation': sha(source_data[r]['paths']['completed_annotations.json']), 'metadata': sha(source_data[r]['paths']['run_metadata.json'])}
        freeze['copied_repository_hashes'][r] = {'annotation': sha(labels_dir / f'{r}.json'), 'metadata': sha(prov_dir / f'{r}_metadata.json')}
    for p in freeze_targets: freeze['new_artifact_hashes'][str(p.relative_to(ROOT))] = sha(p)
    freeze['new_artifact_hashes']['human_delivery/expert_ai_adjudicator_bundle.zip'] = sha(bundle)
    freeze_path = OUT / 'expert_ai_panel_results_freeze_v1.json'; write_json(freeze_path, freeze)
    print(json.dumps({'distributions': dists, 'pairs': pairs, 'binary_pairs': binary_pairs, 'multiclass_fleiss': freeze['new_artifact_hashes'].get('x'), 'binary_fleiss': fmt(fleiss(eligible_rows, ['NEGATIVE', 'POSITIVE'])), 'consensus': dict(consensus_counts), 'adjudication_cases': len(adjudication), 'bundle_sha256': sha(bundle), 'freeze_sha256': sha(freeze_path)}, indent=2))

if __name__ == '__main__': main()
