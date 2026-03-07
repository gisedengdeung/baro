import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../config/app_env.dart';
import '../../auth/state/session_controller.dart';
import '../models/incident_record.dart';
import '../repositories/incident_repository.dart';

final incidentDetailProvider =
    FutureProvider.family<IncidentRecord, String>((ref, incidentId) async {
  final repository = ref.watch(incidentRepositoryProvider);
  return repository.getIncident(incidentId);
});

class IncidentDetailScreen extends ConsumerWidget {
  const IncidentDetailScreen({super.key, required this.incidentId});

  final String incidentId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(incidentDetailProvider(incidentId));
    final token = ref.watch(sessionControllerProvider).accessToken;

    return Scaffold(
      appBar: AppBar(title: const Text('사건 상세')),
      body: detailAsync.when(
        data: (incident) {
          final snapshotPath =
              incident.snapshotUrl ?? '/api/incidents/${incident.id}/snapshot';
          final snapshotUrl = snapshotPath.startsWith('http')
              ? snapshotPath
              : '${AppEnv.apiBaseUrl}$snapshotPath';

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('유형: ${incident.incidentType}'),
              Text('심각도: ${incident.severity}'),
              Text('상태: ${incident.status}'),
              Text('Edge: ${incident.edgeId}'),
              Text('Zone: ${incident.zoneId ?? '-'}'),
              Text('감지시각: ${DateFormat('yyyy-MM-dd HH:mm:ss').format(incident.detectedAt)}'),
              const SizedBox(height: 12),
              const Text('스냅샷'),
              const SizedBox(height: 8),
              AspectRatio(
                aspectRatio: 16 / 9,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.grey.shade400),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Image.network(
                      snapshotUrl,
                      fit: BoxFit.cover,
                      headers: token == null
                          ? null
                          : <String, String>{'Authorization': 'Bearer $token'},
                      errorBuilder: (context, error, stackTrace) {
                        return const Center(child: Text('스냅샷을 불러오지 못했습니다.'));
                      },
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: () {
                  final uri = Uri(
                    path: '/route',
                    queryParameters: {
                      'edgeId': incident.edgeId,
                      if (incident.zoneId != null) 'zoneId': incident.zoneId,
                      'incidentType': incident.incidentType,
                    },
                  );
                  context.push(uri.toString());
                },
                icon: const Icon(Icons.route),
                label: const Text('대피 경로 보기'),
              ),
            ],
          );
        },
        error: (error, stack) => Center(child: Text('상세 조회 실패: $error')),
        loading: () => const Center(child: CircularProgressIndicator()),
      ),
    );
  }
}
