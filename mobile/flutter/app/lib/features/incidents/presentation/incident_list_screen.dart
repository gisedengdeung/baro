import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../auth/state/session_controller.dart';
import '../models/incident_record.dart';
import '../repositories/incident_repository.dart';

final incidentListProvider = FutureProvider<List<IncidentRecord>>((ref) async {
  final repository = ref.watch(incidentRepositoryProvider);
  return repository.listIncidents();
});

class IncidentListScreen extends ConsumerWidget {
  const IncidentListScreen({super.key});

  Color _severityColor(String severity) {
    switch (severity) {
      case 'CRITICAL':
        return Colors.red.shade800;
      case 'HIGH':
        return Colors.orange.shade700;
      case 'MEDIUM':
        return Colors.amber.shade700;
      default:
        return Colors.blueGrey;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final incidentAsync = ref.watch(incidentListProvider);
    final session = ref.watch(sessionControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('사건 목록'),
        actions: [
          IconButton(
            tooltip: '설정',
            onPressed: () => context.push('/settings'),
            icon: const Icon(Icons.settings),
          ),
          IconButton(
            tooltip: '로그아웃',
            onPressed: () async {
              await ref.read(sessionControllerProvider.notifier).logout();
              if (context.mounted) {
                context.go('/login');
              }
            },
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(incidentListProvider);
          await ref.read(incidentListProvider.future);
        },
        child: incidentAsync.when(
          data: (items) {
            if (items.isEmpty) {
              return ListView(
                children: const [
                  SizedBox(height: 180),
                  Center(child: Text('표시할 사건이 없습니다.')),
                ],
              );
            }

            return ListView.builder(
              itemCount: items.length,
              itemBuilder: (context, index) {
                final incident = items[index];
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  child: ListTile(
                    onTap: () => context.push('/incidents/${incident.id}'),
                    title: Text('${incident.incidentType} (${incident.edgeId})'),
                    subtitle: Text(
                      '${DateFormat('yyyy-MM-dd HH:mm:ss').format(incident.detectedAt)}\n'
                      'zone=${incident.zoneId ?? '-'} / status=${incident.status}',
                    ),
                    isThreeLine: true,
                    trailing: Chip(
                      label: Text(incident.severity),
                      backgroundColor: _severityColor(incident.severity),
                      labelStyle: const TextStyle(color: Colors.white),
                    ),
                  ),
                );
              },
            );
          },
          error: (error, stack) => ListView(
            children: [
              const SizedBox(height: 180),
              Center(child: Text('목록 조회 실패: $error')),
            ],
          ),
          loading: () => const Center(child: CircularProgressIndicator()),
        ),
      ),
      bottomNavigationBar: session.userEmail == null
          ? null
          : Padding(
              padding: const EdgeInsets.all(12),
              child: Text(
                '로그인: ${session.userEmail}',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
    );
  }
}
