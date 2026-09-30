import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:image_picker/image_picker.dart';

class ApiClient {
  static const baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );
  static const _accessKey = 'makeupart_access_token';
  static const _refreshKey = 'makeupart_refresh_token';

  final FlutterSecureStorage storage;
  late final Dio dio;

  ApiClient({FlutterSecureStorage? storage}) : storage = storage ?? const FlutterSecureStorage() {
    dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 120),
      headers: {'Accept': 'application/json'},
    ));
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await this.storage.read(key: _accessKey);
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
    ));
  }

  Future<bool> hasSession() async =>
      (await storage.read(key: _accessKey))?.isNotEmpty == true;

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

  Future<void> logout() async {
    await storage.delete(key: _accessKey);
    await storage.delete(key: _refreshKey);
  }

  Future<Map<String, dynamic>> processImage(XFile image, {double intensity = 0.7}) async {
    final data = FormData.fromMap({
      'file': await MultipartFile.fromFile(image.path, filename: image.name),
      'intensity': intensity.toString(),
      'melanin_index': '2.0',
    });
    final response = await dio.post('/beauty/process-upload', data: data);
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
