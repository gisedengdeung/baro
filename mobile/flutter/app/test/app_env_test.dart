import 'package:flutter_test/flutter_test.dart';
import 'package:stop_mobile_app/config/app_env.dart';

void main() {
  test('AppEnv has default API_BASE_URL', () {
    expect(AppEnv.apiBaseUrl, isNotEmpty);
  });
}
