import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/network/dio_provider.dart';
import '../models/evacuation_route.dart';

final evacuationRepositoryProvider = Provider<EvacuationRepository>((ref) {
  final dio = ref.watch(authedDioProvider);
  return EvacuationRepository(dio);
});

class EvacuationRepository {
  EvacuationRepository(this._dio);

  final Dio _dio;

  Future<EvacuationRoute> getRoute({
    required String edgeId,
    String? zoneId,
    String? incidentType,
  }) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/evacuation/route',
        queryParameters: {
          'edge_id': edgeId,
          if (zoneId != null && zoneId.isNotEmpty) 'zone_id': zoneId,
          if (incidentType != null && incidentType.isNotEmpty)
            'incident_type': incidentType,
        },
      );
      final data = response.data;
      if (data == null) {
        throw ApiException('대피 경로 응답이 비어 있습니다.');
      }
      return EvacuationRoute.fromJson(data);
    } on DioException catch (e) {
      throw ApiException('대피 경로를 불러오지 못했습니다.', statusCode: e.response?.statusCode);
    }
  }
}
