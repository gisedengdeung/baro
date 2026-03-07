import 'package:flutter_test/flutter_test.dart';
import 'package:stop_mobile_app/features/incidents/models/incident_record.dart';

void main() {
  test('IncidentRecord.fromJson parses required fields', () {
    final record = IncidentRecord.fromJson({
      'id': 'inc-1',
      'edge_id': 'edge-default',
      'incident_type': 'FIRE_DETECTED',
      'severity': 'CRITICAL',
      'status': 'OPEN',
      'detected_at': '2026-03-01T00:00:00Z',
      'created_at': '2026-03-01T00:00:00Z',
      'updated_at': '2026-03-01T00:00:00Z',
    });

    expect(record.id, 'inc-1');
    expect(record.incidentType, 'FIRE_DETECTED');
    expect(record.severity, 'CRITICAL');
  });
}
