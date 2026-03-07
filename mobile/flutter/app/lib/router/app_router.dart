import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/presentation/login_screen.dart';
import '../features/auth/state/session_controller.dart';
import '../features/evacuation/presentation/evacuation_route_screen.dart';
import '../features/incidents/presentation/incident_detail_screen.dart';
import '../features/incidents/presentation/incident_list_screen.dart';
import '../features/settings/presentation/settings_screen.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final isAuthenticated = ref.watch(
    sessionControllerProvider.select((state) => state.accessToken != null),
  );

  return GoRouter(
    initialLocation: isAuthenticated ? '/incidents' : '/login',
    redirect: (context, state) {
      final inLogin = state.matchedLocation == '/login';
      if (!isAuthenticated && !inLogin) {
        return '/login';
      }
      if (isAuthenticated && inLogin) {
        return '/incidents';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/incidents',
        builder: (context, state) => const IncidentListScreen(),
      ),
      GoRoute(
        path: '/incidents/:id',
        builder: (context, state) => IncidentDetailScreen(
          incidentId: state.pathParameters['id']!,
        ),
      ),
      GoRoute(
        path: '/route',
        builder: (context, state) => EvacuationRouteScreen(
          edgeId: state.uri.queryParameters['edgeId'] ?? 'edge-default',
          zoneId: state.uri.queryParameters['zoneId'],
          incidentType: state.uri.queryParameters['incidentType'],
        ),
      ),
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SettingsScreen(),
      ),
    ],
  );
});
