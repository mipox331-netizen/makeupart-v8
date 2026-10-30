import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:image_picker/image_picker.dart';

class ApiClient {
  static const baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://makeupart-api.onrender.com/api/v1',
  );
  static const _accessKey = 'makeupart_access_token';
  static const _refreshKey = 'makeupart_refresh_token';

  final FlutterSecureStorage storage;
  final void Function()? onSessionExpired;
  late final Dio dio;
  Future<String?>? _refreshInFlight;

  ApiClient({
    FlutterSecureStorage? storage,
    this.onSessionExpired,
  }) : storage = storage ?? const FlutterSecureStorage() {
    dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        // Render Free services can take around a minute to wake after idle.
        // Give the first request enough time to survive a normal cold start.
        connectTimeout: const Duration(seconds: 75),
        sendTimeout: const Duration(seconds: 90),
        receiveTimeout: const Duration(seconds: 120),
        headers: {'Accept': 'application/json'},
      ),
    );

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await this.storage.read(key: _accessKey);
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          final request = error.requestOptions;
          final isUnauthorized = error.response?.statusCode == 401;
          final alreadyRetried = request.extra['authRetried'] == true;
          final isAuthEndpoint = request.path.contains('/auth/login') ||
              request.path.contains('/auth/refresh') ||
              request.path.contains('/auth/logout');

          if (!isUnauthorized || isAuthEndpoint) {
            handler.next(error);
            return;
          }

          // A replay that still returns 401 means the session is no longer
          // usable. Do not refresh endlessly; clear tokens and return to login.
          if (alreadyRetried) {
            await logoutLocal();
            onSessionExpired?.call();
            handler.next(error);
            return;
          }

          final refreshToken = await this.storage.read(key: _refreshKey);
          if (refreshToken == null || refreshToken.isEmpty) {
            await logoutLocal();
            onSessionExpired?.call();
            handler.next(error);
            return;
          }

          final accessToken = await _refreshAccessToken(refreshToken);
          if (accessToken == null) {
            await logoutLocal();
            onSessionExpired?.call();
            handler.next(error);
            return;
          }

          request.extra['authRetried'] = true;
          request.headers['Authorization'] = 'Bearer $accessToken';
          try {
            final response = await dio.fetch(request);
            handler.resolve(response);
          } on DioException catch (retryError) {
            if (retryError.response?.statusCode == 401) {
              await logoutLocal();
              onSessionExpired?.call();
            }
            handler.next(retryError);
          }
        },
      ),
    );
  }

  Future<bool> hasSession() async =>
      (await storage.read(key: _accessKey))?.isNotEmpty == true;

  Future<Map<String, dynamic>> currentUser() async {
    final response = await dio.get('/auth/me');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> getSubscription() async {
    final response = await dio.get('/subscriptions/me');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<List<Map<String, dynamic>>> getAdminUsers() async {
    final response = await dio.get('/admin/users');
    final rows = (response.data as List<dynamic>? ?? const <dynamic>[]);
    return rows.map((row) => Map<String, dynamic>.from(row as Map)).toList();
  }

  Future<Map<String, dynamic>> setAdminUserStatus({
    required String userId,
    required bool active,
  }) async {
    final response = await dio.patch(
      '/admin/users/$userId/status',
      data: {'is_active': active},
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<List<Map<String, dynamic>>> getAdminSubscriptions() async {
    final response = await dio.get('/admin/subscriptions');
    final rows = (response.data as List<dynamic>? ?? const <dynamic>[]);
    return rows.map((row) => Map<String, dynamic>.from(row as Map)).toList();
  }

  Future<Map<String, dynamic>> activateAdminSubscription({
    required String salonId,
    required String plan,
    int days = 30,
  }) async {
    final response = await dio.post(
      '/admin/subscriptions/$salonId/activate',
      data: {'plan': plan, 'days': days},
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> suspendAdminSubscription(String salonId) async {
    final response = await dio.post('/admin/subscriptions/$salonId/suspend');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> recordAdminPayment({
    required String salonId,
    required String plan,
    required String amount,
    String currency = 'TZS',
    required String paymentMethod,
    int periodDays = 30,
    String? reference,
    String? notes,
  }) async {
    final response = await dio.post(
      '/admin/payments/record',
      data: {
        'salon_id': salonId,
        'plan': plan,
        'amount': amount,
        'currency': currency,
        'payment_method': paymentMethod,
        'period_days': periodDays,
        if (reference != null && reference.trim().isNotEmpty)
          'reference': reference.trim(),
        if (notes != null && notes.trim().isNotEmpty) 'notes': notes.trim(),
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> getAdminRevenueSummary({
    String period = 'month',
  }) async {
    final response = await dio.get(
      '/admin/payments/summary',
      queryParameters: {'period': period},
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<void> register({
    required String salonName,
    required String ownerFullName,
    required String email,
    required String password,
    String? phone,
  }) async {
    await dio.post(
      '/auth/register',
      data: {
        'salon_name': salonName,
        'owner_full_name': ownerFullName,
        'email': email,
        'password': password,
        if (phone != null && phone.trim().isNotEmpty) 'phone': phone.trim(),
      },
    );
  }

  Future<List<Map<String, dynamic>>> listCustomers() async {
    final response = await dio.get('/customers');
    final rows = (response.data as List<dynamic>? ?? const <dynamic>[]);
    return rows
        .map((row) => Map<String, dynamic>.from(row as Map))
        .toList();
  }

  Future<Map<String, dynamic>> createCustomer({
    required String firstName,
    required String lastName,
    String? phone,
  }) async {
    final response = await dio.post(
      '/customers',
      data: {
        'first_name': firstName,
        'last_name': lastName,
        if (phone != null && phone.trim().isNotEmpty) 'phone': phone.trim(),
        'consent_required': true,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>?> getActiveConsent(String customerId) async {
    final response = await dio.get('/consents/customer/$customerId/active');
    if (response.data == null) return null;
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<void> setCustomerConsent({
    required String customerId,
    required bool granted,
  }) async {
    await dio.post(
      '/consents',
      data: {
        'customer_id': customerId,
        'granted': granted,
        'consent_text': granted
            ? 'Client consented to AI beauty processing.'
            : 'Client withdrew AI beauty processing consent.',
      },
    );
  }

  Future<Map<String, dynamic>> getSalonProfile() async {
    final response = await dio.get('/salons/me');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> updateSalonProfile({
    required String name,
    String? phone,
    String? instagram,
    String? tiktok,
  }) async {
    final response = await dio.patch(
      '/salons/me',
      data: {
        'name': name.trim(),
        'phone': phone == null || phone.trim().isEmpty ? null : phone.trim(),
        'instagram': instagram == null || instagram.trim().isEmpty
            ? null
            : instagram.trim(),
        'tiktok': tiktok == null || tiktok.trim().isEmpty
            ? null
            : tiktok.trim(),
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> getWatermarkSettings() async {
    final response = await dio.get('/watermarks/me');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> updateWatermarkSettings({
    required String position,
    required double opacity,
    required int size,
    required bool showPhone,
    required bool showInstagram,
    required bool showTikTok,
  }) async {
    final response = await dio.patch(
      '/watermarks/me',
      data: {
        'salon_name': true,
        'position': position,
        'opacity': opacity,
        'size': size,
        'phone': showPhone,
        'instagram': showInstagram,
        'tiktok': showTikTok,
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> uploadWatermarkLogo(XFile image) async {
    final data = FormData.fromMap({
      'file': await MultipartFile.fromFile(image.path, filename: image.name),
    });
    final response = await dio.post('/watermarks/me/logo', data: data);
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> deleteWatermarkLogo() async {
    final response = await dio.delete('/watermarks/me/logo');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<void> login(String email, String password) async {
    final response = await dio.post(
      '/auth/login',
      data: {'username': email, 'password': password},
      options: Options(contentType: Headers.formUrlEncodedContentType),
    );
    final data = Map<String, dynamic>.from(response.data as Map);
    await storage.write(key: _accessKey, value: data['access_token'] as String);
    await storage.write(key: _refreshKey, value: data['refresh_token'] as String);
  }

  Future<String?> _refreshAccessToken(String refreshToken) {
    final running = _refreshInFlight;
    if (running != null) return running;

    final future = () async {
      final refreshDio = Dio(
        BaseOptions(
          baseUrl: baseUrl,
          // Token refresh must tolerate the same Render cold-start delay.
          connectTimeout: const Duration(seconds: 75),
          sendTimeout: const Duration(seconds: 30),
          receiveTimeout: const Duration(seconds: 30),
          headers: const {'Accept': 'application/json'},
        ),
      );
      try {
        final response = await refreshDio.post(
          '/auth/refresh',
          data: {'refresh_token': refreshToken},
        );
        final data = Map<String, dynamic>.from(response.data as Map);
        final accessToken = data['access_token'] as String?;
        final rotatedRefresh = data['refresh_token'] as String?;
        if (accessToken == null || rotatedRefresh == null) return null;
        await storage.write(key: _accessKey, value: accessToken);
        await storage.write(key: _refreshKey, value: rotatedRefresh);
        return accessToken;
      } catch (_) {
        // Network, malformed-response and platform-storage errors all fail
        // closed; the interceptor will clear the unusable local session.
        return null;
      } finally {
        refreshDio.close(force: true);
      }
    }();

    _refreshInFlight = future;
    return future.whenComplete(() => _refreshInFlight = null);
  }

  Future<void> logout() async {
    final refreshToken = await storage.read(key: _refreshKey);
    if (refreshToken != null && refreshToken.isNotEmpty) {
      try {
        await dio.post('/auth/logout', data: {'refresh_token': refreshToken});
      } on DioException {
        // Local logout must still succeed when the API is unavailable.
      }
    }
    await logoutLocal();
  }

  Future<void> logoutLocal() async {
    await storage.delete(key: _accessKey);
    await storage.delete(key: _refreshKey);
  }

  Future<Map<String, dynamic>> getBeautyCapabilities() async {
    final response = await dio.get('/beauty/capabilities');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> processImage(
    XFile image, {
    double intensity = 0.7,
    bool consentConfirmed = false,
    String? customerId,
    required String makeupStyle,
    String photoFinish = 'Natural Finish',
    String engine = "classic",
    String generativeLook = "full_glam",
    bool externalAiConsent = false,
  }) async {
    final data = FormData.fromMap({
      'file': await MultipartFile.fromFile(image.path, filename: image.name),
    });
    final response = await dio.post(
      '/beauty/process-upload',
      queryParameters: {
        'intensity': intensity,
        'makeup_style': makeupStyle,
        'photo_finish': photoFinish,
        'engine': engine,
        'generative_look': generativeLook,
        'external_ai_consent': externalAiConsent,
        'consent_confirmed': consentConfirmed,
        if (customerId != null) 'customer_id': customerId,
      },
      data: data,
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Uint8List> fetchImage(String relativeUrl) async {
    final response = await dio.get<List<int>>(
      relativeUrl,
      options: Options(responseType: ResponseType.bytes),
    );
    return Uint8List.fromList(response.data ?? const <int>[]);
  }

  String imageUrl(String relativeUrl) {
    final root = baseUrl.replaceFirst(RegExp(r'/api/v1/?$'), '');
    return '$root$relativeUrl';
  }
}
