import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/app_env.dart';
import '../../features/auth/state/session_controller.dart';
import 'auth_interceptor.dart';

BaseOptions _buildBaseOptions() {
  return BaseOptions(
    baseUrl: AppEnv.apiBaseUrl,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 15),
    sendTimeout: const Duration(seconds: 15),
    headers: {'Content-Type': 'application/json'},
  );
}

final baseDioProvider = Provider<Dio>((ref) {
  return Dio(_buildBaseOptions());
});

final authedDioProvider = Provider<Dio>((ref) {
  final sessionController = ref.read(sessionControllerProvider.notifier);
  final dio = Dio(_buildBaseOptions());

  dio.interceptors.add(
    AuthInterceptor(
      readAccessToken: () => ref.read(sessionControllerProvider).accessToken,
      onUnauthorized: () {
        sessionController.forceLogout();
      },
    ),
  );

  return dio;
});
