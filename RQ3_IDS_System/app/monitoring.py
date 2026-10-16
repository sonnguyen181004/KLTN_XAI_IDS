"""Read-only dashboard queries, scoped consistently across charts and tables."""
import json

JOIN = ''' FROM FlowRecord f JOIN Prediction p ON p.flow_id=f.flow_id
 LEFT JOIN AlertRecord a ON a.flow_id=f.flow_id
 LEFT JOIN Reliability r ON r.alert_id=a.alert_id '''
SELECT = '''SELECT f.flow_id, f.received_at, f.source, f.capture_run_id, f.run_name,
 f.flow_timestamp, f.flow_timestamp_utc, f.src_ip, f.dst_ip, f.src_port, f.label_true,
 p.predicted_label, p.probabilities_json, p.predicted_at, p.model_version,
 a.alert_id, a.status, a.explanation_status, a.created_at, r.branch, r.branch_reason,
 json_extract(f.features_json, '$."Dst Port"') AS dst_port,
 json_extract(f.features_json, '$."Protocol"') AS protocol,
 r.shap_top5_json, r.lime_top5_json, r.lime_local_r2, r.agreement_jaccard5,
 r.faithfulness_proxy_drop, r.env_fingerprint_count, r.env_fingerprint_flag,
 r.rare_class_flag, r.stability_lookup, r.robustness_lookup_json'''


def rows(cursor):
    return [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]


def scope(filters):
    clauses, values = [], []
    for key, column in {'capture_run_id': 'f.capture_run_id', 'source': 'f.source',
                        'label': 'p.predicted_label', 'branch': 'r.branch', 'group_key': 'a.group_key'}.items():
        value = filters.get(key)
        if value is not None:
            if key == 'capture_run_id' and value == '__legacy__':
                clauses.append('f.capture_run_id IS NULL')
            else:
                clauses.append(column + '=?'); values.append(value)
    for key, op in [('since', '>='), ('until', '<=')]:
        if filters.get(key):
            clauses.append('f.received_at' + op + '?'); values.append(filters[key])
    if filters.get('alerts_only'):
        clauses.append('a.alert_id IS NOT NULL')
    return ' WHERE ' + (' AND '.join(clauses) or '1=1'), values


def decorate(row):
    for key in ('probabilities', 'features', 'shap_top5', 'lime_top5', 'robustness_lookup'):
        if key + '_json' in row:
            raw = row.pop(key + '_json')
            row[key] = json.loads(raw) if raw else None
    row['is_alert'] = row.get('alert_id') is not None
    if not row['is_alert']:
        row['explanation_status'] = 'not_required'
    elif row.get('shap_top5'):
        row['explanation_status'] = 'processed'
    row['confidence'] = (row.get('probabilities') or {}).get(row['predicted_label'])
    return row


def flows(conn, filters, limit=50, offset=0):
    where, values = scope(filters)
    total = conn.execute('SELECT COUNT(*)' + JOIN + where, values).fetchone()[0]
    data = rows(conn.execute(SELECT + JOIN + where +
                ' ORDER BY f.received_at DESC, f.flow_id DESC LIMIT ? OFFSET ?', (*values, limit, offset)))
    return {'count': total, 'flows': [decorate(row) for row in data]}


def detail(conn, flow_id):
    data = rows(conn.execute(SELECT + ', f.features_json' + JOIN + ' WHERE f.flow_id=?', (flow_id,)))
    if not data:
        return None
    result = decorate(data[0])
    result['timing'] = rows(conn.execute('SELECT step, duration_ms, recorded_at FROM Timing WHERE flow_id=? ORDER BY timing_id', (flow_id,)))
    return result


def runs(conn):
    return {'runs': rows(conn.execute('''SELECT COALESCE(capture_run_id, '__legacy__') AS capture_run_id,
 MAX(run_name) AS run_name, MIN(received_at) AS started_at, MAX(received_at) AS last_received_at,
 COUNT(*) AS count FROM FlowRecord GROUP BY capture_run_id ORDER BY last_received_at DESC'''))}


def summary(conn, filters):
    where, values = scope(filters)
    result = rows(conn.execute('''SELECT COUNT(*) AS flows,
 COALESCE(SUM(p.predicted_label='Benign'),0) AS benign,
 COALESCE(SUM(a.alert_id IS NOT NULL),0) AS alerts,
 COALESCE(SUM(r.shap_top5_json IS NOT NULL),0) AS processed,
 COALESCE(SUM(a.explanation_status='queued' AND r.shap_top5_json IS NULL),0) AS queued,
 COALESCE(SUM(a.explanation_status='dropped_queue_full'),0) AS dropped,
 COALESCE(SUM(a.explanation_status='failed'),0) AS failed,
 MAX(f.received_at) AS last_received_at''' + JOIN + where, values))[0]
    result['labels'] = rows(conn.execute('SELECT p.predicted_label AS label, COUNT(*) AS count' + JOIN + where + ' GROUP BY p.predicted_label ORDER BY count DESC', values))
    result['timeline'] = rows(conn.execute('''SELECT strftime('%Y-%m-%dT%H:%M:00Z', f.received_at) AS minute,
 CASE WHEN a.alert_id IS NULL THEN 'Benign' ELSE 'Cảnh báo' END AS category, COUNT(*) AS count''' + JOIN + where + ' GROUP BY minute, category ORDER BY minute', values))
    result['groups'] = rows(conn.execute('''SELECT a.group_key, p.predicted_label AS label,
 f.src_ip, f.dst_ip, CAST(strftime('%s', f.received_at) AS INTEGER)/300 AS window,
 MIN(f.received_at) AS first_seen, MAX(f.received_at) AS last_seen, COUNT(*) AS count''' + JOIN + where +
 ' AND a.alert_id IS NOT NULL GROUP BY a.group_key, window ORDER BY last_seen DESC LIMIT 100', values))
    return result
