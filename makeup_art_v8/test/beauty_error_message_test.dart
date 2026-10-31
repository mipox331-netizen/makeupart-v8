import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/services/beauty_error_message.dart';

DioException _failure({
  int? statusCode,
  Object? data,
  Map<String, List<String>>? headers,
  DioExceptionType type = DioExceptionType.unknown,
}) {
  final request = RequestOptions(path: '/beauty/process-upload');
  final response = statusCode == null
      ? null
      : Response(
          requestOptions: request,
          statusCode: statusCode,
          data: data,
          headers: headers == null ? null : Headers.fromMap(headers),
        );
  return DioException(
    requestOptions: request,
    response: response,
    type: type,
  );
}

void main() {
  test('explains the plan required by the server', () {
    final message = beautyProcessingErrorMessage(
      _failure(
        statusCode: 403,
        data: {'detail': 'Feature not available'},
        headers: {'x-required-plan': ['Pro']},
      ),
    );

    expect(message, 'This editing option requires the PRO plan.');
  });

  test('explains exhausted monthly processing quota', () {
    expect(
      beautyProcessingErrorMessage(
        _failure(statusCode: 429, data: {'detail': 'Quota exceeded'}),
      ),
      contains('processing limit'),
    );
  });

  test('keeps useful portrait-validation details', () {
    expect(
      beautyProcessingErrorMessage(
        _failure(
          statusCode: 422,
          data: {'detail': 'No face detected in the provided image'},
        ),
      ),
      'No face detected in the provided image',
    );
  });

  test('never exposes internal traces from validation errors', () {
    final message = beautyProcessingErrorMessage(
      _failure(
        statusCode: 422,
        data: {'detail': 'Traceback (most recent call last): /srv/app/main.py'},
      ),
    );

    expect(message, contains('one visible face'));
    expect(message, isNot(contains('/srv/app')));
    expect(message, isNot(contains('Traceback')));
  });

  test('uses a safe support reference for server failures', () {
    expect(
      beautyProcessingErrorMessage(
        _failure(
          statusCode: 500,
          data: {'detail': 'Internal server error', 'request_id': 'beauty-123'},
        ),
      ),
      'The server could not process this photo. Support reference: beauty-123.',
    );
  });

  test('explains the Render cold-start timeout separately from lost internet', () {
    expect(
      beautyProcessingErrorMessage(
        _failure(type: DioExceptionType.connectionTimeout),
      ),
      contains('server is waking up'),
    );
  });

  test('distinguishes an unavailable network from an API rejection', () {
    expect(
      beautyProcessingErrorMessage(_failure()),
      contains('internet connection'),
    );
  });
}
