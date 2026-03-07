import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/storage/token_storage.dart';
import '../models/login_response.dart';
import '../repositories/auth_repository.dart';
import 'session_state.dart';

final tokenStorageProvider = Provider<TokenStorage>((ref) {
  return TokenStorage(const FlutterSecureStorage());
});

final sessionControllerProvider =
    StateNotifierProvider<SessionController, SessionState>((ref) {
  final authRepository = ref.watch(authRepositoryProvider);
  final tokenStorage = ref.watch(tokenStorageProvider);
  return SessionController(authRepository, tokenStorage)..loadFromStorage();
});

class SessionController extends StateNotifier<SessionState> {
  SessionController(this._authRepository, this._tokenStorage)
      : super(SessionState.initial);

  final AuthRepository _authRepository;
  final TokenStorage _tokenStorage;

  Future<void> loadFromStorage() async {
    final token = await _tokenStorage.readAccessToken();
    if (token == null || token.isEmpty) {
      return;
    }
    state = state.copyWith(accessToken: token);
  }

  Future<void> login({required String email, required String password}) async {
    state = state.copyWith(isLoading: true);
    try {
      final LoginResponse response = await _authRepository.login(
        email: email,
        password: password,
      );
      await _tokenStorage.saveAccessToken(response.accessToken);
      state = state.copyWith(
        isLoading: false,
        accessToken: response.accessToken,
        userId: response.userId,
        userEmail: response.userEmail,
        userRole: response.userRole,
      );
    } catch (_) {
      state = state.copyWith(isLoading: false);
      rethrow;
    }
  }

  Future<void> logout() async {
    await _tokenStorage.clear();
    state = SessionState.initial;
  }

  Future<void> forceLogout() async {
    await logout();
  }
}
