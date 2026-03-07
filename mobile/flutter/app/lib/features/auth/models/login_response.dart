class LoginResponse {
  LoginResponse({
    required this.userId,
    required this.userEmail,
    required this.userRole,
    required this.accessToken,
  });

  final String userId;
  final String userEmail;
  final String userRole;
  final String accessToken;

  factory LoginResponse.fromJson(Map<String, dynamic> json) {
    final user = (json['user'] as Map<String, dynamic>? ?? const {});
    return LoginResponse(
      userId: (user['id'] ?? '').toString(),
      userEmail: (user['email'] ?? '').toString(),
      userRole: (user['role'] ?? '').toString(),
      accessToken: (json['access_token'] ?? '').toString(),
    );
  }
}
