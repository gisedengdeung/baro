import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/network/dio_provider.dart';

final mobileDeviceRepositoryProvider = Provider<MobileDeviceRepository>((ref) {
  final dio = ref.watch(authedDioProvider);
  return MobileDeviceRepository(dio);
});

class MobileDeviceRepository {
  MobileDeviceRepository(this._dio);

  final Dio _dio;

  Future<void> registerDevice({
    required String platform,
    required String fcmToken,
    required List<String> edgeScope,
  }) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/api/mobile/devices/register',
        data: {
          'platform': platform,
          'fcm_token': fcmToken,
          'edge_scope': edgeScope,
        },
      );
    } on DioException catch (e) {
      throw ApiException(
        '디바이스 등록에 실패했습니다.',
        statusCode: e.response?.statusCode,
      );
    }
  }
}
