import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenStorage {
  TokenStorage(this._storage);

  static const accessTokenKey = 'access_token';
  final FlutterSecureStorage _storage;

  Future<void> saveAccessToken(String token) async {
    await _storage.write(key: accessTokenKey, value: token);
  }

  Future<String?> readAccessToken() async {
    return _storage.read(key: accessTokenKey);
  }

  Future<void> clear() async {
    await _storage.delete(key: accessTokenKey);
  }
}
