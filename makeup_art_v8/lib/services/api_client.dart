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
  late final Dio dio;
  Future<String?>? _refreshInFlight;

  ApiClient({FlutterSecureStorage? storage}) : storage = storage ?? const FlutterSecureStorage() {
    dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 15),
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
              request.path.contains('/auth/refresh');

          if (!isUnauthorized || alreadyRetried || isAuthEndpoint) {
            handler.next(error);
            return;
          }

          final refreshToken = await this.storage.read(key: _refreshKey);
          if (refreshToken == null || refreshToken.isEmpty) {
            handler.next(error);
            return;
          }

          final accessToken = await _refreshAccessToken(refreshToken);
          if (accessToken == null) {
            await logoutLocal();
            handler.next(error);
            return;
          }

          request.extra['authRetried'] = true;
          request.headers['Authorization'] = 'Bearer $accessToken';
          try {
            final response = await dio.fetch(request);
            handler.resolve(response);
          } on DioException catch (retryError) {
            handler.next(retryError);
          }
        },
      ),
    );
  }

  Future<bool> hasSession() async =>
      (await storage.read(key: _accessKey))?.isNotEmpty == true;

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
      try {
        final refreshDio = Dio(BaseOptions(baseUrl: baseUrl));
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
      } on DioException {
        return null;
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

  Future<Map<String, dynamic>> processImage(
    XFile image, {
    double intensity = 0.7,
    bool consentConfirmed = false,
    String? customerId,
  }) async {
    final data = FormData.fromMap({
      'file': await MultipartFile.fromFile(image.path, filename: image.name),
    });
    final response = await dio.post(
      '/beauty/process-upload',
      queryParameters: {
        'intensity': intensity,
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
