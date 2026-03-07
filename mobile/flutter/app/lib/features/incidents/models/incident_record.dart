class IncidentRecord {
  IncidentRecord({
    required this.id,
    required this.edgeId,
    required this.incidentType,
    required this.severity,
    required this.status,
    required this.detectedAt,
    required this.createdAt,
    required this.updatedAt,
    this.zoneId,
    this.details = const {},
    this.snapshotUrl,
  });

  final String id;
  final String edgeId;
  final String incidentType;
  final String severity;
  final String status;
  final String? zoneId;
  final Map<String, dynamic> details;
  final String? snapshotUrl;
  final DateTime detectedAt;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory IncidentRecord.fromJson(Map<String, dynamic> json) {
    DateTime parseDate(String key) {
      final raw = (json[key] ?? '').toString();
      return DateTime.tryParse(raw)?.toLocal() ?? DateTime.now();
    }

    return IncidentRecord(
      id: (json['id'] ?? '').toString(),
      edgeId: (json['edge_id'] ?? '').toString(),
      incidentType: (json['incident_type'] ?? '').toString(),
      severity: (json['severity'] ?? 'HIGH').toString(),
      status: (json['status'] ?? 'OPEN').toString(),
      zoneId: json['zone_id']?.toString(),
      details: (json['details'] as Map?)?.cast<String, dynamic>() ?? const {},
      snapshotUrl: json['snapshot_url']?.toString(),
      detectedAt: parseDate('detected_at'),
      createdAt: parseDate('created_at'),
      updatedAt: parseDate('updated_at'),
    );
  }
}
