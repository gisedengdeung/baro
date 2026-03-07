import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/evacuation_route.dart';
import '../repositories/evacuation_repository.dart';

class RouteQuery {
  const RouteQuery({required this.edgeId, this.zoneId, this.incidentType});

  final String edgeId;
  final String? zoneId;
  final String? incidentType;

  @override
  bool operator ==(Object other) {
    return other is RouteQuery &&
        other.edgeId == edgeId &&
        other.zoneId == zoneId &&
        other.incidentType == incidentType;
  }

  @override
  int get hashCode => Object.hash(edgeId, zoneId, incidentType);
}

final evacuationRouteProvider =
    FutureProvider.family<EvacuationRoute, RouteQuery>((ref, query) async {
  final repository = ref.watch(evacuationRepositoryProvider);
  return repository.getRoute(
    edgeId: query.edgeId,
    zoneId: query.zoneId,
    incidentType: query.incidentType,
  );
});

class EvacuationRouteScreen extends ConsumerWidget {
  const EvacuationRouteScreen({
    super.key,
    required this.edgeId,
    this.zoneId,
    this.incidentType,
  });

  final String edgeId;
  final String? zoneId;
  final String? incidentType;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final query = RouteQuery(edgeId: edgeId, zoneId: zoneId, incidentType: incidentType);
    final routeAsync = ref.watch(evacuationRouteProvider(query));

    return Scaffold(
      appBar: AppBar(title: const Text('대피 경로')),
      body: routeAsync.when(
        data: (route) {
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('Edge: ${route.edgeId}'),
              Text('Zone: ${route.zoneId ?? '-'}'),
              Text('Incident: ${route.incidentType ?? '-'}'),
              Text('거리: ${route.totalDistance.toStringAsFixed(1)} m'),
              Text('예상 시간: ${route.estimatedSeconds.toStringAsFixed(0)} sec'),
              const SizedBox(height: 16),
              SizedBox(
                height: 260,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.grey.shade400),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: CustomPaint(
                    painter: RoutePainter(route.polyline),
                    child: const SizedBox.expand(),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const Text('안내 단계', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              ...route.steps.asMap().entries.map(
                    (entry) => ListTile(
                      dense: true,
                      leading: CircleAvatar(radius: 12, child: Text('${entry.key + 1}')),
                      title: Text(entry.value),
                    ),
                  ),
            ],
          );
        },
        error: (error, stack) => Center(child: Text('경로 조회 실패: $error')),
        loading: () => const Center(child: CircularProgressIndicator()),
      ),
    );
  }
}

class RoutePainter extends CustomPainter {
  RoutePainter(this.points);

  final List<RoutePoint> points;

  @override
  void paint(Canvas canvas, Size size) {
    final framePaint = Paint()
      ..color = Colors.grey.shade300
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    canvas.drawRect(Offset.zero & size, framePaint);

    if (points.length < 2) {
      final tp = TextPainter(
        text: const TextSpan(
          text: '경로 데이터가 없습니다.',
          style: TextStyle(color: Colors.black54),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: size.width);
      tp.paint(canvas, Offset((size.width - tp.width) / 2, (size.height - tp.height) / 2));
      return;
    }

    final minX = points.map((p) => p.x).reduce(min);
    final maxX = points.map((p) => p.x).reduce(max);
    final minY = points.map((p) => p.y).reduce(min);
    final maxY = points.map((p) => p.y).reduce(max);

    final width = (maxX - minX).abs() < 1e-6 ? 1.0 : (maxX - minX);
    final height = (maxY - minY).abs() < 1e-6 ? 1.0 : (maxY - minY);

    const padding = 20.0;
    final scaleX = (size.width - padding * 2) / width;
    final scaleY = (size.height - padding * 2) / height;
    final scale = min(scaleX, scaleY);

    Offset mapPoint(RoutePoint p) {
      final x = padding + (p.x - minX) * scale;
      final y = size.height - padding - (p.y - minY) * scale;
      return Offset(x, y);
    }

    final path = Path()..moveTo(mapPoint(points.first).dx, mapPoint(points.first).dy);
    for (var i = 1; i < points.length; i++) {
      final pt = mapPoint(points[i]);
      path.lineTo(pt.dx, pt.dy);
    }

    final pathPaint = Paint()
      ..color = const Color(0xFF1B6CA8)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;

    canvas.drawPath(path, pathPaint);

    final pointPaint = Paint()..color = Colors.redAccent;
    for (final p in points) {
      final pt = mapPoint(p);
      canvas.drawCircle(pt, 3.5, pointPaint);
    }

    final start = mapPoint(points.first);
    final end = mapPoint(points.last);
    canvas.drawCircle(start, 6, Paint()..color = Colors.green.shade700);
    canvas.drawCircle(end, 6, Paint()..color = Colors.deepOrange.shade700);
  }

  @override
  bool shouldRepaint(covariant RoutePainter oldDelegate) {
    return oldDelegate.points != points;
  }
}
