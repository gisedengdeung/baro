class SessionState {
  const SessionState({
    this.userId,
    this.userEmail,
    this.userRole,
    this.accessToken,
    this.isLoading = false,
  });

  final String? userId;
  final String? userEmail;
  final String? userRole;
  final String? accessToken;
  final bool isLoading;

  SessionState copyWith({
    String? userId,
    String? userEmail,
    String? userRole,
    String? accessToken,
    bool? isLoading,
    bool clearToken = false,
  }) {
    return SessionState(
      userId: userId ?? this.userId,
      userEmail: userEmail ?? this.userEmail,
      userRole: userRole ?? this.userRole,
      accessToken: clearToken ? null : (accessToken ?? this.accessToken),
      isLoading: isLoading ?? this.isLoading,
    );
  }

  static const initial = SessionState();
}
