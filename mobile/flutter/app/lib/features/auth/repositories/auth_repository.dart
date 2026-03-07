import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/network/dio_provider.dart';
import '../models/login_response.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final dio = ref.watch(baseDioProvider);
  return AuthRepository(dio);
});

class AuthRepository {
  AuthRepository(this._dio);

  final Dio _dio;

  Future<LoginResponse> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/auth/login',
        data: {'email': email, 'password': password},
      );
      final data = response.data;
      if (data == null || (data['access_token'] ?? '').toString().isEmpty) {
        throw ApiException('로그인 응답에 access_token이 없습니다.');
      }
      return LoginResponse.fromJson(data);
    } on DioException catch (e) {
      throw ApiException(
        e.response?.data is Map<String, dynamic>
            ? (e.response?.data['detail']?.toString() ?? '로그인 요청에 실패했습니다.')
            : '로그인 요청에 실패했습니다.',
        statusCode: e.response?.statusCode,
      );
    }
  }
}
