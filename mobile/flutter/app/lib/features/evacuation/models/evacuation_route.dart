class RoutePoint {
  RoutePoint({required this.x, required this.y});

  final double x;
  final double y;

  factory RoutePoint.fromJson(Map<String, dynamic> json) {
    return RoutePoint(
      x: (json['x'] as num?)?.toDouble() ?? 0,
      y: (json['y'] as num?)?.toDouble() ?? 0,
    );
  }
}

class EvacuationRoute {
  EvacuationRoute({
    required this.edgeId,
    required this.startNodeId,
    required this.endNodeId,
    required this.totalDistance,
    required this.estimatedSeconds,
    required this.polyline,
    required this.steps,
    required this.nodeIds,
    this.zoneId,
    this.incidentType,
  });

  final String edgeId;
  final String? zoneId;
  final String? incidentType;
  final String startNodeId;
  final String endNodeId;
  final double totalDistance;
  final double estimatedSeconds;
  final List<RoutePoint> polyline;
  final List<String> steps;
  final List<String> nodeIds;

  factory EvacuationRoute.fromJson(Map<String, dynamic> json) {
    final points = (json['polyline'] as List<dynamic>? ?? const [])
        .map((point) => RoutePoint.fromJson((point as Map).cast<String, dynamic>()))
        .toList();
    return EvacuationRoute(
      edgeId: (json['edge_id'] ?? '').toString(),
      zoneId: json['zone_id']?.toString(),
      incidentType: json['incident_type']?.toString(),
      startNodeId: (json['start_node_id'] ?? '').toString(),
      endNodeId: (json['end_node_id'] ?? '').toString(),
      totalDistance: (json['total_distance'] as num?)?.toDouble() ?? 0,
      estimatedSeconds: (json['estimated_seconds'] as num?)?.toDouble() ?? 0,
      polyline: points,
      steps: (json['steps'] as List<dynamic>? ?? const []).map((e) => e.toString()).toList(),
      nodeIds: (json['node_ids'] as List<dynamic>? ?? const []).map((e) => e.toString()).toList(),
    );
  }
}
