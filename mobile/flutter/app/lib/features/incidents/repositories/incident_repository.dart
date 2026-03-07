import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/network/dio_provider.dart';
import '../models/incident_record.dart';

final incidentRepositoryProvider = Provider<IncidentRepository>((ref) {
  final dio = ref.watch(authedDioProvider);
  return IncidentRepository(dio);
});

class IncidentRepository {
  IncidentRepository(this._dio);

  final Dio _dio;

  Future<List<IncidentRecord>> listIncidents({int limit = 50}) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/api/incidents',
        queryParameters: {'limit': limit},
      );
      final list = response.data ?? const [];
      return list
          .map((item) => IncidentRecord.fromJson((item as Map).cast<String, dynamic>()))
          .toList();
    } on DioException catch (e) {
      throw ApiException('사건 목록을 불러오지 못했습니다.', statusCode: e.response?.statusCode);
    }
  }

  Future<IncidentRecord> getIncident(String incidentId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/api/incidents/$incidentId');
      final data = response.data;
      if (data == null) {
        throw ApiException('사건 상세 응답이 비어 있습니다.');
      }
      return IncidentRecord.fromJson(data);
    } on DioException catch (e) {
      throw ApiException('사건 상세를 불러오지 못했습니다.', statusCode: e.response?.statusCode);
    }
  }
}
